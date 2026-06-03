# Story — Observability (structlog + Phoenix trace propagation) and ADK Types Quarantine

**ID:** story-4.5-observability-and-types
**Epic:** Epic 4 — ChaosLab orchestrator + Phoenix tool wrappers
**Depends on:** story-4.1-agent-entrypoint
**Estimate:** ~2h
**Status:** PENDING
**tags:** [backend, p0, observability, structlog, types, adk]

---

## User story

**As a** developer reading any chaoslab-agent log line in Cloud Logging
**I want to** see structured JSON output that includes the active Phoenix `trace_id` + `span_id` AND have all `google.adk.*` types funneled through a single quarantine module
**So that** (a) every log line is joinable against a Phoenix span URL (the recursive observability story), (b) the dynamic-typing surface of the ADK SDK is contained per ADR-001 + `best-practices/03 §3`, and (c) future SDK upgrades only touch one file instead of every business-logic module

---

## File modification map

Exact files the coding agent creates or modifies for this story:

- `apps/chaoslab-agent/src/chaoslab_agent/observability.py` — NEW — defines:
  - `setup_logging(env: str = "production") -> None` — configures structlog per `best-practices/03 §11` and `coding-standards.md`. Processors: `contextvars.merge_contextvars`, `add_log_level`, `TimeStamper(fmt="iso")`, `_add_phoenix_trace_id` (custom processor), `JSONRenderer()` if `env=="production"` else `ConsoleRenderer(colors=True)`. `wrapper_class=structlog.make_filtering_bound_logger(logging.INFO)`. `cache_logger_on_first_use=True`.
  - `_add_phoenix_trace_id(_logger, _method_name, event_dict) -> dict` — internal processor. Reads `opentelemetry.trace.get_current_span()`; if `span.is_recording()` and span context is valid, injects `event_dict["trace_id"] = format(ctx.trace_id, "032x")` and `event_dict["span_id"] = format(ctx.span_id, "016x")`. Returns the event_dict.
  - `setup_phoenix_otel(settings: Settings) -> None` — calls `phoenix.otel.register(project_name="chaoslab", endpoint=settings.phoenix_collector_endpoint, api_key=settings.phoenix_api_key.get_secret_value())`. Then `GoogleADKInstrumentor().instrument()` (from `openinference-instrumentation-google-adk`). MUST be called BEFORE any `google.adk.*` import (per `coding-standards.md` ADK-specific patterns + ADR-005).
  - `get_logger(name: str | None = None) -> structlog.BoundLogger` — thin wrapper around `structlog.get_logger`. ~80 lines total.
