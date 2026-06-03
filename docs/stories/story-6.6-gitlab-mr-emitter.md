# Story — GitLab MR Emitter (Hybrid: python-gitlab SDK + Official MCP for MR creation)

**ID:** story-6.6-gitlab-mr-emitter
**Epic:** Epic 6 — Judge + clustering + hardening recipe
**Depends on:** story-6.4-patcher-sub-agent (consumes `HardeningRecipe`)
**Estimate:** ~2h
**Status:** PENDING
**tags:** [backend, p0, patcher]

---

## ⚠ AMENDED 2026-06-03 per audit A1 (`spec-audit/04-gitlab-mcp-audit.md`)

**Critical correction: the official `https://gitlab.com/api/v4/mcp` endpoint exposes only 16 tools and `create_branch` + `create_or_update_file` are NOT among them.** The original story plan (full MCP-only flow) would hit "unknown tool" errors at runtime.

**Hybrid approach (ADR-011 amended in `docs/architecture.md`):**

1. **Branch creation** → use `python-gitlab` SDK (already in deps at `docs/architecture.md` library table):
   ```python
   import gitlab
   gl = gitlab.Gitlab("https://gitlab.com", private_token=GITLAB_TOKEN)
   project = gl.projects.get(project_id)
   project.branches.create({"branch": f"chaoslab/recipe-{recipe_id}", "ref": "main"})
   ```
2. **File commits** → use `python-gitlab` SDK's commits API for atomic multi-file commits:
   ```python
   project.commits.create({
       "branch": f"chaoslab/recipe-{recipe_id}",
       "commit_message": f"chaoslab: hardening recipe {recipe_id}",
       "actions": [
           {"action": "create", "file_path": "chaoslab-recipes/<recipe_id>/recipe.md",  "content": recipe_md},
           {"action": "create", "file_path": "chaoslab-recipes/<recipe_id>/diff.patch", "content": tool_diff},
           # ... per-diff entries
       ],
   })
   ```
3. **MR creation** → use the **official `https://gitlab.com/api/v4/mcp`** endpoint's `create_merge_request` tool. **This is the call that earns the official-MCP judging credit.** Verified to exist in the 16-tool inventory (`spec-audit/04 §4`).
4. **`_gitlab_mcp_client.py` is now ~80 LOC** (only wraps `create_merge_request` + the MCP handshake), not ~250 LOC. The expanded REST-API client logic lives in `_gitlab_rest_client.py` (NEW, ~150 LOC) which is a thin wrapper around the `python-gitlab` package.

**Amended file modification map (replaces the original below):**

- `apps/chaoslab-agent/src/chaoslab_agent/patcher/gitlab_emitter.py` — NEW — `GitLabMREmitter` orchestrates: REST for branch+files, MCP for MR. ≤300 LOC.
- `apps/chaoslab-agent/src/chaoslab_agent/patcher/_gitlab_rest_client.py` — NEW — thin `python-gitlab` wrapper for branch + commit ops. ≤150 LOC.
- `apps/chaoslab-agent/src/chaoslab_agent/patcher/_gitlab_mcp_client.py` — NEW — MCP client for ONLY `create_merge_request`. ≤80 LOC.
- `apps/chaoslab-agent/src/chaoslab_agent/patcher/__init__.py` — UPDATE — append `GitLabMREmitter, GitLabEmitResult` re-exports
- `apps/chaoslab-agent/src/chaoslab_agent/config.py` — UPDATE — `GITLAB_MCP_ENDPOINT: str = "https://gitlab.com/api/v4/mcp"`, `GITLAB_TOKEN: SecretStr | None = None`, `GITLAB_DEFAULT_BRANCH: str = "main"`
- `apps/chaoslab-agent/tests/unit/patcher/test_gitlab_emitter.py` — NEW — ≥8 unit tests. `respx` for the MCP endpoint, `pytest-mock` for `python-gitlab` to mock `gl.projects.get(...)`. Asserts the SPLIT correctly: branch+files via REST, MR via MCP `create_merge_request`.
- `apps/chaoslab-agent/tests/integration/test_gitlab_emitter_online.py` — NEW — ≥3 `@pytest.mark.online` tests against a real GitLab.com trial project.

