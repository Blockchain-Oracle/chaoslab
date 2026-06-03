# Story — Phoenix `run_experiment` Custom ADK FunctionTool

**ID:** story-4.3-phoenix-run-experiment-tool
**Epic:** Epic 4 — ChaosLab orchestrator + Phoenix tool wrappers
**Depends on:** story-4.1-agent-entrypoint
**Estimate:** ~2h
**Status:** PENDING
**tags:** [backend, p0, phoenix, adk, function-tool]

---

## User story

**As a** Judge sub-agent inside the ChaosLab orchestrator
**I want to** call `run_phoenix_experiment(dataset_name, evaluators, task_callable_id)` as an ADK `FunctionTool` that wraps `phoenix.client.AsyncClient().experiments.run_experiment(...)`
**So that** ChaosLab can close the loop on Phoenix experiment execution — which the Phoenix MCP server explicitly does NOT expose (per ADR-005 + `architecture/02 §1, §9.5`) — and the Judge can grade a cluster of failures with a single LLM-as-judge pass before annotation writeback

---

## File modification map

Exact files the coding agent creates or modifies for this story:

- `apps/chaoslab-agent/src/chaoslab_agent/phoenix_tools/__init__.py` — NEW — empty re-export shim.
- `apps/chaoslab-agent/src/chaoslab_agent/phoenix_tools/run_experiment.py` — NEW — the tool body itself. Defines:
  - `ExperimentResult(BaseModel)` with `experiment_id: str = Field(pattern=r"^exp_[a-z0-9]+$")`, `dataset_name: str`, `evaluator_names: list[str]`, `metrics: dict[str, float]` (keyed by evaluator name, value = mean score 0.0-1.0), `span_ids: list[str]` (the spans the experiment touched), `total_examples: int`, `elapsed_seconds: float`.
  - `run_phoenix_experiment(dataset_name: str, evaluators: list[str], task_callable_id: str = "passthrough") -> ExperimentResult` — async function. Uses `phoenix.client.AsyncClient()` with `concurrency=10` per `architecture/02 §2.3`. Resolves `evaluators` list (strings like `"tool_invocation"`, `"hallucination"`, `"chaoslab_tool_success"`) to actual `phoenix.evals` evaluator instances via a small lookup registry — extensibility hook for S6.1 custom rubrics. The `task_callable_id` is a string key resolved via a `TASK_REGISTRY: dict[str, Callable]` (default `"passthrough"` returns `example.output` as-is — matches `architecture/02 §9.5` pattern). Returns `ExperimentResult`. Includes `rate_limit_errors=[ResourceExhausted, ...]` retry config + `timeout=30 retries=2`.
  - Module-level `phoenix_run_experiment_tool: FunctionTool = FunctionTool(func=run_phoenix_experiment)` — the exported ADK FunctionTool the Judge sub-agent will mount.
  - The `run_phoenix_experiment` function body itself MUST be ≤30 LOC per ADR-005 (excluding imports + docstring + registry lookups, which live above). The supporting `ExperimentResult` + registry adds ~70 lines of well-typed pydantic + lookups. Total file ~150 lines.
- `apps/chaoslab-agent/tests/integration/__init__.py` — NEW — empty.
- `apps/chaoslab-agent/tests/integration/test_phoenix_run_experiment.py` — NEW — at least 8 pytest cases marked `@pytest.mark.integration` and (where applicable) `@pytest.mark.online`:
  - `ExperimentResult` pydantic model validates a sample dict.
  - `ExperimentResult` rejects `experiment_id="exp_INVALID-CAPS"` (regex enforces lowercase alphanumeric).
  - `phoenix_run_experiment_tool` is an instance of `google.adk.tools.FunctionTool`.
  - `phoenix_run_experiment_tool.func.__name__ == "run_phoenix_experiment"`.
  - **`respx`-mocked happy path:** `respx` intercepts the Phoenix REST POST `/v1/datasets/{name}/experiments`, returns a canned JSON with `id="exp_abc123def"`. Tool returns an `ExperimentResult` with that id matching the regex.
  - **`respx`-mocked 429 retry path:** Phoenix returns 429 twice, then 200. Tool succeeds; total request count == 3. Verifies `retries=2` config.
  - **`respx`-mocked failure path:** Phoenix returns 500. Tool raises a `PhoenixExperimentError` (custom exception in `chaoslab_agent.errors`) — never bare `Exception`.
  - **`@pytest.mark.online` real Phoenix hit:** if `PHOENIX_API_KEY` is set in env AND the test is invoked with `-m "online"`, the tool runs against a Phoenix-Cloud dataset named `"test-rat"` (must exist — pre-created by Day-1 RAT runbook per ADR-005), with evaluators=`["tool_invocation"]`. Asserts `result.experiment_id` matches the regex AND `result.metrics` contains the `"tool_invocation"` key. Test is skipped if env var is missing.
  ~200 lines.
