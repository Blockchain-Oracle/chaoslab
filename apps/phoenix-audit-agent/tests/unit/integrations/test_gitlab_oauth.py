"""integrations/gitlab_oauth.py — PKCE connect, exchange, refresh-with-rotation
(story-9.17 slice 1).

Offline: respx intercepts the Authlib httpx client; stores are in-memory
fakes. The rotation test is the load-bearing one — GitLab rotates refresh
tokens, and losing the new pair kills the connection silently.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
import respx

from phoenix_audit_agent.config import get_settings
from phoenix_audit_agent.storage import profiles as profile_storage
from phoenix_audit_agent.storage.models import GitLabConnection, UserProfile

from ..storage.fakes import InMemoryGitLabStateStore, InMemoryProfileStore

TOKEN_URL = "https://gitlab.com/oauth/token"
USER_URL = "https://gitlab.com/api/v4/user"


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    for key in list(os.environ):
        if key.startswith(("PHOENIX_", "GEMINI_", "JUDGE_", "GITLAB_", "RESEND_", "PUBLIC_")):
            monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini")
    monkeypatch.setenv("GITLAB_OAUTH_CLIENT_ID", "cid-test")
    monkeypatch.setenv("GITLAB_OAUTH_CLIENT_SECRET", "csecret-test")
    monkeypatch.setenv("GITLAB_OAUTH_REDIRECT_URI", "https://web.test/integrations/gitlab/callback")
    get_settings.cache_clear()
    profile_storage.set_profile_store(InMemoryProfileStore())
    from phoenix_audit_agent.storage import gitlab_states

    gitlab_states.set_gitlab_state_store(InMemoryGitLabStateStore())
    yield
    profile_storage.set_profile_store(None)
    gitlab_states.set_gitlab_state_store(None)
    get_settings.cache_clear()


def _token_payload(suffix: str = "1") -> dict[str, Any]:
    return {
        "access_token": f"glat-{suffix}",
        "refresh_token": f"glrt-{suffix}",
        "token_type": "bearer",
        "expires_in": 7200,
        "scope": "api",
    }


async def _seed_connection(
    *,
    expires_at: float,
    access_token: str = "glat-old",  # noqa: S107 — test sentinel, not a secret
    refresh_token: str = "glrt-old",  # noqa: S107 — test sentinel, not a secret
) -> None:
    conn = GitLabConnection(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=expires_at,
        username="abu",
        gitlab_user_id=42,
        connected_at="2026-06-11T00:00:00+00:00",
    )
    await profile_storage.get_profile_store().merge(
        "user-a", {"uid": "user-a", "gitlab": conn.model_dump()}
    )


# --- configuration gate ---------------------------------------------------------


def test_not_configured_without_client_id(monkeypatch: pytest.MonkeyPatch) -> None:
    from phoenix_audit_agent.integrations import gitlab_oauth

    monkeypatch.delenv("GITLAB_OAUTH_CLIENT_ID")
    get_settings.cache_clear()
    assert gitlab_oauth.oauth_configured() is False


def test_configured_with_full_triplet() -> None:
    from phoenix_audit_agent.integrations import gitlab_oauth

    assert gitlab_oauth.oauth_configured() is True


# --- authorization redirect ------------------------------------------------------


async def test_authorization_redirect_carries_pkce_and_persists_state() -> None:
    from phoenix_audit_agent.integrations import gitlab_oauth
    from phoenix_audit_agent.storage.gitlab_states import get_gitlab_state_store

    url = await gitlab_oauth.build_authorization_redirect("user-a")
    parsed = urlparse(url)
    assert parsed.scheme == "https"
    assert parsed.netloc == "gitlab.com"
    assert parsed.path == "/oauth/authorize"
    q = parse_qs(parsed.query)
    assert q["client_id"] == ["cid-test"]
    assert q["redirect_uri"] == ["https://web.test/integrations/gitlab/callback"]
    assert q["response_type"] == ["code"]
    assert q["scope"] == ["api"]
    assert q["code_challenge_method"] == ["S256"]
    assert q["code_challenge"][0]
    state = q["state"][0]

    doc = await get_gitlab_state_store().consume(state)
    assert doc is not None
    assert doc.uid == "user-a"
    # The verifier stays server-side and is NOT the challenge in the URL.
    assert doc.code_verifier
    assert doc.code_verifier != q["code_challenge"][0]
    assert doc.code_verifier not in url


# --- exchange --------------------------------------------------------------------


@respx.mock
async def test_exchange_happy_path_persists_connection_and_consumes_state() -> None:
    from phoenix_audit_agent.integrations import gitlab_oauth

    token_route = respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(200, json=_token_payload())
    )
    respx.get(USER_URL).mock(return_value=httpx.Response(200, json={"username": "abu", "id": 42}))

    url = await gitlab_oauth.build_authorization_redirect("user-a")
    state = parse_qs(urlparse(url).query)["state"][0]

    conn = await gitlab_oauth.exchange_code(code="authcode-1", state=state, uid="user-a")
    assert conn.username == "abu"
    assert conn.gitlab_user_id == 42

    # The PKCE verifier rode the token exchange.
    body = parse_qs(token_route.calls[0].request.content.decode())
    assert body["code"] == ["authcode-1"]
    assert "code_verifier" in body

    profile = await profile_storage.get_profile_store().get("user-a")
    assert profile is not None
    assert profile.gitlab is not None
    assert profile.gitlab.access_token == "glat-1"
    assert profile.gitlab.refresh_token == "glrt-1"
    assert profile.gitlab.expires_at > datetime.now(UTC).timestamp() + 7000

    # Single-use: the same state must never exchange twice.
    with pytest.raises(gitlab_oauth.StateError):
        await gitlab_oauth.exchange_code(code="authcode-1", state=state, uid="user-a")


@respx.mock
async def test_concurrent_exchange_same_state_single_use() -> None:
    """Double-fired callback (same state, concurrent): exactly one exchange
    succeeds; the other gets StateError — never two connections minted
    (PR #112 H-2)."""
    import asyncio

    from phoenix_audit_agent.integrations import gitlab_oauth

    token_route = respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(200, json=_token_payload())
    )
    respx.get(USER_URL).mock(return_value=httpx.Response(200, json={"username": "abu", "id": 42}))

    url = await gitlab_oauth.build_authorization_redirect("user-a")
    state = parse_qs(urlparse(url).query)["state"][0]

    results = await asyncio.gather(
        gitlab_oauth.exchange_code(code="c1", state=state, uid="user-a"),
        gitlab_oauth.exchange_code(code="c1", state=state, uid="user-a"),
        return_exceptions=True,
    )
    successes = [r for r in results if not isinstance(r, BaseException)]
    failures = [r for r in results if isinstance(r, gitlab_oauth.StateError)]
    assert len(successes) == 1
    assert len(failures) == 1
    assert token_route.call_count == 1


