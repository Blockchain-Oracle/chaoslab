"""Injector LlmAgent factory (stub — real implementation in Epic 5)."""

from __future__ import annotations

from google.adk.agents.llm_agent import LlmAgent

from chaoslab_agent.config import get_settings

INJECTOR_NAME = "Injector"
INJECTOR_OUTPUT_KEY = "injector_result"

_DESCRIPTION = (
    "Selects a fault class, configures the target adapter, invokes the target, " "captures the span"
)
# `STUB:` prefix is the §14-carve-out per story-4.2 — the orchestrator grep
# allows this literal prefix inside instruction strings (data, not code).
_INSTRUCTION = (
    "STUB: emit a JSON object with keys ['fault_class', 'span_id', 'pass']. "
    "Real implementation lands in Epic 5."
)


def build_injector_agent() -> LlmAgent:
    """Construct the Injector stub for the SequentialAgent pipeline."""
    return LlmAgent(
        name=INJECTOR_NAME,
        description=_DESCRIPTION,
        instruction=_INSTRUCTION,
        model=get_settings().judge_llm,
        output_key=INJECTOR_OUTPUT_KEY,
    )
