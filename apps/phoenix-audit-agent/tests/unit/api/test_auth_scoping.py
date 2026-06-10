"""Auth wiring (401s) + owner stamping/scoping across the product API (story-9.4).

`test_auth_dependency.py` covers require_user in isolation; this file covers
that every user-facing endpoint actually USES it, and that owner_uid scoping
holds: callers see their own records plus legacy `owner_uid=None` ones —
pre-auth audit evidence must not vanish from a regulator-facing registry.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Callable, Iterator
from typing import Any

import httpx
import pytest

from phoenix_audit_agent.config import get_settings
from phoenix_audit_agent.storage import agents as agent_storage
from phoenix_audit_agent.storage import runs as run_storage
from phoenix_audit_agent.storage import schedules as schedule_storage
from phoenix_audit_agent.storage.models import RunRecord, ScheduleRecord

from ..storage.fakes import InMemoryAgentStore, InMemoryRunStore, InMemoryScheduleStore


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    for key in list(os.environ):
        if key.startswith(
            ("PHOENIX_", "GEMINI_", "JUDGE_", "TARGET_", "GITLAB_", "GCS_", "FIREBASE_")
        ):
            monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini")
    monkeypatch.setenv("FIREBASE_PROJECT_ID", "proj-test")
    get_settings.cache_clear()
    run_storage.set_run_store(InMemoryRunStore())
    agent_storage.set_agent_store(InMemoryAgentStore())
    schedule_storage.set_schedule_store(InMemoryScheduleStore())
    _reset_run_registries()
    yield
    _reset_run_registries()
    run_storage.set_run_store(None)
    agent_storage.set_agent_store(None)
    schedule_storage.set_schedule_store(None)
    get_settings.cache_clear()


def _reset_run_registries() -> None:
    from phoenix_audit_agent.main import _RUN_QUEUES, _RUN_REGISTRY, _RUN_TASKS

    for task in _RUN_TASKS.values():
        if not task.done():
            task.cancel()
    _RUN_REGISTRY.clear()
    _RUN_QUEUES.clear()
    _RUN_TASKS.clear()


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    from phoenix_audit_agent.main import app

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


_AGENT_PAYLOAD = {
    "agent_id": "agt_scoped",
    "name": "Scoped Agent",
    "url": "https://agents.example/scoped",
    "framework": "adk-a2a",
    "tier": 1,
}


# --- wiring: every user-facing endpoint rejects tokenless calls -------------


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("POST", "/run", {"target_url": "http://localhost:8001"}),
        ("GET", "/runs", None),
        ("GET", "/runs/run_aaaaaaaaaaaa", None),
        ("GET", "/stream?runId=run_aaaaaaaaaaaa", None),
        ("POST", "/agents", _AGENT_PAYLOAD),
        ("GET", "/agents", None),
        ("GET", "/agents/demo-target", None),
        ("POST", "/schedules", {"target_url": "https://t.example"}),
        ("GET", "/schedules", None),
        ("PATCH", "/schedules/sch_x", {"enabled": False}),
    ],
)
async def test_endpoints_reject_missing_user_token(
    client: httpx.AsyncClient, method: str, path: str, body: dict[str, Any] | None
) -> None:
    r = await client.request(method, path, json=body)
    assert r.status_code == 401, f"{method} {path} -> {r.status_code}: {r.text}"


async def test_health_stays_public(client: httpx.AsyncClient) -> None:
    r = await client.get("/health")
    assert r.status_code == 200


async def test_tick_keeps_its_own_oidc_gate_not_user_auth(client: httpx.AsyncClient) -> None:
    """The tick is machine-to-machine — it must NOT demand a user token; its
    own fail-closed OIDC gate answers (503 here: tick env unset)."""
    r = await client.post("/internal/scheduler-tick")
    assert r.status_code == 503
    assert "fail-closed" in r.json()["detail"]


# --- owner stamping ----------------------------------------------------------


async def test_post_run_stamps_owner_uid(
    client: httpx.AsyncClient, auth_as: Callable[..., None]
) -> None:
    auth_as(uid="user-a")
    r = await client.post("/run", json={"target_url": "http://localhost:8001"})
    assert r.status_code == 201, r.text
    record = await run_storage.get_run_store().get(r.json()["run_id"])
    assert record is not None
    assert record.owner_uid == "user-a"


async def test_register_agent_stamps_owner_uid(
    client: httpx.AsyncClient, auth_as: Callable[..., None]
) -> None:
    auth_as(uid="user-a")
    r = await client.post("/agents", json=_AGENT_PAYLOAD)
    assert r.status_code == 201, r.text
    assert r.json()["owner_uid"] == "user-a"


async def test_create_schedule_stamps_owner_uid(
    client: httpx.AsyncClient, auth_as: Callable[..., None]
) -> None:
    auth_as(uid="user-a")
    r = await client.post("/schedules", json={"target_url": "https://t.example"})
    assert r.status_code == 201, r.text
    assert r.json()["owner_uid"] == "user-a"


async def test_scheduled_run_inherits_schedule_owner() -> None:
    """Tick-launched runs carry the schedule creator's uid — a scheduled run
    must appear in ITS OWNER's registry, not nobody's."""
    from phoenix_audit_agent.main import _launch_scheduled_run

    schedule = ScheduleRecord(
        schedule_id="sch_owned",
        target_url="https://t.example",
        owner_uid="user-a",
        next_fire_at="2026-06-10T00:00:00+00:00",
        created_at="2026-06-10T00:00:00+00:00",
    )
    run_id = await _launch_scheduled_run(schedule)
    record = await run_storage.get_run_store().get(run_id)
    assert record is not None
    assert record.owner_uid == "user-a"
    assert record.source == "scheduled"


# --- owner scoping: own + legacy visible, foreign invisible ------------------


async def _seed_runs() -> None:
    store = run_storage.get_run_store()
    await store.create(
        RunRecord(
            run_id="run_aaaaaaaaaaaa",
            target_url="https://t.example",
            created_at="2026-06-10T01:00:00Z",
            owner_uid="user-a",
        )
    )
    await store.create(
        RunRecord(
            run_id="run_bbbbbbbbbbbb",
            target_url="https://t.example",
            created_at="2026-06-10T02:00:00Z",
            owner_uid="user-b",
        )
    )
    await store.create(
        RunRecord(
            run_id="run_legacy000000",
            target_url="https://t.example",
            created_at="2026-06-10T03:00:00Z",
        )
    )


async def test_list_runs_scopes_to_owner_plus_legacy(
    client: httpx.AsyncClient, auth_as: Callable[..., None]
) -> None:
    await _seed_runs()
    auth_as(uid="user-a")
    r = await client.get("/runs")
    ids = {x["run_id"] for x in r.json()["runs"]}
    assert ids == {"run_aaaaaaaaaaaa", "run_legacy000000"}


async def test_get_foreign_run_is_404_legacy_visible(
    client: httpx.AsyncClient, auth_as: Callable[..., None]
) -> None:
    await _seed_runs()
    auth_as(uid="user-a")
    assert (await client.get("/runs/run_bbbbbbbbbbbb")).status_code == 404
    assert (await client.get("/runs/run_aaaaaaaaaaaa")).status_code == 200
    assert (await client.get("/runs/run_legacy000000")).status_code == 200


async def test_list_agents_scopes_to_owner_plus_seed(
    client: httpx.AsyncClient, auth_as: Callable[..., None]
) -> None:
    auth_as(uid="user-a")
    await client.post("/agents", json=_AGENT_PAYLOAD)
    auth_as(uid="user-b")
    r = await client.get("/agents")
    ids = [a["agent_id"] for a in r.json()["agents"]]
    assert "agt_scoped" not in ids
    assert "demo-target" in ids  # seed has no owner — visible to everyone


async def test_get_foreign_agent_is_404(
    client: httpx.AsyncClient, auth_as: Callable[..., None]
) -> None:
    auth_as(uid="user-a")
    await client.post("/agents", json=_AGENT_PAYLOAD)
    auth_as(uid="user-b")
    assert (await client.get("/agents/agt_scoped")).status_code == 404
    assert (await client.get("/agents/demo-target")).status_code == 200


async def test_list_and_patch_schedules_scoped(
    client: httpx.AsyncClient, auth_as: Callable[..., None]
) -> None:
    auth_as(uid="user-a")
    created = await client.post("/schedules", json={"target_url": "https://t.example"})
    sid = created.json()["schedule_id"]

    auth_as(uid="user-b")
    r = await client.get("/schedules")
    assert sid not in [s["schedule_id"] for s in r.json()["schedules"]]
    # Foreign PATCH must read as not-found — a 403 would CONFIRM the id exists.
    assert (await client.patch(f"/schedules/{sid}", json={"enabled": False})).status_code == 404

    auth_as(uid="user-a")
    assert (await client.patch(f"/schedules/{sid}", json={"enabled": False})).status_code == 200


async def test_stream_foreign_run_is_404(
    client: httpx.AsyncClient, auth_as: Callable[..., None]
) -> None:
    """Live SSE access follows ownership too — the registry state carries the
    launching user's uid."""
    auth_as(uid="user-a")
    r = await client.post("/run", json={"target_url": "http://localhost:8001"})
    run_id = r.json()["run_id"]

    auth_as(uid="user-b")
    foreign = await client.get(f"/stream?runId={run_id}")
    assert foreign.status_code == 404
