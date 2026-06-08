"""FastAPI entrypoint for chaoslab-agent (Phoenix Audit orchestrator).

S4.1 scope: scaffold the 4 endpoints (/run, /stream, /health, /agents/{id}) + an
in-process RunRegistry. The orchestrator pipeline itself (SequentialAgent: Injector
→ Judge → Patcher) lands in S4.2; for this story /run records the request and /stream
emits a hello frame + heartbeat.
"""

from __future__ import annotations

import asyncio
import secrets
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from chaoslab_agent.config import get_settings

# --- Schemas ----------------------------------------------------------------


class RunRequest(BaseModel):
    """POST /run body — minimal contract for S4.1; Epic 4's S4.2 wires the orchestrator."""

    target_url: str = Field(..., description="Reachable URL for the target agent under audit.")
    agent_id: str | None = Field(
        default=None, description="Optional pre-registered target id; falls back to target_url."
    )
    fault_seed: int | None = Field(
        default=None, description="Optional RNG seed for deterministic probe ordering."
    )
    repetitions: int = Field(
        default=25, ge=1, le=100, description="Baseline repetitions before fault injection."
    )


class RunResponse(BaseModel):
    run_id: str
    sse_url: str
    created_at: str


class HealthResponse(BaseModel):
    status: Literal["ok"]
    version: str
    judge_llm: str
    phoenix_provider: Literal["phoenix-audit", "customer"]


class AgentSpec(BaseModel):
    """Placeholder spec — Epic 3's adapter layer ships the real registry."""

    agent_id: str
    url: str
    framework: Literal["adk-a2a", "langchain-http", "crewai-http", "openai-agents", "http-blackbox"]
    registered_at: str


# --- In-process registries (single-tenant per ADR-003) -----------------------


class _RunState(BaseModel):
    run_id: str
    request: RunRequest
    created_at: str
    status: Literal["pending", "running", "succeeded", "failed"] = "pending"


_RUN_REGISTRY: dict[str, _RunState] = {}

# Demo target — Epic 3 replaces with the real cross-framework adapter registry.
_AGENT_REGISTRY: dict[str, AgentSpec] = {
    "demo-target": AgentSpec(
        agent_id="demo-target",
        url="http://localhost:8001",
        framework="adk-a2a",
        registered_at="2026-06-08T00:00:00Z",
    ),
}


def _iso_now() -> str:
    """RFC-3339 UTC timestamp. Pulled out for test patching."""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _new_run_id() -> str:
    """`run_` + 12 hex chars. Format gated by the test regex `^run_[a-z0-9]{12}$`."""
    return "run_" + secrets.token_hex(6)


# --- App lifecycle ----------------------------------------------------------


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Observability setup lands in S4.5 — for S4.1 we import-and-call with a fallback.
    # ty: chaoslab_agent.observability is created in S4.5; the ImportError fallback
    # is the documented S4.1 contract.
    try:  # pragma: no cover — S4.5 wires this for real
        from chaoslab_agent.observability import setup_logging  # ty: ignore[unresolved-import]

        setup_logging()
    except ImportError:
        pass
    yield


app: FastAPI = FastAPI(
    title="chaoslab-agent",
    description="Phoenix Audit orchestrator (S4.1 scaffold).",
    version=get_settings().service_version,
    lifespan=_lifespan,
)


# --- Endpoints --------------------------------------------------------------


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    s = get_settings()
    return HealthResponse(
        status="ok",
        version=s.service_version,
        judge_llm=s.judge_llm,
        phoenix_provider=s.phoenix_provider,
    )


@app.post("/run", response_model=RunResponse, status_code=201)
async def start_run(payload: RunRequest, request: Request) -> RunResponse:
    run_id = _new_run_id()
    created = _iso_now()
    _RUN_REGISTRY[run_id] = _RunState(run_id=run_id, request=payload, created_at=created)
    # SSE URL is relative; the frontend resolves against the agent's base URL.
    return RunResponse(run_id=run_id, sse_url=f"/stream?runId={run_id}", created_at=created)


@app.get("/stream")
async def stream(runId: str) -> EventSourceResponse:  # noqa: N803 — query-param case fixed by frontend contract
    if runId not in _RUN_REGISTRY:
        raise HTTPException(status_code=404, detail=f"run_id not found: {runId}")

    async def _events() -> AsyncIterator[dict[str, Any]]:
        # Hello frame — clients use this to confirm the stream is open.
        yield {
            "event": "hello",
            "data": f'{{"run_id":"{runId}","status":"connected"}}',
        }
        # Heartbeat loop — S4.2 replaces this with the real orchestrator phase events.
        for _ in range(3):
            await asyncio.sleep(0.05)
            yield {"event": "heartbeat", "data": f'{{"run_id":"{runId}"}}'}

    return EventSourceResponse(_events())


@app.get("/agents/{agent_id}", response_model=AgentSpec)
async def get_agent(agent_id: str) -> AgentSpec:
    spec = _AGENT_REGISTRY.get(agent_id)
    if spec is None:
        raise HTTPException(status_code=404, detail=f"agent_id not found: {agent_id}")
    return spec


# --- CLI entrypoint ---------------------------------------------------------


def run_uvicorn() -> None:  # pragma: no cover
    """Console-script entrypoint: `chaoslab-agent` runs uvicorn against the FastAPI app."""
    import uvicorn

    uvicorn.run("chaoslab_agent.main:app", host="0.0.0.0", port=8080, reload=False)  # noqa: S104 — Cloud Run requires 0.0.0.0


run = (
    run_uvicorn  # alias so `[project.scripts] chaoslab-agent = "chaoslab_agent.main:run"` resolves
)
