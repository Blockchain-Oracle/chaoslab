# Story — Tier 2 CrewAI adapter (`crewai_adapter.py`)

**ID:** story-3.4-crewai-adapter
**Epic:** Epic 3 — Cross-framework target adapter layer
**Depends on:** story-3.1-adapter-interface
**Estimate:** ~2h
**Status:** PENDING
**tags:** [backend, p0, adapter, crewai, tier2]

---

## User story

**As a** ChaosLab Injector sub-agent attacking a CrewAI crew (multi-agent system, the framework Oracle and many YC-batch teams deploy per `context/04 §6.8`)
**I want to** drive the CrewAI target via its HTTP `kickoff` surface, with `openinference-instrumentation-crewai` capturing CHAIN-kind spans + child tool spans, and inject faults at the `@before_tool_call` / `@after_tool_call` decorator hooks (`context/04 §6.4`)
**So that** ChaosLab covers the second-most-deployed Python agent framework and Phoenix traces prove the crew's tool-call topology was attacked at the decorator surface — not just the LLM layer

---

## File modification map

Exact files the coding agent creates or modifies for this story:

- `apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/crewai_adapter.py` — NEW — `class CrewAIAdapter(TargetAdapter)`; ≤280 LOC; connect (probes target's `/crew/info` health endpoint), invoke (POSTs to `/kickoff` with `inputs={"prompt": ...}`, registers a per-invocation `@before_tool_call` decorator hook via the CrewAI HTTP webhook-side surface), fingerprint, disconnect
- `apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/__init__.py` — UPDATE — add `CrewAIAdapter` re-export
- `apps/chaoslab-agent/src/chaoslab_agent/observability.py` — UPDATE (or stub if story-4.5 not landed) — register `CrewAIInstrumentor().instrument()` gated by `CHAOSLAB_ENABLE_CREWAI_INSTRUMENTATION=1` env var; per `context/04 §6.2`
- `apps/chaoslab-agent/tests/unit/injector/target_adapters/test_crewai_adapter.py` — NEW — ≥8 unit tests with respx mocks: `/crew/info` parse, `/kickoff` accepts kickoff_id response, polls `/kickoff/{id}` until status=completed, fingerprint returns tier=TIER2_CREWAI + framework="crewai", spec.timeout_s enforced (long-poll abort), fault_config of kind="malformed_tool_output" registers the before_tool_call hook context, missing `kickoff_id` field raises AdapterInvocationError, 4xx on kickoff raises
- `apps/chaoslab-agent/tests/integration/injector/target_adapters/test_crewai_adapter.py` — NEW — ≥3 integration tests against a minimal 2-tool crew fixture (`tests/fixtures/crewai-target/`), marked `@pytest.mark.integration`; verifies a Phoenix in-memory exporter captures a CHAIN-kind span with ≥1 child tool span
- `apps/chaoslab-agent/tests/fixtures/crewai-target/` — NEW — minimal 2-tool crew: `main.py` defines `Crew(agents=[research_agent], tasks=[task1, task2], tools=[calc, search_stub])` wrapped in FastAPI exposing `POST /kickoff` and `GET /crew/info`; `Dockerfile`; `docker-compose.yml` on port 8003

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given a CrewAIAdapter constructed with TargetSpec(tier='tier2_crewai', url='http://localhost:8003')
When adapter.connect() runs and the target responds 200 on /crew/info with {"name": "research-crew", "tools": ["calc", "search"]}
Then no exception is raised
And adapter._crew_info["name"] == "research-crew"
And adapter._connected is True

Given a connected CrewAIAdapter
When adapter.invoke(AdapterInvocation(prompt="Find the latest news on Anthropic")) runs against the live fixture
Then result.error is None
And len(result.span_ids) ≥ 1
And the captured Phoenix trace contains one span of kind == "CHAIN" with ≥1 child span of kind == "TOOL" (per context/04 §6.2)

Given a connected CrewAIAdapter
When adapter.fingerprint() runs
Then result.tier == AdapterTier.TIER2_CREWAI
And result.framework == "crewai"
And result.discovery_path == "crew_info"
And result.behavioral_signals["tool_count"] == 2

Given a CrewAIAdapter and fault_config={"kind": "malformed_tool_output", "tool_name": "calc"}
When adapter.invoke runs
Then a @before_tool_call hook context was registered against the target's webhook surface for the invocation duration
And the registration is torn down after invoke returns

Given the target's /kickoff returns 202 with body {"kickoff_id": "abc123"} and /kickoff/abc123 returns {"status": "in_progress"} twice then {"status": "completed", "result": "..."}
When adapter.invoke runs with respx-driven polling
Then it polls /kickoff/abc123 exactly 3 times before returning
And result.response equals the final result string

Given a CrewAI target whose /kickoff response omits "kickoff_id"
When adapter.invoke runs (respx-mocked)
Then AdapterInvocationError is raised naming the malformed response

Given the source file
When `python3 scripts/check_max_lines.py apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/crewai_adapter.py` runs
Then exit code is 0

Given the unit tests
When `uv run pytest apps/chaoslab-agent/tests/unit/injector/target_adapters/test_crewai_adapter.py -v` runs
Then ≥8 tests pass

Given `grep -rE "(mock|fake|dummy|hardcoded|simulated)" apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/crewai_adapter.py` runs
When the output is checked
Then zero results appear (§14 gate clean)
```

---

## Shell verification

```bash
set -e
cd /Users/abu/dev/hackathon/rapid-agents

# Source file exists
test -f apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/crewai_adapter.py

# Class declared, subclasses TargetAdapter
grep -qE "^class CrewAIAdapter\(TargetAdapter\)" apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/crewai_adapter.py

# All four abstract methods
for method in connect invoke fingerprint disconnect; do
  grep -qE "async def ${method}\b" apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/crewai_adapter.py
done

# Re-export wired
uv run python -c "from chaoslab_agent.injector.target_adapters import CrewAIAdapter; print('ok')"

# Unit tests
uv run pytest apps/chaoslab-agent/tests/unit/injector/target_adapters/test_crewai_adapter.py -v
UNIT_COUNT=$(uv run pytest apps/chaoslab-agent/tests/unit/injector/target_adapters/test_crewai_adapter.py --collect-only -q 2>&1 | grep -cE "test_")
[ "$UNIT_COUNT" -ge 8 ] || { echo "expected ≥8 unit tests, got $UNIT_COUNT"; exit 1; }

# Integration tests (fixture stood up by conftest via docker-compose)
uv run pytest apps/chaoslab-agent/tests/integration/injector/target_adapters/test_crewai_adapter.py -m integration -v
INT_COUNT=$(uv run pytest apps/chaoslab-agent/tests/integration/injector/target_adapters/test_crewai_adapter.py --collect-only -q 2>&1 | grep -cE "test_")
[ "$INT_COUNT" -ge 3 ] || { echo "expected ≥3 integration tests, got $INT_COUNT"; exit 1; }

# Lint + type-check + 400-line clean
uv run ruff check apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/crewai_adapter.py
uv run ruff format --check apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/crewai_adapter.py
uv run ty check apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/crewai_adapter.py || uv run mypy --strict apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/crewai_adapter.py
python3 scripts/check_max_lines.py apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/crewai_adapter.py

# §14 clean
! grep -E "(mock|fake|dummy|hardcoded|simulated)" apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/crewai_adapter.py

echo "story-3.4 verification: PASS"
```

---

## Notes for coding agent

### Required wire path (per `context/04 §6`)

```python
# apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/crewai_adapter.py
from __future__ import annotations
import asyncio
import time
import httpx
from opentelemetry import trace
from chaoslab_agent.errors import AdapterInvocationError, AdapterDiscoveryError
from chaoslab_agent.injector.target_adapters.base import (
    AdapterFingerprint, AdapterInvocation, AdapterResult, AdapterTier, TargetAdapter,
)

POLL_INTERVAL_S = 0.5
POLL_MAX_S = 60.0


class CrewAIAdapter(TargetAdapter):
    """Tier 2 adapter: drives a CrewAI crew via its HTTP kickoff convention.

    Convention (per context/04 §6.7):
      POST /kickoff       body={"inputs": {"prompt": ...}}  -> 202 {"kickoff_id": "..."}
      GET  /kickoff/{id}                                    -> {"status": "...", "result": "..."}
      GET  /crew/info                                       -> {"name": ..., "tools": [...]}
    """

    def __init__(self, spec: TargetSpec) -> None:
        super().__init__(spec)
        self._crew_info: dict | None = None
        self._http: httpx.AsyncClient | None = None

    async def connect(self) -> None:
        if self._connected:
            return
        base = str(self.spec.url).rstrip("/")
        self._http = httpx.AsyncClient(timeout=self.spec.timeout_s)
        try:
            resp = await self._http.get(f"{base}/crew/info")
        except httpx.HTTPError as e:
            raise AdapterDiscoveryError(f"CrewAI target unreachable at {base}: {e}") from e
        if resp.status_code != 200:
            raise AdapterDiscoveryError(
                f"CrewAI /crew/info returned {resp.status_code} at {base}"
            )
        self._crew_info = resp.json()
        self._connected = True

    async def invoke(self, invocation: AdapterInvocation) -> AdapterResult:
        if not self._connected:
            await self.connect()
        assert self._http is not None
        base = str(self.spec.url).rstrip("/")
        start = time.perf_counter()
        span_ids: list[str] = []
        tracer = trace.get_tracer(__name__)

        # Register fault hook BEFORE kickoff (sticks for the duration of this invocation only).
        async with self._fault_hook_context(invocation.fault_config, base):
            with tracer.start_as_current_span("chaoslab.adapter.crewai.invoke") as span:
                span_ids.append(format(span.get_span_context().span_id, "016x"))
                try:
                    headers = {}
                    if self.spec.auth and "bearer" in self.spec.auth:
                        headers["Authorization"] = f"Bearer {self.spec.auth['bearer']}"
                    kickoff_resp = await self._http.post(
                        f"{base}/kickoff",
                        json={"inputs": {"prompt": invocation.prompt}},
                        headers=headers,
                    )
                    if kickoff_resp.status_code not in (200, 202):
                        raise AdapterInvocationError(
                            f"/kickoff returned {kickoff_resp.status_code}: {kickoff_resp.text[:500]}"
                        )
                    payload = kickoff_resp.json()
                    kickoff_id = payload.get("kickoff_id")
                    if not kickoff_id:
                        raise AdapterInvocationError(
                            f"/kickoff response missing kickoff_id: {payload}"
                        )
                    response_text = await self._poll(base, kickoff_id, headers)
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
            metadata={"crew_name": (self._crew_info or {}).get("name")},
        )

    async def _poll(self, base: str, kickoff_id: str, headers: dict) -> str:
        deadline = time.perf_counter() + min(POLL_MAX_S, self.spec.timeout_s)
        assert self._http is not None
        while time.perf_counter() < deadline:
            resp = await self._http.get(f"{base}/kickoff/{kickoff_id}", headers=headers)
            resp.raise_for_status()
            data = resp.json()
            if data.get("status") == "completed":
                return str(data.get("result", ""))
            if data.get("status") == "failed":
                raise AdapterInvocationError(f"crew kickoff failed: {data}")
            await asyncio.sleep(POLL_INTERVAL_S)
        raise AdapterInvocationError(f"crew kickoff {kickoff_id} timed out")

    async def _fault_hook_context(self, fault_config: dict | None, base: str):
        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def _ctx():
            if not fault_config:
                yield None
                return
            # Register the per-invocation hook against the target's webhook surface.
            # Detailed registration logic lives in story-5.2 (malformed_tool_output) +
            # story-5.7 (Injector wiring); here we ship the wiring + a teardown receipt.
            assert self._http is not None
            registration_id = None
            try:
                reg = await self._http.post(
                    f"{base}/hooks/before_tool_call",
                    json={"fault_config": fault_config},
                )
                if reg.status_code == 200:
                    registration_id = reg.json().get("registration_id")
                yield registration_id
            finally:
                if registration_id is not None:
                    await self._http.delete(f"{base}/hooks/before_tool_call/{registration_id}")

        return _ctx()

    async def fingerprint(self) -> AdapterFingerprint:
        if not self._connected:
            await self.connect()
        return AdapterFingerprint(
            tier=AdapterTier.TIER2_CREWAI,
            framework="crewai",
            agent_card=None,
            discovery_path="crew_info",
            behavioral_signals={
                "tool_count": len((self._crew_info or {}).get("tools", [])),
                "crew_name": (self._crew_info or {}).get("name"),
            },
        )

    async def disconnect(self) -> None:
        if self._http is not None:
            await self._http.aclose()
            self._http = None
        self._connected = False
