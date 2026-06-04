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
uv run pytest apps/target-agent/tests/unit -v
```

## Where this fits

- S2.1 (this story) — agent object + 3 tools + unit tests
- S2.2 — A2A server wiring (`to_a2a()` + `[project.scripts]` entry point)
- S2.3 — Phoenix tracing wiring (real `phoenix.otel.register()` + auto-instrumentor)
- S2.4 — Cloud Run Dockerfile + deploy
