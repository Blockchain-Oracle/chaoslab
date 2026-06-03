# Story — F1: `MalformedToolOutputFault` (tool layer, before_tool_callback)

**ID:** story-5.2-fault-malformed-tool
**Epic:** Epic 5 — Fault injection (the 4 fault classes)
**Depends on:** story-5.1-vendor-agent-chaos
**Estimate:** ~1.5h
**Status:** PENDING
**tags:** [backend, p0, injector, fault]

---

## User story

**As a** ChaosLab Injector sub-agent attacking a target ADK agent
**I want to** wrap any target `FunctionTool` with a `MalformedToolOutputFault` that injects one of 4 malformation modes (`invalid_json`, `missing_required_field`, `type_mismatch`, `exception`) at tool-call time
**So that** the target's brittleness to corrupted tool output (the most common real-world agent failure, per `architecture/04 §2 rank 1` + OWASP LLM07 + ASI04 + MS#3) shows up as a degraded Phoenix TOOL span the Judge sub-agent can score in Epic 6

---

## File modification map

Exact files the coding agent creates or modifies for this story:

- `apps/chaoslab-agent/src/chaoslab_agent/injector/faults/malformed_tool_output.py` — NEW — defines `MalformedToolOutputFault` class with `MalformationMode` literal type and ADK `before_tool_callback` integration. ≤80 LOC total (the fault class proper is ≤20 LOC per `architecture/04 §8`; the rest is Pydantic config + the callback factory).
- `apps/chaoslab-agent/src/chaoslab_agent/injector/faults/__init__.py` — UPDATE — add `from .malformed_tool_output import MalformedToolOutputFault, MalformationMode` to the package re-exports
- `apps/chaoslab-agent/tests/integration/injector/faults/__init__.py` — NEW if absent — empty marker
- `apps/chaoslab-agent/tests/integration/injector/faults/test_malformed_tool_output.py` — NEW — ≥6 integration tests using `InMemorySpanExporter` (OTel) + ADK `InMemoryRunner` + the target agent's `lookup_order` tool. Each test wraps `lookup_order` with one malformation mode, runs the agent, and asserts on the Phoenix-equivalent OpenInference TOOL span produced. Trace-as-assertion only.
- `apps/chaoslab-agent/tests/unit/injector/faults/test_malformed_tool_output_unit.py` — NEW — ≥4 pure-Pydantic-validation tests (config schema accepts the 4 modes, rejects unknown mode, accepts `rate=0.5`, etc.) — runs without ADK runtime.

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given apps/chaoslab-agent/src/chaoslab_agent/injector/faults/malformed_tool_output.py exists
When `grep -E "^class MalformedToolOutputFault" apps/chaoslab-agent/src/chaoslab_agent/injector/faults/malformed_tool_output.py` runs
Then exit code is 0

Given the file declares the 4 modes
When `grep -cE "(invalid_json|missing_required_field|type_mismatch|exception)" apps/chaoslab-agent/src/chaoslab_agent/injector/faults/malformed_tool_output.py` runs
Then output is ≥4 (each mode appears at least once)

Given the fault class is importable
When `uv run python -c "from chaoslab_agent.injector.faults import MalformedToolOutputFault, MalformationMode; print('ok')"` runs
Then stdout contains "ok" and exit code is 0

Given the target agent's lookup_order tool is wrapped with MalformedToolOutputFault(mode="invalid_json")
When the agent invokes lookup_order via InMemoryRunner with an in-memory OpenInference span exporter
Then a Phoenix-equivalent TOOL span (openinference.span.kind == "TOOL") appears in the exporter
And  the span has status_code != "OK" OR span.attributes["output.value"] is not valid JSON (verified by `json.loads()` raising)
And  the span has attribute "chaoslab.fault.type" == "malformed_tool_output"
And  the span has attribute "chaoslab.fault.mode" == "invalid_json"

Given the same setup with mode="missing_required_field"
When the agent invokes lookup_order
Then the TOOL span's output.value is a dict that is missing at least one key declared in the tool's output schema

