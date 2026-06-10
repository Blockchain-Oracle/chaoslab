"""MCP client — HTTP status + envelope error handling.

Sibling: test_gitlab_mcp_client_protocol.py (construction + JSON-RPC body),
         test_gitlab_mcp_client_retry.py (5xx + non-JSON retry).
"""

from __future__ import annotations

import httpx
import pytest
import respx

from .conftest import OFFICIAL_ENDPOINT

# ---------------------------------------------------------------------------
# 401 — explicit auth_failed flag (round-3 replaced substring match)
# ---------------------------------------------------------------------------


@respx.mock
async def test_raises_on_401_with_authentication_message() -> None:
    from phoenix_audit_agent.patcher._gitlab_mcp_client import GitLabMcpClient, GitLabMcpError

    respx.post(OFFICIAL_ENDPOINT).mock(
        return_value=httpx.Response(401, json={"message": "401 Unauthorized"})
    )

    async with httpx.AsyncClient(timeout=5.0) as http:
        client = GitLabMcpClient(endpoint=OFFICIAL_ENDPOINT, token="bad", client=http)
        with pytest.raises(GitLabMcpError, match="authentication"):
            await client.create_merge_request(
                project_id="x", source_branch="a", target_branch="b", title="t", description="d"
            )


@respx.mock
async def test_401_sets_auth_failed_flag() -> None:
    """CR-MED round-3: explicit `auth_failed` attr replaces fragile substring match."""
    from phoenix_audit_agent.patcher._gitlab_mcp_client import GitLabMcpClient, GitLabMcpError

    respx.post(OFFICIAL_ENDPOINT).mock(return_value=httpx.Response(401))
    async with httpx.AsyncClient(timeout=5.0) as http:
        client = GitLabMcpClient(endpoint=OFFICIAL_ENDPOINT, token="bad", client=http)
        with pytest.raises(GitLabMcpError) as exc_info:
            await client.create_merge_request(
                project_id="x", source_branch="a", target_branch="b", title="t", description="d"
            )
    assert exc_info.value.auth_failed is True


@respx.mock
async def test_non_auth_failures_have_auth_failed_false() -> None:
    """CR-MED round-3: 5xx (or any non-401) failures must NOT set auth_failed.
    Substring match would have false-positive'd on any "401" or "authentication"
    text in the body — this lock proves the explicit flag fixes that."""
    from phoenix_audit_agent.patcher._gitlab_mcp_client import GitLabMcpClient, GitLabMcpError

    # 500 body mentions "authentication" — the legacy substring code would
    # have misclassified this as auth failure.
    respx.post(OFFICIAL_ENDPOINT).mock(
        return_value=httpx.Response(500, text="internal authentication backend down")
    )
    async with httpx.AsyncClient(timeout=5.0) as http:
        client = GitLabMcpClient(endpoint=OFFICIAL_ENDPOINT, token="tok", client=http)
        with pytest.raises(GitLabMcpError) as exc_info:
            await client.create_merge_request(
                project_id="x", source_branch="a", target_branch="b", title="t", description="d"
            )
    assert exc_info.value.auth_failed is False


# ---------------------------------------------------------------------------
# 4xx (non-401) — wrap to GitLabMcpError (was leaking httpx.HTTPStatusError)
# ---------------------------------------------------------------------------


@respx.mock
async def test_wraps_non_401_404_in_emitter_error() -> None:
    """SFH-BLOCKER #2: 404 must wrap to GitLabMcpError, NOT escape as
    httpx.HTTPStatusError past the emitter's `except GitLabMcpError`."""
    from phoenix_audit_agent.patcher._gitlab_mcp_client import GitLabMcpClient, GitLabMcpError

    respx.post(OFFICIAL_ENDPOINT).mock(return_value=httpx.Response(404, text="Project Not Found"))

    async with httpx.AsyncClient(timeout=5.0) as http:
        client = GitLabMcpClient(endpoint=OFFICIAL_ENDPOINT, token="tok", client=http)
        with pytest.raises(GitLabMcpError, match="404"):
            await client.create_merge_request(
                project_id="nonexistent/project",
                source_branch="a",
                target_branch="b",
                title="t",
                description="d",
            )


@respx.mock
async def test_wraps_403_forbidden() -> None:
    """SFH-BLOCKER #2 — 403 (insufficient PAT scope) also wraps cleanly."""
    from phoenix_audit_agent.patcher._gitlab_mcp_client import GitLabMcpClient, GitLabMcpError

    respx.post(OFFICIAL_ENDPOINT).mock(return_value=httpx.Response(403, text="Forbidden"))
    async with httpx.AsyncClient(timeout=5.0) as http:
        client = GitLabMcpClient(endpoint=OFFICIAL_ENDPOINT, token="tok", client=http)
        with pytest.raises(GitLabMcpError, match="403"):
            await client.create_merge_request(
                project_id="x", source_branch="a", target_branch="b", title="t", description="d"
            )


