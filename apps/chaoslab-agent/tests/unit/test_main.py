"""FastAPI endpoint tests for chaoslab-agent S4.1 scaffold."""

from __future__ import annotations

import os
import re
from collections.abc import AsyncIterator, Iterator

import httpx
import pytest

from chaoslab_agent.config import JUDGE_LLM_LOCKED, get_settings


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch, tmp_path) -> Iterator[None]:
    """Minimal env required for Settings() to construct cleanly across tests."""
    for key in list(os.environ):
        if key.startswith(("PHOENIX_", "GEMINI_", "JUDGE_", "TARGET_", "GITLAB_", "GCS_")):
            monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini")
    monkeypatch.chdir(tmp_path)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def app():
    """Import-deferred so the env fixture runs first; otherwise Settings() loads stale env."""
    # Import inside the fixture to ensure env-isolation runs first.
    from chaoslab_agent.main import _RUN_REGISTRY
    from chaoslab_agent.main import app as fastapi_app

    _RUN_REGISTRY.clear()
    return fastapi_app


@pytest.fixture
async def client(app) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def test_health_returns_ok_with_version_and_judge(client: httpx.AsyncClient) -> None:
    r = await client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["judge_llm"] == JUDGE_LLM_LOCKED
    assert body["phoenix_provider"] == "phoenix-audit"
    assert "version" in body


async def test_post_run_returns_201_with_run_id_format(client: httpx.AsyncClient) -> None:
    r = await client.post(
        "/run",
        json={"target_url": "http://localhost:8001"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert re.fullmatch(r"^run_[a-z0-9]{12}$", body["run_id"]), body["run_id"]
    assert body["run_id"] in body["sse_url"]
    assert body["created_at"].endswith("Z")


async def test_post_run_missing_target_url_returns_422(client: httpx.AsyncClient) -> None:
    r = await client.post("/run", json={})
    assert r.status_code == 422


async def test_post_run_invalid_repetitions_returns_422(client: httpx.AsyncClient) -> None:
    r = await client.post(
        "/run",
        json={"target_url": "http://localhost:8001", "repetitions": 999},
    )
    assert r.status_code == 422  # >100 fails the ge/le bounds


async def test_get_stream_unknown_run_id_returns_404(client: httpx.AsyncClient) -> None:
    r = await client.get("/stream?runId=run_doesnotexist")
    assert r.status_code == 404


async def test_get_stream_known_run_id_emits_hello_event(client: httpx.AsyncClient) -> None:
    # Create a run first.
    run_resp = await client.post("/run", json={"target_url": "http://localhost:8001"})
    run_id = run_resp.json()["run_id"]
    # Hit the SSE endpoint with a short timeout so we drain the hello frame.
    async with client.stream("GET", f"/stream?runId={run_id}") as resp:
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")
        chunks: list[str] = []
        async for chunk in resp.aiter_text():
            chunks.append(chunk)
            if "hello" in chunk:
                break
    joined = "".join(chunks)
    assert "hello" in joined
    assert run_id in joined


async def test_get_agents_known_returns_spec(client: httpx.AsyncClient) -> None:
    r = await client.get("/agents/demo-target")
    assert r.status_code == 200
    body = r.json()
    assert body["agent_id"] == "demo-target"
    assert body["framework"] == "adk-a2a"


async def test_get_agents_unknown_returns_404(client: httpx.AsyncClient) -> None:
    r = await client.get("/agents/no-such-agent")
    assert r.status_code == 404
