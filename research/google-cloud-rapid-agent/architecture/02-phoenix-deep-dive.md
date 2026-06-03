# Phoenix (Arize) Deep Dive — for ChaosLab build

**Downstream consumer:** ChaosLab for Agents (W1 wedge, Google Cloud Rapid Agent Hackathon)
**Build deadline:** 2026-06-11
**Author:** Claude (research agent), 2026-06-02
**Sources cited inline.** `[UNVERIFIED]` = could not pin down from docs alone, needs RAT.

This file lives next to `partner-arize.md` (high-level overview) and `RAT-runbook.md` (90-min test). Its job is to be the single load-bearing engineering reference for Phoenix usage in the ChaosLab build. Every code snippet here should compile.

---

## 0. The one-paragraph TL;DR

Phoenix MCP server (`@arizeai/phoenix-mcp` v1.1.0, Apache 2.0, npx) is **read-mostly observability glue**. Its 24 tools cover every Phoenix surface (projects, traces, spans, sessions, datasets, experiments, prompts, annotation configs) but it is asymmetric: dataset writes ✅ (`add-dataset-examples`), prompt writes ✅ (`upsert-prompt`, `add-prompt-version-tag`), but experiment writes ❌ (no `run-experiment`), annotation writes ❌ (no `log-span-annotation`). For ChaosLab to close the loop — generate trace → cluster failures → spawn dataset → run judge eval → write scores back to spans — the **MCP server handles steps 1–4, but the actual experiment execution AND the score-writeback MUST happen via the Python SDK** (`phoenix.client.Client.experiments.run_experiment(...)` + `client.spans.log_span_annotations_dataframe(...)`). This is the most important architectural finding in this doc. The MCP tools are how the AGENT introspects Phoenix; the SDK is how the AGENT writes back. Both run in the same Python process, sharing `PHOENIX_API_KEY`.

Bottom line: the wedge is buildable in 9 days. The "MCP-only" framing in `partner-arize.md` is wrong on the experiment-execution axis. Adjust the spec accordingly.

---

## 1. Phoenix MCP server — actual tool inventory

### 1.1 Package facts

- NPM: `@arizeai/phoenix-mcp` (source of truth: `js/packages/phoenix-mcp/package.json`, mirrored to npmjs.com)
- Server version string in code: `"phoenix-mcp-server" v1.1.0` (from `src/index.ts`)
- License: Apache 2.0
- Source layout: `js/packages/phoenix-mcp/src/` — file-per-category tool registration (`traceTools.ts`, `spanTools.ts`, etc.) hooked together in `index.ts`
- Transport: **stdio only** (literally `new StdioServerTransport()` in `src/index.ts`). There is no SSE / streamable HTTP transport in the MCP server package itself. If you need a hosted HTTP MCP server, you'd have to wrap it yourself or wait for upstream support.

Source: `gh api repos/Arize-ai/phoenix/contents/js/packages/phoenix-mcp/src/index.ts`

### 1.2 Install + config

```bash
# Smoke test (no install)
npx -y @arizeai/phoenix-mcp@latest --baseUrl https://app.phoenix.arize.com --apiKey $PHOENIX_API_KEY

# Or pin (recommended for hackathon repro)
npm install -g @arizeai/phoenix-mcp@latest
```

CLI flags (parsed via `minimist` in `src/index.ts`):
- `--apiKey <key>` — Phoenix API key
- `--baseUrl <url>` — Phoenix instance URL (e.g. `https://app.phoenix.arize.com`)
- `--project <project-name>` — Optional default project for project-scoped tools

Env vars (read by `src/config.ts`):
- `PHOENIX_API_KEY` — fallback if `--apiKey` not passed
- `PHOENIX_HOST` — fallback if `--baseUrl` not passed
- `PHOENIX_PROJECT` — fallback if `--project` not passed
- `PHOENIX_CLIENT_HEADERS` — optional JSON-encoded request headers

Source: `js/packages/phoenix-mcp/README.md` and `src/config.ts`.

### 1.3 Tool manifest — verbatim from source

The list below is verbatim from `src/index.ts` + the per-category source files (read 2026-06-02 from `Arize-ai/phoenix` main branch). Each entry lists: **tool name → parameters (Zod schema) → return shape**.

#### Projects (2 tools) — `src/projectTools.ts`

1. `list-projects` — `{ limit?: number }` → array of project objects
2. `get-project` — `{ project_identifier: string }` → single project object

#### Traces (2 tools) — `src/traceTools.ts`

3. `list-traces`
   - Params: `{ project_identifier?: string, limit?: number (max=MAX_TRACE_PAGE_SIZE, default=DEFAULT_TRACE_PAGE_SIZE), since?: string (ISO), last_n_minutes?: number, include_annotations?: boolean }`
   - Returns: `Trace[]` — each trace is built by `buildTrace({ spans })` and groups all spans under one `trace_id`.
   - Order: newest first (`sort: "start_time", order: "desc"`).
4. `get-trace`
   - Params: `{ project_identifier?: string, trace_id: string, include_annotations?: boolean }`
   - Returns: single `Trace` with ALL spans for that trace_id. Throws if not found.

#### Spans (2 tools) — `src/spanTools.ts`

5. `get-spans`
   - Params:
     ```ts
     {
       project_identifier?: string,
       start_time?: string,
       end_time?: string,
       trace_ids?: string[],
       parent_id?: string | null,
       names?: string[],
       span_kinds?: string[],         // e.g. ["LLM", "TOOL", "CHAIN", "AGENT", "RETRIEVER"]
       status_codes?: ("OK" | "ERROR" | "UNSET")[],
       cursor?: string,
       limit?: number (max=MAX_SPAN_QUERY_LIMIT, default=DEFAULT_PAGE_SIZE),
       include_annotations?: boolean,
     }
     ```
   - Returns: `{ spans: Span[], nextCursor: string | null }`
   - This is THE workhorse for ChaosLab's failure clustering. Filter by `status_codes: ["ERROR"]` + `start_time` for "all failures in the last hour".

6. `get-span-annotations`
   - Params: `{ project_identifier?: string, span_ids: string[], include_annotation_names?: string[], exclude_annotation_names?: string[], cursor?: string, limit?: number }`
   - Returns: `{ annotations: Annotation[], nextCursor: string | null }`
   - **READ-ONLY.** There is no MCP-server-side mutation tool here.

#### Sessions (2 tools) — `src/sessionTools.ts`

7. `list-sessions` — list multi-turn sessions
8. `get-session` — get a session by ID

#### Annotation Configs (1 tool) — `src/annotationConfigTools.ts`

9. `list-annotation-configs` — `{ limit?: number }` → array of annotation config objects. Annotation configs define the labels/scores schema (e.g. "correctness" with categorical {correct, incorrect}).
   - **No `create-annotation-config` and no `write-annotation` over MCP.**

#### Datasets (5 tools) — `src/datasetTools.ts`

