"""Patcher sub-agent — HardeningRecipe synthesis + GitLab MR emission (Epic 6)."""

from chaoslab_agent.patcher.agent import PATCHER_NAME, build_patcher_agent
from chaoslab_agent.patcher.recipe import (
    FailureCluster,
    FaultClass,
    HardeningRecipe,
    PromptPatch,
    ToolValidationDiff,
    new_recipe_id,
)

__all__ = [
    "PATCHER_NAME",
    "FailureCluster",
    "FaultClass",
    "HardeningRecipe",
    "PromptPatch",
    "ToolValidationDiff",
    "build_patcher_agent",
    "new_recipe_id",
]
