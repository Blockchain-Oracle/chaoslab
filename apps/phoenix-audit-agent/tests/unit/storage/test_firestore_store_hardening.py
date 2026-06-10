"""Firestore store hardening — review-sweep findings (full-codebase review).

Three failure shapes a regulator-facing registry must survive:
1. timestamp-format drift: `Z`-suffixed vs `+00:00` ISO strings compared
   LEXICOGRAPHICALLY made a due schedule read as future, forever, silently;
2. one corrupted document aborting a whole stream (every subsequent tick
   500s; the runs registry dies for everyone over one bad doc);
3. silent truncation: /runs filters in memory over the newest 200 docs —
   once the cap is hit, an agent's older history vanishes undisclosed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from phoenix_audit_agent.storage.models import RunRecord, ScheduleRecord
from phoenix_audit_agent.storage.runs import FirestoreRunStore
from phoenix_audit_agent.storage.schedules import FirestoreScheduleStore


def _schedule_doc(schedule_id: str, *, next_fire_at: str, enabled: bool = True) -> dict[str, Any]:
    return ScheduleRecord(
        schedule_id=schedule_id,
        target_url="https://target.example",
        cadence="daily",
        enabled=enabled,
        next_fire_at=next_fire_at,
        created_at="2026-06-09T00:00:00+00:00",
    ).model_dump()


def _run_doc(run_id: str, *, created_at: str) -> dict[str, Any]:
    return RunRecord(
        run_id=run_id,
        target_url="https://target.example",
        created_at=created_at,
        phase="succeeded",
    ).model_dump()


@dataclass
class _FakeSnapshot:
    id: str
    data: dict[str, Any]
    update_time: object = field(default_factory=object)

    @property
    def exists(self) -> bool:
        return True

    def to_dict(self) -> dict[str, Any]:
        return self.data


class _FakeDocRef:
    def __init__(self, db: _FakeDb, doc_id: str) -> None:
        self._db = db
        self._id = doc_id

    async def update(self, fields: dict[str, Any], option: Any = None) -> None:
        self._db.updates.append((self._id, fields, option))
        self._db.docs[self._id] = {**self._db.docs.get(self._id, {}), **fields}


class _FakeQuery:
    def __init__(self, db: _FakeDb, limit_n: int | None = None) -> None:
        self._db = db
        self._limit = limit_n

    def order_by(self, *a: Any, **k: Any) -> _FakeQuery:
        return self

    def limit(self, n: int) -> _FakeQuery:
        return _FakeQuery(self._db, n)

    async def stream(self) -> Any:
        rows = list(self._db.docs.items())
        if self._limit is not None:
            rows = rows[: self._limit]
        for doc_id, data in rows:
            yield _FakeSnapshot(doc_id, data)


class _FakeCollection(_FakeQuery):
    def document(self, doc_id: str) -> _FakeDocRef:
        return _FakeDocRef(self._db, doc_id)


class _FakeDb:
    def __init__(self, docs: dict[str, dict[str, Any]]) -> None:
        self.docs = docs
        self.updates: list[tuple[str, dict[str, Any], Any]] = []

    def collection(self, name: str) -> _FakeCollection:
        return _FakeCollection(self)

    def write_option(self, **kwargs: Any) -> Any:
        return kwargs


NOW_PLUS = "2026-06-10T12:00:00+00:00"


class TestClaimDueTimestamps:
    async def test_z_suffixed_due_schedule_is_claimed(self) -> None:
        """'Z' (0x5A) > '+' (0x2B) lexicographically — a string compare reads
        a DUE Z-form timestamp as future, silently skipping it every tick."""
        db = _FakeDb({"sch_z": _schedule_doc("sch_z", next_fire_at="2026-06-10T11:00:00Z")})
        store = FirestoreScheduleStore(db)
        claimed, corrupted = await store.claim_due(
            now_iso=NOW_PLUS, advance=lambda r: "2026-06-11T11:00:00+00:00"
        )
        assert [s.schedule_id for s in claimed] == ["sch_z"]
        assert corrupted == 0

    async def test_future_schedule_not_claimed(self) -> None:
        db = _FakeDb({"sch_f": _schedule_doc("sch_f", next_fire_at="2026-06-10T13:00:00+00:00")})
        store = FirestoreScheduleStore(db)
        claimed, _ = await store.claim_due(now_iso=NOW_PLUS, advance=lambda r: "x")
        assert claimed == []


class TestPerDocContainment:
    async def test_corrupted_schedule_doc_does_not_abort_claim(self) -> None:
        db = _FakeDb(
            {
                "bad": {"schedule_id": "bad"},  # missing required fields
                "sch_ok": _schedule_doc("sch_ok", next_fire_at="2026-06-10T11:00:00+00:00"),
            }
        )
        store = FirestoreScheduleStore(db)
        claimed, corrupted = await store.claim_due(
            now_iso=NOW_PLUS, advance=lambda r: "2026-06-11T11:00:00+00:00"
        )
        assert [s.schedule_id for s in claimed] == ["sch_ok"]
        assert corrupted == 1

    async def test_unparseable_next_fire_at_counts_corrupted_not_crash(self) -> None:
        doc = _schedule_doc("sch_t", next_fire_at="not-a-timestamp")
        db = _FakeDb({"sch_t": doc})
        store = FirestoreScheduleStore(db)
        claimed, corrupted = await store.claim_due(now_iso=NOW_PLUS, advance=lambda r: "x")
        assert claimed == []
        assert corrupted == 1

    async def test_corrupted_schedule_doc_skipped_in_list(self) -> None:
        db = _FakeDb(
            {
                "bad": {"schedule_id": "bad"},
                "sch_ok": _schedule_doc("sch_ok", next_fire_at=NOW_PLUS),
            }
        )
        rows = await FirestoreScheduleStore(db).list_schedules()
        assert [s.schedule_id for s in rows] == ["sch_ok"]

    async def test_corrupted_run_doc_skipped_in_list(self) -> None:
        db = _FakeDb(
            {
                "bad": {"run_id": "bad"},
                "run_ok": _run_doc("run_ok", created_at="2026-06-10T00:00:00+00:00"),
            }
        )
        rows, truncated = await FirestoreRunStore(db).list_runs()
        assert [r.run_id for r in rows] == ["run_ok"]
        assert truncated is False


class TestRunsTruncationDisclosure:
    async def test_filtered_list_discloses_truncation_at_query_cap(self) -> None:
        docs = {
            f"run_{i:03d}": _run_doc(f"run_{i:03d}", created_at=f"2026-06-09T{i % 24:02d}:00:00Z")
            for i in range(200)
        }
        db = _FakeDb(docs)
        rows, truncated = await FirestoreRunStore(db).list_runs(agent_id="nope")
        assert rows == []
        assert truncated is True, (
            "the inner query hit its 200-doc cap with a filter applied — older "
            "matching runs may exist; the registry must say so"
        )

    async def test_small_collection_not_truncated(self) -> None:
        db = _FakeDb({"r1": _run_doc("r1", created_at="2026-06-10T00:00:00Z")})
        rows, truncated = await FirestoreRunStore(db).list_runs()
        assert len(rows) == 1
        assert truncated is False
