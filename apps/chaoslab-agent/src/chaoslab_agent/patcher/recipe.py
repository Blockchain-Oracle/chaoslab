"""HardeningRecipe pydantic schemas — canonical recipe artifact format."""

from __future__ import annotations

import secrets
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

# Re-use the clusterer's FailureCluster so the recipe stays drift-free
# with story-6.2's partition output. Same schema, no duplication.
from chaoslab_agent.judge.clustering import FailureCluster
from chaoslab_agent.judge.rubrics._base import FaultClass


class PromptPatch(BaseModel):
    """Edit to a target agent's prompt — system / tool / few-shot."""

    model_config = ConfigDict(frozen=True)

    section: Literal["system_prompt", "tool_description", "few_shot_example"]
    operation: Literal["insert", "replace", "append"]
    before: str | None = None
    after: str = Field(min_length=1)

    @model_validator(mode="after")
    def _replace_requires_before(self) -> PromptPatch:
        # `replace` semantics need the original substring to splice on;
        # `insert` and `append` don't, so before stays optional there.
        if self.operation == "replace" and self.before is None:
            msg = "PromptPatch.before is required when operation == 'replace'"
            raise ValueError(msg)
        return self


class ToolValidationDiff(BaseModel):
    """Unified-diff patch hardening a target tool."""

    model_config = ConfigDict(frozen=True)

    tool_name: str = Field(min_length=1)
    operation: Literal[
        "add_input_validator",
        "add_output_validator",
        "add_retry_policy",
        "add_timeout",
    ]
    # Format is unified diff; schema only enforces non-empty. S6.5
    # renders this in ```diff fences; S6.6 applies it via `git apply`.
    code_patch: str = Field(min_length=1)


class HardeningRecipe(BaseModel):
    """Signed, regulator-facing recipe the Patcher emits per audit cycle."""

    model_config = ConfigDict(frozen=True)

    recipe_id: str = Field(pattern=r"^recipe_[a-z0-9]{12}$")
    target_agent_id: str = Field(min_length=1)
    # ISO 8601 string per architecture.md — kept as str so downstream
    # emitters can render it byte-for-byte without a parse round-trip.
    generated_at: str = Field(min_length=1)
    cluster_set: list[FailureCluster] = Field(min_length=1)
    prompt_patches: list[PromptPatch] = Field(default_factory=list)
    tool_validation_diffs: list[ToolValidationDiff] = Field(default_factory=list)
    # Loose-typed: Phoenix dataset format dictates the shape downstream
    # (architecture/04 §6.3) so we don't double-validate it here.
    regression_test_cases: list[dict[str, Any]] = Field(default_factory=list)
    estimated_resilience_improvement: float = Field(ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)


def new_recipe_id() -> str:
    """Mint a 12-hex-char recipe id matching HardeningRecipe.recipe_id."""
    return f"recipe_{secrets.token_hex(6)}"


__all__ = [
    "FailureCluster",
    "FaultClass",
    "HardeningRecipe",
    "PromptPatch",
    "ToolValidationDiff",
    "new_recipe_id",
]
