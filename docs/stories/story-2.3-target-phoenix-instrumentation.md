# Story — Target Agent OpenInference → Phoenix Cloud Instrumentation

**ID:** story-2.3-target-phoenix-instrumentation
**Epic:** Epic 2 — Target agent (the victim)
**Depends on:** story-2.2-target-a2a-exposure
**Estimate:** ~1.5h
**Status:** PENDING

---

## User story

**As a** ChaosLab demo viewer (judge or developer)
**I want to** see the target agent's tool calls + LLM calls as Phoenix Cloud spans the moment they happen
**So that** the demo's Attack Matrix cells map to real, clickable Phoenix span IDs — the trace-as-UI hero pattern (per `research/.../architecture/05-ux-and-demo.md` §2) lands, and the Arize recursive-observability bonus score is unlocked

---

## File modification map

Exact files the coding agent creates or modifies for this story:

- `apps/target-agent/src/target_agent/observability.py` — NEW — exports `setup_observability(project_name: str = "target-agent") -> TracerProvider`. Reads `PHOENIX_API_KEY` from Google Secret Manager (`google-cloud-secret-manager`) if `PHOENIX_API_KEY` env var is unset; reads `PHOENIX_COLLECTOR_ENDPOINT` from env (default Phoenix Cloud root). Calls `register(project_name=project_name, set_global_tracer_provider=False, batch=False)`. Returns the resulting `TracerProvider`. Then calls `GoogleADKInstrumentor().instrument(tracer_provider=tracer_provider)`. Logs via structlog. ~120 lines.
- `apps/target-agent/src/target_agent/server.py` — UPDATE — at the TOP of the module (BEFORE any `google.adk` import per ADR-005 constraint), call `from target_agent.observability import setup_observability; _TRACER_PROVIDER = setup_observability()`. Only THEN import `target_agent.agent` and `to_a2a`. The order is load-bearing.
- `apps/target-agent/src/target_agent/__init__.py` — UPDATE — DO NOT change top-level imports; `__init__.py` must NOT trigger Phoenix setup at import time (only `server.py` does). Add `from .observability import setup_observability` to `__all__` for explicit consumer access if needed.
- `apps/target-agent/pyproject.toml` — UPDATE — add `arize-phoenix-otel>=0.6.0,<1.0.0`, `arize-phoenix-client>=0.1.0,<1.0.0`, `openinference-instrumentation-google-adk>=0.1.15,<1.0.0`, `opentelemetry-sdk>=1.29.0,<2.0.0`, `opentelemetry-exporter-otlp-proto-http>=1.29.0,<2.0.0`, `google-cloud-secret-manager>=2.28.0,<3.0.0`, `structlog>=25.5.0,<26.0.0` to `[project] dependencies`.
- `apps/target-agent/.env.example` — NEW — documents env vars: `PHOENIX_API_KEY=` (load from Secret Manager in prod), `PHOENIX_COLLECTOR_ENDPOINT=https://app.phoenix.arize.com`, `PHOENIX_PROJECT_NAME=target-agent`, `GCP_PROJECT_ID=`, `PORT=8001`. ~20 lines.
- `apps/target-agent/tests/integration/test_phoenix_instrumentation.py` — NEW — pytest test marked `@pytest.mark.integration @pytest.mark.online`. Sets `PHOENIX_API_KEY` from real env (skips if unset), invokes the target agent through `InMemoryRunner` on a single `lookup_order` call, then polls Phoenix Cloud REST API (`/v1/projects/target-agent/spans?last_n_minutes=2`) for up to 30 seconds. Asserts ≥1 span returned with `attributes["openinference.span.kind"] == "TOOL"`. ~150 lines.
- `apps/target-agent/tests/unit/test_observability.py` — NEW — pytest unit test asserting `setup_observability` returns a `TracerProvider` (not `None`), reads `PHOENIX_API_KEY` from env when set, raises `ConfigurationError` (custom exception) when neither env var nor Secret Manager is reachable. Mocks `google.cloud.secretmanager.SecretManagerServiceClient` via `respx`-style monkeypatching (test-side only — §14 carve-out). ~100 lines.
- `apps/target-agent/README.md` — UPDATE — add "Phoenix observability" section documenting env vars + Secret Manager fallback.

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given apps/target-agent/src/target_agent/observability.py exists with setup_observability()
When  pytest unit test imports it with PHOENIX_API_KEY env var set to a dummy string and PHOENIX_COLLECTOR_ENDPOINT set
Then  setup_observability() returns a non-None object that has attributes consistent with opentelemetry.sdk.trace.TracerProvider

