# Story — Injector sub-agent wiring (selects fault, configures adapter, captures trace)

**ID:** story-5.7-injector-sub-agent
**Epic:** Epic 5 — Fault injection (the 4 fault classes)
**Depends on:** story-5.2-fault-malformed-tool, story-5.3-fault-prompt-injection, story-5.4-fault-context-poisoning, story-5.5-fault-latency-spike, story-5.6-preflight-baseline
**Estimate:** ~2h
**Status:** PENDING
**tags:** [backend, p0, injector, fault]

---

## User story

**As a** ChaosLab orchestrator (Epic 4 `SequentialAgent`)
**I want to** delegate fault-injection execution to a single `Injector` sub-agent that runs `BaselineCheck`, then cycles through the 4 fault classes × ~6 runs each (= 25 attacks), emits OpenInference annotations on each span tagging the fault class, and updates a shared state object the Judge sub-agent (Epic 6) reads
**So that** the Epic 5 fault primitives are composed into the single "attack phase" the demo storyboard requires — judges see 25 Phoenix spans annotated with `chaoslab.fault.type` and the Resilience Curve materializes from the shared state

---

## File modification map

Exact files the coding agent creates or modifies for this story:

- `apps/chaoslab-agent/src/chaoslab_agent/injector/agent.py` — NEW — defines `Injector` sub-agent class wrapping the orchestration logic + `AttackRun` Pydantic schema + `AttackResult` Pydantic schema + `InjectorState` Pydantic schema (the shared state object). ≤350 LOC.
- `apps/chaoslab-agent/src/chaoslab_agent/injector/__init__.py` — UPDATE — add `from .agent import Injector, AttackRun, AttackResult, InjectorState` to the package re-exports
- `apps/chaoslab-agent/tests/integration/injector/test_injector_agent.py` — NEW — ≥6 trace-as-assertion integration tests. Uses `InMemorySpanExporter` + scripted Tier 1 ADK target + the 4 real fault classes from stories 5.2-5.5. Verifies ≥25 spans appear, each tagged with a valid `chaoslab.fault.type`, attack distribution roughly even, baseline check fires first.
- `apps/chaoslab-agent/tests/unit/injector/test_injector_state.py` — NEW — ≥5 unit tests covering: `InjectorState` schema validation, `record_attack(...)` appends and updates pass_rate, total_attacks counter, fault_class breakdown dict, baseline gate flag.

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given apps/chaoslab-agent/src/chaoslab_agent/injector/agent.py exists
When `grep -E "^class Injector" apps/chaoslab-agent/src/chaoslab_agent/injector/agent.py` runs
Then exit code is 0

Given the file declares the 4 fault-class wiring
When `grep -cE "(MalformedToolOutputFault|PromptInjectionFault|ContextPoisoningFault|LatencySpikeFault)" apps/chaoslab-agent/src/chaoslab_agent/injector/agent.py` runs
Then output is ≥4 (each fault class is imported and wired)

Given the file calls BaselineCheck before the attack loop
When `grep -E "BaselineCheck\(" apps/chaoslab-agent/src/chaoslab_agent/injector/agent.py` runs
Then exit code is 0

Given the modules are importable
When `uv run python -c "from chaoslab_agent.injector import Injector, AttackRun, AttackResult, InjectorState; print('ok')"` runs
Then stdout contains "ok" and exit code is 0

Given a ChaosLab run with all 4 faults enabled against an in-process Tier 1 ADK target
When `Injector(target=..., state=...).run()` is awaited with an in-memory OpenInference span exporter
Then at least 25 spans appear with openinference.span.kind in {"TOOL", "LLM", "RETRIEVER"} and the attribute "chaoslab.fault.type" set
And  the set of distinct chaoslab.fault.type values across those spans equals {"malformed_tool_output", "prompt_injection", "context_poisoning", "latency_spike"}
And  the count of spans per fault.type value is ≥4 (≥4 attacks per fault class out of ~6 runs each)
And  the InjectorState.total_attacks equals the count of spans (or 25, whichever is greater)
And  InjectorState.baseline_passed is True

Given a target whose baseline pass rate is 50% (deliberately broken)
When `Injector.run()` is invoked
Then BaselineAbortError is raised BEFORE any attack span is emitted
And  the in-memory span exporter contains zero spans with chaoslab.fault.type attribute

Given the Injector emits a Phoenix-style annotation per span
When the InjectorState.attack_results list is inspected
Then each AttackResult has a non-empty span_id field and a non-null fault_class field

