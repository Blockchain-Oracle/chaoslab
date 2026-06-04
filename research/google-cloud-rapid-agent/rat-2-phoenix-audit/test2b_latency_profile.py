#!/usr/bin/env python3
"""RAT-2 Test 2b: Latency profile of the A2A round-trip.

Decomposes the 15.87s from Test 2 into stages so we know what's slow:
  1. Target subprocess startup (separate, measure once)
  2. AgentCard well-known fetch
  3. RemoteA2aAgent construction
  4. ADK Runner + InMemorySessionService init
  5. First message send (handshake?) — N=1
  6. Subsequent messages (connection-reuse) — N=2..5
  7. Per-stage breakdown

Three optimization passes (each measured separately):
  Pass A: Single message, fresh client + Runner each time (baseline)
  Pass B: Reuse RemoteA2aAgent + Runner across N=5 messages (connection pool)
  Pass C: asyncio.gather N=5 messages concurrently (parallel)

Run (target subprocess must already be running on :19999):
  uv run python research/google-cloud-rapid-agent/rat-2-phoenix-audit/test2b_latency_profile.py
"""
# ruff: noqa

from __future__ import annotations

import asyncio
import os
import socket
import subprocess
import sys
import time
import uuid
from pathlib import Path

env_file = Path.home() / ".config" / "phoenix-rat" / ".env"
if env_file.exists() and "PHOENIX_API_KEY" not in os.environ:
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, val = line.split("=", 1)
            os.environ.setdefault(key.strip(), val.strip())

PROJECT_NAME = f"rat2-test2b-latency-{uuid.uuid4().hex[:8]}"
PORT = 19998  # different port from test2 to avoid collision
TARGET_SCRIPT = Path(__file__).parent / "test2_target_server.py"


def wait_for_port(host, port, timeout=30.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1.0)
            if sock.connect_ex((host, port)) == 0:
                return True
        time.sleep(0.25)
    return False


def stamp(label, t0):
    elapsed = time.time() - t0
    print(f"  [+{elapsed:6.3f}s] {label}")
    return time.time()


async def measure_a2a_call(remote, runner, session_id, user_text):
    """Measure ONE A2A call given pre-built remote + runner."""
    from google.genai.types import Content, Part

    msg = Content(parts=[Part.from_text(text=user_text)])
    text = ""
    start = time.time()
    async for event in runner.run_async(
        user_id="test-user", session_id=session_id, new_message=msg
    ):
        if event.content and event.content.parts:
            for p in event.content.parts:
                t = getattr(p, "text", "") or ""
                text += t
    return text, time.time() - start


async def build_remote_and_runner():
    """Build the RemoteA2aAgent + Runner once. Measure each step."""
    from google.adk.agents.remote_a2a_agent import (
        AGENT_CARD_WELL_KNOWN_PATH,
        RemoteA2aAgent,
    )
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService

    print("[build] Building remote + runner...")
    t0 = time.time()

    agent_card_url = f"http://127.0.0.1:{PORT}{AGENT_CARD_WELL_KNOWN_PATH}"
    t0 = stamp("agent_card_url computed", t0)

    remote = RemoteA2aAgent(
        name="phoenix_audit_tester",
        description="latency profile client",
        agent_card=agent_card_url,
    )
    t0 = stamp("RemoteA2aAgent() constructed", t0)

    session_service = InMemorySessionService()
    t0 = stamp("InMemorySessionService() constructed", t0)

    session = await session_service.create_session(
        app_name="rat2-test2b", user_id="test-user"
    )
    t0 = stamp("session.create() done", t0)

    runner = Runner(
        app_name="rat2-test2b",
        agent=remote,
        session_service=session_service,
    )
    t0 = stamp("Runner() constructed", t0)

    return remote, runner, session.id


async def pass_a_single_fresh():
    """Pass A: ONE call with fresh client + runner. The baseline 16s."""
    print("\n=== Pass A — single message, fresh client + runner ===")
    overall = time.time()
    remote, runner, session_id = await build_remote_and_runner()
    print(f"[build] Setup done in {time.time() - overall:.3f}s")

    text, call_time = await measure_a2a_call(
        remote, runner, session_id, "Pass A: what is your purpose?"
    )
    print(f"[call] Single message round-trip: {call_time:.3f}s")
    print(f"[call] Response length: {len(text)} chars")
    print(f"[total] Pass A end-to-end: {time.time() - overall:.3f}s")
    return time.time() - overall


