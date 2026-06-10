"""S-EC1: fault descriptors — the wire contract the target's hook executor consumes.

The descriptor must carry EVERYTHING the target needs to apply the fault
mechanically (kind + params + resolved payload text/dict). Attack intelligence
stays in the auditor; the target never invents payloads.
"""

from __future__ import annotations

import json

import pytest

from phoenix_audit_agent.injector.faults import (
    ContextPoisoningFault,
    LatencySpikeFault,
    MalformedToolOutputFault,
    PromptInjectionFault,
)
from phoenix_audit_agent.injector.faults.context_poisoning import POISON_MARKER, POISONS
from phoenix_audit_agent.injector.faults.descriptors import as_descriptor
from phoenix_audit_agent.injector.faults.prompt_injection import PAYLOADS


class TestMalformedToolOutputDescriptor:
    def test_invalid_json_carries_literal_payload_dict(self) -> None:
        d = as_descriptor(MalformedToolOutputFault(mode="invalid_json"))
        assert d["kind"] == "malformed_tool_output"
        assert d["mode"] == "invalid_json"
        # The target returns this dict verbatim from before_tool_callback.
        assert isinstance(d["payload"], dict)
        assert "_phoenix_audit_malformed_payload" in d["payload"]

    def test_missing_required_field_payload_omits_total(self) -> None:
        d = as_descriptor(MalformedToolOutputFault(mode="missing_required_field"))
        assert "total" not in d["payload"]
        assert d["payload"]["status"] == "shipped"

    def test_exception_mode_has_no_payload(self) -> None:
        d = as_descriptor(MalformedToolOutputFault(mode="exception"))
        assert d["mode"] == "exception"
        assert d["payload"] is None

    def test_tool_scoping_and_rate_forwarded(self) -> None:
        d = as_descriptor(
            MalformedToolOutputFault(mode="type_mismatch", rate=0.5, target_tool_name="lookup")
        )
        assert d["rate"] == 0.5
        assert d["target_tool_name"] == "lookup"


class TestPromptInjectionDescriptor:
    def test_payload_resolved_from_attack_type(self) -> None:
        d = as_descriptor(PromptInjectionFault(attack="instruction_override"))
        assert d["kind"] == "prompt_injection"
        assert d["attack"] == "instruction_override"
        assert d["payload"] == PAYLOADS["instruction_override"]

    def test_payload_override_wins(self) -> None:
        d = as_descriptor(
            PromptInjectionFault(attack="role_hijacking", payload_override="OVERRIDE")
        )
        assert d["payload"] == "OVERRIDE"


class TestContextPoisoningDescriptor:
    def test_poison_resolved_by_index(self) -> None:
        d = as_descriptor(ContextPoisoningFault(mode="history_insert", poison_idx=1))
        assert d["kind"] == "context_poisoning"
        assert d["mode"] == "history_insert"
        assert d["payload"] == POISONS[1]
        assert POISON_MARKER in d["payload"]

    def test_retriever_mode_forwards_name_filter(self) -> None:
        d = as_descriptor(
            ContextPoisoningFault(mode="retriever_insert", poison_idx=0, target_retriever_name="kb")
        )
        assert d["mode"] == "retriever_insert"
        assert d["target_retriever_name"] == "kb"


class TestLatencySpikeDescriptor:
    def test_delay_forwarded(self) -> None:
        d = as_descriptor(LatencySpikeFault(delay_ms=300, timeout_ms=5000))
        assert d["kind"] == "latency_spike"
        assert d["delay_ms"] == 300


class TestDescriptorWireSafety:
    @pytest.mark.parametrize(
        "fault",
        [
            MalformedToolOutputFault(mode="invalid_json"),
            PromptInjectionFault(attack="payload_smuggling"),
            ContextPoisoningFault(mode="retriever_insert", poison_idx=2),
            LatencySpikeFault(delay_ms=100, timeout_ms=5000),
        ],
    )
    def test_descriptor_is_json_round_trippable(self, fault: object) -> None:
        d = as_descriptor(fault)
        assert json.loads(json.dumps(d)) == d

    def test_unknown_fault_object_raises(self) -> None:
        with pytest.raises(TypeError, match="no descriptor"):
            as_descriptor(object())