async def test_exchange_unknown_state_rejected_without_http() -> None:
    from phoenix_audit_agent.integrations import gitlab_oauth

    with pytest.raises(gitlab_oauth.StateError):
        await gitlab_oauth.exchange_code(code="c", state="state-nobody-minted", uid="user-a")


async def test_exchange_expired_state_rejected() -> None:
    from phoenix_audit_agent.integrations import gitlab_oauth
    from phoenix_audit_agent.storage.gitlab_states import get_gitlab_state_store

    stale = (datetime.now(UTC) - timedelta(minutes=11)).isoformat(timespec="seconds")
    await get_gitlab_state_store().put(
        "state-old", uid="user-a", code_verifier="v" * 48, created_at=stale
    )
    with pytest.raises(gitlab_oauth.StateError):
        await gitlab_oauth.exchange_code(code="c", state="state-old", uid="user-a")


@respx.mock
async def test_exchange_token_endpoint_failure_persists_nothing() -> None:
    from phoenix_audit_agent.integrations import gitlab_oauth

    respx.post(TOKEN_URL).mock(return_value=httpx.Response(400, json={"error": "invalid_grant"}))
    url = await gitlab_oauth.build_authorization_redirect("user-a")
    state = parse_qs(urlparse(url).query)["state"][0]

    with pytest.raises(gitlab_oauth.ExchangeError):
        await gitlab_oauth.exchange_code(code="bad", state=state, uid="user-a")
    profile = await profile_storage.get_profile_store().get("user-a")
    assert profile is None or profile.gitlab is None


# --- token validity + rotation ---------------------------------------------------


async def test_valid_token_returned_without_refresh() -> None:
    from phoenix_audit_agent.integrations import gitlab_oauth

    fresh = datetime.now(UTC).timestamp() + 3600
    await _seed_connection(expires_at=fresh)
    token = await gitlab_oauth.get_valid_access_token("user-a")
    assert token == "glat-old"


@respx.mock
async def test_expired_token_refreshes_and_persists_rotated_pair() -> None:
    """THE rotation invariant: the new refresh token must be persisted
    BEFORE the access token is used — GitLab invalidates the old pair."""
    from phoenix_audit_agent.integrations import gitlab_oauth

    refresh_route = respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(200, json=_token_payload("rotated"))
    )
    await _seed_connection(expires_at=datetime.now(UTC).timestamp() - 10)

    token = await gitlab_oauth.get_valid_access_token("user-a")
    assert token == "glat-rotated"
    body = parse_qs(refresh_route.calls[0].request.content.decode())
    assert body["grant_type"] == ["refresh_token"]
    assert body["refresh_token"] == ["glrt-old"]

    profile = await profile_storage.get_profile_store().get("user-a")
    assert profile is not None
    assert profile.gitlab is not None
    assert profile.gitlab.access_token == "glat-rotated"
    assert profile.gitlab.refresh_token == "glrt-rotated"
    assert profile.gitlab.username == "abu"  # identity survives the rotation


