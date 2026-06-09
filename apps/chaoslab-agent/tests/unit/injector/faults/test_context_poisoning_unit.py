"""Pure Pydantic-validation tests for F3 ContextPoisoningFault.

These tests run without any ADK runtime — they exercise only the config
schema. Behavioral / trace-as-assertion tests live in the integration suite.
"""

from __future__ import annotations

import inspect

import pytest
from pydantic import ValidationError

from chaoslab_agent.injector.faults import ContextPoisoningFault, PoisonMode


def test_accepts_each_of_the_two_modes() -> None:
    for mode in ("retriever_insert", "history_insert"):
        f = ContextPoisoningFault(mode=mode)
        assert f.mode == mode


def test_rejects_unknown_mode() -> None:
    with pytest.raises(ValidationError):
        ContextPoisoningFault(mode="bogus")  # ty: ignore[invalid-argument-type]


def test_payload_override_defaults_to_none_and_accepts_string() -> None:
    f = ContextPoisoningFault(mode="retriever_insert")
    assert f.payload_override is None
    f_custom = ContextPoisoningFault(mode="retriever_insert", payload_override="CUSTOM")
    assert f_custom.payload_override == "CUSTOM"


def test_as_callback_returns_async_callable() -> None:
    fault = ContextPoisoningFault(mode="history_insert")
    cb = fault.as_callback()
    assert callable(cb)
    assert inspect.iscoroutinefunction(cb)


def test_mode_literal_enumerates_two_values() -> None:
    assert set(PoisonMode.__args__) == {
        "retriever_insert",
        "history_insert",
    }
