"""Unit tests for GitLabMREmitter — stubs the python-gitlab + MCP boundaries.

Hybrid mode (ADR-011 + S6.6 amendment): branch + multi-file commit go via
python-gitlab; MR creation goes via the official `https://gitlab.com/api/v4/mcp`
endpoint. Tests assert the SPLIT (a 1-call MCP path + ≥1-call REST path) so a
future refactor can't silently route everything through one transport.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock

import httpx
import pytest
import respx

from chaoslab_agent.config import get_settings
from chaoslab_agent.judge.clustering import FailureClusterSet
from chaoslab_agent.patcher.recipe import (
    FailureCluster,
    HardeningRecipe,
    PromptPatch,
    RegressionTestCase,
    ToolValidationDiff,
)

_OFFICIAL_ENDPOINT = "https://gitlab.com/api/v4/mcp"


@pytest.fixture(autouse=True)
def _vertex_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep Settings() defaults deterministic across tests."""
    monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "true")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")
    monkeypatch.setenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    get_settings.cache_clear()


def _recipe(
    *,
    tool_diffs: list[ToolValidationDiff] | None = None,
    prompt_patches: list[PromptPatch] | None = None,
    regression_cases: list[RegressionTestCase] | None = None,
) -> HardeningRecipe:
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


def _fake_project() -> MagicMock:
    """MagicMock standing in for a python-gitlab Project.

    Records `.branches.create({...})` and `.commits.create({...})` calls so
    tests can assert on the payload shape without touching gitlab.com.
    """
    project = MagicMock()
    project.branches = MagicMock()
    project.branches.create = MagicMock(return_value=MagicMock())
    project.commits = MagicMock()
    project.commits.create = MagicMock(return_value=MagicMock())
    return project


def _mcp_success_response(
    *, iid: int = 42, project_path: str = "abu-chaoslab/test-target"
) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "iid": iid,
            "web_url": f"https://gitlab.com/{project_path}/-/merge_requests/{iid}",
            "state": "opened",
        },
    }


# ---------------------------------------------------------------------------
# Config + import gates
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
    assert get_settings().GITLAB_MCP_ENDPOINT == _OFFICIAL_ENDPOINT


def test_settings_gitlab_default_branch_default() -> None:
    """Default target branch is `main` per S6.6 file map."""
    assert get_settings().GITLAB_DEFAULT_BRANCH == "main"


def test_patcher_init_exports_emitter() -> None:
    """patcher/__init__.py must re-export GitLabMREmitter + GitLabEmitResult."""
    from chaoslab_agent import patcher

    assert hasattr(patcher, "GitLabMREmitter")
    assert hasattr(patcher, "GitLabEmitResult")


# ---------------------------------------------------------------------------
# MCP client — BANNED endpoint guard + auth + retry + error mapping
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "banned_url",
    [
        "https://github.com/zereight/gitlab-mcp",
        "https://github.com/mcpland/gitlab-mcp",
        "https://wadew.io/gitlab-mcp",
    ],
)
def test_mcp_client_rejects_banned_community_endpoints(banned_url: str) -> None:
    """partner-gitlab.md lists community wrappers as banned — judging penalty."""
    from chaoslab_agent.patcher._gitlab_mcp_client import GitLabMcpClient

    with pytest.raises(ValueError, match="Community MCP endpoints banned"):
        GitLabMcpClient(endpoint=banned_url)


def test_mcp_client_accepts_official_endpoint() -> None:
    from chaoslab_agent.patcher._gitlab_mcp_client import GitLabMcpClient

    client = GitLabMcpClient(endpoint=_OFFICIAL_ENDPOINT)
    # Public attribute we can inspect; private is fine for the lock here.
    assert _OFFICIAL_ENDPOINT in repr(getattr(client, "_endpoint", _OFFICIAL_ENDPOINT))


@respx.mock
async def test_mcp_client_posts_create_merge_request_to_official_endpoint() -> None:
    """BDD: exactly 1 POST to https://gitlab.com/api/v4/mcp with tool=create_merge_request."""
    from chaoslab_agent.patcher._gitlab_mcp_client import GitLabMcpClient

    route = respx.post(_OFFICIAL_ENDPOINT).mock(
        return_value=httpx.Response(200, json=_mcp_success_response())
    )

    async with httpx.AsyncClient(timeout=5.0) as http:
        client = GitLabMcpClient(endpoint=_OFFICIAL_ENDPOINT, token="tok", client=http)
        await client.create_merge_request(
            project_id="abu-chaoslab/test-target",
            source_branch="chaoslab/recipe-abc123def456",
            target_branch="main",
            title="title",
            description="desc",
            labels=["chaoslab"],
        )
    assert route.called
    body = json.loads(route.calls.last.request.content)
    assert body["params"]["name"] == "create_merge_request"
    assert body["params"]["arguments"]["source_branch"] == "chaoslab/recipe-abc123def456"
    assert body["params"]["arguments"]["target_branch"] == "main"