10. `list-datasets` — `{ limit?: number (max=MAX_LIST_LIMIT, default=100) }` → `Dataset[]`
11. `get-dataset` — `{ dataset_id?: string, dataset_name?: string }` (exactly one required) → `Dataset`
12. `get-dataset-examples` — `{ dataset_id?: string, dataset_name?: string, version_id?: string, splits?: string[] }` → `{ dataset_id, version_id, examples: DatasetExample[] }`
13. `get-dataset-experiments` — `{ dataset_id?: string, dataset_name?: string, limit?: number }` → `Experiment[]`
14. `add-dataset-examples` — **WRITE TOOL**
    - Params:
      ```ts
      {
        dataset_name: string,
        examples: { input: Record<string, unknown>, output: Record<string, unknown>, metadata?: Record<string, unknown> }[]
      }
      ```
    - Behavior: POSTs to `/v1/datasets/upload` with `action: "append"`. Every example is auto-tagged `metadata.source = MCP_SYNTHETIC_SOURCE` so you can filter MCP-generated examples in the UI.
    - **This is the single most important write surface in the MCP server for ChaosLab.**

#### Experiments (2 tools) — `src/experimentTools.ts`

15. `list-experiments-for-dataset` — `{ dataset_id?: string, dataset_name?: string, limit?: number }` → `Experiment[]`
16. `get-experiment-by-id` — `{ experiment_id: string }` → `{ metadata, experimentResult }` (two parallel GETs: `/v1/experiments/{id}` for metadata, `/v1/experiments/{id}/json` for results)

**MAJOR GAP:** There is NO `run-experiment` tool on the MCP server. Confirmed by reading the entire `experimentTools.ts` source — the file only registers two tools (`list-experiments-for-dataset`, `get-experiment-by-id`). To kick off an experiment from inside an agent, you must call the Phoenix Python SDK directly from your agent code (see §2). The MCP server can READ experiments but not CREATE them.

This contradicts the RAT runbook Step 3 (which asks the agent to "run a simple experiment" via MCP). The actual flow for ChaosLab: the agent calls a CUSTOM ADK tool (a `FunctionTool` you write) that internally invokes `phoenix.client.Client().experiments.run_experiment(...)`. The MCP server's `add-dataset-examples` builds the dataset; your custom Python tool fires the experiment.

#### Prompts (10 tools) — `src/promptTools.ts`

17. `list-prompts` — `{ limit?: number }` → `Prompt[]`
18. `get-prompt` — `{ prompt_identifier?: string, tag?: string, version_id?: string }` → `PromptVersion`
19. `get-latest-prompt` — `{ prompt_identifier: string }` → `PromptVersion`
20. `get-prompt-by-identifier` — `{ prompt_identifier: string }` → `PromptVersion`
21. `get-prompt-version` — `{ version_id: string }` → `PromptVersion`
22. `list-prompt-versions` — `{ prompt_identifier: string, limit?: number }` → `PromptVersion[]`
23. `get-prompt-version-by-tag` — `{ prompt_identifier: string, tag: string }` → `PromptVersion`
24. `list-prompt-version-tags` — `{ version_id: string, limit?: number }` → `Tag[]`
25. `add-prompt-version-tag` — `{ version_id: string, tag_name: string }` → 204 confirmation (WRITE)
26. `upsert-prompt` — create-or-update a prompt with a chat template, model config, invocation params (WRITE)

Note: the README lists "Prompts (8 tools)" but the actual source registers 10 prompt-tool handlers. README is mildly out of date.

### 1.4 Summary table — what's writable from the MCP server

| Category | Read | Write |
|---|---|---|
| Projects | ✅ list, get | ❌ |
| Traces | ✅ list, get | ❌ |
| Spans | ✅ get-spans (filterable), get-span-annotations | ❌ |
| Sessions | ✅ list, get | ❌ |
| Annotation configs | ✅ list | ❌ (no create, no write annotation) |
| Datasets | ✅ list, get, examples, experiments | ✅ `add-dataset-examples` |
| Experiments | ✅ list-for-dataset, get-by-id | ❌ (no run, no create) |
| Prompts | ✅ list, get-many-ways | ✅ `upsert-prompt`, `add-prompt-version-tag` |

### 1.5 What the docs page got wrong/missing

- `arize.com/docs/phoenix/integrations/phoenix-mcp-server` lists functional capabilities but no tool names. The README in the repo (and `src/index.ts`) is the actual source of truth. Always cross-check against `package.json#version`.
- The pulsemcp.com listing references `--baseUrl https://app.phoenix.arize.com` — that's the Phoenix Cloud public URL, but note Phoenix Cloud assigns each user a SPACE within that domain (see §7), so the actual collector endpoint for your traces is `https://app.phoenix.arize.com/s/<your-space-name>`. The MCP baseUrl is the root.

---

## 2. Phoenix Python SDK — the write surface

### 2.1 The two SDK packages

| Package | Purpose | Pin |
|---|---|---|
| `arize-phoenix` | Full server + Python client (datasets, experiments, evaluators) | `pip install arize-phoenix` |
| `arize-phoenix-otel` | Lightweight OTEL register / tracer provider helper | `pip install arize-phoenix-otel` |
| `arize-phoenix-evals` | Evaluator templates (`HallucinationEvaluator`, `ClassificationEvaluator`, etc.) | `pip install arize-phoenix-evals` |
| `arize-phoenix-client` | Just the REST client (lighter, used when you only need to read/write to a remote Phoenix) | `pip install arize-phoenix-client` |

For ChaosLab on Phoenix Cloud (not self-hosted), the minimum install is:
```bash
pip install arize-phoenix-client arize-phoenix-otel arize-phoenix-evals \
    openinference-instrumentation-google-adk \
    opentelemetry-exporter-otlp \
    google-adk
```

You do NOT need the full `arize-phoenix` because you're not running a local Phoenix server.

### 2.2 The two clients (sync + async)

```python
from phoenix.client import Client          # sync
from phoenix.client import AsyncClient     # async (use inside async ADK code paths)
```

Both expose the same resource namespaces:
- `client.datasets` — `create_dataset`, `get_dataset`, `add_examples`
- `client.experiments` — `run_experiment`, `evaluate_experiment`, `get_experiment`
- `client.spans` — `get_spans`, `get_spans_dataframe`, `log_span_annotations`, `log_span_annotations_dataframe`
- `client.prompts` — get/upsert
- `client.projects` — list/get

Source: `packages/phoenix-client/docs/source/api/*.md` in `Arize-ai/phoenix`.

### 2.3 `run_experiment` — full signature

From `packages/phoenix-client/docs/source/api/experiments.md`:

```python
client.experiments.run_experiment(
    dataset,                                   # Dataset object (required)
    task,                                      # sync or async callable: example -> output (required)
    evaluators=None,                           # list of evaluator callables/objects
    experiment_name=None,                      # str
    experiment_description=None,               # str
    experiment_metadata=None,                  # dict
    rate_limit_errors=None,                    # exception or list of exceptions to throttle on
    dry_run=False,                             # True or int -> deterministic sample size
    print_summary=True,                        # noisy console summary
    timeout=60,                                # seconds per task call
    repetitions=1,                             # run each example N times
    retries=3,                                 # task retry count
)
# Returns: RanExperiment (dict-like with .id, .as_dataframe() — implied but not fully documented)
```