@respx.mock
async def test_refresh_failure_clears_connection() -> None:
    from phoenix_audit_agent.integrations import gitlab_oauth

    respx.post(TOKEN_URL).mock(return_value=httpx.Response(400, json={"error": "invalid_grant"}))
    await _seed_connection(expires_at=datetime.now(UTC).timestamp() - 10)

    with pytest.raises(gitlab_oauth.ConnectionExpiredError):
        await gitlab_oauth.get_valid_access_token("user-a")
    profile = await profile_storage.get_profile_store().get("user-a")
    assert profile is not None
    assert profile.gitlab is None


@respx.mock
async def test_refresh_transport_error_preserves_connection() -> None:
    """A network blip must NOT destroy a healthy connection — distinct
    retryable error, stored pair untouched (slice-1 review HIGH-1)."""
    from phoenix_audit_agent.integrations import gitlab_oauth

    respx.post(TOKEN_URL).mock(side_effect=httpx.ConnectError("dns down"))
    await _seed_connection(expires_at=datetime.now(UTC).timestamp() - 10)

    with pytest.raises(gitlab_oauth.GitLabUnavailableError):
        await gitlab_oauth.get_valid_access_token("user-a")
    profile = await profile_storage.get_profile_store().get("user-a")
    assert profile is not None
    assert profile.gitlab is not None
    assert profile.gitlab.refresh_token == "glrt-old"


@respx.mock
async def test_concurrent_callers_refresh_exactly_once() -> None:
    """Two expired-token callers must serialize — the loser re-reads the
    winner's rotated pair instead of double-refreshing (review HIGH-2)."""
    import asyncio

    from phoenix_audit_agent.integrations import gitlab_oauth

    refresh_route = respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(200, json=_token_payload("rotated"))
    )
    await _seed_connection(expires_at=datetime.now(UTC).timestamp() - 10)

    tokens = await asyncio.gather(
        gitlab_oauth.get_valid_access_token("user-a"),
        gitlab_oauth.get_valid_access_token("user-a"),
    )
    assert tokens == ["glat-rotated", "glat-rotated"]
    assert refresh_route.call_count == 1


@respx.mock
async def test_refresh_unparseable_response_clears_and_discloses() -> None:
    """A 200 whose body can't mint a connection means the old pair is
    already dead at GitLab — clear + ConnectionExpired, never a silent
    brick (review MED-1)."""
    from phoenix_audit_agent.integrations import gitlab_oauth

    respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(200, json={"access_token": "glat-x", "token_type": "bearer"})
    )
    await _seed_connection(expires_at=datetime.now(UTC).timestamp() - 10)

    with pytest.raises(gitlab_oauth.ConnectionExpiredError):
        await gitlab_oauth.get_valid_access_token("user-a")
    profile = await profile_storage.get_profile_store().get("user-a")
    assert profile is not None
    assert profile.gitlab is None


@respx.mock
async def test_exchange_user_fetch_missing_fields_is_exchange_error() -> None:
    from phoenix_audit_agent.integrations import gitlab_oauth

    respx.post(TOKEN_URL).mock(return_value=httpx.Response(200, json=_token_payload()))
    respx.get(USER_URL).mock(return_value=httpx.Response(200, json={}))
    url = await gitlab_oauth.build_authorization_redirect("user-a")
    state = parse_qs(urlparse(url).query)["state"][0]

    with pytest.raises(gitlab_oauth.ExchangeError):
        await gitlab_oauth.exchange_code(code="c", state=state, uid="user-a")
    profile = await profile_storage.get_profile_store().get("user-a")
    assert profile is None or profile.gitlab is None


async def test_not_connected_raises() -> None:
    from phoenix_audit_agent.integrations import gitlab_oauth

    with pytest.raises(gitlab_oauth.NotConnectedError):
        await gitlab_oauth.get_valid_access_token("user-nobody")


async def test_disconnect_clears_blob() -> None:
    from phoenix_audit_agent.integrations import gitlab_oauth

    await _seed_connection(expires_at=datetime.now(UTC).timestamp() + 3600)
    await gitlab_oauth.disconnect("user-a")
    profile = await profile_storage.get_profile_store().get("user-a")
    assert profile is not None
    assert profile.gitlab is None


# --- token-leak guard -------------------------------------------------------------


async def test_user_profile_serialization_never_carries_tokens() -> None:
    """GET /profile returns UserProfile verbatim — the gitlab blob must be
    populated on VALIDATION (backend reads it) but stripped from every DUMP
    (no token can reach the browser)."""
    await _seed_connection(expires_at=datetime.now(UTC).timestamp() + 3600)
    profile = await profile_storage.get_profile_store().get("user-a")
    assert profile is not None
    assert isinstance(profile.gitlab, GitLabConnection)

    dumped = profile.model_dump()
    assert "gitlab" not in dumped
    assert "glat-old" not in profile.model_dump_json()

    # And a from-scratch model behaves the same.
    fresh = UserProfile(uid="u2")
    assert "gitlab" not in fresh.model_dump()
