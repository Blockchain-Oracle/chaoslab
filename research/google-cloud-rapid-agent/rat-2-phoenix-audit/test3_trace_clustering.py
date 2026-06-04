#!/usr/bin/env python3
"""RAT-2 Test 3: Trace clustering — the cascade-flip demo moment.

Hypothesis: Given N failed traces in Phoenix (synthetically generated to share
a common upstream cause), we can read them back via Phoenix's Python client
and identify the COMMON UPSTREAM SPAN that all failures share — the
"3 failures collapse into 1 root cause" headline.

This validates the most demo-critical piece. If clustering doesn't work,
the cascade-flip moment is theater, not real.

What this script does:
  1. Emits 6 synthetic traces to a fresh Phoenix project:
     - 3 FAILED traces, all sharing the same upstream span pattern
       (e.g., a `check_formulary` span called WITHOUT a prior `verify_benefits` span)
     - 3 PASSED traces, all with `verify_benefits` -> `check_formulary` order
  2. Reads them back via Phoenix client.
  3. Clusters: which span name appears in ALL failed traces but NOT in any
     passing trace? That's the root cause.
  4. Asserts we identify the right root cause.

Run:
  source ~/.config/phoenix-rat/.env
  uv run python research/google-cloud-rapid-agent/rat-2-phoenix-audit/test3_trace_clustering.py
"""

from __future__ import annotations

import os
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

PROJECT_NAME = f"rat2-test3-clustering-{uuid.uuid4().hex[:8]}"
print(f"[INFO] Phoenix project: {PROJECT_NAME}")

from phoenix.otel import register

tracer_provider = register(
    project_name=PROJECT_NAME,
    endpoint=f"{ENDPOINT}/v1/traces",
    protocol="http/protobuf",
    headers={"authorization": f"Bearer {API_KEY}"},
    auto_instrument=False,
    set_global_tracer_provider=True,
    batch=False,
)
tracer = tracer_provider.get_tracer("rat2.test3")

# === Phase A: emit 6 traces (3 FAIL + 3 PASS) ===
# Each trace simulates one adversarial test against a prior-auth target.
# FAIL traces share the pattern: `check_formulary` called without prior
# `verify_benefits` — that's the "root cause."


def emit_passing_trace(test_id: int) -> None:
    with tracer.start_as_current_span("adversarial_test") as outer:
        outer.set_attribute("rat2.test", "test3_clustering")
        outer.set_attribute("rat2.test_id", f"pass-{test_id}")
        outer.set_attribute("rat2.outcome", "pass")
        outer.set_attribute("openinference.span.kind", "CHAIN")
        with tracer.start_as_current_span("verify_benefits") as v:
            v.set_attribute("openinference.span.kind", "TOOL")
            v.set_attribute("tool_call.function.name", "verify_benefits")
        with tracer.start_as_current_span("check_formulary") as c:
            c.set_attribute("openinference.span.kind", "TOOL")
            c.set_attribute("tool_call.function.name", "check_formulary")


# Set status codes properly — OpenTelemetry status codes use trace.Status
from opentelemetry import trace as ot_trace


def emit_failing_trace_v2(test_id: int) -> None:
    with tracer.start_as_current_span("adversarial_test") as outer:
        outer.set_attribute("rat2.test", "test3_clustering")
        outer.set_attribute("rat2.test_id", f"fail-{test_id}")
        outer.set_attribute("rat2.outcome", "fail")
        outer.set_attribute("openinference.span.kind", "CHAIN")
        with tracer.start_as_current_span("check_formulary") as inner:
            inner.set_attribute("openinference.span.kind", "TOOL")
            inner.set_attribute("tool_call.function.name", "check_formulary")
            inner.set_attribute("rat2.failure_reason", "called without verify_benefits")
            inner.set_status(ot_trace.Status(ot_trace.StatusCode.ERROR, "tool order violation"))


print("[INFO] Emitting 3 FAIL + 3 PASS traces...")
for i in range(3):
    emit_failing_trace_v2(i)
    emit_passing_trace(i)
tracer_provider.force_flush(timeout_millis=10_000)
print("[OK] 6 traces emitted")

# === Phase B: read traces back + cluster ===

import requests

headers = {"Authorization": f"Bearer {API_KEY}"}
base = ENDPOINT.rstrip("/")

print("[INFO] Polling Phoenix for project (10s grace)...")
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
    sys.exit("[FAIL] Project never landed in Phoenix")

print(f"[OK] Project visible: {project_id}")

# Wait + use Phoenix Python client to fetch all spans as a DataFrame
print("[INFO] Waiting for spans to ingest (≤20s)...")
from phoenix.client import Client

phx = Client()

df = None
for _ in range(20):
    time.sleep(1)
    try:
        df = phx.spans.get_spans_dataframe(project_identifier=PROJECT_NAME, limit=500)
    except Exception as e:
        print(f"[WARN] get_spans_dataframe error: {e}; retrying...")
        continue
    if df is not None and len(df) >= 15:  # 6 outer + 3 fail-inner + 6 pass-inner
        break

