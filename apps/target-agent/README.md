# target-agent

The deliberately-naive customer-support agent **Phoenix Audit audits in the demo.** Three tools (`lookup_order`, `refund`, `escalate`), weak prompt, no input validation — by design.

The three naive design choices (no input validation, no idempotency, no PII guard) map 1:1 to the three root causes Phoenix Audit's clusterer surfaces in the demo cascade-flip moment ("3 failures, 1 root cause, patch in 4 seconds").

## Run locally

From the workspace root:

```bash
uv sync
uv run python -c "from target_agent.agent import root_agent; print(root_agent)"
```

For ADK web inspection (local UI for the agent):

```bash
cd apps/target-agent
uv run adk web .
```

## Run the tests

From the workspace root:

```bash
# Unit tests only (fast, no server):
uv run --directory apps/target-agent pytest tests/unit -v

# Integration tests (spawns the live A2A server in-process):
uv run --directory apps/target-agent pytest tests/integration -v
```

## Run the A2A server locally

S2.2 wires the agent up as an A2A server so Phoenix Audit can call it over the wire (fault isolation per ADR-002 — when an adversarial test crashes this target, Phoenix Audit's orchestrator stays alive).

```bash
# From the workspace root — uses the [project.scripts] entry point:
uv run target-agent
# Binds 0.0.0.0:8001 by default; respects $PORT and $HOST env vars.

# In another shell:
curl http://localhost:8001/.well-known/agent-card.json
# Returns: {"name": "target_customer_support", "skills": [{"name": "lookup_order", ...}, ...]}
```

Cloud Run injects `$PORT=8080` automatically; the Dockerfile (S2.4) needs no special config.

## Phoenix observability

Tool and LLM calls emit OpenInference-convention spans to Phoenix Cloud.
The wiring lives in `src/target_agent/observability.py` and is imported by
`server.py` **before any `google.adk.*` import**. OpenInference auto-
instrumentors monkey-patch ADK internals; installing them before consumers
bind module attributes is the documented practice. The S2.3 acceptance
test's AST-based ordering check enforces this at the source level. The
correct ordering pattern is shown in `research/.../architecture/02-phoenix-deep-dive.md §3.4`
(Phoenix Cloud + ADK minimal snippet). Flag-citation history: `audit-notes.md` D4-8.

Env vars (see `.env.example`):

- `PHOENIX_API_KEY` — Phoenix Cloud API key. Local dev sets the env var
  directly. **Planned for S2.4 (Cloud Run deploy):** pull from Google
  Secret Manager (`phoenix-api-key` under `$GCP_PROJECT_ID`).
- `PHOENIX_COLLECTOR_ENDPOINT` — defaults to `https://app.phoenix.arize.com`.
  Some Phoenix Cloud workspaces require the space-scoped URL (`/s/<space>`);
  empirically confirmed in RAT-2 with form
  `https://app.phoenix.arize.com/s/<workspace-slug>`. Update this if the
  integration test 404s on span ingestion.
- `PHOENIX_PROJECT_NAME` — defaults to `target-agent`. Must match the
  orchestrator's `--project` flag (Epic 4) and the demo's Phoenix deep-link.
- `PHOENIX_OBSERVABILITY_OPTIONAL=1` — opt-in to the no-op graceful-degradation
  path. On Cloud Run (where `K_SERVICE` is set), missing credentials normally
  raise a hard `ConfigurationError` — this env var overrides that.

## Container build

S2.4 ships a multi-stage Dockerfile that builds a slim (~300-400 MB), non-root,
signal-safe runtime image. **Important — build context must be the workspace
root** (this is a uv workspace; `uv.lock` lives there, not in `apps/target-agent/`):

```bash
# From the workspace root:
docker build -t target-agent:dev -f apps/target-agent/Dockerfile .

# Run it locally:
docker run --rm -p 8001:8001 \
  -e PHOENIX_OBSERVABILITY_OPTIONAL=1 \
  target-agent:dev

# Or with real Phoenix Cloud creds:
docker run --rm -p 8001:8001 \
  -e PHOENIX_API_KEY="$PHOENIX_API_KEY" \
  -e PHOENIX_COLLECTOR_ENDPOINT="$PHOENIX_COLLECTOR_ENDPOINT" \
  target-agent:dev

# Cloud Run deploy injects PORT=8080 + PUBLIC_URL automatically:
gcloud run deploy target-agent \
  --image=$IMAGE_URL \
  --set-env-vars=PUBLIC_URL=https://target-xxx.run.app
```

The image runs as uid 10001 (non-root) per the 2026 Cloud Run best practice.

**`PUBLIC_URL` env var (fix for issue #22):** without it, the A2A agent card
advertises `http://localhost:8001` regardless of where the container actually
binds. Set `PUBLIC_URL` to the deployed Cloud Run URL so upstream
`RemoteA2aAgent` clients can reach the agent. Local dev omits it and the
card serves `localhost:8001`, which is correct for `curl localhost:8001/...`
loopback testing.

## Where this fits

- S2.1 — agent object + 3 tools + unit tests
- S2.2 — A2A server wiring (`to_a2a()` + `[project.scripts]` entry point)
- S2.3 — Phoenix tracing wiring (`phoenix.otel.register()` + GoogleADKInstrumentor)
- **S2.4 (this story) — Cloud Run Dockerfile + agent-card URL fix (#22)**