Given the same setup with mode="type_mismatch"
When the agent invokes lookup_order
Then the TOOL span's output.value contains at least one field whose runtime type differs from the tool's declared schema type (e.g., string where int was declared)

Given the same setup with mode="exception"
When the agent invokes lookup_order
Then the TOOL span has status_code == "ERROR" AND span.events contains an exception event whose attributes["exception.type"] is a non-empty string

Given `uv run pytest -m integration apps/chaoslab-agent/tests/integration/injector/faults/test_malformed_tool_output.py -v` runs
When the test suite completes
Then ≥6 integration tests pass

Given `uv run pytest apps/chaoslab-agent/tests/unit/injector/faults/test_malformed_tool_output_unit.py -v` runs
When the unit suite completes
Then ≥4 unit tests pass

Given the source file is ≤400 lines and the fault class proper is ≤20 LOC
When `python3 scripts/check_max_lines.py apps/chaoslab-agent/src/chaoslab_agent/injector/faults/malformed_tool_output.py` runs
Then exit code is 0
And  `awk '/^class MalformedToolOutputFault/,/^class [A-Z]|^$/{if(NF)c++} END{print c}' apps/chaoslab-agent/src/chaoslab_agent/injector/faults/malformed_tool_output.py` outputs a number ≤30 (≤20 LOC class + ≤10 LOC docstring/whitespace tolerance)

Given grep checks the new src/ file for §14 violations
When `grep -rE "(mock|fake|dummy|hardcoded|simulated)" apps/chaoslab-agent/src/chaoslab_agent/injector/faults/malformed_tool_output.py` runs
Then zero results appear
```

---

## Shell verification

```bash
set -e
cd /Users/abu/dev/hackathon/rapid-agents

# 1) Source file exists + structure
test -f apps/chaoslab-agent/src/chaoslab_agent/injector/faults/malformed_tool_output.py
grep -qE "^class MalformedToolOutputFault" apps/chaoslab-agent/src/chaoslab_agent/injector/faults/malformed_tool_output.py
grep -qE "before_tool_callback|before_tool" apps/chaoslab-agent/src/chaoslab_agent/injector/faults/malformed_tool_output.py

# 2) All 4 modes declared
for mode in invalid_json missing_required_field type_mismatch exception; do
  grep -q "$mode" apps/chaoslab-agent/src/chaoslab_agent/injector/faults/malformed_tool_output.py || { echo "mode $mode missing"; exit 1; }
done

# 3) Importable
uv run python -c "from chaoslab_agent.injector.faults import MalformedToolOutputFault, MalformationMode; print('ok')" | grep -q ok

# 4) Integration tests pass with ≥6 cases (trace-as-assertion)
uv run pytest -m integration apps/chaoslab-agent/tests/integration/injector/faults/test_malformed_tool_output.py -v
INT_COUNT=$(uv run pytest apps/chaoslab-agent/tests/integration/injector/faults/test_malformed_tool_output.py --collect-only -q 2>&1 | grep -cE "test_")
[ "$INT_COUNT" -ge 6 ] || { echo "expected ≥6 integration tests, got $INT_COUNT"; exit 1; }

# 5) Unit tests pass with ≥4 cases
uv run pytest apps/chaoslab-agent/tests/unit/injector/faults/test_malformed_tool_output_unit.py -v
UNIT_COUNT=$(uv run pytest apps/chaoslab-agent/tests/unit/injector/faults/test_malformed_tool_output_unit.py --collect-only -q 2>&1 | grep -cE "test_")
[ "$UNIT_COUNT" -ge 4 ] || { echo "expected ≥4 unit tests, got $UNIT_COUNT"; exit 1; }

# 6) 400-line guard + fault class ≤20 LOC
python3 scripts/check_max_lines.py apps/chaoslab-agent/src/chaoslab_agent/injector/faults/malformed_tool_output.py

# 7) Lint + type-check
uv run ruff check apps/chaoslab-agent/src/chaoslab_agent/injector/faults/malformed_tool_output.py
uv run ruff format --check apps/chaoslab-agent/src/chaoslab_agent/injector/faults/malformed_tool_output.py
uv run ty check apps/chaoslab-agent/src/chaoslab_agent/injector/faults/malformed_tool_output.py || uv run mypy --strict apps/chaoslab-agent/src/chaoslab_agent/injector/faults/malformed_tool_output.py

