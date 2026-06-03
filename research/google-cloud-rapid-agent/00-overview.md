# 00 — Overview: Google Cloud Rapid Agent Hackathon

**One-page everything.** If Abu reads only one file, read this. Then go to `CONTEXT.md` for the agent-consumable synthesis.

---

## What this is

A **Google + 6-partner hackathon on Devpost** asking you to build a functional AI agent that:

1. Uses **Gemini** as the brain
2. Is built **inside Google Cloud's Agent Builder ecosystem** (visual Studio console _or_ code-first ADK / Agent Runtime / Cloud Run)
3. Integrates **at least one partner's MCP server** to give the agent "superpowers" (the partner provides tools/data the agent calls)
4. Solves a real-world task — "move beyond chat, take action"

It's a **partner-bucketed** prize structure: 6 separate prize pools, one per partner. You compete only against other entrants in your chosen partner's bucket, not across the whole field.

---

## Key dates (today: 2026-06-02)

| Date                        | Event                                            | Status                                                 |
| --------------------------- | ------------------------------------------------ | ------------------------------------------------------ |
| **2026-05-05**              | Contest opened                                   | ✅ Past                                                |
| **2026-06-04**              | $100 Google Cloud credit request form **closes** | 🔴 **2 days** — claim NOW if you don't already have it |
| **2026-06-11, 2:00 PM PT**  | **Submission deadline**                          | 🟡 **9 days**                                          |
| **2026-06-22 → 2026-07-06** | Judging window                                   | —                                                      |
| **2026-07-07**              | Potential winners notified                       | —                                                      |
| **2026-07-13**              | Winner-list request window opens                 | —                                                      |

`Source: Devpost rules §5, §6`

---

## What you build

A submission has **5 deliverables**:

1. **Hosted Project URL** — judges click it and use the agent. No-login sandbox with sample data is acceptable.
2. **Public open-source GitHub repo** — with a detectable open-source license file (visible in the "About" panel). New code only, written during May 5 – June 11.
3. **3-minute demo video** — uploaded to YouTube/Vimeo, public, English (or English subtitles), shows the agent functioning end-to-end.
4. **Devpost text description** — features, tech stack, data sources, learnings.
5. **Track selection** — pick exactly one of Arize / Elastic / Fivetran / GitLab / MongoDB / Dynatrace per submission.

Multiple submissions allowed if each is "unique and substantially different." Each submission wins at most one prize.

---

## The required stack (non-negotiable)

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│   Gemini model  ─────►  Agent Builder ecosystem  ─────►  Partner MCP│
│   (2.5 Flash /         (Studio console OR              (one of the  │
│    2.5 Pro)             ADK / Agent Runtime /           6 partners) │
│                         Cloud Run)                                  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

- **Visual path:** Google Cloud Agent Builder UI (now branded "Agent Platform → Studio" in the console) — drag-and-drop, low-code.
- **Code-first path:** Agent Development Kit (ADK), a Python SDK. Deploy to Agent Runtime or Cloud Run. **The Arize track REQUIRES this path** because Arize tracing needs a code-owned runtime.

**Banned:** LangChain/LangGraph/LlamaIndex as the _primary_ orchestrator. Claude/Cursor/Copilot/non-Google AI services _in the submitted code_ (per Section 7B). They are NOT banned in your dev workflow — see `02a-google-cloud-stack.md` §11 for clarification.

---

## Prize structure ($60K total)

Six identical buckets, one per partner:

| Place  | Cash   | Bonus                  |
| ------ | ------ | ---------------------- |
| 🥇 1st | $5,000 | Social-media promotion |
| 🥈 2nd | $3,000 | —                      |
| 🥉 3rd | $2,000 | —                      |

Per bucket: $10K. Across 6 buckets: $60K. You pick _one_ track per submission.

---

## The 6 partners (one-line each — full details in `partner-*.md`)