Given apps/target-agent/src/target_agent/server.py imports observability BEFORE google.adk
When  `grep -n "setup_observability\|from google.adk\|from target_agent.agent" apps/target-agent/src/target_agent/server.py` runs
Then  the line number of "setup_observability" call < the line number of every "from google.adk" import
And   the line number of "setup_observability" call < the line number of every "from target_agent.agent" import

Given apps/target-agent/src/target_agent/observability.py defines setup_observability
When  `grep -E "register\(.*set_global_tracer_provider=False.*batch=False" apps/target-agent/src/target_agent/observability.py` runs
Then  exactly one match appears (per ADR-005 Agent Engine compatibility — same flag-set works for Cloud Run)

Given apps/target-agent/src/target_agent/observability.py defines setup_observability
When  `grep -E "GoogleADKInstrumentor\(\)\.instrument\(tracer_provider=" apps/target-agent/src/target_agent/observability.py` runs
Then  exactly one match appears

Given PHOENIX_API_KEY is set in the CI environment to a real Phoenix Cloud key for project "target-agent"
When  `uv run pytest tests/integration/test_phoenix_instrumentation.py -v -m "integration and online"` runs
Then  the test passes
And   a Phoenix span with attribute "openinference.span.kind" == "TOOL" appears at https://app.phoenix.arize.com/projects/target-agent within 30 seconds of invocation

Given PHOENIX_API_KEY is unset in the test environment
When  `uv run pytest tests/integration/test_phoenix_instrumentation.py -v` runs
Then  the test is SKIPPED (not failed) via @pytest.mark.skipif(not os.getenv("PHOENIX_API_KEY"), reason="...")

Given unit test runs
When  `cd apps/target-agent && uv run pytest tests/unit -v` completes
Then  ≥ 12 unit tests pass (10 from S2.1 + ≥2 new in test_observability)

Given 400-line guard runs
When  `python3 scripts/check_max_lines.py --strict apps/target-agent/src/ apps/target-agent/tests/` runs
Then  exit code is 0
```

---

## Shell verification

The coding agent runs this to confirm the story is done before opening a PR:

```bash
# 1) uv sync picks up new deps
cd apps/target-agent && uv sync && cd -

# 2) Phoenix imports do not break agent import
cd apps/target-agent && uv run python -c "import target_agent.observability as o; assert callable(o.setup_observability); print('OK')"
# Must print OK

# 3) Import order constraint: observability before adk
grep -n "setup_observability\|from google.adk\|from target_agent.agent" apps/target-agent/src/target_agent/server.py
# Visually verify setup_observability call line < first google.adk import line < target_agent.agent import line
# Automated check:
python3 - <<'PY'
import re, sys
with open("apps/target-agent/src/target_agent/server.py") as f:
    lines = f.readlines()
setup_ln = None
adk_ln = None
agent_ln = None
for i, line in enumerate(lines, 1):
    if setup_ln is None and "setup_observability" in line and "(" in line and "import" not in line:
        setup_ln = i
    if adk_ln is None and re.match(r"\s*from google\.adk", line):
        adk_ln = i
    if agent_ln is None and re.match(r"\s*from target_agent\.agent", line):
        agent_ln = i
assert setup_ln is not None, "setup_observability call not found"
assert adk_ln is None or setup_ln < adk_ln, f"setup_observability (ln {setup_ln}) must come BEFORE google.adk import (ln {adk_ln})"
assert agent_ln is None or setup_ln < agent_ln, f"setup_observability (ln {setup_ln}) must come BEFORE target_agent.agent import (ln {agent_ln})"
print("OK — import order correct")
PY
# Must print OK

# 4) Required flags present
grep -E "register\(.*set_global_tracer_provider=False.*batch=False|register\(.*batch=False.*set_global_tracer_provider=False" apps/target-agent/src/target_agent/observability.py
# Must output exactly one match (per ADR-005)
grep -E "GoogleADKInstrumentor\(\)\.instrument\(tracer_provider=" apps/target-agent/src/target_agent/observability.py
# Must output exactly one match

