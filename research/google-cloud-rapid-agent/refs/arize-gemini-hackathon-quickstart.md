# Arize Gemini Hackathon Quickstart — Deep Reference

**Upstream:** https://github.com/Arize-ai/gemini-hackathon (`main`, fetched 2026-06-03)
**License:** Apache-2.0
**Stated purpose (README §1):** *"End-to-end template for the Arize @ Google Cloud Partnerships Hackathon track."*
**Why this matters for ChaosLab:** this is THE canonical end-to-end example for our chosen track. Every architectural decision in `docs/architecture.md` should be cross-checked against this repo. If the quickstart does X and our spec does Y, we need a deliberate reason for the delta documented in `docs/audit-notes.md`.

---

## 1. Repo Structure

Verified via `gh api repos/Arize-ai/gemini-hackathon/contents` (recursive). Total surface area is intentionally small — the entire repo is ~17 source files outside the lockfile.

```
gemini-hackathon/
├── .env.example                      # 1396 B — PHOENIX_* + GOOGLE_* + GEMINI_MODEL override
├── .gemini/
│   └── settings.json                 # 342 B — Gemini CLI MCP config (phoenix + phoenix-docs servers)
├── .gitignore                        # 141 B — standard + .arize-tmp-traces/ + .adk/
├── LICENSE                           # Apache-2.0
├── Makefile                          # 512 B — setup / run / run-adk targets
├── README.md                         # 5507 B — quickstart narrative + MCP setup
├── pyproject.toml                    # 652 B — deps, hatch wheel target
├── uv.lock                           # 611 KB — pins entire dep tree
└── agent/
    ├── main.py                       # 1781 B — one-shot CLI runner (asyncio + InMemoryRunner)
    ├── instrumentation.py            # 1565 B — phoenix.otel.register(...) wrapper
    └── shopping_demo/
        ├── __init__.py               # re-exports root_agent
        ├── agent.py                  # 1364 B — ADK Agent definition + tool wiring
        ├── prompt.py                 # 1789 B — system instruction string
        ├── mini_webshop.py           # 9831 B — in-memory gym-style env (the bulk of the code)
        └── tools/
            ├── __init__.py           # empty (license header only)
            ├── search.py             # 1720 B — `search(keywords)` ADK FunctionTool
            └── click.py              # 1719 B — `click(button_name)` ADK FunctionTool
```

**Critical observations on what is NOT present (this is signal, not noise):**

