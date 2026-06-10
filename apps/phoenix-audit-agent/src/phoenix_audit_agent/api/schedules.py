"""Monitoring schedules CRUD + the OIDC-gated scheduler tick endpoint."""

from __future__ import annotations

import asyncio
import secrets
from collections.abc import Awaitable, Callable
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from google.auth.transport import requests as ga_requests
from google.oauth2 import id_token
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from phoenix_audit_agent._time import utc_now_iso
from phoenix_audit_agent.api._url_guard import validate_target_url
from phoenix_audit_agent.api.auth import AuthedUser, require_user
from phoenix_audit_agent.config import get_settings
from phoenix_audit_agent.scheduler.tick import TickResult, run_tick
from phoenix_audit_agent.storage.models import Cadence, ScheduleRecord
from phoenix_audit_agent.storage.schedules import get_schedule_store

_log = structlog.get_logger(__name__)

router = APIRouter()

# Injected by main.py after launch_run is defined (avoids a circular import).
# schedule -> run_id
_LAUNCHER: Callable[[ScheduleRecord], Awaitable[str]] | None = None


def set_run_launcher(fn: Callable[[ScheduleRecord], Awaitable[str]]) -> None:
    global _LAUNCHER  # noqa: PLW0603 — wired once at app assembly
    _LAUNCHER = fn


class ScheduleCreate(BaseModel):
    agent_id: str | None = None
    target_url: str = Field(min_length=1)
    cadence: Cadence = "daily"
    enabled: bool = True
    deliver_email: bool = False
    email_recipient: EmailStr | None = None

    @field_validator("target_url")
    @classmethod
    def _guard_target_url(cls, v: str) -> str:
        return validate_target_url(v)

    @model_validator(mode="after")
    def _email_contract(self) -> ScheduleCreate:
        if self.deliver_email and self.email_recipient is None:
            msg = "deliver_email=true requires email_recipient"
            raise ValueError(msg)
        return self


class SchedulePatch(BaseModel):
    enabled: bool | None = None
    cadence: Cadence | None = None
    deliver_email: bool | None = None
    email_recipient: EmailStr | None = None


class ScheduleListResponse(BaseModel):
    schedules: list[ScheduleRecord]


@router.post("/schedules", response_model=ScheduleRecord, status_code=201)
async def create_schedule(
    payload: ScheduleCreate, user: Annotated[AuthedUser, Depends(require_user)]
) -> ScheduleRecord:
    record = ScheduleRecord(
        schedule_id="sch_" + secrets.token_hex(6),
        # next_fire_at = now → the schedule fires on the next tick.
        next_fire_at=utc_now_iso(),
        created_at=utc_now_iso(),
        owner_uid=user.uid,
        **payload.model_dump(),
    )
    await get_schedule_store().upsert(record)
    return record


@router.get("/schedules", response_model=ScheduleListResponse)
async def list_schedules(
    user: Annotated[AuthedUser, Depends(require_user)],
) -> ScheduleListResponse:
    rows = await get_schedule_store().list_schedules()
    # Own + ownerless (pre-auth records) stay visible.
    return ScheduleListResponse(schedules=[s for s in rows if s.owner_uid in (None, user.uid)])


@router.patch("/schedules/{schedule_id}", response_model=ScheduleRecord)
async def patch_schedule(
    schedule_id: str, payload: SchedulePatch, user: Annotated[AuthedUser, Depends(require_user)]
) -> ScheduleRecord:
    store = get_schedule_store()
    record = await store.get(schedule_id)
    # WRITES require exact ownership — legacy ownerless records stay readable
    # (evidence must not vanish) but immutable: sign-ups are open to the
    # internet, so owner_uid=None must not mean world-writable. Foreign and
    # ownerless both read as not-found (a 403 would CONFIRM the id exists).
    if record is None or record.owner_uid != user.uid:
        raise HTTPException(status_code=404, detail=f"schedule not found: {schedule_id}")
    fields = payload.model_dump(exclude_none=True)
    merged = record.model_copy(update=fields)
    if merged.deliver_email and merged.email_recipient is None:
        # Same contract as ScheduleCreate — PATCH must not be a side door into
        # a delivery promise with no recipient.
        raise HTTPException(status_code=422, detail="deliver_email=true requires email_recipient")
    if fields:
        # Partial update of ONLY the patched keys — a full upsert here raced
        # the tick's claim and could write back a stale next_fire_at.
        await store.patch_fields(schedule_id, fields)
    refreshed = await store.get(schedule_id)
    if refreshed is None:
        # Deleted between the existence check and the refresh — fabricating a
        # response from the stale copy would confirm a patch on a record that
        # no longer exists.
        raise HTTPException(status_code=404, detail=f"schedule not found: {schedule_id}")
    return refreshed


# Reused across ticks — carries the Google cert cache; rebuilding it per
# request re-fetches certs on every verification.
_GA_REQUEST = ga_requests.Request()


async def verify_tick_oidc(authorization: str | None) -> dict[str, Any]:
    """Verify the Cloud Scheduler OIDC token. Fails CLOSED on misconfiguration
    — an open tick endpoint would let anyone burn the GCP budget with runs."""
    settings = get_settings()
    audience = settings.SERVICE_BASE_URL
    allowed_email = settings.SCHEDULER_INVOKER_EMAIL
    if not audience or not allowed_email:
        raise HTTPException(
            status_code=503,
            detail=(
                "scheduler tick is not configured: set SERVICE_BASE_URL and "
                "SCHEDULER_INVOKER_EMAIL (fail-closed by design)"
            ),
        )
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    token = authorization.removeprefix("Bearer ")
    try:
        # verify_oauth2_token does blocking I/O (Google cert fetch) — keep it
        # off the event loop so a slow cert endpoint can't stall SSE streams.
        claims = await asyncio.to_thread(id_token.verify_oauth2_token, token, _GA_REQUEST, audience)
    except Exception as err:
        raise HTTPException(status_code=401, detail=f"invalid token: {type(err).__name__}") from err
    if claims.get("email") != allowed_email or claims.get("email_verified") is not True:
        raise HTTPException(status_code=403, detail="caller is not the scheduler invoker")
    return claims


@router.post("/internal/scheduler-tick", response_model=TickResult)
async def scheduler_tick(request: Request) -> TickResult:
    await verify_tick_oidc(request.headers.get("authorization"))
    if _LAUNCHER is None:  # pragma: no cover — wired at app assembly
        raise HTTPException(status_code=503, detail="run launcher not wired")
    result = await run_tick(store=get_schedule_store(), launch=_LAUNCHER)
    _log.info(
        "scheduler_tick",
        claimed=result.claimed,
        launched=len(result.launched),
        launch_failures=result.launch_failures,
    )
    return result


__all__ = ["router", "set_run_launcher", "verify_tick_oidc"]
