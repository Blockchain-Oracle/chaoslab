"""Async client for the OFFICIAL `https://gitlab.com/api/v4/mcp` endpoint.

Per ADR-011 + partner-gitlab.md: ONLY `create_merge_request` flows through MCP.
Branch + file ops use python-gitlab (see _gitlab_rest_client). Community MCP
servers (zereight / mcpland / wadew) are BANNED — judging-credit penalty.

Round-2 hardening (PR #74 reviewer fleet):
- Positive equality check `endpoint == OFFICIAL_ENDPOINT` (the substring banned-list
  is informational; the equality is load-bearing).
- 4xx non-401 errors wrap to GitLabMcpError (was leaking as httpx.HTTPStatusError).
- Nested MCP errors (`result.error` / `result.isError`) surfaced explicitly.
- JSONDecodeError on non-JSON responses (HTML maintenance page, auth wall) → retry.
- Explicit missing-`result`-key error vs. empty-dict-result silent fallthrough.
"""

from __future__ import annotations

import asyncio
import itertools
import json
import logging
from typing import Any

import httpx

from phoenix_audit_agent.errors import PhoenixAuditError

logger = logging.getLogger(__name__)

OFFICIAL_ENDPOINT: str = "https://gitlab.com/api/v4/mcp"
_BANNED_FRAGMENTS: tuple[str, ...] = ("zereight", "mcpland", "wadew")
_MAX_ATTEMPTS: int = 3
_RETRY_BASE_SECONDS: float = 1.0
_HTTP_REDIRECT: int = 300
_HTTP_BAD_REQUEST: int = 400
_HTTP_UNAUTHORIZED: int = 401
_HTTP_INTERNAL_ERROR: int = 500


class GitLabMcpError(PhoenixAuditError, RuntimeError):
    """Raised when MCP `create_merge_request` fails non-recoverably.

    `auth_failed` is set True iff the failure was a 401 — round-3 review
    flagged that substring-matching `"401"` or `"authentication"` on the
    error message was fragile (false-positive on any unrelated mention).
    The emitter checks `exc.auth_failed` to surface auth-specific messaging.
    """

    def __init__(self, *args: object, auth_failed: bool = False) -> None:
        super().__init__(*args)
        self.auth_failed = auth_failed