**Day-1 verification step (added to RAT-runbook + S1.4 secret-manager-setup.sh):**

- Spin up a fresh GitLab.com trial account, mint a PAT with `api` scope, store as `gitlab-token` in Secret Manager
- Test the MCP `initialize` handshake against `https://gitlab.com/api/v4/mcp` with Bearer auth
- If trial-tier access fails (official docs say Premium/Ultimate required; hackathon FAQ disagreed), fall back to all-`python-gitlab` mode and lose the official-MCP judging credit but keep the demo working

**Amended BDD additions** (add to the existing BDD section in the original story below):

```
Given the GitLabMREmitter's emit() runs end-to-end
When the orchestration completes
Then exactly 1 HTTP request hit https://gitlab.com/api/v4/mcp (for create_merge_request)
And ≥2 HTTP requests hit https://gitlab.com/api/v4/projects/.../repository/* (for branches + commits via python-gitlab)
And the returned `mr_url` matches r"^https://gitlab\.com/.+/-/merge_requests/\d+$"

Given a community MCP server URL appears in any source file (e.g., zereight/gitlab-mcp)
When `grep -rE "zereight|mcpland|wadew" apps/chaoslab-agent/src/` runs
Then output is empty (exit 0 with no results — community MCPs are BANNED)
```

**Original story content below — coding agent: the MCP tool inventory `create_branch` / `create_or_update_file` references in the original ARE WRONG; use python-gitlab SDK for those. ONLY `create_merge_request` goes via MCP.**

---

---

## User story

**As a** ChaosLab Receipt card that needs to show "MR #42 opened on GitLab" (per `PRD.md` §3 demo step 6) — AND as a hackathon submission that must claim full GitLab-track partner credit (per `partner-gitlab.md` "Use of GitLab's OFFICIAL MCP server is noted in evaluation")
**I want to** call `GitLabMREmitter.emit(recipe, project_id="user/repo")` which (a) creates a branch `chaoslab/recipe-<id>`, (b) commits the prompt patch + tool validation diff + regression test files, (c) opens a real Merge Request via the **official** `https://gitlab.com/api/v4/mcp` endpoint with the recipe rendered as the MR description, and (d) returns `{mr_url, mr_iid, branch_name}`
**So that** the demo's Receipt card displays a live, clickable GitLab MR URL judges can open, the submission earns full partner-credit (NOT a community MCP wrapper — explicit per `partner-gitlab.md` "lose points" warning), and the closed loop (per `PRD.md` §3) ends with a tangible code change on a real platform, not just a Markdown blob

---

## File modification map

Exact files the coding agent creates or modifies for this story:

- `apps/chaoslab-agent/src/chaoslab_agent/patcher/gitlab_emitter.py` — NEW — `GitLabMREmitter` class with `async emit(recipe, project_id) -> GitLabEmitResult`. ≤300 LOC.
- `apps/chaoslab-agent/src/chaoslab_agent/patcher/_gitlab_mcp_client.py` — NEW — async wrapper over the official GitLab MCP HTTP endpoint at `https://gitlab.com/api/v4/mcp`. Exposes `create_branch`, `create_or_update_file`, `create_merge_request` (official tool names per `partner-gitlab.md`). ≤250 LOC.
- `apps/chaoslab-agent/src/chaoslab_agent/patcher/__init__.py` — UPDATE — append `GitLabMREmitter, GitLabEmitResult` re-exports
- `apps/chaoslab-agent/src/chaoslab_agent/config.py` — UPDATE — append `GITLAB_MCP_ENDPOINT: str = "https://gitlab.com/api/v4/mcp"` (constant — NEVER override to a community URL), `GITLAB_TOKEN: SecretStr | None = None` (Secret Manager at runtime), `GITLAB_DEFAULT_BRANCH: str = "main"`
- `apps/chaoslab-agent/tests/unit/patcher/test_gitlab_emitter.py` — NEW — ≥8 unit tests with `respx` intercepting the MCP endpoint. Asserts correct MCP tool names called, branch name format, MR description contains recipe Markdown.
- `apps/chaoslab-agent/tests/integration/test_gitlab_emitter_online.py` — NEW — ≥3 integration tests marked `@pytest.mark.online`. Runs against a real GitLab.com test project via `GITLAB_TEST_PROJECT_ID` env var. CI skips by default.

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given apps/chaoslab-agent/src/chaoslab_agent/patcher/gitlab_emitter.py exists
When  `uv run python -c "from chaoslab_agent.patcher.gitlab_emitter import GitLabMREmitter, GitLabEmitResult; print('ok')"` runs
Then  stdout contains "ok" and exit code is 0

