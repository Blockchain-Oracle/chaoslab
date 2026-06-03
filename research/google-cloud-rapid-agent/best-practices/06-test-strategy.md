# 06 - Test Strategy: ADK + Phoenix + Next.js on Cloud Run

Factual best-practices reference for a Python ADK agent service, a Phoenix observability stack, and a Next.js frontend, all deployed to Cloud Run. No project-specific opinions. `[UNVERIFIED]` marks any claim not directly grounded in a primary doc cited inline.

Last verified against docs available as of 2026-06-02.

---

## 1. The test pyramid for an agent project

The canonical Cohn test pyramid still applies to LLM agent code, but the proportions shift because integration tests against a real LLM are slow, non-deterministic, and cost real money. A healthy hackathon-grade split:

- **Unit tests - ~70%**. Pure functions, Pydantic schema validation, prompt-template rendering, tool input/output marshalling, retry/backoff logic, deterministic agent state transitions, parsers. Run on every save. Should complete in under 10 seconds locally.
- **Integration tests - ~25%**. Real Phoenix Cloud (or a local docker-compose Phoenix), real Vertex AI / Gemini API, real MCP servers where feasible. These exercise the wiring, not the intelligence. Run on PR open and on merge to main. Should complete in under 5 minutes per shard.
- **End-to-end / visual tests - ~5%**. Playwright against staging Cloud Run URL. Smoke + a small handful of golden user flows + visual regression snapshots. Run on merge to main and pre-demo. Should complete in under 10 minutes total.

Why the asymmetry: the LLM is the most expensive and least deterministic dependency, so push as much logic as possible _out_ of LLM-touching code paths into deterministic helpers, and test those exhaustively. Reserve the LLM-touching layer for thin glue that you exercise with a small number of integration tests. This is the same principle that applies to any project with an expensive external dependency (e.g. payments, file storage) - mock the boundary, drive coverage in the surrounding code.

Two non-standard layers worth calling out for agent projects:

- **Trace-assertion tests** (a subspecies of integration). The agent runs end-to-end against a real or mocked LLM, but the assertion is on the _Phoenix span tree_ produced - did the agent call tool X before tool Y, with the right attributes, in the right order? This is the highest-signal-per-dollar test for an agent. Covered in section 5.
- **LLM-as-judge tests** (a subspecies of integration or nightly). A second LLM grades the first LLM's output against a rubric. Useful for quality gates but expensive; run on a schedule, not per PR. Covered in section 5.

