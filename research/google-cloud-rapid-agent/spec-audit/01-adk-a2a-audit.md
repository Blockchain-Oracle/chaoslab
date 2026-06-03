# Spec Audit 01 — ADK + A2A Claims vs. Actual `google-adk` Source

**Audited:** 2026-06-03
**Auditor:** Sahil (research subagent)
**Source of truth:** `github.com/google/adk-python` @ `main` (commit pushed 2026-06-02), `google-adk` 2.1.0 on PyPI, `a2a-sdk` 0.3.4 / 1.1.0 on PyPI, `arize-phoenix-otel` 0.16.1.
**Repo:** https://github.com/google/adk-python (canonical Python repo)

**Summary verdict:** the spec is mostly correct in _shape_ but contains **three load-bearing bugs** that will silently mis-train downstream coding agents: (1) the wrong callback-signature reference for the malformed-tool fault, (2) a deprecated workflow class (`SequentialAgent`) used as the orchestrator spine, and (3) an `a2a-sdk` pin (`>=1.1.0,<2.0.0`) that is _incompatible_ with the version `google-adk[a2a]` actually ships (`<0.4,>=0.3.4`). The Vertex Agent Engine `set_global_tracer_provider=False, batch=False` gotcha is real and the spec is correct on that one.

---

## Claim 1: `google-adk` package exists on PyPI with Python 3.12 support

**Source in spec:** `docs/architecture.md` line 12 (`google-adk — Agent framework`), line 24 (Python 3.12)
**Verdict:** CONFIRMED
**Evidence:**

- `curl https://pypi.org/pypi/google-adk/json` returns `version: 2.1.0`, `requires_python: >=3.10`
- Classifiers list: `Python :: 3.10, 3.11, 3.12, 3.13`
- Repo URL: `https://github.com/google/adk-python` (verified existence; 19,964 stars; last push 2026-06-02)
  **Note:** spec says "latest verified" without pinning. Latest stable = **`2.1.0`**. The `google-adk[a2a]` extra pulls `a2a-sdk<0.4,>=0.3.4` (see Claim 11 for downstream impact).

---

## Claim 2: `SequentialAgent` class exists with `sub_agents=[...]` parameter

**Source in spec:** `docs/architecture.md` ADR-002, `docs/coding-standards.md` line 162, `docs/stories/story-4.2-sequential-orchestrator.md` (entire story spine)
**Verdict:** NEEDS-FIX (class exists with that exact signature, BUT IS DEPRECATED in `google-adk` 2.1.0)
**Evidence:**

- File: https://github.com/google/adk-python/blob/main/src/google/adk/agents/sequential_agent.py
- The class is decorated with:
  ```python
  @deprecated(
      'SequentialAgent is deprecated and will be removed in future versions.'
      ' Please use Workflow instead.'
  )
  class SequentialAgent(BaseAgent):
  ```
