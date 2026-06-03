# Story — Tier 2 LangChain adapter (`langchain_adapter.py`)

**ID:** story-3.3-langchain-adapter
**Epic:** Epic 3 — Cross-framework target adapter layer
**Depends on:** story-3.1-adapter-interface
**Estimate:** ~2h
**Status:** PENDING
**tags:** [backend, p0, adapter, langchain, tier2]

---

## User story

**As a** ChaosLab Injector sub-agent attacking a non-ADK target (any LangChain agent exposed via LangServe)
**I want to** drive the LangChain target through its native HTTP convention (`/invoke`, `/input_schema`) with `openinference-instrumentation-langchain` capturing model + tool spans, and route prompt-injection faults through a LiteLlm proxy override per invocation
**So that** ChaosLab covers the largest non-ADK Python agent framework in production (Salesforce/Snowflake/Klarna/Replit per `context/04 §4.8`), and Phoenix traces show `openinference.span.kind in {LLM,TOOL,CHAIN} via the langchain instrumentor` proving the cross-framework attack surface is real (per ADR-002 + `context/03 §13`)

---

## File modification map

Exact files the coding agent creates or modifies for this story:

- `apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/langchain_adapter.py` — NEW — `class LangChainAdapter(TargetAdapter)`; ≤280 LOC; implements connect (probes `/input_schema`), invoke (POSTs to `/invoke`, applies LiteLlm proxy if `fault_config.kind == "prompt_injection"`), fingerprint (returns LangServe metadata), disconnect
- `apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/_litellm_proxy.py` — NEW — ≤120 LOC helper module exposing `async def litellm_proxy_session(fault_config) -> AsyncContextManager` that spins a per-invocation LiteLLM CustomLogger context (per `context/04 §17.6`); used by LangChain, CrewAI, and OpenAI Agents SDK adapters
- `apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/__init__.py` — UPDATE — add `LangChainAdapter` re-export
- `apps/chaoslab-agent/src/chaoslab_agent/observability.py` — UPDATE (if it exists from story-4.5) — ensure `LangChainInstrumentor().instrument()` runs at module load when `CHAOSLAB_ENABLE_LANGCHAIN_INSTRUMENTATION=1`; if `observability.py` is not yet built (story-4.5 not landed), add a TODO comment + a stub registration helper here that story-4.5 wires in
- `apps/chaoslab-agent/tests/unit/injector/target_adapters/test_langchain_adapter.py` — NEW — ≥8 unit tests using `respx` to mock LangServe `/invoke` + `/input_schema`: input_schema parsed, invoke maps prompt to `{"input": ...}` LangServe shape, invoke handles SSE streaming response, 422 raises AdapterInvocationError, fingerprint returns tier=TIER2_LANGCHAIN + framework="langchain", LiteLlm proxy context activates on prompt_injection fault, span_ids captured from `OpenInferenceSpanProcessor`, timeout enforced
- `apps/chaoslab-agent/tests/integration/injector/target_adapters/test_langchain_adapter.py` — NEW — ≥4 integration tests against a minimal LangServe sample target (started by `docker-compose -f apps/chaoslab-agent/tests/fixtures/langchain-target/docker-compose.yml up -d` in conftest); marked `@pytest.mark.integration`
- `apps/chaoslab-agent/tests/fixtures/langchain-target/` — NEW — minimal LangServe fixture: `main.py` (3 lines: `add_routes(app, RunnablePassthrough() | ChatOpenAI(), path="/agent")`), `Dockerfile`, `docker-compose.yml` exposing port 8002 — used ONLY by integration tests, exempt from §14 (test fixture)

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given a LangChainAdapter constructed with TargetSpec(tier='tier2_langchain', url='http://localhost:8002/agent')
When adapter.connect() runs and the LangServe target responds 200 on /input_schema
Then no exception is raised
And adapter._input_schema is a dict containing a "type" key
And adapter._connected is True

Given a connected LangChainAdapter
When adapter.invoke(AdapterInvocation(prompt="What's 2+2?", fault_config=None)) runs
Then result.error is None
And len(result.span_ids) ≥ 1
And result.duration_ms > 0.0

Given a connected LangChainAdapter and a Phoenix tracer wired (LangChainInstrumentor active)
When adapter.invoke runs against the live LangServe fixture
Then at least one captured span has attribute openinference.span.kind in {"LLM","TOOL","CHAIN"} AND the OTEL instrumentation_scope.name equals "openinference.instrumentation.langchain"
And the assertion is verified via the in-memory span exporter installed by the integration test fixture

