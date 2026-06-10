"""POST/GET /agents — the target-agent registry API."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from phoenix_audit_agent._time import utc_now_iso
from phoenix_audit_agent.api._url_guard import validate_target_url
from phoenix_audit_agent.api.auth import AuthedUser, require_user
from phoenix_audit_agent.storage.agents import get_agent_store
from phoenix_audit_agent.storage.models import AgentRecord, Framework

router = APIRouter()


class AgentRegisterRequest(BaseModel):
    agent_id: str = Field(min_length=1, pattern=r"^[a-zA-Z0-9_\-]+$")
    name: str = Field(min_length=1)
    url: str = Field(min_length=1)
    framework: Framework
    tier: int = Field(ge=1, le=3)

    @field_validator("url")
    @classmethod
    def _guard_url(cls, v: str) -> str:
        return validate_target_url(v)


class AgentListResponse(BaseModel):
    agents: list[AgentRecord]


@router.post("/agents", response_model=AgentRecord, status_code=201)
async def register_agent(
    payload: AgentRegisterRequest, user: Annotated[AuthedUser, Depends(require_user)]
) -> AgentRecord:
    if payload.agent_id == "demo-target":
        # The seed shadows reads of this id — a successful 201 would write a
        # record nobody can ever read back.
        raise HTTPException(status_code=409, detail="agent_id 'demo-target' is reserved")
    store = get_agent_store()
    if await store.get(payload.agent_id) is not None:
        # `register` uses set() semantics — without this check a re-register
        # silently overwrites the regulator-facing registry record.
        raise HTTPException(
            status_code=409, detail=f"agent_id already registered: {payload.agent_id}"
        )
    record = AgentRecord(**payload.model_dump(), registered_at=utc_now_iso(), owner_uid=user.uid)
    await store.register(record)
    return record


@router.get("/agents", response_model=AgentListResponse)
async def list_agents(user: Annotated[AuthedUser, Depends(require_user)]) -> AgentListResponse:
    rows = await get_agent_store().list_agents()
    # Own + ownerless (the demo seed and pre-auth records) stay visible.
    return AgentListResponse(agents=[a for a in rows if a.owner_uid in (None, user.uid)])


@router.get("/agents/{agent_id}", response_model=AgentRecord)
async def get_agent(
    agent_id: str, user: Annotated[AuthedUser, Depends(require_user)]
) -> AgentRecord:
    record = await get_agent_store().get(agent_id)
    # Foreign-owned reads as not-found — a 403 would CONFIRM the id exists.
    if record is None or record.owner_uid not in (None, user.uid):
        raise HTTPException(status_code=404, detail=f"agent_id not found: {agent_id}")
    return record


__all__ = ["router"]