Reference: [Practical Test Pyramid (Martin Fowler)](https://martinfowler.com/articles/practical-test-pyramid.html); [ADK Evaluation overview](https://adk.dev/evaluate/).

---

## 2. pytest fundamentals for ADK

### 2.1 pytest-asyncio configuration

ADK is async-first. Both the in-process `Runner` and the `Agent.run_async()` entrypoints return coroutines / async generators, so the test harness must drive an event loop.

Use `pytest-asyncio` in **auto mode** so you don't have to decorate every async test with `@pytest.mark.asyncio`. Per the docs: _"Auto mode automatically adds the asyncio marker to all asynchronous test functions and takes ownership of all async fixtures, regardless of whether they are decorated with @pytest.fixture or @pytest_asyncio.fixture."_ ([pytest-asyncio concepts](https://pytest-asyncio.readthedocs.io/en/stable/concepts.html))

`pyproject.toml`:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
markers = [
    "slow: marks tests as slow (deselect with -m 'not slow')",
    "online: marks tests that require network + LLM API access",
    "integration: marks tests that hit real Phoenix / Vertex AI",
    "visual: marks Playwright visual regression tests",
]
```

Event loop scope: by default each test gets a fresh function-scoped loop. For tests that share an expensive resource (e.g. a single Phoenix client, a single in-process MCP server), widen the loop with `@pytest.mark.asyncio(loop_scope="module")` or `"session"`.

Version note: `pytest-asyncio` 1.x changed several defaults from 0.x. As of May 2026 the latest is 1.4.0 ([pytest-asyncio releases](https://pypi.org/project/pytest-asyncio/)). Pin in `pyproject.toml` to avoid surprise breakages.

### 2.2 Fixtures: where to put them

Three-tier `conftest.py` placement:

- `tests/conftest.py` - global fixtures (event loop policy, Phoenix client, env var setup).
- `tests/unit/conftest.py` - fixtures used only by unit tests (deterministic Gemini stub, fake tool registry).
- `tests/integration/conftest.py` - fixtures used only by integration tests (real Phoenix client, Vertex AI credentials check, ADK `Runner` factory).

Fixtures pytest discovers by walking up the directory tree, so any test under `tests/unit/` automatically sees both `tests/conftest.py` and `tests/unit/conftest.py`. Don't import fixtures across `conftest.py` files - pytest does that for you.

### 2.3 Standard fixtures for an ADK project

```python
# tests/conftest.py
import os
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture(scope="session", autouse=True)
def disable_real_telemetry(monkeypatch_session):
    """Prevent OTel exporters from phoning home during unit tests."""
    os.environ["OTEL_SDK_DISABLED"] = "true"

@pytest.fixture
def mock_phoenix_client():
    """Drop-in for `phoenix.Client()` - records calls without network IO."""
    client = MagicMock()
    client.log_traces = AsyncMock()
    client.experiments = MagicMock()
    return client

@pytest_asyncio.fixture
async def deterministic_gemini_stub():
    """Returns a callable that intercepts genai calls and returns canned text."""
    from tests.fakes.gemini import FakeGenerativeModel
    return FakeGenerativeModel(responses=[])

@pytest_asyncio.fixture
async def in_memory_runner():
    """ADK InMemoryRunner - the recommended runner for tests."""
    from google.adk.runners import InMemoryRunner
    runner = InMemoryRunner()
    yield runner
    await runner.aclose()
```

The `InMemoryRunner` is the in-process runner ADK ships specifically for unit tests, per the ADK testing docs ([ADK testing & evaluation](https://deepwiki.com/google/adk-samples/15.3-testing-and-evaluation)). It avoids the gRPC / HTTP transports the production runner uses.

### 2.4 Markers and cost-aware selection

- `@pytest.mark.slow` - takes > 5 s.
- `@pytest.mark.online` - hits a network endpoint outside the test cluster (Vertex AI, Phoenix Cloud, MCP server on the internet).
- `@pytest.mark.integration` - exercises wiring between two or more services, may or may not be online.
- `@pytest.mark.visual` - Playwright visual snapshots.

Selection patterns:

```bash
# Local dev loop - fast unit tests only
pytest -m "not online and not slow"

# PR gate - everything except expensive nightly tests
pytest -m "not online or integration"

# Pre-merge - the full integration suite
pytest -m "integration"

# Nightly - everything including LLM-as-judge rubrics
pytest
```

In CI, define these as distinct workflow steps so a flake in the nightly LLM-judge suite doesn't block PRs that don't touch agent logic.

References: [pytest markers docs](https://docs.pytest.org/en/stable/how-to/mark.html); [ADK testing & evaluation](https://deepwiki.com/google/adk-samples/15.3-testing-and-evaluation).

---

## 3. Mocking the Gemini API for deterministic unit tests

The Gemini Python SDK (`google-genai`) sits on top of `httpx` for REST and on gRPC for streaming. For unit tests, most teams intercept at the HTTP layer; gRPC interception is harder and rarely needed if you stick to the REST surface in tests.

### 3.1 respx (recommended)

`respx` is the cleanest mocking option for httpx-based clients. Per the docs: _"To patch HTTPX, and activate the RESPX router, use the respx.mock decorator/context manager, or the respx_mock pytest fixture."_ ([respx user guide](https://lundberg.github.io/respx/guide/))

```python
import httpx
import pytest

@pytest.mark.asyncio
async def test_agent_handles_gemini_429(respx_mock):
    route = respx_mock.post(
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent"
    ).mock(side_effect=[
        httpx.Response(429, json={"error": "rate limited"}),
        httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": "ok"}]}}]}),
    ])
    result = await my_agent.run("hi")
    assert route.call_count == 2  # retry succeeded on the second call
    assert result.output == "ok"
```

Two assertion patterns worth using:

- `respx_mock(assert_all_called=True)` - fails if any registered route was never hit. Catches stale mocks.
- `respx_mock(assert_all_mocked=True)` - fails if the code under test makes a request you didn't register. Catches accidental network calls.

### 3.2 pytest-httpx (alternative)

`pytest-httpx` is a thinner wrapper around the same idea but with a slightly different API surface (`httpx_mock.add_response(...)` instead of route objects). Either works; `respx` has richer pattern matching (`__contains`, `__regex`, bitwise combinators) and is the de-facto choice for non-trivial agent test suites. `[UNVERIFIED]` - I haven't benchmarked the two against each other.

### 3.3 Mocking at the SDK boundary instead of the HTTP boundary

Sometimes you don't want to construct realistic Gemini JSON payloads. Instead, mock at `google.genai.Client.models.generate_content`:

```python
from unittest.mock import patch, AsyncMock
from google.genai import types

@pytest.mark.asyncio
async def test_agent_calls_search_tool():
    fake_response = types.GenerateContentResponse(
        candidates=[types.Candidate(
            content=types.Content(parts=[
                types.Part(function_call=types.FunctionCall(
                    name="search", args={"q": "phoenix observability"}
                ))
            ])
        )]
    )
    with patch("google.genai.client.AsyncClient.models.generate_content",
               new=AsyncMock(return_value=fake_response)):
        result = await my_agent.run("look up phoenix")
        assert result.tool_calls[0].name == "search"
```

This is brittle - SDK refactors break it - but it gives you typed in-memory responses without any HTTP marshalling.

### 3.4 Stubbing tool calls with deterministic responses

For multi-turn flows, sequence tool responses:

```python
respx_mock.post(GEMINI_URL).mock(side_effect=[
    httpx.Response(200, json=tool_call_response("search", {"q": "x"})),
    httpx.Response(200, json=tool_call_response("summarize", {"text": "..."})),
    httpx.Response(200, json=final_text_response("here is your answer")),
])
```

Per the respx docs: _"If the side effect is an iterable, each repeated request will get the next Response returned, or exception raised, from the iterable."_ ([respx user guide](https://lundberg.github.io/respx/guide/))

Build a small helper module `tests/fakes/gemini.py` with builders for `tool_call_response`, `final_text_response`, `error_response` - this saves enormous time across the suite.

### 3.5 When NOT to mock

At least one test per PR should hit the real Gemini API. Mocks lock in your _assumptions_ about the API; real calls catch SDK upgrades, API surface changes, and quota issues. The standard pattern is:

- Mock 100% in unit tests.
- Hit real Gemini in 5-10 integration tests, gated by `@pytest.mark.online`, run on merge to main.
- Hit real Gemini in nightly LLM-as-judge tests for quality regression detection.

---

## 4. Testing ADK agents specifically

### 4.1 Constructing minimal `Agent` instances

ADK's `Agent` (formerly `LlmAgent`) takes a model, instruction, tools, and optionally sub-agents and callbacks. For tests, construct the smallest valid agent:

```python
from google.adk.agents import Agent
from google.adk.runners import InMemoryRunner

def make_test_agent(tools=None, model="gemini-2.5-flash"):
    return Agent(
        name="test_agent",
        model=model,
        instruction="You are a test agent. Follow instructions literally.",
        tools=tools or [],
    )

@pytest.mark.asyncio
async def test_agent_basic_run(in_memory_runner):
    agent = make_test_agent()
    in_memory_runner.register_agent(agent)
    events = []
    async for event in in_memory_runner.run_async(
        user_id="u1", session_id="s1",
        new_message=types.Content(parts=[types.Part(text="hello")])
    ):
        events.append(event)
    assert any(e.is_final_response for e in events)
```

`[UNVERIFIED]` - exact runner API may shift across ADK minor versions; verify against your pinned `google-adk` version.

### 4.2 Testing `before_model_callback` / `after_model_callback`

Callbacks are pure functions (or coroutines) that wrap LLM invocation. Test them directly without any agent:

```python
from google.adk.agents.callback_context import CallbackContext

@pytest.mark.asyncio
async def test_before_model_callback_redacts_pii():
    from my_agent.callbacks import redact_pii_before_model
    ctx = MagicMock(spec=CallbackContext)
    ctx.user_content = types.Content(parts=[types.Part(text="my SSN is 123-45-6789")])
    await redact_pii_before_model(ctx, llm_request=ctx)
    assert "123-45-6789" not in ctx.user_content.parts[0].text
```

Test integration with the agent only if the callback registration path has logic worth covering (e.g. conditional registration).

### 4.3 Testing tool calls (`FunctionTool`)

ADK `FunctionTool` wraps a Python function. The function itself is just code - test it as a plain function. The wrapping is glue and only needs one happy-path test:

```python
from google.adk.tools import FunctionTool

def search(query: str) -> dict:
    """Search the web."""
    return {"results": [...]}

def test_search_returns_dict():
    assert "results" in search("anything")

@pytest.mark.asyncio
async def test_search_tool_registers():
    tool = FunctionTool(func=search)
    assert tool.name == "search"
    # invoke through the tool interface to confirm marshalling
    result = await tool.run_async(args={"query": "x"}, tool_context=...)
    assert "results" in result
```

### 4.4 Testing sub-agents (in-process)

Sub-agents are agents that another agent delegates to via `transfer_to_agent` or a sub-agent tool. In tests, mount both in the same `InMemoryRunner`:

```python
@pytest.mark.asyncio
async def test_root_delegates_to_specialist(in_memory_runner, mock_gemini):
    root = make_test_agent(name="root")
    specialist = make_test_agent(name="specialist")
    root.sub_agents = [specialist]
    in_memory_runner.register_agent(root)
    # ...
```

For pure unit tests, mock the sub-agent's `run_async` instead of running it.

### 4.5 Testing A2A peers

A2A (Agent-to-Agent) calls go over HTTP. Two strategies:

- **Mock with respx** at the HTTP boundary. Pretend the remote A2A peer responded with a known JSON envelope.
- **Spin up the real peer in-process** on a localhost port for true integration tests. ADK's `RemoteA2aAgent` accepts a base URL; point it at `http://localhost:8001` where a test `uvicorn` instance hosts the peer.

```python
@pytest_asyncio.fixture
async def peer_agent_server():
    import uvicorn, asyncio
    config = uvicorn.Config(app=peer_app, port=0, log_level="error")
    server = uvicorn.Server(config)
    task = asyncio.create_task(server.serve())
    await asyncio.sleep(0.1)  # let it bind
    port = server.servers[0].sockets[0].getsockname()[1]
    yield f"http://localhost:{port}"
    server.should_exit = True
    await task
```

### 4.6 SequentialAgent / LoopAgent / ParallelAgent

These are deterministic flow primitives - they sequence sub-agents without LLM choice. They should be tested with mocked sub-agents to assert ordering, not with real LLM calls.

```python
@pytest.mark.asyncio
async def test_sequential_runs_in_order(in_memory_runner):
    calls = []
    a = MockAgent(name="a", on_run=lambda: calls.append("a"))
    b = MockAgent(name="b", on_run=lambda: calls.append("b"))
    seq = SequentialAgent(name="root", sub_agents=[a, b])
    # ...
    assert calls == ["a", "b"]
```

`[UNVERIFIED]` - exact `MockAgent` shape depends on what helpers your project exposes.

References: [ADK testing & evaluation](https://deepwiki.com/google/adk-samples/15.3-testing-and-evaluation); [google/adk-python](https://github.com/google/adk-python); [ADK evaluate docs](https://adk.dev/evaluate/).

---

## 5. LLM-as-judge tests and trace-as-assertion

### 5.1 Trace-as-assertion: the cleanest pattern

The single most useful pattern for non-deterministic agent code is to assert on the _trace_ the agent produced, not on its natural-language output. The trace is structured (OpenInference spans), deterministic up to LLM choice variability, and directly reflects what the agent _did_.

Pattern:

```python
@pytest.mark.asyncio
async def test_agent_calls_search_before_summarize(phoenix_client):
    async with capture_traces(phoenix_client, project="test") as captured:
        await my_agent.run("research X")

    span_names = [s.name for s in captured.spans]
    assert "tool.search" in span_names
    assert "tool.summarize" in span_names
    assert span_names.index("tool.search") < span_names.index("tool.summarize")

    search_span = next(s for s in captured.spans if s.name == "tool.search")
    assert search_span.attributes["input.query"] == "X"
```

What this catches that natural-language assertions miss:

- Wrong tool sequencing.
- Missing tool calls.
- Wrong tool arguments.
- Slow spans (latency assertions).
- Token-budget violations (via `llm.token_count.total` attributes).

What it doesn't catch: actual answer quality. That's where LLM-as-judge comes in.

### 5.2 ADK's built-in evaluator

ADK ships an `AgentEvaluator` that runs trace-style assertions out of the box, with two criteria per [ADK evaluate docs](https://adk.dev/evaluate/):

- `tool_trajectory_avg_score` - exact match on tool call sequence, 0.0-1.0.
- `response_match_score` - ROUGE-1 similarity vs reference response, 0.0-1.0. Default threshold 0.8.

```python
from google.adk.evaluation.agent_evaluator import AgentEvaluator

@pytest.mark.asyncio
async def test_home_automation_eval():
    await AgentEvaluator.evaluate(
        agent_module="home_automation_agent",
        eval_dataset_file_path_or_dir="tests/eval/home_automation.test.json",
    )
```

The evalset format is backed by Pydantic schemas (`EvalSet`, `EvalCase` in `google.adk.evaluation`). Each case has user query, expected tool trajectory, expected intermediate responses, and a final reference response. A `test_config.json` alongside the evalset sets thresholds:

```json
{
  "criteria": {
    "tool_trajectory_avg_score": 1.0,
    "response_match_score": 0.8
  }
}
```

### 5.3 Phoenix LLM-as-judge

For richer rubrics (faithfulness, toxicity, helpfulness), Phoenix provides an LLM-as-judge framework. Per the Phoenix docs: _"LLM as a Judge is an evaluation pattern where a language model grades another model's output, trace, or session against a set of criteria."_ ([Phoenix LLM-as-a-Judge](https://arize.com/docs/phoenix/evaluation/concepts-evals/llm-as-a-judge))

The workflow:

1. Define a rubric prompt template with placeholders for input + output.
2. Pick an evaluator model (typically a stronger model than the one being evaluated, e.g. gemini-2.5-pro grading gemini-2.5-flash output).
3. Run the evaluator over a dataset of traces.
4. Gate on a threshold (e.g. faithfulness > 0.8 across the dataset).

Phoenix's `tool_invocation` evaluator is a built-in template that checks whether the agent invoked the right tool for the user's intent. Use it as a one-line gate in pytest:

```python
from phoenix.evals import llm_classify, TOOL_CALLING_PROMPT_TEMPLATE
from phoenix.evals.models import LiteLLMModel

@pytest.mark.online
@pytest.mark.integration
def test_tool_invocation_quality(phoenix_client):
    spans_df = phoenix_client.get_spans_dataframe(project="prod-eval")
    results = llm_classify(
        dataframe=spans_df,
        template=TOOL_CALLING_PROMPT_TEMPLATE,
        model=LiteLLMModel(model="gemini/gemini-2.5-pro"),
        rails=["correct", "incorrect"],
    )
    pass_rate = (results["label"] == "correct").mean()
    assert pass_rate > 0.85, f"Tool invocation pass rate dropped to {pass_rate:.2%}"
```

`[UNVERIFIED]` - exact import paths shift across Phoenix versions; verify against your pinned `arize-phoenix` version.

### 5.4 Custom rubrics

Define a project-specific rubric:

```python
RUBRIC = """
You are grading whether an agent gave a CORRECT answer.

User question: {input}
Agent answer: {output}
Reference: {reference}

Grade on a 0.0-1.0 scale:
- 1.0: Factually correct, addresses the question
- 0.5: Partially correct
- 0.0: Wrong or refuses to answer

Output JSON: {{"score": <float>, "reason": "<short>"}}
"""
```

Run the rubric over a small dataset (10-30 examples) committed to `tests/fixtures/golden_dataset.jsonl`. Fail the test if `mean_score < threshold`.

### 5.5 Snapshot-based eval

Maintain a "golden trace" dataset: the canonical span tree for a small set of inputs. Diff new runs against the golden tree. Useful for regression detection across model upgrades. Implement with `syrupy` or a hand-rolled JSON diff.

### 5.6 Cost control for these tests

LLM-as-judge tests are expensive. Defaults:

- Trace-assertion (no second LLM call): every PR.
- ADK `AgentEvaluator` with `tool_trajectory_avg_score` + `response_match_score` (ROUGE, no LLM): every PR.
- LLM-as-judge with a small dataset (10-30 examples): nightly.
- LLM-as-judge with a large dataset (100+ examples): weekly or pre-release.

Track per-run cost in CI (Phoenix logs token counts as span attributes; sum them in a post-run job).

References: [ADK evaluate docs](https://adk.dev/evaluate/); [Phoenix LLM-as-a-Judge](https://arize.com/docs/phoenix/evaluation/concepts-evals/llm-as-a-judge); [Phoenix datasets & experiments](https://arize.com/docs/phoenix/datasets-and-experiments/quickstart-datasets); [Arize Phoenix ADK integration](https://deepwiki.com/google/adk-samples/17.2-arize-phoenix-evaluation-integration).

---

## 6. Phoenix integration testing

### 6.1 Local Phoenix via Docker

Per the Phoenix docs: _"You can run Phoenix locally on your laptop in under a minute by pulling the image and starting the container."_ ([Phoenix self-hosting](https://arize.com/docs/phoenix/self-hosting))

For CI, two viable patterns:

**Pattern A: Docker container per test run.**

```yaml
# .github/workflows/test.yml
services:
  phoenix:
    image: arizephoenix/phoenix:latest
    ports:
      - 6006:6006
    options: --health-cmd="curl -f http://localhost:6006/healthz" --health-interval=5s
```

Then in `conftest.py`:

```python
@pytest.fixture(scope="session")
def phoenix_endpoint():
    return "http://localhost:6006"

@pytest.fixture(scope="session")
def phoenix_client(phoenix_endpoint):
    from phoenix.client import Client
    return Client(endpoint=phoenix_endpoint)
```

**Pattern B: A dedicated Phoenix Cloud project per CI environment.**

Create projects `ci-pr-<pr-number>` and tear them down at the end of the run. Slower setup, but exercises the real Phoenix Cloud surface and catches version drift between local Docker and hosted Phoenix.

### 6.2 Asserting traces materialized

After running the agent, query Phoenix for the spans you expect:

```python
@pytest.mark.integration
async def test_trace_has_expected_spans(phoenix_client, agent_under_test):
    project = f"test-{uuid.uuid4()}"
    configure_tracing(project=project, endpoint=phoenix_client.endpoint)
    await agent_under_test.run("hello")

    # Give Phoenix a moment to ingest
    await asyncio.sleep(2)
    spans = phoenix_client.spans.get_spans_dataframe(project=project)
    assert len(spans) > 0
    assert "llm.gemini" in spans["name"].values
```

The 2-second sleep is a code smell. Better: poll with a timeout for the expected span count, or use the synchronous OTLP exporter in tests (set `OTEL_BSP_SCHEDULE_DELAY=0` or use `SimpleSpanProcessor` instead of `BatchSpanProcessor`).

### 6.3 Asserting datasets + experiments

Phoenix datasets and experiments are first-class for regression eval:

```python
from phoenix.client import Client

@pytest.mark.integration
def test_experiment_runs(phoenix_client):
    dataset = phoenix_client.datasets.get_dataset(dataset="golden-set")
    experiment = phoenix_client.experiments.run_experiment(
        dataset=dataset,
        task=my_task,
        evaluators=[faithfulness_evaluator, helpfulness_evaluator],
    )
    summary = experiment.summary()
    assert summary["faithfulness"]["mean"] > 0.85
```

(API shape adapted from [Phoenix datasets quickstart](https://arize.com/docs/phoenix/datasets-and-experiments/quickstart-datasets); verify against your installed Phoenix version.)

### 6.4 Tearing down test data

CI runs accumulate trash projects. Either:

- Use per-run project names (`ci-<run-id>`) and delete them via `phoenix_client.projects.delete(name=...)` at session teardown.
- Use a single `ci` project and rely on TTL-based cleanup if you've configured retention.

For local Docker Phoenix, the cleanest path is to stop the container and remove the volume between runs.

References: [Phoenix self-hosting](https://arize.com/docs/phoenix/self-hosting); [Phoenix datasets quickstart](https://arize.com/docs/phoenix/datasets-and-experiments/quickstart-datasets); [arize-phoenix on PyPI](https://pypi.org/project/arize-phoenix/).

---

## 7. Mocking external MCP servers

MCP servers are JSON-RPC 2.0 over stdio or SSE. Three test strategies:

### 7.1 In-process mock MCP client

Pass a fake `mcp.ClientSession` into your tool registry. The fake returns canned tool lists and tool call results without ever opening a transport.

```python
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def mock_mcp_session():
    session = MagicMock()
    session.list_tools = AsyncMock(return_value=types.ListToolsResult(tools=[
        types.Tool(name="search", description="...", inputSchema={...}),
    ]))
    session.call_tool = AsyncMock(return_value=types.CallToolResult(content=[
        types.TextContent(type="text", text="result")
    ]))
    return session
```

### 7.2 Record + replay with `agent-vcr`

`agent-vcr` is a VCR.py-style framework specifically for MCP. Per the project README: _"Agent VCR gives teams a way to test MCP: record client-server traffic into .vcr cassettes, replay it in tests and CI."_ ([agent-vcr on GitHub](https://github.com/Jarvis2021/agent-vcr))

```python
import agent_vcr

@agent_vcr.use_cassette("tests/cassettes/search_flow.vcr")
def test_search_against_recorded_mcp():
    # All MCP JSON-RPC traffic is intercepted and served from the cassette
    result = my_agent.run("search for X")
    assert "X" in result.output
```

First run hits the real MCP server and records. Subsequent runs replay from the cassette. Commit cassettes to git.

`[UNVERIFIED]` - `agent-vcr` is third-party and not Anthropic/Google-blessed; verify maturity before relying on it for a critical CI gate.

### 7.3 Vanilla `vcrpy` for HTTP MCP servers

If the MCP server speaks HTTP/SSE (not stdio), plain `vcrpy` works:

```python
import vcr

@vcr.use_cassette("tests/cassettes/mcp_http.yaml")
def test_http_mcp():
    ...
```

References: [vcrpy on GitHub](https://github.com/kevin1024/vcrpy); [agent-vcr on GitHub](https://github.com/Jarvis2021/agent-vcr); [Show HN: mcp-recorder](https://news.ycombinator.com/item?id=47274100).

---

## 8. Property-based testing (hypothesis)

Hypothesis generates inputs and shrinks failing cases. The win for agent code: fuzz tool inputs and prompt-template inputs to catch edge cases human-curated examples miss.

### 8.1 Pydantic + hypothesis

Pydantic registers constrained types with Hypothesis automatically, so `from_type()` works on most Pydantic models out of the box ([hypothesis third-party extensions](https://hypothesis.readthedocs.io/en/latest/extensions.html); [pydantic discussion #2379](https://github.com/pydantic/pydantic/discussions/2379)):

```python
from hypothesis import given, strategies as st
from my_agent.schemas import ToolInput

@given(st.from_type(ToolInput))
def test_tool_input_roundtrip(inp: ToolInput):
    """Any valid ToolInput should round-trip through JSON."""
    serialized = inp.model_dump_json()
    restored = ToolInput.model_validate_json(serialized)
    assert restored == inp
```

### 8.2 Fuzzing tool inputs

```python
@given(query=st.text(min_size=1, max_size=500))
def test_search_tool_never_raises(query):
    result = search(query)
    assert isinstance(result, dict)
    assert "results" in result
```

This catches: empty strings, weird unicode, very long strings, bytes-in-string, etc.

### 8.3 Prompt template invariants

```python
@given(name=st.text(), task=st.text())
def test_prompt_template_renders(name, task):
    prompt = SYSTEM_PROMPT_TEMPLATE.render(name=name, task=task)
    assert "{{" not in prompt  # no unrendered placeholders
    assert "{{" not in prompt and "}}" not in prompt
    assert len(prompt) < MAX_PROMPT_CHARS
```

### 8.4 Settings

Hypothesis tests can be slow. Tune:

```python
from hypothesis import settings, HealthCheck

settings.register_profile("ci", max_examples=200, deadline=500)
settings.register_profile("dev", max_examples=20, deadline=200)
settings.load_profile("ci" if os.getenv("CI") else "dev")
```

Reference: [Hypothesis docs](https://hypothesis.readthedocs.io); [hypothesis strategies](https://hypothesis.readthedocs.io/en/latest/strategies.html).

---

## 9. Coverage strategy

### 9.1 pytest-cov configuration

`pyproject.toml`:

```toml
[tool.coverage.run]
source = ["my_agent"]
branch = true
omit = [
    "*/__init__.py",
    "*/migrations/*",
    "*/tests/*",
    "*/conftest.py",
]

[tool.coverage.report]
fail_under = 80
show_missing = true
skip_covered = false
exclude_lines = [
    "pragma: no cover",
    "raise NotImplementedError",
    "if TYPE_CHECKING:",
    "if __name__ == .__main__.:",
]

[tool.coverage.html]
directory = "htmlcov"
```

Run with:

```bash
pytest --cov --cov-report=term-missing --cov-report=xml --cov-fail-under=80
```

Per the [pytest-cov docs](https://pytest-cov.readthedocs.io/en/latest/config.html), `--cov-fail-under` exits non-zero if total coverage falls below the threshold, which CI uses to fail the build.

### 9.2 Branch vs line coverage

Branch coverage detects untested if/else paths that line coverage misses. Enable with `branch = true` in `[tool.coverage.run]`. The cost: ~10% slower test runs. Worth it.

### 9.3 Thresholds

- 80% overall (the common default).
- 100% on critical paths via path-specific thresholds or pre-commit gates: auth, secrets handling, payment-equivalent operations, prompt injection defenses.
- 0% requirement on `__main__.py` and CLI entrypoints (excluded).

### 9.4 Exclusions

- `__init__.py` (usually just re-exports).
- Type stubs (`.pyi`).
- `if TYPE_CHECKING:` blocks.
- Defensive `raise NotImplementedError` lines.

Reference: [pytest-cov 7.x docs](https://pytest-cov.readthedocs.io/en/latest/config.html).

---

## 10. Testing the frontend (Vitest + RTL)

For a Next.js 14+ frontend on Cloud Run, Vitest + React Testing Library is the de-facto unit test stack as of 2026 ([Next.js Vitest guide](https://nextjs.org/docs/app/guides/testing/vitest)).

### 10.1 Setup

`vitest.config.ts`:

```ts
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "happy-dom", // faster than jsdom for most cases
    globals: true,
    setupFiles: ["./tests/setup.ts"],
    coverage: {
      provider: "v8",
      reporter: ["text", "html", "lcov"],
      thresholds: { lines: 80, branches: 75, functions: 80, statements: 80 },
    },
  },
  resolve: {
    alias: { "@": path.resolve(__dirname, "./src") },
  },
});
```

`tests/setup.ts`:

```ts
import "@testing-library/jest-dom/vitest";
import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";

afterEach(() => cleanup());
```

### 10.2 RTL patterns

Test what the user sees, not implementation:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AttackButton } from "@/components/AttackButton";

test("clicking attack button triggers callback", async () => {
  const onAttack = vi.fn();
  render(<AttackButton onAttack={onAttack} />);
  await userEvent.click(screen.getByRole("button", { name: /attack/i }));
  expect(onAttack).toHaveBeenCalledOnce();
});
```

Query priority (per RTL guidance): `getByRole` > `getByLabelText` > `getByText` > `getByTestId` (last resort).

### 10.3 Mocking Next.js navigation

Server Components and `next/navigation` hooks need mocks:

```ts
import { vi } from "vitest";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
  usePathname: () => "/",
  useSearchParams: () => new URLSearchParams(),
}));
```

### 10.4 Server Components caveat

Per the Next.js Vitest docs: _"Since async Server Components are new to the React ecosystem, Vitest currently does not support them... we recommend using E2E tests for async components."_ ([Next.js testing guide](https://nextjs.org/docs/app/guides/testing/vitest))

So: sync Server Components and all Client Components in Vitest; async Server Components in Playwright E2E.

References: [Next.js Vitest guide](https://nextjs.org/docs/app/guides/testing/vitest); [Vitest docs](https://vitest.dev/guide/); [React Testing Library](https://testing-library.com/docs/react-testing-library/intro/).

---

## 11. Visual regression testing

### 11.1 Playwright `toHaveScreenshot`

Per the [Playwright snapshot docs](https://playwright.dev/docs/test-snapshots), `toHaveScreenshot()` captures and compares PNGs using pixelmatch.

```ts
// tests/visual/landing.spec.ts
import { test, expect } from "@playwright/test";

test.describe("landing page visuals", () => {
  test("hero section matches baseline", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("section.hero")).toHaveScreenshot("hero.png", {
      maxDiffPixelRatio: 0.02,
      threshold: 0.2,
      animations: "disabled",
    });
  });
});
```

### 11.2 Diff thresholds

- `threshold` (0.0-1.0) - per-pixel YIQ color-space tolerance. Default 0.2 catches most real changes while ignoring anti-aliasing noise.
- `maxDiffPixels` - absolute pixel count budget.
- `maxDiffPixelRatio` (0.0-1.0) - ratio of differing pixels to total. 0.01-0.05 is a typical band.

Project-wide defaults in `playwright.config.ts`:

```ts
export default defineConfig({
  expect: {
    toHaveScreenshot: {
      maxDiffPixelRatio: 0.02,
      threshold: 0.2,
      animations: "disabled",
    },
  },
});
```

### 11.3 Update workflow

```bash
# After an intentional visual change
pnpm exec playwright test --update-snapshots
# Then commit the updated PNGs alongside the code change
```

CI must run with the same browser version and platform as the baseline was generated against, otherwise font-rendering and subpixel-AA differences cause endless flakes. Standard practice: pin Playwright version, run on the Playwright Docker image both locally and in CI.

### 11.4 `sahil-visual-loop` integration

The `sahil-visual-loop` skill (at `/Users/abu/.claude/skills/sahil-visual-loop`) wires a screenshot validation loop that goes beyond pixel diffing: a fresh-context Opus 4.7 vision reviewer scores the rendered UI against an immutable anchor screenshot, with structured slop-detection output. Key constraints from that skill's SKILL.md:

- **Anchor is immutable.** `screenshots/anchor/*.png` is captured day-0 from a reference product and never overwritten.
- **Three viewports.** Mobile / tablet / desktop, captured headlessly.
- **Hook-driven.** A `PostToolUse` hook fires on every Edit/Write touching `app/**`, `components/**`, `*.tsx`.
- **CLI, not MCP.** Playwright runs as CLI for cost reasons; MCP loads ~27K tokens just to register tools.
- **Vision review via Anthropic SDK directly**, not Claude Code's Read tool (image support there is unreliable per claude-code#35866).
- **Verdict thresholds.** `slop_score ≤ 2 AND blocking_count == 0` → `ok`; 3-6 → `needs-fix`; ≥7 → `slop`.

The loop is complementary to Playwright `toHaveScreenshot()` - pixel diff catches _unintended_ visual changes; the vision reviewer catches _intended-but-slop_ design output.

References: [Playwright snapshots](https://playwright.dev/docs/test-snapshots); [Playwright visual regression guide](https://playwright.dev/docs/test-snapshots#visual-comparisons); `/Users/abu/.claude/skills/sahil-visual-loop/SKILL.md`.

---

## 12. End-to-end testing against deployed Cloud Run

### 12.1 Configuration

Playwright takes a `baseURL` per project. Drive it from env:

```ts
// playwright.config.ts
export default defineConfig({
  projects: [
    {
      name: "local",
      use: { baseURL: "http://localhost:3000" },
    },
    {
      name: "staging",
      use: {
        baseURL: process.env.STAGING_URL ?? "https://staging-xxx.run.app",
      },
    },
  ],
});
```

Then `pnpm exec playwright test --project=staging`.

### 12.2 Authentication for the demo URL

Cloud Run can be public or behind IAM. If public: nothing to do. If behind IAM auth:

- Generate an ID token via `gcloud auth print-identity-token` and pass as `Authorization: Bearer <token>` header.
- Use Playwright's `storageState` to persist a logged-in session across tests.

```ts
import { test as base } from "@playwright/test";

export const test = base.extend({
  authenticatedPage: async ({ page }, use) => {
    const idToken = process.env.GCP_ID_TOKEN!;
    await page.setExtraHTTPHeaders({ Authorization: `Bearer ${idToken}` });
    await use(page);
  },
});
```

### 12.3 Smoke tests

The minimum bar:

```ts
test("homepage loads under 3s", async ({ page }) => {
  const start = Date.now();
  const response = await page.goto("/");
  expect(response?.status()).toBe(200);
  expect(Date.now() - start).toBeLessThan(3000);
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
});

test("attack button triggers a network call", async ({ page }) => {
  await page.goto("/");
  const responsePromise = page.waitForResponse((r) =>
    r.url().includes("/api/attack"),
  );
  await page.getByRole("button", { name: /attack/i }).click();
  const response = await responsePromise;
  expect(response.status()).toBe(200);
});
```

### 12.4 Full-flow tests

Exercise the happy path through the whole stack: Next.js → ADK agent on Cloud Run → Phoenix telemetry. Assert the UI updates (e.g. a cascade-flip animation appears) AND that a Phoenix trace materialized (via the Phoenix API).

```ts
test("attack flow renders animation and produces trace", async ({
  page,
  request,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: /attack/i }).click();
  await expect(page.locator(".cascade-flip")).toBeVisible({ timeout: 10000 });
  // Verify the backend trace exists
  const trace = await request.get(
    `${PHOENIX_URL}/v1/spans?project=staging&limit=1`,
  );
  expect(trace.ok()).toBeTruthy();
});
```

References: [Playwright authentication](https://playwright.dev/docs/auth); [Playwright CI](https://playwright.dev/docs/ci); [Checkly auth guide](https://www.checklyhq.com/docs/learn/playwright/authentication/).

---

## 13. Performance + load testing (lightweight)

For a hackathon, the question is: _does the demo URL survive a judge clicking around?_ Anything beyond that is gold-plating.

### 13.1 locust

`locust` lets you write a load test in Python. Per the [locust docs](https://docs.locust.io/en/stable/what-is-locust.html), it uses gevent for high-concurrency user simulation on a single machine.

```python
# locustfile.py
from locust import HttpUser, task, between

class DemoUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def view_landing(self):
        self.client.get("/")

    @task(1)
    def trigger_attack(self):
        self.client.post("/api/attack", json={"target": "demo"})
```

Run headless:

```bash
locust -f locustfile.py --headless --users 50 --spawn-rate 5 --run-time 2m \
       --host https://staging-xxx.run.app --html report.html
```

### 13.2 What to measure

- p50, p95, p99 latency.
- Error rate (target < 1%).
- RPS the service sustains before saturating.
- Cold-start frequency (Cloud Run min-instances trade-off).

### 13.3 When this matters for a hackathon

Mostly: pre-demo, run 60 seconds of moderate load against staging, confirm p95 < 2s and 0% errors. If the judges click while a colleague is also clicking, you don't want to discover Cloud Run autoscaling issues live.

If LLM cost is a concern, point load at endpoints that don't call Gemini (`/`, static API endpoints) rather than at the agent endpoint.

Reference: [locust docs](https://docs.locust.io/en/stable/what-is-locust.html).

---

## 14. Snapshot testing

### 14.1 Python snapshot tools

- `syrupy` - the modern pytest snapshot plugin. Supports Pydantic models, dicts, lists, custom serializers.
- `pytest-icdiff` - pretty diffs for snapshot mismatches.

```python
def test_hardening_recipe_markdown(snapshot):
    recipe = generate_hardening_recipe(probe_results=FIXTURES["probe_results"])
    assert recipe.to_markdown() == snapshot
```

Update:

```bash
pytest --snapshot-update
```

### 14.2 Snapshotting Phoenix span trees

Serialize the span tree to a canonical form (sort by start time, drop timestamps and random IDs), then snapshot:

```python
def canonicalize(spans):
    return [
        {"name": s.name, "attributes": {k: v for k, v in s.attributes.items()
                                         if not k.endswith(".id") and not k.endswith(".time")}}
        for s in sorted(spans, key=lambda s: s.start_time)
    ]

def test_span_tree(snapshot, captured_spans):
    assert canonicalize(captured_spans) == snapshot
```

### 14.3 Markdown report snapshots

For the hardening recipe artifact (or any markdown the agent produces), snapshot the rendered markdown. Diff failures are human-readable.

Reference: [syrupy](https://github.com/syrupy-project/syrupy); [pytest-icdiff](https://github.com/hjwp/pytest-icdiff).

---

## 15. CI test orchestration

### 15.1 Which tests run when

| Trigger          | Suite                                                            | Time budget |
| ---------------- | ---------------------------------------------------------------- | ----------- |
| Local pre-commit | Unit only (`-m "not online and not integration"`)                | < 30s       |
| PR open / push   | Unit + integration mocks + Vitest + lint + types                 | < 5 min     |
| PR open (smoke)  | Playwright smoke against preview Cloud Run URL                   | < 3 min     |
| Merge to main    | Full integration (real Phoenix, real Vertex) + visual regression | < 15 min    |
| Nightly          | LLM-as-judge dataset eval + load test + flake retest             | < 30 min    |
| Pre-release      | Everything + cost report + golden dataset diff                   | < 60 min    |

### 15.2 Parallel execution with pytest-xdist

```bash
pytest -n auto --dist loadfile
```

`loadfile` groups tests by file to keep fixtures cheap. For very large suites, `loadgroup` keeps tests within the same `@pytest.mark.xdist_group` together.

Per [pytest-xdist patterns](https://pytest-with-eric.com/plugins/pytest-xdist/), a 5,000-test suite often goes from 45 min to 4.5 min with `-n 16`. Watch out for shared-state flakes: parallel runs expose ordering bugs that sequential runs hide.

### 15.3 Flake detection

`pytest-rerunfailures` is a temporary bandage, not a policy. Per the [pytest flaky tests doc](https://docs.pytest.org/en/stable/explanation/flaky.html), rerunning to mask flakes obscures real bugs.

Two-tier policy:

- On PR: no reruns. Flakes block merge until fixed.
- On main / nightly: `--reruns 2 --reruns-delay 5` to keep the bus moving, but log every rerun to a flaky-test tracker.

Pin known-flaky tests with `@pytest.mark.flaky(reruns=3)` so they're explicit.

### 15.4 Artifact upload

Failed tests should leave forensics:

- Playwright traces (`use: { trace: "on-first-retry" }`).
- Screenshot diffs (`update_snapshots: 'missing'` keeps unexpected images).
- Coverage XML for codecov.
- Phoenix span exports for the failing test (write to a tmp dir, upload as workflow artifact).

GitHub Actions:

```yaml
- name: Upload Playwright report
  if: ${{ failure() }}
  uses: actions/upload-artifact@v4
  with:
    name: playwright-report
    path: playwright-report/
    retention-days: 7
```

References: [pytest-xdist docs](https://pytest-xdist.readthedocs.io/); [pytest flaky tests](https://docs.pytest.org/en/stable/explanation/flaky.html); [pytest-rerunfailures](https://github.com/pytest-dev/pytest-rerunfailures).

---

## 16. Test data management

### 16.1 `tests/fixtures/`

Static test data lives in `tests/fixtures/`:

```
tests/
  fixtures/
    eval/
      basic_search.test.json
      multi_turn_conversation.test.json
      test_config.json
    spans/
      golden_search_trace.json
    schemas/
      sample_tool_input.json
    cassettes/
      mcp_search.vcr
      gemini_429_retry.yaml
```

Anything > ~10KB or binary lives here and is referenced by path from tests, not inlined.

### 16.2 Factory pattern

For dynamic data, build factories. Either `factory_boy` for full-featured needs or a simple builder function:

```python
# tests/factories.py
def make_eval_case(*, query="hi", expected_tools=None, reference="hello"):
    return EvalCase(
        eval_id=str(uuid.uuid4()),
        conversation=Conversation(turns=[Turn(
            user_content=Content(parts=[Part(text=query)]),
            expected_tool_use=expected_tools or [],
            reference=reference,
        )])
    )
```

For Pydantic models, `polyfactory` (formerly `pydantic-factories`) auto-generates factories from schema. Cleaner than rolling your own for trivial models.

### 16.3 Phoenix trace fixtures

Capture a real trace, sanitize timestamps and IDs, commit as JSON. Use in tests as the expected output for span-tree snapshot assertions:

```python
@pytest.fixture
def golden_search_trace():
    with open("tests/fixtures/spans/golden_search_trace.json") as f:
        return json.load(f)

def test_search_produces_expected_trace(captured_spans, golden_search_trace):
    assert canonicalize(captured_spans) == golden_search_trace
```

References: [factory_boy](https://factoryboy.readthedocs.io/); [polyfactory](https://polyfactory.litestar.dev/).

---

## 17. Sources

### Core docs

- [pytest documentation](https://docs.pytest.org/en/stable/)
- [pytest-asyncio concepts](https://pytest-asyncio.readthedocs.io/en/stable/concepts.html)
- [pytest-asyncio on PyPI](https://pypi.org/project/pytest-asyncio/)
- [pytest-cov configuration](https://pytest-cov.readthedocs.io/en/latest/config.html)
- [pytest-xdist parallel execution](https://pytest-xdist.readthedocs.io/)
- [pytest flaky tests explanation](https://docs.pytest.org/en/stable/explanation/flaky.html)
- [pytest-rerunfailures](https://github.com/pytest-dev/pytest-rerunfailures)
- [Hypothesis docs](https://hypothesis.readthedocs.io/)
- [Hypothesis strategies](https://hypothesis.readthedocs.io/en/latest/strategies.html)
- [respx user guide](https://lundberg.github.io/respx/guide/)
- [respx API reference](https://lundberg.github.io/respx/api/)
- [pytest-httpx](https://github.com/Colin-b/pytest_httpx)
- [VCR.py](https://github.com/kevin1024/vcrpy)

### ADK + Gemini

- [Google ADK Python](https://github.com/google/adk-python)
- [ADK evaluate docs](https://adk.dev/evaluate/)
- [ADK evaluation codelab](https://codelabs.developers.google.com/adk-eval/instructions)
- [ADK testing & evaluation (deepwiki)](https://deepwiki.com/google/adk-samples/15.3-testing-and-evaluation)
- [adk-samples repository](https://github.com/google/adk-samples)
- [Future AGI - ADK eval guide](https://futureagi.com/blog/evaluate-google-adk-agents/)

### Phoenix observability

- [Phoenix on GitHub](https://github.com/Arize-ai/phoenix)
- [Phoenix self-hosting](https://arize.com/docs/phoenix/self-hosting)
- [Phoenix tracing quickstart (Python)](https://arize.com/docs/phoenix/tracing/llm-traces-1/quickstart-tracing-python)
- [Phoenix datasets & experiments](https://arize.com/docs/phoenix/datasets-and-experiments/quickstart-datasets)
- [Phoenix LLM-as-a-Judge](https://arize.com/docs/phoenix/evaluation/concepts-evals/llm-as-a-judge)
- [Arize blog - LLM-as-a-Judge evaluators in production](https://arize.com/blog/how-to-build-llm-as-a-judge-evaluators-that-hold-up-in-production/)
- [Phoenix ADK integration (deepwiki)](https://deepwiki.com/google/adk-samples/17.2-arize-phoenix-evaluation-integration)
- [arize-phoenix on PyPI](https://pypi.org/project/arize-phoenix/)
- [Phoenix Docker image](https://hub.docker.com/r/arizephoenix/phoenix)

### MCP testing

- [Agent VCR](https://github.com/Jarvis2021/agent-vcr)
- [agent-vcr on PyPI](https://pypi.org/project/agent-vcr/)
- [Show HN: mcp-recorder](https://news.ycombinator.com/item?id=47274100)

### Frontend testing

- [Next.js Vitest guide](https://nextjs.org/docs/app/guides/testing/vitest)
- [Vitest documentation](https://vitest.dev/guide/)
- [Vitest browser component testing](https://vitest.dev/guide/browser/component-testing)
- [React Testing Library](https://testing-library.com/docs/react-testing-library/intro/)
- [@testing-library/jest-dom](https://github.com/testing-library/jest-dom)

### Playwright + visual

- [Playwright docs](https://playwright.dev/)
- [Playwright visual comparisons](https://playwright.dev/docs/test-snapshots)
- [Playwright SnapshotAssertions API](https://playwright.dev/docs/api/class-snapshotassertions)
- [Playwright authentication](https://playwright.dev/docs/auth)
- [Playwright CI](https://playwright.dev/docs/ci)
- [BrowserStack - Playwright snapshot testing 2026](https://www.browserstack.com/guide/playwright-snapshot-testing)
- [Checkly - Visual monitoring with Playwright](https://www.checklyhq.com/docs/detect/synthetic-monitoring/browser-checks/visual-regressions/)

### Load testing

- [Locust](https://locust.io/)
- [Locust docs](https://docs.locust.io/en/stable/what-is-locust.html)
- [Locust on GitHub](https://github.com/locustio/locust)

### Snapshot testing

- [syrupy](https://github.com/syrupy-project/syrupy)
- [pytest-icdiff](https://github.com/hjwp/pytest-icdiff)
- [factory_boy](https://factoryboy.readthedocs.io/)
- [polyfactory](https://polyfactory.litestar.dev/)

### Local references

- `/Users/abu/.claude/skills/sahil-visual-loop/SKILL.md` - Sahil's visual validation loop scaffolding skill.
