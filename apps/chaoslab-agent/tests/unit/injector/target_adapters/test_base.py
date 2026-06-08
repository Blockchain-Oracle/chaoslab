"""Behavioral tests for the TargetAdapter contract (story-3.1).

The contract is FROZEN per ADR-002 — every adapter story 3.2-3.6 implements
the same ABC + Pydantic schemas. Changing the contract without an ADR
amendment breaks 5 downstream stories.

Construction style: tests use ``TargetSpec.model_validate({...})`` (and
peers) rather than the keyword-argument form. Two reasons:
1. The orchestrator builds specs from JSON over the wire — model_validate
   is the production code path, so the tests exercise it.
2. The kwarg form requires bare ``str`` literals where the field type is
   ``HttpUrl`` / ``AdapterTier`` — pydantic coerces at runtime, but ty has
   no visibility into that coercion and floods the file with
   ``invalid-argument-type`` errors. ``model_validate`` takes a
   ``dict[str, Any]``, sidestepping the static-checker friction.
"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

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
        async def connect(self) -> None:
            self._connected = True

        async def invoke(self, invocation: AdapterInvocation) -> AdapterResult:
            return AdapterResult(response="ok", duration_ms=1.0)

        async def fingerprint(self) -> AdapterFingerprint:
            return AdapterFingerprint(tier=self.spec.tier)

        async def disconnect(self) -> None:
            self._connected = False

    spec = _spec()
    adapter = ConcreteAdapter(spec=spec)
    assert adapter.spec is spec
    assert adapter._connected is False


# -- AdapterTier enum --------------------------------------------------------


def test_adapter_tier_has_five_str_values() -> None:
    values = {member.value for member in AdapterTier}
    assert values == {
        "tier1_adk",
        "tier2_langchain",
        "tier2_crewai",
        "tier2_openai_sdk",
        "tier3_http_blackbox",
    }


def test_target_spec_coerces_tier_string_to_enum() -> None:
    spec = _spec(tier="tier1_adk")
    assert spec.tier is AdapterTier.TIER1_ADK


def test_target_spec_rejects_unknown_tier() -> None:
    with pytest.raises(ValidationError):
        _spec(tier="tier99_invalid")


# -- TargetSpec validation ---------------------------------------------------


def test_target_spec_rejects_non_http_url() -> None:
    with pytest.raises(ValidationError):
        _spec(url="ftp://localhost")


def test_target_spec_timeout_bounds_enforced() -> None:
    with pytest.raises(ValidationError):
        _spec(timeout_s=0.0)
    with pytest.raises(ValidationError):
        _spec(timeout_s=301.0)


def test_target_spec_optional_fields_default_to_none() -> None:
    spec = _spec()
    assert spec.agent_card is None
    assert spec.framework is None
    assert spec.auth is None
    assert spec.timeout_s == 30.0


# -- AdapterInvocation validation --------------------------------------------


def test_adapter_invocation_minimal_valid_construction() -> None:
    inv = AdapterInvocation(prompt="hello")
    assert inv.prompt == "hello"
    assert inv.fault_config is None
    assert inv.session_id is None


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
    with pytest.raises(ValidationError):
        # model_validate accepts dict[str, Any] — ty doesn't see the inner
        # span_ids type mismatch and pydantic catches it at runtime.
        AdapterResult.model_validate({"response": "ok", "span_ids": [123], "duration_ms": 1.0})


def test_adapter_result_rejects_negative_duration() -> None:
    with pytest.raises(ValidationError):
        AdapterResult(response="ok", duration_ms=-1.0)


# -- AdapterFingerprint construction ----------------------------------------


def test_adapter_fingerprint_minimal_valid() -> None:
    fp = AdapterFingerprint(tier=AdapterTier.TIER3_HTTP_BLACKBOX)
    assert fp.tier is AdapterTier.TIER3_HTTP_BLACKBOX
    assert fp.framework is None
    assert fp.discovery_path is None
    assert fp.behavioral_signals is None