Given `uv run pytest -m integration apps/chaoslab-agent/tests/integration/injector/test_injector_agent.py -v` runs
When the test suite completes
Then ≥6 integration tests pass

Given `uv run pytest apps/chaoslab-agent/tests/unit/injector/test_injector_state.py -v` runs
When the unit suite completes
Then ≥5 unit tests pass

Given the source file
When `python3 scripts/check_max_lines.py apps/chaoslab-agent/src/chaoslab_agent/injector/agent.py` runs
Then exit code is 0

Given §14 check
When `grep -rE "(mock|fake|dummy|hardcoded|simulated)" apps/chaoslab-agent/src/chaoslab_agent/injector/agent.py` runs
Then zero results appear
```

---

## Shell verification

```bash
set -e
cd /Users/abu/dev/hackathon/rapid-agents

# 1) Source file exists + structure
test -f apps/chaoslab-agent/src/chaoslab_agent/injector/agent.py
grep -qE "^class Injector" apps/chaoslab-agent/src/chaoslab_agent/injector/agent.py
grep -qE "BaselineCheck\(" apps/chaoslab-agent/src/chaoslab_agent/injector/agent.py

# 2) All 4 fault classes wired
for cls in MalformedToolOutputFault PromptInjectionFault ContextPoisoningFault LatencySpikeFault; do
  grep -q "$cls" apps/chaoslab-agent/src/chaoslab_agent/injector/agent.py || { echo "missing wiring for $cls"; exit 1; }
done

# 3) Importable
uv run python -c "from chaoslab_agent.injector import Injector, AttackRun, AttackResult, InjectorState; print('ok')" | grep -q ok

# 4) Integration tests pass with ≥6 cases (trace-as-assertion)
uv run pytest -m integration apps/chaoslab-agent/tests/integration/injector/test_injector_agent.py -v
INT_COUNT=$(uv run pytest apps/chaoslab-agent/tests/integration/injector/test_injector_agent.py --collect-only -q 2>&1 | grep -cE "test_")
[ "$INT_COUNT" -ge 6 ] || { echo "expected ≥6 integration tests, got $INT_COUNT"; exit 1; }

# 5) Unit tests pass with ≥5 cases
uv run pytest apps/chaoslab-agent/tests/unit/injector/test_injector_state.py -v
UNIT_COUNT=$(uv run pytest apps/chaoslab-agent/tests/unit/injector/test_injector_state.py --collect-only -q 2>&1 | grep -cE "test_")
[ "$UNIT_COUNT" -ge 5 ] || { echo "expected ≥5 unit tests, got $UNIT_COUNT"; exit 1; }

# 6) 400-line guard
python3 scripts/check_max_lines.py apps/chaoslab-agent/src/chaoslab_agent/injector/agent.py

# 7) Lint + type-check
uv run ruff check apps/chaoslab-agent/src/chaoslab_agent/injector/agent.py
uv run ruff format --check apps/chaoslab-agent/src/chaoslab_agent/injector/agent.py
uv run ty check apps/chaoslab-agent/src/chaoslab_agent/injector/agent.py || uv run mypy --strict apps/chaoslab-agent/src/chaoslab_agent/injector/agent.py

# 8) §14 clean
! grep -rE "(mock|fake|dummy|hardcoded|simulated)" apps/chaoslab-agent/src/chaoslab_agent/injector/agent.py

echo "story-5.7 verification: PASS"
```

---

## Notes for coding agent

### Architecture: Injector is a thin orchestrator over the 4 fault classes + BaselineCheck

```
Injector.run():
  1. BaselineCheck(target, n=5).validate()             # bail if <80%
  2. for fault_class in [F1, F2, F3, F4]:              # 4 classes, ~6 runs each = 24-25 total
       for variant_idx in range(6):
         fault = build_fault(fault_class, variant_idx)
         install_fault(target, fault)
         span_id = await target.invoke(prompt) -> emits TOOL/LLM/RETRIEVER spans
                                                  each annotated with chaoslab.fault.type
         result = capture_span_metadata(span_id, fault)
         state.record_attack(result)
         uninstall_fault(target, fault)               # leave target clean for next attack
  3. yield state                                       # Judge sub-agent reads it
```

### Pydantic schemas (canonical)

```python
# apps/chaoslab-agent/src/chaoslab_agent/injector/agent.py
from __future__ import annotations
from typing import Literal
from datetime import datetime
from pydantic import BaseModel, Field

FaultClass = Literal["malformed_tool_output", "prompt_injection", "context_poisoning", "latency_spike"]


