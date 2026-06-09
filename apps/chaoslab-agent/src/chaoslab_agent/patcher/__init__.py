"""Patcher sub-agent — HardeningRecipe synthesis + GitLab MR emission (Epic 6)."""

from chaoslab_agent.patcher.agent import (
    PATCHER_NAME,
    Patcher,
    PatcherEmptyResponseError,
    build_patcher_agent,
    estimate_resilience_improvement,
)
from chaoslab_agent.patcher.gitlab_emitter import (
    GitLabEmitResult,
    GitLabEmitterError,
    GitLabMREmitter,
)
from chaoslab_agent.patcher.markdown_emitter import EmitResult, MarkdownEmitter
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
    "EmitResult",
    "FailureCluster",
    "FailureClusterSet",
    "FaultClass",
    "GitLabEmitResult",
    "GitLabEmitterError",
    "GitLabMREmitter",
    "HardeningRecipe",
    "MarkdownEmitter",
    "Patcher",
    "PatcherEmptyResponseError",
    "PromptPatch",
    "RegressionTestCase",
    "ToolValidationDiff",
    "build_patcher_agent",
    "estimate_resilience_improvement",
    "new_recipe_id",
]