# ---------------------------------------------------------------------------
# 3xx — round-3: redirects that httpx doesn't follow surface explicitly
# ---------------------------------------------------------------------------


@respx.mock
async def test_raises_on_3xx_redirect_not_followed() -> None:
    """SFH-MED round-3: 3xx redirects that httpx doesn't follow MUST surface
    explicitly. Was falling through to `response.json()` → JSONDecodeError →
    retry → confusing "non-JSON body" error."""
    from phoenix_audit_agent.patcher._gitlab_mcp_client import GitLabMcpClient, GitLabMcpError

    # follow_redirects=False on the test client so we observe the raw 3xx.
    respx.post(OFFICIAL_ENDPOINT).mock(
        return_value=httpx.Response(308, headers={"location": "https://elsewhere.example/mcp"})
    )

    async with httpx.AsyncClient(timeout=5.0, follow_redirects=False) as http:
        client = GitLabMcpClient(endpoint=OFFICIAL_ENDPOINT, token="tok", client=http)
        with pytest.raises(GitLabMcpError, match="unexpected redirect 308"):
            await client.create_merge_request(
                project_id="x", source_branch="a", target_branch="b", title="t", description="d"
            )


# ---------------------------------------------------------------------------
# Envelope-shape errors — surface JSON-RPC errors + isError + missing result
# ---------------------------------------------------------------------------


@respx.mock
async def test_surfaces_nested_result_error() -> None:
    """SFH-I #5: tool-level error nested inside `result.error` is surfaced."""
    from phoenix_audit_agent.patcher._gitlab_mcp_client import GitLabMcpClient, GitLabMcpError

    respx.post(OFFICIAL_ENDPOINT).mock(
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
        client = GitLabMcpClient(endpoint=OFFICIAL_ENDPOINT, token="tok", client=http)
        with pytest.raises(GitLabMcpError, match="branch already exists"):
            await client.create_merge_request(
                project_id="x", source_branch="a", target_branch="b", title="t", description="d"
            )


@respx.mock
async def test_surfaces_is_error_envelope() -> None:
    """SFH-I #5: MCP `isError: true` convention is surfaced explicitly."""
    from phoenix_audit_agent.patcher._gitlab_mcp_client import GitLabMcpClient, GitLabMcpError

    respx.post(OFFICIAL_ENDPOINT).mock(
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
        client = GitLabMcpClient(endpoint=OFFICIAL_ENDPOINT, token="tok", client=http)
        with pytest.raises(GitLabMcpError, match="isError"):
            await client.create_merge_request(
                project_id="x", source_branch="a", target_branch="b", title="t", description="d"
            )


@respx.mock
async def test_missing_result_key_raises_explicit() -> None:
    """SFH-S #8: distinguish missing-result (broken server) from empty-result-dict."""
    from phoenix_audit_agent.patcher._gitlab_mcp_client import GitLabMcpClient, GitLabMcpError

    respx.post(OFFICIAL_ENDPOINT).mock(
        return_value=httpx.Response(200, json={"jsonrpc": "2.0", "id": 1})
    )
    async with httpx.AsyncClient(timeout=5.0) as http:
        client = GitLabMcpClient(endpoint=OFFICIAL_ENDPOINT, token="tok", client=http)
        with pytest.raises(GitLabMcpError, match="no 'result' key"):
            await client.create_merge_request(
                project_id="x", source_branch="a", target_branch="b", title="t", description="d"
            )


@respx.mock
async def test_fails_loud_on_non_dict_result() -> None:
    """SFH-MED round-3 + CR-MED #2: result-type mismatch (list/string) must
    surface as 'unexpected result type', NOT silently fall through to
    `_extract_mr_field` raising 'missing required field web_url'."""
    from phoenix_audit_agent.patcher._gitlab_mcp_client import GitLabMcpClient, GitLabMcpError

    respx.post(OFFICIAL_ENDPOINT).mock(
        return_value=httpx.Response(
            200, json={"jsonrpc": "2.0", "id": 1, "result": ["wrong", "shape"]}
        )
    )
    async with httpx.AsyncClient(timeout=5.0) as http:
        client = GitLabMcpClient(endpoint=OFFICIAL_ENDPOINT, token="tok", client=http)
        with pytest.raises(GitLabMcpError, match="unexpected result type: list"):
            await client.create_merge_request(
                project_id="x", source_branch="a", target_branch="b", title="t", description="d"
            )
