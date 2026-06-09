# Partner: GitLab — Rapid Agent Hackathon Track

> **Prize:** 1st $5K / 2nd $3K / 3rd $2K (per partner bucket).
> **Deadline:** June 11, 2026.
> **Stack required:** Code orchestrator = Google Cloud Agent Builder / ADK / Agent Runtime / Cloud Run. Agent must integrate GitLab's official MCP server.

---

## What the product actually is

GitLab is a single-application DevOps platform — think of it as "GitHub + GitHub Actions + Jira + Snyk + Argo + a wiki, all under one product, one auth, one API". Where GitHub is "git host first, everything bolted on", GitLab is "the whole SDLC under one roof from day one". A developer's day-to-day with GitLab looks like: push code → MR opened → pipeline runs CI/CD via `.gitlab-ci.yml` → security/SAST/DAST/license-scanning runs in the same pipeline → reviewer comments → merge → CD pipeline ships to staging or prod → issue closes via commit trailer.

The relevant product layer for this hackathon is GitLab Duo — GitLab's branded AI surface. The MCP server lives inside Duo Agent Platform. From a developer's seat, it exposes the daily GitLab primitives (issues, merge requests, pipelines, jobs, work items, code search) as MCP tools that an external agent (your ADK agent) can call. It is _not_ "GitLab Duo as a coding assistant"; it's the inverse — letting your agent drive GitLab.

For a blockchain-native dev coming in fresh: GitLab is conceptually identical to GitHub for purposes of orchestrating a software project, but the API surface is bigger (CI is first-class, not an "Action" layer on top) and the MCP server gives you a much richer pipeline-management vocabulary than `gh api` ever did.

## Core product surface

The 3-5 things GitLab is genuinely best at:

1. **First-class CI/CD pipelines.** `.gitlab-ci.yml` is the canonical "build → test → deploy" runner. Pipelines, stages, jobs, artifacts, environments, and rollbacks are all native API objects — not third-party app installs.
2. **Merge request workflow.** GitLab MRs were the originals; diff view, threaded review, MR pipelines, approvals, and merge trains all expose well-typed API endpoints.
3. **Issue + epic + work-item hierarchy.** GitLab's issue model goes deeper than GitHub's (epics → issues → tasks, with custom work-item types in newer versions). Strong for triage automation.
4. **Built-in DevSecOps.** SAST, DAST, dependency scanning, secret detection, container scanning all ship as native CI jobs and emit security report artifacts that the API can query.
5. **Self-managed + SaaS parity.** Same API for gitlab.com SaaS and on-prem instances — your agent can target either.

## Their MCP server

