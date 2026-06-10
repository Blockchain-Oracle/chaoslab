"""FirestoreRunStore/AgentStore against REAL Firestore (or the emulator).

Marked @pytest.mark.online — CI skips by default. Runs against the project's
free-tier Firestore database via ADC (or FIRESTORE_EMULATOR_HOST when set);
documents are namespaced with a test prefix and deleted afterwards.
"""

from __future__ import annotations

import uuid

import pytest

from phoenix_audit_agent.storage.agents import FirestoreAgentStore
from phoenix_audit_agent.storage.models import AgentRecord, RunRecord
from phoenix_audit_agent.storage.runs import FirestoreRunStore

pytestmark = [pytest.mark.online, pytest.mark.asyncio]

_SUFFIX = uuid.uuid4().hex[:8]


async def test_run_store_roundtrip_and_finalize_merge() -> None:
    store = FirestoreRunStore()
    run_id = f"run_test{_SUFFIX}"
    try:
        await store.create(
            RunRecord(
                run_id=run_id,
                target_url="https://target.example",
                created_at="2026-06-10T01:00:00Z",
            )
        )
        await store.finalize(
            run_id,
            {"phase": "succeeded", "passed": 6, "failed": 0, "report_available": True},
        )

        record = await store.get(run_id)
        assert record is not None
        assert record.phase == "succeeded"
        assert record.passed == 6
        assert record.target_url == "https://target.example"  # merge kept create fields

        rows = await store.list_runs(limit=200)
        assert any(r.run_id == run_id for r in rows)
    finally:
        await store.db.collection("runs").document(run_id).delete()


async def test_agent_store_roundtrip() -> None:
    store = FirestoreAgentStore()
    agent_id = f"agt_test{_SUFFIX}"
    try:
        await store.register(
            AgentRecord(
                agent_id=agent_id,
                name="Integration Test Agent",
                url="https://it.example",
                framework="http-blackbox",
                tier=3,
                registered_at="2026-06-10T01:00:00Z",
            )
        )
        got = await store.get(agent_id)
        assert got is not None
        assert got.tier == 3
        assert any(a.agent_id == agent_id for a in await store.list_agents())
    finally:
        await store.db.collection("agents").document(agent_id).delete()
