"""FastAPI entrypoint for chaoslab-agent (Phoenix Audit orchestrator).

Endpoints: `/health`, `/run`, `/stream` (SSE), `/agents/{id}`.

`/stream` emits a `hello` frame and a heartbeat placeholder; the real orchestrator
overwrites the placeholder by pushing `phase_change` events into the run's queue.
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import logging
import os
import secrets
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from chaoslab_agent.config import get_settings

logger = logging.getLogger(__name__)


class RunRequest(BaseModel):
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
    agent_id: str
    url: str
    framework: Literal["adk-a2a", "langchain-http", "crewai-http", "openai-agents", "http-blackbox"]
    registered_at: str


class _RunState(BaseModel):
    run_id: str
    request: RunRequest
    created_at: str
    status: Literal["pending", "running", "succeeded", "failed"] = "pending"


# In-process registries — Cloud Run min-instances=1 / max-instances=1 keeps this
# single-replica. A multi-replica deploy would silently split state across pods;
# `/stream` 404s would be indistinguishable from "evicted." See ADR-017 + the
# follow-up tracking issue.
_RUN_REGISTRY: dict[str, _RunState] = {}

# Demo target — replaced by the real cross-framework adapter registry.
_AGENT_REGISTRY: dict[str, AgentSpec] = {
    "demo-target": AgentSpec(
        agent_id="demo-target",
        url="http://localhost:8001",
        framework="adk-a2a",
        registered_at="2026-06-08T00:00:00Z",
    ),
}


def _iso_now() -> str:
    """RFC-3339 UTC timestamp."""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _new_run_id() -> str:
    """`run_` + 12 hex chars (48 bits). Format gated by `^run_[a-z0-9]{12}$`."""
    return "run_" + secrets.token_hex(6)


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Observability is best-effort during boot: a missing setup_logging() must not
    # crash the app (degraded path). Once `chaoslab_agent.observability` ships,
    # fail loud if its setup raises — we never want silent observability loss on
    # the hot path of a compliance product.
    if importlib.util.find_spec("chaoslab_agent.observability") is not None:
        from chaoslab_agent.observability import setup_logging  # ty: ignore[unresolved-import]

        setup_logging()
    else:
        logger.info("observability module not yet wired; tracing/logging in degraded mode")
    yield


app: FastAPI = FastAPI(
    title="chaoslab-agent",
    description="Phoenix Audit orchestrator.",
    version=get_settings().service_version,
    lifespan=_lifespan,
)


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
async def start_run(payload: RunRequest) -> RunResponse:
    run_id = _new_run_id()
    created = _iso_now()
    _RUN_REGISTRY[run_id] = _RunState(run_id=run_id, request=payload, created_at=created)
    return RunResponse(run_id=run_id, sse_url=f"/stream?runId={run_id}", created_at=created)


@app.get("/stream")
async def stream(runId: str, request: Request) -> EventSourceResponse:  # noqa: N803
    if runId not in _RUN_REGISTRY:
        logger.warning("stream_404 run_id=%s known_runs=%d", runId, len(_RUN_REGISTRY))
        raise HTTPException(status_code=404, detail=f"run_id not found: {runId}")

    async def _events() -> AsyncIterator[dict[str, Any]]:
        try:
            yield {"event": "hello", "data": json.dumps({"run_id": runId, "status": "connected"})}
            for _ in range(3):
                if await request.is_disconnected():
                    return
                await asyncio.sleep(0.05)
                yield {"event": "heartbeat", "data": json.dumps({"run_id": runId})}
        except asyncio.CancelledError:
            logger.info("sse_client_disconnect run_id=%s", runId)
            raise
        except Exception:
            logger.exception("sse_stream_failed run_id=%s", runId)
            raise

    return EventSourceResponse(_events())


@app.get("/agents/{agent_id}", response_model=AgentSpec)
async def get_agent(agent_id: str) -> AgentSpec:
    spec = _AGENT_REGISTRY.get(agent_id)
    if spec is None:
        raise HTTPException(status_code=404, detail=f"agent_id not found: {agent_id}")
    return spec


def run_uvicorn() -> None:
    """Console-script entry: read `$PORT` / `$HOST` so Cloud Run + local dev share one code path."""
    import uvicorn

    port_raw = os.environ.get("PORT", "8080")
    try:
        port = int(port_raw)
    except ValueError as e:
        msg = f"chaoslab-agent: PORT env var must be an integer, got {port_raw!r}"
        raise SystemExit(msg) from e
    host = os.environ.get("HOST", "0.0.0.0")  # noqa: S104 — Cloud Run requires 0.0.0.0
    uvicorn.run("chaoslab_agent.main:app", host=host, port=port, reload=False)