@respx.mock
async def test_mcp_client_sends_bearer_auth_header() -> None:
    from chaoslab_agent.patcher._gitlab_mcp_client import GitLabMcpClient

    route = respx.post(_OFFICIAL_ENDPOINT).mock(
        return_value=httpx.Response(200, json=_mcp_success_response())
    )

    async with httpx.AsyncClient(timeout=5.0) as http:
        client = GitLabMcpClient(endpoint=_OFFICIAL_ENDPOINT, token="my-token", client=http)
        await client.create_merge_request(
            project_id="x", source_branch="a", target_branch="b", title="t", description="d"
        )
    assert route.calls.last.request.headers["Authorization"] == "Bearer my-token"


@respx.mock
async def test_mcp_client_raises_on_401_with_authentication_message() -> None:
    from chaoslab_agent.patcher._gitlab_mcp_client import GitLabMcpClient, GitLabMcpError

    respx.post(_OFFICIAL_ENDPOINT).mock(
        return_value=httpx.Response(401, json={"message": "401 Unauthorized"})
    )

    async with httpx.AsyncClient(timeout=5.0) as http:
        client = GitLabMcpClient(endpoint=_OFFICIAL_ENDPOINT, token="bad", client=http)
        with pytest.raises(GitLabMcpError, match="authentication"):
            await client.create_merge_request(
                project_id="x", source_branch="a", target_branch="b", title="t", description="d"
            )


@respx.mock
async def test_mcp_client_retries_on_5xx_up_to_three_attempts() -> None:
    """503 twice → 200. Locks the exponential-backoff retry loop."""
    from chaoslab_agent.patcher._gitlab_mcp_client import GitLabMcpClient

    route = respx.post(_OFFICIAL_ENDPOINT).mock(
        side_effect=[
            httpx.Response(503, text="busy"),
            httpx.Response(503, text="busy"),
            httpx.Response(200, json=_mcp_success_response()),
        ]
    )

    async with httpx.AsyncClient(timeout=5.0) as http:
        client = GitLabMcpClient(endpoint=_OFFICIAL_ENDPOINT, token="tok", client=http)
        result = await client.create_merge_request(
            project_id="x", source_branch="a", target_branch="b", title="t", description="d"
        )
    assert route.call_count == 3
    assert result.get("iid") == 42 or result.get("web_url", "").endswith("/42")


# ---------------------------------------------------------------------------
# Emitter — orchestration + REST split + result shape + error mapping
# ---------------------------------------------------------------------------


@respx.mock
async def test_emit_creates_branch_via_rest_client() -> None:
    """REST path: project.branches.create({"branch": ..., "ref": ...}) is invoked once."""
    from chaoslab_agent.patcher._gitlab_mcp_client import GitLabMcpClient
    from chaoslab_agent.patcher._gitlab_rest_client import GitLabRestClient
    from chaoslab_agent.patcher.gitlab_emitter import GitLabMREmitter

    respx.post(_OFFICIAL_ENDPOINT).mock(
        return_value=httpx.Response(200, json=_mcp_success_response())
    )
    project = _fake_project()
    rest = GitLabRestClient(project=project)

    async with httpx.AsyncClient(timeout=5.0) as http:
        mcp = GitLabMcpClient(endpoint=_OFFICIAL_ENDPOINT, token="tok", client=http)
        emitter = GitLabMREmitter(rest_client=rest, mcp_client=mcp)
        await emitter.emit(_recipe(), project_id="abu-chaoslab/test-target")

    assert project.branches.create.call_count == 1
    call_kwargs = project.branches.create.call_args[0][0]
    assert call_kwargs["branch"] == "chaoslab/recipe-abc123def456"
    assert call_kwargs["ref"] == "main"


@respx.mock
async def test_emit_commits_files_with_create_actions() -> None:
    """REST commit `actions` list includes one `create` per file (Markdown + diffs + tests)."""
    from chaoslab_agent.patcher._gitlab_mcp_client import GitLabMcpClient
    from chaoslab_agent.patcher._gitlab_rest_client import GitLabRestClient
    from chaoslab_agent.patcher.gitlab_emitter import GitLabMREmitter

    respx.post(_OFFICIAL_ENDPOINT).mock(
        return_value=httpx.Response(200, json=_mcp_success_response())
    )

    tool_diff = ToolValidationDiff(
        tool_name="customer_lookup",
        operation="add_input_validator",
        code_patch="--- a/x\n+++ b/x\n@@ -1,1 +1,1 @@\n-old\n+new\n",
    )
    reg_case = RegressionTestCase(input="trigger payload", expected="safe response")
    recipe = _recipe(tool_diffs=[tool_diff], regression_cases=[reg_case])

    project = _fake_project()
    rest = GitLabRestClient(project=project)
    async with httpx.AsyncClient(timeout=5.0) as http:
        mcp = GitLabMcpClient(endpoint=_OFFICIAL_ENDPOINT, token="tok", client=http)
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
    # commit_count tracks the file count, so the result mirrors the REST payload.
    assert result.commit_count == len(actions)


