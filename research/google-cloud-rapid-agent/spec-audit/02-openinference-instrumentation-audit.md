# Spec Audit 02 — OpenInference Instrumentation Claims (Tier-1 ADK + Tier-2 LangChain/CrewAI/OpenAI-SDK/Vercel)

**Audited:** 2026-06-03
**Auditor:** spec-audit subagent
**Verdict:** **MOSTLY CONFIRMED — every package exists, every API call shape works as the spec assumes, and 3.12 is supported everywhere. Two real issues need amendment: (a) one fabricated span attribute name in story-3.3 BDD (`openinference.instrumentation.library == "langchain"`), and (b) `@arizeai/openinference-vercel` is a SpanProcessor not an `.instrument()` instrumentor — semantically different even though both are referenced uniformly in the spec.**

---

## Summary

| Claims audited | Count |
|---|---|
| CONFIRMED | 7 |
| NEEDS-FIX | 2 |
| WRONG (load-bearing) | 1 |

The most important amendment: **story-3.3 BDD claim that `openinference.instrumentation.library == "langchain"` is a captured span attribute is fabricated. No such attribute exists in `openinference-semantic-conventions`.** The closest real thing is OTEL's `InstrumentationScope.name`, which equals `"openinference.instrumentation.langchain"` (the Python module path of the tracer). The BDD assertion as written will never pass.

---

## Package versions — quick reference (all verified via `https://pypi.org/pypi/<pkg>/json` and npm registry on 2026-06-03)

| Package | Latest version | Last release | Python | Framework dep |
|---|---|---|---|---|
| `openinference-instrumentation-google-adk` | **0.1.15** | 2026-05-22 | <3.15, >=3.10 | `google-adk >= 1.2.1` |
| `openinference-instrumentation-langchain` | **0.1.66** | 2026-05-18 | <3.15, >=3.10 | `langchain-core >= 0.3.9` |
| `openinference-instrumentation-crewai` | **1.1.9** | 2026-06-02 | <3.14, >=3.10 | `crewai >= 1.10.1` |
| `openinference-instrumentation-openai-agents` | **1.5.1** | 2026-05-18 | <3.15, >=3.10 | `openai-agents >= 0.2.6` |
| `openinference-instrumentation` (base) | **0.1.53** | 2026-06-02 | <3.15, >=3.10 | — |
| `@arizeai/openinference-vercel` (npm) | **2.7.7** | 2026-05-29 | n/a (TS) | Vercel AI SDK v6 (best-effort v3.3+) |

All five Python packages support Python 3.12 (`architecture.md` stack). CrewAI excludes 3.14; not a concern for our 3.12 target. All packages have been released within the last 30 days — actively maintained.

---

## Claim-by-claim findings

### 1. `openinference-instrumentation-google-adk` exists on PyPI; auto-instruments ADK at the `Runner.run_async` / `BaseAgent.run_async` level

## Claim: ChaosLab's `target-agent` and `chaoslab-agent` rely on `openinference-instrumentation-google-adk` to auto-emit OpenInference spans for ADK agents.
**Source in spec:** `architecture.md` § "Required external libraries" line 165; `story-2.3-target-phoenix-instrumentation.md` BDD lines 49, 53, 184-188; `pyproject.toml` entry `openinference-instrumentation-google-adk>=0.1.15,<1.0.0`.
**Verdict:** ✅ CONFIRMED
**Evidence:**
- PyPI: https://pypi.org/pypi/openinference-instrumentation-google-adk/json → `version=0.1.15`, `requires_python=<3.15,>=3.10`, framework dep `google-adk >= 1.2.1`.
- Source (canonical layout under `python/instrumentation/openinference-instrumentation-google-adk/`): https://github.com/Arize-ai/openinference/tree/main/python/instrumentation/openinference-instrumentation-google-adk
- Module entrypoint exports `GoogleADKInstrumentor` via `openinference.instrumentation.google_adk` — `class GoogleADKInstrumentor(BaseInstrumentor)` with `_instrument(**kwargs)` reading `tracer_provider=` from kwargs (see `__init__.py`).
- The instrumentor wraps `Runner.run_async`, `BaseAgent.run_async`, `base_llm_flow.trace_call_llm`, and `trace_tool_call`. NOT `Agent.run()` (which is a synchronous-style helper, not the canonical ADK entrypoint). The spec uses `Agent.run()` in a hand-wave in the audit prompt; the real surface is `Runner.run_async` + `BaseAgent.run_async`.
- The instrumentor also calls `_disable_existing_tracers()` to prevent double-instrumentation from ADK's built-in OTEL — important for ADR-005 compatibility.
- Release 0.1.15 was uploaded 2026-05-22 (~13 days before audit) → actively maintained.

