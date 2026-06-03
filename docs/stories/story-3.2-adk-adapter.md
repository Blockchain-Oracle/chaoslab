# Story — Tier 1 ADK adapter (`adk_adapter.py`)

**ID:** story-3.2-adk-adapter
**Epic:** Epic 3 — Cross-framework target adapter layer
**Depends on:** story-3.1-adapter-interface, story-2.2-target-a2a-exposure (target exposed via `to_a2a()` on port 8001)
**Estimate:** ~2h
**Status:** PENDING
**tags:** [backend, p0, adapter, adk]

---

## User story

**As a** ChaosLab Injector sub-agent attacking the canonical demo target (naive customer-support ADK agent)
**I want to** drive the target through ADK's native `RemoteA2aAgent` client via its A2A AgentCard
**So that** Tier 1 invocations stay framework-native (no HTTP shimming), AgentCard metadata feeds the fingerprint surface, and Phoenix span IDs returned by `RemoteA2aAgent.run()` flow back into `AdapterResult.span_ids` for downstream judging (Epic 6)

---

## File modification map

Exact files the coding agent creates or modifies for this story:

- `apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/adk_adapter.py` — NEW — `class ADKAdapter(TargetAdapter)` implementing all 4 abstract methods via `google.adk.agents.RemoteA2aAgent`; ≤250 LOC
- `apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/__init__.py` — UPDATE — add `from chaoslab_agent.injector.target_adapters.adk_adapter import ADKAdapter` re-export
- `apps/chaoslab-agent/src/chaoslab_agent/adk_types.py` — UPDATE (if exists from story-4.5) OR NEW stub — add `RemoteA2aAgent` quarantine wrapper if not already present; per `coding-standards.md` §"ADK-specific Python patterns" do not import `google.adk.*` outside this quarantine module
- `apps/chaoslab-agent/tests/integration/injector/target_adapters/__init__.py` — NEW — empty marker
- `apps/chaoslab-agent/tests/integration/injector/target_adapters/test_adk_adapter.py` — NEW — ≥10 integration tests against the live target-agent on `localhost:8001` (marked `@pytest.mark.integration`): connect parses AgentCard, invoke returns span_ids ≥1, invoke captures duration_ms, fingerprint returns tier=TIER1_ADK + agent_card.name non-empty, disconnect is idempotent, malformed AgentCard URL raises explicit error, timeout enforces `spec.timeout_s`, concurrent invocations don't clobber span_ids, `connect()` is idempotent (second call no-op), `invoke()` without prior `connect()` auto-connects
- `apps/chaoslab-agent/tests/unit/injector/target_adapters/test_adk_adapter_unit.py` — NEW — ≥5 unit tests using `respx` to mock the `/.well-known/agent-card.json` endpoint: card parsing, missing card 404 handling, malformed JSON, missing required AgentCard fields, auth header propagation

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given the target_agent service is running at http://localhost:8001 (story-2.2 satisfied)
When ADKAdapter(TargetSpec(tier='tier1_adk', url='http://localhost:8001')).connect() runs
Then no exception is raised
And adapter._connected is True
And adapter._agent_card is not None
And adapter._agent_card["name"] is a non-empty string

Given a connected ADKAdapter
When adapter.invoke(AdapterInvocation(prompt="What's my order status for order #123?")) runs
Then the returned AdapterResult.error is None
And len(result.span_ids) ≥ 1
And result.duration_ms > 0.0
And isinstance(result.response, str) and len(result.response) > 0

Given a connected ADKAdapter
When adapter.fingerprint() runs
Then result.tier == AdapterTier.TIER1_ADK
And result.framework == "google-adk"
And result.agent_card is not None
And result.discovery_path == "agent_card"

Given an ADKAdapter pointed at an unreachable URL http://localhost:9999
When adapter.connect() runs with timeout_s=2.0
Then it raises a specific exception (httpx.ConnectError or wrapped AdapterConnectionError)
And the exception message names the URL

Given an ADKAdapter where the target returns a 404 for /.well-known/agent-card.json
When adapter.connect() runs (respx-mocked)
Then it raises AdapterDiscoveryError naming the missing well-known path

Given an integration test file
When `uv run pytest apps/chaoslab-agent/tests/integration/injector/target_adapters/test_adk_adapter.py -m integration -v` runs
And the target-agent service is up at localhost:8001
Then ≥10 tests pass and exit code is 0

Given a unit test file with respx mocks
When `uv run pytest apps/chaoslab-agent/tests/unit/injector/target_adapters/test_adk_adapter_unit.py -v` runs
Then ≥5 tests pass and exit code is 0

Given the adk_adapter.py source file
When `python3 scripts/check_max_lines.py apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/adk_adapter.py` runs
Then exit code is 0 (file ≤400 lines)

