"""python-gitlab calls made with a USER's OAuth token (story-9.17).

python-gitlab does not auto-refresh OAuth tokens — callers obtain a valid
token via `gitlab_oauth.get_valid_access_token` FIRST. The SDK is blocking;
everything runs in a thread.
"""

from __future__ import annotations

import asyncio
from typing import Any

GITLAB_URL = "https://gitlab.com"
# Developer (30) is the minimum role that can push a branch + open an MR —
# filtering at Maintainer would hide legitimate targets.
MIN_ACCESS_LEVEL = 30


async def list_projects(token: str) -> list[dict[str, Any]]:
    """Projects the user can file an MR into: `[{id, path_with_namespace}]`."""

    def _list() -> list[dict[str, Any]]:
        import gitlab

        gl = gitlab.Gitlab(GITLAB_URL, oauth_token=token)
        projects = gl.projects.list(
            membership=True, min_access_level=MIN_ACCESS_LEVEL, per_page=100, iterator=False
        )
        return [{"id": p.id, "path_with_namespace": p.path_with_namespace} for p in projects]

    return await asyncio.to_thread(_list)


__all__ = ["MIN_ACCESS_LEVEL", "list_projects"]