# 5) Unit tests
cd apps/target-agent && uv run pytest tests/unit -v 2>&1 | tee /tmp/target-obs-unit.log
grep -E "PASSED" /tmp/target-obs-unit.log | wc -l
# Must output ≥ 12

# 6) Integration + online test (only when PHOENIX_API_KEY set)
if [ -n "$PHOENIX_API_KEY" ]; then
  cd apps/target-agent && uv run pytest tests/integration/test_phoenix_instrumentation.py -v -m "integration and online" 2>&1 | tee /tmp/target-obs-int.log
  grep -E "PASSED" /tmp/target-obs-int.log | wc -l
  # Must output ≥ 1
else
  echo "PHOENIX_API_KEY unset — integration test will skip (expected in PR CI without secrets)"
fi

# 7) §14 + 400-line + lint
git diff main...HEAD -- 'apps/target-agent/src/**' | grep -E "^\+" | grep -iE "(mock|fake|dummy|hardcoded|simulated)" | grep -v "test\|spec\|§14 carve-out"
# Must output nothing
python3 scripts/check_max_lines.py --strict apps/target-agent/src/ apps/target-agent/tests/
# Must exit 0
cd apps/target-agent && uv run ruff check . && uv run ruff format . --check && uv run ty check src/ && cd -
# All must exit 0

