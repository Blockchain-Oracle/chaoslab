"""FastAPI endpoint tests for chaoslab-agent."""

from __future__ import annotations

import asyncio
import json
import os
import re
from collections.abc import AsyncIterator, Iterator

import httpx
import pytest

from chaoslab_agent.config import JUDGE_LLM_LOCKED, get_settings


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch, tmp_path) -> Iterator[None]:
    """Strip inherited PHOENIX_*/GEMINI_*/etc. env so Settings() defaults are deterministic."""
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


@pytest.mark.parametrize(
    ("reps", "expected_status"),
    [(0, 422), (1, 201), (100, 201), (101, 422)],
)
async def test_repetitions_boundaries(
    client: httpx.AsyncClient, reps: int, expected_status: int
) -> None:
    """ge=1, le=100 boundaries — all four corners covered to catch off-by-one drift."""
    r = await client.post(
        "/run",
        json={"target_url": "http://localhost:8001", "repetitions": reps},
    )
    assert r.status_code == expected_status, f"reps={reps}: {r.text}"


async def test_post_run_missing_target_url_envelope_names_field(
    client: httpx.AsyncClient,
) -> None:
    """422 envelope must name target_url so frontend can surface field-specific errors."""
    r = await client.post("/run", json={})
    assert r.status_code == 422
    assert any("target_url" in str(e["loc"]) for e in r.json()["detail"])


async def test_post_run_persists_run_id_to_registry(client: httpx.AsyncClient) -> None:
    """The POST→/stream round-trip depends on _RUN_REGISTRY persistence — verify directly."""
    from chaoslab_agent.main import _RUN_REGISTRY

    r = await client.post(
        "/run",
        json={"target_url": "http://target.example:9000", "repetitions": 5},
    )
    run_id = r.json()["run_id"]
    assert run_id in _RUN_REGISTRY
    state = _RUN_REGISTRY[run_id]
    assert state.request.target_url == "http://target.example:9000"
    assert state.request.repetitions == 5


async def test_get_stream_unknown_run_id_returns_404(client: httpx.AsyncClient) -> None:
    r = await client.get("/stream?runId=run_doesnotexist")
    assert r.status_code == 404


async def test_get_stream_known_run_id_emits_hello_event(client: httpx.AsyncClient) -> None:
    run_resp = await client.post("/run", json={"target_url": "http://localhost:8001"})
    run_id = run_resp.json()["run_id"]
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


async def test_stream_data_frames_are_valid_json(client: httpx.AsyncClient) -> None:
    """SSE `data:` payloads must be json.dumps()-emitted — bare f-strings break on quotes."""
    run_resp = await client.post("/run", json={"target_url": "http://localhost:8001"})
    run_id = run_resp.json()["run_id"]
    chunks: list[str] = []
    async with client.stream("GET", f"/stream?runId={run_id}") as resp:
        async for chunk in resp.aiter_text():
            chunks.append(chunk)
    joined = "".join(chunks)
    data_lines = [
        line.removeprefix("data: ").strip()
        for line in joined.splitlines()
        if line.startswith("data:")
    ]
    assert data_lines, f"no SSE data lines parsed from:\n{joined}"
    for line in data_lines:
        parsed = json.loads(line)  # raises on bare-fstring drift
        assert parsed["run_id"] == run_id


async def test_stream_emits_heartbeats_after_hello(client: httpx.AsyncClient) -> None:
    """3 heartbeats follow the hello frame — protects the contract S4.2 will overwrite."""
    run_resp = await client.post("/run", json={"target_url": "http://localhost:8001"})
    run_id = run_resp.json()["run_id"]
    chunks: list[str] = []
    async with client.stream("GET", f"/stream?runId={run_id}") as resp:
        async for chunk in resp.aiter_text():
            chunks.append(chunk)
    joined = "".join(chunks)
    assert joined.count("event: heartbeat") >= 3, joined


async def test_get_agents_known_returns_spec(client: httpx.AsyncClient) -> None:
    r = await client.get("/agents/demo-target")
    assert r.status_code == 200
    body = r.json()
    assert body["agent_id"] == "demo-target"
    assert body["framework"] == "adk-a2a"


async def test_get_agents_unknown_returns_404(client: httpx.AsyncClient) -> None:
    r = await client.get("/agents/no-such-agent")
    assert r.status_code == 404


async def test_concurrent_runs_generate_distinct_ids(client: httpx.AsyncClient) -> None:
    """48-bit run_id collision is improbable but registry overwrite must not be silent."""
    payload = {"target_url": "http://localhost:8001"}
    responses = await asyncio.gather(*(client.post("/run", json=payload) for _ in range(50)))
    ids = [r.json()["run_id"] for r in responses]
    assert len(set(ids)) == len(ids), f"duplicate ids: {ids}"


def test_run_uvicorn_honors_port_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cloud Run sets $PORT dynamically — run_uvicorn must read it, not hardcode 8080."""
    monkeypatch.setenv("PORT", "9123")
    monkeypatch.setenv("HOST", "127.0.0.1")
    captured: dict[str, object] = {}

    def fake_uvicorn_run(app_path: str, **kwargs: object) -> None:
        captured["app"] = app_path
        captured.update(kwargs)

    import uvicorn as uv

    monkeypatch.setattr(uv, "run", fake_uvicorn_run)

    from chaoslab_agent.main import run_uvicorn

    run_uvicorn()
    assert captured["host"] == "127.0.0.1"
    assert captured["port"] == 9123