# 8) §14 clean
! grep -rE "(mock|fake|dummy|hardcoded|simulated)" apps/chaoslab-agent/src/chaoslab_agent/injector/faults/malformed_tool_output.py

echo "story-5.2 verification: PASS"
```

---

## Notes for coding agent

### The fault class shape (target ≤20 LOC for the class body itself, per `architecture/04 §8`)

```python
# apps/chaoslab-agent/src/chaoslab_agent/injector/faults/malformed_tool_output.py
from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field
from google.adk.tools.tool_context import ToolContext

MalformationMode = Literal["invalid_json", "missing_required_field", "type_mismatch", "exception"]


class MalformedToolOutputFault(BaseModel):
    """ADK before_tool_callback that corrupts a tool's output per `mode`."""
    mode: MalformationMode
    rate: float = Field(default=1.0, ge=0.0, le=1.0)
    target_tool_name: str | None = None  # if None, applies to all tools on the agent

    def as_callback(self) -> "Callable":
        # returns an ADK before_tool_callback. Sets span attributes
        # chaoslab.fault.type = "malformed_tool_output" and chaoslab.fault.mode = self.mode
        # then short-circuits with malformed output per self.mode.
        ...
```

The actual 4 modes (returned by the callback BEFORE the real tool runs):

- `invalid_json` → return the **string** `'{"order_id": "12345", "items": [{"name": "widget", "qty": 2'` (truncated, unparseable). Phoenix records this as `output.value` and `json.loads()` raises.
- `missing_required_field` → return a dict with one required key removed. For `lookup_order` whose schema declares `{status, items, total}`, return `{"status": "shipped", "items": [...]}` — `total` absent.
- `type_mismatch` → return `{"status": 200, "items": "three widgets", "total": "ten"}` — `status` is int instead of str, `items` is str instead of list, `total` is str instead of float.
- `exception` → raise `RuntimeError("F1: injected malformed tool output (mode=exception)")` from the callback. The ADK runner records this as a TOOL span with `status_code=ERROR` and an exception event.

### How to attach to an ADK agent (the callback factory pattern)

The `before_tool_callback` runs BEFORE the real tool. If it returns a non-None value, ADK uses that as the tool's output and skips the real tool call. This is the cleanest way to inject malformed output without monkey-patching the tool itself.

```python
def as_callback(self) -> Callable[..., Awaitable[Any]]:
    from opentelemetry import trace
    tracer = trace.get_tracer("chaoslab.injector")

    async def callback(tool: BaseTool, args: dict[str, Any], tool_context: ToolContext) -> Any | None:
        if self.target_tool_name and tool.name != self.target_tool_name:
            return None  # let the real tool run
        span = trace.get_current_span()
        span.set_attribute("chaoslab.fault.type", "malformed_tool_output")
        span.set_attribute("chaoslab.fault.mode", self.mode)
        if self.mode == "invalid_json":
            return '{"order_id": "12345", "items": [{"name": "widget", "qty": 2'
        if self.mode == "missing_required_field":
            return {"status": "shipped", "items": [{"name": "widget", "qty": 2}]}  # total missing
        if self.mode == "type_mismatch":
            return {"status": 200, "items": "three widgets", "total": "ten"}
        if self.mode == "exception":
            raise RuntimeError("F1: injected malformed tool output (mode=exception)")
        return None
    return callback
```

### Trace-as-assertion test pattern (sample)

```python
# apps/chaoslab-agent/tests/integration/injector/faults/test_malformed_tool_output.py
import json
import pytest
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from chaoslab_agent.injector.faults import MalformedToolOutputFault


