# Partner: Dynatrace — Rapid Agent Hackathon Track

> **Prize:** 1st $5K / 2nd $3K / 3rd $2K (per partner bucket).
> **Deadline:** June 11, 2026.
> **Stack required:** Code orchestrator = Google Cloud Agent Builder / ADK / Agent Runtime / Cloud Run. Agent must integrate Dynatrace's official MCP server.

---

## What the product actually is

Dynatrace is an enterprise APM (Application Performance Monitoring) and observability platform. It's the kind of tool a SaaS company with hundreds of microservices buys to answer "why is checkout slow right now?" without humans grepping logs across 30 services. You install a single agent binary (OneAgent) on every host or in every container, and it auto-instruments runtime traces, host metrics, logs, real-user monitoring, and security signals — all flowing into Dynatrace's data lakehouse called **Grail**.

Grail is the central concept. It's a columnar/MPP analytics store you query with **DQL (Dynatrace Query Language)** — think SQL-shaped but built for telemetry. Logs, traces, metrics, and security events all share the same query surface. On top of Grail, Dynatrace ships **Davis** — their AI causal engine that picks out root cause across the topology graph called **Smartscape**.

For a blockchain-native dev coming in fresh: there is no equivalent in your stack. The closest analog is "Etherscan + The Graph + Tenderly, but for traditional servers." It's expensive, enterprise, and has the steepest learning curve of the three partners — but the MCP server is genuinely powerful, with tools that let an agent do real SRE work (problem triage, root cause, security vuln remediation).