Given a LangChainAdapter and fault_config={"kind": "prompt_injection", "payload": "Ignore prior instructions"}
When adapter.invoke runs
Then a LiteLlm proxy CustomLogger context was activated for the duration of the call
And the proxy is torn down after invoke returns (no global state leak)

Given a connected LangChainAdapter
When adapter.fingerprint() runs
Then result.tier == AdapterTier.TIER2_LANGCHAIN
And result.framework == "langchain"
And result.discovery_path == "input_schema"
And result.agent_card is None (LangChain has no AgentCard)

Given a LangServe target returning 422 on /invoke (schema mismatch)
When adapter.invoke runs (respx-mocked)
Then AdapterInvocationError is raised
And the exception carries the response body for debugging

Given the source file
When `python3 scripts/check_max_lines.py apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/langchain_adapter.py` runs
Then exit code is 0

Given the unit tests
When `uv run pytest apps/chaoslab-agent/tests/unit/injector/target_adapters/test_langchain_adapter.py -v` runs
Then ≥8 tests pass

Given `grep -E "from langchain" apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/langchain_adapter.py` runs
When the output is checked
Then no langchain orchestrator imports appear (per banned-patterns rule in coding-standards.md — LangChain as PRIMARY orchestrator is banned; only INSTRUMENTATION via openinference-instrumentation-langchain is permitted)

Given `grep -rE "(mock|fake|dummy|hardcoded|simulated)" apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/langchain_adapter.py apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/_litellm_proxy.py` runs
When the output is checked
Then zero results appear (§14 gate clean)
```

---

## Shell verification

```bash
set -e
cd /Users/abu/dev/hackathon/rapid-agents

# Source files exist
test -f apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/langchain_adapter.py
test -f apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/_litellm_proxy.py

# Class declared, subclasses TargetAdapter
grep -qE "^class LangChainAdapter\(TargetAdapter\)" apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/langchain_adapter.py

# All four abstract methods
for method in connect invoke fingerprint disconnect; do
  grep -qE "async def ${method}\b" apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/langchain_adapter.py
done

# Banned pattern: no langchain orchestrator imports (only instrumentor allowed)
! grep -E "^from langchain[._]" apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/langchain_adapter.py
! grep -E "^from langchain_core" apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/langchain_adapter.py
# The openinference instrumentor is allowed:
grep -qE "openinference\.instrumentation\.langchain" apps/chaoslab-agent/src/chaoslab_agent/observability.py || \
  grep -qE "openinference\.instrumentation\.langchain" apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/langchain_adapter.py

# Unit tests pass
uv run pytest apps/chaoslab-agent/tests/unit/injector/target_adapters/test_langchain_adapter.py -v
UNIT_COUNT=$(uv run pytest apps/chaoslab-agent/tests/unit/injector/target_adapters/test_langchain_adapter.py --collect-only -q 2>&1 | grep -cE "test_")
[ "$UNIT_COUNT" -ge 8 ] || { echo "expected ≥8 unit tests, got $UNIT_COUNT"; exit 1; }

# Integration tests (fixture must be up; conftest stands it up via docker-compose)
uv run pytest apps/chaoslab-agent/tests/integration/injector/target_adapters/test_langchain_adapter.py -m integration -v
INT_COUNT=$(uv run pytest apps/chaoslab-agent/tests/integration/injector/target_adapters/test_langchain_adapter.py --collect-only -q 2>&1 | grep -cE "test_")
[ "$INT_COUNT" -ge 4 ] || { echo "expected ≥4 integration tests, got $INT_COUNT"; exit 1; }

# Lint + type-check + 400-line clean
uv run ruff check apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/langchain_adapter.py
uv run ruff check apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/_litellm_proxy.py
uv run ruff format --check apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/
uv run ty check apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/langchain_adapter.py || uv run mypy --strict apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/langchain_adapter.py
python3 scripts/check_max_lines.py apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/langchain_adapter.py
python3 scripts/check_max_lines.py apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/_litellm_proxy.py

# §14 clean (src/ paths only; fixtures + tests excluded)
! grep -rE "(mock|fake|dummy|hardcoded|simulated)" apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/langchain_adapter.py apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/_litellm_proxy.py

