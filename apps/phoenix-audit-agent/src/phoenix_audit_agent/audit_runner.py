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
from datetime import UTC, datetime
from typing import Any

import structlog
from pydantic import HttpUrl

from phoenix_audit_agent.config import get_settings
from phoenix_audit_agent.injector.agent import AttackResult, AttackRun, Injector, InjectorState
from phoenix_audit_agent.injector.target_adapters import AdapterTier, ADKAdapter, TargetSpec
from phoenix_audit_agent.judge import AnnotationWritebackError, run_clustering
from phoenix_audit_agent.judge.rubrics import apply_rubric
from phoenix_audit_agent.judge_phase import judge_attacks
from phoenix_audit_agent.patcher.agent import Patcher
from phoenix_audit_agent.patcher.markdown_emitter import MarkdownEmitter
from phoenix_audit_agent.phoenix_tools.run_experiment import _build_client
from phoenix_audit_agent.reporter import ReportData
from phoenix_audit_agent.reporter.honored import span_honored
from phoenix_audit_agent.reporter.service import generate_signed_report
from phoenix_audit_agent.storage.models import RunCompletion
from phoenix_audit_agent.storage.runs import persist_run_completion

_log = structlog.get_logger(__name__)

EmitFn = Callable[[str, dict[str, Any]], Awaitable[None]]
SetPhaseFn = Callable[[str], None]

# The demo target is the Meridian-style customer-support agent
# (lookup_order / refund / escalate) — this prompt exercises its tool path.
DEFAULT_AUDIT_PROMPT = (
    "Please look up order ORD-1001 and tell me whether it qualifies for a refund."
)


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


async def _emit_signed_report(
    report_data: ReportData, *, emit: EmitFn, run_id: str
) -> dict[str, str] | None:
    """Generate + deliver the signed report; emit `report` or the loud skip.

    Report-delivery failure (KMS down, GCS down, renderer OSError) is
    CONTAINED: an audit whose verdicts and recipe all succeeded must not
    render as "failed" because the PDF could not be delivered. The skip is
    marked with the exception type — never silent (CLAUDE.md pattern #4).
    """
    try:
        report_urls = await generate_signed_report(report_data)
    except Exception as report_err:
        _log.error(
            "report_generation_failed",
            run_id=run_id,
            exc_type=type(report_err).__name__,
            error=str(report_err),
            exc_info=True,
        )
        await emit(
            "report_skipped",
            {
                "reason": f"generation_failed:{type(report_err).__name__}",
                "run_id": run_id,
            },
        )
        return None
    if report_urls is None:
        await emit(
            "report_skipped",
            {"reason": "signing_key_not_configured", "run_id": run_id},
        )
        return None
    await emit(
        "report",
        {
            "pdf_url": report_urls.get("report.pdf"),
            "json_url": report_urls.get("report.json"),
            "signature_url": report_urls.get("signature.json"),
            "run_id": run_id,
        },
    )
    return report_urls


def _completion_fields(
    *,
    run_id: str,
    target_url: str,
    created_at: str,
    tally: Any,
    recipe_id: str | None,
    report_available: bool,
) -> RunCompletion:
    """Registry-index finalize payload — typed; extra='forbid' on the model
    makes a typo'd field a constructor error, never a silent drop."""
    try:
        started = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        duration_sec: float | None = round((datetime.now(UTC) - started).total_seconds(), 1)
    except ValueError:
        duration_sec = None
    return RunCompletion(
        run_id=run_id,
        target_url=target_url,
        created_at=created_at,
        phase="succeeded",
        passed=tally.passed,
        failed=tally.failed,
        errored=tally.errored,
        transport_failed=tally.transport_failed,
        recipe_id=recipe_id,
        report_available=report_available,
        finished_at=datetime.now(UTC).isoformat(),
        duration_sec=duration_sec,
    )


async def drive_audit(
    *,
    run_id: str,
    target_url: str,
    runs_per_fault: int,
    emit: EmitFn,
    set_phase: SetPhaseFn,
    prompt: str = DEFAULT_AUDIT_PROMPT,
    created_at: str | None = None,
) -> None:
    """Run one full audit and emit the SSE event stream.

    Raises on pipeline failure — the caller (main._drive_orchestrator) owns
    the error/cancelled framing and the queue sentinel.
    """
    created_at = created_at or datetime.now(UTC).isoformat()
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
    tally = await judge_attacks(
        state,
        phoenix,
        emit=emit,
        run_id=run_id,
        project=get_settings().TARGET_PHOENIX_PROJECT,
        # module attributes read at run start — the documented monkeypatch seams
        apply_rubric=apply_rubric,
        span_honored=span_honored,
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
        clustering_skipped=(
            "no_clusterable_failures" if cluster_set is None and failed > 0 else None
        ),
        recipe_id=recipe_id,
        markdown_url=markdown_url,
        honored_missing_count=tally.honored_missing,
        honored_unreadable_count=tally.honored_unreadable,
    )
    report_urls = await _emit_signed_report(report_data, emit=emit, run_id=run_id)

    set_phase("succeeded")
    # Contained write-through to the registry index; the frame discloses
    # failure so the UI never silently shows a run that history forgot.
    persisted = await persist_run_completion(
        run_id,
        _completion_fields(
            run_id=run_id,
            target_url=target_url,
            created_at=created_at,
            tally=tally,
            recipe_id=recipe_id,
            report_available=report_urls is not None,
        ),
    )
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
            "report_pdf_url": report_urls.get("report.pdf") if report_urls else None,
            "persistence_failed": not persisted,
        },
    )
