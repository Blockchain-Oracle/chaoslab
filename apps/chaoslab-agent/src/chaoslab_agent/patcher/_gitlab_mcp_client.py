"""Async client for the OFFICIAL `https://gitlab.com/api/v4/mcp` endpoint.

Per ADR-011 + partner-gitlab.md: ONLY `create_merge_request` flows through MCP.
Branch + file ops use python-gitlab (see _gitlab_rest_client). Community MCP
servers (zereight / mcpland / wadew) are BANNED — judging-credit penalty.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

OFFICIAL_ENDPOINT: str = "https://gitlab.com/api/v4/mcp"
_BANNED_FRAGMENTS: tuple[str, ...] = ("zereight", "mcpland", "wadew")
_MAX_ATTEMPTS: int = 3
_RETRY_BASE_SECONDS: float = 1.0
_HTTP_UNAUTHORIZED: int = 401
_HTTP_INTERNAL_ERROR: int = 500


class GitLabMcpError(RuntimeError):
    """Raised when MCP `create_merge_request` fails non-recoverably."""


class GitLabMcpClient:
    """Async wrapper over the official GitLab MCP endpoint's `create_merge_request` tool."""

    def __init__(
        self,
        endpoint: str | None = None,
        token: str | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._endpoint = endpoint or OFFICIAL_ENDPOINT
        if any(b in self._endpoint for b in _BANNED_FRAGMENTS):
            msg = f"Community MCP endpoints banned per partner-gitlab.md: {self._endpoint}"
            raise ValueError(msg)
        self._token = token
        self._client = client or httpx.AsyncClient(timeout=30.0)

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
        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
            "id": 1,
        }
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        response: httpx.Response | None = None
        for attempt in range(_MAX_ATTEMPTS):
            response = await self._client.post(self._endpoint, json=payload, headers=headers)
            if response.status_code == _HTTP_UNAUTHORIZED:
                raise GitLabMcpError(f"GitLab MCP authentication failed (401) tool={tool_name}")
            if response.status_code >= _HTTP_INTERNAL_ERROR and attempt < _MAX_ATTEMPTS - 1:
                await asyncio.sleep(_RETRY_BASE_SECONDS * (2**attempt))
                continue
            response.raise_for_status()
            data = response.json()
            if "error" in data:
                raise GitLabMcpError(f"GitLab MCP error tool={tool_name} error={data['error']}")
            return data.get("result", {})
        status = response.status_code if response else "?"
        raise GitLabMcpError(f"GitLab MCP exhausted retries tool={tool_name} last_status={status}")

    async def aclose(self) -> None:
        await self._client.aclose()


__all__ = ["OFFICIAL_ENDPOINT", "GitLabMcpClient", "GitLabMcpError"]
