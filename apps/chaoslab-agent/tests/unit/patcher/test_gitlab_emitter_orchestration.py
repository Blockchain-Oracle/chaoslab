"""GitLab emitter — happy-path orchestration + result shape + hybrid split lock.

Failure-path tests (rollback, cause chains, sanitization, ADR-011 endpoint
mismatch) live in test_gitlab_emitter_failure_paths.py.
"""

from __future__ import annotations

import json
import re

import httpx
import pytest
import respx

from chaoslab_agent.config import get_settings
from chaoslab_agent.patcher.recipe import RegressionTestCase, ToolValidationDiff

from .conftest import (
    OFFICIAL_ENDPOINT,
    make_fake_project,
    make_mcp_success_response,
    make_recipe,
)

# ---------------------------------------------------------------------------
# Module-import + Settings + patcher/__init__ re-export gates
# ---------------------------------------------------------------------------


def test_emitter_module_imports_resolve() -> None:
    """Public surface imports clean (GitLabMREmitter + EmitResult + Error)."""
    from chaoslab_agent.patcher.gitlab_emitter import (
        GitLabEmitResult,
        GitLabEmitterError,
        GitLabMREmitter,
    )

    assert GitLabMREmitter is not None
    assert GitLabEmitResult is not None
    assert GitLabEmitterError is not None


def test_settings_gitlab_mcp_endpoint_is_official() -> None:
    """ADR-011 lock — config defaults to the official endpoint."""
    assert get_settings().GITLAB_MCP_ENDPOINT == OFFICIAL_ENDPOINT


def test_settings_gitlab_default_branch_default() -> None:
    """Default target branch is `main` per S6.6 file map."""
    assert get_settings().GITLAB_DEFAULT_BRANCH == "main"


def test_patcher_init_exports_emitter() -> None:
    """patcher/__init__.py must re-export GitLabMREmitter + GitLabEmitResult."""
    from chaoslab_agent import patcher

    assert hasattr(patcher, "GitLabMREmitter")
    assert hasattr(patcher, "GitLabEmitResult")


# ---------------------------------------------------------------------------
# Emit happy path — branch creation, file commits, MR description, result
# ---------------------------------------------------------------------------


@respx.mock
async def test_emit_creates_branch_via_rest_client() -> None:
    """REST path: project.branches.create({"branch": ..., "ref": ...}) once."""
    from chaoslab_agent.patcher._gitlab_mcp_client import GitLabMcpClient
    from chaoslab_agent.patcher._gitlab_rest_client import GitLabRestClient
    from chaoslab_agent.patcher.gitlab_emitter import GitLabMREmitter

    respx.post(OFFICIAL_ENDPOINT).mock(
        return_value=httpx.Response(200, json=make_mcp_success_response())
    )
    project = make_fake_project()
    rest = GitLabRestClient(project=project)

    async with httpx.AsyncClient(timeout=5.0) as http:
        mcp = GitLabMcpClient(endpoint=OFFICIAL_ENDPOINT, token="tok", client=http)
        emitter = GitLabMREmitter(rest_client=rest, mcp_client=mcp)
        await emitter.emit(make_recipe(), project_id="abu-chaoslab/test-target")

    assert project.branches.create.call_count == 1
    call_kwargs = project.branches.create.call_args[0][0]
    assert call_kwargs["branch"] == "chaoslab/recipe-abc123def456"
    assert call_kwargs["ref"] == "main"


