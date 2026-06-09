"""GitLab emitter — failure paths: auth, rollback, cause chains, sanitization, ADR-011.

Happy-path orchestration + result-model tests live in
test_gitlab_emitter_orchestration.py.
"""

from __future__ import annotations

import json

import httpx
import pytest
import respx

from chaoslab_agent.config import get_settings
from chaoslab_agent.judge.clustering import FailureClusterSet
from chaoslab_agent.patcher.recipe import FailureCluster, HardeningRecipe

from .conftest import OFFICIAL_ENDPOINT, make_fake_project, make_mcp_success_response, make_recipe

# ---------------------------------------------------------------------------
# Auth failure surfaces with the explicit `auth_failed` flag (round-3) +
# wraps the receipt-card-grep'able "authentication" marker.
# ---------------------------------------------------------------------------


@respx.mock
async def test_emit_401_wraps_to_emitter_error_with_authentication_message() -> None:
    from chaoslab_agent.patcher._gitlab_mcp_client import GitLabMcpClient
    from chaoslab_agent.patcher._gitlab_rest_client import GitLabRestClient
    from chaoslab_agent.patcher.gitlab_emitter import GitLabEmitterError, GitLabMREmitter

    respx.post(OFFICIAL_ENDPOINT).mock(
        return_value=httpx.Response(401, json={"message": "401 Unauthorized"})
    )
    project = make_fake_project()
    rest = GitLabRestClient(project=project)
    async with httpx.AsyncClient(timeout=5.0) as http:
        mcp = GitLabMcpClient(endpoint=OFFICIAL_ENDPOINT, token="bad", client=http)
        emitter = GitLabMREmitter(rest_client=rest, mcp_client=mcp)
        with pytest.raises(GitLabEmitterError, match="authentication"):
            await emitter.emit(make_recipe(), project_id="abu-chaoslab/test-target")


@respx.mock
async def test_emit_401_chain_preserves_cause() -> None:
    """TQ-MED #6: `__cause__` chain locked — a future refactor that drops `from exc`
    loses debuggability but would pass the substring-match-only assertion."""
    from chaoslab_agent.patcher._gitlab_mcp_client import GitLabMcpClient, GitLabMcpError
    from chaoslab_agent.patcher._gitlab_rest_client import GitLabRestClient
    from chaoslab_agent.patcher.gitlab_emitter import GitLabEmitterError, GitLabMREmitter

    respx.post(OFFICIAL_ENDPOINT).mock(return_value=httpx.Response(401, json={"message": "401"}))
    project = make_fake_project()
    rest = GitLabRestClient(project=project)
    async with httpx.AsyncClient(timeout=5.0) as http:
        mcp = GitLabMcpClient(endpoint=OFFICIAL_ENDPOINT, token="bad", client=http)
        emitter = GitLabMREmitter(rest_client=rest, mcp_client=mcp)
        with pytest.raises(GitLabEmitterError) as exc_info:
            await emitter.emit(make_recipe(), project_id="abu-chaoslab/test-target")

    assert exc_info.value.__cause__ is not None
    assert isinstance(exc_info.value.__cause__, GitLabMcpError)


@respx.mock
async def test_emit_rest_failure_chain_preserves_cause() -> None:
    """CR-MED #3: GitLabRestClientError propagates as __cause__ — locks the rest
    error path (was untested in round-1)."""
    from chaoslab_agent.patcher._gitlab_mcp_client import GitLabMcpClient
    from chaoslab_agent.patcher._gitlab_rest_client import GitLabRestClient, GitLabRestClientError
    from chaoslab_agent.patcher.gitlab_emitter import GitLabEmitterError, GitLabMREmitter

    respx.post(OFFICIAL_ENDPOINT).mock(
        return_value=httpx.Response(200, json=make_mcp_success_response())
    )
    project = make_fake_project()
    project.branches.create.side_effect = RuntimeError("network exploded")
    rest = GitLabRestClient(project=project)

    async with httpx.AsyncClient(timeout=5.0) as http:
        mcp = GitLabMcpClient(endpoint=OFFICIAL_ENDPOINT, token="tok", client=http)
        emitter = GitLabMREmitter(rest_client=rest, mcp_client=mcp)
        with pytest.raises(GitLabEmitterError) as exc_info:
            await emitter.emit(make_recipe(), project_id="abu-chaoslab/test-target")

    assert exc_info.value.__cause__ is not None
    assert isinstance(exc_info.value.__cause__, GitLabRestClientError)


# ---------------------------------------------------------------------------
# Rollback semantics — best-effort delete + branch_name surfaces + flag
# ---------------------------------------------------------------------------