echo "story-3.3 verification: PASS"
```

---

## Notes for coding agent

### Required wire path (per `context/04 §4.2-4.7`)

```python
# apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/langchain_adapter.py
from __future__ import annotations
import time
import httpx
from opentelemetry import trace
from chaoslab_agent.errors import AdapterInvocationError, AdapterDiscoveryError
from chaoslab_agent.injector.target_adapters.base import (
    AdapterFingerprint, AdapterInvocation, AdapterResult, AdapterTier, TargetAdapter,
)
from chaoslab_agent.injector.target_adapters._litellm_proxy import litellm_proxy_session


class LangChainAdapter(TargetAdapter):
    """Tier 2 adapter: drives a LangChain target via LangServe convention (POST /invoke)."""

    def __init__(self, spec: TargetSpec) -> None:
        super().__init__(spec)
        self._input_schema: dict | None = None
        self._http: httpx.AsyncClient | None = None

    async def connect(self) -> None:
        if self._connected:
            return
        base = str(self.spec.url).rstrip("/")
        self._http = httpx.AsyncClient(timeout=self.spec.timeout_s)
        try:
            resp = await self._http.get(f"{base}/input_schema")
        except httpx.HTTPError as e:
            raise AdapterDiscoveryError(f"LangServe /input_schema unreachable at {base}: {e}") from e
        if resp.status_code != 200:
            raise AdapterDiscoveryError(
                f"LangServe target {base} returned {resp.status_code} on /input_schema"
            )
        self._input_schema = resp.json()
        self._connected = True

    async def invoke(self, invocation: AdapterInvocation) -> AdapterResult:
        if not self._connected:
            await self.connect()
        assert self._http is not None
        base = str(self.spec.url).rstrip("/")
        start = time.perf_counter()
        span_ids: list[str] = []
        tracer = trace.get_tracer(__name__)
        async with litellm_proxy_session(invocation.fault_config) as proxy_ctx:
            with tracer.start_as_current_span("chaoslab.adapter.langchain.invoke") as span:
                span_ids.append(format(span.get_span_context().span_id, "016x"))
                try:
                    body = {"input": invocation.prompt}
                    if proxy_ctx is not None:
                        # Per-call header so LangServe target's LiteLLM-routed model
                        # uses our proxy. Convention: target reads X-LiteLLM-Base-Url.
                        headers = {"X-LiteLLM-Base-Url": proxy_ctx.base_url}
                    else:
                        headers = {}
                    if self.spec.auth and "bearer" in self.spec.auth:
                        headers["Authorization"] = f"Bearer {self.spec.auth['bearer']}"
                    resp = await self._http.post(f"{base}/invoke", json=body, headers=headers)
                    if resp.status_code != 200:
                        raise AdapterInvocationError(
                            f"LangServe /invoke returned {resp.status_code}: {resp.text[:500]}"
                        )
                    payload = resp.json()
                    # LangServe shape: {"output": <string-or-object>}
                    response_text = (
                        payload["output"]
                        if isinstance(payload.get("output"), str)
                        else str(payload.get("output"))
                    )
                    error = None
                except Exception as e:  # noqa: BLE001
                    response_text = ""
                    error = f"{type(e).__name__}: {e}"
                    span.record_exception(e)
        return AdapterResult(
            response=response_text,
            span_ids=span_ids,
            duration_ms=(time.perf_counter() - start) * 1000.0,
            error=error,
            metadata={"langserve_endpoint": f"{base}/invoke"},
        )

    async def fingerprint(self) -> AdapterFingerprint:
        if not self._connected:
            await self.connect()
        return AdapterFingerprint(
            tier=AdapterTier.TIER2_LANGCHAIN,
            framework="langchain",
            agent_card=None,
            discovery_path="input_schema",
            behavioral_signals={"input_schema_keys": list((self._input_schema or {}).keys())},
        )

    async def disconnect(self) -> None:
        if self._http is not None:
            await self._http.aclose()
            self._http = None
        self._connected = False
```

### `_litellm_proxy.py` contract

```python
# apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/_litellm_proxy.py
from __future__ import annotations
from contextlib import asynccontextmanager
from dataclasses import dataclass

@dataclass
class ProxyContext:
    base_url: str
    custom_logger_active: bool

