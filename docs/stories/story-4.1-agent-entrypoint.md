# Story — chaoslab-agent FastAPI/ADK Entrypoint + Config

**ID:** story-4.1-agent-entrypoint
**Epic:** Epic 4 — ChaosLab orchestrator + Phoenix tool wrappers
**Depends on:** story-2.1-naive-target-agent
**Estimate:** ~2h
**Status:** PENDING
**tags:** [backend, p0, orchestrator, fastapi, adk]

---

## User story

**As a** ChaosLab demo orchestrator
**I want to** expose the `chaoslab-agent` service as a FastAPI app with `/run`, `/stream`, `/health`, and `/agents/{id}` endpoints, plus a pydantic-settings config loader
**So that** the frontend (`chaoslab-web`) can POST a run and tail SSE trace updates, Cloud Run can liveness-probe the container, and every later Epic 4-6 story has a single typed entry to wire into

---

## File modification map

Exact files the coding agent creates or modifies for this story:

- `apps/chaoslab-agent/pyproject.toml` — NEW — declares `[project]` for chaoslab-agent, deps: `google-adk`, `arize-phoenix`, `arize-phoenix-otel`, `arize-phoenix-client`, `openinference-instrumentation-google-adk`, `pydantic`, `pydantic-settings`, `httpx`, `structlog`, `fastapi`, `uvicorn[standard]`, `sse-starlette`; dev deps: `pytest`, `pytest-asyncio`, `pytest-cov`, `respx`, `httpx` (test client). ~80 lines.
- `apps/chaoslab-agent/src/chaoslab_agent/__init__.py` — NEW — empty re-export shim. ≤10 lines (under 400-line ignore per ADR-010).
- `apps/chaoslab-agent/src/chaoslab_agent/config.py` — NEW — `Settings(BaseSettings)` with `phoenix_api_key: SecretStr`, `phoenix_collector_endpoint: str = "https://app.phoenix.arize.com/v1/traces"`, `gemini_api_key: SecretStr`, `judge_llm: str = "gemini-3.5-flash"` (mandatory per ADR-007 — validator asserts value), `target_default_url: str = "http://localhost:8001"`, `gitlab_token: SecretStr | None = None`, `environment: Literal["dev", "staging", "prod"] = "dev"`, `service_version: str = "0.0.0"` (gets set to `${GITHUB_SHA}` at build time), `gcs_bucket: str = "chaoslab-artifacts"`. `model_config = SettingsConfigDict(env_file=".env", env_prefix="", frozen=True, extra="ignore")`. Module-level `get_settings()` returns a cached `Settings()` via `functools.lru_cache`. ~80 lines.
- `apps/chaoslab-agent/src/chaoslab_agent/main.py` — NEW — `app: FastAPI = FastAPI(title="chaoslab-agent", version=...)`. Endpoints: `POST /run` (accepts `RunRequest` pydantic model with `target_url: str`, `agent_id: str | None`, `fault_seed: int | None`, `repetitions: int = 25`, returns `RunResponse(run_id: str, sse_url: str, created_at: str)`); `GET /stream?runId=X` (returns `EventSourceResponse` via `sse-starlette`, streams `RunEvent` JSON frames from the in-process run registry — orchestrator wiring lands in S4.2, this story streams a hello-frame + heartbeat); `GET /health` (returns `{"status": "ok", "version": settings.service_version, "judge_llm": settings.judge_llm}`); `GET /agents/{agent_id}` (returns the registered `TargetAgentSpec` — placeholder dict for this story, real registry comes from E3). In-memory `_RUN_REGISTRY: dict[str, RunState]` (Module global, single-tenant per ADR-003). `RunRequest` and `RunResponse` are pydantic models defined inline (move to a `schemas.py` if file > 250 lines). Startup event calls `chaoslab_agent.observability.setup_logging(...)` (defined in S4.5 — for this story, import-and-call with a fallback `try/except ImportError: pass` block — clean up in S4.5). ~250 lines max; if longer, split routes into `apps/chaoslab-agent/src/chaoslab_agent/routes/{run,stream,health,agents}.py`.
- `apps/chaoslab-agent/tests/__init__.py` — NEW — empty.
- `apps/chaoslab-agent/tests/unit/__init__.py` — NEW — empty.
- `apps/chaoslab-agent/tests/unit/test_config.py` — NEW — at least 6 pytest cases: defaults load, `judge_llm` validator rejects non-`gemini-3.5-flash` value with `ValueError` (ADR-007), `phoenix_api_key` is `SecretStr` (asserts `repr()` does not leak the value), `get_settings()` returns same instance on repeated calls (lru_cache), env override from monkeypatched `os.environ` works, missing `phoenix_api_key` raises `ValidationError`. ~120 lines.
- `apps/chaoslab-agent/tests/unit/test_main.py` — NEW — at least 8 pytest cases using `httpx.AsyncClient(app=app, base_url="http://test")` (per FastAPI testing docs): `GET /health` returns 200 with `status=="ok"` and version + judge_llm fields, `POST /run` with a valid `RunRequest` returns 201 with `run_id` matching `r"^run_[a-z0-9]{12}$"` + `sse_url` containing the run_id, `POST /run` with missing `target_url` returns 422, `GET /stream?runId=<unknown>` returns 404, `GET /stream?runId=<known>` returns 200 with `content-type: text/event-stream` and the first SSE frame contains a `hello` event, `GET /agents/test-agent` returns the registered placeholder spec, `GET /agents/<unknown>` returns 404, `GET /health` includes `judge_llm == "gemini-3.5-flash"` (ADR-007 enforcement). ~180 lines.
- `apps/chaoslab-agent/.env.example` — NEW — documents every env var: `PHOENIX_API_KEY=`, `PHOENIX_COLLECTOR_ENDPOINT=https://app.phoenix.arize.com/v1/traces`, `GEMINI_API_KEY=`, `JUDGE_LLM=gemini-3.5-flash`, `TARGET_DEFAULT_URL=http://localhost:8001`, `GITLAB_TOKEN=`, `ENVIRONMENT=dev`, `SERVICE_VERSION=local`. ~15 lines.
- `apps/chaoslab-agent/README.md` — NEW — one-paragraph overview + `uv run uvicorn chaoslab_agent.main:app --host 0.0.0.0 --port 8080 --reload` run command + table of endpoints. ~60 lines.
- `pyproject.toml` (workspace root) — UPDATE — append `"apps/chaoslab-agent"` to `[tool.uv.workspace] members` if not already present.

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given apps/chaoslab-agent/pyproject.toml exists with fastapi + google-adk + arize-phoenix deps
When  `cd apps/chaoslab-agent && uv sync` runs
Then  exit code is 0
And   `.venv` is created

