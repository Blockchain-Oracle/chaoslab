# CONTEXT — Google Cloud Rapid Agent Hackathon

> **If you are an agent picking up this folder, this is the file you load FIRST.**
> Everything else is a deep-dive sub-file. This is the orientation document.

**Research compiled:** 2026-06-02 (today)
**Submission deadline:** 2026-06-11, 2:00 PM Pacific Time (**9 days from compile date**)
**Author of research:** prior session (multi-agent parallel research run via `sahil-hackathon-research` skill)
**Compiled for:** Abu (ajweb3dev@gmail.com), blockchain-native solo dev, zero prior Google Cloud / agent-platform experience

**Addendum (2026-06-02, same session):** After initial research, the [Holt Skinner / Google Cloud DevRel video](https://youtu.be/j8qW5poBkEU) and its [companion README directory](https://github.com/Google-Cloud-AI/agent-platform) were processed. They corrected several earlier findings and added significant new context. New canonical file: **`02b-gemini-enterprise-agent-platform.md`** (the 4-phase lifecycle map of the entire platform). Two new refs files: `refs/agent-platform-readme.md` (Google's master link directory) and `refs/official-links.md` (resolved short-links). **Key correction:** Gemini 3.5 Flash is the current default model, not 2.5 Flash as `02a-google-cloud-stack.md` §4 originally documented.

**Brainstorm + Architecture + Context phases complete (2026-06-02):** Three subfolders below this file:

- `brainstorm/` (8 files, ~4,500 lines) — wedge selection pipeline. Final pick: **W1 ChaosLab for Agents (Arize track)**. See `brainstorm/06-idea-rankings.md` + `brainstorm/07-novelty-gate.md`.
- `architecture/` (7 files, ~5,800 lines) — EXPLORATORY build research. **Banner on `architecture/00-synthesis.md` says decisions are PRELIMINARY, not locked.** Treat as data.
- `context/` (7 files, ~9,600 lines) — pure domain knowledge corpus. NO opinions, NO "ChaosLab should..." statements. Downstream agents read this to make their own architectural decisions. **Start at `context/00-README.md`.**

**Total research corpus: ~24,000 lines across 22 files.** Coverage: hackathon rules + Google platform + 6 partner deep-dives + wedge selection + exploratory architecture + agent shapes taxonomy + production failures + red-team product internals + cross-framework instrumentation + agent interfaces + open standards.

**The new master entrypoint for downstream agents is `READING-ORDER.md`** at the top of this folder — it walks through the full corpus in 5 phases (orient → wedge → domain knowledge → technical specifics → exploratory arch → tactical inputs).

**RAT runbook was patched (Step 3)** after architecture research discovered Phoenix MCP server lacks `run-experiment` tool. Step 3 now validates the custom Python SDK FunctionTool wrap path. See `RAT-runbook.md` Step 3.

---

## 1. What this hackathon is (one paragraph)

A Google + 6-partner hackathon hosted on Devpost (`rapid-agent.devpost.com`) asking solo devs and teams to build a **functional AI agent** that uses **Gemini** as the brain, is built inside **Google Cloud Agent Builder** (visual Studio UI _or_ code-first ADK / Agent Runtime / Cloud Run), and integrates **at least one partner's MCP server** to give the agent "superpowers" — tools and data sources beyond what Gemini ships with. The agent must **take real actions** ("move beyond chat"), not just answer questions. Prize structure is six identical $10K buckets (one per partner: Arize, Elastic, Fivetran, GitLab, MongoDB, Dynatrace), so you compete only within your chosen track, not across the whole field. Total prize pool $60K across 18 winners.

---

## 2. The target track decision

**Primary recommendation: 🟢 Arize.**

Reasoning (full version in `06-hidden-field.md` and `07-pre-commit-checklist.md`):

- **Lane-EV math:** Devpost gallery is hidden until post-deadline, so saturation is inferred. Arize is predicted GREEN (least crowded) because (a) Phoenix is observability — not the lazy default for "agent that does X", (b) code-first ADK is required (no visual-builder shortcut), (c) the concept-ladder filters out unsophisticated entries. Predicted ~3× win-odds vs the predicted-RED tracks (MongoDB, GitLab) at the same $10K bucket payout.
- **Personal fit (Abu):** he already uses AI agent coding tools daily, so an agent that **observes / grades / improves other agents** is a recursive angle that's genuine, not contrived. The Phoenix MCP server lets the built agent introspect its own execution.
- **No trial squeeze:** Phoenix Cloud is free forever; no countdown into the judging window. Elastic/Fivetran/Dynatrace all have 14-15 day trial limits that conflict with the Jun 22 – Jul 6 judging window.
- **Built-in Google ADK auto-instrumentation:** OpenInference (Arize's open-source instrumentation library) instruments Google ADK out of the box — minimal wiring to start emitting traces.

**Backup if Arize feels too cerebral after reading `partner-arize.md`:** **🟡 Fivetran** — best mental-model match for blockchain devs (Fivetran connectors map cleanly to multi-chain indexers Abu already knows), cleanest "before/after" demo arc. Cost: pay the 14-day trial-squeeze tax by activating the trial as close to the June 11 deadline as possible.

**Explicit non-recommendations** for Abu's profile:

- ❌ MongoDB / GitLab — predicted RED saturation, lazy-default tracks for solo devs.
- ❌ Elastic — high ceiling but 14-day trial squeeze + Kibana/ES|QL learning curve = too much new surface in 9 days.
- ❌ Dynatrace — best lane-EV but highest operational floor; needs OneAgent collecting real telemetry from day 1.

---

## 3. Verified facts (high-confidence, sourced)

| Fact                                     | Value                                                                                                       | Source                                                                              |
| ---------------------------------------- | ----------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| Submission deadline                      | **2026-06-11, 2:00 PM PT**                                                                                  | Devpost rules §5                                                                    |
| Judging window                           | 2026-06-22 → 2026-07-06                                                                                     | Rules §8                                                                            |
| Winner notification                      | ~2026-07-07                                                                                                 | Rules §8                                                                            |
| $100 GCP credit form deadline            | **2026-06-04** (🔴 2 DAYS)                                                                                  | Devpost FAQ                                                                         |
| Prize per bucket                         | $5K / $3K / $2K (1st / 2nd / 3rd)                                                                           | Rules §9                                                                            |
| Total prize pool                         | $60,000 across 18 winners                                                                                   | Rules §9                                                                            |
| Required stack                           | Gemini + Agent Builder (visual or ADK code-first) + ≥1 partner MCP server                                   | Rules §7B                                                                           |
| Banned in submission                     | Claude/Cursor/Copilot/non-Google AI as runtime deps; LangChain/LangGraph/LlamaIndex as primary orchestrator | Rules §7B + FAQ                                                                     |
| Banned in submission? Dev workflow tools | NOT banned — only banned in submitted code/repo                                                             | FAQ (verified)                                                                      |
| Gemini 2.5 Flash pricing                 | $0.30 / 1M input tok, $2.50 / 1M output tok _(may be stale — re-verify, 3.x is current)_                    | `02a-google-cloud-stack.md` §4                                                      |
| Gemini 2.5 Pro pricing                   | $1.25 / 1M input tok, $10 / 1M output tok _(may be stale — re-verify, 3.x is current)_                      | `02a-google-cloud-stack.md` §4                                                      |
| Gemini 2.0 Flash status                  | **DEPRECATED 2026-06-01**                                                                                   | `02a-google-cloud-stack.md` §4                                                      |
| **Current default model**                | **Gemini 3.5 Flash** (replaces 2.5 Flash as the default)                                                    | Google's official README (verified 2026-06-02, see `refs/agent-platform-readme.md`) |
| Current Pro model                        | Gemini 3.1 Pro                                                                                              | Google's official README                                                            |
| Cheapest model                           | Gemini 3.1 Flash-Lite                                                                                       | Google's official README                                                            |
| Pricing for 3.x                          | **NEEDS VERIFICATION** at https://ai.google.dev/gemini-api/docs/pricing before locking choice               | —                                                                                   |
| Vertex AI rebrand date                   | 2026-04-22 (Google Cloud Next) — now "Gemini Enterprise Agent Platform"                                     | `02a-google-cloud-stack.md` §1                                                      |
| Agent Builder in console today           | Appears as **"Agent Platform → Studio"**                                                                    | `02a-google-cloud-stack.md` §1                                                      |
| Total registered participants            | ~12,582 as of 2026-06-02                                                                                    | `03-project-gallery.md`                                                             |
| Predicted final submission count         | ~500-1,000 (base-rate from ADK Hackathon)                                                                   | `03-project-gallery.md`                                                             |

---

## 4. What exists in the field

**Live competitor count: unknown.** Devpost gallery is unpublished until after the 2026-06-11 deadline. We have NO direct intel on what other entrants are building.

**Inferred competitive shape** (`06-hidden-field.md`):

- ~12,582 participants registered
- ~500-1,000 expected submissions
- Predicted per-track distribution heavily skewed toward MongoDB and GitLab (lowest-friction)
- Predicted least-crowded: Arize and Dynatrace

**Past Google AI/agent hackathon winner patterns** (`05-prior-winners.md` — high-confidence priors from ADK Hackathon, Vertex AI Hackathon, Gemini Developer Competition, AI in Action):

1. **Hyper-specific real-world domain.** "Agent for radiology workflows" wins, "general productivity agent" loses.
2. **3+ step autonomous workflow producing a tangible artifact.** Not Q&A. Agent does something the user couldn't easily do themselves.
3. **Demo video shows the agent ACTING, not the founder narrating.** Camera on the agent's screen, not the team selfie.
4. **Production-feel polish at hackathon scope.** A small, finished thing beats a half-built sprawling thing.

Winners universally use **multiple Google Cloud services together** (e.g., ADK + Agent Engine + Cloud Run + Vertex AI), not just a single service.

---

## 5. Available primitives (what's actually live and usable)

### Google Cloud side

- **Agent Development Kit (ADK)** for Python — code-first, MCPToolset class wires partner MCP servers as agent tools (`02a-google-cloud-stack.md` §3 + §7)
- **Agent Runtime** — managed runtime for ADK-built agents
- **Cloud Run** — general containerized hosting (Streamlit + ADK demo URL fastest path)
- **Gemini 2.5 Flash** (default) or 2.5 Pro (harder reasoning) — both available via Vertex AI
- **Secret Manager** — for partner API keys
- **$100 promotional credit** — claim by 2026-06-04. Covers Vertex AI, Cloud Run, Agent Builder, Secret Manager. Does NOT cover partner services unless subscribed via GCP Marketplace.

### Partner-side primitives (`partner-*.md`)

| Partner       | MCP server                                                          | Free-tier path                                                        | Code-first required?                       |
| ------------- | ------------------------------------------------------------------- | --------------------------------------------------------------------- | ------------------------------------------ |
| **Arize**     | `@arizeai/phoenix-mcp` (npx)                                        | Phoenix Cloud at app.phoenix.arize.com                                | ✅ YES (Arize requires code-owned runtime) |
| **Elastic**   | Agent Builder MCP endpoint in Kibana (ES 9.2+)                      | Elastic Cloud 14-day trial via cloud.elastic.co                       | No                                         |
| **Fivetran**  | github.com/fivetran/fivetran-mcp (official)                         | 14-day Fivetran trial                                                 | No                                         |
| **GitLab**    | `gitlab.com/api/v4/mcp` (official — REQUIRED for evaluation credit) | Trial account works (no Premium needed)                               | No                                         |
| **MongoDB**   | github.com/mongodb-js/mongodb-mcp-server                            | Atlas free tier (subscribe via GCP Marketplace for clean credit draw) | No                                         |
| **Dynatrace** | Dynatrace MCP (official)                                            | 15-day trial; needs OneAgent for real telemetry                       | No                                         |

### MCP protocol primitives (`mcp-primer.md`)

- Two transports today: **stdio** (local subprocess) and **Streamable HTTP** (remote, replacing deprecated HTTP+SSE)
- ADK's `MCPToolset` handles the full handshake — minimal wiring
- All 6 partner MCP servers are production-ready (status verified per partner file)

---

## 6. Three actions Abu must take in the next 48 hours

1. **🔴 Claim the $100 Google Cloud promo credit** via the form at the Devpost Resources page — deadline 2026-06-04 (2 days).
2. **Read in order:** `02a-google-cloud-stack.md` (end to end) → `mcp-primer.md` → `partner-arize.md` (or his chosen track's partner file). Skim the other partner files.
3. **Complete `07-pre-commit-checklist.md` Q1-Q7 on paper.** Most importantly Q2 — the wedge sentence. Do not write code until Q1-Q7 all have sharp answers.

---

## 7. Open questions / [UNVERIFIED]

Things research couldn't confirm and that Abu (or a future agent) should re-check:

| Question                                                                       | Why it matters                                              | How to verify                                                    |
| ------------------------------------------------------------------------------ | ----------------------------------------------------------- | ---------------------------------------------------------------- |
| Actual per-track submission distribution after 2026-06-11                      | Validates the saturation prediction in `06-hidden-field.md` | Re-scrape Devpost gallery post-deadline                          |
| Whether GitLab MCP needs Premium/Ultimate or trial-tier suffices               | Could change Q1 track decision if GitLab gated              | Sign up at gitlab.com trial; try `https://gitlab.com/api/v4/mcp` |
| Exact ADK MCP `streamable_http` keep-alive behavior under Cloud Run cold start | Critical for demo URL reliability                           | Test locally first; instrument with Phoenix tracing              |
| Phoenix MCP tool manifest (definitive list of tools exposed)                   | Drives `07-pre-commit-checklist.md` Q4 answer               | `npx @arizeai/phoenix-mcp --list-tools` (or equivalent)          |
| Whether AI in Action 2025 winners published their repos publicly               | Direct reference for what Google's judging culture rewards  | Scrape aiinaction.devpost.com gallery                            |
| Vertex AI Hackathon 2nd-place project name (`05-prior-winners.md` UNVERIFIED)  | Reference pattern                                           | Devpost search                                                   |

---

## 8. File index (what lives where)

| File                                                               | Purpose                                                                                                                                        | When to load                                                             |
| ------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| **`CONTEXT.md`** (this file)                                       | Master entrypoint, synthesis                                                                                                                   | Always first                                                             |
| `00-overview.md`                                                   | Human-readable one-page brief                                                                                                                  | For humans / quick share                                                 |
| `01-prizes-tracks.md`                                              | Full prize / judging mechanics                                                                                                                 | Strategy questions                                                       |
| `02a-google-cloud-stack.md`                                        | Google Cloud agent stack rosetta stone, ADK code, MCP integration patterns                                                                     | Before writing any agent code                                            |
| **`02b-gemini-enterprise-agent-platform.md`**                      | **The 4-phase lifecycle map (Build/Scale/Govern/Optimize) of EVERY platform component. Includes the 5 open protocols (MCP/A2A/A2UI/AP2/UCP).** | **READ FIRST after `00-overview.md` — most platform-context-dense file** |
| `mcp-primer.md`                                                    | MCP protocol primer + ADK integration                                                                                                          | Before wiring partner MCP server                                         |
| `partner-arize.md`                                                 | Arize / Phoenix MCP deep dive                                                                                                                  | If Arize track                                                           |
| `partner-elastic.md`                                               | Elastic MCP deep dive                                                                                                                          | If Elastic track                                                         |
| `partner-fivetran.md`                                              | Fivetran MCP deep dive                                                                                                                         | If Fivetran track                                                        |
| `partner-gitlab.md`                                                | GitLab MCP deep dive                                                                                                                           | If GitLab track                                                          |
| `partner-mongodb.md`                                               | MongoDB MCP deep dive                                                                                                                          | If MongoDB track                                                         |
| `partner-dynatrace.md`                                             | Dynatrace MCP deep dive                                                                                                                        | If Dynatrace track                                                       |
| `03-project-gallery.md`                                            | Devpost gallery state (pre-deadline = empty)                                                                                                   | Lane saturation reality-check                                            |
| `05-prior-winners.md`                                              | Prior Google AI/agent hackathon winner patterns                                                                                                | Wedge ideation, video planning                                           |
| `06-hidden-field.md`                                               | Per-track saturation verdict + lane recommendation                                                                                             | Track decision                                                           |
| `07-pre-commit-checklist.md`                                       | Q1-Q7 gate before writing code                                                                                                                 | After picking a track, before any coding                                 |
| `refs/agent-platform-readme.md`                                    | Google's official master link directory for every platform component                                                                           | Definitive "where does X live?" lookup                                   |
| `refs/official-links.md`                                           | Resolved goo.gle short-links + Abu's most-used URL card                                                                                        | Quick reference                                                          |
| `refs/holt-skinner-gemini-enterprise-agent-platform-transcript.md` | Full transcript of the canonical platform overview video                                                                                       | Source-of-truth for `02b`                                                |

---

## 9. Hand-off note for the next session

When Abu returns to this folder:

- **If he hasn't picked a track yet:** start at `00-overview.md` → `02b-gemini-enterprise-agent-platform.md` (so he gets the platform context) → `06-hidden-field.md` → `07-pre-commit-checklist.md`. Pick a track. Lock the wedge sentence (Q2). Then proceed.
- **If he has picked a track:** start at `partner-<track>.md` → `02b-gemini-enterprise-agent-platform.md` (decision matrix at the bottom on which components to actually use) → `02a-google-cloud-stack.md` (code patterns) → `mcp-primer.md`. Then start scaffolding the ADK agent.
- **If he's lost on terminology:** `02a-google-cloud-stack.md` §1 OR `02b-gemini-enterprise-agent-platform.md` §"Naming note" (both have the rosetta stone — 02b has more aliases like Agent Engine → Agent Runtime).
- **If a coding agent picks this up:** the file you need is `02a-google-cloud-stack.md` §3 (ADK code) + §7 (MCP integration) + the relevant `partner-<track>.md` + `02b-gemini-enterprise-agent-platform.md` "Decision matrix" (which components to wire). The `refs/official-links.md` has the most-used URLs collected.

**Downstream skills that consume this folder:**

- `first-principles-decomposer` → load CONTEXT.md, decompose the partner's actual capabilities to fundamentals before wedge ideation
- `sahil-idea-generator` → use CONTEXT.md as context for ranked wedge ideas constrained to the chosen track
- `sahil-novelty-gate` → check ideas against ETHGlobal/Devpost prior projects to confirm not duplicate
- `sahil-spec-writer` → load CONTEXT.md + the wedge to produce the PRD/architecture/stories spec set
- `sahil-hackathon-orchestrator` → fires after wedge approval, builds repo + issues + dispatches coding agent

This folder persists. Do not delete even after submission — it informs future Google Cloud agent hackathons.
