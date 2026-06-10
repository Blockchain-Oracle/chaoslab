"""FastAPI entrypoint for phoenix-audit-agent (Phoenix Audit orchestrator).

Endpoints: `/health`, `/run`, `/stream` (SSE), `/agents/{id}`.

`POST /run` spawns a background `asyncio.Task` that drives the REAL audit
pipeline (`phoenix_audit_agent.audit_runner.drive_audit`: Injector -> Judge ->
Patcher against the live target) and pushes its event frames — phase_change,
test_started/test_completed, test_verdict, cluster_set, recipe, complete —
into a per-run `asyncio.Queue`. `GET /stream` drains the queue as SSE frames;
closing the client cancels the background task.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import secrets
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, Literal, cast

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from sse_starlette.sse import EventSourceResponse

from phoenix_audit_agent.api.agents import router as agents_router
from phoenix_audit_agent.api.runs import router as runs_router
from phoenix_audit_agent.audit_runner import drive_audit
from phoenix_audit_agent.config import GCS_PROBE_ENV_NAME, get_settings
from phoenix_audit_agent.storage.models import RunRecord, RunSource
from phoenix_audit_agent.storage.runs import create_run_record

logger = logging.getLogger(__name__)

# Sentinel pushed onto a run's queue to signal the producer is done; /stream
# stops draining when it sees this.
_QUEUE_SENTINEL: None = None

# How long to keep finished run state in the registries before sweeping it out
# (in seconds). Queues are consumed-once (no replay): the window lets a client
# that hasn't connected yet drain the buffered frames of a just-finished run.
# Reconnects after the queue is drained get a terminal `stream_end` frame.
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
    runs_per_fault: int = Field(
        default=2,
        ge=1,
        le=20,
        description="Attacks per fault class (4 classes -> total = 4x this).",
    )
    source: RunSource = Field(
        default="manual",
        description="manual (operator-initiated) or scheduled (monitoring tick).",
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


def _iso_now() -> str:
    """RFC-3339 UTC timestamp."""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _new_run_id() -> str:
    """`run_` + 12 hex chars (48 bits). Format gated by `^run_[a-z0-9]{12}$`."""
    return "run_" + secrets.token_hex(6)


async def _drive_orchestrator(run_id: str) -> None:
    """Frame plumbing around the REAL audit pipeline (audit_runner.drive_audit).

    Owns: per-run queue framing (event name + JSON data), phase bookkeeping on
    the registry, cancellation + failure frames, and the queue sentinel. The
    pipeline itself — Injector -> Judge -> Patcher against the live target —
    lives in `phoenix_audit_agent.audit_runner`. Tests monkeypatch either this
    function (route-level fixtures) or `drive_audit` (frame-plumbing coverage).
    """
    # Registry lookups outside the try block — a missing run_id is a programmer
    # error (task scheduled before registration), not an orchestrator failure;
    # let it crash the task rather than surface as a user-facing SSE error frame.
    state = _RUN_REGISTRY[run_id]
    queue = _RUN_QUEUES[run_id]

    async def emit(event: str, payload: dict[str, Any]) -> None:
        await queue.put({"event": event, "data": json.dumps(payload)})
        # Cooperative yield so /stream gets scheduled at least once between
        # frames — NOT a backpressure guarantee (the queue is unbounded).
        await asyncio.sleep(0)

    def set_phase(phase: str) -> None:
        # _RunState has validate_assignment=True; a value outside the RunPhase
        # Literal raises here instead of corrupting the frontend discriminator.
        state.phase = cast(RunPhase, phase)

    try:
        await drive_audit(
            run_id=run_id,
            target_url=state.request.target_url,
            runs_per_fault=state.request.runs_per_fault,
            emit=emit,
            set_phase=set_phase,
            created_at=state.created_at,
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
    # Observability is mandatory now (S4.5 lands the module + Phoenix register).
    # ANY error inside setup propagates by design — silent observability loss on
    # a compliance product is unacceptable.
    from phoenix_audit_agent.observability import setup_logging, setup_phoenix_otel
    from phoenix_audit_agent.patcher.markdown_emitter import MarkdownEmitter

    settings = get_settings()
    setup_logging(env=settings.environment)
    setup_phoenix_otel(settings)
    # Probe the recipe-artifact bucket so a missing bucket / IAM gap fails
    # at boot instead of mid-demo. Same fail-loud posture as observability:
    # a Markdown URL the Receipt card cannot produce is a broken demo.
    # GCS_PROBE_AT_STARTUP=false is the documented test-only escape hatch
    # (Dockerfile smoke test); the WARNING below names the env var so any
    # accidental prod set is grep-able in Cloud Logging.
    if settings.GCS_PROBE_AT_STARTUP:
        await MarkdownEmitter().health_check()
    else:
        # CRITICAL (not WARNING): a Cloud Logging sink that filters WARNING
        # would silently swallow this, defeating the audit trail. CRITICAL is
        # surfaced by every default sink even on aggressive filter policies.
        # The env var name is interpolated from the shared constant — a rename
        # in config.py crashloops at module load via the drift check there.
        logger.critical(
            "%s=false — Markdown emitter bucket probe skipped at boot. "
            "THIS SHOULD NEVER BE SET IN PRODUCTION; recipe artifacts may fail at /run "
            "time instead of fail-loud at startup.",
            GCS_PROBE_ENV_NAME,
        )
    yield


app: FastAPI = FastAPI(
    title="phoenix-audit-agent",
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
    # Write-through to the registry index (contained — a Firestore outage must
    # never block an audit; finalize at run end heals a failed create).
    await create_run_record(
        RunRecord(
            run_id=run_id,
            agent_id=payload.agent_id,
            target_url=payload.target_url,
            source=payload.source,
            created_at=created,
        )
    )
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
                    # Reconnect after the run finished: the queue was already
                    # drained (sentinel consumed by the first consumer), so
                    # without this the generator ticks forever while the
                    # chamber shows "connected". Frames are enqueued before
                    # the task completes, so done-task + empty queue means
                    # there is nothing left to deliver — say so and close.
                    task = _RUN_TASKS.get(runId)
                    if (task is None or task.done()) and queue.empty():
                        state = _RUN_REGISTRY.get(runId)
                        yield {
                            "event": "stream_end",
                            "data": json.dumps(
                                {
                                    "run_id": runId,
                                    "phase": state.phase if state else "unknown",
                                    "reason": "events_already_consumed",
                                }
                            ),
                        }
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


app.include_router(runs_router)
app.include_router(agents_router)


def run_uvicorn() -> None:
    """Console-script entry: read `$PORT` / `$HOST` so Cloud Run + local dev share one code path."""
    import uvicorn

    port_raw = os.environ.get("PORT", "8080")
    try:
        port = int(port_raw)
    except ValueError as e:
        msg = f"phoenix-audit-agent: PORT env var must be an integer, got {port_raw!r}"
        raise SystemExit(msg) from e
    host = os.environ.get("HOST", "0.0.0.0")  # noqa: S104 — Cloud Run requires 0.0.0.0
    uvicorn.run("phoenix_audit_agent.main:app", host=host, port=port, reload=False)