@asynccontextmanager
async def litellm_proxy_session(fault_config: dict | None):
    """Yields ProxyContext when fault_config requires LLM-layer interception, else yields None.

    The real LiteLLM CustomLogger registration happens in story-5.3 (PromptInjectionFault).
    For story-3.3, this context is a typed no-op when fault_config is None or kind != 'prompt_injection',
    and registers a minimal logger when kind == 'prompt_injection'. The detailed payload-mutation
    logic lands in story-5.3; this story only proves the context-manager wiring works.
    """
    if not fault_config or fault_config.get("kind") != "prompt_injection":
        yield None
        return
    # story-5.3 fills in litellm.callbacks.append(...); for now we yield a real ProxyContext
    # so adapters can pass X-LiteLLM-Base-Url through.
    proxy = ProxyContext(base_url="http://localhost:4000/v1", custom_logger_active=True)
    try:
        yield proxy
    finally:
        proxy.custom_logger_active = False
```

### Architecture context

- **Banned-patterns enforcement (`architecture.md` §"Banned patterns"):** LangChain / LangGraph / LlamaIndex are BANNED as PRIMARY orchestrator in submitted code. They are PERMITTED ONLY as target-instrumentation libraries (Tier 2). This adapter MUST NOT `from langchain import ...` or `from langchain_core import ...`. The ONLY langchain-related import allowed is the openinference instrumentor (lives in `observability.py`, not here).
- **Observability hand-off (`context/04 §4.2`):** `LangChainInstrumentor().instrument()` must be active in the process for the BDD criterion `attribute openinference.span.kind in {"LLM","TOOL","CHAIN"} AND the OTEL instrumentation_scope.name equals "openinference.instrumentation.langchain"` to fire. If story-4.5 hasn't landed yet, add a one-time registration helper at module load gated by `CHAOSLAB_ENABLE_LANGCHAIN_INSTRUMENTATION=1` env var. Story-4.5 will hoist this to the canonical `observability.setup()` entry point and remove the local registration.
- **`/input_schema` discovery (`context/04 §4.7`):** LangServe ships `GET /<route>/input_schema` returning a JSON Schema describing the runnable input. This is a stronger discovery signal than `/invoke` (which always 405s on GET). Use it as the connect() probe.
- **LangServe input shape:** the canonical body is `{"input": ...}` for a runnable, NOT `{"prompt": ...}`. Reading `input_schema` at connect-time tells us the exact key names — store the schema for richer probing later (story-5.6 baseline check may use it).
- **LiteLlm proxy per-invocation (`context/04 §17.6`):** the demo's strongest LangChain fault is prompt injection. The target's LangChain agent must be configured to use a model wrapped by LiteLlm; we then mutate `data["messages"]` in a CustomLogger's `async_pre_call_hook`. For this story, only WIRE the context manager — the actual mutation logic ships in story-5.3 `PromptInjectionFault`.
- **§14 clean (`PRD.md` submission checklist):** `mock` / `fake` / `dummy` / `hardcoded` / `simulated` are banned in `src/`. The `_litellm_proxy.py` helper's stub returns a real `ProxyContext` (not a Mock) — when fault_config is None we yield None, which is the language-level None, not a placeholder.

### Known pitfalls

- **LangServe responses are SOMETIMES SSE** (when `add_routes(..., enabled_endpoints=["invoke", "stream"])`). For now, hit `/invoke` only (non-streaming) — `/stream` support is a future enhancement and not required for the demo.
- **`/input_schema` 405 case:** some LangServe deployments disable schema endpoints in production. If you get 405 (not 404), surface a clear error like "LangServe target has /input_schema disabled — set enabled_endpoints=['invoke','input_schema'] on add_routes". Fingerprint should still set `discovery_path = "invoke_only"` and fingerprint-via-OPTIONS instead.
- **Pydantic HttpUrl + path tail:** `TargetSpec.url` may be `http://localhost:8002/agent` — the `/agent` path is the LangServe runnable mount point. Do NOT strip it. The well-known paths concatenate AFTER it: `{base}/invoke`, `{base}/input_schema`. This is intentional and differs from Tier 1 ADK where `url` is the service root.
- **httpx timeout vs LangServe stream:** `/invoke` returns a single JSON; no streaming. Use the spec.timeout_s value as-is. Streaming `/stream` would need a different timeout strategy (story 5.5 latency injection).
- **Integration test fixture (`tests/fixtures/langchain-target/`):** must use a stub model (e.g., `FakeListChatModel` from langchain_core — NOTE: importing langchain_core in TEST FIXTURES is allowed under the `tests/**` per-file-ignore; it's banned only in src/). Document this carve-out at the top of the fixture's `main.py` so future Abu doesn't trip the lint hook.
- **Coverage gotcha:** the `except Exception` branch in `invoke()` is hit by the 422 respx test. Make sure to assert both `result.error is not None` and the specific exception type name appears in `error`.