- **No `evals/` directory.** Despite "LLM-as-a-Judge or code evals" being mandatory per the Devpost rules (and per partner-arize.md §"Hackathon-specific gotchas" gotcha #3), the quickstart ships ZERO eval code. README never mentions `arize-phoenix-evals` or judge prompts. **This is the single biggest gap ChaosLab must fill.**
- **No `experiments/`.** No `phoenix.client.AsyncClient()` usage. No `run_experiment()` calls. The quickstart trace-emits but never replays or scores.
- **No tests.** No `tests/`, no `pytest.ini`, no CI workflow. Quickstart is "run once, look at Phoenix UI, done."
- **No Dockerfile, no Cloud Run yaml, no GitHub Actions.** The quickstart runs locally only. Production deployment shape is left as exercise.
- **No `a2a-sdk`, no `google-adk[a2a]`.** Single-agent, no multi-agent orchestration. Our spec uses `SequentialAgent` for the orchestrator + a sub-agent (ADR-012); the quickstart sidesteps this entirely.
- **No datasets, no prompt-versioning via Phoenix.** README mentions you *could* do it via MCP at runtime, but the repo itself ships no dataset YAML / JSONL.
- **`.gemini/settings.json` has `--apiKey` as an empty string.** You're expected to either edit the file or `export PHOENIX_API_KEY=...` in the shell. Quickstart does NOT show env-var injection into the MCP `npx` command.

**Subjective read:** the quickstart is laser-focused on one thing — *"prove the trace pipeline works end-to-end."* It deliberately omits eval/experiment/deployment surface so the developer hits the Phoenix UI fast and feels the magic. Everything beyond traces is left to the contestant. **ChaosLab's job is to fill the eval/experiment/deployment gap with chaos engineering as the differentiator.**

---

## 2. The End-to-End Story

What the quickstart actually builds, traced line by line:

### Step 1 — User runs `make run MESSAGE='Find a floral dress in size M'`

Makefile target:
```
run:
    cd agent && uv run python main.py "$(if $(MESSAGE),$(MESSAGE),Help me find a floral summer dress and buy size M.)"
```

### Step 2 — `agent/main.py` boots one ADK turn

```python
load_dotenv(Path(__file__).resolve().parent.parent / ".env")   # repo-root .env
from instrumentation import setup_tracing
from shopping_demo.agent import root_agent

async def run_turn(user_text: str) -> None:
    setup_tracing()                                            # registers Phoenix BEFORE runner
    app_name, user_id, session_id = "hackathon_shopping", "local_user", secrets.token_hex(8)
    runner = InMemoryRunner(agent=root_agent, app_name=app_name)
    await runner.session_service.create_session(...)
    async for _ in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=types.Content(role="user", parts=[types.Part(text=user_text)]),
    ):
        pass
```

Notes:
- `InMemoryRunner` (not `Runner` with a `RuntimeConfig`) — quickstart uses the simplest possible session/runner pair.
- `session_id` is a `secrets.token_hex(8)` per run — each invocation is a fresh session.
- The `async for _ in runner.run_async(...)` loop **discards every event**. The quickstart cares only about side effects (LLM calls, tool calls, spans) — not the agent's text output. This is deliberate: Phoenix captures everything in spans, so stdout is irrelevant.

### Step 3 — `agent/instrumentation.py` registers Phoenix

```python
from phoenix.otel import register

_provider: Optional[Any] = None

def setup_tracing() -> Optional[Any]:
    global _provider
    if _provider is not None:
        return _provider
    if not (os.environ.get("PHOENIX_API_KEY") or "").strip():
        return None                                            # silent no-op if no key
    _provider = register(
        project_name=os.environ.get("PHOENIX_PROJECT_NAME", "gemini-hackathon"),
        batch=False,                                           # synchronous exports
        auto_instrument=True,                                  # ← the whole game
        verbose=False,
    )
    return _provider
```

Three details that matter:
1. **`auto_instrument=True`** auto-discovers installed OpenInference instrumentors. Because `openinference-instrumentation-google-adk` is in `pyproject.toml`, ADK gets instrumented automatically — *no manual `GoogleADKInstrumentor().instrument()` call needed.*
2. **`batch=False`** — synchronous export. For a one-shot CLI run this is correct (script exits before a batched flush could fire). For Cloud Run we'll want batching.
3. **No `set_global_tracer_provider` flag.** Quickstart runs locally (Cloud Run-equivalent shape), so default global provider works. The Vertex Agent Engine gotcha (ADR-005 in our docs) doesn't apply here.

### Step 4 — `shopping_demo/agent.py` defines the ADK `Agent`

```python
_model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

root_agent = Agent(
    model=_model,
    name="personalized_shopping_agent",
    instruction=personalized_shopping_agent_instruction,
    tools=[
        FunctionTool(func=search),
        FunctionTool(func=click),
    ],
)
```

- Single `Agent` (not `SequentialAgent` / `LoopAgent` / `ParallelAgent`).
- Two tools — `search` and `click` — both wrapped via `FunctionTool(func=...)`. This is the canonical pattern from `google/adk-samples` personalized-shopping.
- **Model default is `gemini-2.5-flash`**, not `gemini-3.5-flash`. See §7 — this conflicts with our spec.

### Step 5 — The tools mutate a tiny in-memory gym-style env

`shopping_demo/mini_webshop.py` implements a state machine (`search_page` → `results` → `product` → `done`) with a 3-product hardcoded catalog. Each tool call calls `webshop_env.step(action_string)` and returns the new observation text. The agent reasons over the observation strings.

### Step 6 — Spans flow to Phoenix Cloud

Because `auto_instrument=True` enabled `GoogleADKInstrumentor`, every:
- LLM call → `LLM`-kind span with input/output/token counts/model name
- Tool call → `TOOL`-kind span with `tool_call.function.name` + arguments + return value
- Agent loop iteration → parent `AGENT` span

…streams over OTLP-HTTP to `PHOENIX_COLLECTOR_ENDPOINT` (must include `/s/<space>` suffix — see .env.example warning).

### Step 7 — User opens Phoenix UI → sees trace tree

Project = `gemini-hackathon` (default). Each `make run` produces one trace. README §3: *"Confirm LLM and tool spans appear."* That's the whole acceptance test.

### Step 8 — (Optional) Phoenix MCP from Gemini CLI

This is the *separate, second* surface. README §"Phoenix MCP (Gemini CLI)" is explicit:

> *"Phoenix MCP runs **inside Gemini CLI**, not inside the Python ADK process."*

The Python agent emits traces. The Gemini CLI (running on the developer's laptop, configured via `.gemini/settings.json`) then queries those traces back via the MCP server. The agent itself never invokes the MCP server in this quickstart.

This is the key architectural fact most people miss: **the quickstart's "self-improvement loop" is human-in-the-loop via Gemini CLI, not autonomous via the ADK agent.** Closing that loop autonomously (agent reads its own traces, modifies its own prompt) is what the partner-arize.md bonus criterion asks for and what the quickstart leaves unbuilt.

---

## 3. Phoenix MCP Integration Pattern

### The config file: `.gemini/settings.json`

```json
{
  "mcpServers": {
    "phoenix": {
      "command": "npx",
      "args": [
        "-y",
        "@arizeai/phoenix-mcp@latest",
        "--baseUrl",
        "https://app.phoenix.arize.com/s/your-space",
        "--apiKey",
        ""
      ]
    },
    "phoenix-docs": {
      "url": "https://arizeai-433a7140.mintlify.app/mcp"
    }
  }
}
```

Three things to note:

1. **Two MCP servers configured.** Not just `phoenix` for trace/eval data — also `phoenix-docs` (a hosted Mintlify MCP) for in-IDE doc lookup. The agent gets both runtime data AND documentation as tools.
2. **`@arizeai/phoenix-mcp@latest`** is npx-launched. No local install required. `command: "npx"` + `-y` to skip the "install this package?" prompt. This is the canonical "drop-in MCP server" shape.
3. **`--baseUrl` must include `/s/<space>` suffix.** Same rule as `PHOENIX_COLLECTOR_ENDPOINT` in the .env. Bare `https://app.phoenix.arize.com` will 401.

### What tools the agent gets through Phoenix MCP

Per README §4 ("Agent queries Phoenix via MCP (runtime superpower)") + the Phoenix MCP docs (https://arize.com/docs/phoenix/integrations/phoenix-mcp-server), tool *categories* are:

| Category | What the agent can do |
|---|---|
| **Projects / Traces / Spans** | List recent traces, fetch a specific span, inspect attributes/annotations, query by filter |
| **Sessions** | Review multi-turn conversation flows, fetch session-level annotations |
| **Annotation configs** | Inspect available labeling/scoring configs |
| **Prompts** | Create, list, update, fetch by ID/tag/"latest"; manage tags |
| **Datasets** | List datasets, retrieve examples, synthesize new examples |
| **Experiments** | List results, retrieve metadata, outputs, annotations |

**CRITICAL gap (confirmed by our RAT-results.md and ADR-005):** The Phoenix MCP server does **NOT** expose:
- `experiments.run_experiment` — you must use `phoenix.client.AsyncClient().experiments.run_experiment(...)` via the Python SDK
- `spans.log_span_annotations` (write path) — must go via Python SDK

This means: **if ChaosLab's chaos run needs to programmatically kick off an experiment from inside the agent, we wrap the SDK call in a custom ADK `FunctionTool`.** The quickstart does not show this pattern. ADR-005 in our `docs/architecture.md` is the canonical reference.

### How the quickstart uses MCP (it doesn't, really)

The README's example prompts for Gemini CLI are *human-driven*:
> *"In Phoenix, show me the last 3 traces in my gemini-hackathon project."*
> *"In Phoenix, summarize my latest experiment results."*
> *"In Phoenix, create a prompt that classifies user intent."*

The quickstart does NOT wire the Phoenix MCP server into the Python ADK agent's `tools=[...]` list. The Python agent has only `search` and `click`. The MCP surface is *post-hoc analysis* done by a human in Gemini CLI.

**ChaosLab differentiation:** we want the ADK agent itself to consume Phoenix MCP at runtime, autonomously. That's the "self-improvement loop" the track bonuses.

---

## 4. Evaluation Pattern

### What the quickstart ships: nothing.

There is no eval code in this repo. Verified:
- `grep -r "phoenix.evals" .` → 0 results in main branch (would have shown in tree if present)
- `grep -r "llm_as_judge" .` → 0 results
- `pyproject.toml` does NOT include `arize-phoenix-evals`. Only `arize-phoenix>=7.0` (the meta package; pulls evals transitively per uv.lock 3.0.0, but no import statement uses it)

### What the README *says* about evals: also nothing.

Search for "eval" / "judge" / "rubric" in README.md → zero matches. The README mentions evals only obliquely via Phoenix MCP example prompts ("summarize my latest experiment results"), but never shows how to *produce* an experiment result.

### The official docs path (what ChaosLab must build from scratch)

Per partner-arize.md §"Hackathon-specific gotchas" #3 and Devpost rules, evals are mandatory. The canonical pattern (from `arize-phoenix-evals` 3.0.0 docs):

```python
# Pattern ChaosLab will use — NOT in the quickstart
from phoenix.evals import llm_classify, OpenAIModel  # or GeminiModel
from phoenix.client import AsyncClient

RUBRIC = """
You are grading whether the agent's response correctly executed the user's purchase request.
Output exactly one of: CORRECT | INCORRECT
"""

px = AsyncClient()
spans_df = await px.spans.get_spans_dataframe(project_name="chaoslab")
evals_df = llm_classify(
    dataframe=spans_df,
    template=RUBRIC,
    model=GeminiModel(model="gemini-3.5-flash"),   # ← our pinned judge
    rails=["CORRECT", "INCORRECT"],
)
await px.spans.log_span_annotations(annotations=...)
```

### What ChaosLab adds beyond this

The standard pattern grades *what the agent did*. ChaosLab grades *whether the agent survived a fault*. We need:
1. **Per-fault-class rubrics** (F1 prompt-injection: did the agent refuse? F2 rate-limit: did it back off? F3 tool-error: did it retry/degrade? F4 schema-drift: did it adapt?).
2. **Trace-as-assertion** assertions on span tree structure (per CLAUDE.md hard rule), not just output text.

---

## 5. OpenInference Instrumentor

### Which instrumentor: `openinference-instrumentation-google-adk`

From `pyproject.toml`:
```toml
dependencies = [
    "openinference-instrumentation-google-adk>=0.1.11",
    "google-adk>=1.32.0",
    "google-genai>=1.9.0",
    ...
    "arize-phoenix>=7.0",
]
```

Pinned in `uv.lock`:
- `openinference-instrumentation-google-adk` = **0.1.11**
- `google-adk` = **1.32.0**
- `google-genai` = **1.9.0**

### Why google-adk (not vertexai, not google-genai)

The quickstart instruments at the **ADK framework** layer, not the underlying Gemini SDK. This means:
- One instrumentor covers all ADK-managed spans: agent loops, tool dispatch, LLM calls
- `auto_instrument=True` finds it automatically via entry points (per the OpenInference convention)
- You get the proper `openinference.span.kind` attribute set to `AGENT` / `TOOL` / `LLM` (per ADR-007 in our architecture.md — those are the correct attribute names)

If you were to use `openinference-instrumentation-vertexai` or `openinference-instrumentation-google-genai` instead, you'd only get LLM spans, not agent/tool structure spans. **For our spec: `openinference-instrumentation-google-adk` is the right choice and matches CLAUDE.md.**

### The exact 3-line setup (per official Phoenix docs, verified)

```bash
pip install openinference-instrumentation-google-adk google-adk arize-phoenix-otel
```

```python
from phoenix.otel import register
tracer_provider = register(project_name="my-llm-app", auto_instrument=True)
```

The quickstart's `instrumentation.py` is a defensive wrapper around this — adds an env-var gate (silent no-op if `PHOENIX_API_KEY` missing) and a singleton guard (`_provider is not None` check to prevent double-registration).

### Vertex AI Agent Engine caveat (verified via Phoenix docs)

> *"Vertex AI framework aggressively manages the OpenTelemetry global state. To prevent trace loss, the agent module must use `set_global_tracer_provider=False` when registering Phoenix, along with `batch=False` for synchronous exports."*

ChaosLab deploys to **Cloud Run, not Agent Engine** (per our architecture.md). So the global-state gotcha is FYI only. But the singleton guard pattern in `instrumentation.py` is worth copying verbatim — prevents accidental re-registration in any environment.

---

## 6. What ChaosLab Should COPY (highest-leverage section)

These are concrete, line-level patterns to lift from the quickstart into ChaosLab.

### COPY-1 — The instrumentation singleton wrapper (verbatim)

**Source:** `agent/instrumentation.py` (lines 33–48 of upstream)
**Destination:** `apps/chaoslab-agent/src/chaoslab_agent/instrumentation.py`
**Story:** S1 / S2 (foundation)

```python
# Use this exact shape — env-var gate + singleton + batch=False + auto_instrument=True
_provider: Optional[Any] = None

def setup_tracing() -> Optional[Any]:
    global _provider
    if _provider is not None:
        return _provider
    if not (os.environ.get("PHOENIX_API_KEY") or "").strip():
        return None
    _provider = register(
        project_name=os.environ.get("PHOENIX_PROJECT_NAME", "chaoslab"),
        batch=False,                # see COPY-1-NOTE
        auto_instrument=True,
        verbose=False,
    )
    return _provider
```

**COPY-1-NOTE:** `batch=False` is correct for the one-shot CLI but **WRONG for Cloud Run with sustained traffic**. For the deployed `chaoslab-agent` service, flip to `batch=True` (default). The local dev/test path can keep `batch=False`. Make it env-driven: `batch=os.environ.get("PHOENIX_BATCH", "1") == "1"`.

### COPY-2 — `.gemini/settings.json` MCP config shape

**Source:** `.gemini/settings.json` (whole file)
**Destination:** `.gemini/settings.json` in ChaosLab repo root
**Story:** S0.5 (Phoenix MCP wiring) or whichever story sets up dev-loop tooling

Copy verbatim, but:
- Replace `--baseUrl` with our actual Phoenix space hostname (env-substituted, not committed)
- Add a third MCP server entry for `gitlab` (per ADR-011, MR-emission path) pointing to `https://gitlab.com/api/v4/mcp`
- DO NOT commit a real `--apiKey`. Use `${PHOENIX_API_KEY}` or document the `export` step in our README

### COPY-3 — `auto_instrument=True` reliance (don't manually call `.instrument()`)

**Source:** `agent/instrumentation.py` line 41
**Reason:** Manually calling `GoogleADKInstrumentor().instrument()` works but creates fragility — if the entry-point name ever changes, manual calls break first. `auto_instrument=True` is the documented "future-proof" path. CLAUDE.md hard-rule: "Don't import `google.adk.*` outside `chaoslab_agent.adk_types`" — `auto_instrument=True` keeps us compliant.

### COPY-4 — `FunctionTool(func=...)` wrapping pattern

**Source:** `agent/shopping_demo/agent.py` lines 31–34
**Destination:** every place ChaosLab defines an agent tool
**Story:** S2+ (fault-class tools, judge tools, MR-emission tool)

```python
from google.adk.tools import FunctionTool
# Each fault class becomes a FunctionTool wrapping an async function
tools=[
    FunctionTool(func=inject_prompt_injection),    # F1
    FunctionTool(func=inject_rate_limit),          # F2
    FunctionTool(func=inject_tool_error),          # F3
    FunctionTool(func=inject_schema_drift),        # F4
    FunctionTool(func=run_phoenix_experiment),     # wraps phoenix.client.AsyncClient()
    FunctionTool(func=emit_gitlab_mr),             # wraps python-gitlab hybrid (ADR-011)
]
```

The `tool_context: ToolContext` parameter (see `search.py` line 19) is also the canonical signature when you need access to ADK runtime state — copy that.

### COPY-5 — `load_dotenv(repo_root / ".env")` boot pattern

**Source:** `agent/main.py` line 25 + `agent/shopping_demo/agent.py` line 23
**Destination:** every entrypoint in `apps/chaoslab-agent/` and `apps/target-agent/`

Both the CLI entrypoint AND the agent module itself load `.env` defensively. This lets `make run` AND `adk run shopping_demo` both pick up env. Copy this — our `target-agent` Cloud Run service will have multiple entrypoints (HTTP + CLI for debug).

### COPY-6 — `secrets.token_hex(8)` session IDs

**Source:** `agent/main.py` line 35
**Reason:** Avoids ambient session leakage between runs. Each chaos run gets its own session ID so spans are cleanly partitioned in Phoenix. Use for our chaos-run orchestrator: `session_id = f"chaos-{run_id}-{secrets.token_hex(4)}"`.

### COPY-7 — README "Phoenix MCP runs INSIDE Gemini CLI" mental model

**Source:** README "Phoenix MCP (Gemini CLI)" section, first sentence
**Why this matters:** This is the mental model the judges expect. ChaosLab should also offer a Gemini-CLI-driven "investigate the chaos run" experience for the demo video — not just the autonomous loop. Judges will reach for Gemini CLI to grade.

### COPY-8 — `pyproject.toml` dep set as our floor

The quickstart's deps map cleanly onto ours, plus extras:
- `openinference-instrumentation-google-adk>=0.1.11` ✓ (CLAUDE.md aligned)
- `google-adk>=1.32.0` — note: quickstart pins 1.32, our spec pins `google-adk>=2.1.0,<3.0.0` per CLAUDE.md/ADR-012. **There's a 1.x → 2.x divergence. See §7.**
- `google-genai>=1.9.0` ✓
- `arize-phoenix>=7.0` — meta-package; pulls evals + client transitively. We may want to pin `arize-phoenix-evals` and `arize-phoenix-client` explicitly because we use them in the hot path.
- `opentelemetry-sdk>=1.27.0` ✓
- `opentelemetry-exporter-otlp-proto-http>=1.27.0` ✓

---

## 7. What ChaosLab Should NOT Copy

These are quickstart choices that conflict with our spec or are deliberate shortcuts the quickstart takes that we must NOT.

### NOT-1 — `gemini-2.5-flash` as default model

**Source:** `agent/shopping_demo/agent.py` line 28 — `_model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")`
**Conflict:** CLAUDE.md hard rule pins `gemini-3.5-flash` for JUDGE_LLM and disallows older models. `gemini-2.5-flash` predates our pinned models.
**Action:** In ChaosLab, default to `gemini-3.5-flash` (or `gemini-3.1-pro-preview` for non-judge paths). Never inherit the quickstart's default.
**Also:** `gemini-2.0-flash` is deprecated per CLAUDE.md — make sure no example, doc, or test ever references it.

### NOT-2 — `.env.example` model comment

**Source:** `.env.example` line 13 — `# GEMINI_MODEL=gemini-2.5-flash`
**Conflict:** same as NOT-1. Our `.env.example` should show `GEMINI_MODEL=gemini-3.5-flash` and a comment explaining the pin.

### NOT-3 — `google-adk>=1.32.0` pin

**Source:** `pyproject.toml` line 9
**Conflict:** Our spec pins `google-adk>=2.1.0,<3.0.0` (CLAUDE.md, ADR-012). The quickstart is on the 1.x line and predates the 2.x release that includes our required `[a2a]` extra and the deprecated-but-needed `SequentialAgent` shape.
**Action:** Use `google-adk[a2a]>=2.1.0,<3.0.0`. Do NOT explicitly pin `a2a-sdk` (per CLAUDE.md gotcha — explicit pin breaks `uv sync`; transitive resolution to `a2a-sdk<0.4` is correct).
**Caveat:** the `auto_instrument=True` pattern in the quickstart works on 1.32 and *should* work on 2.x — but `openinference-instrumentation-google-adk` version compatibility needs verification. CLAUDE.md says `>=0.1.11`; check during S1 / S1.5 whether a newer version (e.g. `>=0.2.x`) is needed for ADK 2.x.

### NOT-4 — `InMemoryRunner` for the production hot path

**Source:** `agent/main.py` line 36
**Conflict:** `InMemoryRunner` is a dev convenience. ChaosLab's `chaoslab-agent` Cloud Run service will need a persistent session/state surface — likely the `RuntimeConfig` + a `DatabaseSessionService` or `VertexAiSessionService` per ADR (check architecture.md). Quickstart uses InMemoryRunner because it's a one-shot CLI; we must NOT carry it into production code paths.
**Action:** Use `InMemoryRunner` only in tests and `make demo` local runs. Production agent boots with `Runner(agent=..., session_service=...)` against a persistent backend.

### NOT-5 — `mini_webshop.py` in-memory catalog as the target agent

**Source:** all of `agent/shopping_demo/mini_webshop.py`
**Conflict:** CLAUDE.md hard rule §14 — *"No mocks in submitted hot path. Real Phoenix, real Gemini, real target."* The mini webshop is explicitly a mock (README §1: *"This repo uses a tiny in-memory catalog so you can run locally in minutes"*).
**Action:** ChaosLab's `target-agent` Cloud Run service must be a real agent doing a real task (per spec, it's the ADK agent under test — likely the personalized-shopping ADK sample at full fidelity, OR a domain-relevant ADK agent we author). The quickstart's mini_webshop pattern (`get_webshop_env()` singleton with `step()` interface) is fine *as a test fixture for chaos injection unit tests*, but never as the demo'd target.

### NOT-6 — README upstream credit suggestion ("replace mini_webshop with the full WebShop stack")

The README hints we could swap in the full `google/adk-samples` personalized-shopping agent. That agent requires PyTorch + Pyserini + multi-gigabyte product downloads — heavy lift, not Cloud-Run-friendly. **Don't go there.** Pick a lighter real domain (e.g. a real public API: weather, news, GitHub) so the target-agent stays Cloud-Run-deployable in seconds.

### NOT-7 — Single-`Agent` shape for our orchestrator

**Source:** `agent/shopping_demo/agent.py` — bare `Agent(...)` with two tools.
**Conflict:** ChaosLab's orchestrator is a `SequentialAgent` (per ADR-012) running fault-injection → execute → judge → MR-emit phases. The quickstart's flat single-agent shape doesn't carry over.
**Action:** Use the quickstart's `Agent(...)` definition pattern for our SUB-agents (the target agent, the judge agent), but compose them under a `SequentialAgent` orchestrator at the top.

### NOT-8 — `batch=False` in production code

See COPY-1-NOTE. Quickstart uses `batch=False` correctly for a one-shot CLI. Cloud Run sustained traffic with `batch=False` will hammer Phoenix's ingest. Env-gate it.

### NOT-9 — Empty `--apiKey` committed in `.gemini/settings.json`

The quickstart commits `"--apiKey", ""` and expects users to edit. Worse than env-var injection. For ChaosLab, commit `${PHOENIX_API_KEY}` and document the export step (or generate `.gemini/settings.json` from a template at setup time).

### NOT-10 — Discarding all events from `runner.run_async`

**Source:** `agent/main.py` lines 38–43 — `async for _ in runner.run_async(...): pass`
**Why this is wrong for us:** Quickstart only cares about side effects (spans). ChaosLab's orchestrator needs to *inspect* events in-flight to detect when a fault should fire (e.g. inject rate-limit before the 3rd tool call). Hold onto events: `async for event in runner.run_async(...): chaos_state.observe(event)`.

---

## 8. What ChaosLab Adds That the Quickstart Misses

This is our differentiation. None of this is in the quickstart.

### ADDS-1 — Chaos engineering / fault injection (F1–F4)

The whole core. Quickstart has zero fault injection. ChaosLab introduces:
- **F1 Prompt injection** — adversarial inputs in tool returns
- **F2 Rate-limit / latency spikes** — simulated 429s and 5s+ tool delays
- **F3 Tool errors** — schema mismatches, 500s, partial failures
- **F4 Schema drift** — silent tool-output format changes mid-session

Per CLAUDE.md, F1–F4 are NATIVELY reimplemented (not vendored from `deepankarm/agent-chaos`).

### ADDS-2 — Trace-as-assertion test pattern

Per CLAUDE.md hard rule, we assert on Phoenix span tree structure. Quickstart never runs an assertion — it just emits.

```python
# Pattern ChaosLab adds — NOT in quickstart
spans = await px.spans.get_spans_dataframe(project_name="chaoslab", trace_id=run_id)
assert any(s["openinference.span.kind"] == "TOOL" and s["status_code"] == "ERROR" for s in spans)
assert spans.shape[0] >= 5  # agent did not silently give up after the fault
```

### ADDS-3 — Closed self-improvement loop

The bonus criterion. Quickstart leaves it as human-in-the-loop via Gemini CLI. ChaosLab's orchestrator:
1. Runs target agent under fault
2. Phoenix captures the failure traces
3. Judge LLM evaluates the trace via `arize-phoenix-evals` → score
4. Agent (via Phoenix MCP + custom `FunctionTool` for write-path) reads its own failure pattern
5. Auto-emits a GitLab MR with a prompt/code patch (hybrid python-gitlab + official MCP per ADR-011)
6. Re-runs to verify the patch raises the score

### ADDS-4 — LLM-as-judge + code evals

Quickstart has none. ChaosLab uses `arize-phoenix-evals` with `gemini-3.5-flash` as JUDGE_LLM (CLAUDE.md pinned).

### ADDS-5 — Datasets + experiments

Quickstart never creates a dataset. ChaosLab versions a "fault scenarios" dataset in Phoenix and runs experiments comparing target-agent variants (pre-patch vs post-patch) against it.

### ADDS-6 — Cloud Run deployment

Quickstart runs locally only. ChaosLab ships 3 Cloud Run services (`chaoslab-web`, `chaoslab-agent`, `target-agent`) per architecture.md, deployed via GitHub Actions + WIF.

### ADDS-7 — Frontend dashboard

Quickstart has no UI — you look at the Phoenix UI directly. ChaosLab adds `chaoslab-web` (Next.js 16 + visx + Framer Motion 12) that visualizes fault → trace → judge → patch flow. This is the demo surface.

### ADDS-8 — Tests + TDD discipline + CI

Quickstart has zero tests. CLAUDE.md mandates TDD + trace-as-assertion + the 400-line-per-file guard + pre-commit + CI gates.

### ADDS-9 — Multi-instrumentor Tier 2 coverage

Per architecture.md, we also instrument LangChain / CrewAI / OpenAI-Agents traffic if the target-agent calls those frameworks. Quickstart is ADK-only.

### ADDS-10 — Hybrid GitLab MR emission

Per ADR-011, our MR-emit path is HYBRID: `python-gitlab` SDK for branches+files (the official MCP doesn't expose `create_branch` / `create_or_update_file`), then `create_merge_request` via the official `https://gitlab.com/api/v4/mcp` MCP (preserves judging credit). Quickstart has no MR-emit path.

---

## Cross-references

- Our partner notes: `research/google-cloud-rapid-agent/partner-arize.md`
- Our RAT findings on Phoenix MCP coverage: `research/google-cloud-rapid-agent/RAT-results.md`
- ADR-005 (Phoenix MCP hybrid wrap): `docs/architecture.md`
- ADR-007 (OpenInference attribute names): `docs/architecture.md`
- ADR-011 (GitLab hybrid MR emit): `docs/architecture.md`
- ADR-012 (`google-adk[a2a]>=2.1.0,<3.0.0` pin): `docs/architecture.md`
- CLAUDE.md "Stack (locked)" and "Hard rules" — authoritative

## Open verifications to do during implementation

These are things the quickstart can't answer for us — to be resolved in S1 / S1.5:

1. Does `openinference-instrumentation-google-adk>=0.1.11` work with `google-adk>=2.1.0`? Quickstart proves it works with `google-adk==1.32.0`. The 2.x major could change span emission. **Test in S1.**
2. Does `auto_instrument=True` discover the ADK instrumentor when ADK 2.x's entry-point names change? **Test in S1.**
3. The `phoenix.client.AsyncClient()` wrap for `run_experiment` / `log_span_annotations` (ADR-005) — confirm the exact method signatures for `arize-phoenix-client==2.6.0` (the version pinned in the quickstart's uv.lock). **Verify in S2.**
4. Does `batch=True` cause trace loss in Cloud Run cold-start scenarios? **Test in S5 / S6 deployment.**
