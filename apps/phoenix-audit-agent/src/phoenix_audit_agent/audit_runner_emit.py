"""Post-pipeline emission + finalize helpers extracted from `audit_runner`.

This module owns the work that runs AFTER the injector + judge + patcher have
produced a verdict tally and (optionally) a hardening recipe:

- `emit_signed_report` — generate + sign the report; emit `report` or the
  loud-skip frame.
- `persist_failure_timeline` — best-effort partial-timeline persistence on a
  crashed audit so /replay still has forensic value.
- `finalize_run` — registry write-through + `complete` frame + replay-timeline
  persistence on the success arm.
- `completion_fields` — typed `RunCompletion` constructor used by `finalize_run`.

**Test seam preserved.** The pre-9.7 tests monkeypatch collaborators (e.g.
`monkeypatch.setattr(ar, "generate_signed_report", fake)`) on the
`phoenix_audit_agent.audit_runner` module. To keep that contract working, the
collaborator lookups inside this file resolve via late imports from
`audit_runner` — never directly. A test that patches `ar.X` flows through
unchanged after the split.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

import structlog

from phoenix_audit_agent._time import parse_iso, utc_now_iso
from phoenix_audit_agent.reporter import ReportData
from phoenix_audit_agent.storage.models import RunCompletion

_log = structlog.get_logger(__name__)

EmitFn = Callable[[str, dict[str, Any]], Awaitable[None]]


async def emit_signed_report(
    report_data: ReportData,
    *,
    emit: EmitFn,
    run_id: str,
    recipe_markdown: str | None = None,
) -> dict[str, str] | None:
    """Generate + deliver the signed report; emit `report` or the loud skip.

    Report-delivery failure (KMS down, GCS down, renderer OSError) is CONTAINED:
    an audit whose verdicts and recipe all succeeded must not render as
    "failed" because the PDF could not be delivered. The skip is marked with
    the exception type — never silent (CLAUDE.md pattern #4).
    """
    from phoenix_audit_agent import audit_runner as _ar

    try:
        report_urls = await _ar.generate_signed_report(report_data, recipe_markdown=recipe_markdown)
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


def completion_fields(
    *,
    run_id: str,
    target_url: str,
    created_at: str,
    tally: Any,
    recipe_id: str | None,
    report_available: bool,
) -> RunCompletion:
    """Registry-index finalize payload — typed; `extra='forbid'` on the model
    makes a typo'd field a constructor error, never a silent drop."""
    try:
        started = parse_iso(created_at)
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
        finished_at=utc_now_iso(),
        duration_sec=duration_sec,
    )


async def persist_failure_timeline(
    *, run_id: str, target_url: str, created_at: str, frames: list[dict[str, Any]]
) -> None:
    """Best-effort partial-timeline write so /replay still works for crashed runs."""
    from phoenix_audit_agent import audit_runner as _ar

    if await _ar.persist_run_events(run_id, frames, created_at=created_at):
        await _ar.persist_run_completion(
            run_id,
            RunCompletion(
                run_id=run_id,
                target_url=target_url,
                created_at=created_at,
                phase="failed",
                events_available=True,
            ),
        )


async def finalize_run(
    *,
    run_id: str,
    target_url: str,
    created_at: str,
    tally: Any,
    recipe_id: str | None,
    markdown_url: str | None,
    report_urls: dict[str, str] | None,
    frames: list[dict[str, Any]],
    emit: EmitFn,
) -> None:
    """Registry finalize + complete frame + replay-timeline persistence."""
    from phoenix_audit_agent import audit_runner as _ar

    # Contained write-through; the complete frame discloses failure so the UI
    # never silently shows a run that history forgot.
    persisted = await _ar.persist_run_completion(
        run_id,
        completion_fields(
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
            "passed": tally.passed,
            "failed": tally.failed,
            "errored": tally.errored,
            "transport_failed": tally.transport_failed,
            "recipe_id": recipe_id,
            "markdown_url": markdown_url,
            "report_pdf_url": report_urls.get("report.pdf") if report_urls else None,
            "persistence_failed": not persisted,
        },
    )
    # Replay timeline AFTER the complete frame so the persisted file mirrors
    # the full stream. Contained: an events outage leaves events_available
    # False — the replay affordance simply never lights up for this run.
    if await _ar.persist_run_events(run_id, frames, created_at=created_at):
        flagged = await _ar.persist_run_completion(
            run_id,
            RunCompletion(
                run_id=run_id,
                target_url=target_url,
                created_at=created_at,
                phase="succeeded",
                events_available=True,
            ),
        )
        if not flagged:
            # GCS holds the timeline but the registry never learned it — name
            # the orphaned blob so the drift is greppable as one event.
            _log.error(
                "events_flag_finalize_failed",
                run_id=run_id,
                blob=f"reports/{run_id}/events.json",
            )


__all__ = [
    "completion_fields",
    "emit_signed_report",
    "finalize_run",
    "persist_failure_timeline",
]
