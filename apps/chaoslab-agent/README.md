# chaoslab-agent

Phoenix Audit's orchestrator. ADK `SequentialAgent` composing Injector → Judge → Patcher sub-agents; A2A or HTTP peer to the target agent under audit. Internal directory name is the `chaoslab-agent` codename per CLAUDE.md (rename to `phoenix-audit-agent` is S1.6).

**S4.1 ships:** FastAPI entrypoint (`/run`, `/stream`, `/health`, `/agents/{id}`) + pydantic-settings config loader amended for the ADR-017 hybrid Phoenix-hosting model (`phoenix_provider` field; `phoenix_api_key` optional by default, required in BYO mode).

## Run locally

```bash
# 1. Install deps
uv sync

# 2. Set up env (.env.example -> .env; fill in GEMINI_API_KEY at minimum)
cp apps/chaoslab-agent/.env.example apps/chaoslab-agent/.env

# 3. Start uvicorn
uv run --package chaoslab-agent uvicorn chaoslab_agent.main:app --host 0.0.0.0 --port 8080 --reload
```

## Endpoints

| Method | Path             | Purpose                                                                           |
| ------ | ---------------- | --------------------------------------------------------------------------------- |
| GET    | `/health`        | Liveness probe. Returns `{status, version, judge_llm, phoenix_provider}`.         |
| POST   | `/run`           | Start an audit run. Body = `RunRequest`. Returns `{run_id, sse_url, created_at}`. |
| GET    | `/stream?runId=` | SSE stream of `RunEvent` frames for the given run.                                |
| GET    | `/agents/{id}`   | Look up a registered target agent (Epic 3 ships the real registry).               |

## Container

Multi-stage build → multi-stage cache → non-root runtime per ADR-003. The
workspace lockfile lives at the repo root, so the Docker build context MUST
be the workspace root (NOT `apps/chaoslab-agent/`):

```bash
# From the workspace root:
docker build -t chaoslab-agent:dev -f apps/chaoslab-agent/Dockerfile .

# Run locally — passes dummy creds so /health load + Settings construction work:
docker run --rm -p 8080:8080 \
  -e PHOENIX_API_KEY=dummy \
  -e GEMINI_API_KEY=dummy \
  -e JUDGE_LLM=gemini-3.5-flash \
  chaoslab-agent:dev

# In another shell:
curl http://localhost:8080/health
# -> {"status":"ok","version":"0.0.0","judge_llm":"gemini-3.5-flash","phoenix_provider":"phoenix-audit"}
```

The runtime image is <800MB on first build (matched by the size-gate test).
Cloud Run rebinds `$PORT` at deploy time; `run_uvicorn` reads `$PORT`/`$HOST`
env vars so the same image works locally on 8080 and Cloud Run on whatever
port is injected. Deploy via `.github/workflows/staging-deploy.yaml`.

## Tests

```bash
cd apps/chaoslab-agent
uv run pytest -v
```

Coverage: 9 cases for `Settings` (defaults, locked judge LLM, SecretStr redaction, lru_cache, env overrides, missing required vars, BYO-mode key requirement, valid BYO load, invalid provider enum) + 8 cases for the FastAPI endpoints.

## What's next

- **S4.2** wires the SequentialAgent orchestrator into `/run` (replaces the heartbeat in `/stream`).
- **S4.3-4.4** add Phoenix MCP read tools + Phoenix REST write wrappers.
- **S4.5** lands observability (setup_logging, structlog config, Phoenix register).
- **S4.6** ships the Cloud Run Dockerfile for deploy.

See `docs/stories/story-4.*.md` for the per-story file modification maps.