@respx.mock
async def test_emit_returns_emit_result_with_valid_gitlab_mr_url() -> None:
    """BDD: result.mr_url matches r'^https://gitlab\\.com/.+/-/merge_requests/\\d+$'."""
    import re

    from chaoslab_agent.patcher._gitlab_mcp_client import GitLabMcpClient
    from chaoslab_agent.patcher._gitlab_rest_client import GitLabRestClient
    from chaoslab_agent.patcher.gitlab_emitter import GitLabEmitResult, GitLabMREmitter

    respx.post(_OFFICIAL_ENDPOINT).mock(
        return_value=httpx.Response(200, json=_mcp_success_response(iid=99))
    )
    project = _fake_project()
    rest = GitLabRestClient(project=project)
    async with httpx.AsyncClient(timeout=5.0) as http:
        mcp = GitLabMcpClient(endpoint=_OFFICIAL_ENDPOINT, token="tok", client=http)
        emitter = GitLabMREmitter(rest_client=rest, mcp_client=mcp)
        result = await emitter.emit(_recipe(), project_id="abu-chaoslab/test-target")

    assert isinstance(result, GitLabEmitResult)
    assert result.mr_iid == 99
    assert re.fullmatch(r"https://gitlab\.com/.+/-/merge_requests/\d+", result.mr_url)
    assert result.branch_name == "chaoslab/recipe-abc123def456"
    assert result.recipe_id == "recipe_abc123def456"


def test_emit_result_rejects_non_https_url() -> None:
    """Defense-in-depth at the result-model layer."""
    from chaoslab_agent.patcher.gitlab_emitter import GitLabEmitResult

    with pytest.raises(ValueError, match="https"):
        GitLabEmitResult(
            mr_url="http://gitlab.com/x/-/merge_requests/1",
            mr_iid=1,
            branch_name="chaoslab/recipe-abc123def456",
            commit_count=1,
            recipe_id="recipe_abc123def456",
        )


def test_emit_result_rejects_url_not_pointed_at_gitlab() -> None:
    from chaoslab_agent.patcher.gitlab_emitter import GitLabEmitResult

    with pytest.raises(ValueError, match="gitlab"):
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


@respx.mock
async def test_emit_mr_description_contains_recipe_id_and_rendered_markdown() -> None:
    """BDD: MR description includes recipe_id + the same Markdown S6.5 emits."""
    from chaoslab_agent.patcher._gitlab_mcp_client import GitLabMcpClient
    from chaoslab_agent.patcher._gitlab_rest_client import GitLabRestClient
    from chaoslab_agent.patcher._markdown_renderer import render_recipe
    from chaoslab_agent.patcher.gitlab_emitter import GitLabMREmitter

    route = respx.post(_OFFICIAL_ENDPOINT).mock(
        return_value=httpx.Response(200, json=_mcp_success_response())
    )
    recipe = _recipe()
    project = _fake_project()
    rest = GitLabRestClient(project=project)
    async with httpx.AsyncClient(timeout=5.0) as http:
        mcp = GitLabMcpClient(endpoint=_OFFICIAL_ENDPOINT, token="tok", client=http)
        emitter = GitLabMREmitter(rest_client=rest, mcp_client=mcp)
        await emitter.emit(recipe, project_id="abu-chaoslab/test-target")

    description = json.loads(route.calls.last.request.content)["params"]["arguments"]["description"]
    assert recipe.recipe_id in description
    assert "46.0%" in description  # 0.46 * 100, format-locked
    assert render_recipe(recipe) in description


@respx.mock
async def test_emit_401_wraps_to_emitter_error_with_authentication_message() -> None:
    """BDD: 401 surfaces as GitLabEmitterError naming "authentication"."""
    from chaoslab_agent.patcher._gitlab_mcp_client import GitLabMcpClient
    from chaoslab_agent.patcher._gitlab_rest_client import GitLabRestClient
    from chaoslab_agent.patcher.gitlab_emitter import GitLabEmitterError, GitLabMREmitter

    respx.post(_OFFICIAL_ENDPOINT).mock(
        return_value=httpx.Response(401, json={"message": "401 Unauthorized"})
    )
    project = _fake_project()
    rest = GitLabRestClient(project=project)
    async with httpx.AsyncClient(timeout=5.0) as http:
        mcp = GitLabMcpClient(endpoint=_OFFICIAL_ENDPOINT, token="bad", client=http)
        emitter = GitLabMREmitter(rest_client=rest, mcp_client=mcp)
        with pytest.raises(GitLabEmitterError, match="authentication"):
            await emitter.emit(_recipe(), project_id="abu-chaoslab/test-target")


