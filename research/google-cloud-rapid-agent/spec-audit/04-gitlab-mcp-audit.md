# Spec Audit 04 — GitLab MCP Endpoint Claims (ADR-011 + S6.6)

**Audited:** 2026-06-03
**Auditor:** spec-audit subagent
**Verdict:** **LOAD-BEARING FAILURE — S6.6 is NOT viable as written. ADR-011 needs amendment. MUST PIVOT.**

The official GitLab MCP server at `https://gitlab.com/api/v4/mcp` IS real, but it **does not expose the file-write or branch-create tools that S6.6 calls.** S6.6's `_gitlab_mcp_client.py` will fail at runtime when it sends `tools/call` for `create_branch` or `create_or_update_file` — the server will return "unknown tool". Worse, the tier requirement per official docs is **Premium/Ultimate, not Free** — trial access is the ONLY mechanism that opens it on a non-paid account, and `partner-gitlab.md` already flagged this as UNVERIFIED.

---

## Summary

| Claims audited | Count |
|---|---|
| CONFIRMED | 4 |
| NEEDS-FIX | 2 |
| WRONG (load-bearing) | 3 |

---

## Claim-by-claim findings

### 1. `https://gitlab.com/api/v4/mcp` is a real endpoint — **CONFIRMED**

The endpoint is documented at https://docs.gitlab.com/user/gitlab_duo/model_context_protocol/mcp_server/ and is part of GitLab Duo Agent Platform. Status: Beta (introduced as experiment in GitLab 18.3, beta in 18.6, protocol-spec 2025-06-18 support added in 18.7). It is GitLab's official, first-party MCP server — confirmed source for "official MCP credit" claim.

### 2. Auth model — **NEEDS-FIX**

`partner-gitlab.md` table row 162 says "MCP auth: OAuth 2.0 Dynamic Client Registration" — this is correct per docs. But S6.6 hardcodes PAT-bearer auth (`Authorization: Bearer <token>`) and the spec note line 325 says "PAT bearer token works for the demo per `partner-gitlab.md`." **The official docs page makes NO mention of PAT support** — it documents OAuth DCR exclusively. PAT-bearer may work in practice (the underlying `/api/v4/*` surface accepts `PRIVATE-TOKEN` and `Authorization: Bearer <PAT>` headers), but is NOT a documented MCP auth path. Required PAT scope for any fallback REST path: `api` (read-write).

**Fix:** S6.6 must either (a) implement OAuth DCR flow (heavy — needs a browser-callback redirect handler at demo time), or (b) accept that PAT-bearer is best-effort and document the auth fallback path. Recommend (b) plus a CI integration test that confirms PAT works against the real endpoint.

### 3. Free-tier access — **WRONG**

`partner-gitlab.md` says "Trial account is sufficient" with the explicit UNVERIFIED flag (line 81). The official docs page now says **"Tier: Premium, Ultimate"** — the MCP server is NOT a Free-tier feature. The hackathon FAQ override (trial = OK) is plausible because GitLab.com trials default to Ultimate for 30 days, but no signed source confirms judges' trial accounts will still be in-trial on June 11 deadline.

**Fix:** Treat this as a 30-day trial dependency, not "free tier." Add to S1.4 / submission audit: book the trial start date so the trial covers demo recording + judge review window. If the trial lapses, MCP access disappears mid-judging.

### 4. MCP tools exposed — **WRONG (load-bearing)**

Verified verbatim from https://docs.gitlab.com/user/gitlab_duo/model_context_protocol/mcp_server_tools/ — the official server exposes exactly **16 tools**:

```
get_mcp_server_version, create_issue, get_issue, create_merge_request,
get_merge_request, get_merge_request_commits, get_merge_request_diffs,
get_merge_request_pipelines, get_pipeline_jobs, get_job_log, manage_pipeline,
create_workitem_note, get_workitem_notes, search, search_labels, semantic_code_search
```

(`partner-gitlab.md` lists 15 — it is missing `get_job_log`, added later in GitLab 18.x. Not load-bearing.)

**Tools S6.6 calls that DO NOT EXIST on the official server:**

| S6.6 calls | Status on official MCP | What to do |
|---|---|---|
| `create_merge_request` | EXISTS (18.5, enhanced 18.8) | Keep — this is the only call S6.6 makes that actually works |
| `create_branch` | **DOES NOT EXIST** | Fall back to REST `POST /projects/:id/repository/branches` |
| `create_or_update_file` | **DOES NOT EXIST** | Fall back to REST `POST /projects/:id/repository/files/:file_path` |

Run this against the live endpoint with a valid trial token and you will get `tool not found` for both. S6.6's BDD acceptance criterion at line 53 ("respx history shows POST to ... with tool name `create_merge_request`") passes only because respx is mocking — there is no live-endpoint verification in unit tests, only `@pytest.mark.online` which skips in CI by default.

### 5. `create_or_update_file` assumption — **WRONG (load-bearing)**

S6.6 lines 25, 220-226, 310-311, and the BDD criterion at line 60 ("respx history shows at least 1 file-creation MCP call per patch + diff") all assume `create_or_update_file` is an MCP tool. **It is not.** There is no file-write tool of any name on the official server. The official MCP server's scope is intentionally read-skewed-with-MR-write — it does NOT expose repository-content mutation. Repository writes go through the underlying REST API (`/api/v4/projects/:id/repository/files/:file_path`).

### 6. Official MCP server = judge-credited — **CONFIRMED**