Given `grep -E "from google\.adk" apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/adk_adapter.py` runs
When the output is checked
Then the only google.adk import goes through chaoslab_agent.adk_types (quarantine module per coding-standards.md)

Given `grep -rE "(mock|fake|dummy|hardcoded)" apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/adk_adapter.py` runs
When the output is checked
Then zero results appear (§14 gate clean)
```

---

## Shell verification

```bash
set -e
cd /Users/abu/dev/hackathon/rapid-agents

# Source file exists
test -f apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/adk_adapter.py

# ADKAdapter declared, subclasses TargetAdapter
grep -qE "^class ADKAdapter\(TargetAdapter\)" apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/adk_adapter.py

# All four abstract methods implemented
for method in connect invoke fingerprint disconnect; do
  grep -qE "async def ${method}\b" apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/adk_adapter.py
done

# ADK quarantine respected
! grep -E "from google\.adk\." apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/adk_adapter.py | grep -v "adk_types"

# Re-export wired up
uv run python -c "from chaoslab_agent.injector.target_adapters import ADKAdapter; print('ok')"

# Unit tests (no target needed — respx mocks)
uv run pytest apps/chaoslab-agent/tests/unit/injector/target_adapters/test_adk_adapter_unit.py -v
UNIT_COUNT=$(uv run pytest apps/chaoslab-agent/tests/unit/injector/target_adapters/test_adk_adapter_unit.py --collect-only -q 2>&1 | grep -cE "test_")
[ "$UNIT_COUNT" -ge 5 ] || { echo "expected ≥5 unit tests, got $UNIT_COUNT"; exit 1; }

# Integration tests against live target (story-2.2 must be running)
# CI starts target-agent via docker-compose; locally: `uv run --project apps/target-agent python -m target_agent.main &`
uv run pytest apps/chaoslab-agent/tests/integration/injector/target_adapters/test_adk_adapter.py -m integration -v
INT_COUNT=$(uv run pytest apps/chaoslab-agent/tests/integration/injector/target_adapters/test_adk_adapter.py --collect-only -q 2>&1 | grep -cE "test_")
[ "$INT_COUNT" -ge 10 ] || { echo "expected ≥10 integration tests, got $INT_COUNT"; exit 1; }

# Lint + type-check + 400-line clean
uv run ruff check apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/adk_adapter.py
uv run ruff format --check apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/adk_adapter.py
uv run ty check apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/adk_adapter.py || uv run mypy --strict apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/adk_adapter.py
python3 scripts/check_max_lines.py apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/adk_adapter.py

# §14 clean
! grep -E "(mock|fake|dummy|hardcoded|simulated)" apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/adk_adapter.py

echo "story-3.2 verification: PASS"
```

---

## Notes for coding agent

### Required wire path (per `context/04 §1.4` + `context/04 §1.7`)

```python
# apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/adk_adapter.py
from __future__ import annotations
import time
import httpx
from opentelemetry import trace
from chaoslab_agent.adk_types import RemoteA2aAgentWrapper  # quarantine boundary
from chaoslab_agent.injector.target_adapters.base import (
    AdapterFingerprint, AdapterInvocation, AdapterResult, AdapterTier, TargetAdapter,
)
from chaoslab_agent.errors import AdapterConnectionError, AdapterDiscoveryError

WELL_KNOWN_AGENT_CARD = "/.well-known/agent-card.json"


class ADKAdapter(TargetAdapter):
    """Tier 1 adapter: drives an ADK agent exposed via `to_a2a()` using RemoteA2aAgent."""

    def __init__(self, spec: TargetSpec) -> None:
        super().__init__(spec)
        self._agent_card: dict | None = None
        self._remote: RemoteA2aAgentWrapper | None = None
        self._http: httpx.AsyncClient | None = None

    async def connect(self) -> None:
        if self._connected:
            return
        base = str(self.spec.url).rstrip("/")
        self._http = httpx.AsyncClient(timeout=self.spec.timeout_s)
        try:
            resp = await self._http.get(f"{base}{WELL_KNOWN_AGENT_CARD}")
        except httpx.HTTPError as e:
            raise AdapterConnectionError(f"failed to reach {base}: {e}") from e
        if resp.status_code == 404:
            raise AdapterDiscoveryError(f"no AgentCard at {base}{WELL_KNOWN_AGENT_CARD}")
        resp.raise_for_status()
        self._agent_card = resp.json()
        # Build the RemoteA2aAgent client (quarantined wrapper)
        self._remote = RemoteA2aAgentWrapper(
            url=base,
            agent_card=self._agent_card,
            timeout_s=self.spec.timeout_s,
        )
        self._connected = True

    async def invoke(self, invocation: AdapterInvocation) -> AdapterResult:
        if not self._connected:
            await self.connect()
        assert self._remote is not None
        start = time.perf_counter()
        span_ids: list[str] = []
        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span("chaoslab.adapter.adk.invoke") as span:
            span_ids.append(format(span.get_span_context().span_id, "016x"))
            try:
                response_text = await self._remote.run(
                    prompt=invocation.prompt,
                    session_id=invocation.session_id,
                )
                error = None
            except Exception as e:  # noqa: BLE001 — bubble adapter-level error to caller
                response_text = ""
                error = f"{type(e).__name__}: {e}"
                span.record_exception(e)
            # The RemoteA2aAgent emits child spans; their IDs are exposed via the OTEL context.
            child_ids = self._remote.last_child_span_ids() or []
            span_ids.extend(child_ids)
        return AdapterResult(
            response=response_text,
            span_ids=span_ids,
            duration_ms=(time.perf_counter() - start) * 1000.0,
            error=error,
            metadata={"agent_card_name": (self._agent_card or {}).get("name")},
        )

    async def fingerprint(self) -> AdapterFingerprint:
        if not self._connected:
            await self.connect()
        return AdapterFingerprint(
            tier=AdapterTier.TIER1_ADK,
            framework="google-adk",
            agent_card=self._agent_card,
            discovery_path="agent_card",
        )

    async def disconnect(self) -> None:
        if self._http is not None:
            await self._http.aclose()
            self._http = None
        self._remote = None
        self._connected = False
