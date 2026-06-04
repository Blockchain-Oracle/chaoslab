#!/usr/bin/env python3
"""RAT-2 Test 2 — the TARGET server (runs as a separate process).

This is the Customer's target agent. Launched as a subprocess by
test2_a2a_roundtrip.py. Speaks A2A protocol on the port given in argv[1].
No LLM call — returns a canned response. The whole point of this test is to
prove the A2A WIRE, not Gemini behavior.

Run directly (for debugging):
  uv run python research/google-cloud-rapid-agent/rat-2-phoenix-audit/test2_target_server.py 19999
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Load Phoenix env so the target ships traces too (matches reality —
# Customer's target is OpenInference-instrumented and ships to Phoenix).
env_file = Path.home() / ".config" / "phoenix-rat" / ".env"
if env_file.exists():
    for raw_line in env_file.read_text().splitlines():
        line = raw_line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, val = line.split("=", 1)
            os.environ.setdefault(key.strip(), val.strip())

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 19999
PROJECT_NAME = os.environ.get("RAT2_PROJECT_NAME", "rat2-test2-target")

from phoenix.otel import register

tracer_provider = register(
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

    GoogleADKInstrumentor().instrument(tracer_provider=tracer_provider)
except ImportError as e:
    sys.exit(
        f"[FAIL] openinference-instrumentation-google-adk not importable in "
        f"target subprocess; cross-process tracing cannot be validated. {e}"
    )

from google.adk.a2a.utils.agent_to_a2a import to_a2a
from google.adk.agents import BaseAgent
from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions
from google.genai.types import Content, Part

CANNED_RESPONSE = (
    "I am a deliberately-naive customer-support agent for ACME Health. "
    "I have 3 tools: lookup_order, refund, escalate. "
    "(Test target — RAT-2 cross-process A2A wire validation.)"
)


class NoLLMTargetAgent(BaseAgent):
    async def _run_async_impl(self, ctx):  # type: ignore[override]
        tracer = tracer_provider.get_tracer("rat2.test2.target")
        with tracer.start_as_current_span("target.respond") as span:
            user_text = ""
            if ctx.user_content and ctx.user_content.parts:
                for p in ctx.user_content.parts:
                    user_text += getattr(p, "text", "") or ""
            span.set_attribute("openinference.span.kind", "AGENT")
            span.set_attribute("input.value", user_text)
            span.set_attribute("output.value", CANNED_RESPONSE)
            span.set_attribute("rat2.test", "test2_a2a_roundtrip")
            span.set_attribute("rat2.target_pid", os.getpid())

            yield Event(
                author=self.name,
                content=Content(parts=[Part.from_text(text=CANNED_RESPONSE)]),
                actions=EventActions(),
            )


target = NoLLMTargetAgent(
    name="target_agent",
    description="Deliberately-naive customer-support agent. No LLM. Canned.",
)
a2a_app = to_a2a(target, port=PORT)

import uvicorn

print(f"[target-server] PID={os.getpid()} starting on 127.0.0.1:{PORT}", flush=True)
print(f"[target-server] Phoenix project: {PROJECT_NAME}", flush=True)
uvicorn.run(a2a_app, host="127.0.0.1", port=PORT, log_level="warning")
