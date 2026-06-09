"""The REAL audit pipeline behind POST /run.

Drives Injector -> Judge (rubrics + clustering) -> Patcher -> MarkdownEmitter
against a live target, emitting per-probe SSE frames the chamber UI renders:

    phase_change -> test_started/test_completed (per attack)
    -> phase_change -> test_verdict (per attack) -> cluster_set
    -> phase_change -> recipe -> complete

Collaborators are module attributes so tests can monkeypatch the seams
(`Injector`, `apply_rubric`, `run_clustering`, `Patcher`, `MarkdownEmitter`,
`make_phoenix_client`) without touching the wire protocol.
"""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from typing import Any

import structlog
from pydantic import HttpUrl

from chaoslab_agent.config import get_settings
from chaoslab_agent.injector.agent import (
    AttackResult,
    AttackRun,
    Injector,
    InjectorState,
)
from chaoslab_agent.injector.target_adapters import AdapterTier, ADKAdapter, TargetSpec
from chaoslab_agent.judge import AnnotationWritebackError, FailedSpan, run_clustering
from chaoslab_agent.judge.rubrics import RubricInput, apply_rubric
from chaoslab_agent.patcher.agent import Patcher
from chaoslab_agent.patcher.markdown_emitter import MarkdownEmitter
from chaoslab_agent.phoenix_tools.run_experiment import _build_client

_log = structlog.get_logger(__name__)

EmitFn = Callable[[str, dict[str, Any]], Awaitable[None]]
SetPhaseFn = Callable[[str], None]

# The demo target is the Meridian-style customer-support agent
# (lookup_order / refund / escalate) — this prompt exercises its tool path.
DEFAULT_AUDIT_PROMPT = (
    "Please look up order ORD-1001 and tell me whether it qualifies for a refund."
)

# Mirrors chaoslab_agent.judge.rubrics._base.SPAN_ID_PATTERN: rubrics reject
# anything that is not a 16- or 32-char hex id, so transport failures that
# never produced a span are scored at the transport level instead.
_HEX_SPAN = re.compile(r"^[0-9a-f]{16}(?:[0-9a-f]{16})?$")


def make_phoenix_client() -> Any:
    """Phoenix AsyncClient via the canonical settings-driven constructor."""
    return _build_client(get_settings())


def build_adapter(target_url: str) -> Any:
    """Adapter for the target. v1: ADK/A2A — the demo path.

    Cross-framework selection (langchain-http / crewai-http / openai-agents /
    http-blackbox) keys off the run-config `target.framework` field once the
    wizard sends it; the adapters themselves shipped in Epic 3.
    """
    return ADKAdapter(
        TargetSpec(tier=AdapterTier.TIER1_ADK, url=HttpUrl(target_url), framework="adk-a2a")
    )


class _JudgeTally:
    """Per-run judge outcome — counts plus the clusterable failure set."""

    def __init__(self) -> None:
        self.failures: list[FailedSpan] = []
        self.passed = 0
        self.failed = 0
        self.errored = 0
        self.transport_failed = 0


async def _judge_attacks(
    state: InjectorState,
    phoenix: Any,
    *,
    emit: EmitFn,
    run_id: str,
) -> _JudgeTally:
    """Score every attack with the per-fault rubric, emitting test_verdict frames.

    Containment rules (review findings on PR #81):
    - transport failures (status != ok, or no usable span id) are real FAILs
      with `transport_error: true` and are excluded from the clusterable set;
    - a rubric exception yields a MARKED `error` verdict (`rubric_error: true`)
      and never voids the other probes' verdicts (CLAUDE.md pattern #4).
    """
    tally = _JudgeTally()
    for result in state.attack_results:
        n = result.run_idx + 1
        transport_ok = result.status == "ok" and bool(_HEX_SPAN.fullmatch(result.span_id))
        if not transport_ok:
            tally.failed += 1
            tally.transport_failed += 1
            await emit(
                "test_verdict",
                {
                    "n": n,
                    "verdict": "fail",
                    "fault_class": result.fault_class,
                    "span_id": result.span_id,
                    "score": 0.0,
                    "transport_error": True,
                    "run_id": run_id,
                },
            )
            continue

        try:
            score = await apply_rubric(
                RubricInput(
                    span_id=result.span_id,
                    fault_class=result.fault_class,
                    phoenix_client=phoenix,
                )
            )
        except Exception as rubric_err:
            tally.errored += 1
            _log.error(
                "rubric_failed",
                run_id=run_id,
                span_id=result.span_id,
                fault_class=result.fault_class,
                exc_type=type(rubric_err).__name__,
                error=str(rubric_err),
                exc_info=True,
            )
            await emit(
                "test_verdict",
                {
                    "n": n,
                    "verdict": "error",
                    "rubric_error": True,
                    "fault_class": result.fault_class,
                    "span_id": result.span_id,
                    "score": 0.0,
                    "transport_error": False,
                    "run_id": run_id,
                },
            )
            continue

        if score.passed:
            tally.passed += 1
        else:
            tally.failed += 1
            excerpt = score.reason.strip()[:500] or "[rubric returned no reason]"
            tally.failures.append(
                FailedSpan(
                    span_id=result.span_id,
                    fault_class=result.fault_class,
                    eval_score=score,
                    trace_excerpt=excerpt,
                )
            )
        await emit(
            "test_verdict",
            {
                "n": n,
                "verdict": "pass" if score.passed else "fail",
                "fault_class": result.fault_class,
                "span_id": result.span_id,
                "score": score.score,
                "transport_error": False,
                "run_id": run_id,
            },
        )
    return tally


