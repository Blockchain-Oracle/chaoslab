# Story — Target Agent A2A Exposure via `to_a2a()`

**ID:** story-2.2-target-a2a-exposure
**Epic:** Epic 2 — Target agent (the victim)
**Depends on:** story-2.1-naive-target-agent
**Estimate:** ~1h
**Status:** PENDING

---

## User story

**As a** ChaosLab orchestrator (Cloud Run service #1)
**I want to** call the target agent (Cloud Run service #3) via the A2A protocol over HTTP
**So that** when chaos injection crashes the target, fault isolation per ADR-002 keeps the orchestrator alive — the demo can credibly claim "the victim is its own process; we attack across a real wire"

---

## File modification map

Exact files the coding agent creates or modifies for this story:

- `apps/target-agent/src/target_agent/server.py` — NEW — imports `root_agent` from `target_agent.agent`, wraps it via `from google.adk.a2a.utils.agent_to_a2a import to_a2a`, exposes `a2a_app = to_a2a(root_agent, port=8001)`. Adds a `main()` callable that runs `uvicorn` against `a2a_app` reading `PORT` env var (defaults to `8001`). Reads `HOST` env var (defaults to `0.0.0.0`). ~50 lines.
- `apps/target-agent/pyproject.toml` — UPDATE — add `[project.scripts]` table: `target-agent = "target_agent.server:main"`. Add `uvicorn[standard]>=0.34.0,<1.0.0` to `[project] dependencies`. Add `google-adk[a2a]` extra usage or confirm `a2a-sdk>=1.1.0,<2.0.0` is in dependencies.
- `apps/target-agent/src/target_agent/__init__.py` — UPDATE — extend `__all__` to include `a2a_app` re-export: `from .server import a2a_app`.
- `apps/target-agent/tests/integration/test_a2a_card.py` — NEW — pytest test that spins up `a2a_app` via `uvicorn` in a background thread on a random localhost port, polls `/.well-known/agent-card.json`, asserts JSON structure (`name == "target_customer_support"`, `skills[].name` list includes `"lookup_order"`, `"refund"`, `"escalate"`). Marked `@pytest.mark.integration`. ~120 lines.
- `apps/target-agent/tests/integration/__init__.py` — NEW — empty (pytest discovery)
- `apps/target-agent/README.md` — UPDATE — add "Run the A2A server locally" section: `uv run target-agent` (binds `:8001`), `curl http://localhost:8001/.well-known/agent-card.json`.

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given apps/target-agent/pyproject.toml has [project.scripts] target-agent = "target_agent.server:main"
When  `cd apps/target-agent && uv sync && uv run which target-agent` runs (or `uv run python -c "import target_agent.server; assert callable(target_agent.server.main)"`)
Then  the script entry resolves and main is callable

Given apps/target-agent/src/target_agent/server.py defines a2a_app via to_a2a(root_agent, port=8001)
When  pytest imports `from target_agent.server import a2a_app`
Then  a2a_app is not None
And   the app exposes routes including "/.well-known/agent-card.json" (assert via app.router.routes or equivalent)

Given the integration test starts `uv run target-agent` (or uvicorn against a2a_app) on a free localhost port
When  `curl -s http://localhost:<port>/.well-known/agent-card.json` runs
Then  the HTTP status is 200
And   the response body parses as valid JSON
And   the parsed JSON has key "name" with value "target_customer_support"
And   the parsed JSON has key "skills" whose array contains an object with name == "lookup_order"
And   the skills array also contains objects with name == "refund" and name == "escalate"

Given `cd apps/target-agent && uv run pytest tests/ -v` runs (unit + integration)
When  the suite completes
Then  the integration test test_a2a_card passes
And   total passing tests >= 12 (10 from S2.1 + ≥2 new)

Given the 400-line guard runs on server.py + test file
When  `python3 scripts/check_max_lines.py --strict apps/target-agent/src/ apps/target-agent/tests/integration/` runs
Then  exit code is 0
```

---

## Shell verification

The coding agent runs this to confirm the story is done before opening a PR:

```bash
# 1) uv sync picks up uvicorn + a2a-sdk deps
cd apps/target-agent && uv sync && cd -

# 2) Script entry resolves
cd apps/target-agent && uv run python -c "import target_agent.server as s; assert callable(s.main); assert s.a2a_app is not None; print('OK')"
# Must print OK

# 3) Background-launch the server and curl the agent card
cd apps/target-agent
uv run target-agent &
SERVER_PID=$!
sleep 3  # cold-start window for uvicorn binding
curl -sf http://localhost:8001/.well-known/agent-card.json | tee /tmp/agent-card.json | python3 -c "import json,sys; d=json.load(sys.stdin); assert d['name']=='target_customer_support', d; skills={s['name'] for s in d.get('skills',[])}; assert {'lookup_order','refund','escalate'}.issubset(skills), skills; print('OK')"
kill $SERVER_PID
wait $SERVER_PID 2>/dev/null || true
cd -
# Must print OK; curl returns 200

# 4) Integration test passes
cd apps/target-agent && uv run pytest tests/integration -v -m integration 2>&1 | tee /tmp/target-a2a-int.log
grep -E "PASSED" /tmp/target-a2a-int.log | wc -l
# Must output ≥ 2

# 5) Full test suite still green (no regression vs S2.1)
cd apps/target-agent && uv run pytest tests/ -v 2>&1 | tee /tmp/target-a2a-all.log
grep -E "PASSED" /tmp/target-a2a-all.log | wc -l
# Must output ≥ 12

# 6) §14 + 400-line + lint gates
git diff main...HEAD -- 'apps/target-agent/src/**' | grep -E "^\+" | grep -iE "(mock|fake|dummy|hardcoded|simulated)" | grep -v "test\|spec\|§14 carve-out"
# Must output nothing
python3 scripts/check_max_lines.py --strict apps/target-agent/src/ apps/target-agent/tests/
# Must exit 0
cd apps/target-agent && uv run ruff check . && uv run ruff format . --check && uv run ty check src/ && cd -
# All must exit 0

# 7) green-light
.claude/scripts/green-light.sh
# Must exit 0
```

---

## Notes for coding agent

- **`to_a2a()` is the one-line A2A producer.** Per `research/google-cloud-rapid-agent/architecture/03-multi-agent-patterns.md` §1.2 + §9.A, the canonical pattern is:
  ```python
  from google.adk.a2a.utils.agent_to_a2a import to_a2a
  from target_agent.agent import root_agent
  a2a_app = to_a2a(root_agent, port=8001)
  ```
  `a2a_app` is a Starlette/FastAPI ASGI app. It automatically registers `/.well-known/agent-card.json` per A2A protocol v1.0 spec — the coding agent does NOT need to hand-write the card.
- **Agent card skill discovery.** ADK's `to_a2a()` introspects `root_agent.tools` to generate the `skills[]` array on the agent card. Each tool's `name` (e.g. `lookup_order`, `refund`, `escalate`) becomes a skill with matching `name`. Tool docstrings populate `description`. If `to_a2a()`'s default skill-extraction does not produce skill names that match tool names exactly, override with explicit `AgentSkill` constructors per §2.2 of `architecture/03-multi-agent-patterns.md`. **Verify via the curl in shell verification step 3 before declaring done.**
- **`main()` shape.** Use `uvicorn.run(a2a_app, host=os.environ.get("HOST", "0.0.0.0"), port=int(os.environ.get("PORT", "8001")))`. Do NOT use `uvicorn.Config` + `Server.serve()` (those are for async-from-test patterns; the CLI entry should be plain blocking `uvicorn.run`).
- **Cloud Run `$PORT`.** Cloud Run injects `PORT` env var (default `8080`). The `main()` reads `PORT` so Dockerfile (S2.4) can bind correctly. For local dev, `PORT=8001` is the convention from PRD demo moment + `architecture/03-multi-agent-patterns.md` §9.C.
- **Integration test pattern.** Use a fixture that:
  1. Picks a free port via `socket.socket(...).bind(("", 0)); sock.getsockname()[1]`.
  2. Spawns the server via `subprocess.Popen(["uv", "run", "target-agent"], env={**os.environ, "PORT": str(port)}, ...)` OR via `uvicorn.Server` in a `threading.Thread`.
  3. Polls `http://localhost:<port>/.well-known/agent-card.json` with `httpx.get` + retry (max 30 attempts, 200ms sleep between).
  4. Asserts JSON structure.
  5. Tears down the subprocess in fixture teardown.
- **Mark as `@pytest.mark.integration`** so it can be filtered out of unit-only runs (per `coding-standards.md` `[tool.pytest.ini_options].markers`).
- **DO NOT make this test `@pytest.mark.online`** — it does not hit Gemini, Phoenix, or any real external service. It runs entirely locally.
- **uvicorn dependency.** Already may be transitive via `google-adk[a2a]` — verify by adding `uvicorn[standard]>=0.34.0,<1.0.0` explicitly in `[project] dependencies`; the `[standard]` extra brings `httptools` + `uvloop` for production-grade performance (matches Cloud Run best practices).
- **a2a-sdk version (AMENDED 2026-06-03 per audit A3).** ⚠ **Do NOT explicitly pin `a2a-sdk`.** `google-adk[a2a]` 2.1.0 transitively requires `a2a-sdk<0.4,>=0.3.4` — an explicit `>=1.1.0,<2.0.0` pin (previously documented in `best-practices/01` §4.14) causes a guaranteed `uv sync` resolver conflict. Use `google-adk[a2a]>=2.1.0` ONLY and let the extra resolve `a2a-sdk` transitively. Spec audit (`spec-audit/01-adk-a2a-audit.md`) verified this empirically against PyPI metadata.
- **No Phoenix wiring yet.** Phoenix instrumentation lands in S2.3. This story exposes the agent — instrumentation is layered on next. The agent card must still resolve without `PHOENIX_API_KEY` set (test the server starts cleanly with the env var unset).
- **Auth.** Cloud Run will be deployed with `--allow-unauthenticated` per `architecture/03-multi-agent-patterns.md` §7.4 hackathon-mode guidance. No bearer-token wiring in this story — the orchestrator → target call in Epic 3/4 will use the plain URL.
- **Files near the 400-line limit?** `server.py` should be ~50 lines, `test_a2a_card.py` ~120 lines. Both well under. If either approaches 350 lines during edits, split the test into per-assertion files (`test_card_name.py`, `test_card_skills.py`) — but at this size that's premature.
- **Cross-reference docs:** `/Users/abu/dev/hackathon/rapid-agents/research/google-cloud-rapid-agent/architecture/03-multi-agent-patterns.md` §1.2 (A2A peers), §2.2 (Agent Card structure), §9.A (target ADK agent skeleton), §9.C (local multi-process pattern).