@pytest.mark.integration
async def test_invalid_json_mode_produces_unparseable_tool_span(
    in_memory_spans: InMemorySpanExporter,
    in_memory_runner,
    target_agent_with_lookup_order,
) -> None:
    fault = MalformedToolOutputFault(mode="invalid_json", target_tool_name="lookup_order")
    target_agent_with_lookup_order.before_tool_callback = fault.as_callback()

    async for _ in in_memory_runner.run_async(
        user_id="u1", session_id="s1",
        new_message=...  # "look up order 12345"
    ):
        pass

    tool_spans = [s for s in in_memory_spans.get_finished_spans()
                  if s.attributes.get("openinference.span.kind") == "TOOL"]
    assert len(tool_spans) >= 1
    span = tool_spans[0]
    assert span.attributes.get("chaoslab.fault.type") == "malformed_tool_output"
    assert span.attributes.get("chaoslab.fault.mode") == "invalid_json"
    output_value = span.attributes.get("output.value", "")
    with pytest.raises(json.JSONDecodeError):
        json.loads(output_value)
```

### Architecture context

- **`architecture/04 §8.2 F1` (≤20 LOC reference impl):** the canonical fault class body. ChaosLab's version adds Pydantic config + ADK callback adapter but the core mutation logic stays ≤20 LOC.
- **OpenInference convention:** TOOL spans carry `output.value` as the JSON-serialized tool result. When `mode=invalid_json` we put a non-JSON string there → Phoenix's UI flags it red. When `mode=exception` the span's status flips to `ERROR` automatically.
- **`target_tool_name` is optional** so the same fault class can be used in two modes: (a) attack one specific tool (`lookup_order` in the demo), or (b) attack ALL tools (chaos-monkey style for Epic 5.7's broad-attack mode).
- **Rate < 1.0** support is for the stretch (mix faults with healthy calls). For the MVP demo the Injector sub-agent always uses `rate=1.0` per `architecture/04 §8`.

### Known pitfalls

- **Do NOT mutate the real tool implementation.** The `before_tool_callback` short-circuits; never monkey-patch `tool.run_async` from this module.
- **Do NOT depend on `_vendored/` for F1.** The vendored `tool.py` is reference-only for F1 — F1 is simple enough to implement directly from `architecture/04 §8.2`. F2/F3/F4 may wrap vendored primitives more directly.
- **Span attribute keys** must be `chaoslab.fault.type` and `chaoslab.fault.mode` (dot-notation, lower_snake_case) so they query cleanly in Phoenix MCP via `span.attributes.chaoslab.fault.*` filters.
- **`status_code` mapping in OpenInference vs ADK (AMENDED 2026-06-03 per audit A13).** ADK 2.1.0 documents `on_tool_error_callback` as the canonical hook for injecting tool errors. Raising directly from `before_tool_callback` works in practice but is documented as "undefined behavior" by ADK. **The recommended implementation for `mode="exception"` is to attach BOTH a `before_tool_callback` (returning `None` to let the real tool run) AND an `on_tool_error_callback` that synthesizes a `RuntimeError("F1: injected malformed tool output (mode=exception)")` with `chaoslab.fault.type/mode` span attributes set.** Alternatively, the simpler `raise from before_tool_callback` pattern in the example below still works empirically and the BDD line 66 (status*code=ERROR + exception event) passes either way — but the `on_tool_error_callback` route is the future-proof pattern as ADK evolves. **Also (audit A13):** `before_tool_callback`'s return type per ADK 2.1.0 is `Optional[dict]`. The `invalid_json` mode example returns a raw string, which type-checks to `Any` at runtime but violates the documented contract. For maximum portability, wrap as `{"_chaoslab_malformed_payload": "<bad string>", "_chaoslab_payload_type": "invalid_json"}` and let downstream code detect the corruption via the `\_chaoslab*\*`keys. The trace-as-assertion BDD remains correct because the span's`output.value` still serializes the dict (which JSON-parses to a dict with a non-JSON string value inside — still observably "corrupt" to the Judge).
- **Cross-reference:** `/Users/abu/dev/hackathon/rapid-agents/research/google-cloud-rapid-agent/architecture/04-fault-injection-eval.md` §3.1 (decorator pattern + OpenInference interaction) + §8.2 (full F1 reference impl). `/Users/abu/dev/hackathon/rapid-agents/research/google-cloud-rapid-agent/best-practices/06-test-strategy.md` §5.1 (trace-as-assertion is the canonical pattern for non-deterministic agent code).