- `apps/chaoslab-agent/src/chaoslab_agent/errors.py` — NEW (if not already from S4.1) — defines `class ChaosLabError(Exception)` base + `class PhoenixExperimentError(ChaosLabError)` + `class PhoenixAnnotationError(ChaosLabError)` (used in S4.4). ~30 lines.

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given chaoslab_agent.phoenix_tools.run_experiment imports without side effects
When  pytest imports `from chaoslab_agent.phoenix_tools.run_experiment import phoenix_run_experiment_tool, ExperimentResult`
Then  no exception is raised
And   phoenix_run_experiment_tool is an instance of google.adk.tools.FunctionTool

Given the run_phoenix_experiment function body
When  `python3 -c "import inspect; from chaoslab_agent.phoenix_tools.run_experiment import run_phoenix_experiment; print(len([l for l in inspect.getsource(run_phoenix_experiment).split(chr(10)) if l.strip() and not l.strip().startswith('#') and not l.strip().startswith('\"\"\"')]))"` is computed
Then  the resulting LOC (significant lines, excluding docstring/comments) is ≤ 30 per ADR-005

Given ExperimentResult(experiment_id="exp_abc123def", dataset_name="test", evaluator_names=["t"], metrics={"t":0.9}, span_ids=[], total_examples=3, elapsed_seconds=1.2)
When  the model is constructed
Then  no ValidationError is raised

Given ExperimentResult(experiment_id="exp_INVALID-CAPS", ...)
When  the model is constructed
Then  pydantic.ValidationError is raised (regex pattern mismatch)

Given respx intercepts the Phoenix experiment-creation endpoint and returns id="exp_abc123def"
When  `await run_phoenix_experiment("test-rat", ["tool_invocation"])` is awaited
Then  the return is an ExperimentResult with .experiment_id == "exp_abc123def"
And   .metrics has the key "tool_invocation"

Given respx returns 429 on the first 2 requests and 200 on the 3rd
When  the tool is invoked
Then  the final return is a valid ExperimentResult
And   respx recorded exactly 3 outbound requests (initial + 2 retries)

Given respx returns 500
When  the tool is invoked
Then  chaoslab_agent.errors.PhoenixExperimentError is raised
And   the exception message does NOT contain the literal PHOENIX_API_KEY value

@pytest.mark.online
Given PHOENIX_API_KEY env var is set AND a Phoenix Cloud dataset "test-rat" exists with 3 examples
When  `await run_phoenix_experiment("test-rat", ["tool_invocation"])` is awaited
Then  result.experiment_id matches r"^exp_[a-z0-9]+$"
And   "tool_invocation" in result.metrics
And   result.total_examples >= 1

Given `cd apps/chaoslab-agent && uv run pytest tests/integration/test_phoenix_run_experiment.py -v -m "not online"` runs
When  the test suite completes (offline mode — uses respx)
Then  at least 7 behavioral test cases pass

Given grep counts the wrapper function body LOC
When  `awk '/^async def run_phoenix_experiment/,/^[a-zA-Z]/' apps/chaoslab-agent/src/chaoslab_agent/phoenix_tools/run_experiment.py | grep -cvE "^\s*$|^\s*#|^\s*\"\"\""` runs
Then  the count is ≤ 30 (per ADR-005)

