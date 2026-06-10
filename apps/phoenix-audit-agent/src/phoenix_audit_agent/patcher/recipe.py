"""HardeningRecipe pydantic schemas — canonical recipe artifact format."""

from __future__ import annotations

import secrets
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# Re-use the clusterer's FailureCluster + FailureClusterSet so the recipe
# stays drift-free with the partition output — same shape, no duplication.
from phoenix_audit_agent.judge.clustering import FailureCluster, FailureClusterSet
from phoenix_audit_agent.judge.rubrics import FaultClass

# Top-level field names the metadata bag is forbidden from shadowing.
# Kept inline so adding a recipe field forces a deliberate edit here.
_RESERVED_METADATA_KEYS: frozenset[str] = frozenset(
    {
        "recipe_id",
        "target_agent_id",
        "generated_at",
        "cluster_set",
        "prompt_patches",
        "tool_validation_diffs",
        "regression_test_cases",
        "estimated_resilience_improvement",
        "metadata",
    }
)


class PromptPatch(BaseModel):
    model_config = ConfigDict(frozen=True)

    section: Literal["system_prompt", "tool_description", "few_shot_example"]
    operation: Literal["insert", "replace", "append"]
    before: str | None = None
    after: str = Field(min_length=1)

    @model_validator(mode="after")
    def _replace_requires_before(self) -> PromptPatch:
        if self.operation == "replace" and self.before is None:
            msg = "PromptPatch.before is required when operation == 'replace'"
            raise ValueError(msg)
        return self


class ToolValidationDiff(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_name: str = Field(min_length=1)
    operation: Literal[
        "add_input_validator",
        "add_output_validator",
        "add_retry_policy",
        "add_timeout",
    ]
    # Unified diff string — downstream emitters render in ```diff fences
    # and apply via `git apply`; schema only enforces non-empty.
    code_patch: str = Field(min_length=1)


class RegressionTestCase(BaseModel):
    """One Phoenix-dataset regression row.

    The Phoenix dataset shape (architecture/04 §6.3) requires `input` +
    `expected`; the typed model keeps a typo from silently landing in
    the signed report. Additional Phoenix metadata stays in `extra`.
    """

    model_config = ConfigDict(frozen=True, extra="allow")

    input: str = Field(min_length=1)
    expected: str = Field(min_length=1)


class HardeningRecipe(BaseModel):
    model_config = ConfigDict(frozen=True)

    recipe_id: str = Field(pattern=r"^recipe_[a-z0-9]{12}$")
    target_agent_id: str = Field(min_length=1)
    # ISO 8601 string per architecture.md — kept as str so emitters render
    # it byte-for-byte without a parse round-trip. The field validator
    # below enforces parseability so a typo can't silently land in the
    # signed report.
    generated_at: str = Field(min_length=1)
    # Typed wrapper so the partition mutual-exclusion + total invariant
    # crosses into the recipe instead of being silently bypassed by a
    # bare list[FailureCluster].
    cluster_set: FailureClusterSet
    prompt_patches: list[PromptPatch] = Field(default_factory=list)
    tool_validation_diffs: list[ToolValidationDiff] = Field(default_factory=list)
    regression_test_cases: list[RegressionTestCase] = Field(default_factory=list)
    estimated_resilience_improvement: float = Field(ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("generated_at")
    @classmethod
    def _generated_at_is_iso_8601(cls, value: str) -> str:
        try:
            # `fromisoformat` accepts the trailing `Z` form on Python 3.11+
            # and every offset shape; rejects "x", "NOT_A_DATE", impossible
            # day numbers, etc.
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            msg = f"generated_at must be ISO 8601 (got {value!r})"
            raise ValueError(msg) from exc
        return value

    @model_validator(mode="after")
    def _metadata_does_not_shadow_top_level(self) -> HardeningRecipe:
        collision = _RESERVED_METADATA_KEYS & set(self.metadata.keys())
        if collision:
            msg = (
                f"metadata keys must not shadow top-level recipe fields "
                f"(collision: {sorted(collision)})"
            )
            raise ValueError(msg)
        return self


def new_recipe_id() -> str:
    """Mint a 12-hex-char recipe id matching HardeningRecipe.recipe_id."""
    return f"recipe_{secrets.token_hex(6)}"


__all__ = [
    "FailureCluster",
    "FailureClusterSet",
    "FaultClass",
    "HardeningRecipe",
    "PromptPatch",
    "RegressionTestCase",
    "ToolValidationDiff",
    "new_recipe_id",
]