`partner-gitlab.md` line 82 ("Use of GitLab's OFFICIAL MCP server is noted in evaluation") cites the hackathon brief. The line was copied from the GitLab partner page on Devpost (not re-verified live in this audit — Devpost auth gated). Treat as confirmed based on `partner-gitlab.md`'s sourcing, but recommend re-verifying against Devpost in `07-pre-commit-checklist.md`.

### 7. Banned community MCPs — **CONFIRMED (all 3 exist)**

| Repo | Real? | Stars | Last active | Tools |
|---|---|---|---|---|
| `zereight/gitlab-mcp` | YES | 1.6k | v2.1.18 May 30 2026 | 170 tools including `create_or_update_file`, `create_branch`, `create_merge_request` |
| `mcpland/gitlab-mcp` | YES | 8 | v1.5.1 May 28 2026 | 80+ tools including projects, MRs, pipelines, commits, repo mgmt |
| `wadew/gitlab-mcp` | YES | — | active 2026 | Full GitLab surface incl. branches/commits/MRs; pip-installable as `python-gitlab-mcp` |

All three expose the file-write + branch-create surface that the official server lacks — which is exactly why community MCPs exist. The BAN list and grep-check in S6.6 (line 47, 123) is correctly scoped — these are real packages an unwary coding agent could install. **Keep the ban.**

### 8. Rate limits — **NEEDS-FIX**

No published MCP-specific rate limits on the docs page. Underlying GitLab API rate limits apply (gitlab.com defaults: 2000 req/min authenticated per user). For the demo (single MR per recipe, ~5 tool calls per emit) we are nowhere near limits. Risk is zero for hackathon scope. **No spec change required, but log it in CONTEXT.md so judges asking "what about rate limits" get an answer.**

---

## Recommended pivot — Hybrid: official MCP for MR creation + python-gitlab SDK for files/branch

This preserves the "official MCP credit" claim WHERE IT APPLIES while making S6.6 actually work.

**`_gitlab_mcp_client.py` keeps these official MCP calls only:**
- `create_merge_request` — at the official `https://gitlab.com/api/v4/mcp` endpoint
- Optionally: `create_workitem_note` (MR comment with recipe summary), `get_merge_request` (to fetch web_url for return value)

**New file `_gitlab_rest_client.py` (or via `python-gitlab` SDK) handles the surface the official MCP omits:**
- Branch creation: `python-gitlab` Project.branches.create({'branch': name, 'ref': 'main'})
- File commits: `python-gitlab` Project.files.create(...) / Project.commits.create(...) — use `commits` API to commit multiple files atomically
- Both auth with the same PAT (api scope)

**Spec updates required:**

1. **ADR-011** — change "GitLab MR via `https://gitlab.com/api/v4/mcp`" to "GitLab MR via `https://gitlab.com/api/v4/mcp` for MR creation, with python-gitlab SDK handling branch + file commits (official MCP server does not expose repository-write tools — see audit 04)."

2. **S6.6 file modification map** — add `_gitlab_rest_client.py` (≤200 LOC); `_gitlab_mcp_client.py` shrinks to ≤120 LOC (only `create_merge_request` + version check).

3. **S6.6 BDD criteria** — line 53 keeps the `create_merge_request` assertion; line 60 ("file-creation MCP call per patch + diff") changes to assert `python-gitlab.Project.files.create` or `commits.create` was called per file.

4. **S6.6 tool name list** (line 25, 315) — remove `create_branch` and `create_or_update_file` from the MCP client surface.

5. **`partner-gitlab.md`** — add a callout under "Exposed MCP tools" warning that file/branch ops are NOT in the MCP surface and require fallback to REST/python-gitlab.

6. **`docs/architecture.md` line 173** — `python-gitlab` is already listed as a dep. No package change needed; just expand the usage scope.

**Alternative pivot (if hybrid feels too complex):** drop MCP entirely and use python-gitlab for all 3 calls. Loses the "official MCP credit" hackathon bonus but is the simplest, fully-working path. Recommend AGAINST this unless time pressure forces it — the credit is exactly the kind of judge-visible signal that wins close decisions.

---

## Sources

- [GitLab MCP server overview (docs.gitlab.com)](https://docs.gitlab.com/user/gitlab_duo/model_context_protocol/mcp_server/) — endpoint, Premium/Ultimate tier, OAuth DCR auth, Beta status
- [GitLab MCP server tools reference](https://docs.gitlab.com/user/gitlab_duo/model_context_protocol/mcp_server_tools/) — verbatim 16-tool list, NO file or branch tools
- [GitLab Branches REST API](https://docs.gitlab.com/api/branches/) — `POST /projects/:id/repository/branches`, Free/Premium/Ultimate
- [GitLab Repository Files REST API](https://docs.gitlab.com/api/repository_files/) — `POST /projects/:id/repository/files/:file_path`, requires `api` scope
- [zereight/gitlab-mcp](https://github.com/zereight/gitlab-mcp) — community MCP, 170 tools incl. file/branch ops
- [mcpland/gitlab-mcp](https://github.com/mcpland/gitlab-mcp) — community MCP, 80+ tools
- [wadew/gitlab-mcp](https://github.com/wadew/gitlab-mcp) — community MCP, python-installable, full surface
- `/Users/abu/dev/hackathon/rapid-agents/research/google-cloud-rapid-agent/partner-gitlab.md` — original verified tool list (15) and BAN policy
- `/Users/abu/dev/hackathon/rapid-agents/docs/architecture.md` ADR-011 — current spec to amend
- `/Users/abu/dev/hackathon/rapid-agents/docs/stories/story-6.6-gitlab-mr-emitter.md` — story to amend
