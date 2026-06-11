"""In-memory store fakes honoring the FirestoreRunStore/AgentStore contract.

Used by unit tests via the storage seam (set_run_store/set_agent_store) —
the live audit hot path never sees these; Firestore is the only prod impl.
"""

from __future__ import annotations

from typing import Any

from phoenix_audit_agent.storage.agents import demo_target_seed
from phoenix_audit_agent.storage.models import (
    AgentRecord,
    RunCompletion,
    RunRecord,
    ScheduleRecord,
    UserProfile,
)


class InMemoryRunStore:
    def __init__(self) -> None:
        self._docs: dict[str, dict[str, Any]] = {}

    async def create(self, record: RunRecord) -> None:
        self._docs[record.run_id] = record.model_dump()

    async def finalize(self, run_id: str, completion: RunCompletion) -> None:
        merged = {**self._docs.get(run_id, {}), **completion.merge_fields(), "run_id": run_id}
        self._docs[run_id] = RunRecord.model_validate(merged).model_dump()

    async def list_runs(
        self,
        *,
        agent_id: str | None = None,
        source: str | None = None,
        limit: int = 50,
        visible_to: str | None = None,
    ) -> tuple[list[RunRecord], bool]:
        # NOTE: Firestore filters within the newest 200 docs only (index-free
        # query); this fake filters across ALL docs (never truncates).
        rows = [RunRecord.model_validate(d) for d in self._docs.values()]
        if agent_id is not None:
            rows = [r for r in rows if r.agent_id == agent_id]
        if source is not None:
            rows = [r for r in rows if r.source == source]
        if visible_to is not None:
            rows = [r for r in rows if r.owner_uid in (None, visible_to)]
        rows.sort(key=lambda r: r.created_at, reverse=True)
        return rows[:limit], False

    async def get(self, run_id: str) -> RunRecord | None:
        doc = self._docs.get(run_id)
        return RunRecord.model_validate(doc) if doc else None


class InMemoryAgentStore:
    def __init__(self) -> None:
        seed = demo_target_seed()
        self._docs: dict[str, dict[str, Any]] = {seed.agent_id: seed.model_dump()}

    async def register(self, record: AgentRecord) -> None:
        self._docs[record.agent_id] = record.model_dump()

    async def list_agents(self) -> list[AgentRecord]:
        return sorted(
            (AgentRecord.model_validate(d) for d in self._docs.values()),
            key=lambda a: a.registered_at,
        )

    async def get(self, agent_id: str) -> AgentRecord | None:
        doc = self._docs.get(agent_id)
        return AgentRecord.model_validate(doc) if doc else None


class InMemoryScheduleStore:
    def __init__(self) -> None:
        self._docs: dict[str, dict[str, Any]] = {}

    async def upsert(self, record: ScheduleRecord) -> None:
        self._docs[record.schedule_id] = record.model_dump()

    async def list_schedules(self) -> list[ScheduleRecord]:
        rows = [ScheduleRecord.model_validate(d) for d in self._docs.values()]
        rows.sort(key=lambda s: s.created_at)
        return rows

    async def get(self, schedule_id: str) -> ScheduleRecord | None:
        doc = self._docs.get(schedule_id)
        return ScheduleRecord.model_validate(doc) if doc else None

    async def claim_due(self, *, now_iso: str, advance: Any) -> tuple[list[ScheduleRecord], int]:
        from datetime import datetime

        def _p(ts: str) -> datetime:
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))

        claimed: list[ScheduleRecord] = []
        for doc in list(self._docs.values()):
            record = ScheduleRecord.model_validate(doc)
            if not record.enabled or _p(record.next_fire_at) > _p(now_iso):
                continue
            # claim-before-launch: advance the fire time FIRST, like prod.
            self._docs[record.schedule_id]["next_fire_at"] = advance(record)
            claimed.append(record)
        return claimed, 0

    async def mark_fired(self, schedule_id: str, *, run_id: str, fired_at: str) -> None:
        self._docs[schedule_id]["last_fired_at"] = fired_at
        self._docs[schedule_id]["last_run_id"] = run_id

    async def patch_fields(self, schedule_id: str, fields: dict[str, Any]) -> None:
        self._docs[schedule_id].update(fields)