Given the config's GITLAB_MCP_ENDPOINT
When  `uv run python -c "from chaoslab_agent.config import get_settings; print(get_settings().GITLAB_MCP_ENDPOINT)"` runs
Then  stdout is exactly "https://gitlab.com/api/v4/mcp"
(per ADR-011 + partner-gitlab.md — official endpoint only)

Given `grep -rE "(zereight/gitlab-mcp|mcpland/gitlab-mcp|wadew/gitlab-mcp)" apps/chaoslab-agent/src/` runs
When  output is checked
Then  zero results appear (community MCP servers are BANNED per partner-gitlab.md)

Given a HardeningRecipe with recipe_id="recipe_abc123def456" and a GitLab project_id="user/repo"
When  `await GitLabMREmitter().emit(recipe, project_id="user/repo")` runs (with respx mocking the MCP endpoint)
Then  the respx history shows POST to "https://gitlab.com/api/v4/mcp" with tool name "create_merge_request"
And   the request body includes source_branch == "chaoslab/recipe-abc123def456"
And   the request body includes target_branch == "main"
And   the request body's MR description contains "recipe_abc123def456"

Given the emitter receives a recipe with 2 prompt_patches and 1 tool_validation_diff
When  emit runs
Then  the respx history shows at least 1 file-creation MCP call per patch + diff
And   one of the file paths is "chaoslab/patches/recipe_abc123def456.md"
And   one of the file paths includes "regression_tests/" prefix

Given the integration test runs against a real GitLab project_id="abu-chaoslab/test-target" with GITLAB_TOKEN set
When  emit completes
Then  result.mr_url matches r"^https://gitlab\.com/abu-chaoslab/test-target/-/merge_requests/\d+$"
And   result.mr_iid > 0
And   result.branch_name == "chaoslab/recipe-<recipe_id_suffix>"
And   the branch is reachable via `gh api projects/{quoted_project_id}/repository/branches/{branch_name}` (returns 200)

Given an invalid GitLab token (401)
When  emit runs
Then  GitLabEmitterError is raised with "authentication" in the message
(not a bare httpx.HTTPStatusError — wrap and add context)

Given the GitLab MCP endpoint returns 5xx (retryable)
When  emit runs
Then  the request is retried up to 3 times with exponential backoff (verified via respx call count)

Given `uv run pytest apps/chaoslab-agent/tests/unit/patcher/test_gitlab_emitter.py -v` runs
When  the test suite completes
Then  ≥8 behavioral unit tests pass

Given `uv run pytest apps/chaoslab-agent/tests/integration/test_gitlab_emitter_online.py -v -m online` runs (with GITLAB_TOKEN + GITLAB_TEST_PROJECT_ID set)
When  the test suite completes
Then  ≥3 integration tests pass

Given the gitlab_emitter.py and _gitlab_mcp_client.py source files
When  `python3 scripts/check_max_lines.py apps/chaoslab-agent/src/chaoslab_agent/patcher/gitlab_emitter.py apps/chaoslab-agent/src/chaoslab_agent/patcher/_gitlab_mcp_client.py` runs
Then  exit code is 0 (gitlab_emitter.py ≤300 LOC, _gitlab_mcp_client.py ≤250 LOC per task)

Given `grep -rE "(mock|fake|dummy|hardcoded|simulated)" apps/chaoslab-agent/src/chaoslab_agent/patcher/gitlab_emitter.py apps/chaoslab-agent/src/chaoslab_agent/patcher/_gitlab_mcp_client.py` runs
When  output is checked
Then  zero results appear (§14 gate clean)

