# Story — Tier 2 OpenAI Agents SDK adapter (`openai_sdk_adapter.py`)

**ID:** story-3.5-openai-sdk-adapter
**Epic:** Epic 3 — Cross-framework target adapter layer
**Depends on:** story-3.1-adapter-interface
**Estimate:** ~1.5h
**Status:** PENDING
**tags:** [backend, p0, adapter, openai-sdk, tier2]

---

## User story

**As a** ChaosLab Injector sub-agent attacking an OpenAI Agents SDK target (the SDK OpenAI's keynotes promote — Stripe, Box, Notion, Coinbase per `context/04 §10.8`)
**I want to** drive the target via its HTTP wrapping convention (`POST /run`), leveraging the SDK's NATIVE OpenInference span emission (per `context/04 §10.1`) — no instrumentor patching required — and inject faults at the `function_tool` invocation surface via per-call decorator registration
**So that** Phoenix traces show the canonical Agent → Tool → LLM ≥3-span topology proving the cross-framework attack worked, with minimal adapter glue (this SDK is the cleanest of all Tier 2 frameworks)

---

## File modification map

Exact files the coding agent creates or modifies for this story:

- `apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/openai_sdk_adapter.py` — NEW — `class OpenAISDKAdapter(TargetAdapter)`; ≤220 LOC; connect (probes `/agents` listing endpoint convention), invoke (POSTs to `/run` with `{"input": prompt}`), fingerprint, disconnect; registers per-call fault hook via `/hooks/function_tool` webhook (same pattern as CrewAI adapter)
- `apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/__init__.py` — UPDATE — add `OpenAISDKAdapter` re-export
- `apps/chaoslab-agent/src/chaoslab_agent/observability.py` — UPDATE (or stub if story-4.5 not landed) — register `OpenAIAgentsInstrumentor().instrument()` per `context/04 §10.2` gated by `CHAOSLAB_ENABLE_OPENAI_SDK_INSTRUMENTATION=1` env var
- `apps/chaoslab-agent/tests/unit/injector/target_adapters/test_openai_sdk_adapter.py` — NEW — ≥7 unit tests using respx: `/agents` discovery returns agent metadata, `/run` POST shape correct, fingerprint returns tier=TIER2_OPENAI_SDK, framework="openai-agents", span_ids captured from current OTEL context, fault_config of kind="malformed_tool_output" registers hook, 422 raises AdapterInvocationError, disconnect releases httpx client
- `apps/chaoslab-agent/tests/integration/injector/target_adapters/test_openai_sdk_adapter.py` — NEW — ≥3 integration tests against a minimal OpenAI Agents SDK fixture; verifies in-memory span exporter captures ≥3 spans matching the Agent → Tool → LLM pattern (per `context/04 §10.1`)
- `apps/chaoslab-agent/tests/fixtures/openai-sdk-target/` — NEW — minimal Agents SDK fixture: `main.py` (`Agent(name="...", tools=[function_tool(weather)])` + FastAPI `POST /run`), `Dockerfile`, `docker-compose.yml` on port 8004

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given an OpenAISDKAdapter constructed with TargetSpec(tier='tier2_openai_sdk', url='http://localhost:8004')
When adapter.connect() runs and the target responds 200 on /agents with [{"name": "weather-agent", "tools": ["weather"]}]
Then no exception is raised
And adapter._connected is True
And adapter._agents_info is a non-empty list

Given a connected OpenAISDKAdapter
When adapter.invoke(AdapterInvocation(prompt="What's the weather in SF?")) runs against the live fixture with OpenAIAgentsInstrumentor active
Then result.error is None
And len(result.span_ids) ≥ 3
And the in-memory Phoenix exporter shows spans matching: one with openinference.span.kind=="AGENT", one with kind=="TOOL", one with kind=="LLM"

Given a connected OpenAISDKAdapter
When adapter.fingerprint() runs
Then result.tier == AdapterTier.TIER2_OPENAI_SDK
And result.framework == "openai-agents"
And result.discovery_path == "agents_listing"
And result.behavioral_signals["agent_count"] >= 1

Given an OpenAISDKAdapter and fault_config={"kind": "malformed_tool_output", "tool_name": "weather"}
When adapter.invoke runs
Then POST /hooks/function_tool was called once before /run
And DELETE /hooks/function_tool/{id} was called once after /run returned

Given a target returning 422 on /run with body {"detail": "input required"}
When adapter.invoke runs (respx-mocked)
Then AdapterInvocationError is raised carrying "422" and "input required"

Given the source file
When `python3 scripts/check_max_lines.py apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/openai_sdk_adapter.py` runs
Then exit code is 0

Given the unit tests
When `uv run pytest apps/chaoslab-agent/tests/unit/injector/target_adapters/test_openai_sdk_adapter.py -v` runs
Then ≥7 tests pass

Given `grep -E "^from openai" apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/openai_sdk_adapter.py` runs
When the output is checked
Then no `openai`/`anthropic`/`claude` runtime LLM imports appear (per banned-patterns: Claude/OpenAI/Anthropic SDKs as runtime LLM are banned in submitted code; the openinference instrumentor `openinference.instrumentation.openai_agents` is permitted and lives in observability.py only)

Given `grep -rE "(mock|fake|dummy|hardcoded|simulated)" apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/openai_sdk_adapter.py` runs
When the output is checked
Then zero results appear (§14 gate clean)
```

---

## Shell verification

```bash
set -e
cd /Users/abu/dev/hackathon/rapid-agents

# Source file exists
test -f apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/openai_sdk_adapter.py

# Class declared, subclasses TargetAdapter
grep -qE "^class OpenAISDKAdapter\(TargetAdapter\)" apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/openai_sdk_adapter.py

# All four abstract methods
for method in connect invoke fingerprint disconnect; do
  grep -qE "async def ${method}\b" apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/openai_sdk_adapter.py
done

# Banned-patterns: no openai/anthropic/claude SDK imports in this adapter (only instrumentor in observability.py)
! grep -E "^(from openai|import openai|from anthropic|import anthropic|from claude)" apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/openai_sdk_adapter.py

# Re-export wired
uv run python -c "from chaoslab_agent.injector.target_adapters import OpenAISDKAdapter; print('ok')"

# Unit tests
uv run pytest apps/chaoslab-agent/tests/unit/injector/target_adapters/test_openai_sdk_adapter.py -v
UNIT_COUNT=$(uv run pytest apps/chaoslab-agent/tests/unit/injector/target_adapters/test_openai_sdk_adapter.py --collect-only -q 2>&1 | grep -cE "test_")
[ "$UNIT_COUNT" -ge 7 ] || { echo "expected ≥7 unit tests, got $UNIT_COUNT"; exit 1; }

# Integration tests
uv run pytest apps/chaoslab-agent/tests/integration/injector/target_adapters/test_openai_sdk_adapter.py -m integration -v
INT_COUNT=$(uv run pytest apps/chaoslab-agent/tests/integration/injector/target_adapters/test_openai_sdk_adapter.py --collect-only -q 2>&1 | grep -cE "test_")
[ "$INT_COUNT" -ge 3 ] || { echo "expected ≥3 integration tests, got $INT_COUNT"; exit 1; }

# Lint + type-check + 400-line clean
uv run ruff check apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/openai_sdk_adapter.py
uv run ruff format --check apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/openai_sdk_adapter.py
uv run ty check apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/openai_sdk_adapter.py || uv run mypy --strict apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/openai_sdk_adapter.py
python3 scripts/check_max_lines.py apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/openai_sdk_adapter.py

# §14 clean
! grep -E "(mock|fake|dummy|hardcoded|simulated)" apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/openai_sdk_adapter.py

echo "story-3.5 verification: PASS"
```

---

## Notes for coding agent

### Required wire path (per `context/04 §10`)

```python
# apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/openai_sdk_adapter.py
from __future__ import annotations
import time
from contextlib import asynccontextmanager
import httpx
from opentelemetry import trace
from chaoslab_agent.errors import AdapterInvocationError, AdapterDiscoveryError
from chaoslab_agent.injector.target_adapters.base import (
    AdapterFingerprint, AdapterInvocation, AdapterResult, AdapterTier, TargetAdapter,
)


class OpenAISDKAdapter(TargetAdapter):
    """Tier 2 adapter: drives an OpenAI Agents SDK target.

    Convention:
      GET  /agents                 -> [{"name": ..., "tools": [...]}, ...]
      POST /run                    -> body={"input": ..., "agent_name": ...} -> 200 {"output": "..."}
      POST /hooks/function_tool    -> body={"fault_config": {...}} -> 200 {"registration_id": "..."}
      DELETE /hooks/function_tool/{id}
    """

    def __init__(self, spec: TargetSpec) -> None:
        super().__init__(spec)
        self._agents_info: list[dict] | None = None
        self._http: httpx.AsyncClient | None = None

    async def connect(self) -> None:
        if self._connected:
            return
        base = str(self.spec.url).rstrip("/")
        self._http = httpx.AsyncClient(timeout=self.spec.timeout_s)
        try:
            resp = await self._http.get(f"{base}/agents")
        except httpx.HTTPError as e:
            raise AdapterDiscoveryError(f"OpenAI Agents SDK target unreachable at {base}: {e}") from e
        if resp.status_code != 200:
            raise AdapterDiscoveryError(
                f"/agents returned {resp.status_code} at {base}"
            )
        self._agents_info = resp.json()
        if not isinstance(self._agents_info, list) or len(self._agents_info) == 0:
            raise AdapterDiscoveryError(f"/agents returned empty or non-list payload at {base}")
        self._connected = True

    async def invoke(self, invocation: AdapterInvocation) -> AdapterResult:
        if not self._connected:
            await self.connect()
        assert self._http is not None
        base = str(self.spec.url).rstrip("/")
        start = time.perf_counter()
        span_ids: list[str] = []
        tracer = trace.get_tracer(__name__)

        async with self._fault_hook_context(invocation.fault_config, base):
            with tracer.start_as_current_span("chaoslab.adapter.openai_sdk.invoke") as span:
                span_ids.append(format(span.get_span_context().span_id, "016x"))
                try:
                    headers = {}
                    if self.spec.auth and "bearer" in self.spec.auth:
                        headers["Authorization"] = f"Bearer {self.spec.auth['bearer']}"
                    body = {"input": invocation.prompt}
                    if invocation.session_id:
                        body["session_id"] = invocation.session_id
                    # Default to first agent if multiple; story-5.7 Injector picks deliberately.
                    body["agent_name"] = (self._agents_info or [{}])[0].get("name", "default")
                    resp = await self._http.post(f"{base}/run", json=body, headers=headers)
                    if resp.status_code != 200:
                        raise AdapterInvocationError(
                            f"/run returned {resp.status_code}: {resp.text[:500]}"
                        )
                    payload = resp.json()
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
            metadata={"agent_name": (self._agents_info or [{}])[0].get("name")},
        )

    @asynccontextmanager
    async def _fault_hook_context(self, fault_config: dict | None, base: str):
        if not fault_config:
            yield None
            return
        assert self._http is not None
        registration_id = None
        try:
            reg = await self._http.post(
                f"{base}/hooks/function_tool",
                json={"fault_config": fault_config},
            )
            if reg.status_code == 200:
                registration_id = reg.json().get("registration_id")
            yield registration_id
        finally:
            if registration_id is not None:
                await self._http.delete(f"{base}/hooks/function_tool/{registration_id}")

    async def fingerprint(self) -> AdapterFingerprint:
        if not self._connected:
            await self.connect()
        return AdapterFingerprint(
            tier=AdapterTier.TIER2_OPENAI_SDK,
            framework="openai-agents",
            agent_card=None,
            discovery_path="agents_listing",
            behavioral_signals={
                "agent_count": len(self._agents_info or []),
                "agent_names": [a.get("name") for a in (self._agents_info or [])],
            },
        )

    async def disconnect(self) -> None:
        if self._http is not None:
            await self._http.aclose()
            self._http = None
        self._connected = False
