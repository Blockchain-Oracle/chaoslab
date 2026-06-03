# RAT Runbook — W1 ChaosLab for Agents

**Date scheduled:** 2026-06-03 (Day 1 of build)
**Duration:** 90 minutes max
**Goal:** Validate the single most dangerous assumption BEFORE writing any agent code.
**Pivot trigger:** If any step takes >2× the estimate OR the Phoenix MCP doesn't expose what we need, pivot to W8 DataContract Sentinel on Day 2.

---

## The assumption being tested

> **Phoenix MCP exposes traces + datasets + experiments as agent-callable tools — enough that ChaosLab can be built without hand-rolling significant Phoenix-side infrastructure.**

If this is true, ChaosLab is a 9-day build. If false, every Phoenix interaction requires custom code and the build doesn't fit in 9 days solo.

---

## Pre-flight (5 min)

- [ ] Verify $100 GCP credit is claimed (or in flight — June 4 form deadline)
- [ ] Have a terminal open in `/Users/abu/dev/hackathon/rapid-agents/`
- [ ] Confirm Node 18+ and Python 3.10+ available: `node --version && python3 --version`
- [ ] Optional: pre-install ADK Python: `pip install google-adk`

---

## Step 1 — Phoenix Cloud signup + first trace (30 min)

**Goal:** Confirm Phoenix Cloud is free, auto-instrumentation works, and traces are visible.

- [ ] Sign up at https://app.phoenix.arize.com/ (free, no credit card)
- [ ] Create a new project in the dashboard, name it `chaoslab-rat`
- [ ] Copy your Phoenix API key from settings
- [ ] In a fresh dir `/tmp/phoenix-rat/`, create a minimal Python script:

```python
# /tmp/phoenix-rat/hello.py
import os
from openinference.instrumentation.google_adk import GoogleADKInstrumentor
from phoenix.otel import register

# Connect to Phoenix Cloud
os.environ["PHOENIX_API_KEY"] = "YOUR_KEY_HERE"
os.environ["PHOENIX_COLLECTOR_ENDPOINT"] = "https://app.phoenix.arize.com"
tracer_provider = register(project_name="chaoslab-rat")
GoogleADKInstrumentor().instrument(tracer_provider=tracer_provider)

# Tiny ADK agent — one tool, one model call
from google.adk import Agent
from google.adk.tools import Tool

def echo(text: str) -> str:
    """Echoes its input."""
    return f"echo: {text}"

agent = Agent(name="hello", model="gemini-3.5-flash", tools=[echo])
result = agent.run("Echo 'hello world'")
print(result)
```

- [ ] `pip install google-adk openinference-instrumentation-google-adk arize-phoenix-otel`
- [ ] Run `python hello.py`
- [ ] Open Phoenix dashboard → confirm one trace appears with the `echo` tool call visible

**KILL TRIGGER:** If by minute 30 no trace appears in Phoenix, debug for 15 more minutes then pivot to W8.

---

## Step 2 — Phoenix MCP install + tool discovery (30 min)

**Goal:** Confirm Phoenix MCP exposes the read primitives ChaosLab needs.

- [ ] Install Phoenix MCP server:
  ```bash
  npm install -g @arizeai/phoenix-mcp
  # Or test via npx:
  npx @arizeai/phoenix-mcp --help
  ```
- [ ] Wire to ADK via `MCPToolset` — minimal Python:

```python
# /tmp/phoenix-rat/mcp_test.py
from google.adk import Agent
from google.adk.tools.mcp import MCPToolset, StdioServerParameters

phoenix_mcp = MCPToolset(
    connection_params=StdioServerParameters(
        command="npx",
        args=["@arizeai/phoenix-mcp"],
        env={
            "PHOENIX_API_KEY": "YOUR_KEY_HERE",
            "PHOENIX_COLLECTOR_ENDPOINT": "https://app.phoenix.arize.com",
        },
    )
)

agent = Agent(
    name="phoenix_inspector",
    model="gemini-3.5-flash",
    tools=[phoenix_mcp],
)

# Test 1: can the agent list available Phoenix tools?
result = agent.run("List every tool you have available and what each one does.")
print(result)
```

- [ ] Run it. Verify the agent lists Phoenix MCP tools.

**CHECKLIST — confirm these tools exist (or equivalents):**
- [ ] `phoenix_get_traces` (or `list_traces`, `get_spans`) — read traces from a project
- [ ] `phoenix_create_dataset` (or `add_dataset`) — write a dataset
- [ ] `phoenix_run_experiment` (or `run_experiment`) — kick off an evaluation
- [ ] `phoenix_get_prompts` (read-only is fine for RAT)

**KILL TRIGGER:** If ANY of the first 3 tools above are missing, the ChaosLab loop can't close. Pivot to W8.

---

## Step 3 — Python SDK wrap test (30 min) — REVISED

> ⚠️ **PATCH 2026-06-02:** The architecture research discovered that Phoenix MCP server does NOT expose `run-experiment` or `create-experiment` tools — only read-side experiment tools (`list-experiments-for-dataset`, `get-experiment-by-id`). So the original Step 3 ("agent runs experiment via MCP") is structurally impossible. The architecture spec calls for wrapping `phoenix.client.AsyncClient().experiments.run_experiment(...)` as a **custom ADK `FunctionTool`**. This step validates that path works end-to-end.