`AsyncClient().experiments.run_experiment(...)` also exists; takes a `concurrency` parameter (confirmed in hallucination benchmark notebook: `concurrency=10`). The sync client's concurrency is `[UNVERIFIED]` — likely defaults to a small worker pool; the docs don't say. For ChaosLab use the AsyncClient if you want explicit concurrency control.

**Critical behavior point: `run_experiment` IS SYNCHRONOUS by default** (blocks until all examples × repetitions have run, plus all evaluators). With `dataset_size=100, repetitions=1, evaluators=1, timeout=60`, worst-case wall time is `100 * 60 = 6000s = 100 min`. With `concurrency=10` (AsyncClient), divide by ~10. **For ChaosLab's 7-day continuous loop, plan for non-blocking calls via the async client + `concurrency=10..20`.** Or shell out to a background asyncio task.

### 2.4 Programmatic dataset creation

```python
from phoenix.client import Client
import pandas as pd

px_client = Client()

# Option A: from a DataFrame
df = pd.DataFrame({
    "question": [...],
    "expected_answer": [...],
})
dataset = px_client.datasets.create_dataset(
    dataframe=df,
    name="chaoslab-failures-2026-06-04",
    input_keys=["question"],
    output_keys=["expected_answer"],
)

# Option B: from explicit lists
dataset = px_client.datasets.create_dataset(
    name="chaoslab-failures-2026-06-04",
    inputs=[{"question": q} for q in questions],
    outputs=[{"expected": e} for e in expected_outputs],
)
```

### 2.5 SDK-only capabilities (not via MCP)

| Capability | SDK method | Why it's not MCP |
|---|---|---|
| Run an experiment | `client.experiments.run_experiment(...)` | Requires passing a Python callable as `task`; MCP can't serialize a Python function. |
| Write span annotations | `client.spans.log_span_annotations(...)` / `_dataframe(...)` | No MCP tool — confirmed by reading `annotationConfigTools.ts` (only `list-annotation-configs`). |
| Evaluate an existing experiment | `client.experiments.evaluate_experiment(experiment, evaluators)` | Same reason as run_experiment. |
| Query spans into pandas | `client.spans.get_spans_dataframe(query=SpanQuery().where(...))` | MCP only returns JSON spans, no pandas pipeline. |
| Use built-in evaluators (`HallucinationEvaluator`, `ClassificationEvaluator`) | `phoenix.evals.*` | Pure Python — not exposed over MCP. |

**The relationship between MCP and SDK is:** both hit the same Phoenix REST API (`/v1/...`), with the MCP server being a thin proxy over `@arizeai/phoenix-client` (TypeScript). The SDK can do everything the MCP can, PLUS the writes/runs that don't fit in stateless tool semantics. For ChaosLab, the agent uses MCP tools for read+dataset-write paths, and a SMALL set of custom Python FunctionTools (wrapping `run_experiment`, `log_span_annotations`) for the write/run paths.

---

## 3. OpenInference + Google ADK auto-instrumentation

### 3.1 The library

- PyPI: `openinference-instrumentation-google-adk`
- Repo: `Arize-ai/openinference`, path `python/instrumentation/openinference-instrumentation-google-adk/`
- The package wraps the `google-adk` runtime via OpenTelemetry. Source files: `_wrappers.py` (the actual instrumented methods), `__init__.py` (entrypoint).

Install:
```bash
pip install openinference-instrumentation-google-adk arize-phoenix-otel google-adk
```

### 3.2 What gets auto-traced

From the OpenInference ADK README + the OpenInference span spec (`Arize-ai/openinference/spec/llm_spans.md`):

| Auto-traced | Detail | Span kind |
|---|---|---|
| Agent run (top-level) | start, end, input message, final response | `AGENT` |
| Sub-agent delegation | parent agent → child agent span | `AGENT` (child of parent) |
| Gemini model calls | request payload, response, model name, token counts, invocation params | `LLM` |
| Tool function calls | tool name, arguments, return value, errors | `TOOL` |
| Multi-turn conversation context | each user/assistant message preserved on the LLM span | `LLM` attribute `llm.input_messages` |
| Errors | `status.code = "ERROR"`, exception attributes propagated | any |
| Retries | each retry attempt produces its own span (parent-child) | varies |
| Latency | OTEL `start_time`/`end_time` on every span | all |

### 3.3 What is NOT auto-traced (you must emit manually)

- **MCP tool calls within ADK.** ADK wraps MCPToolset as ADK tools, but the underlying MCP wire calls (JSON-RPC over stdio/HTTP) are NOT spanned by `GoogleADKInstrumentor`. To trace MCP traffic specifically, you'd add `openinference-instrumentation-mcp` (a SEPARATE Python package — it's the MCP-side instrumentor, not an MCP server). For ChaosLab this matters: if Phoenix MCP server tool calls fail, you want them in the trace. Add `openinference-instrumentation-mcp` to the install list.
- Any pure-Python computation that doesn't go through ADK's runner (e.g., your custom data-processing functions outside of a `FunctionTool` wrapper).
- Custom HTTP calls (e.g., calling a Cloud Run endpoint from a tool) — those go untraced unless you wrap with `openinference-instrumentation-httpx` or similar.

### 3.4 Minimal "ADK + auto-instrument + Phoenix Cloud" working snippet

```python
# agent.py — local dev OR Cloud Run deployment
import os
from phoenix.otel import register
from openinference.instrumentation.google_adk import GoogleADKInstrumentor
from google.adk.agents import Agent

os.environ["PHOENIX_API_KEY"] = os.environ["PHOENIX_API_KEY"]                # required
os.environ["PHOENIX_COLLECTOR_ENDPOINT"] = "https://app.phoenix.arize.com/s/your-space-name"

# IMPORTANT for Agent Engine: see §3.5 — must pass set_global_tracer_provider=False
tracer_provider = register(
    project_name="chaoslab",
    auto_instrument=True,       # also picks up other openinference-* libs that are installed
    batch=True,                  # use SimpleSpanProcessor for low-latency tests, BatchSpanProcessor in prod
)
GoogleADKInstrumentor().instrument(tracer_provider=tracer_provider)

def echo(text: str) -> dict:
    """Echoes input back. Tracing-friendly toy tool."""
    return {"echo": text}

root_agent = Agent(
    name="chaoslab_root",
    model="gemini-2.5-flash",
    instruction="You are ChaosLab. Use the echo tool when asked.",
    tools=[echo],
)
```

Source: combined from `phoenix.otel` docs + `openinference-instrumentation-google-adk` README.

### 3.5 Agent Engine remote deployment caveat — DON'T MISS THIS

From `arize.com/docs/phoenix/integrations/python/google-adk/google-adk-tracing` (per WebFetch summary 2026-06-02):