```

### Architecture context

- **`context/04 §10.1`:** OpenAI Agents SDK emits OpenInference-spec spans NATIVELY — no separate instrumentor needed for span emission. The `openinference-instrumentation-openai-agents` package is a BRIDGE that translates those native spans into Phoenix-shaped OTEL exports. This makes the adapter implementation the simplest of all Tier-2 stories — most plumbing is "POST + parse + return span IDs".
- **`context/04 §10.4`:** the canonical surface is `Runner.run(agent, "What's the weather in SF?")`. The HTTP wrapping convention `POST /run` with `{"input": ..., "agent_name": ...}` is a ChaosLab convention enforced by our fixture; production users wrap `Runner.run()` in FastAPI in their own style. We document this convention in `tests/fixtures/openai-sdk-target/README.md`.
- **`/agents` discovery convention:** matches the OpenAI Agents SDK's pattern of named agents (`Agent(name="...", ...)`). Our convention requires the wrapping FastAPI to expose a listing endpoint — same shape as CrewAI's `/crew/info`.
- **3-span topology (BDD criterion):** the OpenAI Agents SDK emits ≥3 spans per invocation: outer Agent span, Tool span(s) for each `function_tool` call, LLM span for each model invocation. The BDD integration test verifies the in-memory exporter captures all three kinds.
- **Banned-patterns enforcement:** Claude/OpenAI/Anthropic SDKs as RUNTIME LLM are banned in submitted code (per `architecture.md` §"Banned patterns"). This adapter does NOT import `openai` / `anthropic` directly — it only speaks HTTP to the target. The target uses the OpenAI Agents SDK internally; that's the TARGET's choice, not ChaosLab's runtime.
- **§14 clean:** no mocks in src/. The fixture in `tests/fixtures/openai-sdk-target/` is allowed to use a fake LLM (e.g., FakeListLLM stand-in) — that lives under `tests/` and is exempt per `[tool.ruff.lint.per-file-ignores] "tests/**" = [...]`.

### Known pitfalls

- **Native span emission caveat:** the SDK emits spans only when its global TraceProvider is active. The target fixture must invoke `OpenAIAgentsInstrumentor().instrument(tracer_provider=tracer_provider)` at startup, OR set `OPENAI_TRACE_PROVIDER` env var. Document this in the fixture's README.
- **`session_id` propagation:** OpenAI Agents SDK supports session continuity via the `Runner.run(..., session=...)` parameter. We pass it through as `body["session_id"]` and the fixture's FastAPI handler converts it into a `Session(id=...)` object. Tier 1 ADK has its own session model; the abstraction is intentional.
- **`agent_name` selection ambiguity:** if a target exposes multiple agents (e.g., a triage agent + a worker agent via handoffs), defaulting to the first is a heuristic. story-5.7 Injector will let the orchestrator pick deliberately based on `fingerprint().behavioral_signals["agent_names"]`. For story-3.5, "first agent" is fine.
- **Coverage gotcha:** `_fault_hook_context` has 4 branches (no fault, registration succeeds, registration fails, registration_id is None on cleanup). Cover all 4 with respx state machines.
- **httpx and `[]` empty-list response:** the `if not isinstance(self._agents_info, list) or len(...) == 0` guard catches the empty case. Test both `/agents` returning `[]` (raise) and returning `null` (raise) — pydantic's strict mode helps here but raw httpx JSON does not enforce.
- **Story sizing audit:** this is the simplest Tier 2 adapter — estimated 1.5h vs the others' 2h. If implementation runs faster, fold the saved time into adding 2 extra integration tests around span-kind assertions.