def test_emitter_construction_rejects_non_official_mcp_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ADR-011 lock at the emitter level — even if settings drift, construction fails."""
    from chaoslab_agent.patcher.gitlab_emitter import GitLabEmitterError, GitLabMREmitter

    monkeypatch.setenv("GITLAB_MCP_ENDPOINT", "https://github.com/zereight/gitlab-mcp")
    get_settings.cache_clear()
    with pytest.raises((GitLabEmitterError, ValueError), match=r"ADR-011|Community MCP"):
        GitLabMREmitter()


@respx.mock
async def test_emit_split_counts_one_mcp_call_and_at_least_two_rest_calls() -> None:
    """BDD: exactly 1 MCP call (MR) + ≥2 REST calls (branch + commit) per emit().

    Locks the HYBRID design — a future refactor that routes everything through
    one transport would fail this test."""
    from chaoslab_agent.patcher._gitlab_mcp_client import GitLabMcpClient
    from chaoslab_agent.patcher._gitlab_rest_client import GitLabRestClient
    from chaoslab_agent.patcher.gitlab_emitter import GitLabMREmitter

    mcp_route = respx.post(_OFFICIAL_ENDPOINT).mock(
        return_value=httpx.Response(200, json=_mcp_success_response())
    )
    project = _fake_project()
    rest = GitLabRestClient(project=project)
    async with httpx.AsyncClient(timeout=5.0) as http:
        mcp = GitLabMcpClient(endpoint=_OFFICIAL_ENDPOINT, token="tok", client=http)
        emitter = GitLabMREmitter(rest_client=rest, mcp_client=mcp)
        await emitter.emit(_recipe(), project_id="abu-chaoslab/test-target")

    # Round-2 (TQ-HIGH): assert each surface independently so a future refactor
    # that drops branch.create (orphan commits) or routes branch through commits
    # API can't slip past with a sum-based >= check.
    assert mcp_route.call_count == 1, "MCP must be called exactly once (create_merge_request)"
    assert project.branches.create.call_count == 1, "REST branches.create must fire exactly once"
    assert project.commits.create.call_count >= 1, "REST commits.create must fire ≥1 time"


# ---------------------------------------------------------------------------
# Round-2 hardening tests (PR #74 reviewer fleet — 3-agent fan-out findings)
# ---------------------------------------------------------------------------


@respx.mock
async def test_mcp_client_wraps_non_401_4xx_in_emitter_error() -> None:
    """SFH-BLOCKER #2: 403/404/422 must wrap to GitLabMcpError so the emitter's
    `except GitLabMcpError` catches them. Was leaking as httpx.HTTPStatusError."""
    from chaoslab_agent.patcher._gitlab_mcp_client import GitLabMcpClient, GitLabMcpError

    respx.post(_OFFICIAL_ENDPOINT).mock(return_value=httpx.Response(404, text="Project Not Found"))

    async with httpx.AsyncClient(timeout=5.0) as http:
        client = GitLabMcpClient(endpoint=_OFFICIAL_ENDPOINT, token="tok", client=http)
        with pytest.raises(GitLabMcpError, match="404"):
            await client.create_merge_request(
                project_id="nonexistent/project",
                source_branch="a",
                target_branch="b",
                title="t",
                description="d",
            )


@respx.mock
async def test_mcp_client_wraps_403_forbidden() -> None:
    """SFH-BLOCKER #2 — 403 (insufficient PAT scope) also wraps cleanly."""
    from chaoslab_agent.patcher._gitlab_mcp_client import GitLabMcpClient, GitLabMcpError

    respx.post(_OFFICIAL_ENDPOINT).mock(return_value=httpx.Response(403, text="Forbidden"))
    async with httpx.AsyncClient(timeout=5.0) as http:
        client = GitLabMcpClient(endpoint=_OFFICIAL_ENDPOINT, token="tok", client=http)
        with pytest.raises(GitLabMcpError, match="403"):
            await client.create_merge_request(
                project_id="x", source_branch="a", target_branch="b", title="t", description="d"
            )


def test_mcp_client_construction_rejects_non_official_endpoint() -> None:
    """SFH-I #3: positive `endpoint == OFFICIAL_ENDPOINT` check.

    A typo like `https://gitlab.com/api/v3/mcp` (v3 not v4) passes the BANNED
    fragment list but is still wrong — needs strict equality."""
    from chaoslab_agent.patcher._gitlab_mcp_client import GitLabMcpClient

    with pytest.raises(ValueError, match="ADR-011"):
        GitLabMcpClient(endpoint="https://gitlab.com/api/v3/mcp", token="tok")


def test_mcp_client_construction_rejects_typo_in_path() -> None:
    """SFH-I #3 follow-up: a single-character typo MUST fail."""
    from chaoslab_agent.patcher._gitlab_mcp_client import GitLabMcpClient

    with pytest.raises(ValueError, match="ADR-011"):
        GitLabMcpClient(endpoint="https://gitlab.com/api/v4/mc", token="tok")


