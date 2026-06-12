"""Helper for recording a black-box AttackResult — kept out of injector/agent.py
to respect the 400-line per-file cap.

Black-box probes happen when the target is a non-instrumented public A2A
agent (AIScan, weather-agent, every a2aregistry entry that isn't ours): no
/hooks/adk, no Phoenix spans. The judge keys off the delivery_mode span
attribute to skip the trace fetch and emit pass-by-avoidance.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from phoenix_audit_agent.injector.agent import AttackResult, AttackRun


def build_black_box_result(
    attack: AttackRun,
    response: Any,
    attack_payload: str | None,
    adapter_span_id: str,
) -> AttackResult:
    """AttackResult for a black-box probe — auditor span is the surrogate trace."""
    # Lazy import — AttackResult lives in the parent module and would create
    # a circular import at module-load time.
    from phoenix_audit_agent.injector.agent import AttackResult

    return AttackResult(
        run_idx=attack.run_idx,
        fault_class=attack.fault_class,
        span_id=adapter_span_id,
        trace_id=adapter_span_id,
        status="ok",
        duration_ms=response.duration_ms,
        attack_payload=attack_payload,
        span_attributes={
            "phoenix_audit.fault.type": attack.fault_class,
            "phoenix_audit.fault.variant_idx": attack.variant_idx,
            "phoenix_audit.delivery_mode": "black_box_no_hook",
            "phoenix_audit.attack.fault_delivered": False,
            "phoenix_audit.adapter_span_id": adapter_span_id,
        },
    )
