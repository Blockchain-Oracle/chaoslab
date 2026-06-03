# Story — TargetAdapter interface contract (`base.py`)

**ID:** story-3.1-adapter-interface
**Epic:** Epic 3 — Cross-framework target adapter layer
**Depends on:** story-2.1-naive-target-agent (Epic 2 — naive ADK target exists so `target_adapters/` lives next to a real victim)
**Estimate:** ~1.5h
**Status:** PENDING
**tags:** [backend, p0, adapter, foundation]

---

## User story

**As a** ChaosLab orchestrator (Injector sub-agent) that must attack ANY agent regardless of framework
**I want to** depend on a single `TargetAdapter` abstract base class with locked Pydantic invocation + result schemas
**So that** every later adapter (ADK, LangChain, CrewAI, OpenAI Agents SDK, HTTP black-box) drops into the same call site, faults compose uniformly across tiers, and ChaosLab's multi-framework differentiator (per `architecture.md` ADR-002 + `context/03 §13`) has a single contract surface

---

## File modification map

Exact files the coding agent creates or modifies for this story:

- `apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/__init__.py` — NEW — re-exports `TargetAdapter`, `TargetSpec`, `AdapterInvocation`, `AdapterResult`, `AdapterFingerprint`, `AdapterTier` from `base.py`
- `apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/base.py` — NEW — defines the ABC + 5 Pydantic schemas; ≤200 LOC; the canonical contract every adapter implements
- `apps/chaoslab-agent/src/chaoslab_agent/injector/__init__.py` — UPDATE (or NEW if absent) — add `from chaoslab_agent.injector.target_adapters import TargetAdapter` re-export so callers can `from chaoslab_agent.injector import TargetAdapter`
- `apps/chaoslab-agent/tests/unit/injector/target_adapters/__init__.py` — NEW — empty marker
- `apps/chaoslab-agent/tests/unit/injector/target_adapters/test_base.py` — NEW — ≥12 behavioral test cases covering: ABC abstract-method enforcement, each Pydantic schema's validation success + failure, `TargetSpec` tier enum coercion, `AdapterResult.error` nullable, `AdapterInvocation.fault_config` optional, span_ids list element type guard
- `apps/chaoslab-agent/tests/unit/injector/__init__.py` — NEW if absent — empty marker

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/base.py exists
When `grep -E "^class TargetAdapter\(.*ABC" apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/base.py` runs
Then exit code is 0 (TargetAdapter is an ABC)

Given the base module is importable
When `uv run python -c "from chaoslab_agent.injector.target_adapters import TargetAdapter, TargetSpec, AdapterInvocation, AdapterResult, AdapterFingerprint, AdapterTier; print('ok')"` runs
Then stdout contains "ok" and exit code is 0

Given TargetAdapter is abstract
When `uv run python -c "from chaoslab_agent.injector.target_adapters import TargetAdapter; TargetAdapter(spec=None)"` runs
Then exit code is non-zero and stderr matches "Can't instantiate abstract class"

Given a TargetSpec with tier='tier1_adk' and url='http://localhost:8001'
When TargetSpec(tier='tier1_adk', url='http://localhost:8001') is constructed
Then no exception is raised and instance.tier == AdapterTier.TIER1_ADK

Given a TargetSpec with tier='tier99_invalid'
When TargetSpec(tier='tier99_invalid', url='http://localhost:8001') is constructed
Then pydantic.ValidationError is raised

Given an AdapterInvocation(prompt="hello", fault_config=None)
When validated by pydantic
Then instance.prompt == "hello" and instance.fault_config is None

Given an AdapterResult(response="ok", span_ids=["abc123"], duration_ms=42.5)
When validated
Then instance.error is None and len(instance.span_ids) == 1

Given an AdapterResult with span_ids=[123] (int instead of str)
When validated
Then pydantic.ValidationError is raised

Given the test file apps/chaoslab-agent/tests/unit/injector/target_adapters/test_base.py
When `uv run pytest apps/chaoslab-agent/tests/unit/injector/target_adapters/test_base.py -v` runs
Then ≥12 tests pass and exit code is 0

Given the base.py source file
When `python3 scripts/check_max_lines.py apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/base.py` runs
Then exit code is 0 (file ≤400 lines)

Given `grep -rE "(mock|fake|dummy|hardcoded|simulated)" apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/` runs on source (excluding tests)
When the output is checked
Then zero results appear (§14 gate clean)
```

---

## Shell verification

```bash
set -e
cd /Users/abu/dev/hackathon/rapid-agents

# Source files exist
test -f apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/base.py
test -f apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/__init__.py
test -f apps/chaoslab-agent/tests/unit/injector/target_adapters/test_base.py

# ABC declared
grep -qE "^class TargetAdapter\(.*ABC" apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/base.py

# Required abstract methods present
grep -qE "@abstractmethod" apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/base.py
grep -cE "async def (connect|invoke|fingerprint|disconnect)" apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/base.py  # expect ≥ 4

# Pydantic schemas present
grep -cE "^class (TargetSpec|AdapterInvocation|AdapterResult|AdapterFingerprint)\(BaseModel\)" apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/base.py  # expect 4

# Imports resolve
uv run python -c "from chaoslab_agent.injector.target_adapters import TargetAdapter, TargetSpec, AdapterInvocation, AdapterResult, AdapterFingerprint, AdapterTier; print('ok')"

# Tests pass
uv run pytest apps/chaoslab-agent/tests/unit/injector/target_adapters/test_base.py -v
TEST_COUNT=$(uv run pytest apps/chaoslab-agent/tests/unit/injector/target_adapters/test_base.py --collect-only -q 2>&1 | grep -cE "test_")
[ "$TEST_COUNT" -ge 12 ] || { echo "expected ≥12 tests, got $TEST_COUNT"; exit 1; }