class InMemoryProfileStore:
    def __init__(self) -> None:
        self._docs: dict[str, dict[str, Any]] = {}

    async def get(self, uid: str) -> UserProfile | None:
        doc = self._docs.get(uid)
        return UserProfile.model_validate(doc) if doc else None

    async def merge(self, uid: str, fields: dict[str, Any]) -> None:
        # Field-level merge like Firestore set(merge=True): unknown stored
        # fields survive (the contract test_patch_preserves_unknown_stored_fields pins).
        self._docs[uid] = {**self._docs.get(uid, {}), **fields}


class FakePhoenixDatasetClient:
    """In-memory `PhoenixDatasetClient` for unit tests.

    Mints Phoenix-ish ids deterministically (`phx_ds_<n>`, `phx_v_<n>`) so
    snapshot assertions stay stable. Supports an `outage=True` switch for
    the 503-graceful-degrade contract on `/datasets/<slug>`.
    """

    def __init__(self) -> None:
        from phoenix_audit_agent.phoenix_tools.dataset_client import FlatDatasetItem

        self._FlatDatasetItem = FlatDatasetItem
        self._datasets: dict[str, list[Any]] = {}
        self._latest_version: dict[str, str] = {}
        self._next_ds = 0
        self._next_v = 0
        self.outage: bool = False

    def _mint_ds(self) -> str:
        self._next_ds += 1
        return f"phx_ds_{self._next_ds:06d}"

    def _mint_v(self) -> str:
        self._next_v += 1
        return f"phx_v_{self._next_v:06d}"

    @staticmethod
    def _normalize(row: Any) -> dict[str, Any]:
        # FlatDatasetItem.model_dump() or already a dict.
        if hasattr(row, "model_dump"):
            return row.model_dump()
        return dict(row)

    async def create(
        self,
        *,
        name: str,
        examples: Any,
        description: str | None,
        source_url: str | None,
    ) -> Any:
        from phoenix_audit_agent.phoenix_tools.dataset_client import CreatedDataset

        ds_id = self._mint_ds()
        rows = [self._normalize(r) for r in examples]
        # Validate by round-tripping through the flat model so a malformed row
        # raises at create time, mirroring the production wrapper's strictness.
        validated = [self._FlatDatasetItem.model_validate(r) for r in rows]
        self._datasets[ds_id] = validated
        v_id = self._mint_v()
        self._latest_version[ds_id] = v_id
        return CreatedDataset(
            phoenix_dataset_id=ds_id,
            version_id=v_id,
            example_count=len(validated),
        )

    async def add_examples(self, phoenix_dataset_id: str, examples: Any) -> str:
        from phoenix_audit_agent.phoenix_tools.dataset_client import (
            PhoenixDatasetNotFoundError,
        )

        if phoenix_dataset_id not in self._datasets:
            raise PhoenixDatasetNotFoundError(phoenix_dataset_id)
        rows = [self._normalize(r) for r in examples]
        validated = [self._FlatDatasetItem.model_validate(r) for r in rows]
        self._datasets[phoenix_dataset_id].extend(validated)
        v_id = self._mint_v()
        self._latest_version[phoenix_dataset_id] = v_id
        return v_id

    async def get_examples(self, phoenix_dataset_id: str) -> list[Any]:
        from phoenix_audit_agent.phoenix_tools.dataset_client import (
            PhoenixDatasetNotFoundError,
            PhoenixUnavailableError,
        )

        if self.outage:
            raise PhoenixUnavailableError("fake-outage")
        if phoenix_dataset_id not in self._datasets:
            raise PhoenixDatasetNotFoundError(phoenix_dataset_id)
        return list(self._datasets[phoenix_dataset_id])

    async def delete(self, phoenix_dataset_id: str) -> None:
        self._datasets.pop(phoenix_dataset_id, None)
        self._latest_version.pop(phoenix_dataset_id, None)
