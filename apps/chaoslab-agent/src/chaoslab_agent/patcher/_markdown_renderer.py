"""Pure-function Markdown rendering for HardeningRecipe.

Separated from markdown_emitter.py so unit tests run without GCS creds.
"""

from __future__ import annotations

import json

from chaoslab_agent.patcher.recipe import (
    FailureCluster,
    HardeningRecipe,
    PromptPatch,
    RegressionTestCase,
    ToolValidationDiff,
)

# Show at most N span_ids per cluster; the rest collapse to an ellipsis so
# wide clusters don't blow up the Markdown.
_SPAN_ID_PREVIEW = 5


def render_recipe(recipe: HardeningRecipe) -> str:
    parts: list[str] = []
    parts.append(_render_header(recipe))
    parts.append(_render_summary(recipe))
    parts.append(_render_root_causes(recipe))
    parts.append(_render_prompt_patches(recipe))
    parts.append(_render_tool_validation_diffs(recipe))
    parts.append(_render_regression_test_cases(recipe))
    parts.append(_render_estimated_improvement(recipe))
    if recipe.metadata.get("fallback_cluster_ids"):
        parts.append(_render_fallback_notice(recipe))
    return "\n".join(parts)


def _render_header(recipe: HardeningRecipe) -> str:
    pct = recipe.estimated_resilience_improvement * 100
    return (
        f"# ChaosLab Hardening Recipe — {recipe.recipe_id}\n\n"
        f"**Target agent:** `{recipe.target_agent_id}`\n"
        f"**Generated:** {recipe.generated_at}\n"
        f"**Estimated resilience improvement:** {pct:.1f}%\n"
    )


def _render_summary(recipe: HardeningRecipe) -> str:
    clusters = recipe.cluster_set.clusters
    return (
        "## Summary\n\n"
        f"ChaosLab identified {len(clusters)} root cause(s) across "
        f"{sum(c.failure_count for c in clusters)} failed attack runs. "
        f"This recipe applies {len(recipe.prompt_patches)} prompt patch(es) and "
        f"{len(recipe.tool_validation_diffs)} tool validation diff(s).\n"
    )


def _render_root_causes(recipe: HardeningRecipe) -> str:
    body: list[str] = ["## Root Causes\n"]
    for c in recipe.cluster_set.clusters:
        body.append(_render_one_cluster(c))
    return "".join(body)


def _render_one_cluster(c: FailureCluster) -> str:
    preview = c.span_ids[:_SPAN_ID_PREVIEW]
    suffix = " ..." if len(c.span_ids) > _SPAN_ID_PREVIEW else ""
    return (
        f"### {c.cluster_id}\n"
        f"- **Root cause:** {c.root_cause}\n"
        f"- **Failure count:** {c.failure_count}\n"
        f"- **Fault classes:** {', '.join(c.fault_classes)}\n"
        f"- **Affected span IDs:** `{', '.join(preview)}`{suffix}\n\n"
    )


def _render_prompt_patches(recipe: HardeningRecipe) -> str:
    body: list[str] = ["## Prompt Patches\n\n"]
    if not recipe.prompt_patches:
        body.append("_(no prompt patches generated)_\n")
        return "".join(body)
    for p in recipe.prompt_patches:
        body.append(_render_one_prompt_patch(p))
    return "".join(body)


def _render_one_prompt_patch(p: PromptPatch) -> str:
    body: list[str] = [f"**Section:** `{p.section}` | **Operation:** `{p.operation}`\n\n"]
    if p.before is not None:
        body.append("Before:\n```text\n")
        body.append(p.before)
        body.append("\n```\n\n")
    body.append("After:\n```text\n")
    body.append(p.after)
    body.append("\n```\n\n")
    return "".join(body)


def _render_tool_validation_diffs(recipe: HardeningRecipe) -> str:
    body: list[str] = ["## Tool Validation Diffs\n\n"]
    if not recipe.tool_validation_diffs:
        body.append("_(no tool validation diffs generated)_\n")
        return "".join(body)
    for d in recipe.tool_validation_diffs:
        body.append(_render_one_tool_diff(d))
    return "".join(body)


def _render_one_tool_diff(d: ToolValidationDiff) -> str:
    return (
        f"**Tool:** `{d.tool_name}` | **Operation:** `{d.operation}`\n\n"
        "```diff\n"
        f"{d.code_patch}\n"
        "```\n\n"
    )


def _render_regression_test_cases(recipe: HardeningRecipe) -> str:
    body: list[str] = ["## Regression Test Cases\n\n"]
    if not recipe.regression_test_cases:
        body.append("_(no regression test cases)_\n")
        return "".join(body)
    for i, tc in enumerate(recipe.regression_test_cases, 1):
        body.append(_render_one_regression(i, tc))
    return "".join(body)


def _render_one_regression(idx: int, tc: RegressionTestCase) -> str:
    # `model_dump` flattens through the `extra="allow"` field so any Phoenix
    # metadata round-trips into the rendered JSON.
    payload = json.dumps(tc.model_dump(), indent=2)
    return f"{idx}. ```json\n{payload}\n```\n\n"


def _render_estimated_improvement(recipe: HardeningRecipe) -> str:
    pct = recipe.estimated_resilience_improvement * 100
    return (
        "## Estimated Resilience Improvement\n\n"
        f"**{pct:.1f}%** (based on cluster coverage x patch density heuristic; "
        "validated by re-attack phase in ChaosLab's closed loop)\n"
    )


def _render_fallback_notice(recipe: HardeningRecipe) -> str:
    # Audit-fidelity: surface fallback-marked clusters to the reader so a
    # reviewer of the signed recipe can tell pseudoknowledge from real
    # LLM-generated patches.
    cluster_ids = recipe.metadata.get("fallback_cluster_ids", [])
    bullet_list = "\n".join(f"- `{cid}`" for cid in cluster_ids)
    return (
        "## Fallback Clusters\n\n"
        "The following clusters received a generic fallback patch because the "
        "Patcher LLM did not return a valid response. Review these manually "
        "before applying the recipe in production:\n\n"
        f"{bullet_list}\n"
    )


__all__ = ["render_recipe"]
