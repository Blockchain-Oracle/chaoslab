"""POST/GET /agents — the target-agent registry API."""

from __future__ import annotations

import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from phoenix_audit_agent.storage.agents import get_agent_store
from phoenix_audit_agent.storage.models import AgentRecord, Framework

router = APIRouter()


class AgentRegisterRequest(BaseModel):
    agent_id: str = Field(min_length=1, pattern=r"^[a-zA-Z0-9_\-]+$")
    name: str = Field(min_length=1)
    url: str = Field(min_length=1)
    framework: Framework
    tier: int = Field(ge=1, le=3)


class AgentListResponse(BaseModel):
    agents: list[AgentRecord]


@router.post("/agents", response_model=AgentRecord, status_code=201)
async def register_agent(payload: AgentRegisterRequest) -> AgentRecord:
    record = AgentRecord(
        **payload.model_dump(),
        registered_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    )
    await get_agent_store().register(record)
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