@respx.mock
async def test_emit_commits_files_with_create_actions() -> None:
    """REST commit `actions` list includes one `create` per file (.md + .diff + .json)."""
    from chaoslab_agent.patcher._gitlab_mcp_client import GitLabMcpClient
    from chaoslab_agent.patcher._gitlab_rest_client import GitLabRestClient
    from chaoslab_agent.patcher.gitlab_emitter import GitLabMREmitter

    respx.post(OFFICIAL_ENDPOINT).mock(
        return_value=httpx.Response(200, json=make_mcp_success_response())
    )

    tool_diff = ToolValidationDiff(
        tool_name="customer_lookup",
        operation="add_input_validator",
        code_patch="--- a/x\n+++ b/x\n@@ -1,1 +1,1 @@\n-old\n+new\n",
    )
    reg_case = RegressionTestCase(input="trigger payload", expected="safe response")
    recipe = make_recipe(tool_diffs=[tool_diff], regression_cases=[reg_case])

    project = make_fake_project()
    rest = GitLabRestClient(project=project)
    async with httpx.AsyncClient(timeout=5.0) as http:
        mcp = GitLabMcpClient(endpoint=OFFICIAL_ENDPOINT, token="tok", client=http)
        emitter = GitLabMREmitter(rest_client=rest, mcp_client=mcp)
        result = await emitter.emit(recipe, project_id="abu-chaoslab/test-target")

    payload = project.commits.create.call_args[0][0]
    assert payload["branch"] == "chaoslab/recipe-abc123def456"
    actions = payload["actions"]
    file_paths = [a["file_path"] for a in actions]
    assert all(a["action"] == "create" for a in actions)
    assert any(p == "chaoslab/patches/recipe_abc123def456.md" for p in file_paths)
    assert any("regression_tests/" in p for p in file_paths)
    assert any(".diff" in p and "customer_lookup" in p for p in file_paths)
    assert result.commit_count == len(actions)


@respx.mock
async def test_emit_returns_emit_result_with_valid_gitlab_mr_url() -> None:
    """BDD: result.mr_url matches r'^https://gitlab\\.com/.+/-/merge_requests/\\d+$'."""
    from chaoslab_agent.patcher._gitlab_mcp_client import GitLabMcpClient
    from chaoslab_agent.patcher._gitlab_rest_client import GitLabRestClient
    from chaoslab_agent.patcher.gitlab_emitter import GitLabEmitResult, GitLabMREmitter

    respx.post(OFFICIAL_ENDPOINT).mock(
        return_value=httpx.Response(200, json=make_mcp_success_response(iid=99))
    )
    project = make_fake_project()
    rest = GitLabRestClient(project=project)
    async with httpx.AsyncClient(timeout=5.0) as http:
        mcp = GitLabMcpClient(endpoint=OFFICIAL_ENDPOINT, token="tok", client=http)
        emitter = GitLabMREmitter(rest_client=rest, mcp_client=mcp)
        result = await emitter.emit(make_recipe(), project_id="abu-chaoslab/test-target")

    assert isinstance(result, GitLabEmitResult)
    assert result.mr_iid == 99
    assert re.fullmatch(r"https://gitlab\.com/.+/-/merge_requests/\d+", result.mr_url)
    assert result.branch_name == "chaoslab/recipe-abc123def456"
    assert result.recipe_id == "recipe_abc123def456"


@respx.mock
async def test_emit_mr_description_contains_recipe_id_and_rendered_markdown() -> None:
    """BDD: MR description includes recipe_id + the same Markdown S6.5 emits."""
    from chaoslab_agent.patcher._gitlab_mcp_client import GitLabMcpClient
    from chaoslab_agent.patcher._gitlab_rest_client import GitLabRestClient
    from chaoslab_agent.patcher._markdown_renderer import render_recipe
    from chaoslab_agent.patcher.gitlab_emitter import GitLabMREmitter

    route = respx.post(OFFICIAL_ENDPOINT).mock(
        return_value=httpx.Response(200, json=make_mcp_success_response())
    )
    recipe = make_recipe()
    project = make_fake_project()
    rest = GitLabRestClient(project=project)
    async with httpx.AsyncClient(timeout=5.0) as http:
        mcp = GitLabMcpClient(endpoint=OFFICIAL_ENDPOINT, token="tok", client=http)
        emitter = GitLabMREmitter(rest_client=rest, mcp_client=mcp)
        await emitter.emit(recipe, project_id="abu-chaoslab/test-target")

    description = json.loads(route.calls.last.request.content)["params"]["arguments"]["description"]
    assert recipe.recipe_id in description
    assert "46.0%" in description
    assert render_recipe(recipe) in description