Given the 400-line guard runs
When  `python3 scripts/check_max_lines.py --strict apps/chaoslab-agent/src/` runs
Then  exit code is 0
```

---

## Shell verification

```bash
# 1) Offline tests pass with ≥7 cases
cd apps/chaoslab-agent && uv run pytest tests/integration/test_phoenix_run_experiment.py -v -m "not online" 2>&1 | tee /tmp/phoenix-runexp.log
grep -E "PASSED" /tmp/phoenix-runexp.log | wc -l
# Must output ≥ 7

# 2) ≤30 LOC body check (ADR-005)
cd apps/chaoslab-agent && uv run python -c "
import inspect
from chaoslab_agent.phoenix_tools.run_experiment import run_phoenix_experiment
src = inspect.getsource(run_phoenix_experiment).split('\n')
sig_lines = [l for l in src if l.strip() and not l.strip().startswith('#') and not l.strip().startswith('\"\"\"') and not l.strip().startswith(\"'''\")]
print(f'LOC: {len(sig_lines)}')
assert len(sig_lines) <= 30, f'Wrapper body must be ≤30 LOC per ADR-005, got {len(sig_lines)}'
print('OK')
"
# Must print OK

# 3) Tool registered as FunctionTool
cd apps/chaoslab-agent && uv run python -c "
from google.adk.tools import FunctionTool
from chaoslab_agent.phoenix_tools.run_experiment import phoenix_run_experiment_tool
assert isinstance(phoenix_run_experiment_tool, FunctionTool), type(phoenix_run_experiment_tool)
assert phoenix_run_experiment_tool.func.__name__ == 'run_phoenix_experiment'
print('OK')
"
# Must print OK

# 4) Optional: online test if PHOENIX_API_KEY set (CI runs this only on a tagged job)
if [ -n "$PHOENIX_API_KEY" ]; then
  cd apps/chaoslab-agent && uv run pytest tests/integration/test_phoenix_run_experiment.py -v -m "online"
fi

# 5) §14 clean (production code path uses real Phoenix; mocks only in tests/)
git diff main...HEAD -- 'apps/chaoslab-agent/src/**' | grep -E "^\+" | grep -iE "(mock|fake|dummy|hardcoded|simulated)" | grep -v "test\|spec\|§14 carve-out"
# Must output nothing

# 6) 400-line guard
python3 scripts/check_max_lines.py --strict apps/chaoslab-agent/src/
# Must exit 0

# 7) ruff + ty
cd apps/chaoslab-agent && uv run ruff check . && uv run ruff format . --check && uv run ty check src/ && cd -
# Must exit 0

# 8) green-light
.claude/scripts/green-light.sh
# Must exit 0
```

---

## Notes for coding agent

- **Why this wrapper exists.** Per ADR-005 + `architecture/02 §1, §9.5`: the Phoenix MCP server (`@arizeai/phoenix-mcp`) exposes `list-experiments-for-dataset` and `get-experiment-by-id` but DOES NOT expose `run-experiment`. To close the ChaosLab loop, ChaosLab MUST wrap the Python SDK as a custom ADK `FunctionTool`. This is the keystone of ADR-005. **Do not reach for the MCP server to run experiments — it cannot.**
- **The 30-LOC budget is a hard rule.** Per ADR-005 the wrapper function itself is ≤30 LOC. Pydantic models, evaluator registry, and task registry live ABOVE the function (they don't count). The CI check in BDD enforces it. If the body exceeds 30 LOC, refactor: extract evaluator resolution to `_resolve_evaluators(names: list[str]) -> list[BaseEvaluator]` above the wrapper.
- **AsyncClient with `concurrency=10`.** Per `architecture/02 §2.3`: "AsyncClient supports `concurrency=N` on `run_experiment`. Default is unverified — likely 1. Pass it explicitly." For ChaosLab's 25-attack runs, `concurrency=10` keeps wall time under 60s on a typical Phoenix-Cloud free-tier rate limit.
- **`rate_limit_errors=[ResourceExhausted]`.** Per `architecture/02 §2.3`: Phoenix `run_experiment` accepts a list of exception classes that trigger backoff + retry. Pass `[ResourceExhausted, httpx.HTTPStatusError]` — the wrapper internally maps Gemini's `google.api_core.exceptions.ResourceExhausted` for 429 handling.
- **Reference canonical wrapper shape** (per `architecture/02 §9.5` — adapt, do not paste verbatim):
  ```python
  async def run_phoenix_experiment(
      dataset_name: str,
      evaluators: list[str],
      task_callable_id: str = "passthrough",
  ) -> ExperimentResult:
      """Run a Phoenix LLM-as-judge experiment over a dataset.

      ADR-005 keystone tool. Wraps phoenix.client.AsyncClient().experiments.run_experiment.
      """
      client = AsyncClient(api_key=get_settings().phoenix_api_key.get_secret_value())
      dataset = await client.datasets.get_dataset(name=dataset_name)
      task = TASK_REGISTRY[task_callable_id]
      evaluator_instances = _resolve_evaluators(evaluators)
      try:
          exp = await client.experiments.run_experiment(
              dataset=dataset, task=task, evaluators=evaluator_instances,
              concurrency=10, timeout=30, retries=2,
              rate_limit_errors=[ResourceExhausted, httpx.HTTPStatusError],
          )
      except Exception as e:
          raise PhoenixExperimentError(f"experiment failed: dataset={dataset_name}") from e
      return _to_experiment_result(exp, dataset_name, evaluators)
  ```
  Body is ~15 LOC of significant code; well under 30.
- **`PhoenixExperimentError` sanitization.** Never include the API key in the error message. Use `from e` to preserve the underlying traceback for debugging but the message itself stays sanitized.
- **`TASK_REGISTRY` extensibility.** Default `"passthrough"` returns `example.output` as-is (the use case is grading already-observed outputs — same shape as `architecture/02 §9.5`). Future stories (S6.x) will register additional task callables like `"chaoslab_rerun"` that re-invoke the target agent for a fresh response.
- **`evaluators` parameter is a list of NAMES.** Tools cannot accept Python callables as arguments over JSON (the ADK FunctionTool serializes args to JSON for the LLM to populate). Resolve strings to evaluator instances via `_resolve_evaluators`:
  ```python
  EVALUATOR_REGISTRY: dict[str, type] = {
      "tool_invocation": ToolResponseEvaluator,
      "hallucination": HallucinationEvaluator,
      # S6.1 registers "chaoslab_tool_success" + "chaoslab_prompt_injection" + ...
  }
  ```
- **`AsyncClient` token + endpoint.** Constructed from `get_settings().phoenix_api_key.get_secret_value()` and `get_settings().phoenix_collector_endpoint`. Phoenix's `AsyncClient` reads `PHOENIX_API_KEY` env var by default — passing explicitly avoids the implicit env lookup pattern (testable + no surprise auth failures).
- **`@pytest.mark.online` carve-out.** Per `coding-standards.md` pytest config: `online` marker tests hit real Phoenix and are skipped in default CI. They run on a nightly tag or when `PHOENIX_API_KEY` is in the runner env. The BDD has both an offline-respx path and an online path so the offline tests gate every PR.
- **400-line vigilance.** `run_experiment.py` at ~150 lines + `errors.py` at ~30 = comfortable. If the evaluator registry grows past ~20 entries, split into `phoenix_tools/evaluator_registry.py`.
- **Cross-reference docs:**
  - `/Users/abu/dev/hackathon/rapid-agents/research/google-cloud-rapid-agent/architecture/02-phoenix-deep-dive.md` §1 (MCP asymmetry), §2.3 (`run_experiment` full signature), §9.5 (Pattern E — canonical wrapper)
  - `/Users/abu/dev/hackathon/rapid-agents/docs/architecture.md` ADR-005 (Phoenix MCP partial)
  - `/Users/abu/dev/hackathon/rapid-agents/research/google-cloud-rapid-agent/best-practices/06-test-strategy.md` §5.3 (Phoenix LLM-as-judge) + §6.1 (Phoenix integration testing)
