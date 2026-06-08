"""Judge LlmAgent factory (stub — real implementation in Epic 6)."""

from __future__ import annotations

from google.adk.agents.llm_agent import LlmAgent

from chaoslab_agent.config import get_settings

JUDGE_NAME = "Judge"
JUDGE_OUTPUT_KEY = "judge_result"

_DESCRIPTION = (
    "Reads attack-phase spans, runs LLM-as-judge rubrics, clusters failures, "
    "writes annotations back"
)
# `{injector_result}` is the ADK state-passing template anchor: the SequentialAgent
# substitutes the upstream output_key into this slot at invocation time.
_INSTRUCTION = (
    "STUB: given upstream injector output {injector_result}, emit a JSON object "
    "with keys ['cluster_id', 'failure_count', 'root_cause']. "
    "Real implementation lands in Epic 6."
)


def build_judge_agent() -> LlmAgent:
    """Construct the Judge stub for the SequentialAgent pipeline."""
    return LlmAgent(
        name=JUDGE_NAME,
        description=_DESCRIPTION,
        instruction=_INSTRUCTION,
        model=get_settings().judge_llm,
        output_key=JUDGE_OUTPUT_KEY,
    )