# ---------------------------------------------------------------------------
# Result-model validators — fail loud on bad URL / branch shape
# ---------------------------------------------------------------------------


def test_emit_result_rejects_non_https_url() -> None:
    """Defense-in-depth at the result-model layer."""
    from chaoslab_agent.patcher.gitlab_emitter import GitLabEmitResult

    with pytest.raises(ValueError, match="must match"):
        GitLabEmitResult(
            mr_url="http://gitlab.com/x/-/merge_requests/1",
            mr_iid=1,
            branch_name="chaoslab/recipe-abc123def456",
            commit_count=1,
            recipe_id="recipe_abc123def456",
        )


def test_emit_result_rejects_url_not_pointed_at_gitlab() -> None:
    from chaoslab_agent.patcher.gitlab_emitter import GitLabEmitResult

    with pytest.raises(ValueError, match="must match"):
        GitLabEmitResult(
            mr_url="https://example.com/x/-/merge_requests/1",
            mr_iid=1,
            branch_name="chaoslab/recipe-abc123def456",
            commit_count=1,
            recipe_id="recipe_abc123def456",
        )


def test_emit_result_rejects_invalid_branch_name() -> None:
    """branch_name pattern locks the `chaoslab/recipe-<12hex>` shape."""
    from chaoslab_agent.patcher.gitlab_emitter import GitLabEmitResult

    with pytest.raises(ValueError, match="String should match pattern"):
        GitLabEmitResult(
            mr_url="https://gitlab.com/x/-/merge_requests/1",
            mr_iid=1,
            branch_name="random/feature",
            commit_count=1,
            recipe_id="recipe_abc123def456",
        )


# ---------------------------------------------------------------------------
# HYBRID split lock + positional-dict + envelope shape + markdown-only
# ---------------------------------------------------------------------------


@respx.mock
async def test_emit_split_counts_exactly_one_mcp_and_one_branch_call() -> None:
    """Round-2 (TQ-HIGH): assert each surface INDEPENDENTLY — sum-based check
    would let a refactor drop branch.create and pile up commits.create instead."""
    from chaoslab_agent.patcher._gitlab_mcp_client import GitLabMcpClient
    from chaoslab_agent.patcher._gitlab_rest_client import GitLabRestClient
    from chaoslab_agent.patcher.gitlab_emitter import GitLabMREmitter

    mcp_route = respx.post(OFFICIAL_ENDPOINT).mock(
        return_value=httpx.Response(200, json=make_mcp_success_response())
    )
    project = make_fake_project()
    rest = GitLabRestClient(project=project)
    async with httpx.AsyncClient(timeout=5.0) as http:
        mcp = GitLabMcpClient(endpoint=OFFICIAL_ENDPOINT, token="tok", client=http)
        emitter = GitLabMREmitter(rest_client=rest, mcp_client=mcp)
        await emitter.emit(make_recipe(), project_id="abu-chaoslab/test-target")

    assert mcp_route.call_count == 1, "MCP must be called exactly once (create_merge_request)"
    assert project.branches.create.call_count == 1, "REST branches.create must fire exactly once"
    assert project.commits.create.call_count >= 1, "REST commits.create must fire ≥1 time"