Given `grep -E "gitlab\.com/api/v4/mcp" apps/chaoslab-agent/src/chaoslab_agent/patcher/_gitlab_mcp_client.py` runs
When  output is checked
Then  at least 1 match found (official endpoint hardcoded as default — ADR-011)
```

---

## Shell verification

```bash
set -e
cd /Users/abu/dev/hackathon/rapid-agents

# Files exist
test -f apps/chaoslab-agent/src/chaoslab_agent/patcher/gitlab_emitter.py
test -f apps/chaoslab-agent/src/chaoslab_agent/patcher/_gitlab_mcp_client.py
test -f apps/chaoslab-agent/tests/unit/patcher/test_gitlab_emitter.py
test -f apps/chaoslab-agent/tests/integration/test_gitlab_emitter_online.py

# Imports resolve
uv run python -c "from chaoslab_agent.patcher.gitlab_emitter import GitLabMREmitter, GitLabEmitResult, GitLabEmitterError; print('ok')"

# Official endpoint enforced
ENDPOINT=$(uv run python -c "from chaoslab_agent.config import get_settings; print(get_settings().GITLAB_MCP_ENDPOINT)")
[ "$ENDPOINT" = "https://gitlab.com/api/v4/mcp" ] || { echo "ADR-011 violation: GITLAB_MCP_ENDPOINT=$ENDPOINT"; exit 1; }

# Community MCP servers banned
! grep -rE "(zereight/gitlab-mcp|mcpland/gitlab-mcp|wadew/gitlab-mcp)" apps/chaoslab-agent/src/

# Official endpoint hardcoded as default
grep -qE "gitlab\.com/api/v4/mcp" apps/chaoslab-agent/src/chaoslab_agent/patcher/_gitlab_mcp_client.py

# Unit tests (with respx — no network needed)
cd apps/chaoslab-agent && uv run pytest tests/unit/patcher/test_gitlab_emitter.py -v 2>&1 | tee /tmp/gitlab-emitter-test.log && cd -
PASS_COUNT=$(grep -E "PASSED" /tmp/gitlab-emitter-test.log | wc -l | tr -d ' ')
[ "$PASS_COUNT" -ge 8 ] || { echo "expected ≥8 unit tests, got $PASS_COUNT"; exit 1; }

# Integration tests (online — only if GITLAB_TOKEN + GITLAB_TEST_PROJECT_ID set)
if [ -n "$GITLAB_TOKEN" ] && [ -n "$GITLAB_TEST_PROJECT_ID" ]; then
  cd apps/chaoslab-agent && uv run pytest tests/integration/test_gitlab_emitter_online.py -v -m online 2>&1 | tee /tmp/gitlab-emitter-int-test.log && cd -
  INT_PASS=$(grep -E "PASSED" /tmp/gitlab-emitter-int-test.log | wc -l | tr -d ' ')
  [ "$INT_PASS" -ge 3 ] || { echo "expected ≥3 integration tests, got $INT_PASS"; exit 1; }
else
  echo "[skip] integration tests — set GITLAB_TOKEN + GITLAB_TEST_PROJECT_ID to run"
fi

# Lint + type-check + per-task LOC ceilings
uv run ruff check apps/chaoslab-agent/src/chaoslab_agent/patcher/gitlab_emitter.py apps/chaoslab-agent/src/chaoslab_agent/patcher/_gitlab_mcp_client.py
uv run ruff format --check apps/chaoslab-agent/src/chaoslab_agent/patcher/gitlab_emitter.py apps/chaoslab-agent/src/chaoslab_agent/patcher/_gitlab_mcp_client.py
uv run ty check apps/chaoslab-agent/src/chaoslab_agent/patcher/ || uv run mypy --strict apps/chaoslab-agent/src/chaoslab_agent/patcher/
python3 scripts/check_max_lines.py --strict apps/chaoslab-agent/src/chaoslab_agent/patcher/

LOC_EMITTER=$(wc -l < apps/chaoslab-agent/src/chaoslab_agent/patcher/gitlab_emitter.py | tr -d ' ')
[ "$LOC_EMITTER" -le 300 ] || { echo "gitlab_emitter.py has $LOC_EMITTER lines, exceeds 300 LOC ceiling"; exit 1; }
LOC_CLIENT=$(wc -l < apps/chaoslab-agent/src/chaoslab_agent/patcher/_gitlab_mcp_client.py | tr -d ' ')
[ "$LOC_CLIENT" -le 250 ] || { echo "_gitlab_mcp_client.py has $LOC_CLIENT lines, exceeds 250 LOC ceiling"; exit 1; }

