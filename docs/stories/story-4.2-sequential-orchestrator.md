# Story — SequentialAgent Orchestrator Scaffolding (Injector → Judge → Patcher)

**ID:** story-4.2-sequential-orchestrator
**Epic:** Epic 4 — ChaosLab orchestrator + Phoenix tool wrappers
**Depends on:** story-4.1-agent-entrypoint
**Estimate:** ~2h
**Status:** PENDING
**tags:** [backend, p0, orchestrator, adk, multi-agent]

---

## User story

**As a** ChaosLab demo orchestrator
**I want to** compose an ADK `SequentialAgent` containing three stub sub-agents (`Injector`, `Judge`, `Patcher`) that pass state via `output_key` and emit a 3-child CHAIN span tree to Phoenix
**So that** Epics 5 (Injector real implementation) and 6 (Judge + Patcher real implementation) drop into a typed spine instead of inventing one, and the end-to-end trace shape is locked from the start

---

## File modification map

Exact files the coding agent creates or modifies for this story:

- `apps/chaoslab-agent/src/chaoslab_agent/orchestrator.py` — NEW — defines `build_orchestrator() -> SequentialAgent` factory function. Creates three stub `LlmAgent` instances (`Injector`, `Judge`, `Patcher`) with `model=settings.judge_llm` (i.e. `gemini-3.5-flash` per ADR-007), single-sentence stub `instruction` fields, and `output_key` set to `"injector_result"`, `"judge_result"`, `"patcher_result"` respectively. Wraps them in `SequentialAgent(name="ChaosLabOrchestrator", sub_agents=[injector, judge, patcher])`. Each stub agent's instruction reads upstream output via `{key}` template substitution to prove state flow (Injector seeds; Judge references `{injector_result}`; Patcher references `{judge_result}`). Module-level `ORCHESTRATOR_NAME = "ChaosLabOrchestrator"` constant for test assertions. ~150 lines.
- `apps/chaoslab-agent/src/chaoslab_agent/injector/__init__.py` — NEW — empty re-export shim (under 400-line ignore per ADR-010).
- `apps/chaoslab-agent/src/chaoslab_agent/injector/agent.py` — NEW — `build_injector_agent() -> LlmAgent` returns the stub. `name="Injector"`, `description="Selects a fault class, configures the target adapter, invokes the target, captures the span"` (the description is load-bearing for E5 supervisor routing per `architecture/03-multi-agent-patterns.md §1.1`), `instruction="STUB: emit a JSON object with keys ['fault_class', 'span_id', 'pass']. Real implementation lands in Epic 5."`, `output_key="injector_result"`. ~50 lines.
- `apps/chaoslab-agent/src/chaoslab_agent/judge/__init__.py` — NEW — empty.
- `apps/chaoslab-agent/src/chaoslab_agent/judge/agent.py` — NEW — `build_judge_agent() -> LlmAgent`. `name="Judge"`, `description="Reads attack-phase spans, runs LLM-as-judge rubrics, clusters failures, writes annotations back"`, `instruction="STUB: given upstream injector output {injector_result}, emit a JSON object with keys ['cluster_id', 'failure_count', 'root_cause']. Real implementation lands in Epic 6."`, `output_key="judge_result"`. ~50 lines.
- `apps/chaoslab-agent/src/chaoslab_agent/patcher/__init__.py` — NEW — empty.
- `apps/chaoslab-agent/src/chaoslab_agent/patcher/agent.py` — NEW — `build_patcher_agent() -> LlmAgent`. `name="Patcher"`, `description="Generates a HardeningRecipe from clustered failures and emits a Markdown artifact + GitLab MR"`, `instruction="STUB: given upstream judge output {judge_result}, emit a JSON object with keys ['recipe_id', 'prompt_patches', 'tool_validation_diffs']. Real implementation lands in Epic 6."`, `output_key="patcher_result"`. ~50 lines.
- `apps/chaoslab-agent/src/chaoslab_agent/main.py` — UPDATE — import `build_orchestrator` from `chaoslab_agent.orchestrator`. Add a background task triggered by `POST /run`: instantiate the orchestrator (lazy, once at startup), `asyncio.create_task` wraps `orchestrator.run_async(...)` (or the ADK `Runner` API equivalent — verify against installed `google-adk` version), updates `_RUN_REGISTRY[run_id]` with intermediate events, those events feed the `/stream` SSE. Failure path: orchestrator exceptions write a `{"event": "error", "data": "<sanitized>"}` SSE frame and 500 the run. ~80 lines of new code added (file must still be ≤400 lines — split to `routes/` if needed).
- `apps/chaoslab-agent/tests/unit/test_orchestrator.py` — NEW — at least 10 pytest cases. Uses an in-memory OTel `InMemorySpanExporter` fixture (same pattern as S2.1) to capture spans:
  - `build_orchestrator()` returns a `SequentialAgent` instance.
  - `.name == "ChaosLabOrchestrator"`.
  - `len(orchestrator.sub_agents) == 3`.
  - `orchestrator.sub_agents[0].name == "Injector"`, `[1].name == "Judge"`, `[2].name == "Patcher"`.
  - Each sub-agent's `.model == "gemini-3.5-flash"` (ADR-007 enforced at the sub-agent level too).
  - Each sub-agent's `.output_key` matches the documented value.
  - The `Judge` instruction contains the literal substring `{injector_result}` (template state flow proven).
  - **Trace-as-assertion:** when the orchestrator runs against a stubbed-LLM (use `respx` to intercept the Gemini API call OR ADK's `InMemoryLlm` if it exists in v1.x — verify; otherwise use `unittest.mock.patch` on the `LlmAgent._generate_content` async method to return a canned response), the captured span list contains a span named `"ChaosLabOrchestrator"` with exactly 3 child spans whose names are `["Injector", "Judge", "Patcher"]` in that order.
  - The child spans' `openinference.span.kind` attribute equals `"CHAIN"` (per OpenInference ADK conventions).
  - The `Patcher` span starts AFTER the `Judge` span ends (asserted via `start_time` comparison) — proves sequential execution, not parallel.
  ~200 lines.
- `apps/chaoslab-agent/tests/unit/test_main.py` — UPDATE — add 3 cases: `POST /run` now creates an entry in `_RUN_REGISTRY` with `phase` field; `GET /stream?runId=X` emits a `phase_change` event when the background task transitions phases (mockable by patching the orchestrator with a stub that yields phase updates); cancellation: closing the SSE client mid-stream cancels the background task. ~50 added lines.

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given chaoslab_agent.orchestrator exists with build_orchestrator()
When  pytest calls build_orchestrator()
Then  the return is a google.adk.agents.SequentialAgent instance
And   .name == "ChaosLabOrchestrator"
And   len(.sub_agents) == 3
And   [a.name for a in .sub_agents] == ["Injector", "Judge", "Patcher"]

Given each stub sub-agent factory (build_injector_agent / build_judge_agent / build_patcher_agent)
When  pytest constructs each
Then  each returned LlmAgent has .model == "gemini-3.5-flash"
And   each has a non-empty .description field (>= 20 chars)
And   .output_key values are exactly ["injector_result", "judge_result", "patcher_result"]

Given the Judge agent's instruction string
When  the string is inspected
Then  it contains the literal substring "{injector_result}" (state flow via template)

Given the Patcher agent's instruction string
When  the string is inspected
Then  it contains the literal substring "{judge_result}"

Given an in-memory OTel SimpleSpanProcessor is wired and the Gemini API is stubbed (respx or LlmAgent generation patched)
When  the orchestrator runs once
Then  the captured spans contain exactly 1 span named "ChaosLabOrchestrator"
And   that span has exactly 3 child spans with names ["Injector", "Judge", "Patcher"] in that order
And   each child span has attribute openinference.span.kind == "CHAIN"
And   Patcher span.start_time > Judge span.end_time (sequential ordering proven)

Given POST /run is called with a valid request body
When  the response returns
Then  HTTP 201 returns with a run_id
And   _RUN_REGISTRY[run_id].phase is one of ("queued", "running")

Given a run_id was created and an SSE client opened /stream?runId=<id>
When  the background orchestrator task transitions Injector → Judge phase (simulated via test fixture)
Then  an SSE frame with event="phase_change" and data containing phase="judge" is emitted

Given `cd apps/chaoslab-agent && uv run pytest tests/unit/test_orchestrator.py tests/unit/test_main.py -v` runs
When  the test suite completes
Then  at least 13 new behavioral test cases pass (10 orchestrator + 3 main update)

Given grep checks the new source files for §14 violations
When  `grep -rE "(mock|fake|dummy|hardcoded|simulated)" apps/chaoslab-agent/src/ | grep -v "STUB: " | grep -v "§14 carve-out"` runs
Then  zero results appear (the word "STUB:" inside instruction strings is allowed and documented)

Given the 400-line guard runs
When  `python3 scripts/check_max_lines.py --strict apps/chaoslab-agent/src/` runs
Then  exit code is 0
```

---

## Shell verification

```bash
# 1) Tests pass with ≥13 new cases
cd apps/chaoslab-agent && uv run pytest tests/unit/test_orchestrator.py tests/unit/test_main.py -v 2>&1 | tee /tmp/orch-test.log
grep -E "PASSED" /tmp/orch-test.log | wc -l
# Must output ≥ 13

# 2) Trace-as-assertion smoke
cd apps/chaoslab-agent && uv run pytest tests/unit/test_orchestrator.py::test_orchestrator_emits_three_child_chain_spans -v
# Must pass

# 3) Orchestrator smoke import
cd apps/chaoslab-agent && uv run python -c "
from chaoslab_agent.orchestrator import build_orchestrator
o = build_orchestrator()
assert o.name == 'ChaosLabOrchestrator'
assert len(o.sub_agents) == 3
assert [a.name for a in o.sub_agents] == ['Injector', 'Judge', 'Patcher']
for a in o.sub_agents:
    assert a.model == 'gemini-3.5-flash', f'{a.name} model={a.model}'
print('OK')
"
# Must print OK

# 4) §14 clean (STUB: carve-out documented)
git diff main...HEAD -- 'apps/chaoslab-agent/src/**' | grep -E "^\+" | grep -iE "(mock|fake|dummy|hardcoded|simulated)" | grep -v "test\|spec\|STUB: \|§14 carve-out"
# Must output nothing

# 5) 400-line guard
python3 scripts/check_max_lines.py --strict apps/chaoslab-agent/src/
# Must exit 0

# 6) ruff + ty
cd apps/chaoslab-agent && uv run ruff check . && uv run ruff format . --check && uv run ty check src/ && cd -
# All must exit 0

# 7) green-light
.claude/scripts/green-light.sh
# Must exit 0
```

---

## Notes for coding agent

- **Stubs are real `LlmAgent` instances, not mocks.** Per §14 + ADR-002, the sub-agents must be real `LlmAgent` instances backed by real Gemini. The trace-as-assertion tests stub the LLM RESPONSE (via `respx` against the Gemini REST endpoint) but never replace the `LlmAgent` class itself. The string `"STUB:"` in the instruction is documentation, not a §14 violation — the test grep explicitly carves it out.
- **`SequentialAgent` shape.** Reference `architecture/03-multi-agent-patterns.md §3.1`:
  ```python
  from google.adk.agents.sequential_agent import SequentialAgent
  from google.adk.agents.llm_agent import LlmAgent

  injector = build_injector_agent()
  judge = build_judge_agent()
  patcher = build_patcher_agent()

  return SequentialAgent(
      name="ChaosLabOrchestrator",
      sub_agents=[injector, judge, patcher],
  )
  ```
- **State passing via `output_key` + `{key}` template.** This is THE mechanism that makes downstream sub-agents read upstream results without manual context plumbing. The Judge instruction MUST contain the literal `{injector_result}` substring or state will not flow. Tests assert on this exact substring.
- **`description` is load-bearing.** Per `architecture/03 §1.1`: "The `description` field on each sub-agent is **load-bearing** — the parent's LLM reads it to decide *when* to delegate." For `SequentialAgent` the description is less critical for routing (sequential is deterministic) but Epic 6 may upgrade to a hierarchical supervisor — keep descriptions ≥20 chars and informative.
- **Trace-as-assertion is the primary correctness signal.** Per `best-practices/06 §5.1`. Assert on the SPAN TREE, not on natural-language LLM output. Sample assertion shape:
  ```python
  span_names = [s.name for s in exporter.get_finished_spans()]
  assert "ChaosLabOrchestrator" in span_names
  orch_span = next(s for s in exporter.get_finished_spans() if s.name == "ChaosLabOrchestrator")
  child_names = [s.name for s in exporter.get_finished_spans() if s.parent and s.parent.span_id == orch_span.context.span_id]
  assert child_names == ["Injector", "Judge", "Patcher"]
  ```
- **`openinference.span.kind = "CHAIN"`** per the OpenInference semantic-conventions spec. `openinference-instrumentation-google-adk` sets this automatically for `LlmAgent` runs. If the attribute is missing, the instrumentation is not loaded — verify `chaoslab_agent.observability.setup()` runs at startup (S4.5 wires it; for this story, an early import is enough).
- **`asyncio.create_task` background pattern in `main.py`.** When `POST /run` lands, do:
  ```python
  state = RunState(run_id=..., phase="queued")
  _RUN_REGISTRY[run_id] = state
  task = asyncio.create_task(_run_orchestrator(run_id, request, state))
  state.task = task
  ```
  The `_run_orchestrator` coroutine is responsible for updating `state.phase` and pushing events into an `asyncio.Queue` that the SSE generator reads from. SSE generator reads from `state.event_queue.get()` with a 15s timeout for heartbeats.
- **ADK Runner API.** ADK ships an `InMemoryRunner` for testing (per `best-practices/06 §4`). Use it in tests to drive the orchestrator without spinning up `adk web`:
  ```python
  from google.adk.runners import InMemoryRunner
  runner = InMemoryRunner(agent=build_orchestrator(), app_name="chaoslab")
  events = [e async for e in runner.run_async(user_id="test", new_message=...)]
  ```
  Wrap the call in an OTel span-capture fixture so the trace tree is observable.
- **Phoenix instrumentation timing.** Per `coding-standards.md` ADK-specific patterns: `chaoslab_agent.observability.setup()` must run BEFORE any ADK import. In `main.py`, the import order is: stdlib → `chaoslab_agent.config` → `chaoslab_agent.observability` → setup() called at module load → THEN `chaoslab_agent.orchestrator` (which imports `google.adk.*`). Until S4.5 lands the real observability module, use a try/except guard.
- **400-line vigilance.** `orchestrator.py` will be ~150 lines, each sub-agent file ~50. The risk is `main.py` — if the orchestrator wiring pushes it past 350, split routes into `apps/chaoslab-agent/src/chaoslab_agent/routes/{run,stream,health,agents}.py` and keep `main.py` as a thin `FastAPI` factory + `app.include_router(...)`.
- **Cross-reference docs:**
  - `/Users/abu/dev/hackathon/rapid-agents/research/google-cloud-rapid-agent/architecture/03-multi-agent-patterns.md` §3.1 (SequentialAgent canonical) + §8 Candidate B (ChaosLab topology)
  - `/Users/abu/dev/hackathon/rapid-agents/research/google-cloud-rapid-agent/best-practices/06-test-strategy.md` §5.1 (trace-as-assertion) + §4 (in-process SequentialAgent test pattern)
  - `/Users/abu/dev/hackathon/rapid-agents/docs/architecture.md` ADR-002 (hybrid multi-agent) + ADR-007 (judge_llm)