> "For Vertex AI Agent Engine (remote deployment): instrumentation must be configured WITHIN the remote agent module, not in the main application code. Place `register()` in your agent module (`adk_agent.py`) with `set_global_tracer_provider=False`. This prevents Vertex AI's aggressive OpenTelemetry management from shutting down the Phoenix export pipeline during container initialization."
>
> "For Agent Engine, use `batch=False` for synchronous export, since Agent Engine pauses CPU after requests."

Translated for ChaosLab:
- If we deploy on **Cloud Run** (current plan): use the snippet in §3.4 verbatim, `set_global_tracer_provider=True` (default), `batch=True`. Standard.
- If we deploy on **Agent Engine** (probably not, but flagged for completeness):
  ```python
  tracer_provider = register(
      project_name="chaoslab",
      auto_instrument=True,
      batch=False,                        # synchronous export — CPU pause hostile
      set_global_tracer_provider=False,   # isolated, won't be torn down
  )
  ```
  AND the `register()` + `GoogleADKInstrumentor().instrument(tracer_provider=tracer_provider)` calls must live inside the agent module that Agent Engine loads (e.g., `agent.py`), NOT in a separate driver/main file. Local-side instrumentation does not propagate to the remote container.

Recommendation: **stick with Cloud Run for ChaosLab.** Avoid this trap.

---

## 4. Trace + span data model

### 4.1 Hierarchy

```
Project (e.g. "chaoslab")
└── Trace (one per top-level agent invocation, trace_id is a hex string)
    └── Span (AGENT kind, the root)
        ├── Span (LLM kind — first Gemini call)
        ├── Span (TOOL kind — first tool invocation)
        │   └── Span (LLM kind — if tool calls Gemini internally)
        ├── Span (AGENT kind — sub-agent delegation)
        │   └── ...
        └── Span (LLM kind — final response generation)
```

Every span has: `id`, `trace_id`, `parent_id` (null for root), `name`, `start_time`, `end_time`, `status_code` (`OK`/`ERROR`/`UNSET`), `attributes`.

Sessions sit one level above traces: a "session" is a multi-turn conversation containing N traces (one per turn).

### 4.2 Standard OpenInference span attributes

From `Arize-ai/openinference/spec/llm_spans.md` (the canonical schema):

| Attribute | Type | Meaning | Set on |
|---|---|---|---|
| `openinference.span.kind` | string | `LLM` / `TOOL` / `AGENT` / `CHAIN` / `RETRIEVER` / `EMBEDDING` / `RERANKER` / `EVALUATOR` | every span |
| `input.value` | string (often JSON) | what went in | every span |
| `input.mime_type` | string | usually `application/json` or `text/plain` | every span |
| `output.value` | string | what came out | every span |
| `output.mime_type` | string | | every span |
| `llm.system` | string | `openai` / `google` / `anthropic` etc. | LLM spans |
| `llm.model_name` | string | e.g. `gemini-2.5-flash` | LLM spans |
| `llm.invocation_parameters` | JSON string | temperature, max_tokens, top_p | LLM spans |
| `llm.input_messages` | array of `{message.role, message.content}` | full conversation history | LLM spans |
| `llm.output_messages` | array — includes `message.tool_calls[].tool_call.function.{name,arguments}` | model response | LLM spans |
| `llm.token_count.prompt` | int | | LLM spans |
| `llm.token_count.completion` | int | | LLM spans |
| `llm.token_count.total` | int | | LLM spans |
| `tool.name` | string | name of the function tool | TOOL spans |
| `tool.parameters` | JSON string | tool call args | TOOL spans |

### 4.3 Querying spans for ChaosLab failure clustering

Three available query paths, in order of preference for ChaosLab:

**A. SDK SpanQuery DSL** (most powerful):
```python
from phoenix.client import Client
from phoenix.client.types.spans import SpanQuery

query = SpanQuery().where("status_code == 'ERROR' and span_kind == 'TOOL'")
df = Client().spans.get_spans_dataframe(project_identifier="chaoslab", query=query)
```

**B. SDK `get_spans` with filters** (Phoenix server ≥14.9.0 required for attribute filtering):
```python
spans = Client().spans.get_spans(
    project_identifier="chaoslab",
    status_code="ERROR",
    span_kind="TOOL",
    attributes={"llm.model_name": "gemini-2.5-flash"},
    limit=500,
)
```

**C. MCP `get-spans` tool** (what the agent itself calls):
```json
{
  "tool": "get-spans",
  "arguments": {
    "project_identifier": "chaoslab",
    "status_codes": ["ERROR"],
    "span_kinds": ["TOOL"],
    "last_n_minutes": 60,
    "limit": 200,
    "include_annotations": true
  }
}
```

The MCP tool returns JSON; the SDK methods return pandas. For ChaosLab's failure-clustering logic (compute embeddings on span output strings, k-means cluster), prefer the SDK pandas path — the agent's tool that does clustering should use the SDK internally.

### 4.4 What ChaosLab needs to WRITE

ChaosLab's value prop is writing back enrichments. The available write surfaces are:

1. **Span annotations** — `client.spans.log_span_annotations(...)` (SDK only, NOT via MCP). Each annotation has `name`, `span_id`, `annotator_kind` (`"LLM"`/`"HUMAN"`/`"CODE"`), `result.{label, score, explanation}`, optional `metadata`. This is THE primary writeback channel for ChaosLab's failure scores. Example:
   ```python
   from phoenix.client.resources.spans import SpanAnnotationData
   ann = SpanAnnotationData(
       name="chaoslab_failure_cluster",
       span_id=span_id,
       annotator_kind="LLM",
       result={"label": "stripe_404_pattern", "score": 0.92, "explanation": "Cluster of tool calls failing on missing customer_id"},
   )
   await async_client.spans.log_span_annotations(span_annotations=[ann])
   ```

2. **Dataset entries** — via MCP `add-dataset-examples` OR SDK `client.datasets.add_examples(...)`. Adding a failing span as a "this should not happen" regression test.

3. **Prompt versions** — via MCP `upsert-prompt`. If ChaosLab synthesizes a hardened prompt variant after seeing a failure pattern, it can register the new version with a `chaoslab-suggested` tag.

4. **Experiments** — via SDK `run_experiment(...)`. The "run a judge over the failure dataset" step.

5. **NOT writable from agent code:** annotation config schemas (you create those once in the UI before the run), project metadata.

---

## 5. LLM-as-a-judge eval templates Phoenix ships

### 5.1 The eval primitives