| Partner       | What they do                 | MCP best for                                                      | Trial gotcha                                                                    |
| ------------- | ---------------------------- | ----------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| **Arize**     | LLM observability (Phoenix)  | Agent self-debug, eval, trace replay                              | None — free Phoenix Cloud. **Code-first runtime required.**                     |
| **Elastic**   | Search + vector store        | Hybrid (semantic + keyword + filter) search over a private corpus | 14-day trial, no extension                                                      |
| **Fivetran**  | Managed data pipelines (ELT) | Unify many SaaS sources into BigQuery, agent reasons over it      | 14-day trial, no extension                                                      |
| **GitLab**    | DevOps platform              | CI/CD automation, MR/issue triage, repo intelligence              | Trial sufficient. Must use **official** MCP server.                             |
| **MongoDB**   | Document DB + vector search  | Doc store + `$vectorSearch` + Atlas Search in one query           | Atlas free tier works. **Subscribe via GCP Marketplace** for clean credit draw. |
| **Dynatrace** | APM / observability          | SRE co-pilot, telemetry-aware agent, RCA automation               | 15-day trial. Need real telemetry data — install OneAgent early.                |

---

## Judging (equal-weighted, Stage 2)

1. **Technological Implementation** — does the Google Cloud + Partner integration show real software craft?
2. **Design** — UX, demo polish, end-to-end thought
3. **Potential Impact** — could this matter for real users?
4. **Quality of the Idea** — creative, novel, not generic

Stage 1 is pass/fail viability screen — meets requirements + reasonably uses the required stack.

---

## Recommended track for Abu (TL;DR — full reasoning in `07-pre-commit-checklist.md`)

**Primary: Arize** — predicted least-crowded bucket; recursive "agent that observes/grades agents" angle aligns with Abu's already-uses-AI-coding workflow; no trial clock; same $10K payout as crowded buckets. Code-first ADK + Phoenix MCP.

**Backup: MongoDB** — lowest friction (doc-store mental model ~ EVM event logs); 40+ MCP tools; vector-search is a clean demo flex. BUT predicted RED saturation.

Skip first-pass: Elastic and Fivetran (trial squeeze risk into July judging window); Dynatrace (highest concept ladder, needs real telemetry pipeline).

---

## Three actions Abu should take in the next 48 hours

1. **Claim the $100 Google Cloud credit** at the request form (form deadline **2026-06-04** — see Devpost resources page).
2. **Read `02a-google-cloud-stack.md`** end-to-end, then the partner file for the track he picks (`partner-arize.md` recommended).
3. **Pick the track + lock the wedge** using `07-pre-commit-checklist.md`. Don't write code until those answers exist on paper.

---

## File index

| File                         | Purpose                                                                        |
| ---------------------------- | ------------------------------------------------------------------------------ |
| `CONTEXT.md`                 | **Master agent entrypoint.** Load first if any downstream agent picks this up. |
| `00-overview.md`             | This file. Human-readable one-pager.                                           |
| `01-prizes-tracks.md`        | Full prize + judging breakdown                                                 |
| `02a-google-cloud-stack.md`  | Google Cloud agent stack rosetta stone + ADK + MCP integration code            |
| `mcp-primer.md`              | Model Context Protocol — what, why, how it wires into ADK                      |
| `partner-arize.md`           | Arize / Phoenix MCP deep dive                                                  |
| `partner-elastic.md`         | Elastic MCP deep dive                                                          |
| `partner-fivetran.md`        | Fivetran MCP deep dive                                                         |
| `partner-gitlab.md`          | GitLab MCP deep dive                                                           |
| `partner-mongodb.md`         | MongoDB / Atlas MCP deep dive                                                  |
| `partner-dynatrace.md`       | Dynatrace MCP deep dive                                                        |
| `03-project-gallery.md`      | Devpost gallery scrape + participant count                                     |
| `05-prior-winners.md`        | Prior Google AI/agent hackathon winner patterns                                |
| `06-hidden-field.md`         | Track saturation verdict + lane recommendation                                 |
| `07-pre-commit-checklist.md` | 7-question pre-build gate + Abu-specific recommendation                        |