if df is None or len(df) < 15:
    print(f"[INFO] DataFrame columns: {df.columns.tolist() if df is not None else 'N/A'}")
    print(f"[INFO] Row count: {len(df) if df is not None else 0}")
    if df is not None:
        print(df[["name"]].value_counts() if "name" in df.columns else df.head())
    sys.exit(f"[FAIL] Expected ≥15 spans; got {0 if df is None else len(df)}")

print(f"[OK] Phoenix returned {len(df)} spans for {PROJECT_NAME}")
print(f"[INFO] Span name counts:\n{df['name'].value_counts().to_string()}")

# === Phase C: cluster ===

from collections import defaultdict

# Pandas DataFrame; columns include 'name', 'context.trace_id', and attributes.
# Find the trace_id column shape
print(f"[INFO] DataFrame columns sample: {df.columns.tolist()[:20]}")

# Pick trace_id column
trace_id_col = None
for cand in ("context.trace_id", "trace_id", "trace.id"):
    if cand in df.columns:
        trace_id_col = cand
        break
if trace_id_col is None:
    sys.exit(f"[FAIL] Can't find trace_id column in: {df.columns.tolist()}")


# Phoenix groups custom-prefix attributes into a dict column ('attributes.rat2').
# Standard OpenInference attrs (tool_call.*, openinference.*) get their own
# dedicated columns. This is a finding worth logging.
def extract_outcome(row) -> str | None:
    """Pull rat2.outcome from row, handling both dict and flat-column forms."""
    rat2 = row.get("attributes.rat2")
    if isinstance(rat2, dict):
        return rat2.get("outcome")
    # Fallback: flat column
    for cand in ("attributes.rat2.outcome", "rat2.outcome"):
        if cand in row.index:
            v = row.get(cand)
            if isinstance(v, str):
                return v
    return None


print(f"[INFO] trace_id_col={trace_id_col}; using attributes.rat2 dict for outcome")

# Group spans by trace_id, gather span names + outcome (outcome is on OUTER span only)
traces_by_id: dict[str, dict] = defaultdict(lambda: {"outcome": None, "span_names": set()})
for _, row in df.iterrows():
    tid = row.get(trace_id_col)
    if not tid or not isinstance(tid, str):
        continue
    nm = row.get("name", "")
    traces_by_id[tid]["span_names"].add(nm)
    outc = extract_outcome(row)
    if outc and outc in ("fail", "pass"):
        traces_by_id[tid]["outcome"] = outc

fail_traces = [t for t in traces_by_id.values() if t["outcome"] == "fail"]
pass_traces = [t for t in traces_by_id.values() if t["outcome"] == "pass"]

print(f"[INFO] Grouped into {len(fail_traces)} fail + {len(pass_traces)} pass traces")

if len(fail_traces) != 3 or len(pass_traces) != 3:
    sys.exit(
        f"[FAIL] Expected 3 fail + 3 pass; got {len(fail_traces)} fail + {len(pass_traces)} pass. "
        "Span attribute grouping is wrong."
    )

# Cluster: which span name is in ALL fail traces and NO pass traces?
# More useful: which span name is in ALL fail traces? Even better: which
# span name PATTERN distinguishes fail from pass?
if not fail_traces or not pass_traces:
    sys.exit(
        f"[FAIL] need non-empty trace lists; got fail={len(fail_traces)} pass={len(pass_traces)}"
    )
common_fail_spans = set.intersection(*(t["span_names"] for t in fail_traces))
common_pass_spans = set.intersection(*(t["span_names"] for t in pass_traces))
diff_spans = common_pass_spans - common_fail_spans  # spans pass has but fail lacks

print(f"[INFO] Spans common to ALL failing traces: {common_fail_spans}")
print(f"[INFO] Spans common to ALL passing traces: {common_pass_spans}")
print(f"[INFO] Spans PASS has but FAIL lacks (the missing protective step): {diff_spans}")

# Validation: the missing span should be "verify_benefits"
if "verify_benefits" not in diff_spans:
    sys.exit(
        f"[FAIL] Clustering algorithm did NOT identify the missing protective step. "
        f"Expected 'verify_benefits' in diff_spans, got {diff_spans}"
    )

# The 'check_formulary' span should be common to ALL traces (both fail and pass)
if "check_formulary" not in common_fail_spans or "check_formulary" not in common_pass_spans:
    sys.exit("[FAIL] Sanity check failed: 'check_formulary' not in common spans")

print()
print("===========================================")
print("[PASS] Test 3 — trace clustering")
print("===========================================")
print("  Identified root cause: 'verify_benefits' span MISSING from all 3 failing traces")
print("  This IS the 'cascade-flip' moment of the demo — 3 failures collapse to")
print("  1 root cause via Phoenix trace differential analysis.")
ui_base = ENDPOINT.split("/v1")[0]
print(f"  View in UI: {ui_base}/projects/{project_id}")