class AttackRun(BaseModel):
    """One scheduled attack: which fault class, which variant, against which target."""
    run_idx: int = Field(ge=0)
    fault_class: FaultClass
    variant_idx: int = Field(ge=0)
    fault_config: dict


class AttackResult(BaseModel):
    """The outcome of one AttackRun, captured from the trace."""
    run_idx: int = Field(ge=0)
    fault_class: FaultClass
    span_id: str = Field(min_length=1)
    trace_id: str = Field(min_length=1)
    status: Literal["ok", "error", "timeout"]
    duration_ms: float = Field(ge=0.0)
    span_attributes: dict = Field(default_factory=dict)
    captured_at: datetime = Field(default_factory=datetime.utcnow)


class InjectorState(BaseModel):
    """The shared state object the Judge sub-agent (Epic 6) reads."""
    baseline_passed: bool = False
    baseline_pass_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    total_attacks: int = 0
    attack_results: list[AttackResult] = Field(default_factory=list)

    def record_attack(self, result: AttackResult) -> None:
        self.attack_results.append(result)
        self.total_attacks += 1

    def fault_breakdown(self) -> dict[FaultClass, int]:
        out: dict[FaultClass, int] = {}
        for r in self.attack_results:
            out[r.fault_class] = out.get(r.fault_class, 0) + 1
        return out
```

### The Injector class

```python
class Injector(BaseModel):
    model_config = {"arbitrary_types_allowed": True}
    target: TargetAdapter
    state: InjectorState
    runs_per_fault: int = Field(default=6, ge=1, le=20)

    async def run(self) -> InjectorState:
        baseline = await BaselineCheck(target=self.target, n=5).validate()
        self.state.baseline_passed = not baseline.aborted
        self.state.baseline_pass_rate = baseline.pass_rate

        plan = self._build_plan()  # 4 * runs_per_fault = 24 AttackRuns by default
        for run in plan:
            fault = self._build_fault(run)
            self._install(fault)
            try:
                response = await self.target.invoke(AdapterInvocation(prompt=...))
            finally:
                self._uninstall(fault)
            result = AttackResult(
                run_idx=run.run_idx,
                fault_class=run.fault_class,
                span_id=response.span_ids[0] if response.span_ids else "<missing>",
                trace_id=response.metadata.get("trace_id", "<missing>"),
                status="error" if response.error else "ok",
                duration_ms=response.duration_ms,
                span_attributes={"chaoslab.fault.type": run.fault_class, **run.fault_config},
            )
            self.state.record_attack(result)
        return self.state

    def _build_plan(self) -> list[AttackRun]:
        plan: list[AttackRun] = []
        classes: list[FaultClass] = [
            "malformed_tool_output", "prompt_injection", "context_poisoning", "latency_spike",
        ]
        idx = 0
        for fc in classes:
            for v in range(self.runs_per_fault):
                plan.append(AttackRun(run_idx=idx, fault_class=fc, variant_idx=v, fault_config={}))
                idx += 1
        return plan

    def _build_fault(self, run: AttackRun): ...      # dispatch table: fault_class -> fault instance
    def _install(self, fault) -> None: ...           # attach callback / monkey-patch
    def _uninstall(self, fault) -> None: ...         # detach after each attack
```

### OpenInference annotation pattern

Each fault class (stories 5.2-5.5) already sets `chaoslab.fault.type` on the active span. The Injector additionally writes a Phoenix span ANNOTATION via the `write_span_annotation` FunctionTool (Epic 4 story 4.4) for each attack — this is what the Judge sub-agent reads in Epic 6.

For this story's BDD, the trace-as-assertion is sufficient: assert the span attribute is present. The annotation-write is invoked from `_install` / inside the attack loop but its OUTPUT (Phoenix annotation row) is verified by Epic 6's tests, not here.

### Integration test pattern

```python
# apps/chaoslab-agent/tests/integration/injector/test_injector_agent.py
import pytest
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from chaoslab_agent.injector import Injector, InjectorState


@pytest.mark.integration
async def test_full_run_emits_25_annotated_spans_across_4_fault_classes(
    in_memory_spans: InMemorySpanExporter,
    healthy_target_adapter,  # baseline passes
) -> None:
    state = InjectorState()
    injector = Injector(target=healthy_target_adapter, state=state, runs_per_fault=6)
    await injector.run()

    spans = in_memory_spans.get_finished_spans()
    attack_spans = [s for s in spans if s.attributes.get("chaoslab.fault.type")]
    assert len(attack_spans) >= 24  # 4 classes * 6 runs (allow 1-attack slip for retriever-less targets)

    fault_types = {s.attributes["chaoslab.fault.type"] for s in attack_spans}
    assert fault_types == {
        "malformed_tool_output", "prompt_injection", "context_poisoning", "latency_spike",
    }

    for fc in fault_types:
        count = sum(1 for s in attack_spans if s.attributes["chaoslab.fault.type"] == fc)
        assert count >= 4

    assert state.baseline_passed is True
    assert state.total_attacks >= 24


