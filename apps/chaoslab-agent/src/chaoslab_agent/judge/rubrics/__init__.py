"""Per-fault-class rubrics for the Judge sub-agent (story-6.1).

One file per rubric to keep eval-prompt-drift surface focused. The
``apply_rubric`` dispatcher routes by ``fault_class``.
"""

from chaoslab_agent.judge.rubrics._base import (
    EvalScore,
    FaultClass,
    RubricInput,
    apply_rubric,
)
from chaoslab_agent.judge.rubrics.hallucination import hallucination_rubric
from chaoslab_agent.judge.rubrics.latency_failure import latency_failure_rubric
from chaoslab_agent.judge.rubrics.prompt_injection_success import (
    prompt_injection_rubric,
)
from chaoslab_agent.judge.rubrics.tool_invocation import tool_invocation_rubric

__all__ = [
    "EvalScore",
    "FaultClass",
    "RubricInput",
    "apply_rubric",
    "hallucination_rubric",
    "latency_failure_rubric",
    "prompt_injection_rubric",
    "tool_invocation_rubric",
]
