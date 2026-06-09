"""HardeningRecipe + sub-schema pydantic validation tests."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from chaoslab_agent.patcher.recipe import (
    FailureCluster,
    HardeningRecipe,
    PromptPatch,
    ToolValidationDiff,
    new_recipe_id,
)


def _cluster() -> FailureCluster:
    return FailureCluster(
        cluster_id="cluster_a3f7b2c1",
        root_cause="no input validation",
        failure_count=1,
        span_ids=["0123456789abcdef"],
        fault_classes=["malformed_tool_output"],
    )


def _recipe(**overrides: object) -> HardeningRecipe:
    base: dict[str, object] = {
        "recipe_id": "recipe_abc123def456",
        "target_agent_id": "target_customer_support",
        "generated_at": "2026-06-02T14:30:00Z",
        "cluster_set": [_cluster()],
        "estimated_resilience_improvement": 0.46,
    }
    base.update(overrides)
    return HardeningRecipe(**base)  # ty: ignore[invalid-argument-type]


# ---------------------------------------------------------------------------
# HardeningRecipe regex + bounds
# ---------------------------------------------------------------------------


def test_recipe_id_pattern_matches_12_hex_chars() -> None:
    r = _recipe()
    assert r.recipe_id == "recipe_abc123def456"


def test_recipe_id_rejects_uppercase() -> None:
    with pytest.raises(ValidationError):
        _recipe(recipe_id="recipe_ABC123DEF456")


def test_recipe_id_rejects_wrong_length() -> None:
    with pytest.raises(ValidationError):
        _recipe(recipe_id="recipe_abc123")


def test_new_recipe_id_round_trips_through_schema() -> None:
    rid = new_recipe_id()
    assert len(rid) == len("recipe_") + 12
    _recipe(recipe_id=rid)


def test_estimated_improvement_rejects_above_one() -> None:
    with pytest.raises(ValidationError):
        _recipe(estimated_resilience_improvement=1.5)


def test_estimated_improvement_rejects_negative() -> None:
    with pytest.raises(ValidationError):
        _recipe(estimated_resilience_improvement=-0.1)


def test_estimated_improvement_accepts_boundary_values() -> None:
    assert _recipe(estimated_resilience_improvement=0.0).estimated_resilience_improvement == 0.0
    assert _recipe(estimated_resilience_improvement=1.0).estimated_resilience_improvement == 1.0


def test_recipe_is_frozen() -> None:
    r = _recipe()
    with pytest.raises(ValidationError):
        r.target_agent_id = "tampered"  # type: ignore[misc]


def test_recipe_requires_at_least_one_cluster() -> None:
    with pytest.raises(ValidationError):
        _recipe(cluster_set=[])


# ---------------------------------------------------------------------------
# PromptPatch — section/operation Literal + replace-needs-before
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("section", ["system_prompt", "tool_description", "few_shot_example"])
def test_prompt_patch_accepts_every_section(section: str) -> None:
    PromptPatch(section=section, operation="insert", after="x")  # ty: ignore[invalid-argument-type]


def test_prompt_patch_rejects_unknown_section() -> None:
    with pytest.raises(ValidationError):
        PromptPatch(
            section="invalid_section",  # ty: ignore[invalid-argument-type]
            operation="insert",
            after="x",
        )


@pytest.mark.parametrize("operation", ["insert", "append"])
def test_prompt_patch_insert_and_append_omit_before(operation: str) -> None:
    PromptPatch(
        section="system_prompt",
        operation=operation,  # ty: ignore[invalid-argument-type]
        before=None,
        after="x",
    )


def test_prompt_patch_replace_requires_before() -> None:
    with pytest.raises(ValidationError, match="before is required"):
        PromptPatch(
            section="system_prompt",
            operation="replace",
            before=None,
            after="x",
        )


def test_prompt_patch_replace_with_before_passes() -> None:
    p = PromptPatch(
        section="system_prompt",
        operation="replace",
        before="old text",
        after="new text",
    )
    assert p.before == "old text"


def test_prompt_patch_after_must_be_non_empty() -> None:
    with pytest.raises(ValidationError):
        PromptPatch(section="system_prompt", operation="insert", after="")


# ---------------------------------------------------------------------------
# ToolValidationDiff — every Literal operation + non-empty patch
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "operation",
    [
        "add_input_validator",
        "add_output_validator",
        "add_retry_policy",
        "add_timeout",
    ],
)
def test_tool_validation_diff_accepts_every_operation(operation: str) -> None:
    ToolValidationDiff(
        tool_name="lookup_order",
        operation=operation,  # ty: ignore[invalid-argument-type]
        code_patch="--- a\n+++ b\n@@ ...",
    )


def test_tool_validation_diff_rejects_unknown_operation() -> None:
    with pytest.raises(ValidationError):
        ToolValidationDiff(
            tool_name="lookup_order",
            operation="evict_cache",  # ty: ignore[invalid-argument-type]
            code_patch="--- a\n+++ b\n@@ ...",
        )


def test_tool_validation_diff_rejects_empty_code_patch() -> None:
    with pytest.raises(ValidationError):
        ToolValidationDiff(
            tool_name="lookup_order",
            operation="add_input_validator",
            code_patch="",
        )


def test_tool_validation_diff_rejects_empty_tool_name() -> None:
    with pytest.raises(ValidationError):
        ToolValidationDiff(
            tool_name="",
            operation="add_input_validator",
            code_patch="--- a\n+++ b\n@@ ...",
        )


# ---------------------------------------------------------------------------
# FailureCluster reuse — every FaultClass value
# ---------------------------------------------------------------------------


def test_failure_cluster_accepts_all_four_fault_classes() -> None:
    c = FailureCluster(
        cluster_id="cluster_a3f7b2c1",
        root_cause="multi-cause",
        failure_count=4,
        span_ids=["s1", "s2", "s3", "s4"],
        fault_classes=[
            "malformed_tool_output",
            "prompt_injection",
            "context_poisoning",
            "latency_spike",
        ],
    )
    assert len(c.fault_classes) == 4
