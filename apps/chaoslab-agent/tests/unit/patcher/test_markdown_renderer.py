"""Pure-function Markdown renderer tests — no GCS, no env vars."""

from __future__ import annotations

import re
from typing import Any

from chaoslab_agent.judge.clustering import FailureClusterSet
from chaoslab_agent.judge.rubrics import FaultClass
from chaoslab_agent.patcher._markdown_renderer import render_recipe
from chaoslab_agent.patcher.recipe import (
    FailureCluster,
    HardeningRecipe,
    PromptPatch,
    RegressionTestCase,
    ToolValidationDiff,
)


def _cluster(
    cluster_id: str = "cluster_a3f7b2c1",
    *,
    span_ids: list[str] | None = None,
    fault_classes: list[FaultClass] | None = None,
    root_cause: str = "no input validation",
) -> FailureCluster:
    return FailureCluster(
        cluster_id=cluster_id,
        root_cause=root_cause,
        failure_count=len(span_ids) if span_ids else 1,
        span_ids=span_ids or ["0123456789abcdef"],
        fault_classes=fault_classes or ["malformed_tool_output"],
    )


def _recipe(**overrides: Any) -> HardeningRecipe:
    default_cluster = _cluster()
    base: dict[str, Any] = {
        "recipe_id": "recipe_abc123def456",
        "target_agent_id": "target_customer_support",
        "generated_at": "2026-06-02T14:30:00Z",
        "cluster_set": FailureClusterSet(clusters=[default_cluster], total_failures=1),
        "prompt_patches": [],
        "tool_validation_diffs": [],
        "regression_test_cases": [],
        "estimated_resilience_improvement": 0.46,
        "metadata": {},
    }
    base.update(overrides)
    return HardeningRecipe(**base)


# ---------------------------------------------------------------------------
# Section headers + recipe_id (BDD line 44-51)
# ---------------------------------------------------------------------------


def test_render_carries_recipe_id_in_header() -> None:
    md = render_recipe(_recipe())
    assert md.startswith("# ChaosLab Hardening Recipe — recipe_abc123def456")


def test_render_contains_every_required_section_header() -> None:
    md = render_recipe(_recipe())
    for header in [
        "## Summary",
        "## Root Causes",
        "## Prompt Patches",
        "## Tool Validation Diffs",
        "## Regression Test Cases",
        "## Estimated Resilience Improvement",
    ]:
        assert header in md, f"missing section: {header}"


def test_render_includes_target_agent_id_and_generated_at() -> None:
    md = render_recipe(_recipe())
    assert "`target_customer_support`" in md
    assert "2026-06-02T14:30:00Z" in md


# ---------------------------------------------------------------------------
# Prompt patches (BDD line 53-55)
# ---------------------------------------------------------------------------


def test_two_prompt_patches_render_two_text_code_blocks() -> None:
    recipe = _recipe(
        prompt_patches=[
            PromptPatch(section="system_prompt", operation="insert", after="A"),
            PromptPatch(section="tool_description", operation="insert", after="B"),
        ]
    )
    md = render_recipe(recipe)
    # Extract the slice between Prompt Patches and the next section header.
    section = md.split("## Prompt Patches")[1].split("## ")[0]
    text_blocks = re.findall(r"```text\n.*?\n```", section, re.DOTALL)
    assert len(text_blocks) == 2


def test_replace_prompt_patch_renders_before_and_after_blocks() -> None:
    recipe = _recipe(
        prompt_patches=[
            PromptPatch(
                section="system_prompt",
                operation="replace",
                before="old text",
                after="new text",
            )
        ]
    )
    md = render_recipe(recipe)
    section = md.split("## Prompt Patches")[1].split("## ")[0]
    assert "old text" in section
    assert "new text" in section


def test_empty_prompt_patches_renders_italic_placeholder() -> None:
    md = render_recipe(_recipe(prompt_patches=[]))
    section = md.split("## Prompt Patches")[1].split("## ")[0]
    assert "_(no prompt patches generated)_" in section


# ---------------------------------------------------------------------------
# Tool validation diffs (BDD line 57-60)
# ---------------------------------------------------------------------------


def test_tool_validation_diff_renders_diff_fence_and_byte_for_byte_patch() -> None:
    patch = "--- a/tools.py\n+++ b/tools.py\n@@ -1,3 +1,5 @@\n+validate(x)"
    recipe = _recipe(
        tool_validation_diffs=[
            ToolValidationDiff(
                tool_name="lookup_order",
                operation="add_input_validator",
                code_patch=patch,
            )
        ]
    )
    md = render_recipe(recipe)
    section = md.split("## Tool Validation Diffs")[1].split("## ")[0]
    assert "```diff" in section
    assert patch in section


