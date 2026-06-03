# Story — Naive ADK Customer-Support Target Agent

**ID:** story-2.1-naive-target-agent
**Epic:** Epic 2 — Target agent (the victim)
**Depends on:** story-1.7-prod-promote-and-visual-tests
**Estimate:** ~1.5h
**Status:** PENDING

---

## User story

**As a** ChaosLab orchestrator
**I want to** have a deliberately-naive ADK customer-support agent to attack
**So that** ChaosLab's 4 fault classes (malformed tool output, prompt injection, context poisoning, latency spike) have a real, semantically-meaningful target whose failure modes (no input validation, no retry policy, no prompt-injection defense) match the 3 root causes the Patcher will cluster on

---

## File modification map

Exact files the coding agent creates or modifies for this story:

- `apps/target-agent/pyproject.toml` — NEW — declares `[project]` for target-agent, `[project.scripts]` (placeholder, real entry in S2.2), `google-adk`, `pydantic`, `structlog`, dev deps (`pytest`, `pytest-asyncio`, `pytest-cov`)
- `apps/target-agent/src/target_agent/__init__.py` — NEW — re-export shim: `from .agent import root_agent`; `__all__ = ["root_agent"]` (under 400-line ignore per ADR-010)
- `apps/target-agent/src/target_agent/agent.py` — NEW — defines `root_agent: LlmAgent` with `name="target_customer_support"`, `model="gemini-3.5-flash"`, weak instruction (no input validation guidance, no retry policy, single-pass tool use), `tools=[lookup_order_tool, refund_tool, escalate_tool]`. ~80 lines.
- `apps/target-agent/src/target_agent/tools.py` — NEW — three ADK `FunctionTool` instances wrapping `lookup_order(order_id: str) -> dict`, `refund(order_id: str, amount: float) -> dict`, `escalate(reason: str) -> dict`. Deliberately naive: no Pydantic input validation, no max-amount cap on refund, no idempotency key, in-memory order DB. ~120 lines.
- `apps/target-agent/src/target_agent/main.py` — NEW — placeholder module entry that imports `root_agent` and exposes it for `adk web` discovery (real server wiring lands in S2.2). ~20 lines.
- `apps/target-agent/tests/unit/test_tools.py` — NEW — at least 10 behavioral pytest cases covering lookup_order happy path + missing order, refund happy path + zero/negative amount, escalate happy path, and one trace-as-assertion test asserting a Phoenix span with `status_code=OK` appears when the agent runs an in-memory request. ~130 lines.
- `apps/target-agent/tests/__init__.py` — NEW — empty (pytest discovery)
- `apps/target-agent/tests/unit/__init__.py` — NEW — empty
- `apps/target-agent/README.md` — NEW — one-paragraph "what is target-agent" + run-locally section pointing at `uv run adk web .` for the workspace. ≤50 lines.
- `pyproject.toml` (workspace root) — UPDATE — add `apps/target-agent` to `[tool.uv.workspace] members`

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given apps/target-agent/pyproject.toml exists with google-adk + pytest deps
When  `cd apps/target-agent && uv sync` runs
Then  exit code is 0
And   `.venv` is created

Given apps/target-agent/src/target_agent/tools.py exists with lookup_order in-memory DB
When  pytest runs `lookup_order("12345")` for an order seeded in the in-memory DB
Then  the return value is a dict containing keys "status", "items", "total"

Given apps/target-agent/src/target_agent/tools.py defines refund(order_id, amount)
When  pytest calls `refund("12345", 50.0)` followed by `refund("12345", 50.0)` (same args)
Then  both calls succeed (no idempotency check — deliberately naive)
And   the in-memory refund ledger has 2 entries for order_id="12345"

Given apps/target-agent/src/target_agent/agent.py defines root_agent: LlmAgent
When  pytest imports `from target_agent.agent import root_agent`
Then  root_agent.name == "target_customer_support"
And   root_agent.model == "gemini-3.5-flash"
And   len(root_agent.tools) == 3

Given a pytest run with PHOENIX_API_KEY+PHOENIX_COLLECTOR_ENDPOINT env vars set and OpenInference ADK instrumentation wired (deferred to S2.3 — this story uses an in-memory OTel SimpleSpanProcessor capture fixture)
When  the agent invokes the `lookup_order` tool through InMemoryRunner
Then  the captured span list contains at least one span with attribute `openinference.span.kind = "TOOL"`
And   that span's `status_code` equals "OK"

Given `cd apps/target-agent && uv run pytest tests/unit -v` runs
When  the test suite completes
Then  at least 10 behavioral test cases pass

Given grep checks the new source files for §14 violations
When  `grep -rE "(mock|fake|dummy|hardcoded|simulated)" apps/target-agent/src/ | grep -v "§14 carve-out"` runs
Then  zero results appear (test fixtures live under tests/, not src/)

Given the 400-line guard runs on the new files
When  `python3 scripts/check_max_lines.py --strict apps/target-agent/src/` runs
Then  exit code is 0
```

---

## Shell verification

The coding agent runs this to confirm the story is done before opening a PR:

```bash
# 1) uv sync works for the new app
cd apps/target-agent && uv sync && cd -

# 2) Tests pass with ≥10 behavioral cases
cd apps/target-agent && uv run pytest tests/unit -v 2>&1 | tee /tmp/target-agent-test.log
grep -E "PASSED" /tmp/target-agent-test.log | wc -l
# Must output ≥ 10

