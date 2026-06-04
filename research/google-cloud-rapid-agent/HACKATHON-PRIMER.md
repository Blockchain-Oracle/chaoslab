# Hackathon Primer — Names, Times, Links

> Built for Abu to self-verify before locking the wedge. Every claim has a link. Read in order; bullets at the end summarize action items.
>
> **Sourced from** the 5-agent research pass (2026-06-03/04): `brainstorm/08-current-pain-points-2026.md` · `09-hackathon-winner-patterns-2025-2026.md` · `10-sponsor-hidden-use-cases.md` · `11-vertical-agent-gaps.md` · `12-saturation-map.md` · `refs/devpost-content-verbatim-2026-06-03.md` · `refs/official-rules-verbatim.md`.

---

## The hackathon at a glance

| Fact                          | Value                                                                                                                         | Link                            |
| ----------------------------- | ----------------------------------------------------------------------------------------------------------------------------- | ------------------------------- |
| Name                          | Google Cloud Rapid Agent Hackathon                                                                                            | https://rapid-agent.devpost.com |
| Sponsor                       | Google LLC (Mountain View, CA)                                                                                                | —                               |
| Contest period                | 2026-05-05 12:00 PT → **2026-06-11 14:00 PT**                                                                                 | rules §5                        |
| Judging window                | 2026-06-22 → 2026-07-06                                                                                                       | rules §8                        |
| Winner notification           | ~2026-07-07 (2 business days to respond)                                                                                      | rules §8                        |
| Tracks                        | 6 — Arize, Elastic, Fivetran, GitLab, MongoDB, Dynatrace                                                                      | rules §3                        |
| Per-track prize               | $5,000 / $3,000 / $2,000                                                                                                      | rules §9                        |
| Total prize pool              | **$60,000** across 18 winners                                                                                                 | rules §9                        |
| Registered participants       | **2,777+**                                                                                                                    | per Devpost                     |
| Required AI runtime           | Gemini models on Agent Platform + ADK + Agent Runtime / Cloud Run + Partner MCP. All other AI tools banned in submitted code. | rules §7B                       |
| GCP $100 credit form deadline | **2026-06-04** (TODAY — confirm submitted)                                                                                    | rules §6                        |

---

## The 6 tracks — one section each

For each: judges by name (with link), sponsor primitives, trial details, named past winners using this sponsor's stack, what to use IMMEDIATELY, saturation rating, gotchas.

### 🟢 Arize (lowest competition — predicted 8-20 entries)

**Judges:**

- **Richard Young** — Director, Partner Solutions @ Arize. Email open during hackathon: `ryoung@arize.com`. https://www.linkedin.com/in/richardyoungiii/
- **Clay Miner** — Head of Solutions Strategy @ Arize. https://www.linkedin.com/in/claymineriii/

**Their sponsor "what we want" quote (verbatim Devpost):**

> "Bonus points for agents that use their own observability data to improve over time."

**Sponsor primitives (build these into your demo):**

- Phoenix Cloud (free tier, hosted) — https://app.phoenix.arize.com
- Phoenix MCP server (`@arizeai/phoenix-mcp` via npx) — https://arize.com/docs/phoenix/integrations/mcp/integrations-mcp
- OpenInference instrumentors:
  - `openinference-instrumentation-google-adk` 0.1.15 — https://pypi.org/project/openinference-instrumentation-google-adk/
  - `openinference-instrumentation-vertexai` 0.1.16 — https://pypi.org/project/openinference-instrumentation-vertexai/
  - `openinference-instrumentation-google-genai` 1.0.2 — https://pypi.org/project/openinference-instrumentation-google-genai/
- **The official quickstart** (THE reference build): https://github.com/Arize-ai/gemini-hackathon — deliberately minimal (17 files, 1 agent, 2 tools, in-memory mock webshop). Proves trace pipeline only. Zero evals/experiments/tests.
- LLM-as-a-Judge cookbook — https://arize.com/blog/llm-as-a-judge/
- Phoenix Prompt Learning — https://arize.com/blog/prompt-learning/

**Trial:** Phoenix Cloud free tier. No trial expiration. Self-hosted Phoenix also free.

**Things people could use IMMEDIATELY:**

- Customer-support agent that learns from past escalations (queries its own Phoenix traces via MCP, finds nearest 3 past tickets, applies their resolution shape)
- Prior-auth or claims agent for a regulated industry that ANNOTATES its own decisions so compliance can audit later
- Coding-assistant tracer that flags regressions in your team's prompt usage week-over-week

