"""Integration tests for GitLabMREmitter — hits real GitLab.com.

Gated by `@pytest.mark.online` + `@pytest.mark.integration`. CI skips by
default; run locally with `GITLAB_TOKEN` + `GITLAB_TEST_PROJECT_ID` set:

    GITLAB_TOKEN=glpat-... GITLAB_TEST_PROJECT_ID=abu-chaoslab/test-target \\
        uv run pytest apps/chaoslab-agent/tests/integration/test_gitlab_emitter_online.py \\
        -v -m online

The test project must:
- exist on gitlab.com
- have `main` as its default branch
- have at least one initial commit so branch creation can use `main` as ref
- the token's user must have Developer or higher access

Cleanup policy (TQ-LOW #32): default is preserve (judges may want to inspect
the artifacts post-run). Set `GITLAB_TEST_CLEANUP=1` to close MRs + delete
branches at session-finish — useful when iterating locally and the test
project would otherwise accumulate cruft against gitlab.com's per-project MR
cap + per-token rate limits.
"""

from __future__ import annotations

import os
import re
import uuid

import pytest

from chaoslab_agent.config import get_settings
from chaoslab_agent.judge.clustering import FailureClusterSet
from chaoslab_agent.patcher.gitlab_emitter import (
    GitLabEmitResult,
    GitLabMREmitter,
)
from chaoslab_agent.patcher.recipe import (
    FailureCluster,
    HardeningRecipe,
    PromptPatch,
    RegressionTestCase,
    ToolValidationDiff,
)

# Both markers — `online` for cost/IO gating, `integration` for grouping.
pytestmark = [pytest.mark.online, pytest.mark.integration]

_GITLAB_TOKEN = os.environ.get("GITLAB_TOKEN")
_TEST_PROJECT_ID = os.environ.get("GITLAB_TEST_PROJECT_ID")
_CLEANUP_ENABLED = os.environ.get("GITLAB_TEST_CLEANUP") == "1"
_REQUIRED_ENV_MISSING = pytest.mark.skipif(
    not (_GITLAB_TOKEN and _TEST_PROJECT_ID),
    reason="GITLAB_TOKEN + GITLAB_TEST_PROJECT_ID must be set for online tests",
)


# Session-wide registry of (branch_name, mr_iid) created by the tests below.
# Populated by individual tests after emit() succeeds; consumed by the
# autouse session-finalizer fixture when GITLAB_TEST_CLEANUP=1.
_session_cleanup: list[tuple[str, int]] = []


@pytest.fixture(scope="session", autouse=True)
def _gitlab_test_cleanup():
    """Close MRs + delete branches created during the session if cleanup is opted in.

    Default OFF preserves the judge-inspection workflow. Set GITLAB_TEST_CLEANUP=1
    locally to keep the test project tidy. Never raises; cleanup failures are
    logged so a broken cleanup never masks a real test failure."""
    import logging
    from urllib.parse import quote

    import httpx as _httpx

    yield
    if not _CLEANUP_ENABLED or not (_GITLAB_TOKEN and _TEST_PROJECT_ID and _session_cleanup):
        return
    project_enc = quote(_TEST_PROJECT_ID, safe="")
    headers = {"PRIVATE-TOKEN": _GITLAB_TOKEN}
    log = logging.getLogger(__name__)
    with _httpx.Client(timeout=15.0) as http:
        for branch_name, mr_iid in _session_cleanup:
            try:
                http.put(
                    f"https://gitlab.com/api/v4/projects/{project_enc}/merge_requests/{mr_iid}",
                    headers=headers,
                    json={"state_event": "close"},
                )
                http.delete(
                    f"https://gitlab.com/api/v4/projects/{project_enc}/repository/branches/"
                    f"{quote(branch_name, safe='')}",
                    headers=headers,
                )
            except Exception:
                log.exception("gitlab_test_cleanup_failed branch=%s mr_iid=%d", branch_name, mr_iid)


def _unique_recipe_id() -> str:
    # 12 hex chars per HardeningRecipe.recipe_id pattern. uuid4().hex[:12] is
    # collision-safe for the integration test cadence (≪ 2^48 per session).
    return f"recipe_{uuid.uuid4().hex[:12]}"