The Dynatrace MCP server is open-source ([dynatrace-oss/dynatrace-mcp](https://github.com/dynatrace-oss/dynatrace-mcp), Apache-2.0) and currently in **maintenance mode** per the README. It works with VS Code, Claude, Cursor, ChatGPT, Amazon Q, GitHub Copilot — and explicitly with Google Gemini CLI.

## Core product surface

The 3-5 things Dynatrace is genuinely best at:

1. **Auto-instrumented APM.** OneAgent picks up Java/.NET/Node/Python/Go/PHP services without code changes. Distributed traces stitched automatically.
2. **Grail + DQL.** Unified query language across logs, metrics, traces, events. `fetch logs | filter loglevel == "ERROR" | summarize count() by service` reads like SQL but spans every signal.
3. **Davis AI causal RCA.** Where Prometheus/Grafana shows you "this metric spiked," Davis shows you "this metric spiked _because_ a deploy 4 minutes ago changed config X on service Y which is upstream of Z" — actual causal graph.
4. **Security signals (Application Security).** Runtime vulnerability detection on live workloads — `list_vulnerabilities` tool surfaces CVEs in the running stack.
5. **Workflow automation.** Trigger Slack/email/webhooks/runbooks from observability signals, exposed via MCP tools.

## Their MCP server

**Name:** Dynatrace MCP Server (`@dynatrace-oss/dynatrace-mcp-server`).
**Repo:** [https://github.com/dynatrace-oss/dynatrace-mcp](https://github.com/dynatrace-oss/dynatrace-mcp)
**Status:** Maintenance mode (as of the current README). Still functional, still officially supported.
**License:** Apache-2.0.
**Hub listing:** [https://www.dynatrace.com/hub/detail/dynatrace-mcp-server/](https://www.dynatrace.com/hub/detail/dynatrace-mcp-server/)

**Install (canonical):**

```bash
npx -y @dynatrace-oss/dynatrace-mcp-server@latest
```

**Required env:**

- `DT_ENVIRONMENT` — your Dynatrace tenant URL, e.g. `https://abc12345.apps.dynatrace.com`

**Optional env:**

- `DT_PLATFORM_TOKEN` — Platform Token for non-interactive auth (alternative: browser OAuth flow)
- `DT_GRAIL_QUERY_BUDGET_GB` — Grail query budget cap (default: 1000 GB). **Set this LOW for hackathon to avoid surprise consumption.**

**Prerequisites:** Node.js v22.10 or newer.

### Exposed MCP tools

Verified from the dynatrace-oss/dynatrace-mcp README:

**Observability & Problem Management**

- `list_problems` — Active problems (Davis-detected incidents) on monitored systems
- `list_vulnerabilities` — Open security vulnerabilities across workloads
- `list_exceptions` — Application exceptions captured by OneAgent
- `get_kubernetes_events` — K8s cluster events

**Grail Data Querying**

- `execute_dql` — Run a DQL query (THIS IS THE BIG ONE — consumes Grail GB scanned)
- `verify_dql` — Validate DQL syntax without executing
- `generate_dql_from_natural_language` — NL → DQL
- `explain_dql_in_natural_language` — DQL → NL summary

**Entity Management**

- `find_entity_by_name` — Locate hosts, services, processes, K8s entities by name

**Davis AI**

- `chat_with_davis_copilot` — Conversational Q&A with Davis
- `list_davis_analyzers` — Available analyzers (root cause, anomaly detection, etc.)
- `execute_davis_analyzer` — Run a specific analyzer programmatically

**Automation & Notifications**

- `create_workflow_for_notification` — Build a notification workflow
- `send_slack_message`
- `send_email`
- `send_event` — Push a custom event into Grail

**Documentation**

- `create_dynatrace_notebook` — Save query results to a shareable notebook

That's roughly 15 tools. The center of gravity is `execute_dql` + `list_problems` + `chat_with_davis_copilot` — those three are what differentiate Dynatrace from "just another logging tool."

## Free tier / trial details + gotchas

Per the hackathon brief (verified against Abu's intake):

- **Dynatrace offers a 15-day free trial.** [https://www.dynatrace.com/trial/](https://www.dynatrace.com/trial/) — full platform access, time-bound, no permanent free tier. This is the path for the hackathon. **The 15-day window means start the trial AFTER your build is ready to demo, not on day 1 — otherwise it'll expire before submission.**
- **No sample data is provided.** This is the killer detail. The hackathon explicitly notes: bring your own dataset. Suggested options:
  - **Synthetic system telemetry logs** — generate via a load generator (k6, locust) hitting a test service
  - **Public APM datasets** — e.g., Google's traces from the Borg paper, or public OpenTelemetry demo apps
  - **Small local server logs** — run a Node/Python service in Docker, point OneAgent at it, generate traffic
- **MCP server is free, Grail queries are NOT.** Every `execute_dql` call costs GB-scanned against your trial allocation. The default `DT_GRAIL_QUERY_BUDGET_GB=1000` is generous for a 15-day trial, but pathological queries (no time filter, broad `fetch`) can burn through fast. **Always include a `from:` time filter.**
- Trial signup typically requires a business email. [UNVERIFIED — confirm whether ajweb3dev@gmail.com works or if you need a custom domain email.]
- Trial does NOT require a credit card [UNVERIFIED — verify at signup].

**Other gotchas:**

- The README states the server is in "maintenance mode" — interpret as "stable but no major new features." Tools shouldn't disappear during the hackathon window, but pin a version: `@dynatrace-oss/dynatrace-mcp-server@<exact-version>`.
- Node 22.10+ required. Cloud Run base images may default lower; check your `Dockerfile`.
- OneAgent must be running on whatever workload you want to monitor. For a demo, install OneAgent on a small Cloud Run service or a single VM and generate traffic. **This is the gating step — get OneAgent reporting BEFORE building the agent.**
- The OAuth browser flow stalls in headless environments. Use Platform Token (`DT_PLATFORM_TOKEN`) for any non-interactive demo.

## What problems Dynatrace is set up to solve well

The natural-fit problem shapes:

1. **Production observability of complex systems.** Multi-service apps with real traffic where "what's broken and why" is hard. Davis + Smartscape are designed for exactly this.
2. **SRE / on-call automation.** Agent watches problems, runs DQL diagnostics, posts Slack with diagnosis. `list_problems` + `execute_dql` + `send_slack_message` is the killer chain.
3. **Security posture / runtime vuln remediation.** `list_vulnerabilities` + `chat_with_davis_copilot` + workflow trigger for CVE response.
4. **Capacity planning / cost optimization.** DQL queries over historical metrics to find over-provisioned services.

Dynatrace is _not_ set up well for: anything where you don't have real workloads to monitor (you'd be demoing fake data), short-lived demo apps with no history (Davis needs hours of data to learn baselines), or anything that competes with the platform's own dashboards (your agent's UI must add value beyond the Dynatrace UI).

## Concrete agent ideas

Six ideas. Each: problem statement → why Dynatrace → tools the agent calls → judging fit.

### 1. On-Call SRE Co-Pilot

**Problem:** "PagerDuty alert at 3am — engineer needs root cause in under 5 minutes."
**Why Dynatrace:** `list_problems` returns Davis-detected incidents with causal links. Agent queries `execute_dql` for surrounding context, calls `chat_with_davis_copilot` for hypothesis, posts to Slack with proposed mitigation.
**Tools:** `list_problems`, `execute_dql`, `chat_with_davis_copilot`, `find_entity_by_name`, `send_slack_message`.
**Judging fit:** Strongest implementation story — multi-tool chain, real value. Risk: very on-the-nose; many submissions will pick this.

### 2. Vulnerability Remediation Conductor

**Problem:** "Security team finds a critical CVE; needs to know which production services are affected and orchestrate patching."
**Why Dynatrace:** `list_vulnerabilities` knows the _runtime_ exposure (which JARs are actually loaded), not just what's in `package.json`. Agent cross-references with deployment metadata, opens triage workflow.
**Tools:** `list_vulnerabilities`, `execute_dql` (deployment correlation), `find_entity_by_name`, `create_workflow_for_notification`, `send_email`.
**Judging fit:** Strong on Potential Impact. Differentiates from "just another security scanner" via runtime visibility.

### 3. World Cup 2026 Streaming Reliability Agent (Devpost domain)

**Problem:** "Live sports broadcaster runs 100+ microservices; can't have buffering during a goal."
**Why Dynatrace:** Real-time DQL queries over user-experience metrics + service traces + Davis problem feed. Agent pre-emptively scales / shifts traffic when latency drifts before users notice.
**Tools:** `execute_dql` (latency p99), `list_problems`, `chat_with_davis_copilot`, `send_event` (back into Grail for audit), `send_slack_message`.
**Judging fit:** Devpost domain hit. Strong on Idea Quality.

### 4. Financial Services SLA Sentinel (Devpost domain)

**Problem:** "Bank has contractual SLAs on transaction latency; needs continuous evidence + automated breach alerts with root cause."
**Why Dynatrace:** DQL over transaction traces, Davis for RCA when SLA breaches, agent produces an auditable notebook via `create_dynatrace_notebook`.
**Tools:** `execute_dql`, `list_problems`, `execute_davis_analyzer`, `create_dynatrace_notebook`, `send_email`.
**Judging fit:** Devpost FinServ. Strong on Potential Impact + auditability.

### 5. Brick-and-Mortar Retail POS Health Agent (Devpost domain)

**Problem:** "Retail chain with 500 stores, POS terminals reporting telemetry. Manager needs proactive alerts on store-level degradation."
**Why Dynatrace:** OneAgent on POS terminals → Grail. Agent runs DQL grouped by store, surfaces top-N degrading stores, calls Davis for per-store root cause.
**Tools:** `execute_dql` (group by store), `list_problems`, `find_entity_by_name`, `chat_with_davis_copilot`, `send_email`.
**Judging fit:** Devpost retail. Strong on Idea Quality if visually presented (map of stores).

### 6. K8s Cluster Whisperer

**Problem:** "DevOps team running multi-cluster GKE; needs natural language Q&A across cluster events + workloads."
**Why Dynatrace:** `get_kubernetes_events` + Davis K8s analyzers + DQL. Agent answers "why is pod X restarting?" with full causal chain.
**Tools:** `get_kubernetes_events`, `list_problems`, `execute_dql`, `chat_with_davis_copilot`, `find_entity_by_name`.
**Judging fit:** Solid on Technological Implementation. Risk: K8s monitoring is crowded; differentiate via the agent's NL interface.

## Track-specific judging risks

What kills a Dynatrace submission:

1. **Not actually wiring real telemetry data.** The brief is explicit. If your demo's data is faked — hardcoded JSON, mock responses — judges will spot it in the 3-minute video. **Get OneAgent installed on a real workload (even a tiny Cloud Run service hitting itself) and let it collect data for at least 24h before recording.** This is the #1 killer.
2. **Demo that's just dashboards Dynatrace already has.** The Dynatrace UI is excellent. If your agent's output is a chart that looks like a Dynatrace dashboard — you've added nothing. Differentiate via: agent reasoning over data, multi-tool chains, actions taken (Slack/email/workflows), NL Q&A that beats clicking through the UI.
3. **Burning the Grail budget pre-demo.** Untimed `fetch logs | sort` queries can scan TB. Set `DT_GRAIL_QUERY_BUDGET_GB=50` and always include `from: now() - 1h` in your DQL.
4. **OAuth browser flow on stage.** Demo will stall. Use `DT_PLATFORM_TOKEN`.
5. **Trial expiration mid-build.** 15 days. Start trial late, finish build first.
6. **Forgetting Cloud Run requirement.** Even if Dynatrace is the star, deploy your ADK agent to Cloud Run; show it in the demo.

## Verified facts table

| Fact                  | Value                                                                  | Source                                        |
| --------------------- | ---------------------------------------------------------------------- | --------------------------------------------- |
| Prize bucket          | $5K / $3K / $2K                                                        | rapid-agent.devpost.com                       |
| Required orchestrator | Google Cloud Agent Builder / ADK / Agent Runtime / Cloud Run           | hackathon brief                               |
| Demo video length     | ~3 minutes                                                             | rapid-agent.devpost.com                       |
| MCP server name       | `@dynatrace-oss/dynatrace-mcp-server`                                  | github.com/dynatrace-oss/dynatrace-mcp        |
| MCP server status     | Maintenance mode (stable, open-source)                                 | github.com/dynatrace-oss/dynatrace-mcp README |
| License               | Apache-2.0                                                             | github.com/dynatrace-oss/dynatrace-mcp        |
| Install               | `npx -y @dynatrace-oss/dynatrace-mcp-server@latest`                    | github.com/dynatrace-oss/dynatrace-mcp        |
| Required env          | `DT_ENVIRONMENT`                                                       | github.com/dynatrace-oss/dynatrace-mcp        |
| Optional env          | `DT_PLATFORM_TOKEN`, `DT_GRAIL_QUERY_BUDGET_GB`                        | github.com/dynatrace-oss/dynatrace-mcp        |
| Node version          | v22.10+                                                                | github.com/dynatrace-oss/dynatrace-mcp        |
| Free tier             | 15-day trial, no permanent free tier                                   | dynatrace.com/trial                           |
| Sample data provided  | NO — bring your own (synthetic, public APM, local logs)                | hackathon brief                               |
| Grail query cost      | Yes — per-GB-scanned, consumes trial allocation                        | dynatrace.com/hub/detail/dynatrace-mcp-server |
| Number of MCP tools   | ~15 across 6 categories                                                | github.com/dynatrace-oss/dynatrace-mcp        |
| Supported clients     | VS Code, Claude, Cursor, ChatGPT, Amazon Q, GitHub Copilot, Gemini CLI | github.com/dynatrace-oss/dynatrace-mcp        |
| Query language        | DQL (Dynatrace Query Language)                                         | docs.dynatrace.com                            |
| AI engine             | Davis (causal RCA)                                                     | dynatrace.com                                 |

## Opinionated take for Abu

**Dynatrace is the HIGHEST friction track for a blockchain-native solo dev.** Three reasons:

1. **You need real telemetry data.** No sample dataset is provided. You'll spend 30-40% of your hackathon time just setting up a workload to monitor (OneAgent on a Cloud Run service, traffic generator, wait for data to land in Grail). This is unique to Dynatrace.
2. **15-day trial pressure.** Tightest time window of any partner. If the trial expires mid-recording, you're done.
3. **Steepest concept ladder.** DQL is new. Smartscape is new. Davis is new. None of this maps onto your Web3 mental model.

**Counter-argument: it's also the lowest-competition track.** If most hackers default to MongoDB (easier) or GitLab (familiar), the Dynatrace prize pool may be the least-contested $5K. **If you have an actual SRE/observability angle you care about, this is the highest-EV track.**

**Biggest leverage:** Pick a Devpost domain (Streaming Reliability for World Cup is the sharpest), get OneAgent reporting on a tiny Cloud Run app on day 1, then build the agent on top of real (if small) Grail data. The On-Call SRE Co-Pilot (#1) is the strongest pure-Dynatrace idea; the World Cup Streaming Reliability Agent (#3) is the strongest domain-fit idea.

**Skip:** Anything that requires multi-day Davis baseline learning. You don't have time. Build for low-data demos where the agent's reasoning over a small dataset is the story.

## Sources

- [dynatrace-oss/dynatrace-mcp GitHub](https://github.com/dynatrace-oss/dynatrace-mcp)
- [Dynatrace MCP Server hub listing](https://www.dynatrace.com/hub/detail/dynatrace-mcp-server/)
- [Dynatrace MCP + GitHub Copilot blog](https://www.dynatrace.com/news/blog/sky-high-developer-productivity-with-dynatrace-mcp-and-github-copilot/)
- [Dynatrace expands AI Coding Agent monitoring (Gemini CLI, Claude Code, Codex)](https://www.dynatrace.com/news/blog/dynatrace-expands-ai-coding-agent-monitoring/)
- [What is Model Context Protocol — Dynatrace knowledge base](https://www.dynatrace.com/knowledge-base/model-context-protocol/)
- [Dynatrace pricing](https://www.dynatrace.com/pricing/)
- [Dynatrace free trial](https://www.dynatrace.com/trial/)
- [Rapid Agent Hackathon home](https://rapid-agent.devpost.com/)
- [Google ADK docs](https://google.github.io/adk-docs/)
- [Deploy ADK agent to Cloud Run](https://docs.cloud.google.com/run/docs/ai/build-and-deploy-ai-agents/deploy-adk-agent)
- Community reference (NOT for this hackathon): [theharithsa/dynatrace-mcp-otel](https://github.com/theharithsa/dynatrace-mcp-otel)
