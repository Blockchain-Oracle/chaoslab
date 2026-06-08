"""Patcher LlmAgent factory (stub — real implementation in Epic 6)."""

from __future__ import annotations

from google.adk.agents.llm_agent import LlmAgent

from chaoslab_agent.config import get_settings

PATCHER_NAME = "Patcher"
PATCHER_OUTPUT_KEY = "patcher_result"

_DESCRIPTION = (
    "Generates a HardeningRecipe from clustered failures and emits a Markdown "
    "artifact + GitLab MR"
)
# `{judge_result}` template reads the Judge sub-agent's output_key at runtime.
_INSTRUCTION = (
    "STUB: given upstream judge output {judge_result}, emit a JSON object "
    "with keys ['recipe_id', 'prompt_patches', 'tool_validation_diffs']. "
    "Real implementation lands in Epic 6."
)


def build_patcher_agent() -> LlmAgent:
    """Construct the Patcher stub for the SequentialAgent pipeline."""
    return LlmAgent(
        name=PATCHER_NAME,
        description=_DESCRIPTION,
        instruction=_INSTRUCTION,
        model=get_settings().judge_llm,
        output_key=PATCHER_OUTPUT_KEY,
    )
