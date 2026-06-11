"""/integrations/gitlab/* — the per-user OAuth connect flow (story-9.17).

Status mapping is the contract here: 503 unconfigured (fail closed), 422 for
state problems (never an exchange), 307 back to settings for both success
and provider-side failure (a user mid-OAuth-dance gets a page, not a JSON
error), 409 for "connect/reconnect first", 502 for GitLab API failures.
"""

from __future__ import annotations

from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from phoenix_audit_agent.api.auth import AuthedUser, require_user
from phoenix_audit_agent.config import get_settings
from phoenix_audit_agent.integrations import gitlab_api, gitlab_oauth
from phoenix_audit_agent.storage.profiles import get_profile_store

_log = structlog.get_logger(__name__)

router = APIRouter(prefix="/integrations/gitlab")


def _require_configured() -> None:
    if not gitlab_oauth.oauth_configured():
        raise HTTPException(
            status_code=503, detail="GitLab OAuth is not configured on this deployment"
        )


def _settings_redirect(flag: str) -> RedirectResponse:
    base = get_settings().PUBLIC_WEB_URL.rstrip("/")
    return RedirectResponse(url=f"{base}/settings?gitlab={flag}", status_code=307)


class ConnectResponse(BaseModel):
    authorize_url: str


@router.get("/connect", response_model=ConnectResponse)
async def connect(user: Annotated[AuthedUser, Depends(require_user)]) -> ConnectResponse:
    # JSON, not a 307 — the browser calls this through the same-origin proxy,
    # where a redirect's Location is unreadable to client JS. The web
    # navigates to authorize_url itself.
    _require_configured()
    url = await gitlab_oauth.build_authorization_redirect(user.uid)
    return ConnectResponse(authorize_url=url)


@router.get("/exchange")
async def exchange(
    code: str, state: str, user: Annotated[AuthedUser, Depends(require_user)]
) -> RedirectResponse:
    _require_configured()
    try:
        await gitlab_oauth.exchange_code(code=code, state=state, uid=user.uid)
    except gitlab_oauth.StateError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except gitlab_oauth.ExchangeError:
        # Provider-side failure mid-dance: land on settings with an honest
        # flag (the page renders the retry affordance), details in the log.
        return _settings_redirect("error")
    return _settings_redirect("connected")


class GitLabStatusResponse(BaseModel):
    connected: bool
    username: str | None = None


@router.get("/status", response_model=GitLabStatusResponse)
async def status(user: Annotated[AuthedUser, Depends(require_user)]) -> GitLabStatusResponse:
    profile = await get_profile_store().get(user.uid)
    connection = profile.gitlab if profile is not None else None
    if connection is None:
        return GitLabStatusResponse(connected=False)
    return GitLabStatusResponse(connected=True, username=connection.username)


@router.delete("/connection", status_code=204)
async def disconnect(user: Annotated[AuthedUser, Depends(require_user)]) -> None:
    await gitlab_oauth.disconnect(user.uid)


class GitLabProject(BaseModel):
    id: int
    path_with_namespace: str


class GitLabProjectsResponse(BaseModel):
    projects: list[GitLabProject]


@router.get("/projects", response_model=GitLabProjectsResponse)
async def projects(
    user: Annotated[AuthedUser, Depends(require_user)],
) -> GitLabProjectsResponse:
    try:
        token = await gitlab_oauth.get_valid_access_token(user.uid)
    except (gitlab_oauth.NotConnectedError, gitlab_oauth.ConnectionExpiredError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except gitlab_oauth.GitLabUnavailableError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    try:
        rows: list[dict[str, Any]] = await gitlab_api.list_projects(token)
    except Exception as exc:
        _log.error("gitlab_projects_list_failed", uid=user.uid, exc_info=True)
        raise HTTPException(
            status_code=502, detail=f"GitLab project listing failed: {type(exc).__name__}"
        ) from exc
    return GitLabProjectsResponse(projects=[GitLabProject(**row) for row in rows])


__all__ = ["router"]
