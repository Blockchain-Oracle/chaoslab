"""Fault → wire descriptor for remote delivery to the target's hook surface.

The deployed target is reached over A2A (Cloud Run) — the Injector cannot
install ADK callbacks in-process. Instead each fault exports a JSON-safe
descriptor carrying kind + params + the RESOLVED payload; the target's
`/hooks/adk` executor applies it mechanically. Attack intelligence (payload
texts, malformed shapes) never leaves the auditor's fault classes.

The target-side reader lives at `target_agent.fault_hooks`; the cross-app
contract test pins the two against drift.
"""

from __future__ import annotations

from typing import Any

from phoenix_audit_agent.injector.faults.context_poisoning import (
    POISONS,
    ContextPoisoningFault,
)
from phoenix_audit_agent.injector.faults.latency_spike import LatencySpikeFault
from phoenix_audit_agent.injector.faults.malformed_tool_output import (
    MODE_PAYLOADS,
    MalformedToolOutputFault,
)
from phoenix_audit_agent.injector.faults.prompt_injection import (
    PAYLOADS,
    PromptInjectionFault,
)


def as_descriptor(fault: object) -> dict[str, Any]:
    """Export a fault instance as the JSON-safe hook-wire descriptor."""
    if isinstance(fault, MalformedToolOutputFault):
        return {
            "kind": "malformed_tool_output",
            "mode": fault.mode,
            "rate": fault.rate,
            "target_tool_name": fault.target_tool_name,
            "payload": MODE_PAYLOADS[fault.mode],
        }
    if isinstance(fault, PromptInjectionFault):
        return {
            "kind": "prompt_injection",
            "attack": fault.attack,
            "payload": fault.payload_override or PAYLOADS[fault.attack],
        }
    if isinstance(fault, ContextPoisoningFault):
        return {
            "kind": "context_poisoning",
            "mode": fault.mode,
            "target_retriever_name": fault.target_retriever_name,
            "payload": fault.payload_override or POISONS[fault.poison_idx],
        }
    if isinstance(fault, LatencySpikeFault):
        return {
            "kind": "latency_spike",
            "delay_ms": fault.delay_ms,
            "timeout_ms": fault.timeout_ms,
        }
    msg = f"no descriptor export for fault type {type(fault).__name__!r}"
    raise TypeError(msg)


__all__ = ["as_descriptor"]