# 3) Agent import smoke test
cd apps/target-agent && uv run python -c "from target_agent.agent import root_agent; assert root_agent.name == 'target_customer_support'; assert root_agent.model == 'gemini-3.5-flash'; assert len(root_agent.tools) == 3; print('OK')"
# Must print OK

# 4) §14 clean — no mocks in src hot path
git diff main...HEAD -- 'apps/target-agent/src/**' | grep -E "^\+" | grep -iE "(mock|fake|dummy|hardcoded|simulated)" | grep -v "test\|spec\|§14 carve-out"
# Must output nothing

# 5) 400-line guard
python3 scripts/check_max_lines.py --strict apps/target-agent/src/
# Must exit 0

# 6) ruff + ty
cd apps/target-agent && uv run ruff check . && uv run ruff format . --check && uv run ty check src/ && cd -
# All must exit 0

# 7) Workspace-level green-light passes
.claude/scripts/green-light.sh
# Must exit 0
```

---

## Notes for coding agent

- **Trace-as-assertion only.** Per Epic 2 spec: do NOT assert on natural-language output ("Then the agent says X"). Assert on Phoenix/OpenInference span attributes (`openinference.span.kind`, `status_code`, span name). The unit test fixture uses an OTel `SimpleSpanProcessor` + in-memory exporter (real Phoenix wiring lands in S2.3).
- **Weak prompt is the point.** The agent's `instruction` field must read like a hackathon prototype — single-sentence, no schema constraints, no "if input is malformed, ask for clarification," no retry guidance, no defense-in-depth language. Sample shape (do not deviate without re-reading PRD §3 demo moment):
  ```
  "You are a customer support agent. Help users with orders, refunds, and escalations. Use the tools when needed."
  ```
- **Tools are deliberately naive.** Per `architecture.md` §"Repo structure" target-agent layout, the 3 tools represent the 3 root causes the Patcher will cluster on:
  - `lookup_order(order_id: str)` — no validation that `order_id` matches `^[a-zA-Z0-9-]+$`, no length check, raw dict lookup → root cause "no input validation"
  - `refund(order_id: str, amount: float)` — no max-amount cap, no idempotency key, no order-existence check → root cause "no retry policy / no idempotency"
  - `escalate(reason: str)` — no PII redaction, no template, accepts free-form string → root cause "no prompt-injection defense"
- **In-memory DB shape.** Seed `_ORDERS_DB: dict[str, dict]` at module level with 3 sample orders (e.g. `"12345"`, `"67890"`, `"ABCDE"`). Each value has `status` (one of `"shipped"`, `"processing"`, `"delivered"`), `items` (list of dicts with `name` + `qty`), `total` (float). This is NOT a §14 violation — it's the canonical demo target data, not a mock of an external service.
- **Refund ledger.** Use a module-level `_REFUND_LEDGER: list[dict]` to record refunds. Append-only. Deliberately no dedup. Tests will assert ledger length grows on duplicate refund calls.
- **`model="gemini-3.5-flash"` is mandatory** per the prompt + PRD. Do not substitute `gemini-2.5-flash` or `gemini-3-flash-preview` — the agent's model field is load-bearing and the test asserts on it.
- **400-line vigilance.** `tools.py` will be close to 120 lines; if it grows past 250 during edits, split per-tool files (`tools/lookup_order.py`, `tools/refund.py`, `tools/escalate.py`) and re-export from `tools/__init__.py`. `agent.py` should stay under 100 lines.
- **`__init__.py` is excluded** from the 400-line guard per ADR-010, but keep it under 20 lines as a re-export shim only.
- **No `print()` in src/** (ruff `T20` will catch it). Use `structlog.get_logger(__name__)` if logging is needed.
- **uv workspace.** The workspace root `pyproject.toml` already has `[tool.uv.workspace] members` from S1.1 — append `"apps/target-agent"` to that list if it isn't already there. Re-run `uv sync` at the workspace root after the edit.
- **Server entry (S2.2 dependency).** This story does NOT add the `to_a2a()` server or the `[project.scripts]` entry point — that's S2.2. `main.py` here is a minimal module that exposes `root_agent` for ADK discovery only.
- **Phoenix wiring (S2.3 dependency).** This story does NOT call `phoenix.otel.register()` or `GoogleADKInstrumentor().instrument(...)`. The unit test fixture uses an in-process OTel `SimpleSpanProcessor` + in-memory exporter (`InMemorySpanExporter` from `opentelemetry.sdk.trace.export.in_memory_span_exporter`) so the trace-as-assertion BDD can run without a real Phoenix endpoint.
- **Sample fixture pattern** for the trace-as-assertion test:
  ```python
  from opentelemetry import trace
  from opentelemetry.sdk.trace import TracerProvider
  from opentelemetry.sdk.trace.export import SimpleSpanProcessor
  from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

  @pytest.fixture
  def in_memory_spans():
      exporter = InMemorySpanExporter()
      provider = TracerProvider()
      provider.add_span_processor(SimpleSpanProcessor(exporter))
      trace.set_tracer_provider(provider)
      yield exporter
      exporter.clear()
  ```
- **Cross-reference docs:** `/Users/abu/dev/hackathon/rapid-agents/research/google-cloud-rapid-agent/best-practices/01-python-project-layout.md` §3.4 (canonical agent.py shape) + §3.8 (test patterns). `/Users/abu/dev/hackathon/rapid-agents/research/google-cloud-rapid-agent/architecture/03-multi-agent-patterns.md` §9.A (target ADK agent skeleton — note our weak-prompt + naive-tools variant).
