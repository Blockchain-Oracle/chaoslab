"""GitLab per-user OAuth: PKCE connect, code exchange, refresh-with-rotation
(story-9.17).

The load-bearing invariant: GitLab ROTATES refresh tokens — every refresh
response carries a new pair, and the old pair is dead. The rotated pair is
persisted BEFORE the access token is returned for use; losing it would kill
the connection silently.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import structlog
from authlib.common.security import generate_token
from authlib.integrations.httpx_client import AsyncOAuth2Client

from phoenix_audit_agent._time import parse_iso, utc_now_iso
from phoenix_audit_agent.config import get_settings
from phoenix_audit_agent.storage.gitlab_states import get_gitlab_state_store
from phoenix_audit_agent.storage.models import GitLabConnection
from phoenix_audit_agent.storage.profiles import get_profile_store

_log = structlog.get_logger(__name__)

GITLAB_AUTHORIZE_URL = "https://gitlab.com/oauth/authorize"
GITLAB_TOKEN_URL = "https://gitlab.com/oauth/token"  # noqa: S105 — endpoint URL, not a secret
GITLAB_API_BASE = "https://gitlab.com/api/v4"
STATE_TTL = timedelta(minutes=10)
# Refresh when within this window of expiry — a token that dies mid-MR-filing
# is worse than one refresh too many.
EXPIRY_SLACK_SECONDS = 60


class GitLabOAuthError(RuntimeError):
    """Base for the connect-flow failures the API maps to status codes."""


class StateError(GitLabOAuthError):
    """Unknown / expired / reused state — never proceeds to an exchange."""


class ExchangeError(GitLabOAuthError):
    """GitLab's token endpoint rejected the code exchange."""


class NotConnectedError(GitLabOAuthError):
    """No GitLab connection on the profile."""


class ConnectionExpiredError(GitLabOAuthError):
    """Refresh failed (revoked upstream) — the stored connection was cleared."""


def oauth_configured() -> bool:
    s = get_settings()
    return bool(
        s.GITLAB_OAUTH_CLIENT_ID
        and s.GITLAB_OAUTH_CLIENT_SECRET is not None
        and s.GITLAB_OAUTH_CLIENT_SECRET.get_secret_value()
        and s.GITLAB_OAUTH_REDIRECT_URI
    )


def _client() -> AsyncOAuth2Client:
    s = get_settings()
    secret = s.GITLAB_OAUTH_CLIENT_SECRET
    return AsyncOAuth2Client(
        client_id=s.GITLAB_OAUTH_CLIENT_ID,
        client_secret=secret.get_secret_value() if secret else "",
        redirect_uri=s.GITLAB_OAUTH_REDIRECT_URI,
        scope="api",
        code_challenge_method="S256",
    )


async def build_authorization_redirect(uid: str) -> str:
    """Mint the GitLab authorize URL; persist {state → uid, verifier}."""
    code_verifier = generate_token(48)
    async with _client() as client:
        url, state = client.create_authorization_url(
            GITLAB_AUTHORIZE_URL, code_verifier=code_verifier
        )
    await get_gitlab_state_store().put(
        state, uid=uid, code_verifier=code_verifier, created_at=utc_now_iso()
    )
    return url


async def exchange_code(*, code: str, state: str) -> GitLabConnection:
    """Single-use state → token exchange → user fetch → persist connection."""
    doc = await get_gitlab_state_store().consume(state)
    if doc is None:
        raise StateError("unknown or already-used state")
    try:
        minted = parse_iso(doc.created_at)
    except ValueError as exc:
        raise StateError("corrupted state document") from exc
    if datetime.now(UTC) - minted > STATE_TTL:
        raise StateError("state expired — restart the connect flow")

    async with _client() as client:
        try:
            token = await client.fetch_token(
                GITLAB_TOKEN_URL, code=code, code_verifier=doc.code_verifier
            )
            user_resp = await client.get(f"{GITLAB_API_BASE}/user")
            user_resp.raise_for_status()
        except Exception as exc:
            _log.error("gitlab_oauth_exchange_failed", uid=doc.uid, error=type(exc).__name__)
            raise ExchangeError(f"token exchange failed: {type(exc).__name__}") from exc
    user = user_resp.json()
    connection = GitLabConnection(
        access_token=token["access_token"],
        refresh_token=token["refresh_token"],
        expires_at=float(token["expires_at"]),
        username=user["username"],
        gitlab_user_id=int(user["id"]),
        connected_at=utc_now_iso(),
    )
    await _persist(doc.uid, connection)
    _log.info("gitlab_connected", uid=doc.uid, username=connection.username)
    return connection


async def get_valid_access_token(uid: str) -> str:
    """Access token gated on expiry; refresh persists the ROTATED pair first."""
    profile = await get_profile_store().get(uid)
    connection = profile.gitlab if profile is not None else None
    if connection is None:
        raise NotConnectedError("no GitLab connection — connect in settings")
    now = datetime.now(UTC).timestamp()
    if connection.expires_at > now + EXPIRY_SLACK_SECONDS:
        return connection.access_token

    async with _client() as client:
        try:
            token = await client.refresh_token(
                GITLAB_TOKEN_URL, refresh_token=connection.refresh_token
            )
        except Exception as exc:
            # The old pair is dead either way — keeping it would produce an
            # infinite refresh-fail loop. Clear, disclose, make the user
            # reconnect (the API maps this to 409).
            await get_profile_store().merge(uid, {"gitlab": None})
            _log.warning("gitlab_connection_expired", uid=uid, error=type(exc).__name__)
            raise ConnectionExpiredError("GitLab connection expired — reconnect") from exc
    rotated = connection.model_copy(
        update={
            "access_token": token["access_token"],
            # A provider that ever omits the new refresh token means the old
            # one is still live — keep it rather than storing nothing.
            "refresh_token": token.get("refresh_token") or connection.refresh_token,
            "expires_at": float(token["expires_at"]),
        }
    )
    await _persist(uid, rotated)
    return rotated.access_token


async def disconnect(uid: str) -> None:
    await get_profile_store().merge(uid, {"gitlab": None})
    _log.info("gitlab_disconnected", uid=uid)


async def _persist(uid: str, connection: GitLabConnection) -> None:
    await get_profile_store().merge(uid, {"uid": uid, "gitlab": connection.model_dump()})


__all__ = [
    "ConnectionExpiredError",
    "ExchangeError",
    "GitLabOAuthError",
    "NotConnectedError",
    "StateError",
    "build_authorization_redirect",
    "disconnect",
    "exchange_code",
    "get_valid_access_token",
    "oauth_configured",
]