class GitLabMcpClient:
    """Async wrapper over the official GitLab MCP endpoint's `create_merge_request` tool."""

    def __init__(
        self,
        endpoint: str | None = None,
        token: str | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._endpoint = endpoint or OFFICIAL_ENDPOINT
        if self._endpoint != OFFICIAL_ENDPOINT:
            # Better error message when the URL matches a known community wrapper;
            # otherwise fall through to the strict ADR-011 mismatch message.
            if any(b in self._endpoint for b in _BANNED_FRAGMENTS):
                msg = f"Community MCP endpoints banned per partner-gitlab.md: {self._endpoint}"
                raise ValueError(msg)
            msg = f"Endpoint must be {OFFICIAL_ENDPOINT!r} per ADR-011 (got {self._endpoint!r})"
            raise ValueError(msg)
        self._token = token
        # follow_redirects=True belts the explicit 3xx branch below: even if a
        # future GitLab MCP version starts redirecting, httpx auto-resolves
        # before we see the status code. The 3xx branch is the suspenders.
        self._client = client or httpx.AsyncClient(timeout=30.0, follow_redirects=True)
        # Per-instance JSON-RPC id counter — round-3 reviewer flagged that
        # hardcoding `id: 1` risks gateway-side dedupe on retries.
        self._id_counter = itertools.count(1)

    async def create_merge_request(
        self,
        project_id: str,
        source_branch: str,
        target_branch: str,
        title: str,
        description: str,
        labels: list[str] | None = None,
    ) -> dict[str, Any]:
        args: dict[str, Any] = {
            "project_id": project_id,
            "source_branch": source_branch,
            "target_branch": target_branch,
            "title": title,
            "description": description,
        }
        if labels:
            args["labels"] = ",".join(labels)
        return await self._call_tool("create_merge_request", args)

    async def _call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        response: httpx.Response | None = None
        for attempt in range(_MAX_ATTEMPTS):
            # Fresh id per attempt — round-3: hardcoded id=1 risks gateway-side
            # request dedupe on retries (and collides between concurrent calls).
            payload = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {"name": tool_name, "arguments": arguments},
                "id": next(self._id_counter),
            }
            response = await self._client.post(self._endpoint, json=payload, headers=headers)
            if response.status_code == _HTTP_UNAUTHORIZED:
                raise GitLabMcpError(
                    f"GitLab MCP authentication failed (401) tool={tool_name}",
                    auth_failed=True,
                )
            if _HTTP_REDIRECT <= response.status_code < _HTTP_BAD_REQUEST:
                # 3xx slipping past httpx's follow_redirects=True means the
                # server returned a redirect httpx didn't follow (e.g.,
                # cross-scheme). Surface explicitly instead of letting the
                # response body trip JSONDecodeError downstream.
                raise GitLabMcpError(
                    f"GitLab MCP unexpected redirect {response.status_code} "
                    f"tool={tool_name} location={response.headers.get('location', '?')}"
                )
            if response.status_code >= _HTTP_INTERNAL_ERROR:
                if attempt < _MAX_ATTEMPTS - 1:
                    await asyncio.sleep(_RETRY_BASE_SECONDS * (2**attempt))
                    continue
                # Retries exhausted — wrap as GitLabMcpError (was leaking as
                # httpx.HTTPStatusError via raise_for_status, escaping the
                # emitter's `except GitLabMcpError` handler).
                raise GitLabMcpError(
                    f"GitLab MCP {response.status_code} (retries exhausted) tool={tool_name} "
                    f"body={response.text[:200]}"
                )
            if _HTTP_BAD_REQUEST <= response.status_code < _HTTP_INTERNAL_ERROR:
                # Non-401 4xx — wrap explicitly so the emitter's `except
                # GitLabMcpError` catches it instead of letting httpx.HTTPStatusError
                # escape the orchestrator.
                raise GitLabMcpError(
                    f"GitLab MCP {response.status_code} tool={tool_name} body={response.text[:200]}"
                )
            try:
                data = response.json()
            except (json.JSONDecodeError, ValueError) as exc:
                if attempt < _MAX_ATTEMPTS - 1:
                    # Server returned 200 + non-JSON (HTML maintenance page, etc.) —
                    # retry, the next attempt may get JSON.
                    await asyncio.sleep(_RETRY_BASE_SECONDS * (2**attempt))
                    continue
                msg = (
                    f"GitLab MCP returned non-JSON body tool={tool_name} "
                    f"body_head={response.text[:200]}"
                )
                raise GitLabMcpError(msg) from exc
            return self._unwrap_result(data, tool_name)
        status = response.status_code if response else "?"
        raise GitLabMcpError(f"GitLab MCP exhausted retries tool={tool_name} last_status={status}")

    @staticmethod
    def _unwrap_result(data: dict[str, Any], tool_name: str) -> dict[str, Any]:
        """Surface MCP error envelopes; return the success payload otherwise."""
        # JSON-RPC top-level error.
        if "error" in data:
            raise GitLabMcpError(f"GitLab MCP error tool={tool_name} error={data['error']}")
        # Distinguish "no result key" from "result is an empty dict" — the former
        # signals a broken server or wrong endpoint version; conflating with the
        # latter would silently fall through to `_extract_mr_field` raising a
        # less-informative "missing key" error.
        if "result" not in data:
            raise GitLabMcpError(
                f"GitLab MCP response had no 'result' key tool={tool_name} keys={list(data.keys())}"
            )
        result = data["result"]
        # Tool-level error envelope (MCP convention) — surface explicitly so the
        # GitLab API's actual error message (e.g. "422 branch already exists")
        # reaches the user instead of bubbling as a missing-web_url error.
        if isinstance(result, dict):
            if result.get("isError"):
                raise GitLabMcpError(
                    f"GitLab MCP tool {tool_name} returned isError=true result={result}"
                )
            nested = result.get("error")
            if nested:
                raise GitLabMcpError(f"GitLab MCP tool {tool_name} returned nested error: {nested}")
        if not isinstance(result, dict):
            # Round-3: silently returning `{}` for a list/string result would
            # trip `_extract_mr_field` with a confusing "missing field 'web_url'"
            # error. Fail loud so the operator sees the actual shape problem.
            raise GitLabMcpError(
                f"GitLab MCP tool {tool_name} returned unexpected result type: "
                f"{type(result).__name__}"
            )
        return result

    async def aclose(self) -> None:
        await self._client.aclose()


__all__ = ["OFFICIAL_ENDPOINT", "GitLabMcpClient", "GitLabMcpError"]
