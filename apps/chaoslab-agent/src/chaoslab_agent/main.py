"""FastAPI entrypoint for chaoslab-agent (Phoenix Audit orchestrator).

Endpoints: `/health`, `/run`, `/stream` (SSE), `/agents/{id}`.

`POST /run` spawns a background `asyncio.Task` that drives the SequentialAgent
pipeline (Injector -> Judge -> Patcher) and pushes `phase_change` events into a
per-run `asyncio.Queue`. `GET /stream` drains the queue as SSE frames; closing
the client cancels the background task.
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
from pydantic import BaseModel, ConfigDict, Field
from sse_starlette.sse import EventSourceResponse

from chaoslab_agent.config import get_settings

logger = logging.getLogger(__name__)

# Sentinel pushed onto a run's queue to signal the producer is done; /stream
# stops draining when it sees this.
_QUEUE_SENTINEL: None = None

# How long to keep finished run state in the registries before sweeping it out
# (in seconds). A /stream client may still be replaying a just-finished run, so
# the registry isn't dropped immediately on task completion.
_RUN_CLEANUP_DELAY_SEC = 300.0

RunPhase = Literal["queued", "injector", "judge", "patcher", "succeeded", "failed"]


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
    # validate_assignment=True enforces the RunPhase Literal at runtime — without it,
    # a typo'd `state.phase = "injecter"` slips past pydantic and breaks the frontend's
    # phase-discriminator silently.
    model_config = ConfigDict(validate_assignment=True)

    run_id: str
    request: RunRequest
    created_at: str
    phase: RunPhase = "queued"


# In-process registries. The current Cloud Run config (story-4.6) sets
# `--min-instances=1 --max-instances=3`, so registry state CAN split across
# pods; `/stream` 404s on a wrong-pod request are indistinguishable from
# "run evicted." Single-replica enforcement is deferred work — until then,
# sticky-routing or external state is the next correctness step.
_RUN_REGISTRY: dict[str, _RunState] = {}
_RUN_QUEUES: dict[str, asyncio.Queue[dict[str, Any] | None]] = {}
_RUN_TASKS: dict[str, asyncio.Task[None]] = {}

# Demo target — a hardcoded seed for `/agents/{id}` resolution. The real
# cross-framework adapter registry is the responsibility of Epic 3.
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


_ORCHESTRATOR_PHASES: tuple[RunPhase, ...] = ("injector", "judge", "patcher")


async def _drive_orchestrator(run_id: str) -> None:
    """Background coroutine that walks the SequentialAgent phases for a run.

    Currently a deterministic phase walker (Injector -> Judge -> Patcher) emitting
    `phase_change` SSE frames; the real `InMemoryRunner(build_orchestrator())` wiring
    is the next swap-in. Tests monkeypatch this function directly to simulate phase
    transitions without spinning up the real Gemini-backed orchestrator.
    """
    # Registry lookups outside the try block — a missing run_id is a programmer
    # error (task scheduled before registration), not an orchestrator failure;
    # let it crash the task rather than surface as a user-facing SSE error frame.
    state = _RUN_REGISTRY[run_id]
    queue = _RUN_QUEUES[run_id]
    try:
        for phase in _ORCHESTRATOR_PHASES:
            state.phase = phase
            await queue.put(
                {
                    "event": "phase_change",
                    "data": json.dumps({"phase": phase, "run_id": run_id}),
                }
            )
            # Cooperative yield so /stream gets scheduled at least once between
            # phases under InMemoryRunner — NOT a backpressure guarantee (the queue
            # is unbounded).
            await asyncio.sleep(0)
        state.phase = "succeeded"
        await queue.put(
            {
                "event": "complete",
                "data": json.dumps({"phase": "succeeded", "run_id": run_id}),
            }
        )
    except asyncio.CancelledError:
        state.phase = "failed"
        # put_nowait so re-entrant CancelledError on the next await can't suppress
        # the cancelled frame or sentinel; queue is unbounded so put_nowait is safe.
        queue.put_nowait({"event": "cancelled", "data": json.dumps({"run_id": run_id})})
        queue.put_nowait(_QUEUE_SENTINEL)
        raise
    except Exception as e:
        state.phase = "failed"
        logger.exception("orchestrator_failed run_id=%s", run_id)
        queue.put_nowait(
            {
                "event": "error",
                "data": json.dumps({"run_id": run_id, "detail": repr(e)}),
            }
        )
        queue.put_nowait(_QUEUE_SENTINEL)
        return
    queue.put_nowait(_QUEUE_SENTINEL)


def _schedule_run_cleanup(run_id: str, delay: float = _RUN_CLEANUP_DELAY_SEC) -> None:
    """Sweep a run's registry/queue/task entries `delay` seconds after the task ends.

    /stream consumers that haven't reconnected within the window lose access to the
    replay; the trade-off prevents unbounded growth in `_RUN_REGISTRY` / `_RUN_QUEUES`
    on a long-lived Cloud Run instance.
    """
    loop = asyncio.get_running_loop()

    def _sweep() -> None:
        _RUN_REGISTRY.pop(run_id, None)
        _RUN_QUEUES.pop(run_id, None)
        _RUN_TASKS.pop(run_id, None)

    loop.call_later(delay, _sweep)


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Observability boot policy: if the observability module is absent, log degraded
    # mode and continue (compliance product still serves /run + /audit). If present,
    # ANY error inside setup_logging() propagates by design — silent observability
    # loss on the hot path of a compliance product is unacceptable.
    if importlib.util.find_spec("chaoslab_agent.observability") is not None:
        from chaoslab_agent.observability import setup_logging  # ty: ignore[unresolved-import]

        setup_logging()
    else:
        logger.info("observability_degraded reason=module_absent")
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
    _RUN_QUEUES[run_id] = asyncio.Queue()
    task = asyncio.create_task(_drive_orchestrator(run_id))
    task.add_done_callback(lambda _t: _schedule_run_cleanup(run_id))
    _RUN_TASKS[run_id] = task
    return RunResponse(run_id=run_id, sse_url=f"/stream?runId={run_id}", created_at=created)


@app.get("/stream")
async def stream(
    runId: str,  # noqa: N803 — camelCase preserved by frontend SSE/EventSource contract
    request: Request,
) -> EventSourceResponse:
    if runId not in _RUN_REGISTRY:
        logger.warning("stream_404 run_id=%s known_runs=%d", runId, len(_RUN_REGISTRY))
        raise HTTPException(status_code=404, detail=f"run_id not found: {runId}")

    queue = _RUN_QUEUES[runId]

    async def _events() -> AsyncIterator[dict[str, Any]]:
        try:
            yield {"event": "hello", "data": json.dumps({"run_id": runId, "status": "connected"})}
            while True:
                # 0.5s timeout = disconnect-check tick; balances responsiveness vs. wakeup cost.
                try:
                    frame = await asyncio.wait_for(queue.get(), timeout=0.5)
                except TimeoutError:
                    if await request.is_disconnected():
                        _cancel_task(runId)
                        return
                    continue
                if frame is _QUEUE_SENTINEL:
                    return
                yield frame
        except asyncio.CancelledError:
            logger.info("sse_client_disconnect run_id=%s", runId)
            _cancel_task(runId)
            raise
        except Exception:
            logger.exception("sse_stream_failed run_id=%s", runId)
            raise

    return EventSourceResponse(_events())


def _cancel_task(run_id: str) -> None:
    """Cancel a run's background orchestrator task if still in-flight (idempotent)."""
    task = _RUN_TASKS.get(run_id)
    if task is not None and not task.done():
        task.cancel()


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