# §14 clean
! grep -rE "(mock|fake|dummy|hardcoded|simulated)" apps/chaoslab-agent/src/chaoslab_agent/patcher/gitlab_emitter.py apps/chaoslab-agent/src/chaoslab_agent/patcher/_gitlab_mcp_client.py

echo "story-6.6 verification: PASS"
```

---

## Notes for coding agent

### `GitLabEmitResult` + `GitLabMREmitter` class shape

```python
# apps/chaoslab-agent/src/chaoslab_agent/patcher/gitlab_emitter.py
from __future__ import annotations

import structlog
from pydantic import BaseModel, Field, HttpUrl

from chaoslab_agent.config import get_settings
from chaoslab_agent.patcher._gitlab_mcp_client import GitLabMcpClient
from chaoslab_agent.patcher._markdown_renderer import render_recipe
from chaoslab_agent.patcher.recipe import HardeningRecipe

log = structlog.get_logger(__name__)


class GitLabEmitterError(Exception):
    """Raised when MR creation fails non-recoverably."""


class GitLabEmitResult(BaseModel):
    mr_url: HttpUrl
    mr_iid: int = Field(ge=1)
    branch_name: str = Field(pattern=r"^chaoslab/recipe-[a-z0-9]{12}$")
    commit_count: int = Field(ge=1)
    recipe_id: str


class GitLabMREmitter:
    """Emits a HardeningRecipe as a GitLab Merge Request via the OFFICIAL MCP endpoint.

    Per ADR-011 + partner-gitlab.md: uses `https://gitlab.com/api/v4/mcp` exclusively.
    Community MCP servers (zereight, mcpland, wadew) are explicitly banned.
    """

    def __init__(self, mcp_client: GitLabMcpClient | None = None) -> None:
        settings = get_settings()
        assert settings.GITLAB_MCP_ENDPOINT == "https://gitlab.com/api/v4/mcp", \
            "ADR-011 violated: only the official GitLab MCP endpoint is permitted"  # noqa: S101
        self._client = mcp_client or GitLabMcpClient(
            endpoint=settings.GITLAB_MCP_ENDPOINT,
            token=settings.GITLAB_TOKEN.get_secret_value() if settings.GITLAB_TOKEN else None,
        )
        self._default_branch = settings.GITLAB_DEFAULT_BRANCH

    async def emit(self, recipe: HardeningRecipe, project_id: str) -> GitLabEmitResult:
        branch_name = f"chaoslab/recipe-{recipe.recipe_id.removeprefix('recipe_')}"
        files_to_commit = self._build_file_list(recipe)
        mr_description = self._build_mr_description(recipe)
        commit_message = f"feat(chaoslab): hardening recipe {recipe.recipe_id}"

        try:
            await self._client.create_branch(
                project_id=project_id, branch=branch_name, ref=self._default_branch
            )
            for file_path, content in files_to_commit:
                await self._client.create_or_update_file(
                    project_id=project_id,
                    branch=branch_name,
                    file_path=file_path,
                    content=content,
                    commit_message=commit_message,
                )
            mr = await self._client.create_merge_request(
                project_id=project_id,
                source_branch=branch_name,
                target_branch=self._default_branch,
                title=f"ChaosLab Hardening Recipe — {recipe.recipe_id}",
                description=mr_description,
                labels=["chaoslab", "hardening-recipe"],
            )
        except Exception as e:
            raise GitLabEmitterError(f"GitLab MR creation failed: {e}") from e

        log.info(
            "gitlab_mr_emitted",
            recipe_id=recipe.recipe_id,
            mr_iid=mr["iid"],
            mr_url=mr["web_url"],
            branch=branch_name,
        )

        return GitLabEmitResult(
            mr_url=mr["web_url"],
            mr_iid=mr["iid"],
            branch_name=branch_name,
            commit_count=len(files_to_commit),
            recipe_id=recipe.recipe_id,
        )

    def _build_file_list(self, recipe: HardeningRecipe) -> list[tuple[str, str]]:
        files: list[tuple[str, str]] = []
        # 1. The recipe Markdown itself (so reviewers can see the human-readable form in the MR)
        files.append((f"chaoslab/patches/{recipe.recipe_id}.md", render_recipe(recipe)))
        # 2. Per-tool diff files (the actual patches to be applied)
        for i, diff in enumerate(recipe.tool_validation_diffs):
            files.append((f"chaoslab/patches/diffs/{recipe.recipe_id}_{i}_{diff.tool_name}.diff", diff.code_patch))
        # 3. Regression tests (one file with all cases serialized)
        if recipe.regression_test_cases:
            import json
            files.append((
                f"chaoslab/regression_tests/{recipe.recipe_id}.json",
                json.dumps(recipe.regression_test_cases, indent=2),
            ))
        return files

    def _build_mr_description(self, recipe: HardeningRecipe) -> str:
        return (
            f"# ChaosLab Hardening Recipe\n\n"
            f"**Recipe ID:** `{recipe.recipe_id}`\n"
            f"**Target agent:** `{recipe.target_agent_id}`\n"
            f"**Estimated resilience improvement:** "
            f"{recipe.estimated_resilience_improvement * 100:.1f}%\n\n"
            f"---\n\n"
            + render_recipe(recipe)
        )
