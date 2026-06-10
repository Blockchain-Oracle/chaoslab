"""Firebase ID-token verification for user-facing endpoints (story-9.4).

The web proxy forwards the signed-in user's Firebase ID token in
`X-Firebase-Id-Token`; `Authorization` stays reserved for Cloud Run's own
service-to-service OIDC ingress auth.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

import structlog
from fastapi import HTTPException, Request
from google.auth import exceptions as ga_exceptions
from google.auth.transport import requests as ga_requests
from google.oauth2 import id_token

from phoenix_audit_agent.config import get_settings

_log = structlog.get_logger(__name__)

USER_TOKEN_HEADER = "x-firebase-id-token"  # noqa: S105 — header NAME, not a credential

# Reused across requests for connection pooling. NOTE: a plain Request()
# re-fetches Google's certs per verification (caching needs a CacheControl
# session) — acceptable because verification runs off the event loop.
_GA_REQUEST = ga_requests.Request()


@dataclass(frozen=True)
class AuthedUser:
    uid: str
    email: str | None


async def require_user(request: Request) -> AuthedUser:
    """Verify the caller's Firebase ID token. Fails CLOSED on misconfiguration
    — an open product API would let anyone read or write audit records."""
    project_id = get_settings().FIREBASE_PROJECT_ID
    if not project_id:
        raise HTTPException(
            status_code=503,
            detail="user auth is not configured: set FIREBASE_PROJECT_ID (fail-closed by design)",
        )
    token = request.headers.get(USER_TOKEN_HEADER)
    if not token:
        raise HTTPException(status_code=401, detail="missing user token")
    try:
        # verify_firebase_token does blocking I/O (Google cert fetch) — keep it
        # off the event loop so a slow cert endpoint can't stall SSE streams.
        claims = await asyncio.to_thread(
            id_token.verify_firebase_token, token, _GA_REQUEST, project_id
        )
    except ga_exceptions.TransportError as err:
        # Cert-endpoint outage is OUR problem, not the caller's — a 401 here
        # would read as "every user's token went bad" in support triage.
        _log.warning("user_token_verification_unavailable", exc_info=True)
        raise HTTPException(
            status_code=503, detail="token verification temporarily unavailable"
        ) from err
    except Exception as err:
        # Logged at WARN so a surge of one error class (cert poisoning vs
        # malformed tokens) stays distinguishable in Cloud Logging.
        _log.warning("user_token_rejected", error_type=type(err).__name__, exc_info=True)
        raise HTTPException(
            status_code=401, detail=f"invalid user token: {type(err).__name__}"
        ) from err
    uid = claims.get("sub") if claims else None
    if not uid:
        raise HTTPException(status_code=401, detail="invalid user token: no subject")
    return AuthedUser(uid=uid, email=claims.get("email"))


__all__ = ["USER_TOKEN_HEADER", "AuthedUser", "require_user"]
