# Story — F4: `LatencySpikeFault` (asyncio sleep + httpx timeout shim)

**ID:** story-5.5-fault-latency-spike
**Epic:** Epic 5 — Fault injection (the 4 fault classes)
**Depends on:** story-5.1-vendor-agent-chaos
**Estimate:** ~1.5h
**Status:** PENDING
**tags:** [backend, p0, injector, fault]

---

## User story

**As a** ChaosLab Injector sub-agent
**I want to** inject `asyncio.sleep(delay_ms)` before tool calls AND reduce the httpx client timeout to `timeout_ms` via a transport shim
**So that** the network-layer fault (per `architecture/04 §2 rank 4` + OWASP LLM04 + MS#9) adds essential layer-diversity to the demo and reveals the target's lack of retry/backoff policy as TOOL spans whose `duration_ms` exceeds the timeout — visible in Phoenix as a degraded curve

---

## File modification map

Exact files the coding agent creates or modifies for this story:

- `apps/chaoslab-agent/src/chaoslab_agent/injector/faults/latency_spike.py` — NEW — defines `LatencySpikeFault` class + the httpx `AsyncBaseTransport` shim. ≤100 LOC total; fault class proper ≤25 LOC per `architecture/04 §8`.
- `apps/chaoslab-agent/src/chaoslab_agent/injector/faults/__init__.py` — UPDATE — add `from .latency_spike import LatencySpikeFault` to the package re-exports
- `apps/chaoslab-agent/tests/integration/injector/faults/test_latency_spike.py` — NEW — ≥6 trace-as-assertion integration tests using `InMemorySpanExporter` + ADK `InMemoryRunner`. Verifies TOOL span `duration_ms` > `delay_ms` AND/OR a timeout-shaped status code when `delay_ms > timeout_ms`. Uses `respx` to back the target's tool with a controllable httpx mock.
- `apps/chaoslab-agent/tests/unit/injector/faults/test_latency_spike_unit.py` — NEW — ≥4 unit tests for Pydantic validation (delay_ms ≥0, timeout_ms ≥0, target_tool_name optional, rate clamp 0-1).

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given apps/chaoslab-agent/src/chaoslab_agent/injector/faults/latency_spike.py exists
When `grep -E "^class LatencySpikeFault" apps/chaoslab-agent/src/chaoslab_agent/injector/faults/latency_spike.py` runs
Then exit code is 0

Given the file declares both injection mechanisms
When `grep -cE "(asyncio\.sleep|AsyncBaseTransport|httpx.*[Tt]imeout)" apps/chaoslab-agent/src/chaoslab_agent/injector/faults/latency_spike.py` runs
Then output is ≥2 (both asyncio.sleep and an httpx timeout shim are present)

Given the fault class is importable
When `uv run python -c "from chaoslab_agent.injector.faults import LatencySpikeFault; print('ok')"` runs
Then stdout contains "ok" and exit code is 0

Given the target agent is configured with LatencySpikeFault(delay_ms=30000, timeout_ms=10000)
When the agent invokes a tool via InMemoryRunner with an in-memory OpenInference span exporter
Then a span with openinference.span.kind == "TOOL" appears in the exporter
And  the span has either: duration_ms > 30000 OR status_code maps to a TIMEOUT-shaped failure (status_code == "ERROR" with an exception event whose attributes["exception.type"] matches "(Timeout|TimeoutError|ReadTimeout|ConnectTimeout|asyncio.TimeoutError)")
And  the span has attribute "chaoslab.fault.type" == "latency_spike"
And  the span has attribute "chaoslab.fault.delay_ms" == 30000
And  the span has attribute "chaoslab.fault.timeout_ms" == 10000

Given LatencySpikeFault(delay_ms=200, timeout_ms=60000) — slow but well under timeout
When the agent invokes a tool
Then the TOOL span has duration_ms > 200
And  the TOOL span has status_code == "OK" (no timeout)

Given the test suite uses respx to back the tool's httpx call
When `uv run pytest -m integration apps/chaoslab-agent/tests/integration/injector/faults/test_latency_spike.py -v` runs
Then ≥6 integration tests pass and no real network call leaks (respx assert_all_mocked=True)

Given the unit suite runs
When `uv run pytest apps/chaoslab-agent/tests/unit/injector/faults/test_latency_spike_unit.py -v` runs
Then ≥4 unit tests pass

Given the source file
When `python3 scripts/check_max_lines.py apps/chaoslab-agent/src/chaoslab_agent/injector/faults/latency_spike.py` runs
Then exit code is 0
And  the LatencySpikeFault class body is ≤25 LOC

Given §14 check
When `grep -rE "(mock|fake|dummy|hardcoded|simulated)" apps/chaoslab-agent/src/chaoslab_agent/injector/faults/latency_spike.py` runs
Then zero results appear
```

---

## Shell verification

```bash
set -e
cd /Users/abu/dev/hackathon/rapid-agents

# 1) Source file exists + structure
test -f apps/chaoslab-agent/src/chaoslab_agent/injector/faults/latency_spike.py
grep -qE "^class LatencySpikeFault" apps/chaoslab-agent/src/chaoslab_agent/injector/faults/latency_spike.py
grep -qE "asyncio\.sleep" apps/chaoslab-agent/src/chaoslab_agent/injector/faults/latency_spike.py
grep -qE "(AsyncBaseTransport|httpx.*[Tt]imeout)" apps/chaoslab-agent/src/chaoslab_agent/injector/faults/latency_spike.py

# 2) Importable
uv run python -c "from chaoslab_agent.injector.faults import LatencySpikeFault; print('ok')" | grep -q ok

# 3) Integration tests pass with ≥6 cases (trace-as-assertion, respx-backed)
uv run pytest -m integration apps/chaoslab-agent/tests/integration/injector/faults/test_latency_spike.py -v
INT_COUNT=$(uv run pytest apps/chaoslab-agent/tests/integration/injector/faults/test_latency_spike.py --collect-only -q 2>&1 | grep -cE "test_")
[ "$INT_COUNT" -ge 6 ] || { echo "expected ≥6 integration tests, got $INT_COUNT"; exit 1; }

# 4) Unit tests pass with ≥4 cases
uv run pytest apps/chaoslab-agent/tests/unit/injector/faults/test_latency_spike_unit.py -v
UNIT_COUNT=$(uv run pytest apps/chaoslab-agent/tests/unit/injector/faults/test_latency_spike_unit.py --collect-only -q 2>&1 | grep -cE "test_")
[ "$UNIT_COUNT" -ge 4 ] || { echo "expected ≥4 unit tests, got $UNIT_COUNT"; exit 1; }

# 5) 400-line guard + fault class ≤25 LOC
python3 scripts/check_max_lines.py apps/chaoslab-agent/src/chaoslab_agent/injector/faults/latency_spike.py

# 6) Lint + type-check
uv run ruff check apps/chaoslab-agent/src/chaoslab_agent/injector/faults/latency_spike.py
uv run ruff format --check apps/chaoslab-agent/src/chaoslab_agent/injector/faults/latency_spike.py
uv run ty check apps/chaoslab-agent/src/chaoslab_agent/injector/faults/latency_spike.py || uv run mypy --strict apps/chaoslab-agent/src/chaoslab_agent/injector/faults/latency_spike.py

# 7) §14 clean
! grep -rE "(mock|fake|dummy|hardcoded|simulated)" apps/chaoslab-agent/src/chaoslab_agent/injector/faults/latency_spike.py

echo "story-5.5 verification: PASS"
```

---

## Notes for coding agent

### The fault class shape (target ≤25 LOC for the class body, per `architecture/04 §8`)

```python
# apps/chaoslab-agent/src/chaoslab_agent/injector/faults/latency_spike.py
from __future__ import annotations
import asyncio
import httpx
from pydantic import BaseModel, Field
from opentelemetry import trace


class LatencySpikeFault(BaseModel):
    """Inject asyncio.sleep before tool calls and tighten httpx timeout."""
    delay_ms: int = Field(ge=0, le=120_000)        # how long to sleep
    timeout_ms: int = Field(ge=0, le=120_000)      # httpx timeout (real-network shim)
    target_tool_name: str | None = None
    rate: float = Field(default=1.0, ge=0.0, le=1.0)

    def as_callback(self):
        async def callback(tool, args, tool_context):
            span = trace.get_current_span()
            span.set_attribute("chaoslab.fault.type", "latency_spike")
            span.set_attribute("chaoslab.fault.delay_ms", self.delay_ms)
            span.set_attribute("chaoslab.fault.timeout_ms", self.timeout_ms)
            if self.target_tool_name and tool.name != self.target_tool_name:
                return None
            await asyncio.sleep(self.delay_ms / 1000)
            return None  # let the real tool run (after the delay)
        return callback

    def httpx_transport(self) -> httpx.AsyncBaseTransport:
        """Return a transport shim that enforces self.timeout_ms on httpx calls."""
        base = httpx.AsyncHTTPTransport()
        timeout = httpx.Timeout(self.timeout_ms / 1000)

        class _Shim(httpx.AsyncBaseTransport):
            async def handle_async_request(self, request):
                request.extensions["timeout"] = {
                    "connect": timeout.connect, "read": timeout.read,
                    "write": timeout.write, "pool": timeout.pool,
                }
                return await base.handle_async_request(request)
        return _Shim()
```

### Two injection surfaces, one fault class

1. **`as_callback()` returns a `before_tool_callback`** that calls `asyncio.sleep(delay_ms/1000)` before the real tool runs. The tool then proceeds normally — the delay shows up as the TOOL span's duration.
2. **`httpx_transport()` returns an `httpx.AsyncBaseTransport`** subclass that injects `request.extensions["timeout"]` per call. Wire it into the target's httpx client at construction (the Injector sub-agent in story 5.7 does this when the target is HTTP-shaped). For tool-call tests, only `as_callback()` is exercised.

The combination of long delay + short timeout produces the canonical TIMEOUT span: tool starts → delay exceeds timeout → httpx raises `ReadTimeout` → ADK records the TOOL span with `status_code=ERROR` and an exception event.

### Trace-as-assertion test pattern

```python
# apps/chaoslab-agent/tests/integration/injector/faults/test_latency_spike.py
import time
import pytest
import respx
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from chaoslab_agent.injector.faults import LatencySpikeFault


@pytest.mark.integration
async def test_long_delay_short_timeout_produces_timeout_span(
    in_memory_spans: InMemorySpanExporter,
    in_memory_runner,
    target_agent_with_httpx_tool,
    respx_mock,
) -> None:
    respx_mock.get("https://crm.example.com/orders/12345").mock(
        return_value=...  # any 200 response — but the delay will exceed timeout
    )
    fault = LatencySpikeFault(delay_ms=30000, timeout_ms=10000, target_tool_name="lookup_order")
    target_agent_with_httpx_tool.before_tool_callback = fault.as_callback()

    async for _ in in_memory_runner.run_async(
        user_id="u1", session_id="s1", new_message=...
    ):
        pass

    tool_spans = [s for s in in_memory_spans.get_finished_spans()
                  if s.attributes.get("openinference.span.kind") == "TOOL"]
    assert len(tool_spans) >= 1
    span = tool_spans[0]
    duration_ms = (span.end_time - span.start_time) / 1_000_000  # ns -> ms
    timeout_shaped = span.status.status_code.name == "ERROR" and any(
        "timeout" in (ev.attributes.get("exception.type") or "").lower()
        for ev in span.events
    )
    assert duration_ms > 30000 or timeout_shaped
    assert span.attributes.get("chaoslab.fault.type") == "latency_spike"
    assert span.attributes.get("chaoslab.fault.delay_ms") == 30000
    assert span.attributes.get("chaoslab.fault.timeout_ms") == 10000


@pytest.mark.integration
async def test_short_delay_long_timeout_produces_slow_but_ok_span(
    in_memory_spans, in_memory_runner, target_agent_with_httpx_tool, respx_mock,
) -> None:
    respx_mock.get("https://crm.example.com/orders/12345").mock(return_value=...)
    fault = LatencySpikeFault(delay_ms=200, timeout_ms=60000)
    target_agent_with_httpx_tool.before_tool_callback = fault.as_callback()

    async for _ in in_memory_runner.run_async(user_id="u1", session_id="s1", new_message=...):
        pass

    tool_spans = [s for s in in_memory_spans.get_finished_spans()
                  if s.attributes.get("openinference.span.kind") == "TOOL"]
    span = tool_spans[0]
    duration_ms = (span.end_time - span.start_time) / 1_000_000
    assert duration_ms > 200
    assert span.status.status_code.name == "OK"
```

### Test-suite acceleration note

For the 30000ms-delay test, real sleeps make CI painfully slow. Two acceptable approaches:

1. **Use a smaller delta** (`delay_ms=300, timeout_ms=100`) for CI tests — still validates the timeout-shaped error path, just faster. Document this in test docstrings.
2. **Use `freezegun` / `pytest-asyncio` time control** to advance the loop without real sleep. More complex; only worth it if test time becomes a real blocker.

The BDD criterion `delay_ms > 30000` in the spec is the canonical demo configuration — tests should validate the SHAPE of the behavior with smaller deltas, then have ONE slow test that runs the full 30s/10s pair gated behind `@pytest.mark.slow` (per `coding-standards.md` markers).

### Architecture context

- **`architecture/04 §3.4` (network shim) + §8.2 F4 (≤25 LOC reference impl):** the canonical fault body. The vendored `tool.py` from agent-chaos (story 5.1) has a `tool_timeout` primitive — ChaosLab's F4 builds on the SAME idea but exposes the ADK callback API.
- **OpenInference TOOL span duration:** `duration_ms = (end_time - start_time) / 1_000_000` because OTel timestamps are in nanoseconds. Phoenix's UI surfaces this as the bar width in the trace timeline.
- **Status mapping on timeout:** when httpx raises `ReadTimeout` mid-call, ADK records the TOOL span with `status_code=ERROR` and adds an exception event. The OTel exception event has `attributes["exception.type"] = "ReadTimeout"` (or `TimeoutError`, `ConnectTimeout`, etc. depending on which phase timed out).
- **`asyncio.sleep` vs `time.sleep`:** MUST be `asyncio.sleep` — ADK is async-first and `time.sleep` blocks the event loop. Per `coding-standards.md` "Async" section, `time.sleep` is banned in async code.

### Known pitfalls

- **`respx_mock(assert_all_mocked=True)`** — set this in the fixture so any accidental real-network call by the tool fails loudly. Per `best-practices/06 §3.1`.
- **The `httpx_transport` shim modifies `request.extensions["timeout"]`** — this is an httpx-internal contract; it shifts across major versions. As of httpx 0.27+ this is stable. If you see `TypeError: Timeout has no attribute connect`, the httpx version is too old; bump to ≥0.27.
- **Span duration measurement** — OpenInference span durations are wall-clock. If the event loop is slow (CI under load), the duration may overshoot the configured delay by hundreds of ms. The BDD criterion uses `duration_ms > delay_ms` (not equality) for exactly this reason.
- **Do NOT inject `time.sleep` anywhere.** Per `coding-standards.md` "Async" banned patterns. Even in test fixtures.
- **`@pytest.mark.slow`** any test with `delay_ms > 1000` so they're deselected from the default PR loop per `best-practices/06 §2.4`.
- **Cross-reference:** `/Users/abu/dev/hackathon/rapid-agents/research/google-cloud-rapid-agent/architecture/04-fault-injection-eval.md` §3.4 (network shim) + §4.2 F4 (latency-spike eval rubric) + §8.2 F4 (reference impl). `/Users/abu/dev/hackathon/rapid-agents/research/google-cloud-rapid-agent/best-practices/06-test-strategy.md` §3 (respx) + §5.1 (trace-as-assertion).