Given a .env.example file with PHOENIX_API_KEY=test-key + GEMINI_API_KEY=test-gemini + JUDGE_LLM=gemini-3.5-flash
When  pytest imports `from chaoslab_agent.config import get_settings; s = get_settings()`
Then  s.judge_llm == "gemini-3.5-flash"
And   repr(s.phoenix_api_key) does NOT contain the literal "test-key"
And   s.environment in ("dev", "staging", "prod")

Given Settings is instantiated with JUDGE_LLM=gemini-2.5-pro via monkeypatched env
When  Settings() is constructed
Then  pydantic.ValidationError is raised with message containing "gemini-3.5-flash"

Given the FastAPI app is started with valid env (PHOENIX_API_KEY, GEMINI_API_KEY set)
When  `curl http://localhost:8080/health` runs (via httpx AsyncClient in tests)
Then  HTTP 200 returns
And   response JSON contains {"status": "ok", "version": "<sha-or-0.0.0>", "judge_llm": "gemini-3.5-flash"}

Given the FastAPI app is up
When  POST /run is called with JSON body {"target_url": "http://localhost:8001", "repetitions": 25}
Then  HTTP 201 returns
And   response JSON has a "run_id" field matching ^run_[a-z0-9]{12}$
And   response JSON has an "sse_url" field containing the run_id

Given a run_id was returned by POST /run
When  GET /stream?runId=<that-id> is opened
Then  HTTP 200 returns with header content-type: text/event-stream
And   the first SSE frame is an event named "hello" with JSON data including the run_id

Given POST /run is called with body missing target_url
When  the request lands
Then  HTTP 422 returns (pydantic validation error)

Given GET /stream?runId=run_doesnotexist000 is opened
When  the request lands
Then  HTTP 404 returns

Given `cd apps/chaoslab-agent && uv run pytest tests/unit -v` runs
When  the test suite completes
Then  at least 14 behavioral test cases pass

Given grep checks the new source files for §14 violations
When  `grep -rE "(mock|fake|dummy|hardcoded|simulated)" apps/chaoslab-agent/src/ | grep -v "§14 carve-out"` runs
Then  zero results appear (test fixtures live under tests/, not src/)

Given the 400-line guard runs on the new files
When  `python3 scripts/check_max_lines.py --strict apps/chaoslab-agent/src/` runs
Then  exit code is 0
```

---

## Shell verification

The coding agent runs this to confirm the story is done before opening a PR:

```bash
# 1) uv sync works
cd apps/chaoslab-agent && uv sync && cd -

# 2) Tests pass with ≥14 cases
cd apps/chaoslab-agent && uv run pytest tests/unit -v 2>&1 | tee /tmp/chaoslab-agent-test.log
grep -E "PASSED" /tmp/chaoslab-agent-test.log | wc -l
# Must output ≥ 14

# 3) /health endpoint smoke test (via test client; real Cloud Run check in S4.6)
cd apps/chaoslab-agent && uv run python -c "
from fastapi.testclient import TestClient
from chaoslab_agent.main import app
r = TestClient(app).get('/health')
assert r.status_code == 200, r.status_code
assert r.json()['status'] == 'ok'
assert r.json()['judge_llm'] == 'gemini-3.5-flash'
print('OK')
"
# Must print OK

