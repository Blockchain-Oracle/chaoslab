"""GitLabMREmitter — renders HardeningRecipe, creates branch + commits files,
opens a real Merge Request via the official GitLab MCP endpoint.

Hybrid per ADR-011 + partner-gitlab.md:
- Branch + multi-file commit ops via python-gitlab REST SDK (the official MCP
  16-tool inventory does not include `create_branch` / `create_or_update_file`).
- MR creation via the official `https://gitlab.com/api/v4/mcp` endpoint's
  `create_merge_request` tool — preserves judging credit per partner doc.

The MR description is the same Markdown S6.5 emits to GCS (via
`patcher._markdown_renderer.render_recipe`), so a reviewer sees the same
human-readable artifact in both surfaces.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from chaoslab_agent.config import get_settings
from chaoslab_agent.patcher._gitlab_mcp_client import (
    OFFICIAL_ENDPOINT,
    GitLabMcpClient,
    GitLabMcpError,
)
from chaoslab_agent.patcher._gitlab_rest_client import (
    GitLabRestClient,
    GitLabRestClientError,
)
from chaoslab_agent.patcher._markdown_renderer import render_recipe
from chaoslab_agent.patcher.recipe import HardeningRecipe

logger = logging.getLogger(__name__)

_MR_URL_PATTERN = re.compile(r"^https://gitlab\.com/.+/-/merge_requests/\d+$")


class GitLabEmitterError(RuntimeError):
    """Raised when MR emission fails — wraps REST + MCP errors with context."""


class GitLabEmitResult(BaseModel):
    """Outcome of emitting a HardeningRecipe as a GitLab MR.

    Frozen + validator-locked so the receipt-card surface can't silently
    accept a URL that doesn't actually point at a real GitLab.com MR.
    """

    model_config = ConfigDict(frozen=True)

    mr_url: str = Field(min_length=1)
    mr_iid: int = Field(ge=1)
    branch_name: str = Field(pattern=r"^chaoslab/recipe-[a-z0-9]{12}$")
    commit_count: int = Field(ge=1)
    recipe_id: str

    @field_validator("mr_url")
    @classmethod
    def _mr_url_is_https_gitlab_mr(cls, value: str) -> str:
        # Plain str (HttpUrl is too loose — it would accept http://gitlab.com
        # and example.com). The pattern enforces https + gitlab.com + the
        # `/-/merge_requests/<int>` tail that judges click on.
        if not value.startswith("https://"):
            msg = f"mr_url must be https:// (got {value[:32]}...)"
            raise ValueError(msg)
        if not _MR_URL_PATTERN.match(value):
            msg = (
                "mr_url must match https://gitlab.com/.../-/merge_requests/<id> "
                f"(got {value[:64]}...)"
            )
            raise ValueError(msg)
        return value


class GitLabMREmitter:
    """Orchestrates render → branch → commit files → open MR.

    The REST client + MCP client are constructor-injected so unit tests stub
    them without touching gitlab.com. Production callers pass `None` and the
    emitter builds defaults from `Settings`.
    """

    def __init__(
        self,
        rest_client: GitLabRestClient | None = None,
        mcp_client: GitLabMcpClient | None = None,
    ) -> None:
        settings = get_settings()
        if settings.GITLAB_MCP_ENDPOINT != OFFICIAL_ENDPOINT:
            msg = (
                f"ADR-011 violated: GITLAB_MCP_ENDPOINT must be {OFFICIAL_ENDPOINT!r} "
                f"(got {settings.GITLAB_MCP_ENDPOINT!r})"
            )
            raise GitLabEmitterError(msg)
        self._rest_client = rest_client
        self._mcp_client = mcp_client or GitLabMcpClient(
            endpoint=settings.GITLAB_MCP_ENDPOINT,
            token=(settings.gitlab_token.get_secret_value() if settings.gitlab_token else None),
        )
        self._default_branch = settings.GITLAB_DEFAULT_BRANCH

    async def emit(self, recipe: HardeningRecipe, project_id: str) -> GitLabEmitResult:
        branch_name = self._branch_name(recipe.recipe_id)
        files = self._build_file_list(recipe)
        description = self._build_mr_description(recipe)
        commit_message = f"feat(chaoslab): hardening recipe {recipe.recipe_id}"

        rest = self._get_rest_client(project_id)
        # python-gitlab is sync; offload so the orchestrator event loop stays
        # responsive (esp. matters during the demo's parallel /run + /stream).
        try:
            await asyncio.to_thread(rest.create_branch, branch_name, self._default_branch)
            await asyncio.to_thread(
                rest.create_commit_with_files, branch_name, commit_message, files
            )
        except GitLabRestClientError as exc:
            msg = f"GitLab branch/commit failed: {exc}"
            raise GitLabEmitterError(msg) from exc

        try:
            mr = await self._mcp_client.create_merge_request(
                project_id=project_id,
                source_branch=branch_name,
                target_branch=self._default_branch,
                title=f"ChaosLab Hardening Recipe — {recipe.recipe_id}",
                description=description,
                labels=["chaoslab", "hardening-recipe"],
            )
        except GitLabMcpError as exc:
            # Translate auth failures with a marker the receipt-card surface
            # can grep ("authentication") — the bare MCP error message stays in
            # __cause__ for the on-call engineer.
            if "401" in str(exc) or "authentication" in str(exc).lower():
                msg = f"GitLab MR authentication failed: {exc}"
                raise GitLabEmitterError(msg) from exc
            msg = f"GitLab MR creation failed: {exc}"
            raise GitLabEmitterError(msg) from exc

        mr_url = self._extract_mr_field(mr, "web_url")
        mr_iid_raw = self._extract_mr_field(mr, "iid")
        try:
            mr_iid = int(mr_iid_raw)
        except (TypeError, ValueError) as exc:
            msg = f"GitLab MR returned non-integer iid: {mr_iid_raw!r}"
            raise GitLabEmitterError(msg) from exc

        logger.info(
            "gitlab_mr_emitted recipe_id=%s branch=%s mr_iid=%d mr_url=%s files=%d",
            recipe.recipe_id,
            branch_name,
            mr_iid,
            mr_url,
            len(files),
        )

        return GitLabEmitResult(
            mr_url=mr_url,
            mr_iid=mr_iid,
            branch_name=branch_name,
            commit_count=len(files),
            recipe_id=recipe.recipe_id,
        )

    def _branch_name(self, recipe_id: str) -> str:
        # recipe_id format: "recipe_" + 12 hex chars (enforced by HardeningRecipe).
        # Strip the prefix so we get `chaoslab/recipe-abc123def456` not
        # `chaoslab/recipe-recipe_abc123def456`.
        return f"chaoslab/recipe-{recipe_id.removeprefix('recipe_')}"

    def _build_file_list(self, recipe: HardeningRecipe) -> list[tuple[str, str]]:
        """Layout of files committed to the MR branch.

        Same paths the spec promises in partner-gitlab.md "show real DevOps
        automation value" — gives reviewers TYPED artifacts (Markdown for
        humans, .diff for git-apply, .json for Phoenix datasets) instead of
        a single opaque blob.
        """
        files: list[tuple[str, str]] = []
        files.append((f"chaoslab/patches/{recipe.recipe_id}.md", render_recipe(recipe)))
        for i, diff in enumerate(recipe.tool_validation_diffs):
            # Slashes in tool_name would create unintended folders. Replace.
            safe_tool = diff.tool_name.replace("/", "_")
            files.append(
                (
                    f"chaoslab/patches/diffs/{recipe.recipe_id}_{i}_{safe_tool}.diff",
                    diff.code_patch,
                )
            )
        if recipe.regression_test_cases:
            payload = [tc.model_dump(mode="json") for tc in recipe.regression_test_cases]
            files.append(
                (
                    f"chaoslab/regression_tests/{recipe.recipe_id}.json",
                    json.dumps(payload, indent=2, sort_keys=True),
                )
            )
        return files

    def _build_mr_description(self, recipe: HardeningRecipe) -> str:
        # Headers first (so the reviewer sees the metadata before the
        # rendered Markdown body), then the same render_recipe output S6.5
        # uploads to GCS — single source of truth for the Markdown artifact.
        return (
            "# ChaosLab Hardening Recipe\n\n"
            f"**Recipe ID:** `{recipe.recipe_id}`\n"
            f"**Target agent:** `{recipe.target_agent_id}`\n"
            f"**Estimated resilience improvement:** "
            f"{recipe.estimated_resilience_improvement * 100:.1f}%\n\n"
            "---\n\n" + render_recipe(recipe)
        )

    @staticmethod
    def _extract_mr_field(mr: dict[str, Any], key: str) -> str:
        """Pull `key` from the MCP response, supporting two known envelope shapes."""
        if key in mr:
            return str(mr[key])
        content = mr.get("content")
        if isinstance(content, list) and content:
            first = content[0]
            if isinstance(first, dict):
                inner = first.get("json") or {}
                if isinstance(inner, dict) and key in inner:
                    return str(inner[key])
        msg = f"GitLab MR response missing required field {key!r}: keys={list(mr.keys())}"
        raise GitLabEmitterError(msg)

    def _get_rest_client(self, project_id: str) -> GitLabRestClient:
        if self._rest_client is not None:
            return self._rest_client
        settings = get_settings()
        if settings.gitlab_token is None:
            msg = "GITLAB_TOKEN must be set in Settings for REST branch + commit operations"
            raise GitLabEmitterError(msg)
        from chaoslab_agent.patcher._gitlab_rest_client import build_default_client

        return build_default_client(
            project_id=project_id, token=settings.gitlab_token.get_secret_value()
        )


__all__ = [
    "GitLabEmitResult",
    "GitLabEmitterError",
    "GitLabMREmitter",
]
