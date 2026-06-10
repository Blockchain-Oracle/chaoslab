"""Shared fixtures + helpers for the GitLab-emitter / MCP-client test modules.

Split out from `test_gitlab_emitter.py` (round-3) so each behavior-grouped
test file stays under the 400-line guideline. The fixtures here are the
same across `test_gitlab_emitter_*.py` and `test_gitlab_mcp_client_*.py`.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from phoenix_audit_agent.config import get_settings
from phoenix_audit_agent.judge.clustering import FailureClusterSet
from phoenix_audit_agent.patcher.recipe import (
    FailureCluster,
    HardeningRecipe,
    PromptPatch,
    RegressionTestCase,
    ToolValidationDiff,
)

OFFICIAL_ENDPOINT = "https://gitlab.com/api/v4/mcp"


@pytest.fixture(autouse=True)
def _vertex_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep Settings() defaults deterministic across patcher tests."""
    monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "true")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")
    monkeypatch.setenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    get_settings.cache_clear()


def make_recipe(
    *,
    tool_diffs: list[ToolValidationDiff] | None = None,
    prompt_patches: list[PromptPatch] | None = None,
    regression_cases: list[RegressionTestCase] | None = None,
) -> HardeningRecipe:
    """Build a canonical HardeningRecipe — `recipe_abc123def456` + one cluster."""
    cluster = FailureCluster(
        cluster_id="cluster_a3f7b2c1",
        root_cause="no input validation",
        failure_count=1,
        span_ids=["0123456789abcdef"],
        fault_classes=["malformed_tool_output"],
    )
    return HardeningRecipe(
        recipe_id="recipe_abc123def456",
        target_agent_id="target_customer_support",
        generated_at="2026-06-02T14:30:00Z",
        cluster_set=FailureClusterSet(clusters=[cluster], total_failures=1),
        prompt_patches=prompt_patches or [],
        tool_validation_diffs=tool_diffs or [],
        regression_test_cases=regression_cases or [],
        estimated_resilience_improvement=0.46,
    )


def make_fake_project() -> MagicMock:
    """MagicMock standing in for a python-gitlab Project.

    Records `.branches.create({...})` / `.branches.delete(...)` /
    `.commits.create({...})` calls so tests can assert on the payload
    shape without touching gitlab.com.
    """
    project = MagicMock()
    project.branches = MagicMock()
    project.branches.create = MagicMock(return_value=MagicMock())
    project.branches.delete = MagicMock(return_value=None)
    project.commits = MagicMock()
    project.commits.create = MagicMock(return_value=MagicMock())
    return project


def make_mcp_success_response(
    *, iid: int = 42, project_path: str = "abu-phoenix-audit/test-target"
) -> dict[str, Any]:
    """JSON-RPC `tools/call` success envelope for `create_merge_request`."""
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "iid": iid,
            "web_url": f"https://gitlab.com/{project_path}/-/merge_requests/{iid}",
            "state": "opened",
        },
    }


__all__ = [
    "OFFICIAL_ENDPOINT",
    "make_fake_project",
    "make_mcp_success_response",
    "make_recipe",
]
