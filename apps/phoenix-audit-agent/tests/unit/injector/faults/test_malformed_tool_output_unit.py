"""Pure Pydantic-validation tests for F1 MalformedToolOutputFault.

These tests run without any ADK runtime — they exercise only the config
schema. Behavioral / trace-as-assertion tests live in the integration suite.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from phoenix_audit_agent.injector.faults import MalformationMode, MalformedToolOutputFault


def test_accepts_each_of_the_four_modes() -> None:
    for mode in ("invalid_json", "missing_required_field", "type_mismatch", "exception"):
        f = MalformedToolOutputFault(mode=mode)
        assert f.mode == mode


def test_rejects_unknown_mode() -> None:
    with pytest.raises(ValidationError):
        MalformedToolOutputFault(mode="bogus")  # ty: ignore[invalid-argument-type]


def test_rate_defaults_to_one_and_rejects_out_of_bounds() -> None:
    f = MalformedToolOutputFault(mode="invalid_json")
    assert f.rate == 1.0
    f_half = MalformedToolOutputFault(mode="invalid_json", rate=0.5)
    assert f_half.rate == 0.5
    with pytest.raises(ValidationError):
        MalformedToolOutputFault(mode="invalid_json", rate=-0.1)
    with pytest.raises(ValidationError):
        MalformedToolOutputFault(mode="invalid_json", rate=1.1)


def test_target_tool_name_defaults_to_none() -> None:
    f = MalformedToolOutputFault(mode="exception")
    assert f.target_tool_name is None


def test_target_tool_name_accepts_string() -> None:
    f = MalformedToolOutputFault(mode="exception", target_tool_name="lookup_order")
    assert f.target_tool_name == "lookup_order"


def test_as_callback_returns_async_callable() -> None:
    import inspect

    fault = MalformedToolOutputFault(mode="exception")
    cb = fault.as_callback()
    assert callable(cb)
    assert inspect.iscoroutinefunction(cb)


def test_malformation_mode_literal_enumerates_four_values() -> None:
    assert set(MalformationMode.__args__) == {
        "invalid_json",
        "missing_required_field",
        "type_mismatch",
        "exception",
    }
