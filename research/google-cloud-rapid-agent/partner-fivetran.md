# Partner Track: Fivetran

Hackathon: Google Cloud Rapid Agent Hackathon — https://rapid-agent.devpost.com/
Deadline: June 11, 2026 @ 2:00pm PDT. Judging: June 22 – July 6, 2026.
Prize per partner bucket: 1st $5,000 / 2nd $3,000 / 3rd $2,000.

---

## What the product actually is

**Fivetran** is a managed ELT pipeline. In plain English: you point Fivetran at a SaaS source (Salesforce, Stripe, HubSpot, Shopify, Postgres, S3, Google Sheets — they support 700+ source connectors), Fivetran pulls the data into a warehouse you own (BigQuery, Snowflake, Redshift, etc.), keeps it in sync on a schedule, and handles schema drift / column changes / new tables automatically. You write zero ingestion code. ([fivetran.com](https://www.fivetran.com/), [fivetran-resources](https://rapid-agent.devpost.com/details/fivetran-resources))

For the hackathon, the agentic angle is: **your Gemini ADK agent uses the Fivetran MCP server to control pipelines and read fresh, unified data out of BigQuery.** Connector lifecycle (create, pause, check sync status, list failures) becomes a tool call. The agent can answer "is my Salesforce data fresh?" and "kick off a Stripe re-sync because today's revenue numbers look wrong" — and it can answer "what does my unified pipeline say about <business question>" by reading the destination warehouse. ([github.com/fivetran/fivetran-mcp](https://github.com/fivetran/fivetran-mcp))

For a blockchain dev: Fivetran is to SaaS data what **a multi-chain indexer (Goldsky, Subsquid, Allium)** is to on-chain data. You don't write the ingestion; you point at a source and trust the platform to keep it warehoused, schemed, deduped. The destination warehouse (BigQuery) is your "indexed datastore" — analogous to a multi-chain unified schema. The Fivetran MCP server is the control plane: "list connectors, sync this one, tell me what's broken" — same shape as Goldsky's API for managing subgraphs.

## Core product surface

Five things Fivetran is genuinely best at:

1. **Pre-built connectors at scale.** 700+ source connectors (Salesforce, Stripe, HubSpot, Shopify, Marketo, Zendesk, Postgres, MySQL, GA4, etc.) covering the long tail of enterprise SaaS. ([fivetran.com](https://www.fivetran.com/))
2. **Automatic schema management.** New column appears in source → it appears in BigQuery on the next sync. No manual migration. This is the productivity moat.
3. **Destination = your warehouse.** Data lives in your BigQuery (or Snowflake / etc.). Fivetran is just the conveyor belt. Once the data is in BQ, your agent can query it with standard SQL via a `bigquery_query` tool — independent of Fivetran being up.
4. **Connector SDK (`fivetran-connector-sdk`).** If the 700+ connectors don't include your weird in-house source, you write a custom one in Python. ([github.com/fivetran/fivetran_connector_sdk](https://github.com/fivetran/fivetran_connector_sdk))
5. **Operational observability of pipelines.** Sync status, freshness, schema-change history, failure logs — all programmable via REST API and now MCP.

## Their MCP server

**Repo:** https://github.com/fivetran/fivetran-mcp
**Status:** Official open-source repo from Fivetran. The Fivetran blog calls it the AI-control-plane for connectors. Partner page lists it as the official integration path. ([fivetran-resources](https://rapid-agent.devpost.com/details/fivetran-resources), [fivetran blog](https://www.fivetran.com/blog/integrate-data-faster-using-natural-language-fivetran-and-mcp))

**Install (recommended via `uvx`):**

```bash
uvx --from git+https://github.com/fivetran/fivetran-mcp fivetran-mcp
```

Or clone + run:

```bash
git clone https://github.com/fivetran/fivetran-mcp
# then configure as an MCP server in your ADK agent's MCP client
```

**Required env vars:**

- `FIVETRAN_API_KEY` — from https://fivetran.com/dashboard/user/api-config
- `FIVETRAN_API_SECRET` — same source
- `FIVETRAN_ALLOW_WRITES` — defaults to `false` (read-only); set `true` to enable mutating tools

**Tools the MCP server exposes** (the blog reports 20+ tools; the GitHub README claims 100+ across categories):

**Always-enabled tool groups:**

- **Accounts** — fetch account info, billing tier.
- **Connections (the headline group)** — list connections, get connection details, sync status, last-sync timestamp, recent errors, pause, resume, trigger sync, get table metadata, schema, history.
- **Destinations** — list / inspect destinations (BigQuery setup, region, etc.).
- **Groups** — list/manage logical groups of connections (e.g. "Production").
- **Hybrid Deployment Agents** — manage on-prem hybrid sync agents.
- **External Logging** — sync logs to S3/CloudWatch/etc.
- **Metadata** — table-level + column-level metadata across connectors.
- **Transformations** — manage dbt transformation jobs.
- **Webhooks** — register/inspect webhooks for sync events.

**Optional (disabled by default):** Users, Teams, Roles, System Keys, Private Links, Proxy Agents, Certificates, Fingerprints.

**Example agent queries the README highlights:**

- _"What connections are failing?"_
- _"When did the Salesforce connection last sync?"_
- _"Show me all connections in the Production group."_

**Important:** the Fivetran MCP server is **about controlling pipelines** — not about querying data. To answer "what's our Q2 revenue?" the agent needs a _separate_ tool (e.g. a BigQuery MCP server or a `bigquery_query` ADK tool) to query the warehouse. Don't conflate the two. The winning shape: Fivetran MCP for pipeline ops + BigQuery MCP/tool for analytical queries.

## Free tier / trial details + gotchas

- **Trial length: 14 days.** Signup: https://fivetran.com/signup ([fivetran-resources](https://rapid-agent.devpost.com/details/fivetran-resources))
- **CANNOT BE EXTENDED.** Per the brief.
- **Activation strategy:** activate the trial **close to submission deadline** (e.g. around May 28 – June 1) so:
  1. The trial is live during the final build sprint AND
  2. The trial is still alive during the early part of judging (Jun 22 – Jul 6) so judges who try the live agent see a working pipeline.
  3. If it dies mid-judging, the 3-minute demo video is the locked artifact.
- **BigQuery free-tier setup:** Fivetran needs a destination. BigQuery free tier (1 TB query/month, 10 GB storage) + Google Cloud free trial credits is enough for hackathon scale. Setup guide: https://fivetran.com/docs/destinations/bigquery/setup-guide
- **Mock data shortcut:** The brief says "public SaaS/CRM mock schemas suggested." Fivetran has sample data sources (Google Sheets, demo Postgres, dummy Stripe) you can use _without needing a real corporate Salesforce_. Use these — they're faster to wire than a real source and judges accept them.
- **API key gotcha:** Same API key works for both REST API and MCP server. Generate once at https://fivetran.com/dashboard/user/api-config.
- **Write operations off by default:** Set `FIVETRAN_ALLOW_WRITES=true` only when you want the agent to mutate (pause/resume/trigger sync). For most submissions read-only is fine and safer to demo (no risk of the agent accidentally breaking a sync mid-video).

## What problems this partner is set up to solve well

1. **Pulling data from many SaaS into one warehouse for one agent to reason over.** The canonical pattern. Salesforce + Stripe + HubSpot + Zendesk → BigQuery → agent does cross-source analysis ("which Stripe-paying customers have stalled Salesforce deals AND open Zendesk tickets?").
2. **Pipeline-aware data agents.** Agents that don't just query data but understand _whether the data is fresh and trustworthy_ before answering. "Salesforce last synced 4 hours ago, so revenue numbers might be stale — should I trigger a re-sync first?" This is the agentic shape that fits Fivetran MCP cleanly.
3. **Ops/SRE agents for the data team.** Replace the Slack-bot-asking-"is-our-pipeline-broken" with an agent that lists failing connections, root-causes them, opens tickets, retries syncs.
4. **Real-time-ish business Q&A.** A retail HQ or finance team asking "what's happening across our SaaS stack right now" gets one agent that orchestrates sync + read.

## Concrete agent ideas that fit this partner

### Idea 1 — "Brick-and-mortar StoreOps daily-standup agent"

_Problem:_ A retail chain's regional manager wants a 7am brief: yesterday's sales (POS via Stripe-shaped source), staffing hours (HRIS), inventory deliveries (ERP), Zendesk store complaints — all unified, summarized, and with anomalies flagged.
_Why Fivetran wins this:_ Cross-source unification is the entire value prop. Mock data sources (sample Stripe, sample HubSpot, sample Postgres) → BigQuery → agent. The agent uses Fivetran MCP to verify each source synced overnight BEFORE writing the brief.
_Tools the agent calls:_ Fivetran MCP `get_connection_status` (×4 sources), `trigger_sync` if stale; BigQuery query tool for actual analytics; output to Slack/email.
_Judging fit:_ Potential Impact (real retail use case), Technological Implementation (multi-source + freshness gate), Design (the brief is the demo).

### Idea 2 — "Financial Services trade-reconciliation agent"

_Problem:_ A buy-side firm reconciles trades nightly across custody (S3 files), OMS (Postgres source), and prime broker (CSV via Google Sheets source). Breaks require human investigation.
_Why Fivetran wins this:_ Three different source types → one BigQuery destination. Agent runs reconciliation SQL, surfaces breaks, uses Fivetran MCP to confirm "yes, all three sources synced post-market-close before I started reconciling."
_Tools the agent calls:_ Fivetran MCP `list_connections`, `get_last_sync`, `trigger_sync`; BigQuery `reconcile_trades`; a notify tool.
_Judging fit:_ Quality of Idea (concrete finance workflow), Potential Impact (real ops cost saved).

### Idea 3 — "World Cup vendor-payment agent"

_Problem:_ During the 2026 World Cup, host-city vendors invoice across Stripe, HubSpot, and a custom Postgres ERP. The tournament's finance team needs an agent that detects late payments and chases vendors.
_Why Fivetran wins this:_ Multi-source (Stripe + HubSpot + Postgres ERP via Fivetran sample sources) → BigQuery. Agent joins vendor invoice + payment status, flags overdue, drafts email.
_Tools the agent calls:_ Fivetran MCP `get_connection_metadata` (for table schemas), `trigger_sync`; BigQuery analytical query; an email-draft tool.
_Judging fit:_ Quality of Idea (World Cup angle the brief asks for), Technological Implementation (cross-source agent reasoning).

### Idea 4 — "PipelineDoctor" — SRE-for-data agent

_Problem:_ The data team has 40 Fivetran connectors. Some fail silently; root-causing eats an analyst's morning.
_Why Fivetran wins this:_ PipelineDoctor is **almost entirely Fivetran MCP** — high integration density. Agent lists all connections, finds the broken ones, fetches recent error logs, suggests fixes (auth re-link, schema-change, rate-limit retry), opens a Jira ticket, optionally re-syncs.
_Tools the agent calls:_ Fivetran MCP `list_connections`, `get_connection_errors`, `get_connection_schema_history`, `trigger_sync`, `pause_connection`; Jira tool for ticket creation.
_Judging fit:_ Technological Implementation (deep MCP usage), Potential Impact (real cost saved).

### Idea 5 — "AdSpend ROI agent (retail marketing)"

_Problem:_ A retail CMO sees Meta + Google + TikTok ad spend in their ad-platform UIs, Stripe revenue in finance, store visits in a POS tool — but can't unify into ROAS.
_Why Fivetran wins this:_ Fivetran's strength is exactly this: connecting ad platforms + finance + POS into one warehouse. Agent computes ROAS per channel per store, flags negative-ROI campaigns, drafts a recommendation.
_Tools the agent calls:_ Fivetran MCP `get_destinations`, `get_connection_metadata`; BigQuery `compute_roas`; reporting tool.
_Judging fit:_ Quality of Idea (CMO-facing dashboard-killer), Design (executive UX).

### Idea 6 — "DataContract sentinel"

_Problem:_ Schema drift in source SaaS silently breaks downstream dashboards.
_Why Fivetran wins this:_ Fivetran tracks schema changes as first-class events. Agent monitors `schema_change` events via Fivetran MCP, evaluates downstream impact (which BigQuery views depend on the changed column), and Slacks the affected analytics-engineer.
_Tools the agent calls:_ Fivetran MCP `get_connection_schema_history`, `list_metadata`; BigQuery lineage query; Slack tool.
_Judging fit:_ Quality of Idea (data-contract is hot in 2026), Potential Impact (preventable outage class).

## Track-specific judging risks (things that kill a submission)

1. **Static demo where the data ingestion isn't actually live.** If the demo video shows pre-loaded BigQuery tables without ever calling Fivetran MCP to verify sync / trigger sync / read pipeline state, you've used Fivetran as a CSV uploader. Track explicitly wants live agentic pipeline control.
2. **Using only BigQuery queries, never the Fivetran MCP server.** The Fivetran _integration_ requirement is the MCP server, not BigQuery. A BigQuery-only agent fails the "meaningful Fivetran integration" bar even if Fivetran loaded the data.
3. **One-shot use of Fivetran MCP.** Calling `list_connections` once at startup is checkbox-tier. Real submissions weave MCP throughout the agent loop (freshness gate before every analytical query, sync-on-demand, post-action verification).
4. **Trial expires before judges open the project.** Without a recorded live demo video, judges see nothing. Record while trial is hot.
5. **No code orchestrator.** ADK / Agent Runtime / Cloud Run is required. A pure Workflows-canvas build won't satisfy.
6. **Missing destination warehouse.** No BigQuery (or equivalent) means no data to query, and the agent can only inspect pipeline status — not reason over the actual business data. Set up BigQuery destination on day 1.

## Verified facts table

| Fact                              | Value                                                                                           | Source                                                                                                          |
| --------------------------------- | ----------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| Trial length                      | 14 days                                                                                         | rapid-agent.devpost.com/details/fivetran-resources                                                              |
| Trial extension                   | NOT available                                                                                   | partner brief                                                                                                   |
| MCP server repo                   | https://github.com/fivetran/fivetran-mcp                                                        | rapid-agent.devpost.com/details/fivetran-resources                                                              |
| MCP server status                 | Production, official (Fivetran-published)                                                       | github.com/fivetran/fivetran-mcp                                                                                |
| MCP tools count                   | 20+ (Fivetran blog) / 100+ (README, across categories)                                          | github.com/fivetran/fivetran-mcp                                                                                |
| MCP install                       | `uvx --from git+https://github.com/fivetran/fivetran-mcp fivetran-mcp`                          | github.com/fivetran/fivetran-mcp README                                                                         |
| Auth                              | FIVETRAN_API_KEY + FIVETRAN_API_SECRET                                                          | fivetran.com/dashboard/user/api-config                                                                          |
| Default mode                      | Read-only (FIVETRAN_ALLOW_WRITES=false)                                                         | github.com/fivetran/fivetran-mcp README                                                                         |
| Supported AI clients              | Claude Desktop, Claude Code CLI, Cursor, OpenAI Codex (any MCP-capable client incl. Gemini ADK) | github.com/fivetran/fivetran-mcp README                                                                         |
| Recommended destination warehouse | BigQuery (Google Cloud–native)                                                                  | rapid-agent.devpost.com/details/fivetran-resources                                                              |
| BigQuery destination setup        | https://fivetran.com/docs/destinations/bigquery/setup-guide                                     | rapid-agent.devpost.com/details/fivetran-resources                                                              |
| REST API fallback                 | https://fivetran.com/docs/rest-api (same key works)                                             | rapid-agent.devpost.com/details/fivetran-resources                                                              |
| Connector SDK                     | Python, `fivetran-connector-sdk` on PyPI                                                        | github.com/fivetran/fivetran_connector_sdk                                                                      |
| Demo video                        | ≤3 minutes, English, public link                                                                | rapid-agent.devpost.com/rules                                                                                   |
| Hackathon webinar (Q&A)           | "Power Your AI Agent with Data: Fivetran and Google Cloud Hackathon Q&A"                        | fivetran.com/resources/on-demand-webinars/power-your-ai-agent-with-data-fivetran-and-google-cloud-hackathon-q-a |

## Opinion: Fivetran is the cleanest fit for a blockchain dev who wants the cleanest demo arc

**Pro 1 — mental model maps perfectly.** Fivetran-to-warehouse is multi-chain-indexer-to-subgraph. You already understand "pull from N sources, normalize, query one schema." Zero conceptual lift.

**Pro 2 — the demo arc writes itself.** "User asks business question → agent checks Fivetran pipeline freshness via MCP → triggers sync if stale → queries BigQuery → answers with sourced data." Clean, multi-step, agent-shaped. Judges instantly see "this is the right shape for the track."

**Pro 3 — mock data is fine and fast.** The brief says public SaaS/CRM mocks are suggested. You don't need a real Salesforce; sample sources + a BigQuery destination = working pipeline in ~1 hour.

**Con — the 14-day trial.** Same constraint as Elastic. But Fivetran's setup is faster than Elastic's (no Kibana / ES|QL / tool-definition learning curve), so the 14 days go further.

**Con — pipeline ops are less visually exciting than search results.** "Look, my connector is synced!" doesn't pop in a demo video the way "look, my agent found the perfect document with citations" does. Counter this by building a strong front-end (the agent's _answer_ to a business question is the hero, the pipeline check is the technical credibility).

**Verdict for a blockchain-native solo dev:** Fivetran is the **highest-EV track** of the three. Easy mental model, clean demo arc, real-world-relevant ideas, mock data accepted, and the MCP server has the deepest tool surface (100+ tools) of any track. The 14-day trial is the main risk but it's manageable. Pair it with Arize (for the eval/observability story) if you want a 2-track-worthy submission, but commit to Fivetran as the primary partner.

## Sources

- Hackathon overview: https://rapid-agent.devpost.com/
- Hackathon rules: https://rapid-agent.devpost.com/rules
- Fivetran partner page: https://rapid-agent.devpost.com/details/fivetran-resources
- Fivetran MCP server: https://github.com/fivetran/fivetran-mcp
- Fivetran MCP blog post: https://www.fivetran.com/blog/integrate-data-faster-using-natural-language-fivetran-and-mcp
- Fivetran hackathon Q&A webinar: https://www.fivetran.com/resources/on-demand-webinars/power-your-ai-agent-with-data-fivetran-and-google-cloud-hackathon-q-a
- Fivetran signup: https://fivetran.com/signup
- Fivetran REST API: https://fivetran.com/docs/rest-api
- API key page: https://fivetran.com/dashboard/user/api-config
- BigQuery destination setup: https://fivetran.com/docs/destinations/bigquery/setup-guide
- Fivetran Connector SDK: https://github.com/fivetran/fivetran_connector_sdk
- Community Fivetran MCP toolkits (reference): https://github.com/kellykohlleffel/fivetran-mcp-toolkit
- End-to-end ADK + BigQuery MCP example: https://medium.com/google-cloud/end-to-end-ai-agent-on-gcp-adk-bigquery-mcp-agent-engine-and-cloud-run-4843fec27c13

## Devpost-listed resources (audit 2026-06-03)

The Devpost Fivetran resources tab (https://rapid-agent.devpost.com/details/fivetran-resources) lists 7 official links. All but one are already covered in the body above. Adding the two not previously emphasized:

- **`github.com/fivetran/api_framework`** — Python framework from Fivetran Professional Services that wraps the Fivetran REST API for automation, connector monitoring, and orchestration workflows. Ships with example solutions (AI-driven automation, HVR orchestration, connector management). Useful as a more batteries-included alternative to raw REST calls when the MCP server doesn't expose the surface you need. Repo: https://github.com/fivetran/api_framework
- **`fivetran.com/docs/rest-api/getting-started#authentication`** — REST API uses HTTP Basic Auth with Base64-encoded `api_key:api_secret`. Generate via the dashboard at username → "API Key" → "Generate API key". Header format: `Authorization: Basic <base64(key:secret)>`. Same credential pair powers the MCP server (`FIVETRAN_API_KEY` / `FIVETRAN_API_SECRET`). https://fivetran.com/docs/rest-api/getting-started#authentication

Coverage status: **all 7 Devpost-listed Fivetran resources now covered.**