# 4) JUDGE_LLM validator rejects wrong model
cd apps/chaoslab-agent && JUDGE_LLM=gemini-2.5-pro uv run python -c "
from pydantic import ValidationError
from chaoslab_agent.config import Settings
try:
    Settings(phoenix_api_key='x', gemini_api_key='y')
    print('FAIL: should have raised')
    exit(1)
except ValidationError as e:
    assert 'gemini-3.5-flash' in str(e), str(e)
    print('OK')
"
# Must print OK

# 5) §14 clean
git diff main...HEAD -- 'apps/chaoslab-agent/src/**' | grep -E "^\+" | grep -iE "(mock|fake|dummy|hardcoded|simulated)" | grep -v "test\|spec\|§14 carve-out"
# Must output nothing

# 6) 400-line guard
python3 scripts/check_max_lines.py --strict apps/chaoslab-agent/src/
# Must exit 0

# 7) ruff + ty
cd apps/chaoslab-agent && uv run ruff check . && uv run ruff format . --check && uv run ty check src/ && cd -
# All must exit 0

# 8) green-light
.claude/scripts/green-light.sh
# Must exit 0
```

---

## Notes for coding agent

- **`JUDGE_LLM` is load-bearing.** ADR-007 mandates `gemini-3.5-flash`. The `Settings` class must reject any other value via a `@field_validator("judge_llm")` that raises `ValueError("JUDGE_LLM must be 'gemini-3.5-flash' per ADR-007, got: ...")`. The CI gate (S1.5) greps for this string — do not soften the validator.
- **`SecretStr` for all secrets.** `phoenix_api_key`, `gemini_api_key`, `gitlab_token` all use `pydantic.SecretStr`. Test asserts `repr(settings.phoenix_api_key)` does NOT leak the literal value. Never `str(x)` a secret in a log line — use `.get_secret_value()` only at the point of API call.
- **`get_settings()` is the only public entry.** All other modules import `from chaoslab_agent.config import get_settings; settings = get_settings()`. Never `Settings()` directly. The `lru_cache` makes Settings effectively a singleton — `frozen=True` keeps it immutable.
- **In-memory `_RUN_REGISTRY` is single-tenant.** Per ADR-003 + PRD "Out of scope," ChaosLab is single-concurrent-session for the judging window. A `dict[str, RunState]` at module scope is sufficient. Document this in a `# IMPORTANT:` comment so future agents do not "fix" it into Redis.
- **`run_id` format.** `f"run_{secrets.token_hex(6)}"` produces 12 lowercase-hex chars — matches the regex `^run_[a-z0-9]{12}$`. Same pattern as `recipe_id` in `architecture.md` schema.
- **SSE via `sse-starlette`.** Use `sse_starlette.EventSourceResponse` — handles retries + `event:` framing. First frame is `{"event": "hello", "data": json.dumps({"run_id": run_id, "version": settings.service_version})}`. Heartbeat every 15s to keep Cloud Run from terminating idle connections (Cloud Run default 60s idle timeout — `ping=15` keeps under it).
- **`/agents/{id}` is a placeholder.** Real registry comes from E3 adapter layer. For this story, return a stub `{"agent_id": agent_id, "adapter_type": "adk", "url": settings.target_default_url, "registered_at": "..."}` for any known id; 404 for unknown. Tests assert on the placeholder shape.
- **`startup` event MUST run observability setup BEFORE any ADK import** (per `coding-standards.md` ADK-specific Python patterns + `architecture.md` ADR-005). For this story, the observability module does not yet exist — use a `try/except ImportError: pass` guard. S4.5 wires it cleanly.
- **No `print()` in src/** (ruff `T20`). Tests can use `print()` (per per-file-ignores). All src/ logging via `structlog.get_logger(__name__)`.
- **`pyproject.toml` workspace member.** Append `"apps/chaoslab-agent"` to `[tool.uv.workspace] members` (added by S1.1). After append, run `uv sync` at the workspace root to refresh the lockfile.
- **400-line vigilance.** `main.py` will be close to 250 lines. If you add `RunRequest`, `RunResponse`, `RunEvent`, `RunState` schemas and they push past 300, split into `apps/chaoslab-agent/src/chaoslab_agent/schemas.py`. Splitting EARLY beats refactoring at 399.
- **Cross-reference docs:**
  - `/Users/abu/dev/hackathon/rapid-agents/docs/architecture.md` (Stack + Data flow + ADR-003, ADR-007)
  - `/Users/abu/dev/hackathon/rapid-agents/research/google-cloud-rapid-agent/best-practices/03-code-quality-enforcement.md` §10 (Settings pattern) + §11 (structlog setup — used in S4.5)
  - `/Users/abu/dev/hackathon/rapid-agents/research/google-cloud-rapid-agent/best-practices/04-nextjs-production.md` §7 (SSE proxy patterns — chaoslab-web side)