**Note for coding agent:** the spec's mention of "Agent.run() level" is loose. The real instrumented methods are `Runner.run_async` and `BaseAgent.run_async`. Tests that assert "tool" + "agent" span kinds emitted via `InMemoryRunner.run_async()` (which is how `target-agent` is invoked) will work fine — that's exactly the path the instrumentor wraps.

---

### 2. `openinference-instrumentation-langchain` exists; covers LangChain Agent + LangGraph

## Claim: A single instrumentor covers LangChain agent + LangGraph (or LangGraph requires a separate package).
**Source in spec:** `architecture.md` line 166; `story-3.3-langchain-adapter.md` lines 16, 27, 51-54, 284-285.
**Verdict:** ✅ CONFIRMED — single instrumentor; **no separate LangGraph package exists**.
**Evidence:**
- PyPI: https://pypi.org/pypi/openinference-instrumentation-langchain/json → `version=0.1.66`, `requires_python=<3.15,>=3.10`, framework dep `langchain-core >= 0.3.9`.
- README (verbatim, from `main` branch): "This instrumentation works with: **LangChain 1.x** (`langchain>=1.0.0`): Modern agent framework built on LangGraph; **LangChain Classic** (`langchain-classic>=1.0.0`): Legacy chains and tools." Quote: "The instrumentation hooks into `langchain-core`, which is the shared foundation used by all LangChain packages."
- Directory listing of `Arize-ai/openinference/python/instrumentation/` (verified via GitHub API) shows **no `openinference-instrumentation-langgraph` package**. LangGraph is covered by the same hook because LangChain 1.x is built on LangGraph.
- The hook is via `BaseCallbackManager.__init__` wrapping — works for any code path that constructs a CallbackManager, which includes both `LCEL` runnables and LangGraph state machines.

---

### 3. `openinference-instrumentation-crewai` exists

## Claim: CrewAI instrumentor exists, emits CHAIN + child TOOL spans for `Crew.kickoff()`.
**Source in spec:** `architecture.md` line 167; `story-3.4-crewai-adapter.md` lines 16, 26, 47-48, 290-291.
**Verdict:** ✅ CONFIRMED
**Evidence:**
- PyPI: https://pypi.org/pypi/openinference-instrumentation-crewai/json → `version=1.1.9`, `requires_python=<3.14,>=3.10`, framework dep `crewai >= 1.10.1`.
- Source: `__init__.py` declares `class CrewAIInstrumentor(BaseInstrumentor)` with `_instrument(**kwargs)` reading `tracer_provider=` from kwargs.
- `_wrappers.py` wraps `Crew.kickoff`, `Agent._execute_without_timeout`, `BaseTool.run`, `Flow.kickoff*`, plus short/long-term memory save/search. Span attributes use `OpenInferenceSpanKindValues.CHAIN`, `AGENT`, and `TOOL` per the OpenInference semconv — matches story-3.4 BDD exactly.
- Latest release uploaded 2026-06-02 (1 day before audit) → actively maintained. **This was released within 24h of the audit** — possible the spec's hard-pin `>=1.10.1` on crewai is actually compatible with the current `crewai 1.14.6`, which it is (semver-compat).
- Caveat: CrewAI's major-version cadence is faster than other Arize-ai instrumentors (1.1.x range). Pin the instrumentor to `>=1.1.9,<2.0.0` rather than the spec's implicit "whatever's current" — version bumps may include breaking changes per their 1.0 → 1.1 history.

---