async def pass_b_reuse_n5():
    """Pass B: Build once, reuse for N=5 sequential calls. Connection-reuse benefit?"""
    print("\n=== Pass B — N=5 sequential, REUSED client + runner ===")
    overall = time.time()
    remote, runner, session_id = await build_remote_and_runner()
    print(f"[build] Setup done in {time.time() - overall:.3f}s")

    call_times = []
    for i in range(5):
        text, call_time = await measure_a2a_call(
            remote, runner, session_id, f"Pass B call {i + 1}: ping {i}"
        )
        call_times.append(call_time)
        print(f"[call {i + 1}/5] {call_time:.3f}s ({len(text)} chars)")

    print(f"[summary] 5 calls totaled: {sum(call_times):.3f}s")
    print(f"[summary] Mean per-call: {sum(call_times) / 5:.3f}s")
    print(f"[summary] First call: {call_times[0]:.3f}s, subsequent mean: {sum(call_times[1:]) / 4:.3f}s")
    print(f"[total] Pass B end-to-end: {time.time() - overall:.3f}s")
    return call_times


async def pass_c_concurrent_n5():
    """Pass C: Build once, fire N=5 calls concurrently via asyncio.gather."""
    print("\n=== Pass C — N=5 CONCURRENT, REUSED client + runner ===")
    overall = time.time()
    remote, runner, session_id = await build_remote_and_runner()
    print(f"[build] Setup done in {time.time() - overall:.3f}s")

    start = time.time()
    tasks = [
        measure_a2a_call(remote, runner, session_id, f"Pass C concurrent {i + 1}")
        for i in range(5)
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    wall = time.time() - start

    successes = [r for r in results if not isinstance(r, Exception)]
    failures = [r for r in results if isinstance(r, Exception)]
    print(f"[summary] Wall-clock for 5 concurrent calls: {wall:.3f}s")
    print(f"[summary] Successes: {len(successes)}, failures: {len(failures)}")
    if failures:
        print(f"[summary] First failure: {failures[0]!r}")
    if successes:
        call_times = [t[1] for t in successes]
        print(f"[summary] Individual call times: {[f'{t:.2f}s' for t in call_times]}")
        print(f"[summary] Mean per-call: {sum(call_times) / len(call_times):.3f}s")
    print(f"[total] Pass C end-to-end: {time.time() - overall:.3f}s")
    return wall, len(successes), len(failures)


def main():
    # Phoenix tracer for this run
    from phoenix.otel import register

    tp = register(
        project_name=PROJECT_NAME,
        endpoint=f"{os.environ['PHOENIX_COLLECTOR_ENDPOINT']}/v1/traces",
        protocol="http/protobuf",
        headers={"authorization": f"Bearer {os.environ['PHOENIX_API_KEY']}"},
        auto_instrument=False,
        set_global_tracer_provider=True,
        batch=False,
    )
    try:
        from openinference.instrumentation.google_adk import GoogleADKInstrumentor

        GoogleADKInstrumentor().instrument(tracer_provider=tp)
        print("[setup] ADK instrumentor attached")
    except ImportError:
        pass

    # Launch target subprocess
    env = {**os.environ, "RAT2_PROJECT_NAME": PROJECT_NAME}
    print(f"[setup] Launching target on :{PORT}")
    proc = subprocess.Popen(
        [sys.executable, str(TARGET_SCRIPT), str(PORT)],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        if not wait_for_port("127.0.0.1", PORT, timeout=30):
            print(f"[FAIL] Target never bound to :{PORT}")
            return 1
        print(f"[setup] Target ready on :{PORT}, beginning passes")
        time.sleep(0.5)  # extra grace

        pa = asyncio.run(pass_a_single_fresh())
        pb = asyncio.run(pass_b_reuse_n5())
        pc = asyncio.run(pass_c_concurrent_n5())

        print("\n" + "=" * 50)
        print("LATENCY PROFILE SUMMARY")
        print("=" * 50)
        print(f"Pass A (single fresh):       {pa:.2f}s   (baseline — Test 2 was 15.87s here)")
        if pb:
            print(f"Pass B (N=5 sequential reused): first={pb[0]:.2f}s, subsequent mean={sum(pb[1:]) / 4:.2f}s")
        print(f"Pass C (N=5 concurrent reused): {pc[0]:.2f}s wall ({pc[1]}/{pc[1] + pc[2]} succeeded)")

        # Headline arithmetic for the 47-test scenario
        print()
        print("Projected 47-test audit wall-clock:")
        seq_per_call = sum(pb[1:]) / 4 if pb else pa
        print(f"  Pure sequential (no reuse): {pa * 47:.0f}s")
        print(f"  Sequential reused:           {seq_per_call * 47:.0f}s")
        print(f"  5-wide concurrent reused:    {(pc[0] / 5 * 47):.0f}s estimate (if scaling holds)")

        return 0
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    sys.exit(main())