@respx.mock
async def test_emit_rolls_back_branch_when_mcp_fails() -> None:
    """SFH-BLOCKER #1: orphan branch leak — REST succeeded, MCP failed.
    `branches.delete` is called best-effort + branch_name surfaces in error."""
    from chaoslab_agent.patcher._gitlab_mcp_client import GitLabMcpClient
    from chaoslab_agent.patcher._gitlab_rest_client import GitLabRestClient
    from chaoslab_agent.patcher.gitlab_emitter import GitLabEmitterError, GitLabMREmitter

    respx.post(OFFICIAL_ENDPOINT).mock(return_value=httpx.Response(500))
    project = make_fake_project()
    rest = GitLabRestClient(project=project)

    async with httpx.AsyncClient(timeout=5.0) as http:
        mcp = GitLabMcpClient(endpoint=OFFICIAL_ENDPOINT, token="tok", client=http)
        emitter = GitLabMREmitter(rest_client=rest, mcp_client=mcp)
        with pytest.raises(GitLabEmitterError, match="chaoslab/recipe-abc123def456"):
            await emitter.emit(make_recipe(), project_id="abu-chaoslab/test-target")

    assert project.branches.delete.call_count == 1
    assert project.branches.delete.call_args[0][0] == "chaoslab/recipe-abc123def456"


@respx.mock
async def test_emit_propagates_mcp_error_even_when_rollback_fails() -> None:
    """SFH-BLOCKER #1: rollback is best-effort. If `branches.delete` ITSELF raises,
    the MCP error still surfaces (preserving root cause for the operator)."""
    from chaoslab_agent.patcher._gitlab_mcp_client import GitLabMcpClient
    from chaoslab_agent.patcher._gitlab_rest_client import GitLabRestClient
    from chaoslab_agent.patcher.gitlab_emitter import GitLabEmitterError, GitLabMREmitter

    respx.post(OFFICIAL_ENDPOINT).mock(return_value=httpx.Response(500))
    project = make_fake_project()
    project.branches.delete.side_effect = RuntimeError("rollback broke too")
    rest = GitLabRestClient(project=project)

    async with httpx.AsyncClient(timeout=5.0) as http:
        mcp = GitLabMcpClient(endpoint=OFFICIAL_ENDPOINT, token="tok", client=http)
        emitter = GitLabMREmitter(rest_client=rest, mcp_client=mcp)
        with pytest.raises(GitLabEmitterError, match="chaoslab/recipe-abc123def456"):
            await emitter.emit(make_recipe(), project_id="abu-chaoslab/test-target")


@respx.mock
async def test_emit_does_not_rollback_when_rest_fails_before_mcp() -> None:
    """If REST branch.create fails, MCP is never called and rollback is moot."""
    from chaoslab_agent.patcher._gitlab_mcp_client import GitLabMcpClient
    from chaoslab_agent.patcher._gitlab_rest_client import GitLabRestClient
    from chaoslab_agent.patcher.gitlab_emitter import GitLabEmitterError, GitLabMREmitter

    mcp_route = respx.post(OFFICIAL_ENDPOINT).mock(
        return_value=httpx.Response(200, json=make_mcp_success_response())
    )
    project = make_fake_project()
    project.branches.create.side_effect = RuntimeError("rest dead")
    rest = GitLabRestClient(project=project)

    async with httpx.AsyncClient(timeout=5.0) as http:
        mcp = GitLabMcpClient(endpoint=OFFICIAL_ENDPOINT, token="tok", client=http)
        emitter = GitLabMREmitter(rest_client=rest, mcp_client=mcp)
        with pytest.raises(GitLabEmitterError, match="GitLab branch/commit failed"):
            await emitter.emit(make_recipe(), project_id="abu-chaoslab/test-target")

    assert mcp_route.call_count == 0
    assert project.branches.delete.call_count == 0


@respx.mock
async def test_emit_rolls_back_signals_rollback_failed_false_on_success() -> None:
    """SFH-LOW round-3: receipt-card surface needs a programmatic signal — not
    just a log — to render "branch may still exist" vs "branch cleaned up"."""
    from chaoslab_agent.patcher._gitlab_mcp_client import GitLabMcpClient
    from chaoslab_agent.patcher._gitlab_rest_client import GitLabRestClient
    from chaoslab_agent.patcher.gitlab_emitter import GitLabEmitterError, GitLabMREmitter

    respx.post(OFFICIAL_ENDPOINT).mock(return_value=httpx.Response(500))
    project = make_fake_project()
    rest = GitLabRestClient(project=project)
    async with httpx.AsyncClient(timeout=5.0) as http:
        mcp = GitLabMcpClient(endpoint=OFFICIAL_ENDPOINT, token="tok", client=http)
        emitter = GitLabMREmitter(rest_client=rest, mcp_client=mcp)
        with pytest.raises(GitLabEmitterError) as exc_info:
            await emitter.emit(make_recipe(), project_id="abu-chaoslab/test-target")

    assert exc_info.value.rollback_failed is False


