"""Thin python-gitlab wrapper for branch + multi-file commit ops (S6.6 hybrid).

ADR-011 + S6.6 amendment: the official `https://gitlab.com/api/v4/mcp` 16-tool
inventory does NOT include `create_branch` or `create_or_update_file`. We use
python-gitlab for those (REST) and route ONLY `create_merge_request` through
MCP — preserving full official-MCP judging credit per partner-gitlab.md.

This client is sync (python-gitlab itself is sync); the orchestrator wraps it
in `asyncio.to_thread` to keep the FastAPI event loop unblocked.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from phoenix_audit_agent.errors import PhoenixAuditError

if TYPE_CHECKING:
    # Stays in TYPE_CHECKING — runtime never needs the actual gitlab module
    # unless `build_default_client` is called. Test stubs satisfy the Protocol
    # below without pulling the SDK into the test process.
    from gitlab.v4.objects import Project  # noqa: F401

logger = logging.getLogger(__name__)


class GitLabRestClientError(PhoenixAuditError, RuntimeError):
    """Raised when a python-gitlab call fails — wrapped with phoenix-audit context."""


# ---------------------------------------------------------------------------
# Narrow Protocols mirroring the python-gitlab Project surface we use.
# Stops a test stub silently drifting from the SDK shape.
# ---------------------------------------------------------------------------


@runtime_checkable
class _BranchesEndpoint(Protocol):
    def create(self, data: dict[str, str], **kwargs: Any) -> Any: ...

    def delete(self, id: str, **kwargs: Any) -> Any: ...  # noqa: A002 — gitlab SDK arg name


@runtime_checkable
class _CommitsEndpoint(Protocol):
    def create(self, data: dict[str, Any], **kwargs: Any) -> Any: ...


@runtime_checkable
class _ProjectLike(Protocol):
    branches: _BranchesEndpoint
    commits: _CommitsEndpoint


class GitLabRestClient:
    """Wraps a python-gitlab Project for branch creation + atomic multi-file commits."""

    def __init__(self, project: _ProjectLike) -> None:
        self._project = project

    def create_branch(self, branch_name: str, ref: str) -> None:
        """POST /projects/:id/repository/branches via python-gitlab."""
        try:
            self._project.branches.create({"branch": branch_name, "ref": ref})
        except Exception as exc:
            msg = f"GitLab branch create failed: {type(exc).__name__}: {exc}"
            raise GitLabRestClientError(msg) from exc
        logger.info("gitlab_branch_created branch=%s ref=%s", branch_name, ref)

    def delete_branch(self, branch_name: str) -> None:
        """DELETE /projects/:id/repository/branches/:branch via python-gitlab.

        Used by `GitLabMREmitter` as a best-effort rollback when MR creation
        fails after the branch+commit pair already landed on GitLab — without
        this, retries hit `Branch already exists` (422) and the user is stuck
        in a half-applied state. Raises GitLabRestClientError on failure so
        the emitter can surface "branch landed without MR" in the user error.
        """
        try:
            self._project.branches.delete(branch_name)
        except Exception as exc:
            msg = f"GitLab branch delete failed: {type(exc).__name__}: {exc}"
            raise GitLabRestClientError(msg) from exc
        logger.info("gitlab_branch_deleted branch=%s", branch_name)

    def create_commit_with_files(
        self,
        branch: str,
        commit_message: str,
        files: list[tuple[str, str]],
    ) -> None:
        """POST /projects/:id/repository/commits with `actions=[{create,...},...]`.

        Atomic — all files land in a single commit so the MR diff is one commit
        instead of N. Empty file list raises; an MR with no files would still
        succeed at the GitLab API but is meaningless for our recipe-emission use.
        """
        if not files:
            msg = "create_commit_with_files: empty file list (would emit a no-op commit)"
            raise GitLabRestClientError(msg)
        actions = [
            {"action": "create", "file_path": path, "content": content} for path, content in files
        ]
        try:
            self._project.commits.create(
                {
                    "branch": branch,
                    "commit_message": commit_message,
                    "actions": actions,
                }
            )
        except Exception as exc:
            msg = (
                f"GitLab commit create failed: {type(exc).__name__}: {exc} "
                f"(branch={branch}, files={len(files)})"
            )
            raise GitLabRestClientError(msg) from exc
        logger.info(
            "gitlab_commit_created branch=%s commit_message=%s files=%d",
            branch,
            commit_message,
            len(files),
        )


def build_default_client(project_id: str, token: str, *, oauth: bool = False) -> GitLabRestClient:
    """Build a python-gitlab Project wrapper.

    `oauth=True` authenticates with a per-user OAuth access token
    (story-9.17 review-first MR filing); default stays the service-env
    private token (seed-script path only).

    Deferred-import so unit tests that inject a stub `_ProjectLike` don't
    incur the gitlab module's transitive HTTP-client imports. Production
    callers (FastAPI lifespan / orchestrator) pay the import cost once at
    boot via the GitLabMREmitter constructor.
    """
    import gitlab

    gl = (
        gitlab.Gitlab("https://gitlab.com", oauth_token=token)
        if oauth
        else gitlab.Gitlab("https://gitlab.com", private_token=token)
    )
    project = gl.projects.get(project_id)
    return GitLabRestClient(project=project)


__all__ = [
    "GitLabRestClient",
    "GitLabRestClientError",
    "build_default_client",
]
