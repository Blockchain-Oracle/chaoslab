"""The REAL audit pipeline behind POST /run.

Drives Injector -> Judge (rubrics + clustering) -> Patcher -> MarkdownEmitter
against a live target, emitting per-probe SSE frames the chamber UI renders:

    phase_change -> test_started/test_completed (per attack)
    -> phase_change -> test_verdict (per attack) -> cluster_set
    -> phase_change -> recipe -> complete

Collaborators are module attributes so tests can monkeypatch the seams
(`Injector`, `apply_rubric`, `span_honored`, `run_clustering`, `Patcher`,
`MarkdownEmitter`, `make_phoenix_client`, `generate_signed_report`,
`persist_run_completion`) without touching the wire protocol.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from time import monotonic
from typing import Any

import structlog
from openinference.instrumentation import using_attributes
from pydantic import HttpUrl

from phoenix_audit_agent._time import utc_now_iso
from phoenix_audit_agent.audit_runner_emit import (
    emit_signed_report,
    finalize_run,
    persist_failure_timeline,
)
from phoenix_audit_agent.config import get_settings
from phoenix_audit_agent.injector.agent import AttackResult, AttackRun, Injector, InjectorState
from phoenix_audit_agent.injector.target_adapters import AdapterTier, ADKAdapter, TargetSpec
from phoenix_audit_agent.judge import AnnotationWritebackError, run_clustering
from phoenix_audit_agent.judge.rubrics import apply_rubric
from phoenix_audit_agent.judge_phase import judge_attacks
from phoenix_audit_agent.patcher._markdown_renderer import render_recipe
from phoenix_audit_agent.patcher.agent import Patcher
from phoenix_audit_agent.patcher.markdown_emitter import MarkdownEmitter
from phoenix_audit_agent.phoenix_tools.run_experiment import _build_client
from phoenix_audit_agent.reporter import ReportData
from phoenix_audit_agent.reporter.events import (
    persist_run_events,  # noqa: F401  re-exported monkeypatch seam read by audit_runner_emit
)
from phoenix_audit_agent.reporter.honored import span_honored
from phoenix_audit_agent.reporter.service import (
    generate_signed_report,  # noqa: F401  re-exported monkeypatch seam read by audit_runner_emit
)
from phoenix_audit_agent.storage.runs import (
    persist_run_completion,  # noqa: F401  re-exported monkeypatch seam read by audit_runner_emit
)

_log = structlog.get_logger(__name__)

EmitFn = Callable[[str, dict[str, Any]], Awaitable[None]]
SetPhaseFn = Callable[[str], None]

# The demo target is the Meridian-style customer-support agent
# (lookup_order / refund / escalate) — this prompt exercises its tool path.
DEFAULT_AUDIT_PROMPT = (
    "Please look up order ORD-1001 and tell me whether it qualifies for a refund."
)


def _recording_emit(inner: EmitFn, frames: list[dict[str, Any]]) -> EmitFn:
    """Wrap emit so every streamed frame also lands in the replay timeline
    with a relative-seconds stamp — what the operator watched live IS what
    replay shows later, by construction."""
    started = monotonic()

    async def record_and_emit(event: str, payload: dict[str, Any]) -> None:
        # Shallow copy: a post-emit payload mutation must not silently
        # diverge the persisted replay from what was streamed live.
        frames.append({"t": round(monotonic() - started, 3), "event": event, "data": dict(payload)})
        await inner(event, payload)

    return record_and_emit


def make_phoenix_client() -> Any:
    """Phoenix AsyncClient via the canonical settings-driven constructor."""
    return _build_client(get_settings())


def build_adapter(target_url: str) -> Any:
    """Adapter for the target. v1: ADK/A2A — the demo path. Cross-framework
    selection keys off run-config `target.framework` once the wizard sends it
    (the Epic 3 adapters are already in-tree)."""
    return ADKAdapter(
        TargetSpec(tier=AdapterTier.TIER1_ADK, url=HttpUrl(target_url), framework="adk-a2a")
    )


async def _run_injector(
    *,
    run_id: str,
    target_url: str,
    runs_per_fault: int,
    prompt: str,
    emit: EmitFn,
    dataset_slug: str | None = None,
) -> InjectorState:
    """Injector phase: drive the attack battery, emitting per-probe frames.

    Story-9.15: `dataset_slug` (when set) tags the synthetic-battery probes
    with `origin="battery"` (the dataset-row probes get `origin=f"dataset:{slug}"`
    when the row-interleave loop lands). The discriminator on the SSE frame
    lets the chamber UI label each probe row by where it came from.
    """
    adapter = build_adapter(target_url)
    state = InjectorState()
    _ = dataset_slug  # reserved for the row-interleave loop in a follow-up

    async def _on_start(attack: AttackRun) -> None:
        await emit(
            "test_started",
            {
                "n": attack.run_idx + 1,
                "fault_class": attack.fault_class,
                "origin": "battery",
                "run_id": run_id,
            },
        )

    async def _on_end(result: AttackResult) -> None:
        await emit(
            "test_completed",
            {
                "n": result.run_idx + 1,
                "fault_class": result.fault_class,
                "origin": "battery",
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
    return state


async def drive_audit(
    *,
    run_id: str,
    target_url: str,
    runs_per_fault: int,
    emit: EmitFn,
    set_phase: SetPhaseFn,
    prompt: str = DEFAULT_AUDIT_PROMPT,
    created_at: str | None = None,
    owner_uid: str | None = None,
) -> None:
    """Run one full audit and emit the SSE event stream.

    Raises on pipeline failure (caller frames error/cancelled). Story 9.7:
    every emitted span runs under `using_attributes(session_id=run_id, ...)`
    so the Phoenix Sessions tab groups by run_id; `user_id=owner_uid` only
    when owner_uid is a non-empty string — None and "" both collapse to
    "scope without user.id" (OpenInference empty-string is a contract no-op).
    """
    created_at = created_at or utc_now_iso()
    frames: list[dict[str, Any]] = []
    emit = _recording_emit(emit, frames)
    # "no tenant" stays distinct from "any-falsy tenant" at the call site —
    # silent-failure pattern #1 (CLAUDE.md): never let `""` masquerade as a
    # populated identity. owner_uid=None or "" => scope without user.id.
    ctx = (
        using_attributes(session_id=run_id, user_id=owner_uid)
        if owner_uid
        else using_attributes(session_id=run_id)
    )
    with ctx:
        try:
            # ---- injector ---------------------------------------------------------
            set_phase("injector")
            await emit("phase_change", {"phase": "injector", "run_id": run_id})
            state = await _run_injector(
                run_id=run_id,
                target_url=target_url,
                runs_per_fault=runs_per_fault,
                prompt=prompt,
                emit=emit,
            )

            # ---- judge ------------------------------------------------------------
            set_phase("judge")
            await emit("phase_change", {"phase": "judge", "run_id": run_id})

            phoenix = make_phoenix_client()
            tally = await judge_attacks(
                state,
                phoenix,
                emit=emit,
                run_id=run_id,
                project=get_settings().TARGET_PHOENIX_PROJECT,
                # module attributes read at run start — the documented monkeypatch seams
                apply_rubric=apply_rubric,
                span_honored=span_honored,
                # The rubrics receive the auditor-known original prompt directly —
                # it never round-trips through span attributes.
                prompt=prompt,
            )
            failures, passed, failed, errored, transport_failed = (
                tally.failures,
                tally.passed,
                tally.failed,
                tally.errored,
                tally.transport_failed,
            )

            recipe_id: str | None = None
            markdown_url: str | None = None
            recipe_markdown: str | None = None
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
                # The durable PDF renders the recipe CONTENT — never the expiring
                # signed URL (story-9.13). render_recipe is pure; same bytes as
                # the uploaded artifact.
                recipe_markdown = render_recipe(recipe)
                await emit(
                    "recipe",
                    {"recipe_id": recipe_id, "markdown_url": markdown_url, "run_id": run_id},
                )

            # Every audit run yields a signed report — including the clean bill.
            report_data = ReportData(
                run_id=run_id,
                target_url=target_url,
                framework_label="EU AI Act · high-risk system",
                created_at=created_at,
                probes=tally.report_probes,
                passed=passed,
                failed=failed,
                errored=errored,
                transport_failed=transport_failed,
                cluster_ids=[c.cluster_id for c in cluster_set.clusters] if cluster_set else [],
                root_causes=[c.root_cause for c in cluster_set.clusters] if cluster_set else [],
                excluded_transport_failures=transport_failed,
                annotation_writeback_failed=writeback_failed,
                # Same predicate as the SSE `cluster_set` skip frame above — an
                # all-rubric-errored run (failed=0, errored>0) must disclose the skip
                # in the SIGNED report too, not only in the live stream.
                clustering_skipped=(
                    "no_clusterable_failures"
                    if cluster_set is None and (failed > 0 or errored > 0)
                    else None
                ),
                recipe_id=recipe_id,
                markdown_url=markdown_url,
                honored_missing_count=tally.honored_missing,
                honored_unreadable_count=tally.honored_unreadable,
            )
            report_urls = await emit_signed_report(
                report_data, emit=emit, run_id=run_id, recipe_markdown=recipe_markdown
            )

            set_phase("succeeded")
            await finalize_run(
                run_id=run_id,
                target_url=target_url,
                created_at=created_at,
                tally=tally,
                recipe_id=recipe_id,
                markdown_url=markdown_url,
                report_urls=report_urls,
                frames=frames,
                emit=emit,
            )
        except Exception:
            # The partial timeline of a FAILED audit is exactly when replay
            # matters for forensics — persist what was recorded (contained).
            await persist_failure_timeline(
                run_id=run_id, target_url=target_url, created_at=created_at, frames=frames
            )
            raise