@respx.mock
async def test_emit_signals_rollback_failed_true_when_delete_raises() -> None:
    """SFH-LOW round-3: when delete_branch raises, surface rollback_failed=True
    so the receipt card can render 'manual cleanup at .../-/branches/<x>'."""
    from chaoslab_agent.patcher._gitlab_mcp_client import GitLabMcpClient
    from chaoslab_agent.patcher._gitlab_rest_client import GitLabRestClient
    from chaoslab_agent.patcher.gitlab_emitter import GitLabEmitterError, GitLabMREmitter

    respx.post(OFFICIAL_ENDPOINT).mock(return_value=httpx.Response(500))
    project = make_fake_project()
    project.branches.delete.side_effect = RuntimeError("rollback also dead")
    rest = GitLabRestClient(project=project)
    async with httpx.AsyncClient(timeout=5.0) as http:
        mcp = GitLabMcpClient(endpoint=OFFICIAL_ENDPOINT, token="tok", client=http)
        emitter = GitLabMREmitter(rest_client=rest, mcp_client=mcp)
        with pytest.raises(GitLabEmitterError) as exc_info:
            await emitter.emit(make_recipe(), project_id="abu-chaoslab/test-target")

    assert exc_info.value.rollback_failed is True


# ---------------------------------------------------------------------------
# Result-extraction failure modes + Markdown injection sanitization +
# emitter-level ADR-011 lock.
# ---------------------------------------------------------------------------


@respx.mock
async def test_emit_returns_descriptive_error_on_null_mr_field() -> None:
    """SFH-I #4: MCP returning `{"web_url": null}` must surface a clear error,
    NOT the string "None" then failing url validation with a confusing message."""
    from chaoslab_agent.patcher._gitlab_mcp_client import GitLabMcpClient
    from chaoslab_agent.patcher._gitlab_rest_client import GitLabRestClient
    from chaoslab_agent.patcher.gitlab_emitter import GitLabEmitterError, GitLabMREmitter

    respx.post(OFFICIAL_ENDPOINT).mock(
        return_value=httpx.Response(
            200, json={"jsonrpc": "2.0", "id": 1, "result": {"iid": 1, "web_url": None}}
        )
    )
    project = make_fake_project()
    rest = GitLabRestClient(project=project)
    async with httpx.AsyncClient(timeout=5.0) as http:
        mcp = GitLabMcpClient(endpoint=OFFICIAL_ENDPOINT, token="tok", client=http)
        emitter = GitLabMREmitter(rest_client=rest, mcp_client=mcp)
        with pytest.raises(GitLabEmitterError, match="missing required field"):
            await emitter.emit(make_recipe(), project_id="abu-chaoslab/test-target")


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

    route = respx.post(OFFICIAL_ENDPOINT).mock(
        return_value=httpx.Response(200, json=make_mcp_success_response())
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
    project = make_fake_project()
    rest = GitLabRestClient(project=project)
    with caplog.at_level(_logging.WARNING, logger="chaoslab_agent.patcher.gitlab_emitter"):
        async with httpx.AsyncClient(timeout=5.0) as http:
            mcp = GitLabMcpClient(endpoint=OFFICIAL_ENDPOINT, token="tok", client=http)
            emitter = GitLabMREmitter(rest_client=rest, mcp_client=mcp)
            await emitter.emit(recipe, project_id="abu-chaoslab/test-target")

    description = json.loads(route.calls.last.request.content)["params"]["arguments"]["description"]
    header_line = next(
        line for line in description.splitlines() if line.startswith("**Target agent:**")
    )
    assert "`evilbacktickagent`" in header_line
    assert "`evil`backtick`agent`" not in header_line
    assert any("mr_description_sanitized" in r.message for r in caplog.records)


def test_emitter_construction_rejects_non_official_mcp_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ADR-011 lock at the emitter level — even if Settings drift, construction fails."""
    from chaoslab_agent.patcher.gitlab_emitter import GitLabEmitterError, GitLabMREmitter

    monkeypatch.setenv("GITLAB_MCP_ENDPOINT", "https://github.com/zereight/gitlab-mcp")
    get_settings.cache_clear()
    with pytest.raises((GitLabEmitterError, ValueError), match=r"ADR-011|Community MCP"):
        GitLabMREmitter()