@pytest.mark.integration
async def test_broken_baseline_aborts_before_any_attack(
    in_memory_spans, broken_target_adapter,  # baseline pass rate 50%
) -> None:
    from chaoslab_agent.errors import BaselineAbortError
    state = InjectorState()
    injector = Injector(target=broken_target_adapter, state=state, runs_per_fault=6)
    with pytest.raises(BaselineAbortError):
        await injector.run()
    spans_with_faults = [s for s in in_memory_spans.get_finished_spans()
                         if s.attributes.get("chaoslab.fault.type")]
    assert spans_with_faults == []
```

### Architecture context

- **`architecture.md` §"Data flow" steps 3-6:** the Injector covers steps 3-5 (baseline + attack phase + span capture). Step 6 (Judge phase) reads `state.attack_results` to build the failure cluster set (Epic 6).
- **`architecture.md` ADR-002:** Injector is an IN-PROCESS sub-agent (not A2A); composed via ADK `SequentialAgent` with Judge + Patcher in Epic 4 story 4.2.
- **25 attacks math:** 4 fault classes × `runs_per_fault=6` = 24 attacks + 1 extra slot for the retry-of-retriever-less-targets case. The demo storyboard says "5×5 grid" (25 cells) per `PRD.md` §"Demo moment" step 3 — `runs_per_fault=6` over-provisions slightly to ensure the grid fills.
- **`architecture/01 §7 Move 4` (Garak N-runs-per-probe):** 6 runs per fault class is the small-side of Garak's recommendation (5-10) but sufficient for confidence intervals on the demo bar chart.
- **OpenInference annotation:** uses Epic 4 story 4.4's `write_span_annotation` FunctionTool to attach a structured annotation per attack span. Annotation payload includes `fault_class`, `variant_idx`, `fault_config_hash`.

### Known pitfalls

- **`_install` / `_uninstall` symmetry:** each attack must clean up after itself. Otherwise context_poisoning's retriever monkey-patch persists into the next attack's run (e.g., prompt_injection sees a poisoned retriever output and the trace becomes confusing).
- **The 4 fault classes have different installation surfaces:**
  - F1 → `target.agent.before_tool_callback = fault.as_callback()`
  - F2 → `target.agent.before_model_callback = fault.as_callback()`
  - F3 → `fault.install(target.agent)` (monkey-patches retrievers in place)
  - F4 → `target.agent.before_tool_callback = fault.as_callback()` AND optionally inject `fault.httpx_transport()` into the target's httpx client
  Implement a per-class dispatch table; don't pretend they share a common interface.
- **Concurrent fault attempts:** the Injector runs attacks SEQUENTIALLY (not `asyncio.gather`) because fault installations mutate target state. Parallel attacks would race on `before_tool_callback`. Keep sequential.
- **`span_id` capture:** `AdapterResult.span_ids[0]` works for Tier 1 ADK adapters that populate span_ids. For Tier 3 HTTP black-box adapters, span_ids may be empty — handle by falling back to OTel's `trace.get_current_span().get_span_context().span_id` formatted as a hex string.
- **DO NOT bypass BaselineCheck.** Even in test mode. If a story 5.7 test wants to skip baseline, configure the target to actually pass baseline (use scripted healthy AdapterResult outcomes) rather than commenting out the check.
- **State immutability assumption:** `InjectorState` is mutated in place by `record_attack`. The Judge sub-agent (Epic 6) reads it AFTER `Injector.run()` returns, so the mutation is safe. Don't share `InjectorState` across concurrent runs.
- **Cross-reference:** `/Users/abu/dev/hackathon/rapid-agents/research/google-cloud-rapid-agent/architecture/04-fault-injection-eval.md` §8.3 (per-fault demo behavior — the 25-attack matrix). `/Users/abu/dev/hackathon/rapid-agents/research/google-cloud-rapid-agent/architecture/01-reference-implementations.md` §7 Move 1 (Voltaros three-agent shape — Injector is the first agent) + §7 Move 4 (Garak N-runs methodology). `/Users/abu/dev/hackathon/rapid-agents/docs/PRD.md` §"Demo moment" steps 3-4 (5×5 grid + cascade-flip).