```

### `_gitlab_mcp_client.py` shape

Async wrapper over the official `https://gitlab.com/api/v4/mcp` endpoint. Core surface:

```python
# apps/chaoslab-agent/src/chaoslab_agent/patcher/_gitlab_mcp_client.py
class GitLabMcpClient:
    OFFICIAL_ENDPOINT = "https://gitlab.com/api/v4/mcp"

    def __init__(self, endpoint: str | None = None, token: str | None = None) -> None:
        self._endpoint = endpoint or self.OFFICIAL_ENDPOINT
        # BANNED-community-MCP gate — protects against accidental override
        if "zereight" in self._endpoint or "mcpland" in self._endpoint or "wadew" in self._endpoint:
            raise ValueError(f"Community MCP endpoints are banned per partner-gitlab.md: {self._endpoint}")
        self._token = token
        self._client = httpx.AsyncClient(timeout=30.0)

    async def _call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """JSON-RPC POST to MCP endpoint. Retries 5xx up to 3 times w/ exp backoff. 401 raises immediately."""
        # payload = {"jsonrpc": "2.0", "method": "tools/call", "params": {"name": tool_name, "arguments": arguments}, "id": 1}
        # Authorization: Bearer <token> header if token is set
        # On 5xx: backoff = 2 ** attempt; max 3 attempts
        # On 401: raise RuntimeError("GitLab authentication failed (401)")
        # On 200 with "error" key: raise RuntimeError(f"GitLab MCP error: {data['error']}")
        ...

    # Public methods (each is a 1-line wrapper over _call_tool with the right MCP tool name):
    #   async create_branch(project_id, branch, ref) -> dict        # tool: "create_branch"
    #   async create_or_update_file(project_id, branch, file_path, content, commit_message) -> dict  # tool: "create_or_update_file"
    #   async create_merge_request(project_id, source_branch, target_branch, title, description, labels=None) -> dict  # tool: "create_merge_request"
    #   async aclose() -> None
```

Tool names (`create_branch`, `create_or_update_file`, `create_merge_request`) are taken verbatim from `partner-gitlab.md` §"Exposed MCP tools". Do NOT rename or paraphrase — the official server rejects unknown tool names.

### Architecture context

