"""POST/GET /agents — the target-agent registry API."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

from phoenix_audit_agent._time import utc_now_iso
from phoenix_audit_agent.api._url_guard import validate_target_url
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
async def register_agent(payload: AgentRegisterRequest) -> AgentRecord:
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
    record = AgentRecord(**payload.model_dump(), registered_at=utc_now_iso())
    await store.register(record)
    return record


@router.get("/agents", response_model=AgentListResponse)
async def list_agents() -> AgentListResponse:
    return AgentListResponse(agents=await get_agent_store().list_agents())


@router.get("/agents/{agent_id}", response_model=AgentRecord)
async def get_agent(agent_id: str) -> AgentRecord:
    record = await get_agent_store().get(agent_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"agent_id not found: {agent_id}")
    return record


__all__ = ["router"]