- `apps/chaoslab-agent/src/chaoslab_agent/adk_types.py` — NEW — quarantine module. Per ADR-001 + `best-practices/03 §3`, this is the ONLY module in `chaoslab-agent/src/` that imports from `google.adk.*` at module top-level. Re-exports the ADK primitives the rest of `chaoslab_agent.*` uses, wrapped in Pydantic models where the ADK type is too dynamic. Contents:
  - `from google.adk.agents.llm_agent import LlmAgent as _LlmAgent` (re-export as `LlmAgent`)
  - `from google.adk.agents.sequential_agent import SequentialAgent`
  - `from google.adk.agents.parallel_agent import ParallelAgent`
  - `from google.adk.agents.loop_agent import LoopAgent`
  - `from google.adk.tools import FunctionTool`
  - `from google.adk.runners import InMemoryRunner, Runner` (for tests)
  - `from google.adk.events import Event as _Event` (re-export as `AdkEvent`)
  - `from google.adk.tools.base_tool import BaseTool`
  - `class AgentSpec(BaseModel)` — pydantic wrapper carrying `name: str`, `description: str = Field(min_length=20)`, `model: Literal["gemini-3.5-flash"]` (ADR-007 enforced at type level), `output_key: str | None = None`, `tools: list[str] = []` (tool names, resolved separately to avoid serializing FunctionTool). Validators ensure the model is exactly `gemini-3.5-flash`.
  - `class RunState(BaseModel)` — `run_id: str = Field(pattern=r"^run_[a-z0-9]{12}$")`, `phase: Literal["queued", "running", "injecting", "judging", "patching", "done", "error"]`, `target_url: str`, `created_at: str`, `pass_rate_baseline: float | None = None`, `pass_rate_post_patch: float | None = None`, `current_event_index: int = 0`. (Used by S4.2 SSE wiring; defined here for type-safety.)
  - `class RunEvent(BaseModel)` — `event_type: Literal["hello", "phase_change", "attack_progress", "cluster_emitted", "recipe_generated", "done", "error", "heartbeat"]`, `data: dict`, `emitted_at: str`.
  - `__all__` list explicitly enumerates every export so a `from chaoslab_agent.adk_types import *` is safe (it's banned in src/ but tests use it).
  - ~150 lines.
- `apps/chaoslab-agent/src/chaoslab_agent/main.py` — UPDATE — replace the S4.1 `try/except ImportError` guard with a proper startup sequence:

  ```python
  from chaoslab_agent.config import get_settings
  from chaoslab_agent.observability import setup_logging, setup_phoenix_otel

  _settings = get_settings()
  setup_logging(env=_settings.environment)
  setup_phoenix_otel(_settings)
  # NOW it's safe to import google.adk.* (via chaoslab_agent.adk_types)
  from chaoslab_agent.adk_types import LlmAgent, SequentialAgent, RunState, RunEvent
  ```

  Replace direct `google.adk.*` imports throughout `main.py` with imports from `chaoslab_agent.adk_types`. ~30 lines net change.

- `apps/chaoslab-agent/src/chaoslab_agent/orchestrator.py` — UPDATE — replace direct `google.adk.*` imports with `from chaoslab_agent.adk_types import LlmAgent, SequentialAgent`. ~5 lines changed.
- `apps/chaoslab-agent/src/chaoslab_agent/injector/agent.py` — UPDATE — same import-rewrite.
- `apps/chaoslab-agent/src/chaoslab_agent/judge/agent.py` — UPDATE — same import-rewrite.
- `apps/chaoslab-agent/src/chaoslab_agent/patcher/agent.py` — UPDATE — same import-rewrite.
- `apps/chaoslab-agent/tests/unit/test_observability.py` — NEW — at least 10 pytest cases:
  - `setup_logging` runs without error in both `production` and `dev` env.
  - After `setup_logging`, `get_logger().info("test", foo="bar")` produces JSON-parseable output containing `event="test"` + `foo="bar"`.
  - Inside an OTel span (using `tracer.start_as_current_span("test_span"):`), a log line contains both `trace_id` (32 hex chars) and `span_id` (16 hex chars) fields.
  - Outside any span, log lines do NOT contain `trace_id` (the processor only adds when `is_recording()` is true).
  - `_add_phoenix_trace_id` is idempotent — calling twice on the same event_dict does not duplicate keys.
  - `setup_phoenix_otel` is callable and registers a `GoogleADKInstrumentor` (assert via `from openinference.instrumentation.google_adk import GoogleADKInstrumentor; assert GoogleADKInstrumentor().is_instrumented_by_opentelemetry`). Mock the actual `phoenix.otel.register` HTTP call via respx.
  - Logged messages never include the literal `phoenix_api_key.get_secret_value()` string (privacy check).
  - `get_logger("chaoslab_agent.test")` returns a bound logger with the correct name in its output.
  - `setup_logging` is idempotent (calling twice does not double-process events).
  - Log level filtering: `setup_logging(env="production")` → INFO+; `log.debug("x")` produces no output.
    ~180 lines.
- `apps/chaoslab-agent/tests/unit/test_adk_types.py` — NEW — at least 8 pytest cases:
  - `from chaoslab_agent.adk_types import LlmAgent, SequentialAgent, FunctionTool` — all import without error.
  - `AgentSpec(name="x", description="a"*25, model="gemini-3.5-flash")` validates.
  - `AgentSpec(model="gemini-2.5-pro")` raises `ValidationError` (Literal mismatch — ADR-007 enforced at type level).
  - `AgentSpec(name="x", description="short")` raises (description min_length=20).
  - `RunState(run_id="run_abc123def456", phase="queued", target_url="http://x", created_at="2026-06-04T...")` validates.
  - `RunState(run_id="INVALID")` raises (regex mismatch).
  - `RunEvent(event_type="hello", data={"x":1}, emitted_at="...")` validates.
  - `RunEvent(event_type="invalid_kind", ...)` raises (Literal mismatch).
  - **Quarantine assertion:** `grep -lE "^(from|import) google\.adk" apps/chaoslab-agent/src/chaoslab_agent/` returns exactly 1 file (`adk_types.py`). This is the load-bearing architectural invariant — enforced by the test via `subprocess.run(["grep", "-lE", ...])`.
    ~140 lines.

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given chaoslab_agent.observability.setup_logging is called with env="production"
When  pytest captures stderr and calls `get_logger().info("test", foo="bar")`
Then  the captured line parses as JSON
And   parsed["event"] == "test"
And   parsed["foo"] == "bar"
And   parsed["level"] == "info"

Given setup_logging was called AND an OTel tracer wraps the log call in a span
When  the in-span log line is emitted
Then  the JSON has a "trace_id" field of exactly 32 lowercase hex chars
And   a "span_id" field of exactly 16 lowercase hex chars

Given setup_logging was called AND no OTel span is active
When  a log line is emitted
Then  "trace_id" is NOT a key in the parsed JSON

Given `grep -lE "^(from|import) google\.adk" apps/chaoslab-agent/src/chaoslab_agent/` runs
When  the output is inspected
Then  exactly one file is listed: apps/chaoslab-agent/src/chaoslab_agent/adk_types.py
And   no other file under apps/chaoslab-agent/src/ imports google.adk.* at the top level

Given AgentSpec(name="MyAgent", description="A" * 25, model="gemini-3.5-flash")
When  the model is constructed
Then  no ValidationError is raised

Given AgentSpec(name="MyAgent", description="A" * 25, model="gemini-2.5-pro")
When  the model is constructed
Then  pydantic.ValidationError is raised (ADR-007 enforced at type level)

Given AgentSpec(name="X", description="short")
When  the model is constructed
Then  ValidationError is raised (description min_length=20)

Given RunState(run_id="run_abc123def456", phase="queued", target_url="http://x", created_at="2026-06-04T12:00:00Z")
When  the model is constructed
Then  no ValidationError is raised

Given RunState(run_id="INVALID-ID-FORMAT", phase="queued", target_url="http://x", created_at="...")
When  the model is constructed
Then  ValidationError is raised (regex pattern violated)

Given setup_logging is called twice with the same env
When  log lines are emitted between the two calls
Then  the second setup_logging does not crash
And   log lines do not contain duplicated keys

Given `cd apps/chaoslab-agent && uv run pytest tests/unit/test_observability.py tests/unit/test_adk_types.py -v` runs
When  the test suite completes
Then  at least 18 behavioral test cases pass (10 obs + 8 types)

Given the 400-line guard runs
When  `python3 scripts/check_max_lines.py --strict apps/chaoslab-agent/src/` runs
Then  exit code is 0
And   observability.py is ≤ 100 lines (target ~80)
And   adk_types.py is ≤ 200 lines (target ~150)
```

---

## Shell verification

```bash
# 1) Tests pass with ≥18 new cases
cd apps/chaoslab-agent && uv run pytest tests/unit/test_observability.py tests/unit/test_adk_types.py -v 2>&1 | tee /tmp/obs-types.log
grep -E "PASSED" /tmp/obs-types.log | wc -l
# Must output ≥ 18

# 2) Quarantine invariant: only one file imports google.adk.* at the top
QUAR=$(grep -lE "^(from|import) google\.adk" apps/chaoslab-agent/src/chaoslab_agent/ -r | sort -u)
echo "$QUAR"
[ "$QUAR" = "apps/chaoslab-agent/src/chaoslab_agent/adk_types.py" ] || { echo "FAIL: ADK imports outside quarantine"; exit 1; }
echo "OK"
# Must print the single quarantine file then OK

# 3) trace_id appears in log when inside a span
cd apps/chaoslab-agent && uv run python -c "
import io, sys, json
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

provider = TracerProvider()
provider.add_span_processor(SimpleSpanProcessor(InMemorySpanExporter()))
trace.set_tracer_provider(provider)

from chaoslab_agent.observability import setup_logging, get_logger

# Capture stderr
buf = io.StringIO()
sys.stderr = buf
setup_logging(env='production')
log = get_logger()
tracer = trace.get_tracer(__name__)
with tracer.start_as_current_span('test'):
    log.info('inside_span', foo='bar')
sys.stderr = sys.__stderr__

line = buf.getvalue().strip().split('\n')[-1]
parsed = json.loads(line)
assert 'trace_id' in parsed, f'trace_id missing in {parsed}'
assert len(parsed['trace_id']) == 32
assert 'span_id' in parsed
assert len(parsed['span_id']) == 16
assert parsed['foo'] == 'bar'
print('OK')
"
# Must print OK

# 4) §14 clean
git diff main...HEAD -- 'apps/chaoslab-agent/src/**' | grep -E "^\+" | grep -iE "(mock|fake|dummy|hardcoded|simulated)" | grep -v "test\|spec\|§14 carve-out"
# Must output nothing

# 5) 400-line guard
python3 scripts/check_max_lines.py --strict apps/chaoslab-agent/src/
# Must exit 0

# 6) ruff + ty (the quarantine module is where ADK type stubs are partial — ty may need overrides)
cd apps/chaoslab-agent && uv run ruff check . && uv run ruff format . --check && uv run ty check src/ && cd -
# Must exit 0

# 7) green-light
.claude/scripts/green-light.sh
# Must exit 0
```

---

## Notes for coding agent

- **Why two files, not one.** The prompt explicitly splits into `observability.py` (~80 LOC) and `adk_types.py` (~150 LOC) — two files, each well under 400. Do not merge them — the 400-line rule is a hard ceiling and the quarantine architectural invariant deserves its own file with a clear purpose statement at the top.
- **`_add_phoenix_trace_id` is the load-bearing processor.** Per `best-practices/03 §11`:

  ```python
  from opentelemetry import trace

  def _add_phoenix_trace_id(_logger, _method_name, event_dict):
      span = trace.get_current_span()
      if span.is_recording():
          ctx = span.get_span_context()
          event_dict["trace_id"] = format(ctx.trace_id, "032x")
          event_dict["span_id"] = format(ctx.span_id, "016x")
      return event_dict
  ```

  The `is_recording()` check is critical — outside a span, `get_current_span()` returns a NonRecordingSpan with `trace_id=0`, and we DON'T want zero-padded fake trace IDs in logs. The BDD asserts both the in-span and outside-span paths.

- **Idempotence of `setup_logging`.** structlog's `cache_logger_on_first_use=True` means the first `get_logger` call freezes the processor chain. Subsequent `setup_logging` calls technically reconfigure but cached loggers don't pick it up. The test asserts no crash; do not over-engineer (this matches the structlog docs' guidance).
- **Quarantine invariant is THE architectural guarantee.** Per ADR-001 + `best-practices/03 §3`: `google.adk.*` ships partial type stubs and dynamic types. By funneling EVERY `google.adk` import through one file, type-check failures land in one well-known place, SDK upgrades touch one file, and business-logic modules stay strict-typed against the local pydantic shape. The grep-based BDD enforces this — if any other src file imports `google.adk.*` at module top level, the gate fails. **Function-local imports inside `if TYPE_CHECKING:` blocks are allowed** (they don't execute at runtime); the grep regex `^(from|import) google\.adk` is anchored to BOL so leading whitespace is fine.
- **`AgentSpec.model: Literal["gemini-3.5-flash"]`** enforces ADR-007 at the type level — pydantic raises on construction if any other string. Belt-and-suspenders with the runtime validator in `config.py`. The BDD has both checks.
- **`RunState` + `RunEvent` are the SSE wire types.** The frontend (E7) consumes JSON-serialized `RunEvent` objects via SSE. Keep the `event_type` Literal closed — every new event type lands here first. `data: dict` is intentionally loose — typed payloads can be Pydantic-discriminated-union later if the wire format settles.
- **`setup_phoenix_otel` ordering.** Per `coding-standards.md` ADK-specific patterns: `setup_phoenix_otel` MUST run BEFORE any `google.adk.*` import. The pattern in `main.py`:
  ```python
  from chaoslab_agent.config import get_settings
  from chaoslab_agent.observability import setup_logging, setup_phoenix_otel
  _settings = get_settings()
  setup_logging(env=_settings.environment)
  setup_phoenix_otel(_settings)
  # NOW safe to import ADK:
  from chaoslab_agent.adk_types import LlmAgent, SequentialAgent
  ```
  This ordering is enforced socially via the lint rule `T20` (no print) + a comment in `main.py` + the quarantine grep.
- **`phoenix.otel.register` rate limits.** Per Phoenix-Cloud free tier (25k spans/month), `setup_phoenix_otel` only runs once at process startup. Tests mock it via respx so no real spans count against the dev quota.
- **`GoogleADKInstrumentor` is a singleton.** Multiple `instrument()` calls in a process trigger a warning ("Already instrumented"). The `is_instrumented_by_opentelemetry` property gates re-instrumentation:
  ```python
  inst = GoogleADKInstrumentor()
  if not inst.is_instrumented_by_opentelemetry:
      inst.instrument()
  ```
- **Never log secrets.** Per `coding-standards.md` standards: `pydantic.SecretStr` values are NEVER `str()`-ed in log calls. Tests grep the captured log output for the literal value of `phoenix_api_key.get_secret_value()` and assert it is NOT present.
- **Cross-reference docs:**
  - `/Users/abu/dev/hackathon/rapid-agents/research/google-cloud-rapid-agent/best-practices/03-code-quality-enforcement.md` §11 (structlog setup) + §3 (ADK quarantine rationale)
  - `/Users/abu/dev/hackathon/rapid-agents/docs/coding-standards.md` (structlog code template + ADK-specific patterns)
  - `/Users/abu/dev/hackathon/rapid-agents/docs/architecture.md` ADR-001 (ty + quarantine), ADR-005 (Phoenix MCP partial — sets the OTel + instrumentation context)
