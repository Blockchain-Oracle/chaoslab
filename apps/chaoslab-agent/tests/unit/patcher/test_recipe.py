"""HardeningRecipe + sub-schema pydantic validation tests."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from chaoslab_agent.patcher.recipe import (
    FailureCluster,
    FailureClusterSet,
    HardeningRecipe,
    PromptPatch,
    RegressionTestCase,
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


def _cluster_set() -> FailureClusterSet:
    return FailureClusterSet(clusters=[_cluster()], total_failures=1)


def _recipe(**overrides: object) -> HardeningRecipe:
    base: dict[str, object] = {
        "recipe_id": "recipe_abc123def456",
        "target_agent_id": "target_customer_support",
        "generated_at": "2026-06-02T14:30:00Z",
        "cluster_set": _cluster_set(),
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


def test_recipe_rejects_thirteen_char_recipe_id() -> None:
    # Regex `^recipe_[a-z0-9]{12}$` must reject above-boundary too, not just
    # below — the `$` anchor is the load-bearing piece.
    with pytest.raises(ValidationError):
        _recipe(recipe_id="recipe_abc123def4567")


def test_recipe_rejects_empty_target_agent_id() -> None:
    with pytest.raises(ValidationError):
        _recipe(target_agent_id="")


def test_recipe_defaults_when_optional_lists_omitted() -> None:
    r = _recipe()
    assert r.prompt_patches == []
    assert r.tool_validation_diffs == []
    assert r.regression_test_cases == []
    assert r.metadata == {}


def test_recipe_rejects_non_iso_8601_generated_at() -> None:
    with pytest.raises(ValidationError, match="ISO 8601"):
        _recipe(generated_at="NOT_A_DATE")


def test_recipe_rejects_garbage_short_generated_at() -> None:
    with pytest.raises(ValidationError, match="ISO 8601"):
        _recipe(generated_at="x")


def test_recipe_rejects_impossible_day_number_in_generated_at() -> None:
    with pytest.raises(ValidationError, match="ISO 8601"):
        _recipe(generated_at="2026-06-32T14:30:00Z")


def test_recipe_accepts_offset_form_generated_at() -> None:
    r = _recipe(generated_at="2026-06-02T14:30:00+02:00")
    assert r.generated_at == "2026-06-02T14:30:00+02:00"


def test_recipe_rejects_metadata_shadowing_top_level_field() -> None:
    with pytest.raises(ValidationError, match="shadow top-level"):
        _recipe(metadata={"recipe_id": "tampered"})


def test_recipe_metadata_with_safe_keys_passes() -> None:
    r = _recipe(metadata={"cycle_id": "x", "audit_round": 3})
    assert r.metadata == {"cycle_id": "x", "audit_round": 3}


def test_recipe_rejects_partition_violating_cluster_set() -> None:
    # The clusterer's FailureClusterSet enforces span_id mutual exclusion
    # — re-using it on the recipe means a partition violation here is
    # caught before the recipe is signed.
    with pytest.raises(ValidationError, match="multiple clusters"):
        FailureClusterSet(
            clusters=[
                FailureCluster(
                    cluster_id="cluster_aaaaaaaa",
                    root_cause="r1",
                    failure_count=1,
                    span_ids=["dupe"],
                    fault_classes=["malformed_tool_output"],
                ),
                FailureCluster(
                    cluster_id="cluster_bbbbbbbb",
                    root_cause="r2",
                    failure_count=1,
                    span_ids=["dupe"],
                    fault_classes=["prompt_injection"],
                ),
            ],
            total_failures=2,
        )


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


def test_failure_cluster_rejects_unknown_fault_class_value() -> None:
    # Symmetry with PromptPatch.section / ToolValidationDiff.operation
    # negative tests — a future FaultClass drift would surface here.
    with pytest.raises(ValidationError):
        FailureCluster(
            cluster_id="cluster_a3f7b2c1",
            root_cause="multi-cause",
            failure_count=1,
            span_ids=["s1"],
            fault_classes=["sql_injection"],  # ty: ignore[invalid-argument-type]
        )


# ---------------------------------------------------------------------------
# RegressionTestCase
# ---------------------------------------------------------------------------


def test_regression_test_case_accepts_required_keys() -> None:
    r = RegressionTestCase(input="lookup X", expected="graceful fallback")
    assert r.input == "lookup X"
    assert r.expected == "graceful fallback"


def test_regression_test_case_rejects_empty_input() -> None:
    with pytest.raises(ValidationError):
        RegressionTestCase(input="", expected="ok")


def test_regression_test_case_rejects_empty_expected() -> None:
    with pytest.raises(ValidationError):
        RegressionTestCase(input="lookup X", expected="")


def test_regression_test_case_allows_phoenix_extra_metadata() -> None:
    # `extra="allow"` keeps Phoenix dataset metadata round-tripping without
    # forcing the schema to know every downstream column.
    r = RegressionTestCase(
        input="x",
        expected="y",
        tags=["smoke"],  # ty: ignore[unknown-argument]
    )
    assert r.input == "x"


# ---------------------------------------------------------------------------
# Frozen sub-types — protect signed-artifact invariants
# ---------------------------------------------------------------------------


def test_prompt_patch_is_frozen() -> None:
    p = PromptPatch(section="system_prompt", operation="insert", after="x")
    with pytest.raises(ValidationError):
        p.after = "tampered"  # type: ignore[misc]


def test_tool_validation_diff_is_frozen() -> None:
    t = ToolValidationDiff(
        tool_name="lookup_order",
        operation="add_input_validator",
        code_patch="--- a\n+++ b\n@@ ...",
    )
    with pytest.raises(ValidationError):
        t.tool_name = "tampered"  # type: ignore[misc]
