"""Firebase user-token verification dependency (story-9.4).

The dependency is tested in isolation on a minimal FastAPI app — endpoint
wiring (owner stamping/filtering) is covered in the per-router test files.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Iterator
from typing import Any

import httpx
import pytest
from fastapi import Depends, FastAPI

from phoenix_audit_agent.config import get_settings


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    for key in list(os.environ):
        if key.startswith(("PHOENIX_", "GEMINI_", "FIREBASE_", "SERVICE_", "SCHEDULER_")):
            monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    from phoenix_audit_agent.api.auth import AuthedUser, require_user

    app = FastAPI()

    @app.get("/whoami")
    async def whoami(user: AuthedUser = Depends(require_user)) -> dict[str, Any]:  # noqa: B008
        return {"uid": user.uid, "email": user.email}

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def test_fails_closed_when_project_id_unconfigured(client: httpx.AsyncClient) -> None:
    """No FIREBASE_PROJECT_ID => 503 naming the env var — never an open
    endpoint because someone forgot a deploy env (mirrors the tick OIDC gate)."""
    r = await client.get("/whoami", headers={"x-firebase-id-token": "tok"})
    assert r.status_code == 503
    assert "FIREBASE_PROJECT_ID" in r.json()["detail"]


async def test_missing_token_is_401(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FIREBASE_PROJECT_ID", "proj-test")
    get_settings.cache_clear()
    r = await client.get("/whoami")
    assert r.status_code == 401


async def test_invalid_token_is_401_with_error_name(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verifier is mocked to raise — the real one fetches Google certs over
    HTTPS, so an unmocked call would fail offline for the wrong reason."""
    from phoenix_audit_agent.api import auth as auth_api

    monkeypatch.setenv("FIREBASE_PROJECT_ID", "proj-test")
    get_settings.cache_clear()

    def reject(token: object, request: object, audience: object) -> dict[str, Any]:
        msg = "synthetic verification failure"
        raise ValueError(msg)

    monkeypatch.setattr(auth_api.id_token, "verify_firebase_token", reject)
    r = await client.get("/whoami", headers={"x-firebase-id-token": "bad"})
    assert r.status_code == 401
    assert "ValueError" in r.json()["detail"]


async def test_verified_token_without_subject_is_401(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A token that verifies but carries no `sub` must not mint an identity —
    an empty uid would stamp owner_uid="" on regulator-facing records."""
    from phoenix_audit_agent.api import auth as auth_api

    monkeypatch.setenv("FIREBASE_PROJECT_ID", "proj-test")
    get_settings.cache_clear()
    monkeypatch.setattr(
        auth_api.id_token,
        "verify_firebase_token",
        lambda token, request, audience: {"email": "no-sub@example.com"},
    )
    r = await client.get("/whoami", headers={"x-firebase-id-token": "no-sub"})
    assert r.status_code == 401


async def test_valid_token_yields_uid_and_email(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from phoenix_audit_agent.api import auth as auth_api

    monkeypatch.setenv("FIREBASE_PROJECT_ID", "proj-test")
    get_settings.cache_clear()

    seen: dict[str, Any] = {}

    def accept(token: str, request: object, audience: str) -> dict[str, Any]:
        seen["token"] = token
        seen["audience"] = audience
        return {"sub": "uid-abc", "email": "abu@example.com"}

    monkeypatch.setattr(auth_api.id_token, "verify_firebase_token", accept)
    r = await client.get("/whoami", headers={"x-firebase-id-token": "good-token"})
    assert r.status_code == 200
    assert r.json() == {"uid": "uid-abc", "email": "abu@example.com"}
    # audience must be the Firebase project id — wrong audience accepts
    # tokens minted for ANY Firebase app.
    assert seen["audience"] == "proj-test"
    assert seen["token"] == "good-token"


async def test_email_is_optional_in_claims(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from phoenix_audit_agent.api import auth as auth_api

    monkeypatch.setenv("FIREBASE_PROJECT_ID", "proj-test")
    get_settings.cache_clear()
    monkeypatch.setattr(
        auth_api.id_token,
        "verify_firebase_token",
        lambda token, request, audience: {"sub": "uid-noemail"},
    )
    r = await client.get("/whoami", headers={"x-firebase-id-token": "tok"})
    assert r.status_code == 200
    assert r.json() == {"uid": "uid-noemail", "email": None}


async def test_cert_endpoint_outage_is_503_not_401(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A Google cert-endpoint outage is OUR problem — answering 401 would read
    as 'every user's token went bad' during support triage."""
    from google.auth import exceptions as ga_exceptions

    from phoenix_audit_agent.api import auth as auth_api

    monkeypatch.setenv("FIREBASE_PROJECT_ID", "proj-test")
    get_settings.cache_clear()

    def transport_down(token: object, request: object, audience: object) -> dict[str, Any]:
        raise ga_exceptions.TransportError("cert fetch failed")

    monkeypatch.setattr(auth_api.id_token, "verify_firebase_token", transport_down)
    r = await client.get("/whoami", headers={"x-firebase-id-token": "tok"})
    assert r.status_code == 503
    assert "temporarily unavailable" in r.json()["detail"]
