"""Patcher sub-agent — HardeningRecipe synthesis + GitLab MR emission (Epic 6)."""

from chaoslab_agent.patcher.agent import (
    PATCHER_NAME,
    Patcher,
    PatcherEmptyResponseError,
    build_patcher_agent,
    estimate_resilience_improvement,
)
from chaoslab_agent.patcher.recipe import (
    FailureCluster,
    FailureClusterSet,
    FaultClass,
    HardeningRecipe,
    PromptPatch,
    RegressionTestCase,
    ToolValidationDiff,
    new_recipe_id,
)

__all__ = [
    "PATCHER_NAME",
    "FailureCluster",
    "FailureClusterSet",
    "FaultClass",
    "HardeningRecipe",
    "Patcher",
    "PatcherEmptyResponseError",
    "PromptPatch",
    "RegressionTestCase",
    "ToolValidationDiff",
    "build_patcher_agent",
    "estimate_resilience_improvement",
    "new_recipe_id",
]