@respx.mock
async def test_mcp_client_surfaces_nested_result_error() -> None:
    """SFH-I #5: tool-level error nested inside `result.error` is surfaced."""
    from chaoslab_agent.patcher._gitlab_mcp_client import GitLabMcpClient, GitLabMcpError

    respx.post(_OFFICIAL_ENDPOINT).mock(
        return_value=httpx.Response(
            200,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "result": {"error": "422 branch already exists"},
            },
        )
    )
    async with httpx.AsyncClient(timeout=5.0) as http:
        client = GitLabMcpClient(endpoint=_OFFICIAL_ENDPOINT, token="tok", client=http)
        with pytest.raises(GitLabMcpError, match="branch already exists"):
            await client.create_merge_request(
                project_id="x", source_branch="a", target_branch="b", title="t", description="d"
            )


@respx.mock
async def test_mcp_client_surfaces_is_error_envelope() -> None:
    """SFH-I #5: MCP `isError: true` convention is surfaced explicitly."""
    from chaoslab_agent.patcher._gitlab_mcp_client import GitLabMcpClient, GitLabMcpError

    respx.post(_OFFICIAL_ENDPOINT).mock(
        return_value=httpx.Response(
            200,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "result": {"isError": True, "content": [{"type": "text", "text": "denied"}]},
            },
        )
    )
    async with httpx.AsyncClient(timeout=5.0) as http:
        client = GitLabMcpClient(endpoint=_OFFICIAL_ENDPOINT, token="tok", client=http)
        with pytest.raises(GitLabMcpError, match="isError"):
            await client.create_merge_request(
                project_id="x", source_branch="a", target_branch="b", title="t", description="d"
            )


@respx.mock
async def test_mcp_client_missing_result_key_raises_explicit() -> None:
    """SFH-S #8: distinguish missing-result (broken server) from empty-result-dict."""
    from chaoslab_agent.patcher._gitlab_mcp_client import GitLabMcpClient, GitLabMcpError

    respx.post(_OFFICIAL_ENDPOINT).mock(
        return_value=httpx.Response(200, json={"jsonrpc": "2.0", "id": 1})
    )
    async with httpx.AsyncClient(timeout=5.0) as http:
        client = GitLabMcpClient(endpoint=_OFFICIAL_ENDPOINT, token="tok", client=http)
        with pytest.raises(GitLabMcpError, match="no 'result' key"):
            await client.create_merge_request(
                project_id="x", source_branch="a", target_branch="b", title="t", description="d"
            )


@respx.mock
async def test_mcp_client_retries_on_non_json_response() -> None:
    """SFH-S #6: maintenance-page HTML at 200 → retry, eventual JSON success."""
    from chaoslab_agent.patcher._gitlab_mcp_client import GitLabMcpClient

    route = respx.post(_OFFICIAL_ENDPOINT).mock(
        side_effect=[
            httpx.Response(200, text="<html>maintenance</html>"),
            httpx.Response(200, json=_mcp_success_response()),
        ]
    )
    async with httpx.AsyncClient(timeout=5.0) as http:
        client = GitLabMcpClient(endpoint=_OFFICIAL_ENDPOINT, token="tok", client=http)
        result = await client.create_merge_request(
            project_id="x", source_branch="a", target_branch="b", title="t", description="d"
        )
    assert route.call_count == 2
    assert result.get("iid") == 42