def _recipe(*, recipe_id: str | None = None) -> HardeningRecipe:
    rid = recipe_id or _unique_recipe_id()
    cluster = FailureCluster(
        cluster_id="cluster_a3f7b2c1",
        root_cause="no input validation on customer_lookup",
        failure_count=3,
        span_ids=["0123456789abcdef", "fedcba9876543210", "abcdef0123456789"],
        fault_classes=["malformed_tool_output"],
    )
    return HardeningRecipe(
        recipe_id=rid,
        target_agent_id="target_customer_support",
        generated_at="2026-06-09T17:00:00Z",
        cluster_set=FailureClusterSet(clusters=[cluster], total_failures=3),
        prompt_patches=[
            PromptPatch(
                section="system_prompt",
                operation="append",
                after=(
                    "Always validate that customer_id matches r'^cust_[0-9]+$' "
                    "before calling lookup."
                ),
            ),
        ],
        tool_validation_diffs=[
            ToolValidationDiff(
                tool_name="customer_lookup",
                operation="add_input_validator",
                code_patch=(
                    "--- a/tools/customer_lookup.py\n"
                    "+++ b/tools/customer_lookup.py\n"
                    "@@ -1,3 +1,7 @@\n"
                    " def customer_lookup(customer_id: str) -> dict:\n"
                    "+    import re\n"
                    "+    if not re.fullmatch(r'cust_[0-9]+', customer_id):\n"
                    "+        raise ValueError(f'invalid customer_id: {customer_id!r}')\n"
                    "     return _backend.lookup(customer_id)\n"
                ),
            ),
        ],
        regression_test_cases=[
            RegressionTestCase(
                input="lookup customer ; rm -rf /",
                expected="ValueError: invalid customer_id",
            ),
        ],
        estimated_resilience_improvement=0.62,
    )


@_REQUIRED_ENV_MISSING
async def test_online_emit_returns_real_mr_url() -> None:
    """Round-trip: real branch, real commits, real MR. URL pattern locked."""
    # Make sure get_settings picks up the env-provided GITLAB_TOKEN. The
    # autouse fixture pattern from unit tests doesn't apply here (we WANT
    # real env to flow through).
    get_settings.cache_clear()

    recipe = _recipe()
    emitter = GitLabMREmitter()  # uses default REST + MCP clients from Settings
    result = await emitter.emit(recipe, project_id=_TEST_PROJECT_ID or "")  # type: ignore[arg-type]
    _session_cleanup.append((result.branch_name, result.mr_iid))

    assert isinstance(result, GitLabEmitResult)
    assert re.fullmatch(r"https://gitlab\.com/.+/-/merge_requests/\d+", result.mr_url)
    assert result.mr_iid >= 1
    assert result.branch_name.startswith("chaoslab/recipe-")
    assert result.recipe_id == recipe.recipe_id


@_REQUIRED_ENV_MISSING
async def test_online_emit_commits_recipe_markdown_and_diff_files() -> None:
    """The MR branch contains the expected file paths: Markdown + diff + regression JSON."""
    import httpx

    get_settings.cache_clear()
    recipe = _recipe()
    emitter = GitLabMREmitter()
    result = await emitter.emit(recipe, project_id=_TEST_PROJECT_ID or "")  # type: ignore[arg-type]
    _session_cleanup.append((result.branch_name, result.mr_iid))

    # Fetch the branch's tree via REST to assert files landed. URL-encode the
    # project id since it may contain `/`.
    from urllib.parse import quote

    project_id_enc = quote(_TEST_PROJECT_ID or "", safe="")
    headers = {"PRIVATE-TOKEN": _GITLAB_TOKEN or ""}
    async with httpx.AsyncClient(timeout=15.0) as http:
        # List tree at the branch tip — flat structure under `chaoslab/`.
        tree_response = await http.get(
            f"https://gitlab.com/api/v4/projects/{project_id_enc}/repository/tree",
            params={"ref": result.branch_name, "recursive": "true", "path": "chaoslab"},
            headers=headers,
        )
        tree_response.raise_for_status()
        paths = {item["path"] for item in tree_response.json()}

    assert f"chaoslab/patches/{recipe.recipe_id}.md" in paths
    assert any(
        p.startswith(f"chaoslab/patches/diffs/{recipe.recipe_id}_") and p.endswith(".diff")
        for p in paths
    )
    assert f"chaoslab/regression_tests/{recipe.recipe_id}.json" in paths


@_REQUIRED_ENV_MISSING
async def test_online_emit_mr_description_visible_on_gitlab() -> None:
    """Fetch the MR via REST and confirm the description contains the rendered Markdown."""
    import httpx

    from chaoslab_agent.patcher._markdown_renderer import render_recipe

    get_settings.cache_clear()
    recipe = _recipe()
    emitter = GitLabMREmitter()
    result = await emitter.emit(recipe, project_id=_TEST_PROJECT_ID or "")  # type: ignore[arg-type]
    _session_cleanup.append((result.branch_name, result.mr_iid))

    from urllib.parse import quote

    project_id_enc = quote(_TEST_PROJECT_ID or "", safe="")
    headers = {"PRIVATE-TOKEN": _GITLAB_TOKEN or ""}
    async with httpx.AsyncClient(timeout=15.0) as http:
        mr_response = await http.get(
            f"https://gitlab.com/api/v4/projects/{project_id_enc}/merge_requests/{result.mr_iid}",
            headers=headers,
        )
        mr_response.raise_for_status()
        mr_body = mr_response.json()

    assert mr_body["state"] == "opened"
    description = mr_body["description"]
    assert recipe.recipe_id in description
    assert render_recipe(recipe) in description
    assert "chaoslab" in mr_body.get("labels", [])