### 4. `openinference-instrumentation-openai-agents` exists for OpenAI Agents SDK — distinct from `openinference-instrumentation-openai`

## Claim: Two separate packages exist: one for the OpenAI Agents SDK (`openinference-instrumentation-openai-agents`), and one for the base OpenAI client (`openinference-instrumentation-openai`). Spec uses the former.
**Source in spec:** `story-3.5-openai-sdk-adapter.md` lines 15, 26, 269, 273; `architecture.md` (implicit via "OpenAI Agents SDK" naming).
**Verdict:** ✅ CONFIRMED — two distinct packages, story-3.5 references the right one.
**Evidence:**
- `openinference-instrumentation-openai-agents` (the SDK one): https://pypi.org/pypi/openinference-instrumentation-openai-agents/json → `version=1.5.1`, framework dep `openai-agents >= 0.2.6` (the `openai-agents` SDK package, NOT the `openai` client).
- `openinference-instrumentation-openai` (the base client one): https://pypi.org/pypi/openinference-instrumentation-openai/json → `version=0.1.50`, instruments `openai>=1.0.0`.
- Source for openai-agents instrumentor: `class OpenAIAgentsInstrumentor(BaseInstrumentor)` calls `agents.set_trace_processors([OpenInferenceTracingProcessor(...)])` (exclusive mode, default) or `agents.add_trace_processor(...)` — it integrates with the SDK's native trace processor surface rather than monkey-patching. This is the SDK's "official extension point" per OpenAI's own docs.
- `_processor.py` maps the SDK's span types to OpenInference `AGENT`, `TOOL`, `LLM`, `CHAIN`, and `GUARDRAIL` kinds. Story-3.5's BDD claim of ≥3 spans with kinds `AGENT` + `TOOL` + `LLM` is grounded in real implementation.

**Note:** The spec correctly chose the SDK package. The base-client one (`openinference-instrumentation-openai`) would be wrong for the Agents SDK case — it instruments raw `openai.ChatCompletion.create` calls and would miss the SDK's `Agent.run` / `Runner.run_sync` topology.

---

### 5. `@arizeai/openinference-vercel` exists on npm

## Claim: An npm package exists to instrument Vercel AI SDK for OpenInference / Phoenix ingestion.
**Source in spec:** `best-practices/04` (referenced as a Vercel adapter); not directly cited in the per-story specs but listed as a Tier-2 future adapter in audit prompt.
**Verdict:** 🟡 NEEDS-FIX — package exists, but it is a **SpanProcessor**, not a `BaseInstrumentor.instrument()`-style hook. The spec's mental model treats all instrumentors uniformly with `.instrument(tracer_provider=...)` — that pattern does NOT apply here.
**Evidence:**
- npm registry: https://registry.npmjs.org/@arizeai/openinference-vercel → `version=2.7.7`, last published 2026-05-29.
- README (verbatim): "This package provides utilities to ingest Vercel AI SDK spans into platforms like Arize and Phoenix." Compat table: AI SDK **v6.x = Targeted**, v5.x = best-effort, >=3.3 and <5 = best-effort.
- The package exports `OpenInferenceSimpleSpanProcessor` and `OpenInferenceBatchSpanProcessor`. Usage pattern is `registerOTel({ ..., spanProcessors: [ new OpenInferenceSimpleSpanProcessor({ exporter, spanFilter: isOpenInferenceSpan }) ] })`. This is fundamentally different from the Python `.instrument(tracer_provider=...)` shape — the Python instrumentors PATCH the framework; the JS one TRANSLATES Vercel's `gen_ai.*` + `ai.*` attributes into OpenInference shape AT EXPORT TIME.
- Dependencies: `@arizeai/openinference-core@2.2.0`, `@arizeai/openinference-genai@0.1.10`, `@arizeai/openinference-semantic-conventions@2.5.0`, peer `@opentelemetry/api`.

