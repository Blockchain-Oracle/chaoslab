"""Run-record store: Firestore implementation + contained write helpers.

Persistence failure must never kill an audit — the signed artifact set is the
durable evidence; this collection is the registry index. Both write helpers
contain ALL exceptions, log at CRITICAL, and return False so the caller can
mark the run (`persistence_failed`) instead of dying.
"""

from __future__ import annotations

import asyncio
from typing import Any, Protocol

import structlog

from phoenix_audit_agent.storage.firestore_client import get_firestore
from phoenix_audit_agent.storage.models import RunRecord

_log = structlog.get_logger(__name__)

_COLLECTION = "runs"

# Outage bound for contained writes: Firestore's default retry deadline is
# ~60s; POST /run must never hang that long on the registry index.
_WRITE_TIMEOUT_SEC = 5.0


def assert_known_run_fields(fields: dict[str, Any]) -> None:
    """finalize() writes raw dicts and RunRecord reads with extra='ignore' — a
    typo'd key would write cleanly and silently read back as the field default.
    Raise instead; the containment above converts the raise into a DISCLOSED
    persistence_failed (drift-guard discipline)."""
    unknown = set(fields) - set(RunRecord.model_fields)
    if unknown:
        msg = f"unknown RunRecord fields in finalize payload: {sorted(unknown)}"
        raise ValueError(msg)


class RunStore(Protocol):
    async def create(self, record: RunRecord) -> None: ...

    async def finalize(self, run_id: str, fields: dict[str, Any]) -> None: ...

    async def list_runs(
        self, *, agent_id: str | None = None, source: str | None = None, limit: int = 50
    ) -> list[RunRecord]: ...

    async def get(self, run_id: str) -> RunRecord | None: ...


class FirestoreRunStore:
    def __init__(self, db: Any | None = None) -> None:
        self._db = db

    @property
    def db(self) -> Any:
        if self._db is None:
            self._db = get_firestore()
        return self._db

    async def create(self, record: RunRecord) -> None:
        await self.db.collection(_COLLECTION).document(record.run_id).set(record.model_dump())

    async def finalize(self, run_id: str, fields: dict[str, Any]) -> None:
        # merge=True heals a failed create: the completion write carries enough
        # keys (run_id/target_url/created_at) to stand alone as a valid record.
        assert_known_run_fields(fields)
        await self.db.collection(_COLLECTION).document(run_id).set(fields, merge=True)

    async def list_runs(
        self, *, agent_id: str | None = None, source: str | None = None, limit: int = 50
    ) -> list[RunRecord]:
        # order_by only (no where): a where+order_by combo needs a composite
        # index per filter field. Registry volume is small — filter in memory
        # and keep Firestore index admin at zero.
        collection = self.db.collection(_COLLECTION)
        query = collection.order_by("created_at", direction="DESCENDING").limit(200)
        rows: list[RunRecord] = []
        async for doc in query.stream():
            rows.append(RunRecord.model_validate(doc.to_dict()))
        if agent_id is not None:
            rows = [r for r in rows if r.agent_id == agent_id]
        if source is not None:
            rows = [r for r in rows if r.source == source]
        return rows[:limit]

    async def get(self, run_id: str) -> RunRecord | None:
        doc = await self.db.collection(_COLLECTION).document(run_id).get()
        if not doc.exists:
            return None
        return RunRecord.model_validate(doc.to_dict())


_STORE: RunStore | None = None


def set_run_store(store: RunStore | None) -> None:
    """Test/bootstrap seam. None resets to the lazy Firestore default."""
    global _STORE  # noqa: PLW0603 — module singleton is the documented seam
    _STORE = store


def get_run_store() -> RunStore:
    global _STORE  # noqa: PLW0603 — module singleton is the documented seam
    if _STORE is None:
        _STORE = FirestoreRunStore()
    return _STORE


async def create_run_record(record: RunRecord) -> bool:
    """Contained create — CRITICAL log on failure, never raises."""
    try:
        await asyncio.wait_for(get_run_store().create(record), timeout=_WRITE_TIMEOUT_SEC)
    except Exception:
        _log.critical(
            "run_record_create_failed — registry index will heal at finalize",
            run_id=record.run_id,
            exc_info=True,
        )
        return False
    return True


async def persist_run_completion(run_id: str, fields: dict[str, Any]) -> bool:
    """Contained finalize — CRITICAL log on failure, never raises."""
    try:
        await asyncio.wait_for(get_run_store().finalize(run_id, fields), timeout=_WRITE_TIMEOUT_SEC)
    except Exception:
        _log.critical(
            "run_record_finalize_failed — run is NOT in the registry index; "
            "the signed artifact set in GCS remains the durable evidence",
            run_id=run_id,
            exc_info=True,
        )
        return False
    return True


__all__ = [
    "FirestoreRunStore",
    "RunStore",
    "assert_known_run_fields",
    "create_run_record",
    "get_run_store",
    "persist_run_completion",
    "set_run_store",
]
