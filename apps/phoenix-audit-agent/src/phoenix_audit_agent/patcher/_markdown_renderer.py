"""Pure-function Markdown rendering for HardeningRecipe.

Separated from markdown_emitter.py so unit tests run without GCS creds.
"""

from __future__ import annotations

import json
import logging

from phoenix_audit_agent.patcher.recipe import (
    FailureCluster,
    HardeningRecipe,
    PromptPatch,
    RegressionTestCase,
    ToolValidationDiff,
)

logger = logging.getLogger(__name__)

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
        f"# PhoenixAudit Hardening Recipe — {recipe.recipe_id}\n\n"
        f"**Target agent:** `{recipe.target_agent_id}`\n"
        f"**Generated:** {recipe.generated_at}\n"
        f"**Estimated resilience improvement:** {pct:.1f}%\n"
    )


def _render_summary(recipe: HardeningRecipe) -> str:
    clusters = recipe.cluster_set.clusters
    return (
        "## Summary\n\n"
        f"PhoenixAudit identified {len(clusters)} root cause(s) across "
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
    extra = len(c.span_ids) - _SPAN_ID_PREVIEW
    # Make the suppression auditable — `... (+N more)` is grep-able and
    # tells a reviewer how big the elided tail actually was.
    suffix = f" ... (+{extra} more)" if extra > 0 else ""
    # FailureCluster.fault_classes has min_length=1 at the schema level,
    # but render defensively in case a future relaxation slips through.
    fault_classes = ", ".join(c.fault_classes) if c.fault_classes else "_(unclassified)_"
    return (
        f"### {c.cluster_id}\n"
        f"- **Root cause:** {c.root_cause}\n"
        f"- **Failure count:** {c.failure_count}\n"
        f"- **Fault classes:** {fault_classes}\n"
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
    # Pydantic extras carry Phoenix metadata; `default=` coerces non-JSON
    # scalars (datetime, bytes, set) lossy rather than crashing the render.
    payload = json.dumps(tc.model_dump(), indent=2, default=_json_default_with_warning)
    return f"{idx}. ```json\n{payload}\n```\n\n"


def _json_default_with_warning(obj: object) -> str:
    type_name = type(obj).__name__
    logger.warning("regression_test_case extra type=%s coerced via str()", type_name)
    try:
        return str(obj)
    except Exception:
        # A hostile __str__ would otherwise kill the whole recipe render.
        logger.exception("regression_test_case __str__ raised on type=%s", type_name)
        return f"<unrenderable {type_name}>"


def _render_estimated_improvement(recipe: HardeningRecipe) -> str:
    pct = recipe.estimated_resilience_improvement * 100
    return (
        "## Estimated Resilience Improvement\n\n"
        f"**{pct:.1f}%** (based on cluster coverage x patch density heuristic; "
        "validated by re-attack phase in PhoenixAudit's closed loop)\n"
    )


def _render_fallback_notice(recipe: HardeningRecipe) -> str:
    # Audit-fidelity: surface fallback-marked clusters to the reader so a
    # reviewer of the signed recipe can tell pseudoknowledge from real
    # LLM-generated patches.
    raw = recipe.metadata.get("fallback_cluster_ids", []) or []
    # A non-list (e.g. the string "all") would otherwise iterate character
    # by character into bullet points and silently corrupt the audit.
    if not isinstance(raw, list):
        logger.error(
            "fallback_cluster_ids must be a list, got type=%s; ignoring",
            type(raw).__name__,
        )
        # Render the corruption IN-BAND so the regulator reading the signed
        # recipe sees the integrity warning — not just an Operator grepping
        # Cloud Logging after the fact. Silent return ("") was pattern #4
        # from docs/architecture.md: fallback indistinguishable from "no fallback at all."
        return (
            "## Fallback Clusters\n\n"
            "_(audit-integrity warning: `metadata.fallback_cluster_ids` was "
            f"`{type(raw).__name__}`, expected `list`; corruption logged at "
            "ERROR. Treat this recipe as suspect until the upstream Patcher "
            "issue is identified.)_\n"
        )
    cluster_ids = [str(cid) for cid in raw]
    valid_cluster_ids = {c.cluster_id for c in recipe.cluster_set.clusters}
    unknown = [cid for cid in cluster_ids if cid not in valid_cluster_ids]
    if unknown:
        # A fallback_cluster_id that doesn't correspond to any cluster in
        # the recipe is a data-integrity bug upstream; warn so the
        # Patcher pipeline shows up in logs rather than silently producing
        # a misleading Markdown.
        logger.warning(
            "fallback_cluster_ids references unknown cluster_id(s): %s",
            ", ".join(unknown),
        )
    bullet_list = "\n".join(f"- `{cid}`" for cid in cluster_ids)
    return (
        "## Fallback Clusters\n\n"
        "The following clusters received a generic fallback patch because the "
        "Patcher LLM did not return a valid response. Review these manually "
        "before applying the recipe in production:\n\n"
        f"{bullet_list}\n"
    )


__all__ = ["render_recipe"]
