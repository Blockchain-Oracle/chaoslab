"""Store contract — exercised against the in-memory fake used by API tests.

The fake must honor the same contract as FirestoreRunStore (create/finalize/
list/get ordering + filters + the unknown-field guard) or the API tests prove
nothing. The Firestore implementation proves the load-bearing pieces (round
trip, merge-heal) under @pytest.mark.online in
tests/integration/test_firestore_stores_online.py.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from phoenix_audit_agent.config import get_settings
from phoenix_audit_agent.storage.models import AgentRecord, RunCompletion, RunRecord, RunSource

from .fakes import InMemoryAgentStore, InMemoryRunStore


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    # demo_target_seed() (constructed by InMemoryAgentStore) reads Settings,
    # which needs a Gemini/Vertex path configured — deterministic here.
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini")
    monkeypatch.delenv("DEMO_TARGET_URL", raising=False)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _run(
    run_id: str, *, created_at: str, source: RunSource = "manual", agent_id: str | None = None
) -> RunRecord:
    return RunRecord(
        run_id=run_id,
        agent_id=agent_id,
        target_url="https://target.example",
        created_at=created_at,
        source=source,
    )


@pytest.mark.asyncio
async def test_create_then_get_roundtrips() -> None:
    store = InMemoryRunStore()
    await store.create(_run("run_aaaaaaaaaaaa", created_at="2026-06-10T01:00:00Z"))

    record = await store.get("run_aaaaaaaaaaaa")
    assert record is not None
    assert record.target_url == "https://target.example"
    assert record.phase == "queued"
    assert record.org_id == "default"


@pytest.mark.asyncio
async def test_get_unknown_returns_none() -> None:
    assert await InMemoryRunStore().get("run_nope") is None


@pytest.mark.asyncio
async def test_finalize_merges_even_without_create() -> None:
    """finalize uses merge semantics — a failed create must not orphan the
    completion record (the index heals itself at run end)."""
    store = InMemoryRunStore()
    await store.finalize(
        "run_bbbbbbbbbbbb",
        RunCompletion(
            run_id="run_bbbbbbbbbbbb",
            target_url="https://target.example",
            created_at="2026-06-10T01:00:00Z",
            phase="succeeded",
            passed=5,
            failed=1,
            finished_at="2026-06-10T01:02:00Z",
        ),
    )

    record = await store.get("run_bbbbbbbbbbbb")
    assert record is not None
    assert record.phase == "succeeded"
    assert record.passed == 5


@pytest.mark.asyncio
async def test_list_newest_first_with_filters() -> None:
    store = InMemoryRunStore()
    await store.create(_run("run_111111111111", created_at="2026-06-10T01:00:00Z"))
    await store.create(
        _run("run_222222222222", created_at="2026-06-10T02:00:00Z", source="scheduled")
    )
    await store.create(
        _run("run_333333333333", created_at="2026-06-10T03:00:00Z", agent_id="agt_x")
    )

    rows, truncated = await store.list_runs()
    assert truncated is False
    assert [r.run_id for r in rows] == [
        "run_333333333333",
        "run_222222222222",
        "run_111111111111",
    ]
    by_source, _ = await store.list_runs(source="scheduled")
    assert [r.run_id for r in by_source] == ["run_222222222222"]
    by_agent, _ = await store.list_runs(agent_id="agt_x")
    assert [r.run_id for r in by_agent] == ["run_333333333333"]


@pytest.mark.asyncio
async def test_agent_store_register_list_get_and_seed() -> None:
    store = InMemoryAgentStore()
    # the demo seed is present on first read
    seeded = await store.list_agents()
    assert any(a.agent_id == "demo-target" for a in seeded)

    await store.register(
        AgentRecord(
            agent_id="agt_prior",
            name="Prior-Authorization Agent",
            url="https://agents.example/prior-auth",
            framework="adk-a2a",
            tier=1,
            registered_at="2026-06-10T01:00:00Z",
        )
    )
    assert (await store.get("agt_prior")) is not None
    assert {a.agent_id for a in await store.list_agents()} >= {"demo-target", "agt_prior"}
    assert await store.get("agt_missing") is None
