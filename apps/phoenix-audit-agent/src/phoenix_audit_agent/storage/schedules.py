"""Monitoring-schedule store (Firestore) with optimistic claim semantics.

claim_due() advances next_fire_at with a last-update-time precondition: a
concurrent claimer loses the write and skips the schedule — due schedules
fire at most once per tick window, enforced by the store, not the caller.
"""

from __future__ import annotations

from typing import Any, Protocol

import structlog
from google.api_core.exceptions import FailedPrecondition
from pydantic import ValidationError

# Both 'Z' and '+00:00' forms exist in stored documents (pre-canonicalization
# writers). A lexicographic compare reads a DUE Z-form timestamp as future
# ('Z' > '+'), silently skipping it every tick — always compare via parse.
from phoenix_audit_agent._time import parse_iso as _parse_iso
from phoenix_audit_agent.storage.firestore_client import get_firestore
from phoenix_audit_agent.storage.models import ScheduleRecord

_log = structlog.get_logger(__name__)

_COLLECTION = "schedules"


class ScheduleStore(Protocol):
    async def upsert(self, record: ScheduleRecord) -> None: ...

    async def list_schedules(self) -> list[ScheduleRecord]: ...

    async def get(self, schedule_id: str) -> ScheduleRecord | None: ...

    async def claim_due(self, *, now_iso: str, advance: Any) -> tuple[list[ScheduleRecord], int]:
        """advance: Callable[[ScheduleRecord], str] -> the new next_fire_at.

        Returns (claimed, corrupted_doc_count) — corruption is DISCLOSED to
        the tick response, never a stream-aborting crash.
        """
        ...

    async def mark_fired(self, schedule_id: str, *, run_id: str, fired_at: str) -> None: ...

    async def patch_fields(self, schedule_id: str, fields: dict[str, Any]) -> None: ...


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
            try:
                rows.append(ScheduleRecord.model_validate(doc.to_dict()))
            except ValidationError:
                # One corrupted doc must not 500 the whole monitoring page.
                _log.error("schedule_doc_corrupted", doc_id=doc.id, exc_info=True)
        rows.sort(key=lambda s: s.created_at)
        return rows

    async def get(self, schedule_id: str) -> ScheduleRecord | None:
        doc = await self.db.collection(_COLLECTION).document(schedule_id).get()
        if not doc.exists:
            return None
        return ScheduleRecord.model_validate(doc.to_dict())

    async def claim_due(self, *, now_iso: str, advance: Any) -> tuple[list[ScheduleRecord], int]:
        """Atomically claim every enabled schedule with next_fire_at <= now.

        The advance callback maps the claimed record -> its new
        next_fire_at. The update carries a last-update-time precondition;
        losing a concurrent race skips the schedule (the winner fired it).
        Corrupted documents are counted + logged, never stream-aborting —
        one bad doc must not halt the entire monitoring fleet forever.
        """
        claimed: list[ScheduleRecord] = []
        corrupted = 0
        now_dt = _parse_iso(now_iso)
        async for snapshot in self.db.collection(_COLLECTION).stream():
            try:
                record = ScheduleRecord.model_validate(snapshot.to_dict())
                due = record.enabled and _parse_iso(record.next_fire_at) <= now_dt
            except (ValidationError, ValueError):
                corrupted += 1
                _log.error("schedule_doc_corrupted", doc_id=snapshot.id, exc_info=True)
                continue
            if not due:
                continue
            new_fire_at = advance(record)
            try:
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
            except Exception:
                # Contained per-document: a transient error on ONE update must
                # not discard the claims already made — those schedules' fire
                # times are advanced and their audits would silently vanish
                # for a full cadence with no trace.
                _log.error("schedule_claim_failed", schedule_id=record.schedule_id, exc_info=True)
                continue
            claimed.append(record)
        return claimed, corrupted

    async def mark_fired(self, schedule_id: str, *, run_id: str, fired_at: str) -> None:
        await (
            self.db.collection(_COLLECTION)
            .document(schedule_id)
            .update({"last_fired_at": fired_at, "last_run_id": run_id})
        )

    async def patch_fields(self, schedule_id: str, fields: dict[str, Any]) -> None:
        # update() writes ONLY the patched keys — a read-modify-write upsert
        # here raced the tick's claim and could resurrect a stale next_fire_at
        # (= duplicate signed audit on the next tick).
        await self.db.collection(_COLLECTION).document(schedule_id).update(fields)


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
