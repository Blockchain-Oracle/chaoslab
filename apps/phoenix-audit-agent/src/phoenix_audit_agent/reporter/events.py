"""Replay-timeline artifact — reports/{run_id}/events.json (story-9.11).

Every audit's SSE frame stream is persisted verbatim so any finished run can
be replayed from wire truth. Same bucket/path conventions and create-only
upload as the report artifact set (ReportEmitter reuse).
"""

from __future__ import annotations

import json
from typing import Any

import structlog

from phoenix_audit_agent.reporter.emitter import ReportEmitter

_log = structlog.get_logger(__name__)


async def persist_run_events(
    run_id: str,
    frames: list[dict[str, Any]],
    *,
    created_at: str,
    emitter: ReportEmitter | None = None,
) -> bool:
    """Upload the recorded frame timeline. Contained: returns False on any
    failure (or when there is nothing to replay) — an events outage must
    never void a successful audit."""
    if not frames:
        _log.warning("events_persist_skipped_empty", run_id=run_id)
        return False
    document = {
        "run_id": run_id,
        "created_at": created_at,
        "duration_sec": frames[-1]["t"],
        "frames": frames,
    }
    payload = json.dumps(document, separators=(",", ":")).encode("utf-8")
    try:
        await (emitter or ReportEmitter()).emit(run_id, {"events.json": payload})
    except Exception:
        _log.error("events_persist_failed", run_id=run_id, frames=len(frames), exc_info=True)
        return False
    return True