**Goal:** Verify wrapping the Phoenix Python SDK as a custom ADK FunctionTool works end-to-end (run experiment + see results in Phoenix Cloud).

- [ ] Install Phoenix client SDK if not already: `pip install arize-phoenix-client`
- [ ] Create the test file:

```python
# /tmp/phoenix-rat/run_experiment_via_tool.py
import os
from google.adk import Agent
from google.adk.tools import FunctionTool
from phoenix.client import AsyncClient

phoenix = AsyncClient(
    base_url="https://app.phoenix.arize.com",
    api_key=os.environ["PHOENIX_API_KEY"],
)

async def run_phoenix_experiment(dataset_name: str) -> dict:
    """Runs a Phoenix experiment with a built-in tool-invocation eval."""
    dataset = await phoenix.datasets.get_dataset(name=dataset_name)
    result = await phoenix.experiments.run_experiment(
        dataset=dataset,
        task=lambda ex: {"output": "stub"},  # placeholder task
        evaluators=["tool_invocation"],
        experiment_name="rat-test",
    )
    return {"experiment_id": result.id, "metrics": result.metrics}

agent = Agent(
    name="phoenix_runner",
    model="gemini-3.5-flash",
    tools=[FunctionTool(run_phoenix_experiment)],
)

# Need a dataset to point to first — create one trivially in Phoenix UI
# named "rat-test" with 2-3 dummy spans before running this.

result = agent.run("Run the experiment on the 'rat-test' dataset.")
print(result)
```

- [ ] In Phoenix UI: create a small dataset named `rat-test` (2-3 dummy examples from your Step 1 traces)
- [ ] Run the Python script
- [ ] Open Phoenix Cloud dashboard → "Experiments" tab → confirm `rat-test` experiment appears with results

**PASS CRITERIA:** experiment is server-side visible + the agent's tool call returned a non-empty `experiment_id` + `metrics` dict.

**KILL TRIGGER:** If `experiments.run_experiment(...)` fails to return OR experiment doesn't materialize in Phoenix Cloud OR import errors on `phoenix.client`, pivot to W8 DataContract Sentinel. The closed-loop ChaosLab build requires this exact Python SDK path.

---

## Decision tree

| Outcome | Action |
|---|---|
| ✅ All 3 steps pass in ≤90 min | **COMMIT W1.** Tell Claude to fire `sahil-spec-writer` immediately. |
| ⚠️ Pass with caveats (e.g., one tool missing but workaround exists) | Tell Claude the caveats; we adjust the spec accordingly. |
| ❌ Hard fail on Step 1 (Phoenix not reachable) | Pivot to W8 DataContract Sentinel. Same brainstorm folder applies. |
| ❌ Hard fail on Step 2 (MCP tools missing) | Pivot to W8. ChaosLab's loop structurally can't close without these primitives. |
| ❌ Hard fail on Step 3 (can't run experiment) | Pivot to W8. Same reason. |

---

## Open questions Claude couldn't pre-verify (RAT must answer)

These come from `CONTEXT.md` §7 (Open questions):
- Phoenix MCP write-access to span annotations from inside an agent run — needed for clustering output
- Whether Phoenix MCP `streamable_http` keep-alive survives Cloud Run cold start
- Whether `phoenix_run_experiment` blocks or returns async (affects ChaosLab's 7-day continuous reasoning design)

Note these answers in `RAT-results.md` after running the RAT — they'll feed into the spec.

---

## Trigger sequence after RAT passes

1. Tell Claude: "RAT passed, all 3 steps green, here are the answers to the open questions" + paste any caveats
2. Claude fires `sahil-spec-writer` with the locked wedge + research folder as input
3. Spec-writer produces:
   - `docs/PRD.md` (product spec)
   - `docs/architecture.md` (system design)
   - `docs/ux-spec.md` (the demo + UI surface)
   - `docs/epics.md`
   - `docs/stories/story-<slug>.md` per story
4. You approve the artifact set
5. Claude fires `sahil-hackathon-orchestrator` which creates repo + issues + dispatches coding agents

---

## Trigger sequence after RAT fails

1. Tell Claude: "RAT failed on step N, pivoting to W8"
2. Claude re-loads `brainstorm/06-idea-rankings.md` §W8 deep-dive
3. Claude runs the W8 RAT (different — see below)
4. Same downstream sequence after W8 RAT passes

### W8 RAT (~2 hours, only if W1 dies)

1. Sign up for Fivetran trial → connect a sample source → trigger manual schema change → confirm event visible via MCP `list_schema_changes`
2. Connect to GitLab trial workspace → confirm `gitlab.com/api/v4/mcp` exposes `semantic_code_search` on a free trial (NOT Premium-gated)
3. Run one round-trip: "find files referencing `stripe.charges.amount_captured`" → confirm meaningful results

If W8 also dies, swap to W6 (World Cup Concierge) — that's the third fallback per `06-idea-rankings.md`.
