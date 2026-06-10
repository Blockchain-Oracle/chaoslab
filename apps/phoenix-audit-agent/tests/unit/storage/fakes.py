"""In-memory store fakes honoring the FirestoreRunStore/AgentStore contract.

Used by unit tests via the storage seam (set_run_store/set_agent_store) —
the live audit hot path never sees these; Firestore is the only prod impl.
"""

from __future__ import annotations

from typing import Any

from phoenix_audit_agent.storage.agents import DEMO_TARGET_SEED
from phoenix_audit_agent.storage.models import AgentRecord, RunCompletion, RunRecord, ScheduleRecord


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
    ) -> list[RunRecord]:
        # NOTE: Firestore filters within the newest 200 docs only (index-free
        # query); this fake filters across ALL docs. Divergence is irrelevant
        # below 200 runs but documented for honesty.
        rows = [RunRecord.model_validate(d) for d in self._docs.values()]
        if agent_id is not None:
            rows = [r for r in rows if r.agent_id == agent_id]
        if source is not None:
            rows = [r for r in rows if r.source == source]
        rows.sort(key=lambda r: r.created_at, reverse=True)
        return rows[:limit]

    async def get(self, run_id: str) -> RunRecord | None:
        doc = self._docs.get(run_id)
        return RunRecord.model_validate(doc) if doc else None


class InMemoryAgentStore:
    def __init__(self) -> None:
        self._docs: dict[str, dict[str, Any]] = {
            DEMO_TARGET_SEED.agent_id: DEMO_TARGET_SEED.model_dump()
        }

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

    async def claim_due(self, *, now_iso: str, advance: Any) -> list[ScheduleRecord]:
        claimed: list[ScheduleRecord] = []
        for doc in list(self._docs.values()):
            record = ScheduleRecord.model_validate(doc)
            if not record.enabled or record.next_fire_at > now_iso:
                continue
            # claim-before-launch: advance the fire time FIRST, like prod.
            self._docs[record.schedule_id]["next_fire_at"] = advance(record)
            claimed.append(record)
        return claimed

    async def mark_fired(self, schedule_id: str, *, run_id: str, fired_at: str) -> None:
        self._docs[schedule_id]["last_fired_at"] = fired_at
        self._docs[schedule_id]["last_run_id"] = run_id

    async def patch_fields(self, schedule_id: str, fields: dict[str, Any]) -> None:
        self._docs[schedule_id].update(fields)