# Lint + type-check + 400-line clean
uv run ruff check apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/
uv run ruff format --check apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/
uv run ty check apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/ || uv run mypy --strict apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/
python3 scripts/check_max_lines.py apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/base.py

# §14 clean (no mocks in src/)
! grep -rE "(mock|fake|dummy|hardcoded|simulated)" apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/ | grep -v "__pycache__"

echo "story-3.1 verification: PASS"
```

---

## Notes for coding agent

### Required Pydantic schemas (exact contract — do not paraphrase)

```python
# apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/base.py
from __future__ import annotations
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field, HttpUrl


class AdapterTier(str, Enum):
    TIER1_ADK = "tier1_adk"
    TIER2_LANGCHAIN = "tier2_langchain"
    TIER2_CREWAI = "tier2_crewai"
    TIER2_OPENAI_SDK = "tier2_openai_sdk"
    TIER3_HTTP_BLACKBOX = "tier3_http_blackbox"


class TargetSpec(BaseModel):
    tier: AdapterTier
    url: HttpUrl
    agent_card: dict[str, Any] | None = None     # parsed AgentCard JSON if available
    framework: str | None = None                  # e.g. "langchain", "crewai", "openai-agents"
    auth: dict[str, str] | None = None            # bearer token, API key, etc.
    timeout_s: float = Field(default=30.0, ge=0.1, le=300.0)


class AdapterInvocation(BaseModel):
    prompt: str = Field(min_length=1)
    fault_config: dict[str, Any] | None = None    # serialized fault descriptor (F1-F4); typed in Epic 5
    session_id: str | None = None


class AdapterResult(BaseModel):
    response: str
    span_ids: list[str] = Field(default_factory=list)
    duration_ms: float = Field(ge=0.0)
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AdapterFingerprint(BaseModel):
    tier: AdapterTier
    framework: str | None = None
    agent_card: dict[str, Any] | None = None
    discovery_path: str | None = None             # which probe in context/05 §13 succeeded
    behavioral_signals: dict[str, Any] | None = None  # populated by Tier 3 fingerprinting (story 3.6)


class TargetAdapter(ABC):
    """Abstract base for every target adapter. Tier 1/2/3 implementations subclass this."""

    def __init__(self, spec: TargetSpec) -> None:
        self.spec = spec
        self._connected = False

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection / fetch metadata. Idempotent."""

    @abstractmethod
    async def invoke(self, invocation: AdapterInvocation) -> AdapterResult:
        """Send one prompt + optional fault config; capture response + span IDs."""

    @abstractmethod
    async def fingerprint(self) -> AdapterFingerprint:
        """Return discovery + behavioral metadata about the target."""

    @abstractmethod
    async def disconnect(self) -> None:
        """Release connections, clients, sockets."""
```

### Architecture context

- **ADR-002 (`architecture.md`):** the adapter layer is THE ChaosLab differentiator — no existing red-team tool supports multi-framework agents natively. This contract LOCKS the abstraction; all 5 implementing stories (3.2-3.6) only fill in subclass bodies, never modify the schemas.
- **§14 (`architecture.md`):** no `mock`/`fake`/`dummy` in `src/` hot path. Test doubles live ONLY in `tests/`.
- **400-line rule (ADR-010):** if `base.py` approaches 400 LOC (it shouldn't — target is ≤200), split schemas into a sibling `schemas.py`.
- **HttpUrl validation:** `pydantic.HttpUrl` rejects non-http(s) at parse time — good. For Tier 3 we may receive `https://...` only; that's fine, both http and https accepted.
- **`AdapterTier` is a str-Enum** so it serializes cleanly to JSON for SSE streaming to the frontend.
- **Async-by-default:** all four abstract methods are async. Tier 1 ADK + Tier 2 frameworks all expose async surfaces (per `context/04 §1.4, §4.4, §6.4, §10.4`); HTTP black-box uses `httpx.AsyncClient`. No sync escape hatch.
- **`session_id` in `AdapterInvocation`:** optional but reserved for multi-turn fault scenarios in Epic 5. Tier 1/2 adapters MAY pass it through to the underlying framework session; Tier 3 MAY use it as a header.
- **`metadata` in `AdapterResult`:** open dict for adapter-specific extras (e.g., CrewAI returns crew step counts; Tier 3 may return raw response headers). Keep tightly scoped — do not pollute with mutable state.
- **Coverage:** Pydantic schemas auto-cover much of the surface via validation; the ABC abstract-method enforcement is verified by attempting instantiation. Hit ≥80% line coverage on `base.py` per `pyproject.toml` `[tool.coverage.report] fail_under = 80`.

### Known pitfalls

- **Do NOT import `google.adk.*` here.** This is the FRAMEWORK-AGNOSTIC contract — `base.py` must be importable in a process with zero ADK installed (so test target stubs can run cheaply). ADK imports live in `adk_adapter.py` (story 3.2).
- **Do NOT add concrete methods to `TargetAdapter`.** Even `__repr__` is overkill. Keep the ABC surgical — every byte of shared logic is a future merge conflict.
- **Do NOT serialize `TargetSpec.auth` to logs.** Add `model_config = ConfigDict(json_schema_extra={"sensitive": ["auth"]})` and exclude it from any future `model_dump()` in observability code. Story 4.5 will enforce this in structlog; for now, comment the field as sensitive.
- **`HttpUrl` rejects trailing slashes inconsistently across pydantic v2 patches** — normalize with `str(spec.url).rstrip("/")` when building well-known discovery URLs in story 3.6.