**Saturation:** 🟢 LOW. 🔴 AVOID: agent observability dashboards (15+ priors, Great Agent Hack "Glass Box" track had 17). Build a PRODUCT, not a dashboard.

**Gotchas:**

- Phoenix MCP is partial — `experiments.run_experiment` and `spans.log_span_annotations` are NOT MCP tools. Use `phoenix.client.AsyncClient()` to wrap as ADK FunctionTools.
- Phoenix MCP can be wired in 2 places: (a) `.gemini/settings.json` for Gemini CLI (the quickstart's pattern), (b) Python runtime via ADK FunctionTool (what RAT verified). Different mental models — pick deliberately.

### 🟡 Elastic (predicted 25-50 entries)

**Judges:**

- **Anish Mathur** — Director of Product Management @ Elastic. https://www.linkedin.com/in/anishmathur/
- **Philipp Krenn** — Director of DevRel @ Elastic. https://twitter.com/xeraa

**Sponsor primitives:**

- Elastic Cloud Serverless (free trial) — https://cloud.elastic.co
- Agent Builder (Kibana UI) — https://www.elastic.co/docs/solutions/search/elastic-agent-builder
- Elastic MCP server (built-in with Agent Builder) — https://www.elastic.co/docs/solutions/search/elastic-agent-builder/mcp-server
- ELSER semantic model (auto-runs) — https://www.elastic.co/docs/solutions/search/semantic-search-elser-ingest-pipelines
- ES|QL Language Reference — https://www.elastic.co/docs/reference/query-languages/esql
- Workflows + subagents — https://www.elastic.co/docs/solutions/search/elastic-agent-builder/workflows
- Reference architecture blog (the closest-shape canonical build) — https://www.elastic.co/blog/agentic-reference-architecture-elastic-agent-builder-mcp
- Past Elasticsearch Agent Builder Hackathon — https://www.elastic.co/blog/the-elasticsearch-agent-builder-hackathon

**Trial:** Elastic Cloud Serverless **14 days**. Will likely expire mid-judging window (Jun 22 - Jul 6). Devpost FAQ confirms expiry during judging doesn't disqualify — video + repo are what judges evaluate.

**Things people could use IMMEDIATELY:**

- Engineering Q&A agent over your team's Confluence + GitHub + Slack (Elastic connectors index, ELSER auto-embeds, agent answers + writes its enriched answer back as a permanent doc — "living documentation")
- Compliance audit agent over a regulated corpus (SOC 2 + your internal policies)
- Multi-step research agent that orchestrates 3 subagents (retrieve → analyze → cite) via Workflows

**Saturation:** 🟡 MEDIUM-HIGH. 🔴 AVOID: vector-RAG knowledge bot (30+ priors across MongoDB/Elastic/Vertex). Differentiation = the WRITE-BACK loop (most teams only read).

**Gotchas:**

- ELSER setup requires a dedicated ML node; can be slow on free tier
- Agent Builder MCP path differs from the legacy `mcp-server-elasticsearch` repo — use the Agent Builder UI endpoint
- Reference architecture blog is the canonical demo shape — diverge from it deliberately, don't accidentally rebuild it

### 🟡 Fivetran (predicted 10-25 entries)

**Judges:**

- **Elijah Davis** — Lead Solution Architect @ Fivetran. https://www.linkedin.com/in/elijahdavis/
- **Andrew Madson** — Principal DevRel @ Fivetran. https://www.linkedin.com/in/andrewmadson/ (active publisher, has personal newsletter on data engineering)

**Sponsor primitives:**

- Fivetran free trial signup — https://fivetran.com/signup
- Fivetran MCP server (open-source) — https://github.com/fivetran/fivetran-mcp
- REST API + auth — https://fivetran.com/docs/rest-api/getting-started#authentication
- API framework (Python example) — https://github.com/fivetran/api_framework
- BigQuery destination setup — https://fivetran.com/docs/destinations/bigquery/setup-guide

**Trial:** **14 days** free. Same expiry-during-judging concern as Elastic. Cite video.

**Things people could use IMMEDIATELY:**

- "Why did revenue drop in EMEA last week?" agent — pulls fresh Salesforce+Stripe+HubSpot data via Fivetran, queries BigQuery, hypothesizes causes, drills in
- Data freshness watchdog — checks Fivetran sync status across N connectors; alerts when SLO breach
- Agent-curated data quality rules — agent reads your historical warehouse, learns "what good data looks like," writes new constraint rules (NEW shape — nobody has built per agent 3 research)

**Saturation:** 🟡 MEDIUM. Probably less crowded than MongoDB/GitLab because data engineering isn't hackathon-glamorous.

**Gotchas:**

- Demo needs real BigQuery data — set up synthetic schema before the demo recording
- Fivetran trial does NOT include all connectors free — verify the demo connector is in the trial bundle

### 🔴 GitLab (predicted 30-60 entries)

**Judges:**

- **Regnard Raquedan** — Senior Solutions Architect @ GitLab. https://www.linkedin.com/in/regnard/
- **Nick Veenhof** — Director of Contributor Success @ GitLab. https://twitter.com/nickveenhof (active on "agents that ACT" thesis — see his blog posts)

**Sponsor primitives:**

- 30-day Ultimate trial (longest of all sponsors — covers full contest + judging) — https://about.gitlab.com/free-trial/
- Each trial = 24 Duo credits per user (budget for the agent)
- Custom Agents (GA) — https://docs.gitlab.com/user/duo_agent_platform/agents/custom/
- Custom Flows (Beta) — https://docs.gitlab.com/user/duo_agent_platform/flows/custom/
- AI Catalog (GA) — https://docs.gitlab.com/user/duo_agent_platform/ai_catalog/
- MCP Server (Beta) — https://docs.gitlab.com/user/gitlab_duo/model_context_protocol/mcp_server/
- **Critical:** external tools calling GitLab via MCP need a default Duo namespace (per the MCP server doc)

**Trial:** **30 days** — covers contest period + most of judging. Best trial timeline of any sponsor.

**Things people could use IMMEDIATELY:**

- Team-velocity DORA coach (cycle time + deploy freq + review latency, actively coached by an agent — NEW shape per agent 3 research, NOBODY built this in the 600+ project Feb 2026 GitLab AI Hackathon)
- Compliance gate agent — for each MR, checks SOC2/GDPR/HIPAA implications via MCP, posts inline comments
- Vulnerability triage agent — reads security scan output, looks up CVE, drafts remediation MR

**Saturation:** 🔴 HIGH. The Feb-Mar 2026 GitLab AI Hackathon ran with 600+ entries; **"Gitdefender" is the canonical winner** that anyone going GitLab will be compared to. Code-review/MR-emission agents are massively over-saturated.

**Gotchas:**

- Default Duo namespace setup required for external MCP calls
- 24 Duo credits per user means agent runs can deplete budget during demo recording
- Token cost issue — see PAIN-3 in pain-points-2026

### 🔴 MongoDB (predicted 40-80 entries — MOST CROWDED)

**Judges:**

- **Daoud Farooqi** — Partner Solutions Architect @ MongoDB. https://www.linkedin.com/in/daoudfarooqi/
- **Gaurab Aryal** — Senior PM @ MongoDB. https://www.linkedin.com/in/gaurabaryal/

**Sponsor primitives:**

- MongoDB Atlas free tier (M0) — https://www.mongodb.com/cloud/atlas/register
- `sample_mflix.embedded_movies` dataset (pre-loaded with vector embeddings) — https://www.mongodb.com/docs/atlas/sample-data/sample-mflix/#sample-mflix.embedded-movies
- MongoDB MCP server — https://www.mongodb.com/docs/mongodb-mcp-server/
- Atlas Vector Search ($vectorSearch aggregation stage) — https://www.mongodb.com/docs/atlas/atlas-vector-search/
- Voyage AI auto-embedding (Winter 2026 release) — https://www.mongodb.com/blog/post/announcing-voyage-ai-mongodb-vector-store
- 40+ MCP tools — https://github.com/mongodb-js/mongodb-mcp-server

**Trial:** Atlas M0 free tier (no expiry). Voyage AI separate API key required for auto-embedding (also has free tier).

**Things people could use IMMEDIATELY:**

- Live policy enforcement — every write to a collection checked against a vector index of "forbidden patterns" before commit (NEW shape per agent 3)
- Schema drift detective — watches collections, alerts on new fields, proposes safe migrations
- Movie/content recommendation agent (low effort — `sample_mflix.embedded_movies` is plug-and-play)

**Saturation:** 🔴 HIGHEST. Vector RAG over `sample_mflix` is the default demo. Anyone going MongoDB without a clear "I'm not RAG" angle will lose.

**Gotchas:**

- Atlas M0 has connection-pool limits — burst load during demo can fail
- Voyage AI key is SEPARATE from MongoDB account — register both

### 🟡 Dynatrace (predicted 15-30 entries)

**Judges:**

- **Sean O'Dell** — Principal Product Marketing Manager, Developer Experience @ Dynatrace. Has "rise of the developer" thesis. https://www.linkedin.com/in/seanodell/
- **Jeff Blankenburg** — Principal Developer Advocate @ Dynatrace. https://twitter.com/jeffblankenburg

**Sponsor primitives:**

- Dynatrace 15-day free trial — https://www.dynatrace.com/trial/
- Dynatrace for Agent Platform — https://www.dynatrace.com/news/blog/agent-platform-with-dynatrace/
- Dynatrace for Gemini Enterprise — one-click Marketplace deploy — https://console.cloud.google.com/marketplace
- **AI Coding Agent Monitoring** (passive OTel for Claude Code / Gemini CLI / Codex CLI / OpenCode / GitHub Copilot SDK) — https://www.dynatrace.com/news/blog/coding-agent-observability/
- Instrumentation Examples (GitHub) — https://github.com/dynatrace-extensions/dt-extensions-ai-observability
- Bindplane Google Edition — free OTel pipeline — https://bindplane.com/google-edition/

**Trial:** **15 days** free. Same expiry-during-judging concern as Elastic/Fivetran.

**Things people could use IMMEDIATELY:**

- AI Coding Agent Budget Guardrail — observes Claude Code / Cursor / Copilot usage via Dynatrace OTel, intervenes (kill/downgrade/re-auth) on runaway sessions BEFORE the $4.2K weekend bill (this is the Microsoft-revoking-Claude-Code pain category per pain points research; NEW shape per agent 3)
- K8s/cluster whisperer — agent observes cluster via Dynatrace, diagnoses red alerts, suggests kubectl
- SLA sentinel for regulated workloads — agent monitors p95/p99 + drafts customer-facing comms on breach

**Saturation:** 🟡 MEDIUM-LOW. Dynatrace is brand-new to this hackathon (zero priors). Could be the lowest-competition track IF Arize crowds.

**Gotchas:**

- Dynatrace is the most complex SaaS to set up correctly
- AI Coding Agent Monitoring is genuinely novel — judges may not have seen demos of it before, which cuts both ways (high impact possible / high explanation cost)

---

## Cross-cutting findings (the empirical lessons)

### Top 5 production pain points (cite-able)

Source: `brainstorm/08-current-pain-points-2026.md`

1. **Catastrophic unsafe action** — Replit agent deleted prod DB + faked 4K records during freeze (https://x.com/jasonlk/status/1946069562723897802) · Cursor 2.1 modifies unrelated files · Claude Code used to breach 9 Mexican gov agencies (195M records leaked)
2. **Silent failure** — "200 OK with wrong output is the most dangerous response in production." Only 62% of orgs can inspect step-level despite 89% claiming observability (https://arize.com/blog/state-of-ai-engineering-2026)
3. **Token-cost runaway** — Uber burned ENTIRE 2026 AI coding budget in 4 months · **Microsoft REVOKING Claude Code from employees on 2026-06-30** · $500M Claude spend incident at unnamed enterprise (https://news.ycombinator.com/item?id=39842042)
4. **Tool-call hallucination** — AgentHallu benchmark shows top models at 11.6% accuracy on tool-use hallucination localization
5. **Vendor quality regressions** — Anthropic April 2026 postmortem documents 6 weeks of complaints traced to 3 unrelated changes; customers acted as QA (https://www.anthropic.com/news/april-2026-postmortem)

**Surprise:** Authentication (OAuth/2FA) is the **#1 deployment-failure category** — 62% of 847-deployment study. Hallucination is what people TALK about; auth is what kills deployments.

### Top winning hackathon patterns 2025-2026

Source: `brainstorm/09-hackathon-winner-patterns-2025-2026.md` (30 named winners with URLs)

| Pattern                                         | Frequency                                     | Example winner                                                                   |
| ----------------------------------------------- | --------------------------------------------- | -------------------------------------------------------------------------------- |
| Solo or 2-person team                           | 13/30                                         | zenith.chat (Anthropic Forum Ventures, 8h build, 10-month pre-tuned skill stack) |
| Sponsor primitive at CORE, not bolted-on        | 11/30                                         | Vigil AI plugged directly into Bank of Anthos                                    |
| Domain-vertical with NAMED geography/regulation | 10/30                                         | CA ADU permits, Ugandan roads, Brussels cardiology, IRS Form 1040, SOC 2         |
| Multi-agent with NAMED human roles              | 9/30                                          | TransactionMonitor + InvestigationAgent + Orchestrator (vs "agent-1/agent-2")    |
| Demo-as-pitch / viral 30s loop                  | 6/30                                          | GibberLink (10M+ X views), RoboChef (physical robot demo)                        |
| Quantified result headline                      | 6/30 (but EVERY Bedrock/Microsoft top winner) | "100% on Form 1040", "<60 seconds", "131 dupes / 1,010 records / 10s"            |
| Closed-loop self-improvement                    | 5/30 (every observability-sponsor placement)  | —                                                                                |

**Biggest 2026 signal:** Non-engineers are winning. The Anthropic Built-with-Opus-4.6 hackathon (Feb 2026) was won by **a lawyer, a Ugandan road technician, a Brussels cardiologist, and an electronic musician**. They built tools they themselves needed. https://claude.com/blog/meet-the-winners-of-our-built-with-opus-4-6-claude-code-hackathon

### Vertical demand with named companies + dates

Source: `brainstorm/11-vertical-agent-gaps.md` (852 lines, every claim linked)

| Vertical                         | Demand signal                                                                                                                                                                                     | Named companies                                                                                                                          | Source                                                                                         |
| -------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| **Healthcare**                   | 10+ named agent-engineer JDs · CMS prior-auth rule effective Jan 1 2026 (regulatory forcing function)                                                                                             | Hippocratic AI ($3.5B / 1000+ prod use cases), Cadence Solutions, IMO Health, Cohere Health, Sirona, Natera, Sword, Ada Health, Medeloop | https://hippocraticai.com · CMS-9088-F                                                         |
| **Legal**                        | Harvey $200M Series E @ $11B valuation (Mar 2026) · 3.9x YoY ARR · Hiring "Legal Engineers" in Dallas/EMEA/Toronto                                                                                | Harvey, Legora ($5.55B), Ironclad (Assistant launched Mar 2026), Spellbook                                                               | https://www.harvey.ai/blog/harvey-raises-at-dollar11-billion-valuation                         |
| **Financial Services**           | Sierra AI $15B (May 2026 Series E, $200M ARR) · FIS+Anthropic AML agent shipping 2H 2026 to BMO + Amalgamated Bank                                                                                | Sierra AI, Decagon ($4.5B), Spektr ($20M NEA-led)                                                                                        | https://siliconangle.com/2026/05/04/ai-agent-startup-sierra-valued-15b-new-950m-funding-round/ |
| **Insurance (MOST UNDERSERVED)** | SIU fraud agents = **fastest payback of ANY agentic-AI category at 6-9 months** · 400K worker attrition expected by 2026 · No $1B+ incumbent · P&C insurtech funding $1.13B in Q1 2025 (+90% QoQ) | Avallon ($4.6M YC seed), Pasito, Bevaya, Corgi, Stream — all small                                                                       | https://www.businesswire.com/news/home/20251106838494/en/Avallon-Secures-$4.6-Million          |

### Saturation map — what to AVOID

Source: `brainstorm/12-saturation-map.md`

- 🔴 **Code-review / security-fix MR-emission agent** — Gitdefender + 600+ others on the GitLab AI Hackathon (Feb-Mar 2026). https://about.gitlab.com/blog/gitlab-ai-hackathon-2026-meet-the-winners/
- 🔴 **Vector-RAG knowledge bot** — 30+ priors across MongoDB/Elastic/Vertex galleries
- 🔴 **Agent observability/tracing dashboard** — 15+ priors. Great Agent Hack "Glass Box" track had 17 such projects. https://hai-great-agent-hack-2025.devpost.com/project-gallery
- 🔴 **Generic prompt-injection / jailbreak red-team agent** — RedBot ships 140+ jailbreak templates already

### Whitespace (NEW shapes nobody has built per agent 3 + agent 5)

- **Closed-loop chaos-FOR-agents at the agent layer** (Voltaros does infra-chaos for GKE pods only — agent-layer is empty in priors)
- **Agent that emits an MR against its OWN prompt/tool config** (recursive self-patching — Gitdefender does human-code only)
- **Team-velocity DORA coach** (zero velocity-coach agents in 600+ GitLab projects)
- **AI Coding Agent Budget Guardrail** (Dynatrace passive monitoring exists; ACTIVE intervention agent does not)
- **Agent-curated data quality rules** (Fivetran MCP capability nobody's exercised)
- **Live policy enforcement via $vectorSearch** (MongoDB capability nobody's exercised)

---

## "Immediate utility" filter — Abu's bias check

For each track, here's what would pass the "real person can use this within 7 days" filter (vs framework/tool for engineers):

| Track     | Immediate-utility build                                                                                                                                                                                    | Who uses it on day 1                                                                    |
| --------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| Arize     | **Customer-support agent that learns from past escalations** (queries own Phoenix traces via MCP to find similar past tickets, applies their resolution shape) — closed-loop self-improvement IS the wedge | Support team lead at any SaaS — solves the "new hire doesn't know the playbook" problem |
| Arize     | **Prior-auth claims agent with audit trail** — every decision is annotated to Phoenix; compliance can audit by querying traces                                                                             | Compliance officer at a payer (Cohere Health, Hippocratic AI buyers)                    |
| Elastic   | **Living documentation agent** for engineering teams (Confluence + GitHub + Slack ingested; agent answers + WRITES back enriched answers)                                                                  | Engineering manager at any 50+ eng team                                                 |
| Fivetran  | **Revenue diagnostician** — "why did EMEA drop?" Pulls fresh Salesforce/Stripe/HubSpot, queries BigQuery, hypothesizes, drills in                                                                          | Head of Revenue Ops at any SaaS                                                         |
| GitLab    | **Compliance gate agent** — per-MR SOC2/GDPR/HIPAA check, inline comments                                                                                                                                  | CISO / compliance lead at any regulated org                                             |
| MongoDB   | **Live policy enforcement on writes** — `$vectorSearch` against forbidden-patterns index before commit                                                                                                     | Platform engineer at any data-sensitive org                                             |
| Dynatrace | **AI Coding Agent Budget Guardrail** — observes Claude Code / Cursor usage, intervenes on runaway sessions BEFORE the $4.2K bill                                                                           | Eng manager at any team where 5+ devs use AI tools                                      |

**Pattern:** The named persona on the right is the winner-pattern test. If you can't name a real person who would use this within 7 days, the wedge fails the immediate-utility filter.

---

## Open decisions before locking the wedge

1. **Track** — Arize is structurally validated AND lowest-competition AND the sponsor language ("agents that use their own observability data to improve over time") is literal. Insurance / healthcare verticals are best-paying but don't map cleanly to a single sponsor. **Default: Arize.** Reconsider if you want a different angle.
2. **Demo target** — If Arize: pick a regulated vertical with synthetic public data (healthcare prior-auth via MIMIC-IV / Synthea, financial trade reconciliation, insurance fraud triage). Not generic customer support.
3. **Pitch frame** — Loop > attacks (saturation map). Product > tool (immediate-utility filter). Named persona > "any user."
4. **Quantified headline** — Required per winner pattern. Examples to aim for: "Hardens prior-auth agent against 4 fault classes in 90 seconds, reducing silent-denial rate from X% to Y%."
5. **Scope** — Drop Tier 2/3 cross-framework from the SUBMITTED demo. Keep them in the README architecture footnote. Winners narrow, not broaden.

---

## What this primer DOES NOT cover (next research if you want it)

- **Ecosystem-refactor candidates** — winning projects from other ecosystems (ETHGlobal corpus of 17,180 projects, DoraHacks AI tracks, HackQuest agent tracks) that could be ported to Google Cloud Rapid Agent. Your `sahil-ecosystem-refactor` skill is built for exactly this. **You've said 3 of 4 of your wins came from rebuilding.** Worth running before lock-in.
- **Track-specific judge alpha** — what Richard Young / Anish Mathur / Andrew Madson / Nick Veenhof / Daoud Farooqi / Sean O'Dell have personally said on Twitter / their blogs about agents in 2026. Could surface what each judge actively WANTS to see.
- **Real Devpost gallery** — gallery still unpublished as of 2026-06-04. Worth re-checking after 2026-06-12 (post-deadline) to verify track distribution prediction.

---

## Open verifications (time-sensitive)

1. **GCP $100 credit form submitted today (2026-06-04)?** — deadline closes today. Verify it shows in your billing account, not just that account exists.
2. **W-8BEN ready** — non-US winner requirement. 60-day disbursement window post-Required-Forms.
3. **Nigerian bank can receive international USD wire** — some account types gate this; verify with your bank.
4. **GitHub Settings → About → "License" field** auto-detected as "Apache License 2.0"? — required for OSI-license detectability per rules §12.
