"""FastAPI endpoint tests for chaoslab-agent."""

from __future__ import annotations

import asyncio
import json
import os
import re
from collections.abc import AsyncIterator, Iterator

import httpx
import pytest

from chaoslab_agent.config import JUDGE_LLM_LOCKED, get_settings


def _reset_run_registries() -> None:
    """Cancel in-flight tasks + clear module-level run state.

    Extracted so the autouse fixture below + the `app` fixture below don't
    drift apart. test-quality-reviewer #5 flagged that lifespan-only tests
    skipping the `app` fixture would leave background tasks dangling across
    test boundaries under --randomly-seed; this fixes that at module scope."""
    from chaoslab_agent.main import _RUN_QUEUES, _RUN_REGISTRY, _RUN_TASKS

    for task in _RUN_TASKS.values():
        if not task.done():
            task.cancel()
    _RUN_REGISTRY.clear()
    _RUN_QUEUES.clear()
    _RUN_TASKS.clear()


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch, tmp_path) -> Iterator[None]:
    """Strip inherited PHOENIX_*/GEMINI_*/etc. env so Settings() defaults are deterministic.

    Also resets the module-level run registries — every test in this module
    starts from a clean slate, regardless of which fixtures it requests."""
    for key in list(os.environ):
        if key.startswith(("PHOENIX_", "GEMINI_", "JUDGE_", "TARGET_", "GITLAB_", "GCS_")):
            monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini")
    monkeypatch.chdir(tmp_path)
    get_settings.cache_clear()
    _reset_run_registries()
    yield
    _reset_run_registries()
    get_settings.cache_clear()


@pytest.fixture
def app():
    """FastAPI app instance. Registry cleanup is handled by the autouse `_env`
    fixture; this fixture only resolves the app object so tests don't import."""
    from chaoslab_agent.main import app as fastapi_app

    return fastapi_app


@pytest.fixture
async def client(app) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def test_health_returns_ok_with_version_and_judge(client: httpx.AsyncClient) -> None:
    r = await client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["judge_llm"] == JUDGE_LLM_LOCKED
    assert body["phoenix_provider"] == "phoenix-audit"
    assert "version" in body


