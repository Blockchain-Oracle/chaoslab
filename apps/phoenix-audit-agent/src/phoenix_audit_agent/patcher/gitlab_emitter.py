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

from phoenix_audit_agent.config import get_settings
from phoenix_audit_agent.errors import PhoenixAuditError
from phoenix_audit_agent.patcher._gitlab_mcp_client import (
    OFFICIAL_ENDPOINT,
    GitLabMcpClient,
    GitLabMcpError,
)
from phoenix_audit_agent.patcher._gitlab_rest_client import (
    GitLabRestClient,
    GitLabRestClientError,
    build_default_client,
)
from phoenix_audit_agent.patcher._markdown_renderer import render_recipe
from phoenix_audit_agent.patcher.recipe import HardeningRecipe

logger = logging.getLogger(__name__)

_MR_URL_PATTERN = re.compile(r"^https://gitlab\.com/.+/-/merge_requests/\d+$")


class GitLabEmitterError(PhoenixAuditError, RuntimeError):
    """Raised when MR emission fails — wraps REST + MCP errors with context.

    Round-3: `rollback_failed=True` signals that the orphan-branch rollback
    itself failed AFTER the original MR-creation failure. The receipt-card
    surface uses this to render "manual cleanup needed at .../-/branches/<x>"
    instead of "MR creation failed" alone.
    """

    def __init__(self, *args: object, rollback_failed: bool = False) -> None:
        super().__init__(*args)
        self.rollback_failed = rollback_failed


