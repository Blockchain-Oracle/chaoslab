"""Injector LlmAgent factory.

Emits a JSON object `{fault_class, span_id, pass}` into state['injector_result']
for downstream Judge consumption. Currently ships a STUB instruction; a real
implementation replaces the factory body without changing the contract.
"""

from __future__ import annotations

from chaoslab_agent.adk_types import LlmAgent
from chaoslab_agent.config import get_settings

INJECTOR_NAME = "Injector"
INJECTOR_OUTPUT_KEY = "injector_result"

_DESCRIPTION = (
    "Selects a fault class, configures the target adapter, invokes the target, " "captures the span"
)
# `STUB:` prefix is the §14-carve-out documented in story-4.2 — the orchestrator
# §14 grep allows this literal prefix inside instruction strings (data, not code).
_INSTRUCTION = (
    "STUB: emit a JSON object with keys ['fault_class', 'span_id', 'pass']. "
    "Stub-mode response is acceptable."
)


def build_injector_agent() -> LlmAgent:
    """Construct the Injector for the SequentialAgent pipeline."""
    return LlmAgent(
        name=INJECTOR_NAME,
        description=_DESCRIPTION,
        instruction=_INSTRUCTION,
        model=get_settings().judge_llm,
        output_key=INJECTOR_OUTPUT_KEY,
    )