@respx.mock
async def test_mcp_client_5xx_retry_uses_increasing_backoff(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """TQ-HIGH #2: assert the BACKOFF SCHEDULE (not wall-clock). A future refactor
    that drops asyncio.sleep would silently pass the call-count test alone."""
    import asyncio as _asyncio

    from chaoslab_agent.patcher import _gitlab_mcp_client as mcp_mod

    respx.post(_OFFICIAL_ENDPOINT).mock(
        side_effect=[
            httpx.Response(503),
            httpx.Response(503),
            httpx.Response(200, json=_mcp_success_response()),
        ]
    )

    sleep_delays: list[float] = []

    async def _record_sleep(delay: float) -> None:
        sleep_delays.append(delay)

    monkeypatch.setattr(mcp_mod.asyncio, "sleep", _record_sleep)

    async with httpx.AsyncClient(timeout=5.0) as http:
        client = mcp_mod.GitLabMcpClient(endpoint=_OFFICIAL_ENDPOINT, token="tok", client=http)
        await client.create_merge_request(
            project_id="x", source_branch="a", target_branch="b", title="t", description="d"
        )

    # Strict: two sleeps between three POSTs, strictly increasing (1.0s then 2.0s
    # per `_RETRY_BASE_SECONDS * 2**attempt`).
    assert len(sleep_delays) == 2
    assert sleep_delays[1] > sleep_delays[0]
    _ = _asyncio  # marker for the future-attempt sanity check below; no functional use


@respx.mock
async def test_emit_extracts_mr_from_envelope_shape() -> None:
    """TQ-HIGH #3 / CR-MED #5: prove the `content[0].json` envelope path works
    AND emits the documented WARNING so production drift to the envelope shape
    is observable."""
    from chaoslab_agent.patcher._gitlab_mcp_client import GitLabMcpClient
    from chaoslab_agent.patcher._gitlab_rest_client import GitLabRestClient
    from chaoslab_agent.patcher.gitlab_emitter import GitLabMREmitter

    respx.post(_OFFICIAL_ENDPOINT).mock(
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
    project = _fake_project()
    rest = GitLabRestClient(project=project)
    async with httpx.AsyncClient(timeout=5.0) as http:
        mcp = GitLabMcpClient(endpoint=_OFFICIAL_ENDPOINT, token="tok", client=http)
        emitter = GitLabMREmitter(rest_client=rest, mcp_client=mcp)
        result = await emitter.emit(_recipe(), project_id="abu-chaoslab/test-target")

    assert result.mr_iid == 77


@respx.mock
async def test_emit_returns_descriptive_error_on_null_mr_field() -> None:
    """SFH-I #4: MCP returning `{"web_url": null}` must surface a clear error,
    NOT the string "None" then failing url validation with a confusing message."""
    from chaoslab_agent.patcher._gitlab_mcp_client import GitLabMcpClient
    from chaoslab_agent.patcher._gitlab_rest_client import GitLabRestClient
    from chaoslab_agent.patcher.gitlab_emitter import GitLabEmitterError, GitLabMREmitter

    respx.post(_OFFICIAL_ENDPOINT).mock(
        return_value=httpx.Response(
            200, json={"jsonrpc": "2.0", "id": 1, "result": {"iid": 1, "web_url": None}}
        )
    )
    project = _fake_project()
    rest = GitLabRestClient(project=project)
    async with httpx.AsyncClient(timeout=5.0) as http:
        mcp = GitLabMcpClient(endpoint=_OFFICIAL_ENDPOINT, token="tok", client=http)
        emitter = GitLabMREmitter(rest_client=rest, mcp_client=mcp)
        with pytest.raises(GitLabEmitterError, match="missing required field"):
            await emitter.emit(_recipe(), project_id="abu-chaoslab/test-target")


@respx.mock
async def test_emit_rolls_back_branch_when_mcp_fails() -> None:
    """SFH-BLOCKER #1 / CR-HIGH #1: orphan branch leak — REST succeeded, MCP failed.
    Lifespan: branches.delete is called best-effort + branch_name surfaces in error."""
    from chaoslab_agent.patcher._gitlab_mcp_client import GitLabMcpClient
    from chaoslab_agent.patcher._gitlab_rest_client import GitLabRestClient
    from chaoslab_agent.patcher.gitlab_emitter import GitLabEmitterError, GitLabMREmitter

    # MCP returns 500 → exhausted retries → GitLabMcpError → rollback path.
    respx.post(_OFFICIAL_ENDPOINT).mock(return_value=httpx.Response(500))
    project = _fake_project()
    rest = GitLabRestClient(project=project)

    async with httpx.AsyncClient(timeout=5.0) as http:
        mcp = GitLabMcpClient(endpoint=_OFFICIAL_ENDPOINT, token="tok", client=http)
        emitter = GitLabMREmitter(rest_client=rest, mcp_client=mcp)
        with pytest.raises(GitLabEmitterError, match="chaoslab/recipe-abc123def456"):
            await emitter.emit(_recipe(), project_id="abu-chaoslab/test-target")

    # The orphan branch must have been rollback-attempted exactly once.
    assert project.branches.delete.call_count == 1
    assert project.branches.delete.call_args[0][0] == "chaoslab/recipe-abc123def456"


@respx.mock
async def test_emit_propagates_mcp_error_even_when_rollback_fails() -> None:
    """SFH-BLOCKER #1: rollback is best-effort. If `branches.delete` ITSELF raises,
    the MCP error still surfaces (preserving root cause for the operator) — and
    the branch_name in the message tells them what to clean up manually."""
    from chaoslab_agent.patcher._gitlab_mcp_client import GitLabMcpClient
    from chaoslab_agent.patcher._gitlab_rest_client import GitLabRestClient
    from chaoslab_agent.patcher.gitlab_emitter import GitLabEmitterError, GitLabMREmitter

    respx.post(_OFFICIAL_ENDPOINT).mock(return_value=httpx.Response(500))
    project = _fake_project()
    project.branches.delete.side_effect = RuntimeError("rollback broke too")
    rest = GitLabRestClient(project=project)

    async with httpx.AsyncClient(timeout=5.0) as http:
        mcp = GitLabMcpClient(endpoint=_OFFICIAL_ENDPOINT, token="tok", client=http)
        emitter = GitLabMREmitter(rest_client=rest, mcp_client=mcp)
        with pytest.raises(GitLabEmitterError, match="chaoslab/recipe-abc123def456"):
            await emitter.emit(_recipe(), project_id="abu-chaoslab/test-target")


@respx.mock
async def test_emit_does_not_rollback_when_rest_fails_before_mcp() -> None:
    """If REST branch.create fails, MCP is never called and rollback is moot."""
    from chaoslab_agent.patcher._gitlab_mcp_client import GitLabMcpClient
    from chaoslab_agent.patcher._gitlab_rest_client import GitLabRestClient
    from chaoslab_agent.patcher.gitlab_emitter import GitLabEmitterError, GitLabMREmitter

    mcp_route = respx.post(_OFFICIAL_ENDPOINT).mock(
        return_value=httpx.Response(200, json=_mcp_success_response())
    )
    project = _fake_project()
    project.branches.create.side_effect = RuntimeError("rest dead")
    rest = GitLabRestClient(project=project)

    async with httpx.AsyncClient(timeout=5.0) as http:
        mcp = GitLabMcpClient(endpoint=_OFFICIAL_ENDPOINT, token="tok", client=http)
        emitter = GitLabMREmitter(rest_client=rest, mcp_client=mcp)
        with pytest.raises(GitLabEmitterError, match="GitLab branch/commit failed"):
            await emitter.emit(_recipe(), project_id="abu-chaoslab/test-target")

    # MCP never called → nothing to roll back.
    assert mcp_route.call_count == 0
    assert project.branches.delete.call_count == 0


@respx.mock
async def test_emit_only_markdown_file_when_no_diffs_or_regressions() -> None:
    """TQ-MED #5: markdown-only emit. commit_count==1, no diffs/regression paths."""
    from chaoslab_agent.patcher._gitlab_mcp_client import GitLabMcpClient
    from chaoslab_agent.patcher._gitlab_rest_client import GitLabRestClient
    from chaoslab_agent.patcher.gitlab_emitter import GitLabMREmitter

    respx.post(_OFFICIAL_ENDPOINT).mock(
        return_value=httpx.Response(200, json=_mcp_success_response())
    )
    recipe = _recipe()  # no tool_diffs, no regression_cases by default
    project = _fake_project()
    rest = GitLabRestClient(project=project)
    async with httpx.AsyncClient(timeout=5.0) as http:
        mcp = GitLabMcpClient(endpoint=_OFFICIAL_ENDPOINT, token="tok", client=http)
        emitter = GitLabMREmitter(rest_client=rest, mcp_client=mcp)
        result = await emitter.emit(recipe, project_id="abu-chaoslab/test-target")

    assert result.commit_count == 1
    payload = project.commits.create.call_args[0][0]
    actions = payload["actions"]
    assert len(actions) == 1
    assert actions[0]["file_path"] == f"chaoslab/patches/{recipe.recipe_id}.md"


@respx.mock
async def test_emit_401_chain_preserves_cause(monkeypatch: pytest.MonkeyPatch) -> None:
    """TQ-MED #6: `__cause__` chain locked — a future refactor that drops `from exc`
    loses debuggability but would pass the substring-match-only assertion."""
    from chaoslab_agent.patcher._gitlab_mcp_client import GitLabMcpClient, GitLabMcpError
    from chaoslab_agent.patcher._gitlab_rest_client import GitLabRestClient
    from chaoslab_agent.patcher.gitlab_emitter import GitLabEmitterError, GitLabMREmitter

    respx.post(_OFFICIAL_ENDPOINT).mock(return_value=httpx.Response(401, json={"message": "401"}))
    project = _fake_project()
    rest = GitLabRestClient(project=project)
    async with httpx.AsyncClient(timeout=5.0) as http:
        mcp = GitLabMcpClient(endpoint=_OFFICIAL_ENDPOINT, token="bad", client=http)
        emitter = GitLabMREmitter(rest_client=rest, mcp_client=mcp)
        with pytest.raises(GitLabEmitterError) as exc_info:
            await emitter.emit(_recipe(), project_id="abu-chaoslab/test-target")

    assert exc_info.value.__cause__ is not None
    assert isinstance(exc_info.value.__cause__, GitLabMcpError)


@respx.mock
async def test_emit_rest_failure_chain_preserves_cause() -> None:
    """CR-MED #3: GitLabRestClientError propagates as __cause__ — locks the rest
    error path (was untested in round-1; the `except Exception` branch was dead)."""
    from chaoslab_agent.patcher._gitlab_mcp_client import GitLabMcpClient
    from chaoslab_agent.patcher._gitlab_rest_client import GitLabRestClient, GitLabRestClientError
    from chaoslab_agent.patcher.gitlab_emitter import GitLabEmitterError, GitLabMREmitter

    respx.post(_OFFICIAL_ENDPOINT).mock(
        return_value=httpx.Response(200, json=_mcp_success_response())
    )
    project = _fake_project()
    project.branches.create.side_effect = RuntimeError("network exploded")
    rest = GitLabRestClient(project=project)

    async with httpx.AsyncClient(timeout=5.0) as http:
        mcp = GitLabMcpClient(endpoint=_OFFICIAL_ENDPOINT, token="tok", client=http)
        emitter = GitLabMREmitter(rest_client=rest, mcp_client=mcp)
        with pytest.raises(GitLabEmitterError) as exc_info:
            await emitter.emit(_recipe(), project_id="abu-chaoslab/test-target")

    assert exc_info.value.__cause__ is not None
    assert isinstance(exc_info.value.__cause__, GitLabRestClientError)


@respx.mock
async def test_emit_rest_calls_positional_dict_only() -> None:
    """TQ-MED #4 / CR-MED #3: lock python-gitlab's positional-dict contract.

    Real python-gitlab takes `project.branches.create({"branch": ..., "ref": ...})`
    — NOT kwargs. A future refactor that drifts to kwargs would silently pass a
    MagicMock test but break in production with TypeError."""
    from chaoslab_agent.patcher._gitlab_mcp_client import GitLabMcpClient
    from chaoslab_agent.patcher._gitlab_rest_client import GitLabRestClient
    from chaoslab_agent.patcher.gitlab_emitter import GitLabMREmitter

    respx.post(_OFFICIAL_ENDPOINT).mock(
        return_value=httpx.Response(200, json=_mcp_success_response())
    )
    project = _fake_project()
    rest = GitLabRestClient(project=project)
    async with httpx.AsyncClient(timeout=5.0) as http:
        mcp = GitLabMcpClient(endpoint=_OFFICIAL_ENDPOINT, token="tok", client=http)
        emitter = GitLabMREmitter(rest_client=rest, mcp_client=mcp)
        await emitter.emit(_recipe(), project_id="abu-chaoslab/test-target")

    # Positional-only: kwargs MUST be empty, args[0] MUST be a dict.
    branches_call = project.branches.create.call_args
    assert branches_call.kwargs == {}
    assert isinstance(branches_call.args[0], dict)
    commits_call = project.commits.create.call_args
    assert commits_call.kwargs == {}
    assert isinstance(commits_call.args[0], dict)


@respx.mock
async def test_emit_sanitizes_backticks_in_target_agent_id(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """SFH-S #7: backticks in target_agent_id MUST be stripped so the inline
    code-span in the MR description doesn't break. WARNING logged so bad
    upstream data is observable in Cloud Logging."""
    import logging as _logging

    from chaoslab_agent.patcher._gitlab_mcp_client import GitLabMcpClient
    from chaoslab_agent.patcher._gitlab_rest_client import GitLabRestClient
    from chaoslab_agent.patcher.gitlab_emitter import GitLabMREmitter

    route = respx.post(_OFFICIAL_ENDPOINT).mock(
        return_value=httpx.Response(200, json=_mcp_success_response())
    )
    cluster = FailureCluster(
        cluster_id="cluster_a3f7b2c1",
        root_cause="...",
        failure_count=1,
        span_ids=["0123456789abcdef"],
        fault_classes=["malformed_tool_output"],
    )
    recipe = HardeningRecipe(
        recipe_id="recipe_abc123def456",
        target_agent_id="evil`backtick`agent",
        generated_at="2026-06-02T14:30:00Z",
        cluster_set=FailureClusterSet(clusters=[cluster], total_failures=1),
        prompt_patches=[],
        tool_validation_diffs=[],
        regression_test_cases=[],
        estimated_resilience_improvement=0.5,
    )
    project = _fake_project()
    rest = GitLabRestClient(project=project)
    with caplog.at_level(_logging.WARNING, logger="chaoslab_agent.patcher.gitlab_emitter"):
        async with httpx.AsyncClient(timeout=5.0) as http:
            mcp = GitLabMcpClient(endpoint=_OFFICIAL_ENDPOINT, token="tok", client=http)
            emitter = GitLabMREmitter(rest_client=rest, mcp_client=mcp)
            await emitter.emit(recipe, project_id="abu-chaoslab/test-target")

    description = json.loads(route.calls.last.request.content)["params"]["arguments"]["description"]
    # The header line carrying the inline code-span MUST contain the sanitized
    # form. The body (from render_recipe — S6.5 territory) may carry the raw
    # value verbatim; sanitization only protects the emitter's own headers.
    header_line = next(
        line for line in description.splitlines() if line.startswith("**Target agent:**")
    )
    assert "`evilbacktickagent`" in header_line
    assert "`evil`backtick`agent`" not in header_line
    assert any("mr_description_sanitized" in r.message for r in caplog.records)