class GitLabEmitResult(BaseModel):
    """Outcome of emitting a HardeningRecipe as a GitLab MR.

    Frozen + validator-locked so the receipt-card surface can't silently
    accept a URL that doesn't actually point at a real GitLab.com MR.
    """

    model_config = ConfigDict(frozen=True)

    mr_url: str = Field(min_length=1)
    mr_iid: int = Field(ge=1)
    branch_name: str = Field(pattern=r"^phoenix-audit/recipe-[a-z0-9]{12}$")
    commit_count: int = Field(ge=1)
    recipe_id: str

    @field_validator("mr_url")
    @classmethod
    def _mr_url_is_https_gitlab_mr(cls, value: str) -> str:
        # Single pattern is load-bearing — the regex starts with `^https://gitlab\.com/`
        # so the prefix is enforced as a side effect. A separate `startswith` check
        # would just duplicate that constraint.
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
        oauth_token: str | None = None,
    ) -> None:
        settings = get_settings()
        if settings.GITLAB_MCP_ENDPOINT != OFFICIAL_ENDPOINT:
            msg = (
                f"ADR-011 violated: GITLAB_MCP_ENDPOINT must be {OFFICIAL_ENDPOINT!r} "
                f"(got {settings.GITLAB_MCP_ENDPOINT!r})"
            )
            raise GitLabEmitterError(msg)
        # Story-9.17: when set, BOTH halves (REST branch+files, MCP MR) run
        # as the USER — never mixed identities, never a service-token
        # fallback (filing as the wrong identity is worse than failing).
        # The official MCP endpoint is OAuth-only (PAT support is an open
        # GitLab issue, #586184) — the user OAuth bearer is the DOCUMENTED
        # credential here, verified 2026-06-11 (PR #112 M-2).
        self._oauth_token = oauth_token
        self._rest_client = rest_client
        self._mcp_client = mcp_client or GitLabMcpClient(
            endpoint=settings.GITLAB_MCP_ENDPOINT,
            token=(
                oauth_token
                if oauth_token is not None
                else (settings.gitlab_token.get_secret_value() if settings.gitlab_token else None)
            ),
        )
        self._default_branch = settings.GITLAB_DEFAULT_BRANCH

    async def emit(self, recipe: HardeningRecipe, project_id: str) -> GitLabEmitResult:
        branch_name = self._branch_name(recipe.recipe_id)
        files = self._build_file_list(recipe)
        description = self._build_mr_description(recipe)
        commit_message = f"feat(phoenix-audit): hardening recipe {recipe.recipe_id}"

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
                title=f"PhoenixAudit Hardening Recipe — {recipe.recipe_id}",
                description=description,
                labels=["phoenix-audit", "hardening-recipe"],
            )
        except GitLabMcpError as exc:
            # The REST half already landed branch+commit on GitLab. If we
            # don't roll back, retries hit `Branch already exists` (422) on
            # the next attempt and the user is stuck in a half-applied state.
            # Best-effort delete — log failure but preserve the original cause
            # so the operator sees what actually broke. The branch_name is
            # included in the user-facing message so manual cleanup is
            # possible at gitlab.com/.../-/branches/<branch_name>.
            rollback_failed = self._rollback_branch_best_effort(rest, branch_name)
            # Round-3: `exc.auth_failed` flag replaces fragile substring match
            # ("401" in body would have false-positive'd on unrelated errors).
            if exc.auth_failed:
                msg = f"GitLab MR authentication failed (branch={branch_name}): {exc}"
                raise GitLabEmitterError(msg, rollback_failed=rollback_failed) from exc
            msg = f"GitLab MR creation failed (branch={branch_name}): {exc}"
            raise GitLabEmitterError(msg, rollback_failed=rollback_failed) from exc

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
        # Strip the prefix so we get `phoenix-audit/recipe-abc123def456` not
        # `phoenix-audit/recipe-recipe_abc123def456`.
        return f"phoenix-audit/recipe-{recipe_id.removeprefix('recipe_')}"

    def _build_file_list(self, recipe: HardeningRecipe) -> list[tuple[str, str]]:
        """Layout of files committed to the MR branch.

        Same paths the spec promises in partner-gitlab.md "show real DevOps
        automation value" — gives reviewers TYPED artifacts (Markdown for
        humans, .diff for git-apply, .json for Phoenix datasets) instead of
        a single opaque blob.
        """
        files: list[tuple[str, str]] = []
        files.append((f"phoenix-audit/patches/{recipe.recipe_id}.md", render_recipe(recipe)))
        for i, diff in enumerate(recipe.tool_validation_diffs):
            # Slashes in tool_name would create unintended folders. Replace.
            safe_tool = diff.tool_name.replace("/", "_")
            files.append(
                (
                    f"phoenix-audit/patches/diffs/{recipe.recipe_id}_{i}_{safe_tool}.diff",
                    diff.code_patch,
                )
            )
        if recipe.regression_test_cases:
            payload = [tc.model_dump(mode="json") for tc in recipe.regression_test_cases]
            files.append(
                (
                    f"phoenix-audit/regression_tests/{recipe.recipe_id}.json",
                    json.dumps(payload, indent=2, sort_keys=True),
                )
            )
        return files

    def _build_mr_description(self, recipe: HardeningRecipe) -> str:
        # Headers first (so the reviewer sees the metadata before the
        # rendered Markdown body), then the same render_recipe output S6.5
        # uploads to GCS — single source of truth for the Markdown artifact.
        # HardeningRecipe.target_agent_id only enforces min_length=1, so a
        # backtick inside would break the inline code-span and degrade the
        # regulator-readable artifact. Strip + WARNING log so bad upstream
        # data is observable rather than silently corrupting the MR.
        safe_agent_id = self._sanitize_code_span(recipe.target_agent_id, "target_agent_id")
        safe_recipe_id = self._sanitize_code_span(recipe.recipe_id, "recipe_id")
        return (
            "# PhoenixAudit Hardening Recipe\n\n"
            f"**Recipe ID:** `{safe_recipe_id}`\n"
            f"**Target agent:** `{safe_agent_id}`\n"
            f"**Estimated resilience improvement:** "
            f"{recipe.estimated_resilience_improvement * 100:.1f}%\n\n"
            "---\n\n" + render_recipe(recipe)
        )

    @staticmethod
    def _sanitize_code_span(value: str, field_name: str) -> str:
        """Strip backticks from `value` so an inline Markdown code-span stays intact.

        Logs WARNING on substitution so an upstream model emitting Markdown
        control chars surfaces in Cloud Logging instead of silently degrading
        the regulator-facing MR description.
        """
        if "`" in value:
            logger.warning(
                "mr_description_sanitized field=%s original=%r — backticks stripped",
                field_name,
                value,
            )
            return value.replace("`", "")
        return value

    @staticmethod
    def _extract_mr_field(mr: dict[str, Any], key: str) -> str:
        """Pull `key` from the MCP response, supporting both known envelope shapes.

        Some MCP servers return the tool result top-level (`{"iid": 42, ...}`);
        others wrap it in the `content` list shape per MCP spec
        (`{"content": [{"type": "json", "json": {"iid": 42, ...}}]}`). Tested
        against both shapes; envelope-path usage is WARNING-logged so a
        production drift to the envelope shape is observable instead of silent.
        """
        # Top-level — but an explicit null on the field IS a server bug (returning
        # the string "None" would then fail mr_url validation with a confusing
        # "must match pattern" error instead of surfacing the actual issue).
        if key in mr and mr[key] is not None:
            return str(mr[key])
        content = mr.get("content")
        if isinstance(content, list) and content:
            first = content[0]
            if isinstance(first, dict):
                inner = first.get("json") or {}
                if isinstance(inner, dict) and inner.get(key) is not None:
                    logger.warning(
                        "mcp_envelope_fallback_used key=%s — MCP returned `content[0].json` "
                        "shape; consider verifying server version",
                        key,
                    )
                    return str(inner[key])
        msg = (
            f"GitLab MR response missing required field {key!r} "
            f"(or value was null): keys={list(mr.keys())}"
        )
        raise GitLabEmitterError(msg)

    @staticmethod
    def _rollback_branch_best_effort(rest: GitLabRestClient, branch_name: str) -> bool:
        """Delete a branch after MR creation failed. Returns True iff rollback failed.

        Best-effort: if rollback itself fails (network, IAM gap, etc.), we still
        want to propagate the ORIGINAL MR-creation error. The return value
        signals rollback state to the caller so it can attach `rollback_failed`
        to the raised GitLabEmitterError — receipt-card surface uses this to
        render "manual cleanup needed" instead of "MR creation failed" alone.
        """
        try:
            rest.delete_branch(branch_name)
            logger.info("orphan_branch_rolled_back branch=%s", branch_name)
        except Exception:
            logger.exception("orphan_branch_rollback_failed branch=%s", branch_name)
            return True
        return False

    def _get_rest_client(self, project_id: str) -> GitLabRestClient:
        if self._rest_client is not None:
            return self._rest_client
        if self._oauth_token is not None:
            return build_default_client(project_id=project_id, token=self._oauth_token, oauth=True)
        settings = get_settings()
        if settings.gitlab_token is None:
            msg = "GITLAB_TOKEN must be set in Settings for REST branch + commit operations"
            raise GitLabEmitterError(msg)
        # build_default_client is hoisted to module-top — round-3 reviewer
        # flagged the lazy import on the hot path (every audit run).
        return build_default_client(
            project_id=project_id, token=settings.gitlab_token.get_secret_value()
        )


__all__ = [
    "GitLabEmitResult",
    "GitLabEmitterError",
    "GitLabMREmitter",
]
