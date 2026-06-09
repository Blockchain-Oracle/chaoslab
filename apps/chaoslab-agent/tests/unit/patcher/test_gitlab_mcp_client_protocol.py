"""MCP client — endpoint construction + JSON-RPC protocol surface.

Sibling: test_gitlab_mcp_client_errors.py (status-code handling),
         test_gitlab_mcp_client_retry.py (5xx + non-JSON retry).
"""

from __future__ import annotations

import json

import httpx
import pytest
import respx

from .conftest import OFFICIAL_ENDPOINT, make_mcp_success_response

# ---------------------------------------------------------------------------
# Construction — banned endpoints + official-equality check
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "banned_url",
    [
        "https://github.com/zereight/gitlab-mcp",
        "https://github.com/mcpland/gitlab-mcp",
        "https://wadew.io/gitlab-mcp",
    ],
)
def test_rejects_banned_community_endpoints(banned_url: str) -> None:
    """partner-gitlab.md lists community wrappers as banned — judging penalty."""
    from chaoslab_agent.patcher._gitlab_mcp_client import GitLabMcpClient

    with pytest.raises(ValueError, match="Community MCP endpoints banned"):
        GitLabMcpClient(endpoint=banned_url)


def test_construction_rejects_non_official_endpoint() -> None:
    """SFH-I #3: positive `endpoint == OFFICIAL_ENDPOINT` check.

    A typo like `https://gitlab.com/api/v3/mcp` (v3 not v4) passes the BANNED
    fragment list but is still wrong — needs strict equality."""
    from chaoslab_agent.patcher._gitlab_mcp_client import GitLabMcpClient

    with pytest.raises(ValueError, match="ADR-011"):
        GitLabMcpClient(endpoint="https://gitlab.com/api/v3/mcp", token="tok")


def test_construction_rejects_typo_in_path() -> None:
    """SFH-I #3 follow-up: a single-character typo MUST fail."""
    from chaoslab_agent.patcher._gitlab_mcp_client import GitLabMcpClient

    with pytest.raises(ValueError, match="ADR-011"):
        GitLabMcpClient(endpoint="https://gitlab.com/api/v4/mc", token="tok")


# ---------------------------------------------------------------------------
# Protocol — actual POST URL + JSON-RPC body shape + Bearer auth + id counter
# ---------------------------------------------------------------------------


@respx.mock
async def test_accepts_official_endpoint_and_posts_to_it() -> None:
    """Behavior probe: actually POSTs to the official URL (was inspecting
    private `_endpoint` attribute — getattr default would silently fall back
    on rename)."""
    from chaoslab_agent.patcher._gitlab_mcp_client import GitLabMcpClient

    route = respx.post(OFFICIAL_ENDPOINT).mock(
        return_value=httpx.Response(200, json=make_mcp_success_response())
    )
    async with httpx.AsyncClient(timeout=5.0) as http:
        client = GitLabMcpClient(endpoint=OFFICIAL_ENDPOINT, token="tok", client=http)
        await client.create_merge_request(
            project_id="x", source_branch="a", target_branch="b", title="t", description="d"
        )
    assert route.called
    assert str(route.calls.last.request.url) == OFFICIAL_ENDPOINT


@respx.mock
async def test_posts_create_merge_request_tool_with_arguments() -> None:
    """BDD: exactly 1 POST with tool=create_merge_request + correct argument shape."""
    from chaoslab_agent.patcher._gitlab_mcp_client import GitLabMcpClient

    route = respx.post(OFFICIAL_ENDPOINT).mock(
        return_value=httpx.Response(200, json=make_mcp_success_response())
    )

    async with httpx.AsyncClient(timeout=5.0) as http:
        client = GitLabMcpClient(endpoint=OFFICIAL_ENDPOINT, token="tok", client=http)
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
async def test_sends_bearer_auth_header() -> None:
    from chaoslab_agent.patcher._gitlab_mcp_client import GitLabMcpClient

    route = respx.post(OFFICIAL_ENDPOINT).mock(
        return_value=httpx.Response(200, json=make_mcp_success_response())
    )

    async with httpx.AsyncClient(timeout=5.0) as http:
        client = GitLabMcpClient(endpoint=OFFICIAL_ENDPOINT, token="my-token", client=http)
        await client.create_merge_request(
            project_id="x", source_branch="a", target_branch="b", title="t", description="d"
        )
    assert route.calls.last.request.headers["Authorization"] == "Bearer my-token"


@respx.mock
async def test_increments_jsonrpc_id_per_attempt() -> None:
    """CR-LOW round-3: hardcoded id=1 on retries risked gateway-side dedupe.
    Lock that the JSON-RPC id increments across retry attempts."""
    from chaoslab_agent.patcher._gitlab_mcp_client import GitLabMcpClient

    route = respx.post(OFFICIAL_ENDPOINT).mock(
        side_effect=[
            httpx.Response(503),
            httpx.Response(503),
            httpx.Response(200, json=make_mcp_success_response()),
        ]
    )

    async with httpx.AsyncClient(timeout=5.0) as http:
        client = GitLabMcpClient(endpoint=OFFICIAL_ENDPOINT, token="tok", client=http)
        await client.create_merge_request(
            project_id="x", source_branch="a", target_branch="b", title="t", description="d"
        )

    ids = [json.loads(call.request.content)["id"] for call in route.calls]
    assert len(ids) == 3
    assert len(set(ids)) == 3, f"ids must be distinct across retries: {ids}"
    assert ids == sorted(ids), f"ids must be monotonic: {ids}"
