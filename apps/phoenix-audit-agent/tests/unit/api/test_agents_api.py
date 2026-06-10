"""POST/GET /agents — the target-agent registry API (story-9.1)."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Iterator

import httpx
import pytest

from phoenix_audit_agent.config import get_settings
from phoenix_audit_agent.storage import agents as agent_storage
from phoenix_audit_agent.storage import runs as run_storage

from ..storage.fakes import InMemoryAgentStore, InMemoryRunStore


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    for key in list(os.environ):
        if key.startswith(("PHOENIX_", "GEMINI_", "JUDGE_", "TARGET_", "GITLAB_", "GCS_")):
            monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini")
    get_settings.cache_clear()
    run_storage.set_run_store(InMemoryRunStore())
    agent_storage.set_agent_store(InMemoryAgentStore())
    yield
    run_storage.set_run_store(None)
    agent_storage.set_agent_store(None)
    get_settings.cache_clear()


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    from phoenix_audit_agent.main import app

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def test_list_agents_includes_demo_seed(client: httpx.AsyncClient) -> None:
    r = await client.get("/agents")
    assert r.status_code == 200
    ids = [a["agent_id"] for a in r.json()["agents"]]
    assert "demo-target" in ids


async def test_register_then_get(client: httpx.AsyncClient) -> None:
    r = await client.post(
        "/agents",
        json={
            "agent_id": "agt_prior",
            "name": "Prior-Authorization Agent",
            "url": "https://agents.example/prior-auth",
            "framework": "adk-a2a",
            "tier": 1,
        },
    )
    assert r.status_code == 201
    assert r.json()["agent_id"] == "agt_prior"

    got = await client.get("/agents/agt_prior")
    assert got.status_code == 200
    assert got.json()["name"] == "Prior-Authorization Agent"
    assert got.json()["registered_at"]  # server-stamped


async def test_register_invalid_framework_422(client: httpx.AsyncClient) -> None:
    r = await client.post(
        "/agents",
        json={
            "agent_id": "agt_bad",
            "name": "Bad",
            "url": "https://x.example",
            "framework": "not-a-framework",
            "tier": 1,
        },
    )
    assert r.status_code == 422


async def test_get_unknown_agent_404(client: httpx.AsyncClient) -> None:
    r = await client.get("/agents/agt_missing")
    assert r.status_code == 404


async def test_register_demo_target_is_rejected(client: httpx.AsyncClient) -> None:
    """The seed shadows reads of this id — a 201 would write an unreadable record."""
    r = await client.post(
        "/agents",
        json={
            "agent_id": "demo-target",
            "name": "Imposter",
            "url": "https://x.example",
            "framework": "adk-a2a",
            "tier": 1,
        },
    )
    assert r.status_code == 409
