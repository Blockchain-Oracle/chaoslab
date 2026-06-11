"""/integrations/gitlab/* — the connect-flow HTTP contract (story-9.17 slice 2).

OAuth mechanics are slice 1's subject (test_gitlab_oauth.py); this module
pins the API mapping: auth scope, config gate, redirects, error statuses,
and that no token ever appears in a response body.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Callable, Iterator
from datetime import UTC, datetime
from typing import Any

import httpx
import pytest

from phoenix_audit_agent.config import get_settings
from phoenix_audit_agent.storage import profiles as profile_storage
from phoenix_audit_agent.storage.models import GitLabConnection

from ..storage.fakes import InMemoryGitLabStateStore, InMemoryProfileStore


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    for key in list(os.environ):
        if key.startswith(
            ("PHOENIX_", "GEMINI_", "JUDGE_", "GITLAB_", "RESEND_", "PUBLIC_", "FIREBASE_")
        ):
            monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini")
    monkeypatch.setenv("GITLAB_OAUTH_CLIENT_ID", "cid-test")
    monkeypatch.setenv("GITLAB_OAUTH_CLIENT_SECRET", "csecret-test")
    monkeypatch.setenv("GITLAB_OAUTH_REDIRECT_URI", "https://web.test/integrations/gitlab/callback")
    monkeypatch.setenv("PUBLIC_WEB_URL", "https://phxaudit.xyz")
    get_settings.cache_clear()
    profile_storage.set_profile_store(InMemoryProfileStore())
    from phoenix_audit_agent.storage import gitlab_states

    gitlab_states.set_gitlab_state_store(InMemoryGitLabStateStore())
    yield
    profile_storage.set_profile_store(None)
    gitlab_states.set_gitlab_state_store(None)
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _authed(_env: None, auth_as: Callable[..., None]) -> Callable[..., None]:
    auth_as(uid="user-a", email="a@example.com")
    return auth_as


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    from phoenix_audit_agent.main import app

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def _connect(uid: str = "user-a") -> None:
    conn = GitLabConnection(
        access_token="glat-x",
        refresh_token="glrt-x",
        expires_at=datetime.now(UTC).timestamp() + 3600,
        username="abu",
        gitlab_user_id=42,
        connected_at="2026-06-11T00:00:00+00:00",
    )
    await profile_storage.get_profile_store().merge(uid, {"uid": uid, "gitlab": conn.model_dump()})


# --- /connect --------------------------------------------------------------------


async def test_connect_returns_authorize_url(client: httpx.AsyncClient) -> None:
    """JSON (not a 307): the browser reaches this through the same-origin
    proxy, where a redirect's Location is unreadable to client JS — the web
    navigates to authorize_url itself."""
    r = await client.get("/integrations/gitlab/connect")
    assert r.status_code == 200
    assert r.json()["authorize_url"].startswith("https://gitlab.com/oauth/authorize?")


async def test_connect_503_when_unconfigured(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("GITLAB_OAUTH_CLIENT_ID")
    get_settings.cache_clear()
    r = await client.get("/integrations/gitlab/connect")
    assert r.status_code == 503


# --- /exchange -------------------------------------------------------------------


async def test_exchange_success_redirects_to_settings(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from phoenix_audit_agent.api import integrations as api_mod

    async def fake_exchange(*, code: str, state: str, uid: str) -> Any:
        assert (code, state, uid) == ("c1", "s1", "user-a")
        return None

    monkeypatch.setattr(api_mod.gitlab_oauth, "exchange_code", fake_exchange)
    r = await client.get("/integrations/gitlab/exchange", params={"code": "c1", "state": "s1"})
    assert r.status_code == 307
    assert r.headers["location"] == "https://phxaudit.xyz/settings?gitlab=connected"


async def test_exchange_state_error_422(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from phoenix_audit_agent.api import integrations as api_mod
    from phoenix_audit_agent.integrations.gitlab_oauth import StateError

    async def fake_exchange(*, code: str, state: str, uid: str) -> Any:
        raise StateError("unknown or already-used state")

    monkeypatch.setattr(api_mod.gitlab_oauth, "exchange_code", fake_exchange)
    r = await client.get("/integrations/gitlab/exchange", params={"code": "c", "state": "s"})
    assert r.status_code == 422


async def test_exchange_provider_failure_redirects_with_error(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """GitLab-side failures land the user back on settings with an honest
    error flag — not a bare 502 page mid-OAuth-dance."""
    from phoenix_audit_agent.api import integrations as api_mod
    from phoenix_audit_agent.integrations.gitlab_oauth import ExchangeError

    async def fake_exchange(*, code: str, state: str, uid: str) -> Any:
        raise ExchangeError("token exchange failed: HTTPStatusError")

    monkeypatch.setattr(api_mod.gitlab_oauth, "exchange_code", fake_exchange)
    r = await client.get("/integrations/gitlab/exchange", params={"code": "c", "state": "s"})
    assert r.status_code == 307
    assert r.headers["location"] == "https://phxaudit.xyz/settings?gitlab=error"


async def test_exchange_uid_mismatch_is_a_state_error() -> None:
    """A state minted for user A must never connect on user B's session —
    slice-1 module-level pin (exchange_code itself enforces it)."""
    from phoenix_audit_agent.integrations import gitlab_oauth
    from phoenix_audit_agent.storage.gitlab_states import get_gitlab_state_store

    await get_gitlab_state_store().put(
        "state-a",
        uid="user-a",
        code_verifier="v" * 48,
        created_at=datetime.now(UTC).isoformat(timespec="seconds"),
    )
    with pytest.raises(gitlab_oauth.StateError):
        await gitlab_oauth.exchange_code(code="c", state="state-a", uid="user-b")


# --- /status + /connection -------------------------------------------------------


async def test_status_disconnected(client: httpx.AsyncClient) -> None:
    r = await client.get("/integrations/gitlab/status")
    assert r.status_code == 200
    assert r.json() == {"connected": False, "username": None}


async def test_status_connected_carries_username_and_no_tokens(
    client: httpx.AsyncClient,
) -> None:
    await _connect()
    r = await client.get("/integrations/gitlab/status")
    assert r.json() == {"connected": True, "username": "abu"}
    assert "glat-x" not in r.text
    assert "glrt-x" not in r.text


async def test_disconnect_clears_connection(client: httpx.AsyncClient) -> None:
    await _connect()
    r = await client.delete("/integrations/gitlab/connection")
    assert r.status_code == 204
    status = await client.get("/integrations/gitlab/status")
    assert status.json()["connected"] is False


# --- /projects -------------------------------------------------------------------


async def test_projects_listed_with_user_token(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from phoenix_audit_agent.integrations import gitlab_api

    await _connect()
    seen_tokens: list[str] = []

    async def fake_list(token: str) -> list[dict[str, Any]]:
        seen_tokens.append(token)
        return [{"id": 7, "path_with_namespace": "abu/agents"}]

    monkeypatch.setattr(gitlab_api, "list_projects", fake_list)
    r = await client.get("/integrations/gitlab/projects")
    assert r.status_code == 200
    assert r.json() == {"projects": [{"id": 7, "path_with_namespace": "abu/agents"}]}
    assert seen_tokens == ["glat-x"]


async def test_projects_409_when_not_connected(client: httpx.AsyncClient) -> None:
    r = await client.get("/integrations/gitlab/projects")
    assert r.status_code == 409
    assert "connect" in r.json()["detail"].lower()


async def test_projects_409_when_connection_expired(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from phoenix_audit_agent.api import integrations as api_mod
    from phoenix_audit_agent.integrations.gitlab_oauth import ConnectionExpiredError

    await _connect()

    async def fake_token(uid: str) -> str:
        raise ConnectionExpiredError("GitLab connection expired — reconnect")

    monkeypatch.setattr(api_mod.gitlab_oauth, "get_valid_access_token", fake_token)
    r = await client.get("/integrations/gitlab/projects")
    assert r.status_code == 409
    assert "reconnect" in r.json()["detail"]


async def test_projects_502_on_gitlab_api_failure(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from phoenix_audit_agent.integrations import gitlab_api

    await _connect()

    async def fake_list(token: str) -> list[dict[str, Any]]:
        raise RuntimeError("gitlab down")

    monkeypatch.setattr(gitlab_api, "list_projects", fake_list)
    r = await client.get("/integrations/gitlab/projects")
    assert r.status_code == 502
