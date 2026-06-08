"""Behavioral tests for the TargetAdapter contract (story-3.1).

The contract is FROZEN per ADR-002 — every downstream adapter (Tier 1 ADK,
Tier 2 LangChain/CrewAI/OpenAI-SDK, Tier 3 HTTP black-box) plus the Injector
sub-agent that drives them subclass / consume it. Schema-breaking edits here
require an ADR amendment.

Construction style: tests use ``TargetSpec.model_validate({...})`` (and peers)
instead of kwarg construction. Two reasons: (1) this is the production code
path the orchestrator takes when deserializing JSON over the wire; (2) it
sidesteps the ty[invalid-argument-type] noise that bare-str-into-HttpUrl /
AdapterTier generates — pydantic's runtime coercion is invisible to the static
type checker, while model_validate's dict[str, Any] signature is not.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from pydantic import SecretStr, ValidationError

from chaoslab_agent.injector.target_adapters import (
    AdapterFingerprint,
    AdapterInvocation,
    AdapterResult,
    AdapterTier,
    TargetAdapter,
    TargetSpec,
)


def _spec(**overrides: Any) -> TargetSpec:
    """Build a TargetSpec with sensible defaults; overrides win."""
    payload: dict[str, Any] = {"tier": "tier1_adk", "url": "http://localhost:8001"}
    payload.update(overrides)
    return TargetSpec.model_validate(payload)


# -- ABC enforcement ---------------------------------------------------------


def test_target_adapter_is_abstract_cannot_instantiate() -> None:
    spec = _spec()
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        TargetAdapter(spec=spec)


def test_target_adapter_declares_four_abstract_methods() -> None:
    expected = {"connect", "invoke", "fingerprint", "disconnect"}
    assert expected.issubset(TargetAdapter.__abstractmethods__)


def test_concrete_subclass_with_all_methods_instantiates() -> None:
    class ConcreteAdapter(TargetAdapter):
        async def connect(self) -> None: ...
        async def invoke(self, invocation: AdapterInvocation) -> AdapterResult:
            return AdapterResult(response="ok", duration_ms=1.0)

        async def fingerprint(self) -> AdapterFingerprint:
            return AdapterFingerprint(tier=self.spec.tier)

        async def disconnect(self) -> None: ...

    spec = _spec()
    adapter = ConcreteAdapter(spec=spec)
    assert adapter.spec is spec


# -- AdapterTier enum --------------------------------------------------------


def test_adapter_tier_matches_adr_002() -> None:
    """DRIFT GUARD: hardcoded canonical set per ADR-002.

    If ADR-002 ever adds / removes / renames a tier, update both the enum in
    base.py AND this set literal in the same PR. The test fails loudly on
    drift so the implementer can't silently degrade the contract.
    """
    canonical = {
        "tier1_adk",
        "tier2_langchain",
        "tier2_crewai",
        "tier2_openai_sdk",
        "tier3_http_blackbox",
    }
    assert {member.value for member in AdapterTier} == canonical


def test_target_spec_coerces_tier_string_to_enum() -> None:
    spec = _spec(tier="tier1_adk")
    assert spec.tier is AdapterTier.TIER1_ADK


def test_target_spec_rejects_unknown_tier() -> None:
    with pytest.raises(ValidationError):
        _spec(tier="tier99_invalid")


# -- TargetSpec validation ---------------------------------------------------


@pytest.mark.parametrize(
    "bad_url",
    ["ftp://x", "localhost:8001", "https//typo.com", "", "not-a-url"],
)
def test_target_spec_rejects_invalid_urls(bad_url: str) -> None:
    with pytest.raises(ValidationError):
        _spec(url=bad_url)


def test_target_spec_timeout_rejects_outside_bounds() -> None:
    with pytest.raises(ValidationError):
        _spec(timeout_s=0.0)
    with pytest.raises(ValidationError):
        _spec(timeout_s=301.0)


def test_target_spec_timeout_accepts_inclusive_bounds() -> None:
    """ge=0.1 / le=300.0 — locks against a future `gt`/`lt` regression."""
    assert _spec(timeout_s=0.1).timeout_s == 0.1
    assert _spec(timeout_s=300.0).timeout_s == 300.0


def test_target_spec_optional_fields_default_to_none() -> None:
    spec = _spec()
    assert spec.agent_card is None
    assert spec.framework is None
    assert spec.auth is None
    assert spec.timeout_s == 30.0


def test_target_spec_auth_is_secretstr_and_redacts_in_json_dump() -> None:
    """SecretStr lock — bearer tokens / API keys must not surface in logs.

    `model_dump_json()` is what structlog's JSON renderer + every external
    serialization path goes through. pydantic 2's SecretStr renders as
    '**********' in that path by default.
    """
    spec = _spec(auth={"bearer": "super-secret-token-XYZ"})
    assert spec.auth is not None
    assert isinstance(spec.auth["bearer"], SecretStr)
    dumped = json.loads(spec.model_dump_json())
    assert "super-secret-token-XYZ" not in spec.model_dump_json()
    assert dumped["auth"]["bearer"] == "**********"


# -- AdapterInvocation validation --------------------------------------------


def test_adapter_invocation_minimal_valid_construction() -> None:
    inv = AdapterInvocation(prompt="hello")
    assert inv.prompt == "hello"
    assert inv.fault_config is None
    assert inv.session_id is None


def test_adapter_invocation_accepts_fault_config_dict() -> None:
    """Epic 5's typed F1-F4 descriptors round-trip through this field."""
    inv = AdapterInvocation(prompt="probe", fault_config={"type": "F1", "delay_ms": 200})
    assert inv.fault_config == {"type": "F1", "delay_ms": 200}


