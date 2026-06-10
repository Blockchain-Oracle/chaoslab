"""Schedules CRUD + the OIDC-gated tick endpoint (story-9.3)."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Iterator
from typing import Any

import httpx
import pytest

from phoenix_audit_agent.config import get_settings
from phoenix_audit_agent.storage import agents as agent_storage
from phoenix_audit_agent.storage import runs as run_storage
from phoenix_audit_agent.storage import schedules as schedule_storage

from ..storage.fakes import InMemoryAgentStore, InMemoryRunStore, InMemoryScheduleStore


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    for key in list(os.environ):
        if key.startswith(
            (
                "PHOENIX_",
                "GEMINI_",
                "JUDGE_",
                "TARGET_",
                "GITLAB_",
                "GCS_",
                "SERVICE_",
                "SCHEDULER_",
            )
        ):
            monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini")
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
    """The tick launches REAL background orchestrator tasks — cancel + clear
    so they cannot leak across test boundaries (mirrors test_main)."""
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


async def _create(client: httpx.AsyncClient, **overrides: Any) -> dict[str, Any]:
    payload = {
        "target_url": "https://target.example",
        "cadence": "daily",
        "deliver_email": False,
        **overrides,
    }
    r = await client.post("/schedules", json=payload)
    assert r.status_code == 201, r.text
    return r.json()


async def test_create_then_list(client: httpx.AsyncClient) -> None:
    created = await _create(client, cadence="hourly")
    assert created["schedule_id"].startswith("sch_")
    assert created["cadence"] == "hourly"
    assert created["enabled"] is True
    assert created["next_fire_at"]  # fires on the next tick

    r = await client.get("/schedules")
    ids = [s["schedule_id"] for s in r.json()["schedules"]]
    assert created["schedule_id"] in ids


async def test_patch_toggles_enabled(client: httpx.AsyncClient) -> None:
    created = await _create(client)
    r = await client.patch(f"/schedules/{created['schedule_id']}", json={"enabled": False})
    assert r.status_code == 200
    assert r.json()["enabled"] is False

    r404 = await client.patch("/schedules/sch_missing", json={"enabled": False})
    assert r404.status_code == 404


async def test_create_deliver_email_without_recipient_is_422(
    client: httpx.AsyncClient,
) -> None:
    """deliver_email=True with no recipient is an unhonorable delivery
    contract — reject at POST instead of silently never emailing."""
    r = await client.post(
        "/schedules",
        json={"target_url": "https://target.example", "deliver_email": True},
    )
    assert r.status_code == 422


async def test_patch_deliver_email_without_recipient_is_422(
    client: httpx.AsyncClient,
) -> None:
    """PATCH must not be a side door into the delivery contract POST rejects."""
    created = await _create(client)
    r = await client.patch(f"/schedules/{created['schedule_id']}", json={"deliver_email": True})
    assert r.status_code == 422


async def test_create_rejects_ssrf_target(client: httpx.AsyncClient) -> None:
    r = await client.post(
        "/schedules",
        json={"target_url": "http://metadata.google.internal/computeMetadata/v1/"},
    )
    assert r.status_code == 422


async def test_patch_vanished_schedule_is_404(client: httpx.AsyncClient) -> None:
    """A schedule deleted between the existence check and the refresh must 404
    — never fabricate a response record from the stale pre-patch copy."""
    created = await _create(client)

    store = schedule_storage.get_schedule_store()
    assert isinstance(store, InMemoryScheduleStore)
    original_patch_fields = store.patch_fields

    async def patch_then_vanish(schedule_id: str, fields: dict[str, Any]) -> None:
        await original_patch_fields(schedule_id, fields)
        store._docs.pop(schedule_id, None)

    store.patch_fields = patch_then_vanish  # ty: ignore[invalid-assignment]
    r = await client.patch(f"/schedules/{created['schedule_id']}", json={"enabled": False})
    assert r.status_code == 404


async def test_invalid_email_rejected(client: httpx.AsyncClient) -> None:
    r = await client.post(
        "/schedules",
        json={"target_url": "https://t.example", "deliver_email": True, "email_recipient": "nope"},
    )
    assert r.status_code == 422


async def test_tick_fails_closed_when_unconfigured(client: httpx.AsyncClient) -> None:
    """No SERVICE_BASE_URL/SCHEDULER_INVOKER_EMAIL => 503, never an open
    endpoint that anyone can use to burn the GCP budget."""
    r = await client.post("/internal/scheduler-tick")
    assert r.status_code == 503
    assert "fail-closed" in r.json()["detail"]


async def test_tick_rejects_missing_and_invalid_tokens(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from phoenix_audit_agent.api import schedules as schedules_api

    monkeypatch.setenv("SERVICE_BASE_URL", "https://agent.example")
    monkeypatch.setenv("SCHEDULER_INVOKER_EMAIL", "deploy@p.iam.gserviceaccount.com")
    get_settings.cache_clear()

    r = await client.post("/internal/scheduler-tick")
    assert r.status_code == 401

    # Mock the Google verifier — the real one fetches certs over HTTPS, so an
    # unmocked call passes-by-accident offline (cert fetch raises → 401 for
    # the wrong reason) and hits a live endpoint from a unit test otherwise.
    def reject(token: object, request: object, audience: object) -> dict[str, Any]:
        msg = "synthetic verification failure"
        raise ValueError(msg)

    monkeypatch.setattr(schedules_api.id_token, "verify_oauth2_token", reject)
    r = await client.post(
        "/internal/scheduler-tick", headers={"authorization": "Bearer not-a-real-token"}
    )
    assert r.status_code == 401
    assert "ValueError" in r.json()["detail"]


@pytest.mark.parametrize(
    "claims",
    [
        # wrong service account
        {"email": "attacker@evil.example", "email_verified": True},
        # right account, unverified email claim
        {"email": "deploy@p.iam.gserviceaccount.com", "email_verified": False},
        # right account, email_verified absent (must not pass an is-True gate)
        {"email": "deploy@p.iam.gserviceaccount.com"},
    ],
    ids=["wrong-email", "unverified-email", "missing-email-verified"],
)
async def test_tick_rejects_valid_token_with_wrong_claims(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch, claims: dict[str, Any]
) -> None:
    """The authorization decision itself (claims gate) — verify_oauth2_token is
    mocked to SUCCEED so the 403 must come from the email/email_verified check."""
    from phoenix_audit_agent.api import schedules as schedules_api

    monkeypatch.setenv("SERVICE_BASE_URL", "https://agent.example")
    monkeypatch.setenv("SCHEDULER_INVOKER_EMAIL", "deploy@p.iam.gserviceaccount.com")
    get_settings.cache_clear()

    monkeypatch.setattr(
        schedules_api.id_token,
        "verify_oauth2_token",
        lambda token, request, audience: claims,
    )
    r = await client.post(
        "/internal/scheduler-tick", headers={"authorization": "Bearer signed-but-wrong"}
    )
    assert r.status_code == 403


async def test_tick_launches_due_schedules_with_valid_token(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from phoenix_audit_agent.api import schedules as schedules_api

    monkeypatch.setenv("SERVICE_BASE_URL", "https://agent.example")
    monkeypatch.setenv("SCHEDULER_INVOKER_EMAIL", "deploy@p.iam.gserviceaccount.com")
    get_settings.cache_clear()

    async def fake_verify(authorization: str | None) -> dict[str, Any]:
        assert authorization == "Bearer good-token"
        return {"email": "deploy@p.iam.gserviceaccount.com", "email_verified": True}

    monkeypatch.setattr(schedules_api, "verify_tick_oidc", fake_verify)

    await _create(client)  # next_fire_at = now → due immediately

    r = await client.post(
        "/internal/scheduler-tick", headers={"authorization": "Bearer good-token"}
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["claimed"] == 1
    assert len(body["launched"]) == 1
    run_id = body["launched"][0]

    # the launched run is a REAL run: registry record with source=scheduled
    record = await run_storage.get_run_store().get(run_id)
    assert record is not None
    assert record.source == "scheduled"