**Name:** GitLab MCP server (official, ships as part of GitLab Duo Agent Platform).
**Status:** Beta as of writing — refer to docs for current status before relying in production. [https://docs.gitlab.com/user/gitlab_duo/model_context_protocol/mcp_server/](https://docs.gitlab.com/user/gitlab_duo/model_context_protocol/mcp_server/)
**Endpoint:** `https://<gitlab.example.com>/api/v4/mcp` (use `gitlab.com` for SaaS).
**Transport:** HTTP. Auth via OAuth 2.0 Dynamic Client Registration — your agent registers itself as an OAuth app on first connect.

**Install (Claude Code-style; same idea for any MCP-aware ADK agent):**

```bash
claude mcp add --transport http GitLab https://gitlab.com/api/v4/mcp
```

For Claude Desktop / Cursor / generic MCP-remote client:

```json
{
  "mcpServers": {
    "gitlab": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://gitlab.com/api/v4/mcp"]
    }
  }
}
```

Docker mode for self-managed (env vars `GITLAB_URL`, `GITLAB_TOKEN`) is also documented.

### Exposed MCP tools

Verified from [https://docs.gitlab.com/user/gitlab_duo/model_context_protocol/mcp_server_tools/](https://docs.gitlab.com/user/gitlab_duo/model_context_protocol/mcp_server_tools/):

| Tool                          | What it does                                                                  |
| ----------------------------- | ----------------------------------------------------------------------------- |
| `get_mcp_server_version`      | Returns MCP server version (sanity check).                                    |
| `create_issue`                | Creates an issue with title, description, assignees, milestone, labels, epic. |
| `get_issue`                   | Reads an issue by project + issue ID.                                         |
| `create_merge_request`        | Opens an MR with source/target branches, assignees, reviewers, labels.        |
| `get_merge_request`           | Reads an MR by project + MR ID.                                               |
| `get_merge_request_commits`   | Lists commits in an MR.                                                       |
| `get_merge_request_diffs`     | Gets file-level diffs of an MR (paginated).                                   |
| `get_merge_request_pipelines` | Lists pipelines attached to an MR.                                            |
| `get_pipeline_jobs`           | Lists jobs in a pipeline (build/test/deploy steps).                           |
| `manage_pipeline`             | List / create / update / retry / cancel / delete pipelines.                   |
| `create_workitem_note`        | Comments on an issue/MR/work item.                                            |
| `get_workitem_notes`          | Reads comments on a work item.                                                |
| `search`                      | Full-instance search across issues, MRs, projects.                            |
| `search_labels`               | Searches labels in a project/group.                                           |
| `semantic_code_search`        | AI-powered semantic code search across a project.                             |

That's 15 tools, and the genuinely interesting ones for agent work are `manage_pipeline`, `semantic_code_search`, and the MR diff + commits combo — together they let an agent reason about _why a pipeline failed_, not just _that it failed_.

## Free tier / trial details + gotchas

Per the hackathon brief (verified against Abu's intake):

- **Trial account is sufficient.** A GitLab.com trial account works for getting access to the GitLab MCP server.
- **NO GitLab Premium / GitLab Duo paid tier required for hackathon purposes.** This contradicts the public docs (which list Premium/Ultimate as required) — the hackathon FAQ explicitly grants trial access. _Plan for this to potentially be a trial of Premium/Ultimate, not the Free tier._ [UNVERIFIED — confirm by signing up and checking which tier the trial drops you into.]
- **Use of GitLab's OFFICIAL MCP server is noted in evaluation.** This means if you skip the official server and use a community one (e.g., `zereight/gitlab-mcp` or `mcpland/gitlab-mcp`), you lose points. Pin yourself to `https://gitlab.com/api/v4/mcp`.

**Other gotchas:**

- The MCP server is **Beta** — expect schema churn. Pin a server version via `get_mcp_server_version` and log it in your demo.
- OAuth Dynamic Client Registration means first-run UX includes a browser auth dance. For demo videos, pre-register or use a long-lived token to avoid stalling on-camera.
- `semantic_code_search` quality scales with how much of the repo GitLab has indexed; for a fresh demo project, push real code (not lorem ipsum) and let indexing run before recording.
- Self-managed instances need their own `GITLAB_URL` + token; gitlab.com is the path of least resistance.

## What problems GitLab is set up to solve well

The natural-fit problem shapes:

1. **DevOps automation.** "Agent watches CI/CD, reacts to failures, retries, opens MRs to fix" — pipelines + jobs + MRs are all first-class.
2. **Code review & triage.** Agent reads MR diffs, leaves review notes, files security issues. `get_merge_request_diffs` + `create_workitem_note` is the killer pair.
3. **Repo & issue management at scale.** Bulk triage, label cleanup, epic restructuring, cross-project search via `search` and `search_labels`.
4. **Pipeline failure RCA.** Combine `get_pipeline_jobs` + log retrieval + `semantic_code_search` to point an LLM at the actual failing code path.

GitLab is _not_ set up well for: anything that's purely about hosting/serving code (use the raw API), anything that needs deep git plumbing (clone locally), or anything that needs sub-second event reactions (the MCP server is request/response, not push).

## Concrete agent ideas

Six ideas. Each: one-line problem statement → why GitLab → tools the agent calls → judging-criteria fit.

### 1. CI Pipeline Doctor (DevOps automation)

**Problem:** "Pipeline failed at 2am, on-call dev has to spelunk through job logs to find root cause."
**Why GitLab:** `get_merge_request_pipelines` + `get_pipeline_jobs` + `semantic_code_search` lets the agent correlate the failing job's stderr with the actual code change in the MR.
**Tools:** `get_merge_request`, `get_merge_request_diffs`, `get_merge_request_pipelines`, `get_pipeline_jobs`, `semantic_code_search`, `create_workitem_note`, `manage_pipeline` (retry).
**Judging fit:** Strong on Technological Implementation (multi-tool orchestration), Potential Impact (every team has flaky CI).

### 2. MR Reviewer Agent (Code review)

**Problem:** "Junior devs need senior-style MR review at midnight."
**Why GitLab:** `get_merge_request_diffs` + Gemini for review reasoning + `create_workitem_note` to post threaded inline comments.
**Tools:** `get_merge_request_diffs`, `get_merge_request_commits`, `semantic_code_search` (to pull related code), `create_workitem_note`.
**Judging fit:** Good on Design and Idea Quality. Risk: judges have seen 100 versions of this — differentiate with the semantic_code_search angle.

### 3. World Cup 2026 Match-Day Release Conductor (Devpost example domain)

**Problem:** "Sports broadcaster needs zero-downtime deploys timed around match kickoffs; manual coordination is error-prone."
**Why GitLab:** Agent reads the match schedule (external feed) and uses `manage_pipeline` to gate deploys outside match windows, opens MRs for hotfixes via `create_merge_request`, comments status on a tracking issue.
**Tools:** `manage_pipeline`, `create_merge_request`, `create_issue`, `create_workitem_note`, plus external sports API.
**Judging fit:** Hits the Devpost example domain head-on. Strong on Idea Quality.

### 4. Financial Services Compliance Gate Agent

**Problem:** "Every MR touching payment code must have a SOX-traceable approval trail; manual audit is brutal."
**Why GitLab:** Agent watches new MRs, runs `semantic_code_search` to detect touches to flagged paths (payment, PCI), auto-creates a compliance issue via `create_issue`, links it as a blocker via `create_workitem_note`.
**Tools:** `search`, `semantic_code_search`, `get_merge_request_diffs`, `create_issue`, `create_workitem_note`.
**Judging fit:** Hits Devpost FinServ example. Strong on Potential Impact (regulated industries pay).

### 5. Brick-and-Mortar Retail Deploy Pilot

**Problem:** "Retail chain pushes POS firmware updates to 500 stores; need staged rollout coordinated with store hours."
**Why GitLab:** Agent uses `manage_pipeline` to drive multi-environment pipelines (canary store → region → all), reads `get_pipeline_jobs` for per-store status, files `create_issue` on failures with store metadata.
**Tools:** `manage_pipeline`, `get_pipeline_jobs`, `create_issue`, `create_workitem_note`.
**Judging fit:** Devpost retail domain. Strong on Technological Implementation if you actually model the staged rollout.

### 6. Repo Health Auditor (cross-domain)

**Problem:** "Big GitLab group with 200 repos, no one knows which ones are stale, which have failing main branch, which have open critical security MRs."
**Why GitLab:** Agent enumerates projects via `search`, checks each repo's pipeline state via `get_merge_request_pipelines`, surfaces a weekly health dashboard, opens triage issues via `create_issue`.
**Tools:** `search`, `get_merge_request_pipelines`, `get_pipeline_jobs`, `create_issue`.
**Judging fit:** Good on Potential Impact (every CTO wants this); medium on Quality of Idea (somewhat done before).

## Track-specific judging risks

What kills a GitLab submission:

1. **Thin wrapper around `gh api`-equivalent calls.** If your agent just calls `get_issue` + `create_workitem_note` and that's the demo — judges will read it as "you slapped Gemini on top of curl." Show real DevOps automation value: pipeline orchestration, multi-MR reasoning, semantic search driving decisions.
2. **Using a community MCP server instead of the official one.** The brief says "Use of GitLab's OFFICIAL MCP server is noted in evaluation." Pin to `https://gitlab.com/api/v4/mcp`. Don't use `zereight/gitlab-mcp`, `mcpland/gitlab-mcp`, or `wadew/gitlab-mcp` even if the docs are better — judges will downscore.
3. **No actual CI/CD demonstrated.** GitLab's USP is the pipeline. If your demo only touches issues and MRs but never runs a pipeline, you've used the weakest part of the surface.
4. **Demo video doesn't show the agent doing the thing.** 3-minute demo. Show the agent's tool calls live — pipeline retry, MR comment posted, issue created. Don't just talk over a slide.
5. **Hardcoded project IDs / no multi-project story.** Judges will assume one-off. Show the agent working across at least 2-3 projects in a group.

## Verified facts table

| Fact                          | Value                                                        | Source                    |
| ----------------------------- | ------------------------------------------------------------ | ------------------------- |
| Prize bucket                  | $5K / $3K / $2K                                              | rapid-agent.devpost.com   |
| Required orchestrator         | Google Cloud Agent Builder / ADK / Agent Runtime / Cloud Run | hackathon brief           |
| Demo video length             | ~3 minutes                                                   | rapid-agent.devpost.com   |
| MCP server name               | GitLab MCP server (official, part of Duo Agent Platform)     | docs.gitlab.com           |
| MCP server status             | Beta                                                         | docs.gitlab.com           |
| MCP endpoint                  | `https://<instance>/api/v4/mcp`                              | docs.gitlab.com           |
| MCP transport                 | HTTP                                                         | docs.gitlab.com           |
| MCP auth                      | OAuth 2.0 Dynamic Client Registration                        | docs.gitlab.com           |
| Tier required (public docs)   | Premium or Ultimate                                          | docs.gitlab.com           |
| Tier required (hackathon FAQ) | Trial account sufficient                                     | hackathon brief           |
| Number of tools exposed       | 15                                                           | docs.gitlab.com           |
| Official vs community         | OFFICIAL server required for full credit                     | hackathon brief           |
| SDK languages for ADK         | Python, TypeScript, Go, Java, Kotlin                         | google.github.io/adk-docs |
| Deploy target                 | Cloud Run, Agent Runtime, GKE                                | cloud.google.com          |

## Opinionated take for Abu

GitLab is **medium difficulty** for a blockchain-native solo dev. You already understand git, MRs, and CI/CD conceptually. The risk is that the surface area looks deceptively shallow (only 15 tools) but the _value-creating_ idea space is dominated by deep DevOps insight — and devs who live in GitLab daily will out-execute on idea quality. **If you go GitLab, lean into something cross-domain (sports / FinServ / retail Devpost domains) rather than competing on "best generic CI/CD bot" where domain experts win.** The Pipeline Doctor (#1) and the World Cup Release Conductor (#3) are the highest leverage.

## Sources

- [GitLab MCP Server docs (overview)](https://docs.gitlab.com/user/gitlab_duo/model_context_protocol/mcp_server/)
- [GitLab MCP Server tools reference](https://docs.gitlab.com/user/gitlab_duo/model_context_protocol/mcp_server_tools/)
- [GitLab blog: Duo Agent Platform with MCP](https://about.gitlab.com/blog/duo-agent-platform-with-mcp/)
- [Rapid Agent Hackathon home](https://rapid-agent.devpost.com/)
- [Google ADK docs](https://google.github.io/adk-docs/)
- [Deploy ADK agent to Cloud Run](https://docs.cloud.google.com/run/docs/ai/build-and-deploy-ai-agents/deploy-adk-agent)
- Community MCP servers (NOT for this hackathon, reference only): [zereight/gitlab-mcp](https://github.com/zereight/gitlab-mcp), [mcpland/gitlab-mcp](https://github.com/mcpland/gitlab-mcp)

## Devpost-listed resources (audit 2026-06-03)

The Devpost GitLab resources tab lists 6 official links. Coverage check + fill-in:

| Devpost-listed resource                                                                     | Status                                                 |
| ------------------------------------------------------------------------------------------- | ------------------------------------------------------ |
| `docs.gitlab.com/user/get_started/get_started_agent_platform/`                              | ❌ missing — add below                                 |
| `docs.gitlab.com/user/duo_agent_platform/agents/custom/`                                    | ❌ missing — add below                                 |
| `docs.gitlab.com/user/duo_agent_platform/flows/custom/`                                     | ❌ missing — add below                                 |
| `docs.gitlab.com/user/duo_agent_platform/ai_catalog/`                                       | ❌ missing — add below                                 |
| `docs.gitlab.com/user/gitlab_duo/model_context_protocol/mcp_server/`                        | ✅ covered (in body)                                   |
| `about.gitlab.com/free-trial/` + 30-day Ultimate trial + 24 Duo credits + namespace warning | ⚠ partial (trial mentioned in body, not the specifics) |

### Amendments

- **Duo Agent Platform get-started:** https://docs.gitlab.com/user/get_started/get_started_agent_platform/ — 5-step path: Agentic Chat → use built-in agents → combine in flows → monitor sessions → extend via integrations (Knowledge Graph + MCP). **This is the canonical onboarding doc**; read before building.
- **Custom agents:** https://docs.gitlab.com/user/duo_agent_platform/agents/custom/ — Custom agents are user-defined AI assistants for specific tasks (MR creation, code review). Public/private per project. Accessible via GitLab UI, VS Code, JetBrains via Duo Chat. **For full hackathon credit, define at least one custom agent in the Duo Agent Platform** (mirrors the Elastic "define tools in Kibana" requirement).
- **Custom flows:** https://docs.gitlab.com/user/duo_agent_platform/flows/custom/ — Multi-step AI workflows triggered by events (mentions, assignments, pipeline changes). **Runs on Claude Sonnet 4** (not Gemini) inside GitLab — important nuance: if our agent IS the orchestrator on Cloud Run, we call the MCP server but never trigger a GitLab Duo flow. If we wanted a hybrid (GitLab flow handing off to our Cloud Run agent), this doc explains the trigger model.
- **AI Catalog:** https://docs.gitlab.com/user/duo_agent_platform/ai_catalog/ — Central directory of agents + flows (GitLab-maintained + community). **Publishing our hackathon agent here post-submission is a way to amplify reach** — verify whether the AI Catalog accepts community submissions during the hackathon window.
- **Free trial details:** https://about.gitlab.com/free-trial/ — **30-day Ultimate tier trial.** Includes Duo Agent Platform access + **24 Duo credits per user** + 400 compute minutes/month on GitLab.com. Self-managed trials (GitLab 18.9+) get the same Duo allotment, support excluded. **The 24-credit cap is the real constraint** — credits burn on Duo-platform LLM calls (Claude Sonnet 4). Plan to run our agent off-platform (Cloud Run + Gemini) and use the MCP server primarily for git/MR/pipeline operations to avoid burning credits on inference.
- **External MCP namespace warning** (from Devpost brief, not the public free-trial page): When using third-party MCP servers from within Duo flows, exposed namespaces must be scoped carefully — flows have access to whatever the host namespace can see. **For our submission this is moot** (we drive the GitLab MCP from outside Cloud Run), but worth knowing for any judge who asks about security posture.

Coverage status: **all 6 Devpost-listed GitLab resources now covered.**