async def drive_audit(
    *,
    run_id: str,
    target_url: str,
    runs_per_fault: int,
    emit: EmitFn,
    set_phase: SetPhaseFn,
    prompt: str = DEFAULT_AUDIT_PROMPT,
) -> None:
    """Run one full audit and emit the SSE event stream.

    Raises on pipeline failure — the caller (main._drive_orchestrator) owns
    the error/cancelled framing and the queue sentinel.
    """
    # ---- injector ---------------------------------------------------------
    set_phase("injector")
    await emit("phase_change", {"phase": "injector", "run_id": run_id})

    adapter = build_adapter(target_url)
    state = InjectorState()

    async def _on_start(attack: AttackRun) -> None:
        await emit(
            "test_started",
            {
                "n": attack.run_idx + 1,
                "fault_class": attack.fault_class,
                "run_id": run_id,
            },
        )

    async def _on_end(result: AttackResult) -> None:
        await emit(
            "test_completed",
            {
                "n": result.run_idx + 1,
                "fault_class": result.fault_class,
                "status": result.status,
                "span_id": result.span_id,
                "duration_ms": result.duration_ms,
                "run_id": run_id,
            },
        )

    injector = Injector(
        target=adapter,
        state=state,
        prompt=prompt,
        runs_per_fault=runs_per_fault,
        on_attack_start=_on_start,
        on_attack_end=_on_end,
    )
    await injector.run()

    # ---- judge ------------------------------------------------------------
    set_phase("judge")
    await emit("phase_change", {"phase": "judge", "run_id": run_id})

    phoenix = make_phoenix_client()
    tally = await _judge_attacks(state, phoenix, emit=emit, run_id=run_id)
    failures = tally.failures
    passed = tally.passed
    failed = tally.failed
    errored = tally.errored
    transport_failed = tally.transport_failed

    recipe_id: str | None = None
    markdown_url: str | None = None
    cluster_set = None
    writeback_failed = False

    if failures:
        try:
            cluster_set = await run_clustering(failures, phoenix)
        except AnnotationWritebackError as wb:
            # Clustering SUCCEEDED — only the Phoenix annotation write-back
            # failed, and the exception preserves the valid cluster_set for
            # exactly this recovery. Discarding it would void a good result
            # over a telemetry hiccup.
            cluster_set = wb.cluster_set
            writeback_failed = True
            _log.error(
                "annotation_writeback_failed",
                run_id=run_id,
                attempted=wb.attempted_count,
                error=str(wb),
                exc_info=True,
            )
        await emit(
            "cluster_set",
            {
                "clusters": len(cluster_set.clusters),
                "total_failures": cluster_set.total_failures,
                "cluster_ids": [c.cluster_id for c in cluster_set.clusters],
                "root_causes": [c.root_cause for c in cluster_set.clusters],
                "excluded_transport_failures": transport_failed,
                "rubric_errors": errored,
                "annotation_writeback_failed": writeback_failed,
                "run_id": run_id,
            },
        )
    elif failed > 0 or errored > 0:
        # Failures exist but none are clusterable (all transport-level and/or
        # rubric-errored). This is NOT a clean audit — say so explicitly so
        # the chamber and the report can explain the missing cluster/recipe.
        _log.warning(
            "audit_no_clusterable_failures",
            run_id=run_id,
            transport_failed=transport_failed,
            rubric_errors=errored,
            failed=failed,
        )
        await emit(
            "cluster_set",
            {
                "clusters": 0,
                "total_failures": 0,
                "cluster_ids": [],
                "root_causes": [],
                "excluded_transport_failures": transport_failed,
                "rubric_errors": errored,
                "annotation_writeback_failed": False,
                "skipped": "no_clusterable_failures",
                "run_id": run_id,
            },
        )
    else:
        # Clean audit — every probe passed. Nothing to cluster or patch.
        _log.info("audit_clean_run", run_id=run_id, attacks=state.total_attacks)

    # The phase rail always walks patcher so the chamber completes its arc.
    set_phase("patcher")
    await emit("phase_change", {"phase": "patcher", "run_id": run_id})

    if cluster_set is not None:
        recipe = await Patcher().run(cluster_set, target_agent_id=target_url)
        emit_result = await MarkdownEmitter().emit(recipe)
        recipe_id = recipe.recipe_id
        markdown_url = emit_result.signed_url
        await emit(
            "recipe",
            {"recipe_id": recipe_id, "markdown_url": markdown_url, "run_id": run_id},
        )

    set_phase("succeeded")
    await emit(
        "complete",
        {
            "phase": "succeeded",
            "run_id": run_id,
            "passed": passed,
            "failed": failed,
            "errored": errored,
            "transport_failed": transport_failed,
            "recipe_id": recipe_id,
            "markdown_url": markdown_url,
        },
    )
