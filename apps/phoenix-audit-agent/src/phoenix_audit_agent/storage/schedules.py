"""Monitoring-schedule store (Firestore) with optimistic claim semantics.

claim_due() advances next_fire_at with a last-update-time precondition: a
concurrent claimer loses the write and skips the schedule — due schedules
fire at most once per tick window, enforced by the store, not the caller.
"""

from __future__ import annotations

from typing import Any, Protocol

import structlog

from phoenix_audit_agent.storage.firestore_client import get_firestore
from phoenix_audit_agent.storage.models import ScheduleRecord

_log = structlog.get_logger(__name__)

_COLLECTION = "schedules"


class ScheduleStore(Protocol):
    async def upsert(self, record: ScheduleRecord) -> None: ...

    async def list_schedules(self) -> list[ScheduleRecord]: ...

    async def get(self, schedule_id: str) -> ScheduleRecord | None: ...

    async def claim_due(self, *, now_iso: str, advance: Any) -> list[ScheduleRecord]:
        """advance: Callable[[ScheduleRecord], str] -> the new next_fire_at."""
        ...

    async def mark_fired(self, schedule_id: str, *, run_id: str, fired_at: str) -> None: ...


class FirestoreScheduleStore:
    def __init__(self, db: Any | None = None) -> None:
        self._db = db

    @property
    def db(self) -> Any:
        if self._db is None:
            self._db = get_firestore()
        return self._db

    async def upsert(self, record: ScheduleRecord) -> None:
        await self.db.collection(_COLLECTION).document(record.schedule_id).set(record.model_dump())

    async def list_schedules(self) -> list[ScheduleRecord]:
        rows: list[ScheduleRecord] = []
        async for doc in self.db.collection(_COLLECTION).stream():
            rows.append(ScheduleRecord.model_validate(doc.to_dict()))
        rows.sort(key=lambda s: s.created_at)
        return rows

    async def get(self, schedule_id: str) -> ScheduleRecord | None:
        doc = await self.db.collection(_COLLECTION).document(schedule_id).get()
        if not doc.exists:
            return None
        return ScheduleRecord.model_validate(doc.to_dict())

    async def claim_due(self, *, now_iso: str, advance: Any) -> list[ScheduleRecord]:
        """Atomically claim every enabled schedule with next_fire_at <= now.

        The advance callback maps the claimed record -> its new
        next_fire_at. The update carries a last-update-time precondition;
        losing a concurrent race skips the schedule (the winner fired it).
        """
        claimed: list[ScheduleRecord] = []
        async for snapshot in self.db.collection(_COLLECTION).stream():
            record = ScheduleRecord.model_validate(snapshot.to_dict())
            if not record.enabled or record.next_fire_at > now_iso:
                continue
            new_fire_at = advance(record)
            try:
                from google.api_core.exceptions import FailedPrecondition

                await (
                    self.db.collection(_COLLECTION)
                    .document(record.schedule_id)
                    .update(
                        {"next_fire_at": new_fire_at},
                        option=self.db.write_option(last_update_time=snapshot.update_time),
                    )
                )
            except FailedPrecondition:
                _log.info("schedule_claim_lost_race", schedule_id=record.schedule_id)
                continue
            claimed.append(record)
        return claimed

    async def mark_fired(self, schedule_id: str, *, run_id: str, fired_at: str) -> None:
        await (
            self.db.collection(_COLLECTION)
            .document(schedule_id)
            .update({"last_fired_at": fired_at, "last_run_id": run_id})
        )


_STORE: ScheduleStore | None = None


def set_schedule_store(store: ScheduleStore | None) -> None:
    """Test/bootstrap seam. None resets to the lazy Firestore default."""
    global _STORE  # noqa: PLW0603 — module singleton is the documented seam
    _STORE = store


def get_schedule_store() -> ScheduleStore:
    global _STORE  # noqa: PLW0603 — module singleton is the documented seam
    if _STORE is None:
        _STORE = FirestoreScheduleStore()
    return _STORE


__all__ = [
    "FirestoreScheduleStore",
    "ScheduleStore",
    "get_schedule_store",
    "set_schedule_store",
]
