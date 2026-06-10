"""HardeningRecipe JSON Schema export contract."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import jsonschema
import pytest

from phoenix_audit_agent.patcher.recipe import (
    FailureCluster,
    FailureClusterSet,
    HardeningRecipe,
    PromptPatch,
    RegressionTestCase,
    ToolValidationDiff,
)

REPO_ROOT = Path(__file__).resolve().parents[5]
SCHEMA_PATH = REPO_ROOT / "packages/shared-types/hardening-recipe.json"


def _run_export() -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts/export_recipe_schema.py")],
        check=True,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )


@pytest.fixture(scope="module")
def exported_schema() -> dict[str, object]:
    # Regenerate to guarantee parity with the live pydantic model — a stale
    # committed JSON file would otherwise mask a schema-drift bug.
    _run_export()
    return json.loads(SCHEMA_PATH.read_text())


def test_exported_file_exists(exported_schema: dict[str, object]) -> None:
    assert SCHEMA_PATH.is_file()
    assert exported_schema


def test_exported_schema_is_valid_draft_2020_12(
    exported_schema: dict[str, object],
) -> None:
    jsonschema.Draft202012Validator.check_schema(exported_schema)


def test_exported_schema_carries_required_defs(
    exported_schema: dict[str, object],
) -> None:
    defs = exported_schema.get("$defs", {})
    assert isinstance(defs, dict)
    required = {
        "FailureCluster",
        "FailureClusterSet",
        "PromptPatch",
        "RegressionTestCase",
        "ToolValidationDiff",
    }
    missing = required - set(defs.keys())
    assert not missing, f"missing $defs: {missing}"


def test_exported_schema_top_level_properties(
    exported_schema: dict[str, object],
) -> None:
    props = exported_schema.get("properties", {})
    assert isinstance(props, dict)
    required = {
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
    missing = required - set(props.keys())
    assert not missing, f"missing top-level properties: {missing}"


def test_exported_schema_is_deterministically_sorted(
    exported_schema: dict[str, object],
) -> None:
    _run_export()
    after = SCHEMA_PATH.read_text()
    assert after.endswith("\n")
    canonical = json.dumps(json.loads(after), indent=2, sort_keys=True) + "\n"
    assert after == canonical


def test_exported_schema_required_set_matches_declared(
    exported_schema: dict[str, object],
) -> None:
    # pydantic's `required` list is field-declaration order; the byte-
    # determinism test catches order drift on a single Python version,
    # this set-based test catches the cross-version drift sort_keys can't.
    required = exported_schema.get("required", [])
    assert isinstance(required, list)
    expected = {
        "recipe_id",
        "target_agent_id",
        "generated_at",
        "cluster_set",
        "estimated_resilience_improvement",
    }
    assert set(required) == expected, f"required drifted: {sorted(required)}"


def test_recipe_instance_round_trips_through_exported_schema(
    exported_schema: dict[str, object],
) -> None:
    cluster = FailureCluster(
        cluster_id="cluster_a3f7b2c1",
        root_cause="no input validation",
        failure_count=1,
        span_ids=["0123456789abcdef"],
        fault_classes=["malformed_tool_output"],
    )
    recipe = HardeningRecipe(
        recipe_id="recipe_abc123def456",
        target_agent_id="target_customer_support",
        generated_at="2026-06-02T14:30:00Z",
        cluster_set=FailureClusterSet(clusters=[cluster], total_failures=1),
        prompt_patches=[
            PromptPatch(
                section="system_prompt",
                operation="insert",
                before=None,
                after="TOOL OUTPUT VALIDATION RULES...",
            )
        ],
        tool_validation_diffs=[
            ToolValidationDiff(
                tool_name="lookup_order",
                operation="add_input_validator",
                code_patch="--- a/tools.py\n+++ b/tools.py\n@@ ...",
            )
        ],
        regression_test_cases=[RegressionTestCase(input="lookup X", expected="graceful fallback")],
        estimated_resilience_improvement=0.46,
        metadata={"cycle_id": "phoenix-audit-2026-06-08T14:30:00Z"},
    )
    payload = json.loads(recipe.model_dump_json())
    jsonschema.validate(payload, exported_schema)
