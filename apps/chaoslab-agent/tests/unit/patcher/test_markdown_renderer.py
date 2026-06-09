"""Pure-function Markdown renderer tests — no GCS, no env vars."""

from __future__ import annotations

import re
from typing import Any

import pytest

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
# Section headers + recipe_id
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
# Prompt patches
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
# Tool validation diffs
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
# Estimated improvement formatting
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
# Cluster rendering
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


# ---------------------------------------------------------------------------
# Round-2 regression tests (PR #70 review findings)
# ---------------------------------------------------------------------------


def test_insert_only_patch_does_not_render_a_before_block() -> None:
    recipe = _recipe(
        prompt_patches=[
            PromptPatch(section="system_prompt", operation="insert", after="x"),
        ]
    )
    md = render_recipe(recipe)
    section = md.split("## Prompt Patches")[1].split("## ")[0]
    assert "Before:" not in section


def test_exactly_five_span_ids_no_ellipsis() -> None:
    cluster = _cluster(span_ids=[f"{i:016x}" for i in range(5)])
    recipe = _recipe(
        cluster_set=FailureClusterSet(clusters=[cluster], total_failures=5),
    )
    md = render_recipe(recipe)
    span_line = md.split("Affected span IDs")[1].split("\n")[0]
    assert "..." not in span_line
    assert "more" not in span_line


def test_six_span_ids_renders_plus_n_more_suffix() -> None:
    cluster = _cluster(span_ids=[f"{i:016x}" for i in range(6)])
    recipe = _recipe(
        cluster_set=FailureClusterSet(clusters=[cluster], total_failures=6),
    )
    md = render_recipe(recipe)
    span_line = md.split("Affected span IDs")[1].split("\n")[0]
    assert "(+1 more)" in span_line


def test_fallback_metadata_with_unknown_cluster_id_logs_warning(
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Audit-fidelity: a `fallback_cluster_ids` entry that doesn't map to any
    # cluster in the recipe is a data-integrity bug upstream; the renderer
    # should still emit the notice but log a warning so the bug surfaces.
    recipe = _recipe(metadata={"fallback_cluster_ids": ["cluster_99999999"]})
    with caplog.at_level("WARNING"):
        md = render_recipe(recipe)
    assert "## Fallback Clusters" in md
    assert any("unknown cluster_id" in r.message for r in caplog.records)


def test_regression_case_with_non_json_native_value_renders_via_str(
    caplog: pytest.LogCaptureFixture,
) -> None:
    # `extra="allow"` lets a Phoenix metadata column carry a non-JSON
    # scalar (e.g. datetime / set). Render lossy via str() rather than
    # crashing the whole recipe; warn so the coercion shows up in logs.
    from datetime import datetime

    tc = RegressionTestCase(
        input="x",
        expected="y",
        recorded_at=datetime(2026, 6, 9, 12, 0, 0),  # ty: ignore[unknown-argument]
    )
    recipe = _recipe(regression_test_cases=[tc])
    with caplog.at_level("WARNING"):
        md = render_recipe(recipe)
    section = md.split("## Regression Test Cases")[1].split("## ")[0]
    assert "2026-06-09" in section
    assert any("coerced via str" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# Round-3 regression tests (PR #70 post-merge verification findings)
# ---------------------------------------------------------------------------


def test_fallback_cluster_ids_string_does_not_corrupt_output(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """If a future caller passes the string `"all"`, the renderer must not
    iterate characters and silently corrupt the audit Markdown."""
    recipe = _recipe(metadata={"fallback_cluster_ids": "all"})
    with caplog.at_level("ERROR"):
        md = render_recipe(recipe)
    assert "## Fallback Clusters" not in md
    assert "- a" not in md
    assert any("must be a list" in r.message for r in caplog.records)


def test_regression_case_with_hostile_str_falls_back_to_placeholder(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A hostile __str__ inside an extras column must not crash the whole render."""

    class HostileRepr:
        def __str__(self) -> str:
            raise RuntimeError("hostile __str__")

    tc = RegressionTestCase(
        input="x",
        expected="y",
        hostile_field=HostileRepr(),  # ty: ignore[unknown-argument]
    )
    recipe = _recipe(regression_test_cases=[tc])
    with caplog.at_level("WARNING"):
        md = render_recipe(recipe)
    section = md.split("## Regression Test Cases")[1].split("## ")[0]
    assert "<unrenderable HostileRepr>" in section
    assert any("hostile" in r.message.lower() or "__str__" in r.message for r in caplog.records)
