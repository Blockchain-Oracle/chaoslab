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
`server.py` **before any `google.adk.*` import** (ADR-005 — instrumentation
must patch ADK module attributes before consumers hold pre-patch references).

Env vars (see `.env.example`):

- `PHOENIX_API_KEY` — Phoenix Cloud API key. Local dev sets the env var
  directly; Cloud Run pulls from Google Secret Manager (`phoenix-api-key`
  under `$GCP_PROJECT_ID`).
- `PHOENIX_COLLECTOR_ENDPOINT` — defaults to `https://app.phoenix.arize.com`.
  Some Phoenix Cloud workspaces require the space-scoped URL (`/s/<space>`);
  update this if the integration test 404s on span ingestion.
- `PHOENIX_PROJECT_NAME` — defaults to `target-agent`. Must match the
  orchestrator's `--project` flag (Epic 4) and the demo's Phoenix deep-link.

## Where this fits

- S2.1 — agent object + 3 tools + unit tests
- S2.2 — A2A server wiring (`to_a2a()` + `[project.scripts]` entry point)
- **S2.3 (this story) — Phoenix tracing wiring (`phoenix.otel.register()` + GoogleADKInstrumentor)**
- S2.4 — Cloud Run Dockerfile + deploy
