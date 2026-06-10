"""MCP client — 5xx + non-JSON retry behavior.

Sibling: test_gitlab_mcp_client_protocol.py (construction + JSON-RPC body),
         test_gitlab_mcp_client_errors.py (status-code handling).
"""

from __future__ import annotations

import httpx
import pytest
import respx

from .conftest import OFFICIAL_ENDPOINT, make_mcp_success_response


@respx.mock
async def test_retries_on_5xx_up_to_three_attempts() -> None:
    """503 twice → 200. Locks the retry loop call count."""
    from phoenix_audit_agent.patcher._gitlab_mcp_client import GitLabMcpClient

    route = respx.post(OFFICIAL_ENDPOINT).mock(
        side_effect=[
            httpx.Response(503, text="busy"),
            httpx.Response(503, text="busy"),
            httpx.Response(200, json=make_mcp_success_response()),
        ]
    )

    async with httpx.AsyncClient(timeout=5.0) as http:
        client = GitLabMcpClient(endpoint=OFFICIAL_ENDPOINT, token="tok", client=http)
        result = await client.create_merge_request(
            project_id="x", source_branch="a", target_branch="b", title="t", description="d"
        )
    assert route.call_count == 3
    assert result.get("iid") == 42 or result.get("web_url", "").endswith("/42")


@respx.mock
async def test_retries_on_non_json_response() -> None:
    """SFH-S #6: maintenance-page HTML at 200 → retry, eventual JSON success."""
    from phoenix_audit_agent.patcher._gitlab_mcp_client import GitLabMcpClient

    route = respx.post(OFFICIAL_ENDPOINT).mock(
        side_effect=[
            httpx.Response(200, text="<html>maintenance</html>"),
            httpx.Response(200, json=make_mcp_success_response()),
        ]
    )
    async with httpx.AsyncClient(timeout=5.0) as http:
        client = GitLabMcpClient(endpoint=OFFICIAL_ENDPOINT, token="tok", client=http)
        result = await client.create_merge_request(
            project_id="x", source_branch="a", target_branch="b", title="t", description="d"
        )
    assert route.call_count == 2
    assert result.get("iid") == 42


@respx.mock
async def test_5xx_retry_uses_exponential_backoff_schedule(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Round-3 (TQ-MED): lock the EXPONENTIAL schedule magnitudes — `[1.0, 2.0]`
    matches `_RETRY_BASE_SECONDS * 2**attempt`. A linear (1.0→1.5) refactor would
    silently pass an "only-strictly-increasing" assertion."""
    from phoenix_audit_agent.patcher import _gitlab_mcp_client as mcp_mod

    respx.post(OFFICIAL_ENDPOINT).mock(
        side_effect=[
            httpx.Response(503),
            httpx.Response(503),
            httpx.Response(200, json=make_mcp_success_response()),
        ]
    )

    sleep_delays: list[float] = []

    async def _record_sleep(delay: float) -> None:
        sleep_delays.append(delay)

    # Patch at the module's bound `asyncio.sleep` — a future refactor that
    # switches to `time.sleep`, `anyio.sleep`, or removes sleep entirely will
    # record zero delays, failing the length assertion below loudly.
    monkeypatch.setattr(mcp_mod.asyncio, "sleep", _record_sleep)

    async with httpx.AsyncClient(timeout=5.0) as http:
        client = mcp_mod.GitLabMcpClient(endpoint=OFFICIAL_ENDPOINT, token="tok", client=http)
        await client.create_merge_request(
            project_id="x", source_branch="a", target_branch="b", title="t", description="d"
        )

    # Two sleeps between three POSTs. Magnitudes locked to base * 2**attempt,
    # not just "strictly increasing" — a future linear-backoff refactor would
    # silently pass the looser check.
    assert sleep_delays == [pytest.approx(1.0), pytest.approx(2.0)]
