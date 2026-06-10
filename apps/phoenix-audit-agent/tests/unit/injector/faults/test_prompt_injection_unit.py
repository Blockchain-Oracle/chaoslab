"""Pure Pydantic-validation tests for F2 PromptInjectionFault.

These tests run without any ADK runtime — they exercise only the config
schema. Behavioral / trace-as-assertion tests live in the integration suite.
"""

from __future__ import annotations

import inspect

import pytest
from pydantic import ValidationError

from phoenix_audit_agent.injector.faults import AttackType, PromptInjectionFault


def test_accepts_each_of_the_four_attacks() -> None:
    for attack in (
        "instruction_override",
        "role_hijacking",
        "payload_smuggling",
        "indirect_injection",
    ):
        f = PromptInjectionFault(attack=attack)
        assert f.attack == attack


def test_rejects_unknown_attack() -> None:
    with pytest.raises(ValidationError):
        PromptInjectionFault(attack="bogus")  # ty: ignore[invalid-argument-type]


def test_payload_override_defaults_to_none_and_accepts_string() -> None:
    f = PromptInjectionFault(attack="instruction_override")
    assert f.payload_override is None
    f_custom = PromptInjectionFault(attack="instruction_override", payload_override="CUSTOM")
    assert f_custom.payload_override == "CUSTOM"


def test_as_callback_returns_async_callable() -> None:
    fault = PromptInjectionFault(attack="instruction_override")
    cb = fault.as_callback()
    assert callable(cb)
    assert inspect.iscoroutinefunction(cb)


def test_attack_type_literal_enumerates_four_values() -> None:
    assert set(AttackType.__args__) == {
        "instruction_override",
        "role_hijacking",
        "payload_smuggling",
        "indirect_injection",
    }