```

### Architecture context

- **ADK quarantine (`coding-standards.md` §"ADK-specific Python patterns" + ADR-001):** `from google.adk.agents import RemoteA2aAgent` is BANNED outside `chaoslab_agent.adk_types`. This story adds `RemoteA2aAgentWrapper` to that module if absent.
- **`context/04 §1.7`:** ADK does NOT ship `/.well-known/agent-card.json` automatically — Epic 2 story-2.2 wires `to_a2a(agent, port=8001)` which (per ADK ≥ June 2026 release) exposes the AgentCard at that path. If the build of ADK in use does not yet emit the AgentCard, story-2.2 has a fallback that serves it from `target_agent/static/agent-card.json` — handle 200-on-that-path identically.
- **Span ID capture:** the OpenInference ADK instrumentor (`openinference-instrumentation-google-adk`, configured in story-4.5) auto-emits LLM/TOOL/CHAIN/AGENT spans during `RemoteA2aAgent.run()`. We capture our own outer span explicitly so even a target-side trace-export failure still yields ≥1 span_id (the BDD criterion). `last_child_span_ids()` is a helper exposed on the wrapper that reads `tracer_provider.get_active_span_processors()` and harvests IDs from the current trace context — implement in `adk_types.py`.
- **No mocks in src/ (§14):** every `respx`-mocked path lives in `tests/unit/`; integration tests hit the REAL target_agent service (started by docker-compose in CI; locally by `uv run --project apps/target-agent python -m target_agent.main`).
- **Idempotency:** `connect()` short-circuits if already connected; `invoke()` auto-connects; `disconnect()` safe to call without prior `connect()`. Test all three.
- **Authentication:** if `spec.auth` is set, pass `headers={"Authorization": f"Bearer {spec.auth['bearer']}"}` to both the well-known fetch AND to the `RemoteA2aAgentWrapper` for `run()` calls. For the demo target this is None.

### Known pitfalls

- **`RemoteA2aAgent` is an ADK Python class that opens an SSE-or-JSONRPC channel** depending on AgentCard `interfaces`. Do NOT roll your own HTTP loop — let ADK handle protocol negotiation. The wrapper just adapts the result shape.
- **Pydantic v2 + `httpx.AsyncClient`:** `str(self.spec.url)` returns a normalized URL (pydantic v2 HttpUrl quirk). Always wrap in `str(...)` before passing to httpx — passing the HttpUrl object raises a TypeError on some httpx releases.
- **`.well-known/agent-card.json` vs `.well-known/a2a.json`:** the A2A spec evolved mid-2025; ADK ≥ June 2026 ships `agent-card.json`. If the target serves `a2a.json` instead, this adapter must NOT silently fall back — that's the HTTP black-box adapter's job (story 3.6). For Tier 1, hard-require `agent-card.json` and let the fallback adapter pick up oddities.
- **Coverage gotcha:** the `except Exception` branch in `invoke()` is hit only by integration tests that kill the target mid-flight. Add a respx-driven unit test that returns 500 on the JSONRPC POST to force the branch and meet ≥80% coverage on this module.
- **`@pytest.mark.integration`:** these tests must be marked so CI's `pr-checks.yaml` can opt-in (per `coding-standards.md` `[tool.pytest.ini_options] markers`). The standard PR check runs `-m "not integration and not online"`; a separate matrix job runs `-m integration` with the target-agent docker compose stood up.