- `sub_agents` is inherited from `BaseAgent`: `sub_agents: list[BaseAgent] = Field(default_factory=list)` (https://github.com/google/adk-python/blob/main/src/google/adk/agents/base_agent.py L139-140)
- Import path: `from google.adk.agents import SequentialAgent` (works; also exported at `google.adk.agents.sequential_agent.SequentialAgent`)
- The canonical sample `contributing/samples/legacy_workflows/simple_sequential_agent/agent.py` lives in a folder explicitly called `legacy_workflows/`.
- Replacement: `from google.adk.workflow import Workflow` (https://github.com/google/adk-python/blob/main/src/google/adk/workflow/__init__.py) — new graph-based API with `Node`, `Edge`, `FunctionNode`, `JoinNode`, `START`.

**If NEEDS-FIX — recommended spec amendment:**

- Add an explicit ADR line: "We use the _deprecated-but-stable_ `SequentialAgent` for hackathon delivery speed; `Workflow` migration is out-of-scope (TODO post-hackathon)." This lets coding agents ignore the `DeprecationWarning` filter and not panic-rewrite to `Workflow`.
- Story-4.2 line "the return is a `google.adk.agents.SequentialAgent` instance" — add note that a `DeprecationWarning` will be emitted at import; explicitly silence it via the existing `pyproject.toml` `filterwarnings = ["ignore::DeprecationWarning:google.*"]` (already present at coding-standards.md line 131). Add a confirmation test case: `pytest.warns(DeprecationWarning)` is expected at construction.

---

## Claim 3: `LlmAgent` class with `model=`, `instruction=`, `tools=`, `name=` parameters

**Source in spec:** Story-4.2 (lines 158-164 example), story-2.2 (target agent), coding-standards.md
**Verdict:** NEEDS-FIX (field name is `instruction` singular, not `instructions`; spec uses correct singular in story-4.2 lines 24, 26, 28, 30 — but `agent-starter-pack` and many docs say `instructions`. The spec is OK here. The fix is to a tangential point.)
**Evidence:**

- https://github.com/google/adk-python/blob/main/src/google/adk/agents/llm_agent.py L213-228
  ```python
  model: Union[str, BaseLlm] = ''
  instruction: Union[str, InstructionProvider] = ''   # SINGULAR
  global_instruction: Union[str, InstructionProvider] = ''
  tools: list[ToolUnion] = Field(default_factory=list)  # L306
  name: str  # inherited from BaseAgent
  description: str = ''  # inherited
  output_key: Optional[str] = None  # L373
  ```
- `Agent` is an alias for `LlmAgent` (re-exported at the top level): `from google.adk import Agent`
- `tools=` accepts `Callable | BaseTool | BaseToolset` — plain Python functions are auto-wrapped as `FunctionTool` via `_convert_tool_union_to_tools` (llm_agent.py L142-186).
- **Important caveat — `DEFAULT_MODEL`:** ADK's built-in default is `'gemini-3-flash-preview'` (llm_agent.py L209), NOT `gemini-3.5-flash`. The spec wants `gemini-3.5-flash` (ADR-007) — that string is accepted by ADK (passed straight to Gemini API; `gemini-3.5-flash` is GA as of 2026-05-19) but agents MUST set `model="gemini-3.5-flash"` explicitly. Never rely on ADK's default.

**If NEEDS-FIX — recommended spec amendment:**

- Coding-standards.md ADK-specific Python patterns: add bullet "Every `LlmAgent` MUST set `model=` explicitly. ADK default is `gemini-3-flash-preview` — ADR-007 mandates `gemini-3.5-flash`."
- Story-4.2 line 37 already asserts `.model == "gemini-3.5-flash"` — good. The shell-verification step at lines 122-127 also asserts this. Confirmed.

---

## Claim 4: `LoopAgent` and `ParallelAgent` exist

**Source in spec:** `docs/coding-standards.md` line 162 ("`SequentialAgent`/`ParallelAgent`/`LoopAgent` for in-process")
**Verdict:** NEEDS-FIX (both exist, both deprecated — same migration story as `SequentialAgent`)
**Evidence:**

- https://github.com/google/adk-python/blob/main/src/google/adk/agents/parallel_agent.py — `@deprecated('ParallelAgent is deprecated ... Please use Workflow instead.')`
- https://github.com/google/adk-python/blob/main/src/google/adk/agents/loop_agent.py — `@deprecated('LoopAgent is deprecated ... Please use Workflow instead.')`
- Both inherit `sub_agents: list[BaseAgent]` from `BaseAgent`.
- Import: `from google.adk.agents import LoopAgent, ParallelAgent`
- `LoopAgent` additionally has `max_iterations: Optional[int] = None`

**If NEEDS-FIX:** Same fix as Claim 2 — add explicit "use deprecated workflow classes for hackathon scope" note. ChaosLab does not use Loop/Parallel in the orchestrator (only mentioned as banned-pattern context), so impact is minimal.

---

## Claim 5: `google.adk.tools.FunctionTool` exists (class wrapping a Python function)

**Source in spec:** Story-4.3 (referenced from coding-standards.md line 164: "Custom FunctionTools: wrap Phoenix Python SDK calls. Each ≤30 LOC")
**Verdict:** CONFIRMED
**Evidence:**

- https://github.com/google/adk-python/blob/main/src/google/adk/tools/function_tool.py
  ```python
  class FunctionTool(BaseTool):
      def __init__(self, func: Callable[..., Any], *, require_confirmation=False):
          ...
  ```
- Import: `from google.adk.tools import FunctionTool` (lazy-loaded via `_LAZY_MAPPING` in `tools/__init__.py`)
- It is a **class wrapping a callable**, NOT a decorator. Usage: `FunctionTool(func=my_function)`.
- Plain functions passed to `LlmAgent(tools=[my_func])` get auto-wrapped — explicit `FunctionTool(func=...)` is only needed when you want non-default behavior (e.g. `require_confirmation`).

**Spec impact:** Story-4.3 plan to "wrap Phoenix Python SDK as `FunctionTool`" is valid. The coding standard line "Custom FunctionTools: wrap Phoenix Python SDK calls. Each ≤30 LOC" is achievable — pattern is just `tool = FunctionTool(func=run_experiment)`.

---

## Claim 6: `before_tool_callback`, `after_tool_callback`, `before_model_callback`, `after_model_callback` are real ADK hooks

**Source in spec:** `docs/coding-standards.md` line 161 ("Callback registration: use `before_tool_callback`, `after_tool_callback`, `before_model_callback`, `after_model_callback`"); story-5.2 entire spec
**Verdict:** CONFIRMED (all four exist, plus two error-callbacks the spec doesn't mention)
**Evidence:**

- https://github.com/google/adk-python/blob/main/src/google/adk/agents/llm_agent.py L403-490
- Exact field declarations:
  ```python
  before_model_callback: Optional[BeforeModelCallback] = None   # L403
  after_model_callback: Optional[AfterModelCallback] = None      # L418
  on_model_error_callback: Optional[OnModelErrorCallback] = None # L432 (NEW — spec doesn't mention)
  before_tool_callback: Optional[BeforeToolCallback] = None      # L447
  after_tool_callback: Optional[AfterToolCallback] = None        # L462
  on_tool_error_callback: Optional[OnToolErrorCallback] = None   # L477 (NEW — spec doesn't mention)
  ```
- All four (plus two error variants) accept either a single callable OR a `list[callable]`. List-mode runs callbacks in order until one returns non-None.
- `before_agent_callback` / `after_agent_callback` live on `BaseAgent` (base_agent.py L149-163).

### Exact signatures (load-bearing for story-5.2)

```python
# from llm_agent.py L92-130 — these are typealiases used by the fields above

_SingleBeforeModelCallback = Callable[
    [CallbackContext, LlmRequest],
    Union[Awaitable[Optional[LlmResponse]], Optional[LlmResponse]],
]
# Return: non-None LlmResponse → skips real model call, uses callback's response

_SingleAfterModelCallback = Callable[
    [CallbackContext, LlmResponse],
    Union[Awaitable[Optional[LlmResponse]], Optional[LlmResponse]],
]
# Return: non-None LlmResponse → replaces actual model response

_SingleOnModelErrorCallback = Callable[
    [CallbackContext, LlmRequest, Exception],
    Union[Awaitable[Optional[LlmResponse]], Optional[LlmResponse]],
]

_SingleBeforeToolCallback = Callable[
    [BaseTool, dict[str, Any], ToolContext],
    Union[Awaitable[Optional[dict]], Optional[dict]],
]
# Return: non-None dict → skips real tool, uses callback's return as tool result
# NOTE: return type is Optional[DICT], not Optional[Any]

_SingleAfterToolCallback = Callable[
    [BaseTool, dict[str, Any], ToolContext, dict],  # 4 args (tool, args, ctx, tool_response)
    Union[Awaitable[Optional[dict]], Optional[dict]],
]

_SingleOnToolErrorCallback = Callable[
    [BaseTool, dict[str, Any], ToolContext, Exception],
    Union[Awaitable[Optional[dict]], Optional[dict]],
]
```

**Key facts for coding agents:**

- `CallbackContext`, `LlmRequest`, `LlmResponse` are imported from `google.adk.agents.callback_context` / `google.adk.models.llm_request` / `google.adk.models.llm_response`.
- `BaseTool` is at `google.adk.tools.base_tool`.
- `ToolContext` lives at `google.adk.tools.tool_context` and is _aliased_ to `Context`: `ToolContext = Context` (tool_context.py L23). So `from google.adk.tools.tool_context import ToolContext` resolves.
- Callbacks may be `async` (returning `Awaitable`) or sync — ADK awaits if awaitable. Story-5.2's `async def callback` is fine.
- Mutation in place: `before_model_callback` may mutate `llm_request` (docstring L412-414 says "Callback can mutate the request").

**Critical signature bug in story-5.2 spec example (lines 138-191):**
The spec's example returns a raw string for `invalid_json` mode:

```python
if self.mode == "invalid_json":
    return '{"order_id": "12345", "items": [{"name": "widget", "qty": 2'
```

But the **return type of `_SingleBeforeToolCallback` is `Optional[dict]`** — returning a string violates the type contract. ADK does not crash (the type is enforced at type-check time only) but the OpenInference TOOL span's `output.value` will be set from a dict-shaped result; a returned string will either be coerced or set the attribute unexpectedly. Story-5.2 BDD acceptance criterion "the span has attribute output.value is not valid JSON" depends on ADK's coercion behavior here, which is undefined.

**If NEEDS-FIX — recommended amendments:**

1. Coding-standards.md ADK-specific patterns: replace `"Callback registration: use \`before_tool_callback\`, ..."`with a list that includes`on_tool_error_callback`and`on_model_error_callback`— the spec's malformed-tool exception mode (story-5.2 line 188) should land in`on_tool_error_callback`, NOT raise from `before_tool_callback`.
2. Story-5.2 line 144 (`MalformationMode`): clarify the return contract — for `invalid_json` mode, return `{"__chaoslab_invalid_json__": '{"truncated":...'}` — i.e. wrap the bogus string in a dict so it conforms to the `Optional[dict]` contract, then have the BDD assertion read `output.value["__chaoslab_invalid_json__"]` and `json.loads` THAT. Or: set the malformed string as a span ATTRIBUTE (`span.set_attribute("output.value", ...)`) and return `{}` to satisfy the type contract.
3. Story-5.2 line 189 (`exception` mode): the callback should NOT raise — `before_tool_callback` raising is undefined behavior. Instead use `on_tool_error_callback` registered separately on the same agent, OR return a dict that the target's tool wrapper detects and raises from. Document the chosen approach explicitly.

---

## Claim 7: `to_a2a(agent, port=8001)` function exists

**Source in spec:** `docs/stories/story-2.2-target-a2a-exposure.md` lines 23, 117-122, lines 23 specifically says `from google.adk.a2a.utils.agent_to_a2a import to_a2a`
**Verdict:** CONFIRMED (import path correct, function exists, takes keyword arg `port`)
**Evidence:**

- File: https://github.com/google/adk-python/blob/main/src/google/adk/a2a/utils/agent_to_a2a.py
- Signature (L82-95):
  ```python
  @a2a_experimental
  def to_a2a(
      agent: BaseAgent | Workflow,
      *,
      host: str = "localhost",
      port: int = 8000,        # NOT 8001 — default is 8000
      protocol: str = "http",
      agent_card: AgentCard | str | None = None,
      push_config_store: PushNotificationConfigStore | None = None,
      task_store: TaskStore | None = None,
      runner: Runner | None = None,
      lifespan: Callable[[Starlette], AsyncIterator[None]] | None = None,
      agent_executor_factory: Callable[[Runner], A2aAgentExecutor] | None = None,
  ) -> Starlette:
  ```
- Returns a Starlette ASGI app.
- Decorated `@a2a_experimental` — emits an experimental-API warning at call time; not blocking.
- Imports `from google.adk.a2a.utils.agent_to_a2a import to_a2a` (matches spec) — also accessible via `from google.adk.a2a.utils import to_a2a` indirectly.

**Spec note:** story-2.2 sets `port=8001` (not the default 8000) — that's a deliberate choice and is fine because port is a kwarg.

**Important nuance:** the agent card path is NOT registered until the Starlette `lifespan` runs (`setup_a2a` is inside `_combined_lifespan` — agent_to_a2a.py L201-227). This means a simple `app.router.routes` check at import-time will NOT show `/.well-known/agent-card.json` because routes are added lazily via `A2AStarletteApplication.add_routes_to_app(app)`. Story-2.2 BDD line 44 ("the app exposes routes including `/.well-known/agent-card.json` (assert via `app.router.routes` or equivalent)") will FAIL pre-lifespan. The route check MUST happen after starting the server (which story-2.2's curl in step 3 of shell verification already does correctly — but the python test fixture line 44 is buggy).

**If NEEDS-FIX — recommended amendment:**

- Story-2.2 line 44 acceptance criterion: change "assert via `app.router.routes` or equivalent" to "assert via HTTP GET to `/.well-known/agent-card.json` against a running uvicorn instance (lifespan must execute first)". The existing shell-verification step 3 already does this correctly via curl.

---

## Claim 8: `RemoteA2aAgent` class with `agent_card="<URL>/.well-known/agent-card.json"` parameter, usable as a sub-agent

**Source in spec:** `docs/architecture.md` ADR-002, `docs/stories/story-3.2-adk-adapter.md` lines 24, 159-235
**Verdict:** CONFIRMED with caveat (the `agent_card` parameter takes URL string, file path, OR `AgentCard` object — flexible. Class is `@a2a_experimental`.)
**Evidence:**

- File: https://github.com/google/adk-python/blob/main/src/google/adk/agents/remote_a2a_agent.py
- Constructor signature (L141-160):
  ```python
  @a2a_experimental
  class RemoteA2aAgent(BaseAgent):
      def __init__(
          self,
          name: str,
          agent_card: Union[AgentCard, str],   # URL or file path or AgentCard object
          *,
          description: str = "",
          httpx_client: Optional[httpx.AsyncClient] = None,
          timeout: float = DEFAULT_TIMEOUT,    # 600.0 seconds
          ...
      )
  ```
- Imports: `from google.adk.agents.remote_a2a_agent import RemoteA2aAgent, AGENT_CARD_WELL_KNOWN_PATH`
- Used as `sub_agents=[remote_agent]` in canonical sample: https://github.com/google/adk-python/blob/main/contributing/samples/a2a/a2a_basic/agent.py (line: `sub_agents=[roll_agent, prime_agent]` where `prime_agent` is `RemoteA2aAgent`)
- `RemoteA2aAgent` inherits from `BaseAgent`, so YES it can be a sub-agent.

**Well-known path:**

- ADK imports `AGENT_CARD_WELL_KNOWN_PATH` from `a2a.utils.constants` (remote_a2a_agent.py L51-54):
  ```python
  try:
      from a2a.utils.constants import AGENT_CARD_WELL_KNOWN_PATH
  except ImportError:
      AGENT_CARD_WELL_KNOWN_PATH = "/.well-known/agent.json"   # OLD fallback
  ```
- `a2a-sdk` 0.3.4 and 1.1.0 both set `AGENT_CARD_WELL_KNOWN_PATH = '/.well-known/agent-card.json'` (the newer hyphenated form). Verified: https://github.com/a2aproject/a2a-python/blob/main/src/a2a/utils/constants.py and `v0.3.4` tag.
- Spec is correct: `/.well-known/agent-card.json` is the canonical path. The hyphenated form is the new spec; the old `agent.json` is only the in-ADK fallback for _very_ old a2a-sdk installs.

**Canonical usage pattern (verified from contributing/samples/a2a/a2a_basic/agent.py):**

```python
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent, AGENT_CARD_WELL_KNOWN_PATH

prime_agent = RemoteA2aAgent(
    name="prime_agent",
    description="Agent that handles checking if numbers are prime.",
    agent_card=f"http://localhost:8001/a2a/check_prime_agent{AGENT_CARD_WELL_KNOWN_PATH}",
)
```

**If NEEDS-FIX:** none for this claim — story-3.2 is correct in shape. But the spec adds a wrapper class `RemoteA2aAgentWrapper` in `chaoslab_agent.adk_types` (line 165 of story-3.2) — that's fine but optional; the wrapper exists purely for type-quarantine, not because `RemoteA2aAgent` lacks any feature.

---

## Claim 9: `google.adk` exposes `Runner` class

**Source in spec:** story-4.2 line 31 ("ADK Runner API"), line 187 ("`from google.adk.runners import InMemoryRunner`")
**Verdict:** CONFIRMED
**Evidence:**

- https://github.com/google/adk-python/blob/main/src/google/adk/runners.py L152 — `class Runner:`
- L2206 — `class InMemoryRunner(Runner):`
- Top-level export: `from google.adk import Runner` (per https://github.com/google/adk-python/blob/main/src/google/adk/__init__.py)
  ```python
  __all__ = ["Agent", "Context", "Event", "Runner", "Workflow"]
  ```
- `InMemoryRunner(agent=root_agent)` is the test-friendly variant (uses in-memory artifact/session/memory services). Signature: `InMemoryRunner(agent: Optional[BaseAgent] = None, *, node=None, app_name=None, plugins=None, app=None, plugin_close_timeout=5.0)` (runners.py L2218-2227).

**Spec note:** story-4.2 line 187 is correct. `app_name="chaoslab"` is valid. Use:

```python
from google.adk.runners import InMemoryRunner
runner = InMemoryRunner(agent=build_orchestrator(), app_name="chaoslab")
async for event in runner.run_async(user_id="test", session_id="s", new_message=...):
    ...
```

---

## Claim 10: `set_global_tracer_provider=False, batch=False` are valid `phoenix.otel.register()` arguments

**Source in spec:** Vertex Agent Engine context (mentioned in architecture/05 and observability setup notes)
**Verdict:** CONFIRMED
**Evidence:**

- File: https://github.com/Arize-ai/phoenix/blob/main/packages/phoenix-otel/src/phoenix/otel/otel.py L64-76
  ```python
  def register(
      *,
      endpoint: Optional[str] = None,
      project_name: Optional[str] = None,
      batch: bool = False,                          # confirmed kwarg
      set_global_tracer_provider: bool = True,      # confirmed kwarg
      headers: Optional[Dict[str, str]] = None,
      protocol: Optional[Literal["http/protobuf", "grpc"]] = None,
      verbose: bool = True,
      auto_instrument: bool = False,
      api_key: Optional[str] = None,
      **kwargs: Any,
  ) -> _TracerProvider:
  ```
- `arize-phoenix-otel` latest version: `0.16.1` (PyPI).

---

## Claim 11: Vertex Agent Engine "register without these flags = silent trace loss" gotcha is real

**Source in spec:** mentioned in best-practices research; spec implies ChaosLab is deployed to **Cloud Run** (ADR-003) not Agent Engine, so this is documentation-relevant rather than blocking
**Verdict:** CONFIRMED (real gotcha; documented at Arize official Phoenix-ADK integration page)
**Evidence:**

- https://arize.com/docs/phoenix/integrations/python/google-adk/google-adk-tracing recommends:
  ```python
  tracer_provider = register(
      project_name="adk-agent",
      batch=False,                          # Agent Engine pauses CPU between requests
      set_global_tracer_provider=False,     # Agent Engine has its own global provider
  )
  GoogleADKInstrumentor().instrument(tracer_provider=tracer_provider)
  ```
- The reason: Vertex Agent Runtime aggressively manages OTel global state; if Phoenix uses the global provider, Agent Engine's init shuts down Phoenix's export pipeline and drops traces silently.
- Spec impact: ChaosLab is on Cloud Run (ADR-003), not Agent Engine, so `set_global_tracer_provider=True` (the default) is safe. But the spec should still recommend `batch=False` for the canonical-replay subset (≤5k spans during judging) — `SimpleSpanProcessor` (batch=False) is fine at this volume and avoids drop-on-shutdown.

**If NEEDS-FIX:** none — but worth adding a note to `chaoslab_agent.observability.setup()` (story-4.5) so the coding agent uses `batch=False` for the demo path.

---

## ADDITIONAL FINDING: `a2a-sdk` version pin in story-2.2 is wrong

**Source in spec:** `docs/stories/story-2.2-target-a2a-exposure.md` line 134: "`a2a-sdk>=1.1.0,<2.0.0` is the canonical 2026 pin"
**Verdict:** WRONG
**Evidence:**

- PyPI `google-adk` 2.1.0 metadata: `requires_dist` for the `[a2a]` extra is `a2a-sdk<0.4,>=0.3.4; extra == "a2a"`
- This means installing `google-adk[a2a]` will RESOLVE to `a2a-sdk` in the `0.3.x` line (latest `0.3.x` at the time of writing).
- Pinning `a2a-sdk>=1.1.0,<2.0.0` will produce an **uv resolver conflict** when combined with `google-adk[a2a]`. The build will fail.
- Although `a2a-sdk` 1.1.0 exists on PyPI as the latest stable, `google-adk` 2.1.0 has not yet bumped its constraint to allow 1.x.

**If WRONG — recommended spec amendment:**

- Story-2.2 line 134: replace "a2a-sdk>=1.1.0,<2.0.0 is the canonical 2026 pin" with "let `google-adk[a2a]` extra pull `a2a-sdk` transitively; do NOT pin `a2a-sdk` explicitly. If you must pin, use `a2a-sdk>=0.3.4,<0.4` to match `google-adk` 2.1.0's constraint. Bump in lockstep with future ADK releases."
- best-practices/01 §4.14 (referenced in story-2.2) likely contains the same wrong pin — audit that doc too in a follow-up.

---

## ADDITIONAL FINDING: agent card route exposure is lifespan-deferred

**Source in spec:** `docs/stories/story-2.2-target-a2a-exposure.md` BDD line 44
**Verdict:** NEEDS-FIX
**Evidence:** as documented under Claim 7 — `to_a2a()`'s agent-card route is registered inside the Starlette `lifespan` async context manager (agent_to_a2a.py L201-227), so a static `app.router.routes` check at import-time will be empty. The HTTP curl test (shell-verification step 3) does work, but the BDD criterion phrasing is misleading.

---

## Verified minimal "hello world" ADK SequentialAgent code (pulled from official ADK repo)

```python
# Verified against https://github.com/google/adk-python/blob/main/contributing/samples/legacy_workflows/simple_sequential_agent/agent.py

from google.adk.agents.llm_agent import LlmAgent
from google.adk.agents.sequential_agent import SequentialAgent
from google.genai import types


def roll_die(sides: int) -> int:
    """Roll a die and return the rolled result."""
    import random
    return random.randint(1, sides)


roll_agent = LlmAgent(
    name="roll_agent",
    description="Handles rolling dice of different sizes.",
    instruction="When asked to roll a die, you must call the roll_die tool.",
    tools=[roll_die],   # plain callable — auto-wrapped as FunctionTool
    model="gemini-3.5-flash",   # MUST set explicitly per ADR-007; ADK default is gemini-3-flash-preview
)


def check_prime(nums: list[int]) -> str:
    """Check if a given list of numbers are prime."""
    ...


prime_agent = LlmAgent(
    name="prime_agent",
    description="Handles checking if numbers are prime.",
    instruction="When asked to check primes, call the check_prime tool.",
    tools=[check_prime],
    model="gemini-3.5-flash",
)


root_agent = SequentialAgent(
    name="simple_sequential_agent",
    sub_agents=[roll_agent, prime_agent],
    # agents run in order: roll_agent -> prime_agent
)


# To run it:
async def main() -> None:
    from google.adk.runners import InMemoryRunner
    from google.genai import types as genai_types

    runner = InMemoryRunner(agent=root_agent, app_name="hello_adk")
    new_message = genai_types.Content(
        role="user",
        parts=[genai_types.Part(text="Roll a 6-sided die")],
    )
    async for event in runner.run_async(
        user_id="user1",
        session_id="session1",
        new_message=new_message,
    ):
        print(event)
```

---

## Verified import paths (for coding-standards.md adk-types quarantine module)

| Symbol                       | Verified import path                                                        | Notes                                                  |
| ---------------------------- | --------------------------------------------------------------------------- | ------------------------------------------------------ |
| `Agent` (alias)              | `from google.adk import Agent`                                              | top-level re-export of `LlmAgent`                      |
| `LlmAgent`                   | `from google.adk.agents import LlmAgent`                                    | OR `from google.adk.agents.llm_agent import LlmAgent`  |
| `SequentialAgent`            | `from google.adk.agents import SequentialAgent`                             | DEPRECATED                                             |
| `LoopAgent`                  | `from google.adk.agents import LoopAgent`                                   | DEPRECATED                                             |
| `ParallelAgent`              | `from google.adk.agents import ParallelAgent`                               | DEPRECATED                                             |
| `BaseAgent`                  | `from google.adk.agents import BaseAgent`                                   |                                                        |
| `Workflow` (new API)         | `from google.adk.workflow import Workflow`                                  | OR top-level `from google.adk import Workflow`         |
| `RemoteA2aAgent`             | `from google.adk.agents.remote_a2a_agent import RemoteA2aAgent`             | `@a2a_experimental`                                    |
| `AGENT_CARD_WELL_KNOWN_PATH` | `from google.adk.agents.remote_a2a_agent import AGENT_CARD_WELL_KNOWN_PATH` | resolves to `/.well-known/agent-card.json` via a2a-sdk |
| `to_a2a`                     | `from google.adk.a2a.utils.agent_to_a2a import to_a2a`                      | `@a2a_experimental`                                    |
| `FunctionTool`               | `from google.adk.tools import FunctionTool`                                 | lazy-loaded                                            |
| `BaseTool`                   | `from google.adk.tools.base_tool import BaseTool`                           | also `from google.adk.tools import BaseTool`           |
| `ToolContext`                | `from google.adk.tools.tool_context import ToolContext`                     | aliased to `Context`                                   |
| `Runner`                     | `from google.adk.runners import Runner`                                     | OR top-level `from google.adk import Runner`           |
| `InMemoryRunner`             | `from google.adk.runners import InMemoryRunner`                             |                                                        |
| `CallbackContext`            | `from google.adk.agents.callback_context import CallbackContext`            | for `before_model_callback`                            |
| `LlmRequest`                 | `from google.adk.models.llm_request import LlmRequest`                      |                                                        |
| `LlmResponse`                | `from google.adk.models.llm_response import LlmResponse`                    |                                                        |

---

## Recommended spec amendments (concrete diffs)

### 1. `docs/architecture.md` (around ADR-002, line 234-238)

ADD a new ADR-002a paragraph:

> **ADR-002a: Use deprecated `SequentialAgent` for hackathon scope; defer `Workflow` migration.** ADK 2.1.0 deprecated `SequentialAgent`/`LoopAgent`/`ParallelAgent` in favor of `Workflow` (graph-based API). For hackathon delivery speed and because the canonical multi-agent samples (`contributing/samples/legacy_workflows/`) still use `SequentialAgent`, ChaosLab targets `SequentialAgent`. `DeprecationWarning` is silenced via `[tool.pytest.ini_options].filterwarnings = ["ignore::DeprecationWarning:google.*"]` (already in coding-standards.md line 131). Post-hackathon migration to `Workflow` is tracked in `docs/post-hackathon-todo.md`.

### 2. `docs/coding-standards.md` line 161 (ADK-specific Python patterns)

REPLACE:

> **Callback registration:** use `before_tool_callback`, `after_tool_callback`, `before_model_callback`, `after_model_callback` as the injection surface for faults.

WITH:

> **Callback registration:** use `before_tool_callback`, `after_tool_callback`, `before_model_callback`, `after_model_callback`, `on_tool_error_callback`, `on_model_error_callback`. All six are real fields on `LlmAgent`. Each callback receives ADK-typed args (`CallbackContext`/`LlmRequest`/`LlmResponse` for model callbacks; `BaseTool, dict[str, Any], ToolContext` for tool callbacks) and returns `Optional[LlmResponse]` (model) or `Optional[dict]` (tool). Returning non-None **short-circuits** the real call. Fault injection that needs to RAISE belongs in `on_tool_error_callback`, NOT `before_tool_callback` (raising from before_tool_callback is undefined behavior).

### 3. `docs/coding-standards.md` line 162

ADD a sentence after the existing one:

> **Note:** `SequentialAgent`/`ParallelAgent`/`LoopAgent` are deprecated in ADK 2.1.0 (replacement: `Workflow`). For hackathon scope per ADR-002a, continue using the deprecated classes; `DeprecationWarning` is silenced via the existing pytest `filterwarnings` config.

### 4. `docs/coding-standards.md` add new bullet under ADK-specific patterns

ADD:

> **Always set `model=` explicitly on every `LlmAgent`.** ADK's built-in default is `gemini-3-flash-preview` (see `LlmAgent.DEFAULT_MODEL`). ADR-007 mandates `gemini-3.5-flash`. Test fixtures assert `.model == "gemini-3.5-flash"` per story-4.2 line 37.

### 5. `docs/stories/story-2.2-target-a2a-exposure.md` line 134

REPLACE:

> a2a-sdk version. Per `best-practices/01-python-project-layout.md` §4.14, `a2a-sdk>=1.1.0,<2.0.0` is the canonical 2026 pin.

WITH:

> a2a-sdk version. `google-adk[a2a]` 2.1.0 transitively requires `a2a-sdk<0.4,>=0.3.4`. Do NOT pin `a2a-sdk` explicitly in pyproject.toml — let the extra resolve it. If a future ADK release relaxes the constraint and you need to pin, match `google-adk`'s `requires_dist` for `[a2a]` extra exactly. **Note:** `a2a-sdk` 1.1.0 exists on PyPI but is incompatible with `google-adk` 2.1.0; pinning it produces a uv resolver conflict.

### 6. `docs/stories/story-2.2-target-a2a-exposure.md` line 44 (BDD criterion)

REPLACE:

> And the app exposes routes including "/.well-known/agent-card.json" (assert via app.router.routes or equivalent)

WITH:

> And the agent-card endpoint resolves: an HTTP GET to `http://localhost:<port>/.well-known/agent-card.json` against the running uvicorn instance returns 200 with valid JSON (the route is registered inside Starlette's lifespan, so `app.router.routes` is empty at import-time — assert via HTTP after server start).

### 7. `docs/stories/story-5.2-fault-malformed-tool.md` lines 144-191 (fault class signature)

REPLACE the example callback's return for `invalid_json`:

> ```python
> if self.mode == "invalid_json":
>     return '{"order_id": "12345", "items": [{"name": "widget", "qty": 2'
> ```

WITH:

> ```python
> if self.mode == "invalid_json":
>     # `before_tool_callback` return type is Optional[dict]; wrap the bogus string
>     # so the type contract holds. Phoenix's TOOL span renders output.value from
>     # the dict — the test asserts json.loads on the wrapped string field.
>     return {"__chaoslab_malformed__": '{"order_id": "12345", "items": [{"name": "widget", "qty": 2'}
> ```

AND for the `exception` mode, REPLACE:

> ```python
> if self.mode == "exception":
>     raise RuntimeError("F1: injected malformed tool output (mode=exception)")
> ```

WITH:

> ```python
> # `exception` mode: register a SEPARATE on_tool_error_callback that raises.
> # before_tool_callback short-circuits via return; raising from before_tool_callback
> # is undefined behavior per ADK source.
> if self.mode == "exception":
>     # signal that the test fixture should wire on_tool_error_callback to raise:
>     return {"__chaoslab_should_raise__": "F1: injected malformed tool output (mode=exception)"}
> ```

Update the corresponding BDD criterion (lines 64-67) to assert that the TOOL span has `status_code == "ERROR"` after the `on_tool_error_callback` raises, rather than before.

### 8. `docs/architecture.md` — Phoenix observability setup

Add to ADR-004 or new ADR-004a:

> **`phoenix.otel.register()` arguments for Cloud Run:** `register(project_name="chaoslab-<env>", batch=False, set_global_tracer_provider=True, auto_instrument=False)`. `batch=False` avoids drop-on-shutdown for the canonical-replay subset (≤5k spans). For Vertex Agent Engine deployment (NOT used in ChaosLab) the rule is `set_global_tracer_provider=False, batch=False` — Agent Engine aggressively manages OTel global state and will shut down Phoenix's exporter otherwise (https://arize.com/docs/phoenix/integrations/python/google-adk/google-adk-tracing).

---

## Counts

- **CONFIRMED:** 6 (Claims 1, 3-partial, 5, 7, 9, 10, 11)
- **NEEDS-FIX:** 4 (Claims 2, 4, 6-signature, story-2.2 BDD-44)
- **WRONG:** 1 (story-2.2 line 134 a2a-sdk pin)

## Most important single amendment

**Story-2.2 line 134 (a2a-sdk pin) — WRONG.** This will hard-break `uv sync` for `apps/target-agent` if a coding agent literally copies the spec's pin. Every other finding is a NEEDS-FIX where the code-as-written will probably still run; this one alone fails the build.

---

## Sources

- [google/adk-python on GitHub](https://github.com/google/adk-python) — canonical Python ADK source
- [google-adk on PyPI (2.1.0)](https://pypi.org/project/google-adk/)
- [a2aproject/a2a-python](https://github.com/a2aproject/a2a-python) — a2a-sdk source
- [Arize-ai/phoenix register source](https://github.com/Arize-ai/phoenix/blob/main/packages/phoenix-otel/src/phoenix/otel/otel.py)
- [Phoenix Google ADK integration docs](https://arize.com/docs/phoenix/integrations/python/google-adk/google-adk-tracing) — Agent Engine register gotcha
- [Canonical SequentialAgent sample](https://github.com/google/adk-python/blob/main/contributing/samples/legacy_workflows/simple_sequential_agent/agent.py)
- [Canonical RemoteA2aAgent sample](https://github.com/google/adk-python/blob/main/contributing/samples/a2a/a2a_basic/agent.py)