**Recommended amendment:** If ChaosLab adds a Tier-2 Vercel adapter (the spec only hints at this; no story file yet), do NOT model it after the Python instrumentor pattern. The adapter would either (a) call the Vercel target via HTTP and rely on the TARGET process having installed `OpenInferenceSimpleSpanProcessor` in its `instrumentation.ts`, or (b) be omitted from the Python-side adapter layer entirely and documented as "Vercel target observability is the target's responsibility — ChaosLab will receive the spans Phoenix-side regardless of who emits them." Recommend (b) for the 9-day window: dropping the Tier-2 Vercel adapter from MVP scope keeps story count manageable.

---

### 6. Each instrumentor's `.instrument(tracer_provider=...)` API works as documented

## Claim: All four Python instrumentors expose `.instrument(tracer_provider=tracer_provider)` and the call shape in our spec matches.
**Source in spec:** `story-2.3` line 53 (`GoogleADKInstrumentor().instrument(tracer_provider=tracer_provider)`); `story-3.3` line 285 (`LangChainInstrumentor().instrument()`); `story-3.4` line 291 (`CrewAIInstrumentor().instrument(tracer_provider=tracer_provider)`); `story-3.5` line 26 (`OpenAIAgentsInstrumentor().instrument()`).
**Verdict:** ✅ CONFIRMED — all four match the canonical README + source shape.
**Evidence:** (verified verbatim from each package's `__init__.py` on the `main` branch)
- `GoogleADKInstrumentor()._instrument(**kwargs)`: reads `tracer_provider = kwargs.get("tracer_provider") or trace_api.get_tracer_provider()`. Accepts both forms.
- `LangChainInstrumentor()._instrument(**kwargs)`: same kwargs pattern. README example uses bare `LangChainInstrumentor().instrument()` (no tracer_provider) which works because the global tracer provider has already been set via `trace_api.set_tracer_provider(tracer_provider)`.
- `CrewAIInstrumentor()._instrument(**kwargs)`: same. README uses `CrewAIInstrumentor().instrument(tracer_provider=trace_provider)`.
- `OpenAIAgentsInstrumentor()._instrument(**kwargs)`: same, plus an `exclusive_processor: bool = True` kwarg controlling whether `agents.set_trace_processors` (replaces) or `agents.add_trace_processor` (additive) is called. The spec doesn't reference this kwarg; default behavior is exclusive which is correct for our case (no upstream processors to preserve).

All four accept the `BaseInstrumentor` standard kwargs (`config=TraceConfig(...)`, `tracer_provider=...`). No surprises. Note: `OpenAIAgentsInstrumentor._uninstrument` is a TODO stub — calling it does nothing. Not load-bearing for the demo but worth noting if the test suite relies on instrument/uninstrument cycles.

---

### 7. Base package `openinference-instrumentation` provides `using_session`, `using_user`, `using_metadata`, `using_tags`, `using_attributes`

## Claim: The base utility package (no framework suffix) exposes these context managers for trace-attribute enrichment.
**Source in spec:** referenced in `context/06-open-standards.md` (the prompt's claim 7).
**Verdict:** ✅ CONFIRMED
**Evidence:** `python/openinference-instrumentation/src/openinference/instrumentation/__init__.py` `__all__` includes all of them: `using_attributes`, `using_metadata`, `using_prompt_template`, `using_session`, `using_tags`, `using_user`. They live under `context_attributes.py`. Plus bonus utilities: `dangerously_using_project`, `suppress_tracing`, `TraceConfig`, `OITracer`, `capture_span_context`, `get_attributes_from_context`.
- PyPI: https://pypi.org/pypi/openinference-instrumentation/json → `version=0.1.53`, released 2026-06-02 (1 day before audit).
- Usage pattern (verified in `openinference-instrumentation-google-adk/_wrappers.py`): `from openinference.instrumentation import using_session, using_user, get_attributes_from_context, safe_json_dumps` — the framework instrumentors themselves consume these helpers.

These are usable inside both Phoenix tool wrappers (`chaoslab_agent.phoenix_tools/`) and the structlog `_add_phoenix_trace_id` processor that `coding-standards.md` references. The base package will be a transitive dep of all four framework instrumentors (each pins `openinference-instrumentation>=0.1.51`) but should ALSO be explicitly listed in `apps/chaoslab-agent/pyproject.toml` since `observability.py` will import from it directly (`coding-standards.md` mentions this).

---

### 8. OpenInference span attribute conventions match what BDD criteria reference

## Claim: `openinference.span.kind`, `input.value`, `output.value`, `tool_call.name`, `retrieval.documents` are the real attribute name strings emitted by OpenInference instrumentors.
**Source in spec:** `story-2.3` BDD line 59 (`openinference.span.kind` == "TOOL"); `story-3.5` BDD line 48 (`openinference.span.kind` == "AGENT"|"TOOL"|"LLM"); spec-wide use of input/output/tool_call attribute names in ADR-005 and rubric design.
**Verdict:** 🟡 NEEDS-FIX — most names confirmed, one is wrong.
**Evidence:** (from `python/openinference-semantic-conventions/src/openinference/semconv/trace/__init__.py`)
- `OPENINFERENCE_SPAN_KIND = "openinference.span.kind"` ✅
- `INPUT_VALUE = "input.value"` ✅
- `OUTPUT_VALUE = "output.value"` ✅
- `RETRIEVAL_DOCUMENTS = "retrieval.documents"` ✅
- `TOOL_NAME = "tool.name"` ✅ (this is the tool DEFINITION attribute on a TOOL-kind span)
- `tool_call.name` ❌ — **does not exist**. The canonical attribute for the name of a function being CALLED is `TOOL_CALL_FUNCTION_NAME = "tool_call.function.name"`. Related: `TOOL_CALL_ID = "tool_call.id"`, `TOOL_CALL_FUNCTION_ARGUMENTS_JSON = "tool_call.function.arguments"`. The audit prompt assumed `tool_call.name`; that name appears nowhere in the semconv package.

**Recommended amendment:** Wherever rubric design / BDD criteria refer to `tool_call.name`, swap to `tool_call.function.name`. Concrete locations to grep on implementation:
- `apps/chaoslab-agent/src/chaoslab_agent/judge/rubrics/` (when the Judge sub-agent inspects tool-call attributes)
- `apps/chaoslab-agent/src/chaoslab_agent/injector/faults/malformed_tool_output.py` (when it asserts which tool call to corrupt)
- Any future story BDD that pattern-matches on `tool_call.name`

This is a small fix but failing to apply it means assertion mismatches at runtime — the attribute will silently be missing rather than mismatched, which is worse for debugging.

---

### 9. Story-3.3 BDD claim that captured spans carry `openinference.instrumentation.library == "langchain"`

## Claim: After `LangChainInstrumentor().instrument()` is active, an integration test can assert `span.attributes["openinference.instrumentation.library"] == "langchain"` on a captured span.
**Source in spec:** `story-3.3-langchain-adapter.md` lines 16, 53-54 (`Then at least one captured span has attribute openinference.instrumentation.library == "langchain"`).
**Verdict:** 🔴 WRONG (load-bearing — BDD assertion will never pass)
**Evidence:**
- `openinference.instrumentation.library` is NOT a defined attribute in `openinference-semantic-conventions` (verified by grepping the full `trace/__init__.py` — 557 lines, no occurrence of `instrumentation.library` as an attribute name string).
- What IS captured: the OTEL `InstrumentationScope` of the tracer. When `LangChainInstrumentor` calls `OITracer(trace_api.get_tracer(__name__, __version__, tracer_provider), ...)`, the tracer's scope name becomes `__name__` = `openinference.instrumentation.langchain` (the Python MODULE name). This is exposed on the resulting span as `span.instrumentation_scope.name == "openinference.instrumentation.langchain"` (NOT as an attribute — as a separate field of the span record).
- The author of story-3.3 likely confused the instrumentation-scope NAME for an attribute, or invented the attribute name from intuition.

**Recommended amendment:** Rewrite the story-3.3 BDD criterion as follows:
```
Given a connected LangChainAdapter and a Phoenix tracer wired (LangChainInstrumentor active)
When adapter.invoke runs against the live LangServe fixture
Then at least one captured span has instrumentation_scope.name == "openinference.instrumentation.langchain"
And the assertion is verified via the in-memory span exporter installed by the integration test fixture
```
Alternatively, assert on `span.attributes["openinference.span.kind"]` (one of the actual OI attribute names) being any of `"LLM" | "TOOL" | "CHAIN"` — this is a behavioral assertion that the LangChain instrumentor fired AT ALL, which is what the BDD's intent really is.

Note: the in-memory exporter pattern is `from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter`. The `ReadableSpan` returned exposes both `.attributes` and `.instrumentation_scope`. Test code must read the right field.

---

## Cross-cutting findings

- **All five Python packages support Python 3.12** (required by `architecture.md` line 8). Three of five also support 3.13; CrewAI hard-caps at <3.14 (the spec is 3.12-locked so this doesn't bite).
- **All five packages have been released within the past 30 days** (range: 2026-05-18 to 2026-06-02). No risk of using a stale, abandoned package.
- **No CHANGELOG.md files** are maintained per-instrumentor in the Arize-ai/openinference monorepo (verified by checking the directory listing); they batch release notes into the top-level repo Releases. For breaking-change scouting, watch the per-version `requires_dist` deltas (e.g., the `langchain-core>=0.3.9` floor moved in 2026-Q1; older spec snippets using `langchain-core<0.3` will not work).
- **All four framework instrumentors pin `openinference-instrumentation>=0.1.51`**, so the base package will be picked up transitively. Spec-wise, listing it explicitly in `pyproject.toml` is harmless and documents intent.
- **OpenInferenceSpanKindValues enum** (verified in semconv `__init__.py`) includes: `AGENT`, `CHAIN`, `EMBEDDING`, `EVALUATOR`, `GUARDRAIL`, `LLM`, `RERANKER`, `RETRIEVER`, `TOOL`, `UNKNOWN`. Story BDDs use a subset of these (`AGENT`, `CHAIN`, `TOOL`, `LLM`). All real.
- **`OITracer` (the wrapper installed by every instrumentor) handles `using_session` / `using_user` / `using_metadata` / `using_tags` context-managed attributes via `get_attributes_from_context` in `OITracer.start_as_current_span()`.** This means a single `with using_session(...)`: block in the orchestrator will tag every downstream span emitted by ANY instrumentor — Tier-1 ADK, Tier-2 LangChain, Tier-2 CrewAI, Tier-2 OpenAI Agents. This is exactly the cross-cutting attribute propagation the spec assumes.

---

## Bottom-line amendments required before coding starts

1. **`docs/stories/story-3.3-langchain-adapter.md` lines 51-54:** rewrite the `openinference.instrumentation.library == "langchain"` assertion as either `instrumentation_scope.name == "openinference.instrumentation.langchain"` OR `attributes["openinference.span.kind"] in {"LLM", "TOOL", "CHAIN"}`. Update the matching shell verification step if any greps the BDD text.
2. **Spec-wide attribute name swap:** every reference to `tool_call.name` becomes `tool_call.function.name`. (Likely zero hits today but flag this for rubric authoring.)
3. **`@arizeai/openinference-vercel` is not a `.instrument()`-shaped library.** If a Vercel adapter story is later written, model it as "target installs `OpenInferenceSimpleSpanProcessor` in its own `instrumentation.ts`" — not as a Python-side `.instrument(tracer_provider=...)` call. Recommend deferring this entire story; the MVP-3 frameworks (ADK + LangChain + CrewAI + OpenAI Agents) already cover Tier-2 demonstrably.
4. **`architecture.md` "Required external libraries" table:** add `openinference-instrumentation-openai-agents>=1.5.1,<2.0.0` (currently missing — only LangChain and CrewAI Tier-2 instrumentors are listed, but story-3.5 needs the OpenAI Agents one too). Add `openinference-instrumentation>=0.1.53` for `using_session` / `using_user` direct use in `observability.py` + Phoenix tool wrappers.
5. **Minor (not blocking):** the audit prompt's phrasing "auto-instruments ADK at the `Agent.run()` level" is loose. The real instrumentation points are `Runner.run_async` + `BaseAgent.run_async` + `base_llm_flow.trace_call_llm` + `trace_tool_call`. Test code that invokes the target via `InMemoryRunner` is fine — that's the path the instrumentor wraps. No spec change needed; just a comment in `observability.py`.
