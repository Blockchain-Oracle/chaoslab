"""Post-pipeline emission + finalize helpers extracted from `audit_runner`.

This module owns the work that runs AFTER the injector + judge + patcher have
produced a verdict tally and (optionally) a hardening recipe:

- `emit_signed_report` — generate + sign the report; emit `report` or the
  loud-skip frame.
- `persist_failure_timeline` — best-effort partial-timeline persistence on a
  crashed audit so /replay still has forensic value.
- `finalize_run` — registry write-through + `complete` frame + replay-timeline
  persistence on the success arm. Threads story-9.15's dataset snapshot +
  regression upsert via `audit_runner_datasets`.
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
from phoenix_audit_agent.audit_runner_datasets import (
    build_dataset_snapshot,
    try_regression_upsert,
)
from phoenix_audit_agent.reporter import ReportData
from phoenix_audit_agent.storage.models import RunCompletion

_log = structlog.get_logger(__name__)

EmitFn = Callable[[str, dict[str, Any]], Awaitable[None]]

# Round-3 S-2: literal for `RunCompletion.regression_overwrite_mode` —
# one canonical string so tests + code never drift. Story-9.16 will add
# SDK-side strategies (e.g. "phoenix_delete_then_recreate") alongside.
REGRESSION_OVERWRITE_NEWEST_WINS = "newest_wins"


def _check_dataset_snapshot_keys_match_completion() -> None:
    """Round-5 LOW-1: module-load drift guard. `_apply_dataset_evidence`
    setattr's the snapshot dict keys onto `RunCompletion`. If
    `dataset_snapshot_fields` ever returns a key that isn't a
    `RunCompletion` field, the setattr raises on a `extra="forbid"`
    Pydantic model and crashloops the audit at finalize. Surface that
    contract drift at import time so deployments fail fast on rollout,
    not silently mid-audit. (CLAUDE.md silent-failure pattern: module-
    load drift guards.)
    """
    from phoenix_audit_agent.audit_runner_datasets import dataset_snapshot_fields
    from phoenix_audit_agent.storage.models import DatasetIndex, RunCompletion

    sentinel = DatasetIndex(
        dataset_id="x",
        phoenix_dataset_id="x",
        name="x",
        kind="battery",
        owner_uid=None,
        agent_id=None,
        row_count=0,
        source_url=None,
        content_hash="sha256:x",
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
    )
    snapshot_keys = set(dataset_snapshot_fields(idx=sentinel, version_id="x").keys())
    completion_keys = set(RunCompletion.model_fields)
    missing = snapshot_keys - completion_keys
    if missing:
        msg = (
            f"dataset_snapshot_fields emits keys absent from RunCompletion: "
            f"{sorted(missing)!r}. Add the fields to RunCompletion or trim "
            f"the snapshot — silent-failure pattern (module-load drift)."
        )
        raise RuntimeError(msg)


_check_dataset_snapshot_keys_match_completion()


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
    makes a typo'd field a constructor error, never a silent drop.

    Note (story-9.15): `RunCompletion` carries the dataset_* + regression_*
    snapshot fields. We populate them inside `finalize_run` via attribute
    assignment so the contained snapshot helper can return None without
    forcing the function signature to grow."""
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


async def _apply_dataset_evidence(
    completion: RunCompletion,
    *,
    run_id: str,
    dataset_id: str | None,
    agent_id: str | None,
    owner_uid: str | None,
    failing_rows: list[dict[str, Any]] | None,
) -> None:
    """Story-9.15 finalize attachments — snapshot + regression upsert.

    Mutates `completion` in place. Both halves are contained: any failure
    in the dataset snapshot or the regression upsert leaves the
    completion intact and lets the audit finalize cleanly.
    """
    if dataset_id is not None:
        snapshot = await build_dataset_snapshot(dataset_id=dataset_id, run_id=run_id)
        if snapshot is not None:
            for key, value in snapshot.items():
                setattr(completion, key, value)
    if agent_id is not None and owner_uid is not None and failing_rows:
        version_id = await try_regression_upsert(
            agent_id=agent_id,
            owner_uid=owner_uid,
            failing_rows=failing_rows,
            run_id=run_id,
        )
        if version_id is not None:
            # "newest_wins" describes the dedup semantics, true on both
            # fake AND real SDK paths. The constant lives at module top
            # (round-3 S-2) so tests + code never drift on the literal.
            completion.regression_overwrite_mode = REGRESSION_OVERWRITE_NEWEST_WINS


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
    dataset_id: str | None = None,
    agent_id: str | None = None,
    owner_uid: str | None = None,
    failing_rows: list[dict[str, Any]] | None = None,
) -> None:
    """Registry finalize + complete frame + replay-timeline persistence.

    Story 9.15: when `dataset_id` is set, the dataset name + Phoenix ids
    snapshot onto `RunCompletion`. When `agent_id` is set + `failing_rows`
    is non-empty, those rows append into `regression-<agent_id>` via the
    upsert path. Both are contained — a Phoenix outage during
    snapshot/upsert doesn't fail the finalize."""
    from phoenix_audit_agent import audit_runner as _ar

    completion = completion_fields(
        run_id=run_id,
        target_url=target_url,
        created_at=created_at,
        tally=tally,
        recipe_id=recipe_id,
        report_available=report_urls is not None,
    )
    await _apply_dataset_evidence(
        completion,
        run_id=run_id,
        dataset_id=dataset_id,
        agent_id=agent_id,
        owner_uid=owner_uid,
        failing_rows=failing_rows,
    )

    # Contained write-through; the complete frame discloses failure so the UI
    # never silently shows a run that history forgot.
    persisted = await _ar.persist_run_completion(run_id, completion)
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
            _log.error(
                "events_flag_finalize_failed",
                run_id=run_id,
                blob=f"reports/{run_id}/events.json",
            )
    # Story-9.5: scheduled-summary email, LAST — mail must never delay the
    # complete frame or the replay timeline. Double-contained: the hook
    # contains internally, and this guard keeps a monkeypatched/future hook
    # from ever failing a finalize.
    from phoenix_audit_agent.notifier import report_mail

    try:
        await report_mail.maybe_send_scheduled_summary(run_id)
    except Exception:
        _log.error("schedule_email_hook_failed", run_id=run_id, exc_info=True)


__all__ = [
    "REGRESSION_OVERWRITE_NEWEST_WINS",
    "completion_fields",
    "emit_signed_report",
    "finalize_run",
    "persist_failure_timeline",
]