@respx.mock
async def test_emit_rest_calls_positional_dict_only() -> None:
    """TQ-MED #4: lock python-gitlab's positional-dict contract.

    Real python-gitlab takes `project.branches.create({"branch": ..., "ref": ...})`
    — NOT kwargs. A future refactor that drifts to kwargs would silently pass a
    MagicMock test but break in production with TypeError."""
    from chaoslab_agent.patcher._gitlab_mcp_client import GitLabMcpClient
    from chaoslab_agent.patcher._gitlab_rest_client import GitLabRestClient
    from chaoslab_agent.patcher.gitlab_emitter import GitLabMREmitter

    respx.post(OFFICIAL_ENDPOINT).mock(
        return_value=httpx.Response(200, json=make_mcp_success_response())
    )
    project = make_fake_project()
    rest = GitLabRestClient(project=project)
    async with httpx.AsyncClient(timeout=5.0) as http:
        mcp = GitLabMcpClient(endpoint=OFFICIAL_ENDPOINT, token="tok", client=http)
        emitter = GitLabMREmitter(rest_client=rest, mcp_client=mcp)
        await emitter.emit(make_recipe(), project_id="abu-chaoslab/test-target")

    branches_call = project.branches.create.call_args
    assert branches_call.kwargs == {}
    assert isinstance(branches_call.args[0], dict)
    commits_call = project.commits.create.call_args
    assert commits_call.kwargs == {}
    assert isinstance(commits_call.args[0], dict)


@respx.mock
async def test_emit_only_markdown_file_when_no_diffs_or_regressions() -> None:
    """TQ-MED #5: markdown-only emit. commit_count==1, single-action list."""
    from chaoslab_agent.patcher._gitlab_mcp_client import GitLabMcpClient
    from chaoslab_agent.patcher._gitlab_rest_client import GitLabRestClient
    from chaoslab_agent.patcher.gitlab_emitter import GitLabMREmitter

    respx.post(OFFICIAL_ENDPOINT).mock(
        return_value=httpx.Response(200, json=make_mcp_success_response())
    )
    recipe = make_recipe()  # no diffs/regressions by default
    project = make_fake_project()
    rest = GitLabRestClient(project=project)
    async with httpx.AsyncClient(timeout=5.0) as http:
        mcp = GitLabMcpClient(endpoint=OFFICIAL_ENDPOINT, token="tok", client=http)
        emitter = GitLabMREmitter(rest_client=rest, mcp_client=mcp)
        result = await emitter.emit(recipe, project_id="abu-chaoslab/test-target")

    assert result.commit_count == 1
    payload = project.commits.create.call_args[0][0]
    actions = payload["actions"]
    assert len(actions) == 1
    assert actions[0]["file_path"] == f"chaoslab/patches/{recipe.recipe_id}.md"


@respx.mock
async def test_emit_extracts_mr_from_envelope_shape(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """TQ-HIGH #3: prove the `content[0].json` envelope path works AND emits the
    documented WARNING so production drift to the envelope shape is observable."""
    import logging as _logging

    from chaoslab_agent.patcher._gitlab_mcp_client import GitLabMcpClient
    from chaoslab_agent.patcher._gitlab_rest_client import GitLabRestClient
    from chaoslab_agent.patcher.gitlab_emitter import GitLabMREmitter

    respx.post(OFFICIAL_ENDPOINT).mock(
        return_value=httpx.Response(
            200,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "result": {
                    "content": [
                        {
                            "type": "json",
                            "json": {
                                "iid": 77,
                                "web_url": (
                                    "https://gitlab.com/abu-chaoslab/test-target"
                                    "/-/merge_requests/77"
                                ),
                            },
                        }
                    ]
                },
            },
        )
    )
    project = make_fake_project()
    rest = GitLabRestClient(project=project)
    with caplog.at_level(_logging.WARNING, logger="chaoslab_agent.patcher.gitlab_emitter"):
        async with httpx.AsyncClient(timeout=5.0) as http:
            mcp = GitLabMcpClient(endpoint=OFFICIAL_ENDPOINT, token="tok", client=http)
            emitter = GitLabMREmitter(rest_client=rest, mcp_client=mcp)
            result = await emitter.emit(make_recipe(), project_id="abu-chaoslab/test-target")

    assert result.mr_iid == 77
    assert any("mcp_envelope_fallback_used" in r.message for r in caplog.records), [
        r.message for r in caplog.records
    ]
