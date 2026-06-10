"""Scheduler tick — claim-before-launch, containment, cadence math."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from phoenix_audit_agent.scheduler.tick import advance_fire_time, run_tick
from phoenix_audit_agent.storage.models import ScheduleRecord

from ..storage.fakes import InMemoryScheduleStore


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _schedule(schedule_id: str, *, next_fire_at: str, enabled: bool = True) -> ScheduleRecord:
    return ScheduleRecord(
        schedule_id=schedule_id,
        target_url="https://target.example",
        cadence="daily",
        enabled=enabled,
        next_fire_at=next_fire_at,
        created_at="2026-06-09T00:00:00+00:00",
    )


@pytest.mark.asyncio
async def test_due_schedule_fires_and_advances() -> None:
    store = InMemoryScheduleStore()
    past = _iso(datetime.now(UTC) - timedelta(minutes=5))
    await store.upsert(_schedule("sch_due", next_fire_at=past))

    launched: list[str] = []

    async def launch(schedule: ScheduleRecord) -> str:
        launched.append(schedule.schedule_id)
        return "run_scheduled001"

    result = await run_tick(store=store, launch=launch)

    assert result.claimed == 1
    assert result.launched == ["run_scheduled001"]
    assert launched == ["sch_due"]
    after = await store.get("sch_due")
    assert after is not None
    assert after.next_fire_at > _iso(datetime.now(UTC))  # advanced into the future
    assert after.last_run_id == "run_scheduled001"
    assert after.last_fired_at is not None


@pytest.mark.asyncio
async def test_not_due_and_disabled_schedules_skipped() -> None:
    store = InMemoryScheduleStore()
    future = _iso(datetime.now(UTC) + timedelta(hours=2))
    past = _iso(datetime.now(UTC) - timedelta(hours=2))
    await store.upsert(_schedule("sch_future", next_fire_at=future))
    await store.upsert(_schedule("sch_disabled", next_fire_at=past, enabled=False))

    async def launch(schedule: ScheduleRecord) -> str:  # pragma: no cover
        raise AssertionError("nothing should launch")

    result = await run_tick(store=store, launch=launch)
    assert result.claimed == 0
    assert result.launched == []


@pytest.mark.asyncio
async def test_second_tick_does_not_double_fire() -> None:
    """The claim advances next_fire_at BEFORE launch — an immediate second
    tick finds nothing due."""
    store = InMemoryScheduleStore()
    past = _iso(datetime.now(UTC) - timedelta(minutes=5))
    await store.upsert(_schedule("sch_once", next_fire_at=past))

    async def launch(schedule: ScheduleRecord) -> str:
        return "run_first"

    first = await run_tick(store=store, launch=launch)
    second = await run_tick(store=store, launch=launch)
    assert first.claimed == 1
    assert second.claimed == 0


@pytest.mark.asyncio
async def test_launch_failure_contained_and_counted() -> None:
    """One broken target must not block the rest of the fleet — and the
    schedule stays CLAIMED (skip one tick, never a retry storm)."""
    store = InMemoryScheduleStore()
    past = _iso(datetime.now(UTC) - timedelta(minutes=5))
    await store.upsert(_schedule("sch_bad", next_fire_at=past))
    await store.upsert(_schedule("sch_good", next_fire_at=past))

    async def launch(schedule: ScheduleRecord) -> str:
        if schedule.schedule_id == "sch_bad":
            raise RuntimeError("target exploded")
        return "run_good"

    result = await run_tick(store=store, launch=launch)
    assert result.claimed == 2
    assert result.launched == ["run_good"]
    assert result.launch_failures == 1
    bad = await store.get("sch_bad")
    assert bad is not None
    assert bad.last_run_id is None  # never fired
    assert bad.next_fire_at > _iso(datetime.now(UTC))  # but claimed — no storm


def test_advance_anchors_to_schedule_not_tick_time() -> None:
    """+1 interval from the OLD fire time — no drift accumulation."""
    # Second precision — the canonical timestamp format truncates microseconds.
    recent = (datetime.now(UTC) - timedelta(minutes=10)).replace(microsecond=0)
    record = _schedule("sch_x", next_fire_at=_iso(recent)).model_copy(update={"cadence": "hourly"})
    advanced = datetime.fromisoformat(advance_fire_time(record))
    assert advanced == recent + timedelta(hours=1)


def test_advance_fast_forwards_after_outage_no_backlog() -> None:
    """A week-long outage on an hourly schedule produces ONE catch-up window,
    not 168 queued runs."""
    week_ago = datetime.now(UTC) - timedelta(days=7)
    record = _schedule("sch_x", next_fire_at=_iso(week_ago)).model_copy(
        update={"cadence": "hourly"}
    )
    advanced = datetime.fromisoformat(advance_fire_time(record))
    assert advanced > datetime.now(UTC)
    assert advanced <= datetime.now(UTC) + timedelta(hours=1)
