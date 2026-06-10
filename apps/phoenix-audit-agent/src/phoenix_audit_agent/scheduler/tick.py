"""The scheduler tick: claim due schedules, launch runs, disclose failures.

Claim happens BEFORE launch — a crash between the two skips one tick (safe);
the reverse order would double-fire (a regulator-visible duplicate audit).
Per-schedule launch failures are contained and counted: one broken target
must not block the rest of the fleet's monitoring.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta

import structlog
from pydantic import BaseModel

from phoenix_audit_agent.storage.models import Cadence, ScheduleRecord
from phoenix_audit_agent.storage.schedules import ScheduleStore

_log = structlog.get_logger(__name__)

# schedule -> run_id of the launched audit
LaunchFn = Callable[[ScheduleRecord], Awaitable[str]]

_INTERVALS: dict[Cadence, timedelta] = {
    "hourly": timedelta(hours=1),
    "daily": timedelta(days=1),
}


class TickResult(BaseModel):
    claimed: int
    launched: list[str]
    launch_failures: int
    # Disclosure counters: corrupted schedule docs skipped during the claim,
    # and post-launch bookkeeping (mark_fired) failures — operators must see
    # both in the tick response, not only in logs.
    corrupted_docs: int = 0
    bookkeeping_failures: int = 0


def advance_fire_time(record: ScheduleRecord) -> str:
    """Next fire time anchored to the OLD schedule (no drift), fast-forwarded
    past `now` so a long outage produces ONE catch-up run, not a backlog."""
    interval = _INTERVALS[record.cadence]
    now = datetime.now(UTC)
    try:
        next_at = datetime.fromisoformat(record.next_fire_at.replace("Z", "+00:00"))
    except ValueError:
        # Re-anchoring heals the schedule, but corrupted state must be VISIBLE.
        _log.warning(
            "schedule_fire_time_corrupted",
            schedule_id=record.schedule_id,
            next_fire_at=record.next_fire_at,
        )
        next_at = now
    next_at += interval
    while next_at <= now:
        next_at += interval
    return next_at.isoformat()


async def run_tick(*, store: ScheduleStore, launch: LaunchFn) -> TickResult:
    now_iso = datetime.now(UTC).isoformat()
    schedules, corrupted = await store.claim_due(now_iso=now_iso, advance=advance_fire_time)
    launched: list[str] = []
    failures = 0
    bookkeeping_failures = 0
    for schedule in schedules:
        try:
            run_id = await launch(schedule)
        except Exception:
            failures += 1
            _log.error(
                "scheduled_run_launch_failed",
                schedule_id=schedule.schedule_id,
                target_url=schedule.target_url,
                exc_info=True,
            )
            continue
        launched.append(run_id)
        try:
            await store.mark_fired(schedule.schedule_id, run_id=run_id, fired_at=now_iso)
        except Exception:
            # The run IS launched and registered; the schedule bookkeeping
            # lagging is logged AND counted, never fatal.
            bookkeeping_failures += 1
            _log.error(
                "schedule_mark_fired_failed", schedule_id=schedule.schedule_id, exc_info=True
            )
    return TickResult(
        claimed=len(schedules),
        launched=launched,
        launch_failures=failures,
        corrupted_docs=corrupted,
        bookkeeping_failures=bookkeeping_failures,
    )


__all__ = ["LaunchFn", "TickResult", "advance_fire_time", "run_tick"]
