"""Shared types + dispatcher for Judge rubrics (story-6.1).

Each fault class maps to exactly one rubric. ``apply_rubric`` is the public
dispatcher the Judge sub-agent calls; per-class rubrics live in sibling
modules so the eval-prompt-drift surface stays one-file-per-rubric.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

FaultClass = Literal[
    "malformed_tool_output",
    "prompt_injection",
    "context_poisoning",
    "latency_spike",
]


class EvalScore(BaseModel):
    """Canonical rubric outcome. ``score`` is the [0,1] confidence the agent
    handled the fault correctly; ``passed`` is the boolean verdict; ``reason``
    is a one-sentence-or-shorter human-readable explanation."""

    model_config = ConfigDict(frozen=True)

    passed: bool
    score: float = Field(ge=0.0, le=1.0)
    reason: str = Field(min_length=1)


class RubricInput(BaseModel):
    """Per-attack input to a rubric.

    ``phoenix_client`` is typed loosely (``object``) because Phoenix's
    ``AsyncClient`` doesn't ship ty-friendly stubs in the current alpha —
    quarantine the dynamic boundary here, not in business logic
    (story-6.1 spec line 206).
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    span_id: str = Field(min_length=1)
    fault_class: FaultClass
    phoenix_client: object


def _import_tool_invocation_rubric() -> Callable[[RubricInput], Awaitable[EvalScore]]:
    from chaoslab_agent.judge.rubrics.tool_invocation import tool_invocation_rubric

    return tool_invocation_rubric


def _import_prompt_injection_rubric() -> Callable[[RubricInput], Awaitable[EvalScore]]:
    from chaoslab_agent.judge.rubrics.prompt_injection_success import (
        prompt_injection_rubric,
    )

    return prompt_injection_rubric


def _import_hallucination_rubric() -> Callable[[RubricInput], Awaitable[EvalScore]]:
    from chaoslab_agent.judge.rubrics.hallucination import hallucination_rubric

    return hallucination_rubric


def _import_latency_failure_rubric() -> Callable[[RubricInput], Awaitable[EvalScore]]:
    from chaoslab_agent.judge.rubrics.latency_failure import latency_failure_rubric

    return latency_failure_rubric


async def apply_rubric(inp: RubricInput) -> EvalScore:
    """Route ``inp.fault_class`` to its rubric and return the score.

    Lazy-imports the per-class rubric module on first call to keep import-time
    side-effects (Phoenix LLM client construction) out of the hot path until
    the dispatcher actually needs that rubric.
    """
    if inp.fault_class == "malformed_tool_output":
        rubric = _import_tool_invocation_rubric()
    elif inp.fault_class == "prompt_injection":
        rubric = _import_prompt_injection_rubric()
    elif inp.fault_class == "context_poisoning":
        rubric = _import_hallucination_rubric()
    elif inp.fault_class == "latency_spike":
        rubric = _import_latency_failure_rubric()
    else:
        msg = f"unknown fault_class {inp.fault_class!r} — expected one of {FaultClass.__args__}"
        raise ValueError(msg)
    return await rubric(inp)


__all__ = ["EvalScore", "FaultClass", "RubricInput", "apply_rubric"]