async def test_post_run_returns_201_with_run_id_format(client: httpx.AsyncClient) -> None:
    r = await client.post(
        "/run",
        json={"target_url": "http://localhost:8001"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert re.fullmatch(r"^run_[a-z0-9]{12}$", body["run_id"]), body["run_id"]
    assert body["run_id"] in body["sse_url"]
    assert body["created_at"].endswith("Z")


async def test_post_run_missing_target_url_returns_422(client: httpx.AsyncClient) -> None:
    r = await client.post("/run", json={})
    assert r.status_code == 422


@pytest.mark.parametrize(
    ("reps", "expected_status"),
    [(0, 422), (1, 201), (100, 201), (101, 422)],
)
async def test_repetitions_boundaries(
    client: httpx.AsyncClient, reps: int, expected_status: int
) -> None:
    """ge=1, le=100 boundaries — all four corners covered to catch off-by-one drift."""
    r = await client.post(
        "/run",
        json={"target_url": "http://localhost:8001", "repetitions": reps},
    )
    assert r.status_code == expected_status, f"reps={reps}: {r.text}"


async def test_post_run_missing_target_url_envelope_names_field(
    client: httpx.AsyncClient,
) -> None:
    """422 envelope must name target_url so frontend can surface field-specific errors."""
    r = await client.post("/run", json={})
    assert r.status_code == 422
    assert any("target_url" in str(e["loc"]) for e in r.json()["detail"])


async def test_post_run_persists_run_id_to_registry(client: httpx.AsyncClient) -> None:
    """The POST→/stream round-trip depends on _RUN_REGISTRY persistence — verify directly."""
    from chaoslab_agent.main import _RUN_REGISTRY

    r = await client.post(
        "/run",
        json={"target_url": "http://target.example:9000", "repetitions": 5},
    )
    run_id = r.json()["run_id"]
    assert run_id in _RUN_REGISTRY
    state = _RUN_REGISTRY[run_id]
    assert state.request.target_url == "http://target.example:9000"
    assert state.request.repetitions == 5


async def test_post_run_initial_phase_is_queued_or_running(client: httpx.AsyncClient) -> None:
    """Story-4.2 BDD: state.phase must be one of (queued, running, ...) immediately after POST."""
    from chaoslab_agent.main import _RUN_REGISTRY

    r = await client.post("/run", json={"target_url": "http://localhost:8001"})
    run_id = r.json()["run_id"]
    # The background task may race past 'queued' into one of the running phases; both ok.
    valid = {"queued", "injector", "judge", "patcher", "succeeded"}
    assert _RUN_REGISTRY[run_id].phase in valid, _RUN_REGISTRY[run_id].phase


async def test_get_stream_unknown_run_id_returns_404(client: httpx.AsyncClient) -> None:
    r = await client.get("/stream?runId=run_doesnotexist")
    assert r.status_code == 404


async def test_get_stream_known_run_id_emits_hello_event(client: httpx.AsyncClient) -> None:
    run_resp = await client.post("/run", json={"target_url": "http://localhost:8001"})
    run_id = run_resp.json()["run_id"]
    async with client.stream("GET", f"/stream?runId={run_id}") as resp:
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")
        chunks: list[str] = []
        async for chunk in resp.aiter_text():
            chunks.append(chunk)
            if "hello" in chunk:
                break
    joined = "".join(chunks)
    assert "hello" in joined
    assert run_id in joined


async def test_stream_data_frames_are_valid_json(client: httpx.AsyncClient) -> None:
    """SSE `data:` payloads must be json.dumps()-emitted — bare f-strings break on quotes."""
    run_resp = await client.post("/run", json={"target_url": "http://localhost:8001"})
    run_id = run_resp.json()["run_id"]
    chunks: list[str] = []
    async with client.stream("GET", f"/stream?runId={run_id}") as resp:
        async for chunk in resp.aiter_text():
            chunks.append(chunk)
    joined = "".join(chunks)
    data_lines = [
        line.removeprefix("data: ").strip()
        for line in joined.splitlines()
        if line.startswith("data:")
    ]
    assert data_lines, f"no SSE data lines parsed from:\n{joined}"
    for line in data_lines:
        parsed = json.loads(line)  # raises on bare-fstring drift
        assert parsed["run_id"] == run_id


async def test_stream_emits_phase_change_when_phase_transitions(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Story-4.2 BDD: simulated injector->judge transition surfaces as phase_change(phase=judge)."""
    from chaoslab_agent import main as _main

    async def fixture_drive(run_id: str) -> None:
        queue = _main._RUN_QUEUES[run_id]
        # Only emit the judge transition — assert downstream sees this exact frame.
        await queue.put(
            {"event": "phase_change", "data": json.dumps({"phase": "judge", "run_id": run_id})}
        )
        await queue.put(None)

    monkeypatch.setattr(_main, "_drive_orchestrator", fixture_drive)

    run_resp = await client.post("/run", json={"target_url": "http://localhost:8001"})
    run_id = run_resp.json()["run_id"]

    chunks: list[str] = []
    async with client.stream("GET", f"/stream?runId={run_id}") as resp:
        async for chunk in resp.aiter_text():
            chunks.append(chunk)
    joined = "".join(chunks)
    assert "event: phase_change" in joined, joined
    assert '"phase": "judge"' in joined, joined


async def test_cancel_task_cancels_in_flight_drive() -> None:
    """`_cancel_task` is what the /stream disconnect path invokes. Test directly.

    A true end-to-end "client disconnect cancels task" test against httpx.ASGITransport
    deadlocks because the in-process transport never sends a real close-frame; the
    server-side `_events()` generator never gets `CancelledError`. The cancel
    propagation logic itself is a tiny helper we can exercise directly: place a task
    in the registry, call `_cancel_task`, assert it cancels.
    """
    from chaoslab_agent.main import _RUN_TASKS, _cancel_task

    cancelled = asyncio.Event()

    async def slow() -> None:
        try:
            await asyncio.sleep(30)
        except asyncio.CancelledError:
            cancelled.set()
            raise

    task = asyncio.create_task(slow())
    _RUN_TASKS["test_cancel"] = task
    try:
        # Let the task actually start before we cancel it (avoids racing the scheduler).
        await asyncio.sleep(0)
        _cancel_task("test_cancel")
        for _ in range(20):
            if cancelled.is_set():
                break
            await asyncio.sleep(0.05)
        assert cancelled.is_set(), "task did not receive CancelledError"
        assert task.cancelled() or task.done(), "task did not complete after cancel"
    finally:
        _RUN_TASKS.pop("test_cancel", None)


def test_cancel_task_is_idempotent_on_completed_task() -> None:
    """Cancelling an already-done task must be a silent no-op (post-run cleanup path)."""
    from chaoslab_agent.main import _RUN_TASKS, _cancel_task

    async def _done() -> None:
        return

    async def _drive() -> None:
        task = asyncio.create_task(_done())
        await task
        _RUN_TASKS["finished"] = task
        _cancel_task("finished")  # must not raise even though task.done() is True
        _cancel_task("never_existed")  # must not raise for unknown run_id
        _RUN_TASKS.pop("finished", None)

    asyncio.run(_drive())


async def test_stream_emits_full_phase_change_sequence(
    client: httpx.AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pipeline phase walk surfaces as phase_change SSE frames: injector -> judge -> patcher."""
    from chaoslab_agent import main as _main

    monkeypatch.setattr(_main, "drive_audit", _fake_phase_walk_drive)
    run_resp = await client.post("/run", json={"target_url": "http://localhost:8001"})
    run_id = run_resp.json()["run_id"]
    chunks: list[str] = []
    async with client.stream("GET", f"/stream?runId={run_id}") as resp:
        async for chunk in resp.aiter_text():
            chunks.append(chunk)
    joined = "".join(chunks)
    # Each `phase_change` event line appears once per phase, in order.
    inj = joined.find('"phase": "injector"')
    jud = joined.find('"phase": "judge"')
    pat = joined.find('"phase": "patcher"')
    assert -1 < inj < jud < pat, f"phase order broken (inj={inj}, jud={jud}, pat={pat}):\n{joined}"
    assert joined.count("event: phase_change") == 3, joined


async def test_get_agents_known_returns_spec(client: httpx.AsyncClient) -> None:
    r = await client.get("/agents/demo-target")
    assert r.status_code == 200
    body = r.json()
    assert body["agent_id"] == "demo-target"
    assert body["framework"] == "adk-a2a"


async def test_get_agents_unknown_returns_404(client: httpx.AsyncClient) -> None:
    r = await client.get("/agents/no-such-agent")
    assert r.status_code == 404


# --- `_drive_orchestrator` frame-plumbing coverage --------------------------
# These tests exercise the PRODUCTION wrapper (queue framing, error/cancel
# branches, the sentinel) while faking the pipeline seam (`drive_audit`) —
# the real pipeline hits live Gemini/Phoenix/target and is covered by
# tests/unit/test_audit_runner.py with its own seams.


async def _fake_phase_walk_drive(
    *,
    run_id: str,
    target_url: str,
    runs_per_fault: int,
    emit,
    set_phase,
    **_kw,
) -> None:
    """Mirrors drive_audit's frame shape without the real pipeline."""
    for phase in ("injector", "judge", "patcher"):
        set_phase(phase)
        await emit("phase_change", {"phase": phase, "run_id": run_id})
    set_phase("succeeded")
    await emit("complete", {"phase": "succeeded", "run_id": run_id})


async def test_real_drive_emits_complete_frame_and_sets_succeeded_phase(
    client: httpx.AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Production `_drive_orchestrator` happy path: emit `complete` + transition to succeeded."""
    from chaoslab_agent import main as _main
    from chaoslab_agent.main import _RUN_REGISTRY

    monkeypatch.setattr(_main, "drive_audit", _fake_phase_walk_drive)

    run_resp = await client.post("/run", json={"target_url": "http://localhost:8001"})
    run_id = run_resp.json()["run_id"]
    chunks: list[str] = []
    async with client.stream("GET", f"/stream?runId={run_id}") as resp:
        async for chunk in resp.aiter_text():
            chunks.append(chunk)
    joined = "".join(chunks)
    assert "event: complete" in joined, joined
    assert '"phase": "succeeded"' in joined, joined
    assert _RUN_REGISTRY[run_id].phase == "succeeded"


async def test_real_drive_walks_all_four_phase_states(
    client: httpx.AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Registry transitions queued -> injector -> judge -> patcher -> succeeded."""
    from chaoslab_agent import main as _main
    from chaoslab_agent.main import _RUN_REGISTRY

    monkeypatch.setattr(_main, "drive_audit", _fake_phase_walk_drive)

    run_resp = await client.post("/run", json={"target_url": "http://localhost:8001"})
    run_id = run_resp.json()["run_id"]
    # Drain the stream to let the drive complete.
    async with client.stream("GET", f"/stream?runId={run_id}") as resp:
        async for _ in resp.aiter_text():
            pass
    assert _RUN_REGISTRY[run_id].phase == "succeeded"


async def test_real_drive_failure_emits_error_frame_and_logs(
    client: httpx.AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Real `_drive_orchestrator`'s except Exception branch (not the test fixture)."""
    import logging as _logging

    from chaoslab_agent import main as _main

    monkeypatch.setattr(_main, "drive_audit", _fake_phase_walk_drive)

    # Force the drive's frame loop to raise on the second frame by patching
    # asyncio.Queue.put on the real queue.
    original_put = asyncio.Queue.put
    call_n = {"i": 0}

    async def boom_put(self, item):
        call_n["i"] += 1
        if call_n["i"] == 2:  # let the first phase_change land, fail the second
            raise RuntimeError("synthetic-orchestrator-failure")
        return await original_put(self, item)

    monkeypatch.setattr(_main.asyncio.Queue, "put", boom_put)

    with caplog.at_level(_logging.ERROR, logger="chaoslab_agent.main"):
        run_resp = await client.post("/run", json={"target_url": "http://localhost:8001"})
        run_id = run_resp.json()["run_id"]
        chunks: list[str] = []
        async with client.stream("GET", f"/stream?runId={run_id}") as resp:
            async for chunk in resp.aiter_text():
                chunks.append(chunk)

    joined = "".join(chunks)
    assert "event: error" in joined, joined
    assert "synthetic-orchestrator-failure" in joined, joined
    assert any("orchestrator_failed" in r.message for r in caplog.records), [
        r.message for r in caplog.records
    ]
    assert _main._RUN_REGISTRY[run_id].phase == "failed"


async def test_real_drive_cancelled_emits_cancelled_frame_and_marks_failed(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cancelling the real drive task surfaces the `cancelled` SSE frame + phase=failed."""
    from chaoslab_agent import main as _main

    monkeypatch.setattr(_main, "drive_audit", _fake_phase_walk_drive)

    # Slow the first phase_change so cancel can land cleanly mid-drive.
    original_sleep = asyncio.sleep
    sleep_calls = {"n": 0}

    async def slow_sleep(seconds: float) -> None:
        sleep_calls["n"] += 1
        if sleep_calls["n"] == 1:
            await original_sleep(0.5)
        else:
            await original_sleep(seconds)

    monkeypatch.setattr(_main.asyncio, "sleep", slow_sleep)

    run_resp = await client.post("/run", json={"target_url": "http://localhost:8001"})
    run_id = run_resp.json()["run_id"]
    task = _main._RUN_TASKS[run_id]
    await original_sleep(0.05)  # let first phase_change emit
    task.cancel()
    await original_sleep(0.1)

    queue = _main._RUN_QUEUES[run_id]
    frames: list[dict] = []
    while not queue.empty():
        item = queue.get_nowait()
        if item is not None:
            frames.append(item)

    events = [f.get("event") for f in frames]
    assert "cancelled" in events, events
    assert _main._RUN_REGISTRY[run_id].phase == "failed"


async def test_concurrent_runs_generate_distinct_ids(
    client: httpx.AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """48-bit run_id collision is improbable but registry overwrite must not be silent."""
    from chaoslab_agent import main as _main

    monkeypatch.setattr(_main, "drive_audit", _fake_phase_walk_drive)
    payload = {"target_url": "http://localhost:8001"}
    responses = await asyncio.gather(*(client.post("/run", json=payload) for _ in range(50)))
    ids = [r.json()["run_id"] for r in responses]
    assert len(set(ids)) == len(ids), f"duplicate ids: {ids}"


def test_run_uvicorn_honors_port_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cloud Run sets $PORT dynamically — run_uvicorn must read it, not hardcode 8080."""
    monkeypatch.setenv("PORT", "9123")
    monkeypatch.setenv("HOST", "127.0.0.1")
    captured: dict[str, object] = {}

    def fake_uvicorn_run(app_path: str, **kwargs: object) -> None:
        captured["app"] = app_path
        captured.update(kwargs)

    import uvicorn as uv

    monkeypatch.setattr(uv, "run", fake_uvicorn_run)

    from chaoslab_agent.main import run_uvicorn

    run_uvicorn()
    assert captured["host"] == "127.0.0.1"
    assert captured["port"] == 9123


def test_run_uvicorn_rejects_non_integer_port(monkeypatch: pytest.MonkeyPatch) -> None:
    """A garbage $PORT must crash loudly (Cloud Run treats non-zero exit as crashloop)."""
    monkeypatch.setenv("PORT", "not-a-port")

    from chaoslab_agent.main import run_uvicorn

    with pytest.raises(SystemExit, match="must be an integer"):
        run_uvicorn()


async def test_orchestrator_failure_emits_error_frame_and_logs_at_error(
    client: httpx.AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Orchestrator exceptions log `orchestrator_failed` at ERROR + emit an `error` SSE frame."""
    import logging as _logging

    from chaoslab_agent import main as _main

    async def _boom_drive(run_id: str) -> None:
        # Mirror the production drive shape — push the error frame + sentinel — so the
        # stream cleanly terminates instead of hanging on the queue.
        queue = _main._RUN_QUEUES[run_id]
        try:
            raise RuntimeError("synthetic-orchestrator-failure")
        except Exception as e:
            _main.logger.exception("orchestrator_failed run_id=%s", run_id)
            await queue.put(
                {"event": "error", "data": json.dumps({"run_id": run_id, "detail": repr(e)})}
            )
        finally:
            await queue.put(None)

    monkeypatch.setattr(_main, "_drive_orchestrator", _boom_drive)

    run_resp = await client.post("/run", json={"target_url": "http://localhost:8001"})
    run_id = run_resp.json()["run_id"]

    chunks: list[str] = []
    with caplog.at_level(_logging.ERROR, logger="chaoslab_agent.main"):
        async with client.stream("GET", f"/stream?runId={run_id}") as resp:
            async for chunk in resp.aiter_text():
                chunks.append(chunk)

    joined = "".join(chunks)
    assert "event: error" in joined, joined
    assert "synthetic-orchestrator-failure" in joined, joined
    assert any("orchestrator_failed" in r.message for r in caplog.records), [
        r.message for r in caplog.records
    ]


async def test_stream_stops_when_client_disconnects(
    client: httpx.AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`request.is_disconnected()` truthy must short-circuit the heartbeat loop."""
    from starlette.requests import Request

    call_count = {"n": 0}

    async def fake_disconnected(self: Request) -> bool:
        call_count["n"] += 1
        return call_count["n"] >= 2  # first call False (hello frame already past), then True

    monkeypatch.setattr(Request, "is_disconnected", fake_disconnected)

    run_resp = await client.post("/run", json={"target_url": "http://localhost:8001"})
    run_id = run_resp.json()["run_id"]

    chunks: list[str] = []
    async with client.stream("GET", f"/stream?runId={run_id}") as resp:
        async for chunk in resp.aiter_text():
            chunks.append(chunk)
    joined = "".join(chunks)
    assert joined.count("event: heartbeat") < 3, f"disconnect did not short-circuit: {joined!r}"


# ---------------------------------------------------------------------------
# Round-3: verify lifespan wires MarkdownEmitter.health_check
# ---------------------------------------------------------------------------


def _patch_lifespan_deps(monkeypatch: pytest.MonkeyPatch, emitter_cls: type) -> None:
    """Stub observability + patch MarkdownEmitter at BOTH sites (belt-and-suspenders).

    `_lifespan` currently does `from … import MarkdownEmitter` inside the function
    body, so `me.MarkdownEmitter` is the live binding. But a future refactor that
    hoists the import to module top would silently neuter a single-site patch —
    so we also patch `chaoslab_agent.main.MarkdownEmitter` (raising=False because
    that name doesn't exist at module top today; the patch survives a hoist).
    """
    import chaoslab_agent.main as main_mod
    import chaoslab_agent.observability as obs
    import chaoslab_agent.patcher.markdown_emitter as me

    monkeypatch.setattr(obs, "setup_logging", lambda env: None)
    monkeypatch.setattr(obs, "setup_phoenix_otel", lambda settings: None)
    monkeypatch.setattr(me, "MarkdownEmitter", emitter_cls)
    monkeypatch.setattr(main_mod, "MarkdownEmitter", emitter_cls, raising=False)


async def test_lifespan_invokes_markdown_emitter_health_check(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Round-3 wired health_check into FastAPI's lifespan so a misconfigured
    bucket fails at boot instead of mid-demo. Lock the wiring."""
    from contextlib import asynccontextmanager

    called: dict[str, int] = {"count": 0}
    yielded: dict[str, bool] = {"ok": False}

    class _FakeEmitter:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        async def health_check(self) -> None:
            called["count"] += 1

    _patch_lifespan_deps(monkeypatch, _FakeEmitter)

    from chaoslab_agent.main import _lifespan
    from chaoslab_agent.main import app as fastapi_app

    @asynccontextmanager
    async def _drive():
        async with _lifespan(fastapi_app):
            yield

    async with _drive():
        yielded["ok"] = True

    # Both must hold: health_check was called AND the lifespan yielded (i.e.
    # nothing crashed AFTER the probe and before /run is ready to serve).
    assert called["count"] == 1
    assert yielded["ok"], "lifespan did not yield — call path crashed after the probe"


async def test_lifespan_skips_health_check_when_probe_disabled(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """`GCS_PROBE_AT_STARTUP=false` skips the bucket probe AND emits a CRITICAL log
    naming the env var (CRITICAL surfaces in Cloud Logging even when WARNING is
    filtered, defending the accidental-prod-set audit trail). Test-only escape
    hatch for the Dockerfile smoke test, which has no real GCS bucket to probe."""
    import logging as _logging
    from contextlib import asynccontextmanager

    monkeypatch.setenv("GCS_PROBE_AT_STARTUP", "false")
    get_settings.cache_clear()

    yielded: dict[str, bool] = {"ok": False}

    class _PoisonEmitter:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            # Poison construction — proves the lifespan didn't even instantiate
            # the emitter, which would have triggered a real storage.Client()
            # ADC probe at boot. Pure skip, not skip-after-construct.
            raise AssertionError("MarkdownEmitter must not be constructed when probe is disabled")

        async def health_check(self) -> None:
            raise AssertionError("health_check must not be invoked when probe is disabled")

    _patch_lifespan_deps(monkeypatch, _PoisonEmitter)

    from chaoslab_agent.main import _lifespan
    from chaoslab_agent.main import app as fastapi_app

    @asynccontextmanager
    async def _drive():
        async with _lifespan(fastapi_app):
            yield

    with caplog.at_level(_logging.CRITICAL, logger="chaoslab_agent.main"):
        async with _drive():
            yielded["ok"] = True

    # Three locks: (1) lifespan yielded — `else` branch didn't crash;
    # (2) env var name surfaces literally for Cloud Logging grep;
    # (3) the "should never be set in production" copy stays intact — a future
    # edit that softens the warning copy is the silent-failure shape we guard.
    assert yielded["ok"], "lifespan did not yield — skip branch crashed"
    crit_messages = [r.getMessage() for r in caplog.records if r.levelno >= _logging.CRITICAL]
    assert any("GCS_PROBE_AT_STARTUP" in m for m in crit_messages), crit_messages
    assert any("THIS SHOULD NEVER BE SET IN PRODUCTION" in m for m in crit_messages), crit_messages


def test_settings_env_prod_forbids_disabled_probe(monkeypatch: pytest.MonkeyPatch) -> None:
    """ADR audit posture: a prod deploy MUST NOT silently boot with the probe
    disabled. Settings construction itself raises so Cloud Run crashloops loud.
    The Field description warns; this validator enforces."""
    from pydantic import ValidationError

    from chaoslab_agent.config import Settings

    monkeypatch.setenv("ENVIRONMENT", "prod")
    monkeypatch.setenv("GCS_PROBE_AT_STARTUP", "false")

    with pytest.raises(ValidationError, match="FORBIDDEN when environment='prod'"):
        Settings()


@pytest.mark.parametrize("env", ["dev", "staging"])
def test_settings_non_prod_allows_disabled_probe(monkeypatch: pytest.MonkeyPatch, env: str) -> None:
    """The escape hatch IS allowed outside prod — local dev + staging smoke tests."""
    from chaoslab_agent.config import Settings

    monkeypatch.setenv("ENVIRONMENT", env)
    monkeypatch.setenv("GCS_PROBE_AT_STARTUP", "false")

    s = Settings()
    assert s.environment == env
    assert s.GCS_PROBE_AT_STARTUP is False


def test_gcs_probe_env_name_constant_matches_settings_field() -> None:
    """Drift guard — main.py's CRITICAL log interpolates GCS_PROBE_ENV_NAME so a
    silent rename of the Settings field would defeat the Cloud-Logging grep
    safety net. The module-load check in config.py raises if these diverge;
    this test belt-and-suspenders it from the test side too."""
    from chaoslab_agent.config import GCS_PROBE_ENV_NAME, Settings

    assert GCS_PROBE_ENV_NAME in Settings.model_fields, (
        f"GCS_PROBE_ENV_NAME={GCS_PROBE_ENV_NAME!r} does not name a Settings field"
    )
