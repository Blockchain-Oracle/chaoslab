# OpenInference Google Ecosystem Instrumentor Matrix

**Audience:** ChaosLab implementers (Arize track, Google Cloud Rapid Agent hackathon)
**Status:** Verified against PyPI + Arize-ai/openinference source as of 2026-06-03
**Scope:** The three OpenInference instrumentors that target Google's agent/LLM stack, plus the cross-framework instrumentors that matter for ChaosLab's target agents.

> **Why this doc exists.** ChaosLab is on the Arize track, so OpenInference traces are the substrate we attack and read. Our `chaoslab-agent` runtime is Google ADK (instrumentor #1 below), but `target-agent` can be any of the three Google SDK shapes or a cross-framework runtime. This file is the decision tree + verified API surface for each.

> **Audit linkage.** This doc directly answers `docs/audit-notes.md` findings A6 (use `openinference.span.kind`, not the fabricated `openinference.instrumentation.library`) and A7 (use `tool_call.function.name`, not `tool_call.name`). Every attribute name below has been verified against `openinference/semconv/trace/__init__.py` in the canonical repo.

---

## 1. The three packages at a glance

| # | Package (PyPI) | Latest ver | Patches | Span kinds assigned |
|---|---|---|---|---|
| 1 | `openinference-instrumentation-google-adk` | **0.1.15** (2026-05-22) | `google.adk.Runner`, `google.adk.agents.BaseAgent`, `google.adk.models.BaseLlm`, `google.adk.tools.BaseTool` | `CHAIN` (Runner), `AGENT` (BaseAgent), `LLM`, `TOOL` |
| 2 | `openinference-instrumentation-vertexai` | **0.1.16** (2026-05-18) | `google.cloud.aiplatform_v1.PredictionService` + `_v1beta1` (`GenerateContentRequest` / `GenerateContentResponse`) | `LLM` only |
| 3 | `openinference-instrumentation-google-genai` | **1.0.2** (2026-05-18) | `google.genai.models.generate_content`, `generate_content_stream`, `embed_content`, `caches.create`, `live.connect` (interactions) | `LLM` (generate*), `EMBEDDING` (embed_content), `CHAIN` (interactions) |

**Python support:** all three require Python ≥3.10. ADK is the only one tested on 3.14; GenAI lists 3.10–3.14; VertexAI lists 3.10–3.13.

**Minimum host SDK versions (from each package's `pyproject.toml`):**
- `openinference-instrumentation-google-adk` → `google-adk >= 1.2.1`
- `openinference-instrumentation-vertexai` → `google-cloud-aiplatform >= 1.71.0`
- `openinference-instrumentation-google-genai` → `google-genai >= 0.7.0`

**ChaosLab pin (locked, ADR-012):** `google-adk >= 2.1.0, < 3.0.0`. This is well above the instrumentor's floor, so we're safe.

---

## 2. Decision tree — which instrumentor for a given target agent?

Walk the target agent's imports top-down. First match wins.

```
target agent imports …
├── from google.adk.agents import Agent / SequentialAgent / LoopAgent / ParallelAgent
│       → openinference-instrumentation-google-adk           (Case A)
│
├── from vertexai.generative_models import GenerativeModel   (legacy Vertex)
│   OR from google.cloud import aiplatform                   (Agent Engine deploy SDK)
│       → openinference-instrumentation-vertexai             (Case B)
│
├── from google import genai                                 (new unified SDK)
│   OR from google.genai import Client
│       → openinference-instrumentation-google-genai         (Case C)
│
├── from langchain… / from crewai… / from agents… (OpenAI Agents SDK)
│       → corresponding cross-framework OI instrumentor      (Case D, §6)
│
└── raw HTTPS to https://*-aiplatform.googleapis.com         (Case E)
        → none of the above cover it; instrument the HTTP client
          (httpx / requests / aiohttp) with the matching OI instrumentor,
          OR add a small manual span around the call.
```

### Case A — Google ADK agent (the ChaosLab `chaoslab-agent` runtime)

ADK already emits OTel GenAI semconv spans natively (`invoke_agent`, `execute_tool`, `generate_content {model}`) — see [google/adk-docs/observability/traces.md](https://github.com/google/adk-docs/blob/main/docs/observability/traces.md). The OpenInference instrumentor **adds the `openinference.span.kind` attribute** (AGENT / CHAIN / LLM / TOOL) on top of those spans so Phoenix can render the agent waterfall.

### Case B — `vertexai.generative_models.GenerativeModel` or `google.cloud.aiplatform`

VertexAI instrumentor patches the **lower-level `aiplatform_v1.PredictionService` request classes**, not the user-facing `GenerativeModel` class. This means it captures Gemini calls regardless of which entry point you use, as long as the call goes through the standard prediction service. It does NOT specifically instrument the Agent Engine SDK's `agent_engines.create()` / `query()` calls; those land as raw RPCs and need Case E handling.

### Case C — `google.genai` (unified SDK)

This is the new SDK that supersedes both `vertexai.generative_models` and the standalone `google-generativeai` library. Instruments synchronous + async clients for `generate_content`, streaming, embeddings, caches, and live interactions. **Known gap (as of 1.0.2):** tool definitions on requests are captured but the wrapper module README still lists "tool definition capture" as work-in-progress for one of the sub-wrappers — verify per-span before depending on it.

### Case D — Cross-framework target (LangChain / CrewAI / OpenAI Agents)

ChaosLab attacks any agent; many will use a non-Google framework over a Google LLM. Install the framework instrumentor (§6) AND the relevant Google LLM instrumentor (B or C) — they compose (§4).

### Case E — Raw HTTP

If the target hits `*-aiplatform.googleapis.com` directly with `httpx` / `requests`, install `openinference-instrumentation-httpx` / `…-requests` (these exist as community packages on Arize-ai/openinference). Or add a manual span:

```python
from opentelemetry import trace
from openinference.semconv.trace import OpenInferenceSpanKindValues, SpanAttributes

tracer = trace.get_tracer(__name__)
with tracer.start_as_current_span("vertex.raw") as span:
    span.set_attribute(SpanAttributes.OPENINFERENCE_SPAN_KIND,
                       OpenInferenceSpanKindValues.LLM.value)
    span.set_attribute(SpanAttributes.LLM_SYSTEM, "vertexai")
    span.set_attribute(SpanAttributes.LLM_MODEL_NAME, "gemini-3.5-flash")
    # … call …
```

---

## 3. Per-instrumentor: install, setup, span output

### 3.1 `openinference-instrumentation-google-adk`

**Install:**
```bash
pip install "openinference-instrumentation-google-adk>=0.1.15" "google-adk>=2.1.0,<3.0.0"
```

**Bare setup (OTel only):**
```python
from openinference.instrumentation.google_adk import GoogleADKInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

tracer_provider = TracerProvider()
tracer_provider.add_span_processor(
    SimpleSpanProcessor(OTLPSpanExporter("http://127.0.0.1:6006/v1/traces"))
)
GoogleADKInstrumentor().instrument(tracer_provider=tracer_provider)
```

**Spans produced (verified against `…/google_adk/_wrappers.py`):**

| Wrapper class | Wraps | Span name | `openinference.span.kind` |
|---|---|---|---|
| `_RunnerRunAsync` | `google.adk.Runner.run_async` | `invocation [app_name]` | `CHAIN` |
| `_BaseAgentRunAsync` | `google.adk.agents.BaseAgent.run_async_impl` | `agent_run [name]` | `AGENT` |
| `_TraceCallLlm` | `BaseLlm.generate_content_async` (via callback) | `call_llm [model]` | `LLM` |
| `_TraceToolCall` | `BaseTool.run_async` | tool name | `TOOL` |

**Attributes captured on LLM spans:** `llm.system="google"`, `llm.model_name`, `llm.input_messages.*`, `llm.output_messages.*`, `llm.token_count.prompt`, `…completion`, `…total`, `llm.tools` (list of tool JSON schemas), `input.value`, `output.value`.

**Attributes captured on TOOL spans:** `tool.name`, `tool.description`, `tool.parameters` (JSON schema), `input.value`, `output.value`, and on the parent LLM span when the LLM produced the tool call: `message.tool_calls.0.tool_call.function.name`, `…tool_call.function.arguments` (the JSON args string).

> **Audit A7 reminder:** the canonical attribute is `tool_call.function.name`, NOT `tool_call.name`. The Python constant is `SpanAttributes.TOOL_CALL_FUNCTION_NAME`. Same for `tool_call.function.arguments` (constant: `TOOL_CALL_FUNCTION_ARGUMENTS_JSON`).

**Known gaps:**
- ADK ≥1.2.1 required (we're on 2.1.0+ so fine).
- `gemini-2.0-flash-exp` and `gemini-2.0-flash` are deprecated host models — don't use either even though sample code shows them. ChaosLab uses `gemini-3.5-flash` (JUDGE_LLM) and optionally `gemini-3.1-pro-preview`.

### 3.2 `openinference-instrumentation-vertexai`

**Install:**
```bash
pip install "openinference-instrumentation-vertexai>=0.1.16" "google-cloud-aiplatform>=1.71.0"
```

**Bare setup:**
```python
from openinference.instrumentation.vertexai import VertexAIInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

tracer_provider = TracerProvider()
tracer_provider.add_span_processor(SimpleSpanProcessor(OTLPSpanExporter("http://127.0.0.1:4317")))
VertexAIInstrumentor().instrument(tracer_provider=tracer_provider)
```

**Spans produced (verified against `…/vertexai/_wrapper.py`):**
Patches every class in `google.cloud.aiplatform_v1` and `_v1beta1` that ends with `Request` and is a `proto.Message`. In practice this means `GenerateContentRequest` and friends. All spans get `openinference.span.kind = "LLM"`.

**Attributes:** `llm.system="vertexai"`, `llm.model_name`, `llm.input_messages.*`, `llm.output_messages.*`, `llm.token_count.*`, `input.value`, `output.value`, `llm.invocation_parameters` (JSON of temperature/top_p/etc).

**Known gaps:**
- Agent Engine SDK (`agent_engines.create()`, `.query()`) — NOT covered. Use the GenAI instrumentor when running on Agent Engine if the agent internally uses `google.genai`, otherwise add manual spans.
- No `AGENT`/`TOOL` spans — only LLM. If the target uses `vertexai.generative_models.GenerativeModel` with function calling, you'll see the function calls in the LLM span's `llm.tools` and `message.tool_calls.*` attributes but no separate TOOL span.

### 3.3 `openinference-instrumentation-google-genai`

**Install:**
```bash
pip install "openinference-instrumentation-google-genai>=1.0.2" "google-genai>=0.7.0"
```

**Bare setup:**
```python
from openinference.instrumentation.google_genai import GoogleGenAIInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

tracer_provider = TracerProvider()
tracer_provider.add_span_processor(SimpleSpanProcessor(OTLPSpanExporter("http://127.0.0.1:4317")))
GoogleGenAIInstrumentor().instrument(tracer_provider=tracer_provider)
```

**Spans produced (verified against `…/google_genai/_wrappers.py`):**

| Wrapper | Method | `openinference.span.kind` |
|---|---|---|
| `_Sync/_AsyncGenerateContentWrapper` | `Client.models.generate_content` | `LLM` |
| `_Sync/_AsyncGenerateContentStream` | `Client.models.generate_content_stream` | `LLM` |
| `_Sync/_AsyncEmbedContentWrapper` | `Client.models.embed_content` | `EMBEDDING` |
| `_Sync/_AsyncCreateInteractionWrapper` | live interactions create | `CHAIN` |
| `_Sync/_AsyncGetInteractionWrapper` | live interactions get | `CHAIN` |
| `_Sync/_AsyncCreateCachesWrapper` | `Client.caches.create` | `LLM` (request-shaped) |

**Attributes:** standard LLM set (`llm.system="google_genai"`, `llm.model_name`, messages, tokens, tools) on LLM spans. `embedding.embeddings.*` on EMBEDDING spans.

**Known gaps:**
- Tool-definition capture inside `generate_content_stream` is incomplete as of 1.0.2 — verify per-span before asserting on it in tests.
- No first-class chat session span — multi-turn `chats.send_message` lands as a series of `generate_content` LLM spans, not parented under a CHAIN span. If you need that grouping, wrap manually with `using_session(session_id=…)`.

---

## 4. Compatibility — can you stack multiple instrumentors?

**Yes, with one caveat.** OpenInference instrumentors are independent BaseInstrumentor subclasses with non-overlapping monkey-patch surfaces in practice:
- ADK patches `google.adk.*` only
- VertexAI patches `google.cloud.aiplatform_v1*` request classes
- GenAI patches `google.genai.*`

You can call all three `.instrument(tracer_provider=...)` in any order. The only real overlap risk: an ADK agent that uses `google.genai` under the hood will produce **both** an ADK `call_llm` span (with `openinference.span.kind=LLM`) AND a GenAI `generate_content` child span (also `LLM`). This is the documented dual-span pattern and is what you want for full provenance — the GenAI span becomes a child of the ADK LLM span. ADR-005 (Phoenix tools) accepts this dual-span shape.

**Recommended registration order** (most-specific to least-specific so child spans inherit the right parent context):
```python
GoogleADKInstrumentor().instrument(tracer_provider=tp)        # outermost
GoogleGenAIInstrumentor().instrument(tracer_provider=tp)      # middle
VertexAIInstrumentor().instrument(tracer_provider=tp)         # inner (raw aiplatform RPCs)
```

To `uninstrument()` selectively (useful for test isolation): each instrumentor exposes `.uninstrument()`. Call them in reverse order.

---

## 5. Phoenix integration — `register()` 3-liners

The recommended Phoenix pattern uses `phoenix.otel.register()`, which sets up the tracer provider, applies env vars, and (with `auto_instrument=True`) auto-discovers installed OpenInference packages.

**Common env vars** (set in shell, `.env`, or Cloud Run service env):
```bash
PHOENIX_COLLECTOR_ENDPOINT=https://app.phoenix.arize.com
PHOENIX_API_KEY=<your-key>
PHOENIX_PROJECT_NAME=chaoslab
# When self-hosting:
# PHOENIX_COLLECTOR_ENDPOINT=http://localhost:6006
```

**Universal Phoenix register pattern (works for all three Google instrumentors):**
```python
from phoenix.otel import register

tracer_provider = register(
    project_name="chaoslab",
    auto_instrument=True,            # picks up every installed OI instrumentor
)
```

`auto_instrument=True` will, behind the scenes, import and call `.instrument(tracer_provider=tracer_provider)` on every `openinference-instrumentation-*` package it finds in the active venv. If you want explicit control (e.g. instrumenting only the target-agent for chaos isolation):
```python
from phoenix.otel import register
from openinference.instrumentation.google_adk import GoogleADKInstrumentor

tracer_provider = register(project_name="chaoslab", auto_instrument=False)
GoogleADKInstrumentor().instrument(tracer_provider=tracer_provider)
```

**ADR-007 reminder:** `register(set_global_tracer_provider=False, batch=False)` is only required when running on **Vertex Agent Engine** (the managed Agent Engine deploy target swallows traces otherwise). ChaosLab deploys to Cloud Run, so the defaults are fine.

---

## 6. Canonical attribute set — verified against `openinference.semconv.trace`

These are the attribute names actually emitted (verified against the live semconv module). Use these constants in test assertions per `best-practices/06 §5.1` (trace-as-assertion).

| Attribute name | Python constant | Where it shows up |
|---|---|---|
| `openinference.span.kind` | `SpanAttributes.OPENINFERENCE_SPAN_KIND` | **Required on every span.** Values: `LLM`, `CHAIN`, `AGENT`, `TOOL`, `RETRIEVER`, `RERANKER`, `EMBEDDING`, `GUARDRAIL`, `EVALUATOR`, `PROMPT` |
| `llm.system` | `LLM_SYSTEM` | LLM spans — `"google"` (ADK), `"vertexai"`, `"google_genai"` |
| `llm.model_name` | `LLM_MODEL_NAME` | LLM spans — e.g. `"gemini-3.5-flash"` |
| `llm.invocation_parameters` | `LLM_INVOCATION_PARAMETERS` | JSON of model params |
| `llm.input_messages` | `LLM_INPUT_MESSAGES` | Flattened messages list |
| `llm.output_messages` | `LLM_OUTPUT_MESSAGES` | Flattened response messages |
| `llm.token_count.prompt` | `LLM_TOKEN_COUNT_PROMPT` | Token usage |
| `llm.token_count.completion` | `LLM_TOKEN_COUNT_COMPLETION` | Token usage |
| `llm.token_count.total` | `LLM_TOKEN_COUNT_TOTAL` | Token usage |
| `llm.tools` | `LLM_TOOLS` | List of tool JSON schemas advertised to the LLM |
| `tool.name` | `TOOL_NAME` | TOOL spans |
| `tool.description` | `TOOL_DESCRIPTION` | TOOL spans |
| `tool.parameters` | `TOOL_PARAMETERS` | TOOL spans — JSON schema |
| `tool_call.function.name` | `TOOL_CALL_FUNCTION_NAME` | LLM spans (inside `message.tool_calls.*`) — **NOT** `tool_call.name` |
| `tool_call.function.arguments` | `TOOL_CALL_FUNCTION_ARGUMENTS_JSON` | LLM spans (inside `message.tool_calls.*`) |
| `input.value` / `input.mime_type` | `INPUT_VALUE` / `INPUT_MIME_TYPE` | All spans |
| `output.value` / `output.mime_type` | `OUTPUT_VALUE` / `OUTPUT_MIME_TYPE` | All spans |
| `session.id` | `SESSION_ID` | Context attribute |
| `user.id` | `USER_ID` | Context attribute |
| `agent.name` | `AGENT_NAME` | AGENT spans |
| `metadata` | `METADATA` | JSON metadata blob, all spans |

**Forbidden / fabricated attributes (DO NOT assert on these — audit findings A6/A7):**
- ❌ `openinference.instrumentation.library` — does not exist. Use `instrumentation_scope.name` (set automatically by OTel) or `openinference.span.kind`.
- ❌ `tool_call.name` — wrong. Use `tool_call.function.name`.
- ❌ `instrumentation.library` — pre-OTel-1.0 legacy. Use `instrumentation_scope.name`.

**ADK extra (OTel GenAI semconv) attributes ADK emits natively** (not from OpenInference, but you'll see them on the same spans):
`gen_ai.agent.name`, `gen_ai.system`, `gen_ai.operation.name`, `gen_ai.request.model`, `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`, `gen_ai.response.finish_reasons`. Useful for cross-correlating with Google's own dashboards but not required for OpenInference-style trace assertions.

---

## 7. Cross-framework instrumentors (Case D, §2)

ChaosLab is cross-framework. Target agents may be:

| Framework | Instrumentor | PyPI |
|---|---|---|
| LangChain / LangGraph | `openinference-instrumentation-langchain` | https://pypi.org/project/openinference-instrumentation-langchain/ |
| CrewAI | `openinference-instrumentation-crewai` | https://pypi.org/project/openinference-instrumentation-crewai/ |
| OpenAI Agents SDK | `openinference-instrumentation-openai-agents` | https://pypi.org/project/openinference-instrumentation-openai-agents/ |
| Anthropic (raw) | `openinference-instrumentation-anthropic` | https://pypi.org/project/openinference-instrumentation-anthropic/ |
| LlamaIndex | `openinference-instrumentation-llama-index` | https://pypi.org/project/openinference-instrumentation-llama-index/ |
| AutoGen | `openinference-instrumentation-autogen` | https://pypi.org/project/openinference-instrumentation-autogen/ |
| Haystack | `openinference-instrumentation-haystack` | https://pypi.org/project/openinference-instrumentation-haystack/ |
| DSPy | `openinference-instrumentation-dspy` | https://pypi.org/project/openinference-instrumentation-dspy/ |

All compose with the Google instrumentors per §4: a LangChain target using Gemini gets `LangChainInstrumentor()` + `VertexAIInstrumentor()` (or GenAI). Phoenix `register(auto_instrument=True)` picks all of them up automatically.

**ChaosLab Tier 1/2 split (from `research/.../best-practices`):**
- **Tier 1 (must ship, primary track):** google-adk, langchain, crewai, openai-agents.
- **Tier 2 (nice-to-have):** anthropic, llama-index, autogen, haystack, dspy.

---

## 8. ChaosLab-specific deployment

ChaosLab has three Cloud Run services (locked in ADR-007):

### 8.1 `chaoslab-agent` (the orchestrator)

Runs Google ADK. Installs:
```bash
openinference-instrumentation-google-adk        # primary
arize-phoenix-otel                              # register()
arize-phoenix-client                            # for log_span_annotations / experiments wrappers (ADR-005)
```

Sends traces to a **Phoenix project named `chaoslab-orchestrator`** so we can distinguish orchestrator runs from target traces during chaos experiments.

### 8.2 `target-agent` (the victim agent we attack)

Runs whatever the demo target is (default: a small ADK agent for the canned scenarios). Installs **only the matching instrumentor for the target's framework**. For the default demo:
```bash
openinference-instrumentation-google-adk
arize-phoenix-otel
```

Sends traces to a **Phoenix project named `chaoslab-target`**.

For the cross-framework demo (LangChain target):
```bash
openinference-instrumentation-langchain
openinference-instrumentation-google-genai      # if the LangChain agent uses Gemini via google-genai
arize-phoenix-otel
```

### 8.3 `chaoslab-web` (Next.js)

No Python OI instrumentation. It reads spans from Phoenix via `arize-phoenix-client` (server-side API route) — not an instrumented service in the OI sense.

### 8.4 Why two projects?

Chaos experiments inject faults into the target. We need to assert that:
- the target's trace shows the fault (in `chaoslab-target`)
- the orchestrator's trace shows the planning / replay / fix (in `chaoslab-orchestrator`)

Keeping them in separate Phoenix projects lets us run independent evals + experiment IDs against each.

---

## 9. Quick verification checklist (for any PR touching instrumentation)

1. `uv pip show openinference-instrumentation-google-adk` reports `>= 0.1.15`
2. A test asserts on `span.attributes["openinference.span.kind"]` (NOT `instrumentation.library`)
3. A test asserts on `tool_call.function.name` (NOT `tool_call.name`)
4. No code imports from `google.adk.*` outside `chaoslab_agent.adk_types` (ADR-012 quarantine)
5. `PHOENIX_API_KEY` set in Cloud Run secrets, not committed
6. `JUDGE_LLM=gemini-3.5-flash` env var, not `gemini-2.0-flash` (deprecated) or `gemini-pro` (alias)

---

## 10. Sources (all verified 2026-06-03)

- Arize-ai/openinference repo: https://github.com/Arize-ai/openinference
- `openinference-instrumentation-google-adk` README: https://github.com/Arize-ai/openinference/blob/main/python/instrumentation/openinference-instrumentation-google-adk/README.md
- `openinference-instrumentation-vertexai` README: https://github.com/Arize-ai/openinference/blob/main/python/instrumentation/openinference-instrumentation-vertexai/README.md
- `openinference-instrumentation-google-genai` README: https://github.com/Arize-ai/openinference/blob/main/python/instrumentation/openinference-instrumentation-google-genai/README.md
- Semantic conventions source: `python/openinference-semantic-conventions/src/openinference/semconv/trace/__init__.py`
- Google ADK observability docs: https://github.com/google/adk-docs/blob/main/docs/observability/traces.md
- Google ADK + Arize integration: https://github.com/google/adk-docs/blob/main/docs/integrations/arize-ax.md
- OpenInference spans concept page: https://www.mintlify.com/Arize-ai/openinference/concepts/spans
- OpenInference semantic conventions spec: https://www.mintlify.com/Arize-ai/openinference/spec/semantic-conventions
- PyPI packages: https://pypi.org/project/openinference-instrumentation-{google-adk,vertexai,google-genai}/
- Phoenix `register()` docs: https://arize.com/docs/phoenix/tracing/integrations-tracing/google-genai
