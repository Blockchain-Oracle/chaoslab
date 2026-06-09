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
from chaoslab_agent.judge import FailedSpan, run_clustering
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
    failures: list[FailedSpan] = []
    passed = 0
    failed = 0

    for result in state.attack_results:
        n = result.run_idx + 1
        transport_ok = result.status == "ok" and bool(_HEX_SPAN.fullmatch(result.span_id))
        if not transport_ok:
            # Real failure, but no span evidence the rubric/clusterer can use.
            failed += 1
            await emit(
                "test_verdict",
                {
                    "n": n,
                    "verdict": "fail",
                    "span_id": result.span_id,
                    "score": 0.0,
                    "transport_error": True,
                    "run_id": run_id,
                },
            )
            continue

        score = await apply_rubric(
            RubricInput(
                span_id=result.span_id,
                fault_class=result.fault_class,
                phoenix_client=phoenix,
            )
        )
        if score.passed:
            passed += 1
        else:
            failed += 1
            excerpt = score.reason.strip()[:500] or result.fault_class
            failures.append(
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
                "span_id": result.span_id,
                "score": score.score,
                "transport_error": False,
                "run_id": run_id,
            },
        )

    recipe_id: str | None = None
    markdown_url: str | None = None

    if failures:
        cluster_set = await run_clustering(failures, phoenix)
        await emit(
            "cluster_set",
            {
                "clusters": len(cluster_set.clusters),
                "total_failures": cluster_set.total_failures,
                "cluster_ids": [c.cluster_id for c in cluster_set.clusters],
                "root_causes": [c.root_cause for c in cluster_set.clusters],
                "run_id": run_id,
            },
        )

        # ---- patcher ------------------------------------------------------
        set_phase("patcher")
        await emit("phase_change", {"phase": "patcher", "run_id": run_id})

        recipe = await Patcher().run(cluster_set, target_agent_id=target_url)
        emit_result = await MarkdownEmitter().emit(recipe)
        recipe_id = recipe.recipe_id
        markdown_url = emit_result.signed_url
        await emit(
            "recipe",
            {"recipe_id": recipe_id, "markdown_url": markdown_url, "run_id": run_id},
        )
    else:
        # Clean audit — nothing to cluster, nothing to patch. The phase rail
        # still walks patcher so the chamber completes its arc.
        _log.info("audit_clean_run", run_id=run_id, attacks=state.total_attacks)
        set_phase("patcher")
        await emit("phase_change", {"phase": "patcher", "run_id": run_id})

    set_phase("succeeded")
    await emit(
        "complete",
        {
            "phase": "succeeded",
            "run_id": run_id,
            "passed": passed,
            "failed": failed,
            "recipe_id": recipe_id,
            "markdown_url": markdown_url,
        },
    )
