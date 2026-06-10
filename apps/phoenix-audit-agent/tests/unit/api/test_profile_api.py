"""GET/PATCH /profile — the users/{uid} settings spine (story-9.12).

The uid always comes from the verified token: there is no profile-id
parameter, so cross-user reads/writes are impossible by construction.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Iterator

import httpx
import pytest

from phoenix_audit_agent.config import get_settings
from phoenix_audit_agent.storage import profiles as profile_storage

from ..storage.fakes import InMemoryProfileStore


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    for key in list(os.environ):
        if key.startswith(
            ("PHOENIX_", "GEMINI_", "JUDGE_", "TARGET_", "GITLAB_", "GCS_", "FIREBASE_")
        ):
            monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini")
    get_settings.cache_clear()
    profile_storage.set_profile_store(InMemoryProfileStore())
    yield
    profile_storage.set_profile_store(None)
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _authed(_env: None, auth_as) -> None:
    auth_as("user-profile-1", email="officer@example.com")


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    from phoenix_audit_agent.main import app

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def test_get_profile_returns_defaults_without_creating_doc(
    client: httpx.AsyncClient,
) -> None:
    r = await client.get("/profile")
    assert r.status_code == 200
    body = r.json()
    assert body["uid"] == "user-profile-1"
    assert body["email"] == "officer@example.com"
    assert body["org_name"] is None
    assert body["framework_default"] == "EU AI Act"
    assert body["hosting_pref"] == "default"
    assert body["onboarded"] is False
    # Read-only default: no document materialized by a GET.
    store = profile_storage.get_profile_store()
    assert await store.get("user-profile-1") is None


async def test_patch_upserts_subset_and_get_reflects(client: httpx.AsyncClient) -> None:
    r = await client.patch("/profile", json={"org_name": "Meridian Mutual", "onboarded": True})
    assert r.status_code == 200
    body = r.json()
    assert body["org_name"] == "Meridian Mutual"
    assert body["onboarded"] is True
    # Untouched fields keep their defaults.
    assert body["framework_default"] == "EU AI Act"
    assert body["created_at"]
    assert body["updated_at"]

    r2 = await client.patch("/profile", json={"framework_default": "NIST AI RMF"})
    assert r2.status_code == 200
    body2 = r2.json()
    # Earlier fields survive a later partial PATCH.
    assert body2["org_name"] == "Meridian Mutual"
    assert body2["framework_default"] == "NIST AI RMF"
    assert body2["created_at"] == body["created_at"]

    r3 = await client.get("/profile")
    assert r3.json()["framework_default"] == "NIST AI RMF"


async def test_patch_rejects_unknown_fields_and_bad_values(client: httpx.AsyncClient) -> None:
    assert (await client.patch("/profile", json={"is_admin": True})).status_code == 422
    assert (await client.patch("/profile", json={"hosting_pref": "cloud9"})).status_code == 422
    assert (await client.patch("/profile", json={"framework_default": ""})).status_code == 422


async def test_profiles_are_scoped_to_the_token_uid(client: httpx.AsyncClient, auth_as) -> None:
    await client.patch("/profile", json={"org_name": "Meridian Mutual"})

    auth_as("user-profile-2", email="other@example.com")
    r = await client.get("/profile")
    body = r.json()
    assert body["uid"] == "user-profile-2"
    assert body["org_name"] is None  # never another user's data
