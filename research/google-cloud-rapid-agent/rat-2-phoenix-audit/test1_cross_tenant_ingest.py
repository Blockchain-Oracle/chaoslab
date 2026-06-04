#!/usr/bin/env python3
"""RAT-2 Test 1: Cross-tenant Phoenix trace ingest.

Hypothesis: A Customer's target agent (running in a SEPARATE process / env)
can ship OpenInference traces to our Phoenix project using our API key +
endpoint, and we can then read those traces back via Phoenix API.

This is load-bearing for Phoenix Audit's architecture: the whole product
assumes the Customer's target ships traces somewhere we can read.

What this script does:
  1. Acts as the Customer's target — instruments with OpenInference, pointed
     at our Phoenix project + endpoint via the env file.
  2. Emits a single span (no LLM call needed for this test — we're testing
     the ingest pipeline, not LLM behavior).
  3. Polls Phoenix REST API server-side to confirm the span landed.
  4. Reports PASS / FAIL with timing.

Run:
  source ~/.config/phoenix-rat/.env
  uv run python research/google-cloud-rapid-agent/rat-2-phoenix-audit/test1_cross_tenant_ingest.py
"""

from __future__ import annotations

import os
import sys
import time
import uuid
from pathlib import Path

# Load env from ~/.config/phoenix-rat/.env if not already in environ.
env_file = Path.home() / ".config" / "phoenix-rat" / ".env"
if env_file.exists() and "PHOENIX_API_KEY" not in os.environ:
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, val = line.split("=", 1)
            os.environ.setdefault(key.strip(), val.strip())

API_KEY = os.environ.get("PHOENIX_API_KEY")
ENDPOINT = os.environ.get("PHOENIX_COLLECTOR_ENDPOINT")
if not API_KEY or not ENDPOINT:
    sys.exit("[FAIL] PHOENIX_API_KEY or PHOENIX_COLLECTOR_ENDPOINT not set")

print(f"[INFO] Phoenix endpoint: {ENDPOINT}")
print(f"[INFO] API key present: {'yes (' + str(len(API_KEY)) + ' chars)' if API_KEY else 'no'}")

# Use a unique project name per run so we can verify the trace cleanly.
PROJECT_NAME = f"rat2-test1-cross-tenant-{uuid.uuid4().hex[:8]}"
print(f"[INFO] Phoenix project (for THIS test run): {PROJECT_NAME}")

# === Phase A: act as the Customer's target — emit a trace ===

from phoenix.otel import register

tracer_provider = register(
    project_name=PROJECT_NAME,
    endpoint=f"{ENDPOINT}/v1/traces",
    protocol="http/protobuf",
    headers={"authorization": f"Bearer {API_KEY}"},
    auto_instrument=False,  # we'll manually emit a span
    set_global_tracer_provider=True,
    batch=False,  # immediate export so we can poll quickly
)
print("[OK] phoenix.otel.register() returned a tracer provider")

tracer = tracer_provider.get_tracer("rat2.test1.target")

# Emit a span shaped like an OpenInference LLM span (so it looks like a real
# target agent's trace, not a synthetic blob).
span_id_marker = f"rat2-marker-{uuid.uuid4().hex[:12]}"
with tracer.start_as_current_span("target_agent.respond") as span:
    # OpenInference convention attributes
    span.set_attribute("openinference.span.kind", "LLM")
    span.set_attribute("llm.model_name", "gemini-3.5-flash")
    span.set_attribute("input.value", "Test prompt: what is your purpose?")
    span.set_attribute(
        "output.value",
        "I am a customer-support agent for ACME health insurance.",
    )
    span.set_attribute("rat2.marker", span_id_marker)
    span.set_attribute("rat2.purpose", "cross-tenant-ingest verification")

# Force flush so the span is sent before we poll.
tracer_provider.force_flush(timeout_millis=10_000)
print(f"[OK] Span emitted with marker={span_id_marker}")

# === Phase B: verify server-side that the trace landed ===

import requests

# Phoenix REST: list projects, find ours, then list spans in it
headers = {"Authorization": f"Bearer {API_KEY}"}
base = ENDPOINT.rstrip("/")

print("[INFO] Polling Phoenix REST for the project (5s grace period)...")
project_id = None
for attempt in range(5):
    time.sleep(1)
    r = requests.get(f"{base}/v1/projects", headers=headers, timeout=10)
    if r.status_code != 200:
        print(f"[WARN] /v1/projects returned {r.status_code}: {r.text[:200]}")
        continue
    projects = r.json().get("data", [])
    for p in projects:
        if p.get("name") == PROJECT_NAME:
            project_id = p.get("id")
            break
    if project_id:
        print(f"[OK] Project found server-side: id={project_id}")
        break
else:
    sys.exit(
        f"[FAIL] Project {PROJECT_NAME} did not appear in Phoenix after 5s. "
        "Cross-tenant ingest BROKEN at project-creation stage."
    )

# Now look for the span. Phoenix REST exposes /v1/projects/{id}/spans
print("[INFO] Polling for the emitted span...")
found_span = False
poll_start = time.time()
while time.time() - poll_start < 15:
    r = requests.get(
        f"{base}/v1/projects/{project_id}/spans",
        headers=headers,
        timeout=10,
        params={"limit": 50},
    )
    if r.status_code != 200:
        print(f"[WARN] /spans returned {r.status_code}: {r.text[:200]}")
        time.sleep(1)
        continue
    spans = r.json().get("data", [])
    for s in spans:
        attrs = s.get("attributes", {}) or {}
        marker = attrs.get("rat2.marker")
        if marker == span_id_marker:
            found_span = True
            print(f"[OK] Span landed in Phoenix. server-side span_id={s.get('id')}")
            print(
                f"[OK] Roundtrip latency (emit → server-side visible): "
                f"{time.time() - poll_start:.2f}s"
            )
            break
    if found_span:
        break
    time.sleep(1)

if not found_span:
    sys.exit(
        f"[FAIL] Emitted span (marker={span_id_marker}) did NOT land in "
        f"Phoenix project {PROJECT_NAME} within 15 seconds. "
        "Cross-tenant ingest BROKEN at trace-export stage."
    )

print()
print("===========================================")
print("[PASS] Test 1 — cross-tenant Phoenix ingest")
print("===========================================")
print(f"  project: {PROJECT_NAME}")
print(f"  project_id: {project_id}")
print(f"  span_marker: {span_id_marker}")
print(f"  view in UI: {ENDPOINT.replace('/v1', '')}/projects/{project_id}")