def test_adapter_invocation_rejects_empty_prompt() -> None:
    with pytest.raises(ValidationError):
        AdapterInvocation(prompt="")


# -- AdapterResult validation ------------------------------------------------


def test_adapter_result_happy_path() -> None:
    res = AdapterResult(response="ok", span_ids=["abc123"], duration_ms=42.5)
    assert res.error is None
    assert len(res.span_ids) == 1
    assert res.metadata == {}


def test_adapter_result_rejects_non_string_span_ids() -> None:
    """Assert on the error path explicitly — pydantic's lax mode would
    otherwise coerce int→str silently, defeating the type guard."""
    with pytest.raises(ValidationError) as exc:
        AdapterResult.model_validate({"response": "ok", "span_ids": [123], "duration_ms": 1.0})
    errors = exc.value.errors()
    assert any(
        e["loc"] == ("span_ids", 0) and e["type"].startswith("string") for e in errors
    ), f"expected string-type error on span_ids[0]; got {errors}"


def test_adapter_result_duration_zero_is_valid() -> None:
    """ge=0.0 — a cached / synthetic response can legitimately log 0.0 ms."""
    res = AdapterResult(response="ok", duration_ms=0.0)
    assert res.duration_ms == 0.0


def test_adapter_result_rejects_negative_duration() -> None:
    with pytest.raises(ValidationError):
        AdapterResult(response="ok", duration_ms=-1.0)


def test_adapter_result_metadata_accepts_arbitrary_payload() -> None:
    res = AdapterResult(response="ok", duration_ms=1.0, metadata={"crew_steps": 5})
    assert res.metadata["crew_steps"] == 5


# -- AdapterFingerprint construction ----------------------------------------


def test_adapter_fingerprint_minimal_valid() -> None:
    fp = AdapterFingerprint(tier=AdapterTier.TIER3_HTTP_BLACKBOX)
    assert fp.tier is AdapterTier.TIER3_HTTP_BLACKBOX
    assert fp.framework is None
    assert fp.discovery_path is None
    assert fp.behavioral_signals is None


def test_adapter_fingerprint_with_behavioral_signals() -> None:
    """Tier 3 populates this with system-prompt extraction + style + timing."""
    fp = AdapterFingerprint(
        tier=AdapterTier.TIER3_HTTP_BLACKBOX,
        framework="unknown",
        discovery_path="well_known_agent_card",
        behavioral_signals={"tool_call_count": 3, "openai_style_chunks": True},
    )
    assert fp.behavioral_signals is not None
    assert fp.behavioral_signals["tool_call_count"] == 3