def test_empty_tool_validation_diffs_renders_italic_placeholder() -> None:
    md = render_recipe(_recipe(tool_validation_diffs=[]))
    section = md.split("## Tool Validation Diffs")[1].split("## ")[0]
    assert "_(no tool validation diffs generated)_" in section


# ---------------------------------------------------------------------------
# Estimated improvement formatting (BDD line 62-64)
# ---------------------------------------------------------------------------


def test_estimated_improvement_rendered_as_percentage_with_one_decimal() -> None:
    md = render_recipe(_recipe(estimated_resilience_improvement=0.467))
    assert "46.7%" in md


def test_estimated_improvement_zero_renders_zero_percent() -> None:
    md = render_recipe(_recipe(estimated_resilience_improvement=0.0))
    assert "0.0%" in md


def test_estimated_improvement_one_renders_hundred_percent() -> None:
    md = render_recipe(_recipe(estimated_resilience_improvement=1.0))
    assert "100.0%" in md


# ---------------------------------------------------------------------------
# Cluster rendering (BDD line 66-69)
# ---------------------------------------------------------------------------


def test_three_clusters_each_appear_with_cluster_prefix() -> None:
    clusters = [
        _cluster(
            f"cluster_{i:08x}",
            span_ids=[f"{i:016x}"],
            fault_classes=["malformed_tool_output"],
            root_cause=f"root-{i}",
        )
        for i in range(3)
    ]
    recipe = _recipe(
        cluster_set=FailureClusterSet(clusters=clusters, total_failures=3),
    )
    md = render_recipe(recipe)
    # Header (line 1) is `# ChaosLab ... — recipe_...` so the `cluster_`
    # prefix only appears once per cluster in the Root Causes section.
    assert md.count("### cluster_") == 3
    for c in clusters:
        assert c.root_cause in md


def test_cluster_with_more_than_five_span_ids_truncates_with_ellipsis() -> None:
    cluster = _cluster(
        span_ids=[f"{i:016x}" for i in range(7)],
        fault_classes=["malformed_tool_output"],
    )
    recipe = _recipe(
        cluster_set=FailureClusterSet(clusters=[cluster], total_failures=7),
    )
    md = render_recipe(recipe)
    # The first 5 span_ids appear; the remainder collapses to ` ...`
    assert "..." in md.split("Affected span IDs")[1].split("\n")[0]


# ---------------------------------------------------------------------------
# Regression test cases
# ---------------------------------------------------------------------------


def test_regression_test_cases_rendered_as_indexed_json_blocks() -> None:
    recipe = _recipe(
        regression_test_cases=[
            RegressionTestCase(input="lookup X", expected="graceful fallback"),
            RegressionTestCase(input="refund Y", expected="deny then escalate"),
        ]
    )
    md = render_recipe(recipe)
    section = md.split("## Regression Test Cases")[1].split("## ")[0]
    assert "1. ```json" in section
    assert "2. ```json" in section
    # Payload uses model_dump JSON so the keys round-trip cleanly.
    assert '"input": "lookup X"' in section


def test_empty_regression_test_cases_renders_italic_placeholder() -> None:
    md = render_recipe(_recipe(regression_test_cases=[]))
    section = md.split("## Regression Test Cases")[1].split("## ")[0]
    assert "_(no regression test cases)_" in section


# ---------------------------------------------------------------------------
# Fallback notice — audit-fidelity surface
# ---------------------------------------------------------------------------


def test_fallback_metadata_renders_audit_fidelity_section() -> None:
    md = render_recipe(
        _recipe(metadata={"fallback_cluster_ids": ["cluster_aaaaaaaa", "cluster_bbbbbbbb"]})
    )
    assert "## Fallback Clusters" in md
    assert "`cluster_aaaaaaaa`" in md
    assert "`cluster_bbbbbbbb`" in md


def test_happy_path_recipe_omits_fallback_notice() -> None:
    md = render_recipe(_recipe(metadata={}))
    assert "## Fallback Clusters" not in md


# ---------------------------------------------------------------------------
# Renderer is pure
# ---------------------------------------------------------------------------


def test_render_recipe_is_deterministic_for_same_input() -> None:
    recipe = _recipe(
        prompt_patches=[PromptPatch(section="system_prompt", operation="insert", after="x")]
    )
    first = render_recipe(recipe)
    second = render_recipe(recipe)
    assert first == second