Three layers of abstraction (PRO TIP: don't conflate them):

1. **Raw prompt templates** — string constants like `HALLUCINATION_PROMPT_TEMPLATE` from `phoenix.evals`. These define the rubric text + the answer rails (e.g. `["factual", "hallucinated"]`).
2. **`llm_classify(dataframe, template, model, rails)`** — the legacy classify-a-DataFrame helper. Returns a DataFrame with predicted labels + optional explanation column.
3. **Evaluator classes** — `HallucinationEvaluator`, `ClassificationEvaluator`, `ToolResponseEvaluator`, etc., from `phoenix.evals`. These are the per-row, async-friendly evaluators you pass to `run_experiment(evaluators=[...])`.

### 5.2 Built-in prompt template — Hallucination (actual prompt text)

From `tutorials/llm_application_tracing_evaluating_and_analysis.ipynb` (verbatim):

```python
hallucination_prompt = """
In this task, you will be presented with a query, a reference text and an answer. The answer is
generated to the question based on the reference text. The answer may contain false information.
You must use the reference text to determine if the answer to the question contains false information,
if the answer is a hallucination of facts. Your objective is to determine whether the answer text
contains factual information and is not a hallucination. A 'hallucination' refers to
an answer that is not based on the reference text or assumes information that is not available in
the reference text. Your response should be a single word: either "factual" or "hallucinated", and
it should not include any other text or characters. "hallucinated" indicates that the answer
provides factually inaccurate information to the query based on the reference text. "factual"
indicates that the answer to the question is correct relative to the reference text, and does not
contain made up information.

    [BEGIN DATA]
    ************
    [Query]: {input}
    ************
    [Reference text]: {reference}
    ************
    [Answer]: {output}
    ************
    [END DATA]

    Is the answer above factual or hallucinated based on the query and reference text?
"""
```

Rails: `["factual", "hallucinated"]`.

### 5.3 Built-in prompt template — Tool selection correctness (actual prompt text)

From `tutorials/evals/evaluate_agent_tool_selection_classifications.ipynb`:

```python
TOOL_SELECTION_PROMPT_TEMPLATE = """
You are an evaluation assistant assessing whether a tool call correctly matches a user's question.
Your task is to decide if the tool selected is the best choice to answer the question,
using only the list of available tools provided below. You are not responsible for checking the
parameters or arguments passed to the tool. You are evaluating **only** whether the correct tool
was selected based on the content of the question. Think like a grading rubric. Be strict. If the
selected tool is not clearly correct based on the question alone, label it "incorrect". Do not
make assumptions or infer information that is not explicitly stated in the question.
Only use the information provided.

Your response must be a **single word**: either `"correct"` or `"incorrect"`.
Do not include any explanation, punctuation, or other characters. The output will be parsed
programmatically.

---

Label the tool call as `"correct"` if **all** of the following are true:
- The selected tool is clearly the best fit to answer the user's question
- The tool is among those available in the tool list
- The question contains enough explicit information to justify selecting this tool

Label the tool call as `"incorrect"` if **any** of the following are true:
- A more appropriate tool exists to answer the question
- The tool is not clearly justified by the question content
- The tool would not produce a relevant or meaningful answer to the question

---

[BEGIN DATA]
************
[Question]: {question}
************
[Tool Called]: {tool_call}
[END DATA]

[Tool Definitions]: {tool_definitions}
"""
```

Rails: `["correct", "incorrect"]`. This is the closest off-the-shelf template to ChaosLab's "did this tool call succeed?" rubric. Customize the system prompt to bias toward strictness when grading tool-call FAILURES (as opposed to selections).

### 5.4 Custom eval prompt for ChaosLab — "did the tool call succeed?"

ChaosLab's specific need: given a TOOL span (with input args, output, status), did it functionally succeed? Status alone isn't enough — a tool can return `status_code=OK` but return garbage. Custom template:

```python
CHAOSLAB_TOOL_SUCCESS_TEMPLATE = """
You are an evaluator judging whether a tool call inside an autonomous agent functionally succeeded.

A tool call "succeeded" only if ALL of these are true:
1. The status code is OK (no exception thrown).
2. The output payload is non-empty and well-formed.
3. The output answers the apparent intent of the tool's inputs (e.g., a search returning hits, not "no results"; a write returning a confirmation, not silence).
4. There are no error strings, "could not", "unable to", "rate limit", "404", "500" in the output.

Respond with EXACTLY ONE WORD: `success` or `failure`.

[Tool Name]: {tool_name}
[Tool Inputs]: {tool_args}
[Tool Output]: {tool_output}
[Status Code]: {status_code}
"""
```

Wire it via `ClassificationEvaluator`:

```python
from phoenix.evals import LLM, ClassificationEvaluator

llm = LLM(provider="google_genai", model="gemini-2.5-flash")
chaoslab_eval = ClassificationEvaluator(
    name="chaoslab_tool_success",
    llm=llm,
    prompt_template=CHAOSLAB_TOOL_SUCCESS_TEMPLATE,
    choices={"success": 1.0, "failure": 0.0},
)
result = chaoslab_eval.evaluate({
    "tool_name": span_attrs["tool.name"],
    "tool_args": span_attrs["tool.parameters"],
    "tool_output": span_attrs["output.value"],
    "status_code": span.status_code,
})
```

### 5.5 Registering a custom eval as a "prompt" in Phoenix

Custom evaluators live primarily in your Python code. But you CAN register the rubric prompt as a Phoenix prompt for versioning + the prompt-management story:

```python
# Via MCP — agent self-modifying its own eval rubric
{
  "tool": "upsert-prompt",
  "arguments": {
    "name": "chaoslab_tool_success_eval",
    "description": "Judges whether a single tool call functionally succeeded",
    "template": "<paste CHAOSLAB_TOOL_SUCCESS_TEMPLATE>",
    "model_provider": "GOOGLE_GENAI",
    "model_name": "gemini-2.5-flash",
    "tag": "chaoslab-v1"
  }
}
```

Then the agent later fetches the active prompt via `get-prompt-by-identifier` and uses it as the rubric. This is the "self-improvement" loop the Arize track explicitly bonuses (per `partner-arize.md`).

---

## 6. Experiment execution model

### 6.1 Sync vs async

- `Client().experiments.run_experiment(...)` — **blocking**. Returns only after all `dataset_size × repetitions` task calls + all evaluator runs finish. Useful for one-shot.
- `AsyncClient().experiments.run_experiment(...)` — **awaitable**. Takes a `concurrency=N` parameter (confirmed: `concurrency=10` in the hallucination benchmark notebook).

For ChaosLab's design — the agent fires a "judge over these 50 failures" command and continues reasoning while it runs — use `AsyncClient`, await with `asyncio.create_task(...)` to avoid blocking the agent's main loop, then poll via `client.experiments.get_experiment(experiment_id)`.

### 6.2 How to fetch results back

```python
# After run_experiment returned an experiment with .id
experiment = client.experiments.get_experiment(experiment_id=experiment.id)
# experiment.runs - the per-example outputs
# experiment.evaluations - the per-example scores
df = experiment.as_dataframe()    # [UNVERIFIED — implied by docs but not in primary API ref]
```

Or via MCP:
```json
{ "tool": "get-experiment-by-id", "arguments": { "experiment_id": "RXhwZXJpbWVudDo4" } }
```
Returns `{ metadata, experimentResult }` — two parallel API calls behind the scenes (`/v1/experiments/{id}` for metadata, `/v1/experiments/{id}/json` for results).

### 6.3 Concurrency + rate limit handling

- `AsyncClient` supports `concurrency=N` on `run_experiment`. Default `[UNVERIFIED]` — likely `1` or a small default. Pass it explicitly.
- `run_experiment(rate_limit_errors=[...])` accepts a list of exception classes; when caught, Phoenix backs off and retries. Use this for Gemini's `ResourceExhausted` exceptions.
- `retries=3` (default) means each task attempt has up to 3 retries on uncaught exceptions before being marked failed in the experiment.

### 6.4 Cost: how many LLM calls per experiment?

For an experiment with `N` examples, `R` repetitions, `E` evaluators (each a 1-LLM-call classifier):

- Task calls: `N × R` (each task call typically = 1 LLM call if your task is a Gemini call; could be 0 if pure code, or many if it's an agent run)
- Evaluator calls: `N × R × E` (each evaluator runs once per task result)
- Total: `N × R × (1 + E)` LLM calls (assuming 1-LLM-call task and per-row evaluators)

ChaosLab's typical experiment: cluster has 30 failing spans, judge with 1 evaluator, no repetitions → `30 × 1 × (1 + 1) = 60` LLM calls. At Gemini 2.5 Flash ($0.30/M input, $2.50/M output) and ~1k tokens per call (mostly input), that's ~`60 * 0.001 * 0.30 = $0.018` for inputs + ~`60 * 0.0002 * 2.50 = $0.03` for outputs = **~$0.05 per ChaosLab cycle**. Bonkers cheap. The $100 credit easily covers 2000 cycles.

---

## 7. Phoenix Cloud vs self-hosted Phoenix

### 7.1 Phoenix Cloud free tier — confirmed limits

Per `arize.com/pricing/` (WebFetch 2026-06-02 — the page is named "AX Free" but Phoenix Cloud is in the same Arize product line and runs on the same free SKU):

- **Storage:** 1 GB / month
- **Span retention:** 15 days
- **Max spans / month:** **25,000**
- **Projects:** N/A (likely effectively unlimited within storage cap)
- **Support:** Community Slack
- **API rate limits:** Not published.

**For ChaosLab specifically: 25k spans/month is TIGHT.** A target agent with chained tool calls easily emits 20+ spans per run. 25k / 20 = 1250 runs/month before the cap. During a 9-day build with active iteration, that's plausibly hit. **Mitigation:** turn down trace sampling, or self-host Phoenix locally for dev (free, infinite) and only push to Cloud for the demo recording.

Phoenix Cloud paid tier ("AX Pro"): $50/month, 50k spans/month, 10 GB storage, 30-day retention.

### 7.2 Self-hosted Phoenix

- Apache 2.0, `pip install arize-phoenix` then `phoenix serve` (binds to `localhost:6006`).
- Or Docker: `docker run -p 6006:6006 -p 4317:4317 arizephoenix/phoenix:latest`.
- Default retention: indefinite. Configurable via `PHOENIX_DEFAULT_RETENTION_POLICY_DAYS` env var.
- No span/project limits.
- Setup time: ~5 minutes local, 15 minutes containerized on Cloud Run with persistent volume.

### 7.3 Recommendation for ChaosLab

**Hybrid:**
- **Local dev (days 1–7):** self-hosted Phoenix via Docker on Abu's laptop. Free, no span cap, full-fidelity tracing.
- **Demo recording (day 8–9):** push a curated subset to Phoenix Cloud at `https://app.phoenix.arize.com/s/<space>` so the judges can click in. This satisfies the "live observability dashboard" demo requirement without burning the cap mid-build.
- **Judging (judging window):** keep the Cloud project alive for ~2 weeks. 25k cap should hold if no new runs.

This also dodges the latency concern: pushing to Phoenix Cloud from Cloud Run can add 200–500ms per trace export.

---

## 8. Auth, rate limits, gotchas

### 8.1 API key handling

- Phoenix Cloud: one API key per workspace, generated in Settings → API Keys. Format: opaque string.
- Pass via env var (`PHOENIX_API_KEY`) — the SDK reads it automatically. The MCP server requires the same env var OR the `--apiKey` CLI flag.
- The endpoint must include the SPACE in the path: `https://app.phoenix.arize.com/s/<your-space-name>` — NOT the bare root URL. This is the most common config mistake.

### 8.2 MCP transport — stdio only

- The Phoenix MCP server in `js/packages/phoenix-mcp/src/index.ts` uses `StdioServerTransport` and nothing else.
- For ADK integration via `MCPToolset`, this means `StdioServerParameters` (NOT `SseServerParams`).
- For Cloud Run deployment: the MCP server runs as a child process of the agent container. `npx` must be in `PATH` (install Node in the Dockerfile).
- **No "streamable HTTP" / SSE transport** today. This eliminates a class of bugs (cold-start keep-alive over SSE) but means the MCP server can't be hosted as a separate service.

### 8.3 Known gotchas (from docs + source reading + community signals)

1. **`add-dataset-examples` auto-tags `metadata.source = "MCP_SYNTHETIC_SOURCE"`.** If you want to filter dataset examples that the agent added vs. seed examples, query on this metadata field. (Source: `src/constants.ts` + `src/datasetTools.ts`.)
2. **`get-spans` defaults to a small page size.** Default = `DEFAULT_PAGE_SIZE` constant (typically 100). Cap = `MAX_SPAN_QUERY_LIMIT` (likely 1000). Iterate with `cursor` for full coverage.
3. **Attribute filtering on `get_spans` requires Phoenix server ≥14.9.0.** Phoenix Cloud is current; self-hosted may not be. If your filter silently ignores the `attributes={}` param, check your Phoenix version.
4. **Phoenix Cloud instances created before June 24, 2025** require an extra `PHOENIX_CLIENT_HEADERS` env var with the auth header pre-formatted. New instances (Abu's will be new) use the simpler `PHOENIX_API_KEY` only. (Source: `arize.com/docs/phoenix/environments`.)
5. **Agent Engine + Phoenix tracing requires `set_global_tracer_provider=False` + `batch=False`** — see §3.5.
6. **MCP processes leak if not closed.** ADK's `MCPToolset` should be used inside an `async with` block or with explicit `await toolset.close()`. Otherwise child `npx` processes accumulate.
7. **Experiment runs are NOT cancellable mid-flight via MCP.** Once you fire `run_experiment`, there's no `cancel-experiment` tool. Plan for max-timeout per task call (`timeout=60`).
8. **OpenInference `auto_instrument=True` blindly hooks every installed openinference-* package.** If you `pip install openinference-instrumentation-langchain` (even by accident, e.g., via a transitive dep), it'll start emitting LangChain spans into Phoenix, polluting your project. Pin and audit your dependency tree.
9. **The MCP server is single-tenant per process.** It connects to one Phoenix `--baseUrl` at a time. If ChaosLab wants to read from project A and write to project B, both must be on the same Phoenix instance (Cloud or self-hosted).
10. **No bulk delete tool.** If you pollute a project with junk traces during dev, you have to clear via the UI (Settings → Data Retention) or wipe the database. Plan for separate Phoenix projects for `chaoslab-dev` vs `chaoslab-demo`.

---

## 9. Code patterns ChaosLab will need (paste-ready)

### 9.1 Pattern A — Instrument a target ADK agent → push to Phoenix Cloud

```python
# target_agent/agent.py — the agent under observation by ChaosLab
import os
from phoenix.otel import register
from openinference.instrumentation.google_adk import GoogleADKInstrumentor
from google.adk.agents import Agent
from google.adk.tools import FunctionTool

# Phoenix Cloud auth — set these in your runtime (Cloud Run env vars, or .env locally)
# os.environ["PHOENIX_API_KEY"] = "..."
# os.environ["PHOENIX_COLLECTOR_ENDPOINT"] = "https://app.phoenix.arize.com/s/abu-rapidagent"

tracer_provider = register(
    project_name="chaoslab-target",          # the project ChaosLab observes
    auto_instrument=True,                     # also enables openinference-instrumentation-mcp if installed
    batch=True,                               # OK on Cloud Run; flip to False on Agent Engine
)
GoogleADKInstrumentor().instrument(tracer_provider=tracer_provider)

def stripe_charge(customer_id: str, amount_cents: int) -> dict:
    """Charges a customer's stored card. Calls Stripe."""
    # ... real call ...
    return {"status": "ok", "charge_id": "ch_xxx"}

target_agent = Agent(
    name="payment_agent",
    model="gemini-2.5-flash",
    instruction="You process customer payments. Use the stripe_charge tool.",
    tools=[FunctionTool(func=stripe_charge)],
)
```

### 9.2 Pattern B — Connect a ChaosLab ADK agent to Phoenix MCP server

```python
# chaoslab/agent.py — the observer agent
import os
from contextlib import AsyncExitStack
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool import MCPToolset
from mcp import StdioServerParameters

async def build_chaoslab_agent():
    phoenix_mcp = MCPToolset(
        connection_params=StdioServerParameters(
            command="npx",
            args=[
                "-y",
                "@arizeai/phoenix-mcp@latest",
                "--baseUrl", os.environ["PHOENIX_COLLECTOR_ENDPOINT"],   # https://app.phoenix.arize.com/s/<space>
                "--apiKey",  os.environ["PHOENIX_API_KEY"],
                "--project", "chaoslab-target",                         # default project for project-scoped reads
            ],
            env={
                # belt-and-suspenders — phoenix-mcp ALSO reads env vars
                "PHOENIX_API_KEY":  os.environ["PHOENIX_API_KEY"],
                "PHOENIX_HOST":     os.environ["PHOENIX_COLLECTOR_ENDPOINT"],
                "PHOENIX_PROJECT":  "chaoslab-target",
            },
        ),
        # whitelist only the tools ChaosLab actually needs — keeps Gemini context lean
        tool_filter=[
            "list-traces", "get-trace",
            "get-spans", "get-span-annotations",
            "list-datasets", "get-dataset", "get-dataset-examples", "add-dataset-examples",
            "list-experiments-for-dataset", "get-experiment-by-id",
            "list-prompts", "get-prompt", "upsert-prompt",
        ],
    )

    # Plus a CUSTOM Python tool for the things MCP can't do (run_experiment, log_span_annotations)
    from chaoslab.custom_tools import run_judge_experiment, write_span_annotation
    from google.adk.tools import FunctionTool

    chaoslab_agent = LlmAgent(
        name="chaoslab_inspector",
        model="gemini-2.5-pro",         # root reasoner — pro is worth it here
        instruction=(
            "You are ChaosLab. Continuously inspect the 'chaoslab-target' project for failing tool calls. "
            "When you find a cluster of failures, create a dataset, run a judge experiment, "
            "annotate the spans with the failure pattern, and emit a postmortem."
        ),
        tools=[phoenix_mcp, FunctionTool(run_judge_experiment), FunctionTool(write_span_annotation)],
    )
    return chaoslab_agent, phoenix_mcp
```

### 9.3 Pattern C — Read last N failing traces from a project

```python
# chaoslab/queries.py — used inside custom Python tools, NOT directly by the agent
from phoenix.client import Client
from phoenix.client.types.spans import SpanQuery
from datetime import datetime, timedelta, timezone

def fetch_recent_failures(project: str, minutes_back: int = 60, limit: int = 200):
    """Returns a DataFrame of TOOL spans with ERROR status in the last `minutes_back` minutes."""
    client = Client()                          # reads PHOENIX_API_KEY, PHOENIX_COLLECTOR_ENDPOINT
    since = (datetime.now(timezone.utc) - timedelta(minutes=minutes_back)).isoformat()
    query = SpanQuery().where(
        f"status_code == 'ERROR' and span_kind == 'TOOL' and start_time > '{since}'"
    )
    return client.spans.get_spans_dataframe(
        project_identifier=project,
        query=query,
        limit=limit,
    )
```

### 9.4 Pattern D — Create a Phoenix dataset from a list of failing spans

```python
# chaoslab/dataset.py
from phoenix.client import Client

def build_dataset_from_failures(failures_df, dataset_name: str):
    """Take rows from fetch_recent_failures() and upload as a Phoenix dataset."""
    client = Client()
    inputs  = [{"tool_name": r["attributes.tool.name"],
                "tool_args": r["attributes.tool.parameters"],
                "input":     r["attributes.input.value"]} for _, r in failures_df.iterrows()]
    outputs = [{"observed_output": r["attributes.output.value"],
                "status":          r["status_code"]} for _, r in failures_df.iterrows()]
    dataset = client.datasets.create_dataset(
        name=dataset_name,
        inputs=inputs,
        outputs=outputs,
    )
    return dataset
```

Alternative — via MCP from the agent's own context:
```json
{
  "tool": "add-dataset-examples",
  "arguments": {
    "dataset_name": "chaoslab-failures-2026-06-04",
    "examples": [
      {
        "input":  { "tool_name": "stripe_charge", "tool_args": "{\"customer_id\":\"cus_xxx\",\"amount_cents\":500}" },
        "output": { "observed_output": "404 customer not found", "status": "ERROR" },
        "metadata": { "trace_id": "abc...", "cluster_id": "stripe_404_pattern" }
      }
    ]
  }
}
```

### 9.5 Pattern E — Run an LLM-as-judge experiment with a custom rubric

```python
# chaoslab/custom_tools.py — exposed as ADK FunctionTool to the agent
from phoenix.client import AsyncClient
from phoenix.evals import LLM, ClassificationEvaluator

CHAOSLAB_TOOL_SUCCESS_TEMPLATE = """
You are an evaluator judging whether a tool call inside an autonomous agent functionally succeeded.

A tool call "succeeded" only if ALL of these are true:
1. The status code is OK (no exception thrown).
2. The output payload is non-empty and well-formed.
3. The output answers the apparent intent of the tool's inputs.
4. There are no error strings ("could not", "unable to", "rate limit", "404", "500") in the output.

Respond with EXACTLY ONE WORD: `success` or `failure`.

[Tool Name]: {tool_name}
[Tool Inputs]: {tool_args}
[Tool Output]: {observed_output}
[Status Code]: {status}
"""

async def run_judge_experiment(dataset_name: str, experiment_name: str) -> dict:
    """Run a ChaosLab tool-success judge over a Phoenix dataset.

    Returns experiment_id and aggregate stats. The agent uses this to grade
    a cluster of failures with one LLM-as-judge pass.
    """
    client = AsyncClient()
    dataset = await client.datasets.get_dataset(name=dataset_name)
    llm = LLM(provider="google_genai", model="gemini-2.5-flash")
    judge = ClassificationEvaluator(
        name="chaoslab_tool_success",
        llm=llm,
        prompt_template=CHAOSLAB_TOOL_SUCCESS_TEMPLATE,
        choices={"success": 1.0, "failure": 0.0},
    )

    # Task: pass through the example as-is — we're judging an already-observed result,
    # not generating new outputs.
    async def task(example):
        return example.output  # whatever was observed

    experiment = await client.experiments.run_experiment(
        dataset=dataset,
        task=task,
        evaluators=[judge],
        experiment_name=experiment_name,
        experiment_metadata={"agent": "chaoslab", "rubric_version": "v1"},
        concurrency=10,
        timeout=30,
        retries=2,
        rate_limit_errors=[Exception],     # crude but works as a backstop
    )
    return {"experiment_id": experiment.id}
```

### 9.6 Pattern F — Read experiment results back + write span annotations

```python
# chaoslab/custom_tools.py — continued
from phoenix.client import AsyncClient
from phoenix.client.resources.spans import SpanAnnotationData

async def write_span_annotation(span_id: str, label: str, score: float, explanation: str) -> dict:
    """Attach a ChaosLab failure-cluster annotation to a span. Used after the judge experiment."""
    client = AsyncClient()
    annotation = SpanAnnotationData(
        name="chaoslab_cluster",
        span_id=span_id,
        annotator_kind="LLM",
        result={"label": label, "score": score, "explanation": explanation},
        metadata={"chaoslab_version": "v1"},
    )
    await client.spans.log_span_annotations(span_annotations=[annotation])
    return {"status": "ok", "span_id": span_id, "label": label}


async def fetch_experiment_results(experiment_id: str):
    """Get the full per-row results of a finished experiment."""
    client = AsyncClient()
    exp = await client.experiments.get_experiment(experiment_id=experiment_id)
    df = exp.as_dataframe()   # [UNVERIFIED — exact attribute name not in primary API ref; verify in RAT]
    return df
```

These six patterns (A–F) cover ChaosLab's full loop:
- A instruments the target.
- B wires ChaosLab to Phoenix MCP + custom tools.
- C, D find and persist failure clusters.
- E grades them.
- F reads results + writes scores back to the original spans.

---

## 10. Open questions remaining for the RAT

Things this research could NOT pin down from docs alone. Verify these during the 90-min RAT (`RAT-runbook.md`):

1. **Does `experiment.as_dataframe()` exist on the experiment object?** The primary API ref doesn't list its attributes/methods explicitly. Need to run a tiny experiment and `dir(exp)` to confirm. (Step 3 of the RAT will hit this.)
2. **What's the actual default `concurrency` on `Client().experiments.run_experiment` (sync version)?** Docs are silent. If sync defaults to 1, ChaosLab's 30-span cluster would take 30 × N seconds serial — measure with `time` during RAT.
3. **Does `client.spans.log_span_annotations` work against Phoenix Cloud's free tier without extra config?** The annotation config it references must exist first — does it auto-create on first call, or does the user have to create the annotation config in the UI? Test by calling `log_span_annotations` with a NEW annotation name and see if it appears in the UI.
4. **What's the exact size of `MAX_SPAN_QUERY_LIMIT` and `DEFAULT_PAGE_SIZE` in `phoenix-mcp/src/constants.ts`?** Couldn't pull `constants.ts` cleanly. Affects pagination strategy for the failure-clustering loop.
5. **Cold start: does the `npx @arizeai/phoenix-mcp` subprocess survive Cloud Run instance restarts gracefully?** `MCPToolset` with `StdioServerParameters` spawns the npx process per agent instance. On a scale-to-zero Cloud Run with cold starts, will the toolset reconnect cleanly, or does it leak state? Smoke-test by deploying to Cloud Run and triggering 5 cold starts in a row.
6. **`PHOENIX_COLLECTOR_ENDPOINT` format with `/s/<space-name>`** — does the MCP `--baseUrl` flag take the space-scoped URL or the root URL? Conflicting hints in docs. Try both during RAT step 2.

These six items are the difference between "ChaosLab is a 9-day build" and "ChaosLab is a 14-day build." Burn the 90 minutes; get binary answers.

---

## Appendix: source manifest

Cited and read for this file (in order of load-bearing-ness):

- `Arize-ai/phoenix` repo, paths:
  - `js/packages/phoenix-mcp/README.md` (tool list — primary source)
  - `js/packages/phoenix-mcp/src/index.ts` (all tool registrations)
  - `js/packages/phoenix-mcp/src/traceTools.ts` (exact trace tool signatures)
  - `js/packages/phoenix-mcp/src/spanTools.ts` (exact span tool signatures)
  - `js/packages/phoenix-mcp/src/datasetTools.ts` (exact dataset tool signatures)
  - `js/packages/phoenix-mcp/src/experimentTools.ts` (exact experiment tool signatures — confirmed NO run/create)
  - `js/packages/phoenix-mcp/src/annotationConfigTools.ts` (confirmed READ-ONLY)
  - `js/packages/phoenix-mcp/src/promptTools.ts` (10 prompt tool signatures)
  - `packages/phoenix-client/docs/source/api/experiments.md` (run_experiment full signature)
  - `packages/phoenix-client/docs/source/api/spans.md` (log_span_annotations)
  - `docs/phoenix/integrations/python/google-adk/google-adk-tracing` (Agent Engine caveat)
  - `docs/phoenix/datasets-and-experiments/how-to-experiments/run-experiments.mdx` (dry_run, signature)
  - `scripts/benchmarks/hallucination_eval_benchmark.ipynb` (concurrency=10 verified)
  - `tutorials/llm_application_tracing_evaluating_and_analysis.ipynb` (hallucination prompt verbatim)
  - `tutorials/evals/evaluate_agent_tool_selection_classifications.ipynb` (tool selection prompt verbatim)
- `Arize-ai/openinference` repo:
  - `python/instrumentation/openinference-instrumentation-google-adk/README.md` (minimal ADK instrumentation snippet)
  - `spec/llm_spans.md` (span attribute schema)
- `arize.com/docs/phoenix/integrations/phoenix-mcp-server` (MCP overview, install)
- `arize.com/docs/phoenix/sdk-api-reference/typescript/mcp-server` (MCP tool list categorical)
- `arize.com/docs/phoenix/environments` (Cloud limits, 10 GB user-managed)
- `arize.com/pricing/` (AX Free: 1 GB / 15 days / 25k spans; AX Pro $50/mo: 10 GB / 30 days / 50k spans)
- `adk.dev/integrations/phoenix/` (high-level ADK Phoenix integration)
- Context7 corpus IDs queried: `/arize-ai/phoenix` (6442 snippets), `/arize-ai/openinference` (801 snippets), `/websites/arize_phoenix`.

[UNVERIFIED] markers throughout = items the RAT will resolve.
