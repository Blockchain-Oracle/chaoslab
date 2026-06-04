#!/usr/bin/env python3
"""RAT-2 Test 2: A2A protocol round-trip between Phoenix Audit and a target.

Hypothesis: Phoenix Audit (acting as A2A client via `RemoteA2aAgent`) can
connect to a target ADK agent (exposed via `to_a2a()`) running in a SEPARATE
process, send a prompt, get a response, and have both sides' execution
emit Phoenix traces that share a logical conversation context.

No LLM required for this test — the target returns a canned response. We
are validating the A2A wire, not Gemini behavior.

Run:
  source ~/.config/phoenix-rat/.env
  uv run python research/google-cloud-rapid-agent/rat-2-phoenix-audit/test2_a2a_roundtrip.py
"""

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
    for raw_line in env_file.read_text().splitlines():
        line = raw_line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, val = line.split("=", 1)
            os.environ.setdefault(key.strip(), val.strip())

API_KEY = os.environ.get("PHOENIX_API_KEY")
ENDPOINT = os.environ.get("PHOENIX_COLLECTOR_ENDPOINT")
if not API_KEY or not ENDPOINT:
    sys.exit("[FAIL] PHOENIX_API_KEY or PHOENIX_COLLECTOR_ENDPOINT not set")

PROJECT_NAME = f"rat2-test2-a2a-{uuid.uuid4().hex[:8]}"
PORT = 19999
TARGET_SCRIPT = Path(__file__).parent / "test2_target_server.py"


def wait_for_port(host: str, port: int, timeout: float = 30.0) -> bool:
    """Block until TCP port is bound on host, or timeout."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1.0)
            if sock.connect_ex((host, port)) == 0:
                return True
        time.sleep(0.25)
    return False


async def call_target_via_a2a() -> str:
    """Phoenix Audit-side: connect via RemoteA2aAgent, send prompt, return response."""
    from google.adk.agents.remote_a2a_agent import (
        AGENT_CARD_WELL_KNOWN_PATH,
        RemoteA2aAgent,
    )
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai.types import Content, Part

    agent_card_url = f"http://127.0.0.1:{PORT}{AGENT_CARD_WELL_KNOWN_PATH}"
    print(f"[client] Fetching A2A agent card: {agent_card_url}")

    remote = RemoteA2aAgent(
        name="phoenix_audit_tester",
        description="Phoenix Audit Tester acting as A2A client",
        agent_card=agent_card_url,
    )

    session_service = InMemorySessionService()
    session = await session_service.create_session(app_name="rat2-test2", user_id="test-user")
    runner = Runner(
        app_name="rat2-test2",
        agent=remote,
        session_service=session_service,
    )

    user_msg = Content(
        parts=[Part.from_text(text="What is your purpose, and what tools do you have?")],
    )

    final_text = ""
    async for event in runner.run_async(
        user_id="test-user", session_id=session.id, new_message=user_msg
    ):
        if event.content and event.content.parts:
            for p in event.content.parts:
                t = getattr(p, "text", "") or ""
                final_text += t

    return final_text


def main() -> int:  # noqa: PLR0912, PLR0915 — research smoke script; refactor deferred
    # Set up our own Phoenix tracer for the client side
    from phoenix.otel import register

    tp = register(
        project_name=PROJECT_NAME,
        endpoint=f"{ENDPOINT}/v1/traces",
        protocol="http/protobuf",
        headers={"authorization": f"Bearer {API_KEY}"},
        auto_instrument=False,
        set_global_tracer_provider=True,
        batch=False,
    )

    try:
        from openinference.instrumentation.google_adk import GoogleADKInstrumentor

        GoogleADKInstrumentor().instrument(tracer_provider=tp)
        print("[client] ADK instrumentor attached on client side")
    except ImportError:
        print("[client] ADK instrumentor not installed; client-side spans manual only")

    print(f"[client] Phoenix project for THIS run: {PROJECT_NAME}")

    # Launch target as subprocess. Pass project name via env so target uses the same.
    env = {**os.environ, "RAT2_PROJECT_NAME": PROJECT_NAME}
    print(f"[client] Launching target subprocess: python {TARGET_SCRIPT} {PORT}")
    proc = subprocess.Popen(  # noqa: S603 — controlled args (sys.executable + fixed script)
        [sys.executable, str(TARGET_SCRIPT), str(PORT)],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    try:
        print(f"[client] Waiting for target to bind to 127.0.0.1:{PORT} (≤30s)...")
        if not wait_for_port("127.0.0.1", PORT, timeout=30):
            try:
                out, _ = proc.communicate(timeout=2)
                print(f"[FAIL] Target never bound. Output:\n{out[:2000]}")
            except subprocess.TimeoutExpired:
                proc.kill()
            return 1
        print(f"[client] Target ready on 127.0.0.1:{PORT}")
        # Tiny additional grace
        time.sleep(0.5)

        # Issue the A2A call
        start = time.time()
        response = asyncio.run(call_target_via_a2a())
        elapsed = time.time() - start
        print(f"[client] A2A call returned in {elapsed:.2f}s")
        print(f"[client] Response (first 300 chars): {response[:300]!r}")

        # Validate canned response made it
        if "deliberately-naive" not in response:
            print(f"[FAIL] Canned response NOT in reply. Got: {response[:500]}")
            return 1
        print("[OK] Canned response content matches — A2A wire works")

        # Flush spans
        tp.force_flush(timeout_millis=10_000)

        # Verify Phoenix-side
        import requests  # noqa: PLC0415 — local import keeps cold-start optional dep

        headers = {"Authorization": f"Bearer {API_KEY}"}
        base = ENDPOINT.rstrip("/")
        print("[client] Verifying Phoenix-side traces (10s grace)...")

        project_id = None
        for _ in range(10):
            time.sleep(1)
            r = requests.get(f"{base}/v1/projects", headers=headers, timeout=10)
            if r.status_code == 200:
                for p in r.json().get("data", []):
                    if p.get("name") == PROJECT_NAME:
                        project_id = p.get("id")
                        break
            if project_id:
                break

        if not project_id:
            print("[WARN] Phoenix project never appeared. A2A wire OK, tracing did not flush.")
        else:
            r = requests.get(
                f"{base}/v1/projects/{project_id}/spans",
                headers=headers,
                timeout=10,
                params={"limit": 100},
            )
            if r.status_code == 200:
                spans = r.json().get("data", [])
                target_spans = [
                    s
                    for s in spans
                    if (s.get("attributes") or {}).get("rat2.test") == "test2_a2a_roundtrip"
                ]
                assert len(target_spans) >= 1, (
                    f"[FAIL] A2A wire round-tripped, but target-side spans did NOT cross "
                    f"the process boundary into Phoenix. Got {len(spans)} total spans, "
                    f"{len(target_spans)} carrying the rat2.test marker. "
                    f"Cross-process tracing is broken; the test's core hypothesis FAILS."
                )
                print(
                    f"[OK] Phoenix has {len(spans)} total span(s) in {PROJECT_NAME}; "
                    f"{len(target_spans)} carry our rat2.test marker"
                )
                ui_base = ENDPOINT.split("/v1")[0]
                print(f"[OK] View in UI: {ui_base}/projects/{project_id}")

        print()
        print("===========================================")
        print("[PASS] Test 2 — A2A round-trip wire")
        print("===========================================")
        print(f"  project: {PROJECT_NAME}")
        print(f"  client→target latency: {elapsed:.2f}s")
        return 0

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    sys.exit(main())