```

### Architecture context

- **`context/04 §6.4`:** CrewAI ships `@before_tool_call` / `@after_tool_call` decorators. These are PROCESS-LOCAL hooks — they run inside the target's Python process, not ours. For Tier 2 we cannot monkey-patch the target process directly; instead we rely on the target exposing a webhook surface (`POST /hooks/before_tool_call`) that registers fault descriptors. The fixture in `tests/fixtures/crewai-target/` ships such an endpoint. This is the canonical Tier-2 pattern: **target opts in to faults by exposing a registration endpoint**.
- **OpenInference CrewAI instrumentor (`context/04 §6.2`):** `CrewAIInstrumentor().instrument(tracer_provider=tracer_provider)` emits CHAIN-kind spans for `Crew.kickoff()` with child TOOL spans for each `@tool` invocation. The BDD requires capturing this in an in-memory span exporter during integration tests.
- **Kickoff polling shape (`context/04 §6.7`):** `kickoff_id` returned at 202; status endpoint polled until `completed | failed`. This is the CrewAI Enterprise convention; self-hosted deployments using FastAPI wrappers may differ — our fixture matches the Enterprise shape.
- **§14 + banned-patterns:** unlike LangChain, CrewAI is NOT banned as orchestrator — but we don't use it as ours either; we only use the instrumentor. No `from crewai import ...` in this adapter. Only `openinference.instrumentation.crewai` (in `observability.py`).
- **Span kind assertion:** in the integration test, after `adapter.invoke()`, query the in-memory span exporter for spans where `span.attributes["openinference.span.kind"] == "CHAIN"`. The CHAIN parent + ≥1 child TOOL span is the proof-of-cross-framework-attack the BDD requires.

### Known pitfalls

- **CrewAI Enterprise vs self-hosted convention drift:** CrewAI Enterprise's hosted API returns `kickoff_id`; self-hosted deployments using `crew.kickoff()` synchronously inside a FastAPI handler return the result directly with no async polling. The adapter assumes the polling shape (matching the Enterprise-style fixture). If a future user points us at a synchronous deployment, the `kickoff_id is None` path will give a clear error — they can wrap in a webhook of their own.
- **`/hooks/before_tool_call` is NOT a real CrewAI Enterprise endpoint** — it's a ChaosLab convention enforced by our fixture. Document this clearly: the target must opt in by exposing this endpoint. Production targets won't have it; story-5.7 Injector handles this by checking `fingerprint().behavioral_signals.get("hooks_available")` before scheduling a `malformed_tool_output` fault against a CrewAI target.
- **httpx async polling loop:** uses `asyncio.sleep(POLL_INTERVAL_S)` which is async-safe. NEVER `time.sleep` — banned by ruff `T20`-adjacent + general async hygiene.
- **Coverage gotcha:** the `failed` branch in `_poll()` and the timeout branch both need explicit unit tests via respx state machines (`respx.post(...).mock(side_effect=[response_a, response_b, response_c])` pattern).
- **Pydantic + dict access:** `payload.get("kickoff_id")` returns `None | str`; the `if not kickoff_id:` guard catches both empty string and missing key. Tests should cover both.
- **`_fault_hook_context` shape:** declared as `async def` returning the context manager. The async-double-wrapping pattern (`@asynccontextmanager` inside the method) is required because the hook registration itself is an HTTP call. Keep this pattern; don't refactor to a plain `@asynccontextmanager` at module scope (we need `self._http`).