# 8) green-light
.claude/scripts/green-light.sh
# Must exit 0
```

---

## Notes for coding agent

- **Import order is load-bearing (ADR-005).** `setup_observability()` MUST be called BEFORE any `google.adk.*` import. Reason: `GoogleADKInstrumentor().instrument()` patches ADK module attributes; if ADK is already imported and used by other modules at the time of instrumentation, those modules hold pre-patch references and emit no spans. The pattern in `server.py` must be:
  ```python
  """Target agent A2A server entrypoint."""
  from __future__ import annotations

  # 1) Phoenix instrumentation FIRST (per ADR-005)
  from target_agent.observability import setup_observability
  _TRACER_PROVIDER = setup_observability()

  # 2) ONLY THEN: ADK imports
  from google.adk.a2a.utils.agent_to_a2a import to_a2a
  from target_agent.agent import root_agent

  a2a_app = to_a2a(root_agent, port=8001)

  def main() -> None:
      import os
      import uvicorn
      uvicorn.run(a2a_app, host=os.environ.get("HOST", "0.0.0.0"), port=int(os.environ.get("PORT", "8001")))
  ```
  The CI grep step (shell verification #3) hard-asserts this ordering.
- **`set_global_tracer_provider=False` + `batch=False`.** Per `research/.../architecture/02-phoenix-deep-dive.md` §3.5 (Agent Engine caveat) and the prompt's explicit ADR-005 reference, these flags are mandatory. While Cloud Run does not strictly require `batch=False`, using it here means traces flush synchronously — critical for the 90-second demo where the Attack Matrix must show spans land in real time. Tradeoff: slightly higher per-request latency (200-500ms p99). Acceptable for demo-scale traffic.
- **Phoenix register() call shape:**
  ```python
  from phoenix.otel import register
  tracer_provider = register(
      project_name=project_name,
      set_global_tracer_provider=False,
      batch=False,
      auto_instrument=False,  # we manually wire GoogleADKInstrumentor below
  )
  ```
  Set `auto_instrument=False` to avoid the trap in `architecture/02-phoenix-deep-dive.md` §8.3 #8 (auto_instrument blindly hooks every installed openinference-* package, polluting spans).
- **GoogleADKInstrumentor wiring:**
  ```python
  from openinference.instrumentation.google_adk import GoogleADKInstrumentor
  GoogleADKInstrumentor().instrument(tracer_provider=tracer_provider)
  ```
  Must run AFTER `register()` and BEFORE any ADK use. The instrumentor is idempotent — calling it twice in tests is safe.
- **Secret Manager fallback.** The function should follow this resolution order for `PHOENIX_API_KEY`:
  1. `os.environ["PHOENIX_API_KEY"]` if set (local dev convenience)
  2. `google.cloud.secretmanager.SecretManagerServiceClient().access_secret_version(name=f"projects/{GCP_PROJECT_ID}/secrets/phoenix-api-key/versions/latest")` (Cloud Run prod)
  3. Raise `ConfigurationError("PHOENIX_API_KEY not found in env or Secret Manager")`
- **`PHOENIX_COLLECTOR_ENDPOINT`.** Default to `"https://app.phoenix.arize.com"` if env var unset. Per `architecture/02-phoenix-deep-dive.md` §7.1 the space-scoped URL `https://app.phoenix.arize.com/s/<space>` may be needed — coding agent verifies during their first integration test run; if the integration test fails with a 404 on span ingestion, switch to the space-scoped URL and document the actual value in `.env.example`.
- **`project_name="target-agent"` is canonical.** The Phoenix project name MUST match across the integration test, the URL in the BDD criterion (`https://app.phoenix.arize.com/projects/target-agent`), and ChaosLab's later orchestrator → Phoenix MCP `--project` flag. Hardcode the default to `"target-agent"` in `setup_observability(project_name: str = "target-agent")`.
- **structlog usage.** Configure structlog in `observability.py` per `coding-standards.md` "structlog setup" — use the `_add_phoenix_trace_id` processor so logs carry trace IDs. This is the same processor chain pattern used by `chaoslab-agent` (which lands in Epic 4).
- **Integration test pattern (BDD #5).** The test must:
  1. Skip if `PHOENIX_API_KEY` is unset (use `@pytest.mark.skipif(not os.getenv("PHOENIX_API_KEY"), reason="Requires real Phoenix Cloud key")`).
  2. Set `PHOENIX_PROJECT_NAME = f"target-agent-test-{uuid.uuid4().hex[:8]}"` (per-run isolation to avoid trash projects polluting Phoenix Cloud — see `best-practices/06-test-strategy.md` §6.4).
  3. Call `setup_observability(project_name=test_project_name)`.
  4. Run the agent through `InMemoryRunner` invoking the `lookup_order` tool (use a seeded order ID from S2.1's `_ORDERS_DB`).
  5. Sleep up to 30 seconds polling Phoenix Cloud REST API (`GET https://app.phoenix.arize.com/v1/projects/{test_project_name}/spans?last_n_minutes=2`) for spans.
  6. Filter spans where `attributes["openinference.span.kind"] == "TOOL"`.
  7. Assert at least one such span exists.
- **`@pytest.mark.online`.** Mark integration test with BOTH `integration` and `online` markers so cost-conscious CI runs can exclude it via `-m "not online"`.
- **No `print()` in src/.** Use `structlog.get_logger(__name__).info(...)` instead. ruff `T20` will catch violations.
- **Unit test for `setup_observability`.** Per BDD #1 + #6, the unit test must:
  - Set `PHOENIX_API_KEY=test-dummy` and `PHOENIX_COLLECTOR_ENDPOINT=http://localhost:6006` (a never-bound port — OTel will queue spans but not error on send).
  - Call `setup_observability(project_name="unit-test")`.
  - Assert return value is a `TracerProvider` (use `from opentelemetry.sdk.trace import TracerProvider; assert isinstance(rv, TracerProvider)`).
- **`§14 carve-out` annotation.** When the unit test uses `pytest-mock` or `monkeypatch` to stub `SecretManagerServiceClient`, add a `# §14 carve-out: test-side mock of GCP Secret Manager` comment above the patch line so the §14 grep in shell verification step 7 ignores it. Tests under `tests/` are already excluded from the `git diff` filter, but the explicit annotation documents intent.
- **400-line vigilance.** `observability.py` is the densest file in this story — Phoenix wiring + Secret Manager fallback + structlog + error handling can balloon. Target ≤150 lines; if it grows past 300, split into `observability/phoenix.py` (register + instrumentor) and `observability/secrets.py` (Secret Manager resolver).
- **Cross-reference docs:** `/Users/abu/dev/hackathon/rapid-agents/research/google-cloud-rapid-agent/architecture/02-phoenix-deep-dive.md` §3.4 (minimal snippet), §3.5 (Agent Engine caveat — applies to Cloud Run too for `batch=False`), §8.3 (gotchas, especially #5 + #8), §9.1 (Pattern A: instrument a target ADK agent). `coding-standards.md` "structlog setup" + ADR-005.
