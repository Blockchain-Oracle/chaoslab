"""ADK type quarantine for phoenix-audit-agent (ADR-001 + best-practices/03 §3).

This is the ONLY module in `apps/phoenix-audit-agent/src/phoenix_audit_agent/` that imports
from `google.adk.*` at the top level. Every other module that needs ADK types
must import them from here. The invariant is gate-tested by
`tests/unit/test_adk_types.py::test_only_quarantine_imports_google_adk`.

Pydantic wrappers (`AgentSpec`, `RunState`, `RunEvent`) carry the project's
type-level invariants: judge_llm is `gemini-3.5-flash` (ADR-007), run_id matches
`^run_[a-z0-9]{12}$` (the phoenix-audit-web frontend SSE contract — see
`docs/run-config-schema.md`), descriptions are >=20 chars per
architecture/03 §1.1 (supervisor-routing requirement).
"""

from __future__ import annotations

from typing import Any, Literal

# ADR-012: SequentialAgent / LoopAgent / ParallelAgent are the deprecated-but-pinned
# ADK 2.x workflow primitives. Workflow (the v3 replacement) is out-of-scope.
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.llm_agent import LlmAgent
from google.adk.agents.loop_agent import LoopAgent  # ty: ignore[deprecated]
from google.adk.agents.parallel_agent import ParallelAgent  # ty: ignore[deprecated]
from google.adk.agents.sequential_agent import SequentialAgent  # ty: ignore[deprecated]
from google.adk.events import Event as AdkEvent
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.runners import InMemoryRunner, Runner
from google.adk.tools import FunctionTool
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.retrieval.base_retrieval_tool import BaseRetrievalTool
from google.adk.tools.tool_context import ToolContext
from pydantic import BaseModel, Field, field_validator

# Pinned per ADR-007 + docs/architecture.md hard rule.
JUDGE_LLM_PINNED = "gemini-3.5-flash"

# Minimum description length for a sub-agent (load-bearing for supervisor routing
# per architecture/03 §1.1: parent LLMs read sub-agent descriptions to delegate).
_MIN_DESCRIPTION_LEN = 20


class AgentSpec(BaseModel):
    """Type-safe sub-agent spec consumed by the orchestrator factory.

    `model` is a Literal — pydantic rejects anything other than gemini-3.5-flash
    at the type-checker level AND at runtime construction.
    """

    name: str = Field(min_length=1)
    description: str = Field(min_length=_MIN_DESCRIPTION_LEN)
    model: Literal["gemini-3.5-flash"] = JUDGE_LLM_PINNED
    output_key: str | None = None
    tools: list[str] = Field(default_factory=list)


# Run lifecycle phases. The SSE `phase_change` event on /stream carries one of
# these strings; extending the Literal widens the frontend wire contract.
RunPhaseLiteral = Literal["queued", "running", "injecting", "judging", "patching", "done", "error"]


class RunState(BaseModel):
    """In-process run state shared by the FastAPI `_RUN_REGISTRY` + SSE stream.

    Defined in the quarantine so the orchestrator and SSE consumer share one
    type definition without re-importing pydantic everywhere.
    """

    run_id: str = Field(pattern=r"^run_[a-z0-9]{12}$")
    phase: RunPhaseLiteral
    target_url: str
    created_at: str
    # Closed-loop delta: baseline is the pass-rate BEFORE the Injector probes the
    # target; post_patch is the pass-rate AFTER the Patcher's recipe is applied.
    # The frontend's Resilience Curve renders the delta.
    pass_rate_baseline: float | None = None
    pass_rate_post_patch: float | None = None
    current_event_index: int = 0

    @field_validator("created_at")
    @classmethod
    def _created_at_iso(cls, v: str) -> str:
        # Same lightweight shape gate as `write_annotation.AnnotationResult.wrote_at`.
        if not v.endswith("Z") or "T" not in v:
            msg = f"created_at must be RFC-3339 UTC with trailing Z, got {v!r}"
            raise ValueError(msg)
        return v


# SSE event taxonomy. Every `event:` line on the /stream wire carries one of these.
RunEventLiteral = Literal[
    "hello",
    "phase_change",
    "attack_progress",
    "cluster_emitted",
    "recipe_generated",
    "done",
    "error",
    "heartbeat",
    "complete",
    "cancelled",
]


class RunEvent(BaseModel):
    """Single SSE event envelope; the `data` payload shape varies by event_type."""

    event_type: RunEventLiteral
    data: dict[str, Any]
    emitted_at: str


__all__ = [
    "JUDGE_LLM_PINNED",
    "AdkEvent",
    "AgentSpec",
    "BaseRetrievalTool",
    "BaseTool",
    "CallbackContext",
    "FunctionTool",
    "InMemoryRunner",
    "LlmAgent",
    "LlmRequest",
    "LlmResponse",
    "LoopAgent",
    "ParallelAgent",
    "RunEvent",
    "RunEventLiteral",
    "RunPhaseLiteral",
    "RunState",
    "Runner",
    "SequentialAgent",
    "ToolContext",
]
