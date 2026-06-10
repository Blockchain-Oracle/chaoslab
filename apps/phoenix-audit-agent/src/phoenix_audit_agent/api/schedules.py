"""Monitoring schedules CRUD + the OIDC-gated scheduler tick endpoint."""

from __future__ import annotations

import secrets
import time
from collections.abc import Awaitable, Callable
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field

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


class SchedulePatch(BaseModel):
    enabled: bool | None = None
    cadence: Cadence | None = None
    deliver_email: bool | None = None
    email_recipient: EmailStr | None = None


class ScheduleListResponse(BaseModel):
    schedules: list[ScheduleRecord]


def _iso_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime())


@router.post("/schedules", response_model=ScheduleRecord, status_code=201)
async def create_schedule(payload: ScheduleCreate) -> ScheduleRecord:
    record = ScheduleRecord(
        schedule_id="sch_" + secrets.token_hex(6),
        # next_fire_at = now → the schedule fires on the next tick.
        next_fire_at=_iso_now(),
        created_at=_iso_now(),
        **payload.model_dump(),
    )
    await get_schedule_store().upsert(record)
    return record


@router.get("/schedules", response_model=ScheduleListResponse)
async def list_schedules() -> ScheduleListResponse:
    return ScheduleListResponse(schedules=await get_schedule_store().list_schedules())


@router.patch("/schedules/{schedule_id}", response_model=ScheduleRecord)
async def patch_schedule(schedule_id: str, payload: SchedulePatch) -> ScheduleRecord:
    store = get_schedule_store()
    record = await store.get(schedule_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"schedule not found: {schedule_id}")
    updated = record.model_copy(update=payload.model_dump(exclude_none=True))
    await store.upsert(updated)
    return updated


def verify_tick_oidc(authorization: str | None) -> dict[str, Any]:
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
        from google.auth.transport import requests as ga_requests
        from google.oauth2 import id_token

        claims = id_token.verify_oauth2_token(token, ga_requests.Request(), audience=audience)
    except Exception as err:
        raise HTTPException(status_code=401, detail=f"invalid token: {type(err).__name__}") from err
    if claims.get("email") != allowed_email or claims.get("email_verified") is not True:
        raise HTTPException(status_code=403, detail="caller is not the scheduler invoker")
    return claims


@router.post("/internal/scheduler-tick", response_model=TickResult)
async def scheduler_tick(request: Request) -> TickResult:
    verify_tick_oidc(request.headers.get("authorization"))
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
