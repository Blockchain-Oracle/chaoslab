"""Unit tests for InjectorState + AttackRun + AttackResult schemas (story-5.7).

Pure Pydantic schema tests — Injector.run() orchestration lives in the
integration suite (test_injector_agent.py) where the trace-as-assertion
pattern verifies real span emission.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

import pytest
from pydantic import ValidationError

from phoenix_audit_agent.injector import AttackResult, AttackRun, InjectorState
from phoenix_audit_agent.injector.agent import FaultClass

_Status = Literal["ok", "error", "timeout"]


def _attack_result(
    run_idx: int = 0,
    fault_class: FaultClass = "malformed_tool_output",
    span_id: str = "span-abc123",
    trace_id: str = "trace-xyz789",
    status: _Status = "ok",
) -> AttackResult:
    return AttackResult(
        run_idx=run_idx,
        fault_class=fault_class,
        span_id=span_id,
        trace_id=trace_id,
        status=status,
        duration_ms=12.5,
    )


# ---------------------------------------------------------------------------
# FaultClass literal
# ---------------------------------------------------------------------------


def test_fault_class_literal_enumerates_four_values() -> None:
    assert set(FaultClass.__args__) == {
        "malformed_tool_output",
        "prompt_injection",
        "context_poisoning",
        "latency_spike",
    }


# ---------------------------------------------------------------------------
# AttackRun schema
# ---------------------------------------------------------------------------


def test_attack_run_accepts_valid_construction() -> None:
    run = AttackRun(run_idx=0, fault_class="prompt_injection", variant_idx=2)
    assert run.run_idx == 0
    assert run.fault_class == "prompt_injection"
    assert run.variant_idx == 2


def test_attack_run_is_frozen() -> None:
    run = AttackRun(run_idx=0, fault_class="prompt_injection", variant_idx=0)
    with pytest.raises(ValidationError):
        run.run_idx = 99  # type: ignore[misc]


def test_attack_run_rejects_negative_run_idx() -> None:
    with pytest.raises(ValidationError):
        AttackRun(run_idx=-1, fault_class="prompt_injection", variant_idx=0)


def test_attack_run_rejects_unknown_fault_class() -> None:
    with pytest.raises(ValidationError):
        AttackRun(
            run_idx=0,
            fault_class="bogus_fault",  # ty: ignore[invalid-argument-type]
            variant_idx=0,
        )


# ---------------------------------------------------------------------------
# AttackResult schema
# ---------------------------------------------------------------------------


def test_attack_result_requires_non_empty_span_id() -> None:
    with pytest.raises(ValidationError):
        AttackResult(
            run_idx=0,
            fault_class="malformed_tool_output",
            span_id="",  # min_length=1 violation
            trace_id="trace-1",
            status="ok",
            duration_ms=1.0,
        )


def test_attack_result_requires_non_empty_trace_id() -> None:
    with pytest.raises(ValidationError):
        AttackResult(
            run_idx=0,
            fault_class="malformed_tool_output",
            span_id="span-1",
            trace_id="",
            status="ok",
            duration_ms=1.0,
        )


def test_attack_result_rejects_unknown_status() -> None:
    with pytest.raises(ValidationError):
        AttackResult(
            run_idx=0,
            fault_class="malformed_tool_output",
            span_id="span-1",
            trace_id="trace-1",
            status="weird",  # ty: ignore[invalid-argument-type]
            duration_ms=1.0,
        )


def test_attack_result_status_accepts_ok_error_timeout() -> None:
    for status in ("ok", "error", "timeout"):
        result = AttackResult(
            run_idx=0,
            fault_class="latency_spike",
            span_id="span-1",
            trace_id="trace-1",
            status=status,
            duration_ms=1.0,
        )
        assert result.status == status


def test_attack_result_captured_at_defaults_to_utc_now() -> None:
    before = datetime.now(UTC)
    result = _attack_result()
    after = datetime.now(UTC)
    assert before <= result.captured_at <= after
    assert result.captured_at.tzinfo == UTC


def test_attack_result_is_frozen() -> None:
    result = _attack_result()
    with pytest.raises(ValidationError):
        result.status = "error"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# InjectorState — record_attack + fault_breakdown
# ---------------------------------------------------------------------------


def test_injector_state_defaults_baseline_passed_to_false() -> None:
    state = InjectorState()
    assert state.baseline_passed is False
    assert state.baseline_pass_rate == 0.0
    assert state.total_attacks == 0
    assert state.attack_results == []


def test_record_attack_appends_and_increments_total_attacks() -> None:
    state = InjectorState()
    state.record_attack(_attack_result(run_idx=0))
    state.record_attack(_attack_result(run_idx=1, fault_class="prompt_injection"))
    assert state.total_attacks == 2
    assert len(state.attack_results) == 2
    assert state.attack_results[0].run_idx == 0
    assert state.attack_results[1].run_idx == 1


def test_total_attacks_derives_from_attack_results_length() -> None:
    """``total_attacks`` is a computed_field — no desync vector possible."""
    state = InjectorState()
    assert state.total_attacks == 0
    state.attack_results.append(_attack_result())
    assert state.total_attacks == 1


def test_fault_breakdown_counts_attacks_by_fault_class() -> None:
    state = InjectorState()
    state.record_attack(_attack_result(fault_class="malformed_tool_output"))
    state.record_attack(_attack_result(fault_class="prompt_injection"))
    state.record_attack(_attack_result(fault_class="prompt_injection"))
    state.record_attack(_attack_result(fault_class="latency_spike"))
    breakdown = state.fault_breakdown()
    assert breakdown == {
        "malformed_tool_output": 1,
        "prompt_injection": 2,
        "latency_spike": 1,
    }


def test_fault_breakdown_omits_classes_with_zero_attacks() -> None:
    """Only classes that actually fired appear in the breakdown — avoids the
    Judge agent having to filter zero counts when rendering the demo bar chart."""
    state = InjectorState()
    state.record_attack(_attack_result(fault_class="malformed_tool_output"))
    breakdown = state.fault_breakdown()
    assert breakdown == {"malformed_tool_output": 1}
    assert "context_poisoning" not in breakdown


def test_injector_state_baseline_pass_rate_in_valid_range() -> None:
    state = InjectorState(baseline_pass_rate=0.95, baseline_passed=True)
    assert state.baseline_pass_rate == 0.95
    with pytest.raises(ValidationError):
        InjectorState(baseline_pass_rate=1.5)
