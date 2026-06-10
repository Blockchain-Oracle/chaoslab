"""Target-agent registry store (Firestore) + the demo-target seed."""

from __future__ import annotations

from typing import Any, Protocol

from phoenix_audit_agent.config import get_settings
from phoenix_audit_agent.storage.firestore_client import get_firestore
from phoenix_audit_agent.storage.models import AgentRecord

_COLLECTION = "agents"

DEMO_TARGET_ID = "demo-target"


def demo_target_seed() -> AgentRecord:
    """Built per-call from settings — the seed URL must point at the DEPLOYED
    target-agent in deployed envs; a hardcoded localhost:8001 fired real
    (failing) runs from staging with one click (story-9.10)."""
    return AgentRecord(
        agent_id=DEMO_TARGET_ID,
        name="Demo Support Agent",
        url=get_settings().DEMO_TARGET_URL,
        framework="adk-a2a",
        tier=1,
        registered_at="2026-06-08T00:00:00Z",
    )


class AgentStore(Protocol):
    async def register(self, record: AgentRecord) -> None: ...

    async def list_agents(self) -> list[AgentRecord]: ...

    async def get(self, agent_id: str) -> AgentRecord | None: ...


class FirestoreAgentStore:
    def __init__(self, db: Any | None = None) -> None:
        self._db = db

    @property
    def db(self) -> Any:
        if self._db is None:
            self._db = get_firestore()
        return self._db

    async def register(self, record: AgentRecord) -> None:
        await self.db.collection(_COLLECTION).document(record.agent_id).set(record.model_dump())

    async def list_agents(self) -> list[AgentRecord]:
        rows: list[AgentRecord] = []
        async for doc in self.db.collection(_COLLECTION).stream():
            rows.append(AgentRecord.model_validate(doc.to_dict()))
        if not any(a.agent_id == DEMO_TARGET_ID for a in rows):
            rows.append(demo_target_seed())
        rows.sort(key=lambda a: a.registered_at)
        return rows

    async def get(self, agent_id: str) -> AgentRecord | None:
        if agent_id == DEMO_TARGET_ID:
            return demo_target_seed()
        doc = await self.db.collection(_COLLECTION).document(agent_id).get()
        if not doc.exists:
            return None
        return AgentRecord.model_validate(doc.to_dict())


_STORE: AgentStore | None = None


def set_agent_store(store: AgentStore | None) -> None:
    """Test/bootstrap seam. None resets to the lazy Firestore default."""
    global _STORE  # noqa: PLW0603 — module singleton is the documented seam
    _STORE = store


def get_agent_store() -> AgentStore:
    global _STORE  # noqa: PLW0603 — module singleton is the documented seam
    if _STORE is None:
        _STORE = FirestoreAgentStore()
    return _STORE


__all__ = [
    "DEMO_TARGET_ID",
    "AgentStore",
    "FirestoreAgentStore",
    "demo_target_seed",
    "get_agent_store",
    "set_agent_store",
]