- **ADR-011 (mandatory):** OFFICIAL endpoint is `https://gitlab.com/api/v4/mcp`. Per `partner-gitlab.md`: "Use of GitLab's OFFICIAL MCP server is noted in evaluation. If you skip the official server and use a community one (e.g., `zereight/gitlab-mcp` or `mcpland/gitlab-mcp`), you lose points." Shell verification asserts the config string + greps for banned community MCP package names.
- **`@pytest.mark.online`:** integration tests skip in CI by default; run locally with `GITLAB_TOKEN` + `GITLAB_TEST_PROJECT_ID`. Orchestrator runs them in staging pipeline once before demo recording.
- **Per-recipe branch naming:** `chaoslab/recipe-<id_without_prefix>` — strips `recipe_` prefix to avoid `recipe_recipe_` ugliness. Regex `^chaoslab/recipe-[a-z0-9]{12}$` enforces structure.
- **MR description** = recipe ID + estimated improvement at the top + full `render_recipe(recipe)` output. The Markdown emitter (S6.5) is reused — same rendering logic, two destinations.
- **Files committed** (per `partner-gitlab.md` "show real DevOps automation value"): `chaoslab/patches/<recipe_id>.md` (full Markdown), `chaoslab/patches/diffs/<recipe_id>_<i>_<tool>.diff` (one per tool), `chaoslab/regression_tests/<recipe_id>.json` (Phoenix-dataset format). Gives reviewers TYPED artifacts, not just a blob.
- **Auth via `GITLAB_TOKEN`** stored in Secret Manager (S1.4), read via `pydantic.SecretStr` so accidental `.model_dump()` doesn't leak it. PAT with `api` scope — least-privilege per ADR-009.
- **MCP transport = HTTP JSON-RPC** (unlike Phoenix MCP's stdio per `architecture/02 §1.1`). Official auth is OAuth 2.0 Dynamic Client Registration, but PAT bearer token works for the demo per `partner-gitlab.md`.
- **Retry policy:** 3 attempts with exponential backoff on 5xx. 4xx (especially 401) raises immediately. §14 gate: zero mocks in `src/`; unit tests use `respx` at the httpx boundary.

### Test guidance

- **Unit tests (`respx`):** mock `https://gitlab.com/api/v4/mcp` to return canned JSON-RPC responses. Assert (a) correct tool name in payload (`create_branch`, `create_or_update_file`, `create_merge_request`), (b) correct argument shape, (c) auth header includes bearer token, (d) branch name matches `chaoslab/recipe-<id>`, (e) retry triggers on 502/503, (f) 401 raises immediately.
- **Integration tests (`@pytest.mark.online`):** create test project `abu-chaoslab/test-target` with `main` default branch, run `emit(recipe, project_id=...)`, assert real MR URL matches `^https://gitlab\.com/abu-chaoslab/test-target/-/merge_requests/\d+$`, then cleanup by closing MR via `gh api -X PUT ...` (don't delete branch — judges may inspect).
- **BANNED-COMMUNITY-MCP gate test:** assert `GitLabMcpClient(endpoint="https://github.com/zereight/gitlab-mcp/...")` raises `ValueError` — protects against accidental endpoint override.

### Known pitfalls

- **GitLab MCP server is Beta** (per `partner-gitlab.md`). Pin a server version via `get_mcp_server_version` and log it at startup; if tool names change (e.g., `create_or_update_file` → `create_file`), update the client. Test with the real endpoint before demo recording. PAT works for the demo per `partner-gitlab.md`; if OAuth is required later, add a second auth mode behind `GITLAB_AUTH_MODE`.
- **`pydantic.SecretStr.get_secret_value()`** is required to extract the actual token string — `str(SecretStr("x"))` returns `"**********"`. Test fixtures must use real strings or `model_construct` bypass. `HttpUrl` max length is not a concern — GitLab MR URLs are short.
- **Branch creation idempotency:** if the branch already exists (very rare due to 12-char hex), GitLab returns 400. Raise `GitLabEmitterError` with a clear message. Recipe_ids are unique per run, so this shouldn't fire in practice.
- **`project_id` accepts numeric IDs (12345) or path form (`"user/repo"`).** The official MCP server URL-encodes the path form internally — do NOT URL-encode at the Python layer. MR descriptions have a 1MB limit on GitLab; typical recipes are 5-20KB so we're safe.
- **Cross-reference:** `partner-gitlab.md` (MCP tool inventory, BANNED community servers, evaluation credit gate); `architecture.md` ADR-011 (Markdown + GitLab dual-path); `architecture.md` ADR-009 (WIF for GitLab token via Secret Manager); `coding-standards.md` pytest markers (`@pytest.mark.online`).
