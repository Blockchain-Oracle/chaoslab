# AI Trust Auditor — The Plain-English Plan

> Written 2026-06-04 after 10 parallel research agents (5 fresh-data + 5 Direction-A deep-dive). Every claim has a source file under `research/google-cloud-rapid-agent/brainstorm/` or `refs/`. Read this in ~15 minutes, then we lock and ship.

---

## TL;DR (60-second read)

**The product.** An audit agent that audits OTHER AI agents — the way SOC-2 auditors audit security, but for AI safety/compliance.

**The buyer.** Director of AI Governance / AI Safety Officer / Head of Responsible AI at a 10K+ employee company that runs production AI agents (healthcare, fintech, insurance, pharma). 2,000+ open jobs on LinkedIn US today. Median salary $158K. Their boss (the CRO / CISO / Chief AI Officer) signs the check.

**The deadline that sells it.** EU AI Act enforces 2026-08-02 (59 days from today). Penalty for non-compliance is **€15M or 3% of global revenue** (some readings say 7% / €35M). Big-4 consulting charges €80K-€250K per audit pack. Lead time 12-18 months.

**The market is forming RIGHT NOW.** $15M went into AIUC (the category leader) in July 2025. Fiddler closed $30M Series C in Jan 2026. OpenAI bought Promptfoo for $86M in March 2026. Three observability platforms got acquired in the last 6 months. We're not late; we're on time.

**Our angle.** Continuous, self-serve, Phoenix-native, no auditor/insurer conflict-of-interest. AIUC is quarterly + enterprise-priced. We're real-time + mid-market.

**Can we build it in 8 days?** Yes. The architecture maps to ~80h of new work + ~30h reuse from existing ChaosLab pieces (Cloud Run shape, Phoenix wrappers, GitLab MR hybrid, Next.js layout, A2A target wiring). ~72h capacity = on the edge but feasible. Cuts identified.

**The "cascade-flip" demo moment.** Audit completes 44/47 passes. The 3 failures collapse into ONE root cause via Phoenix trace clustering. Patch generated in 4 seconds. Headline: _"3 failures, 1 root cause, patch in 4 seconds."_

---

## 1. The category — why now, who's in it

### What "AI Trust Auditor" means in plain English

Today, when a company ships an AI agent to production (a customer-support bot, a coding assistant, a healthcare prior-auth tool, a fraud-triage agent), nobody can prove it behaves correctly. The product DOES things — answers tickets, files claims, writes code. But when a regulator asks "show me every decision and prove your AI didn't violate GDPR / HIPAA / EU AI Act," the compliance team's answer today is "we have logs in Datadog, slides in Confluence, and a stack of screenshots."

An **AI Trust Auditor** is a separate AI agent that does this job:

1. You give it your production agent (Cloud Run URL / OpenAPI spec / ADK config)
2. It runs a battery of adversarial tests (prompt injection, role confusion, data exfiltration probes, tool misuse, hallucination probes, off-topic drift)
3. It captures every trace via Phoenix
4. It grades pass/fail using `gemini-3.5-flash` as the LLM-as-judge
5. It produces a regulator-ready audit report — signed PDF + signed JSON keyed to a commit SHA

The audit report is what the compliance officer hands to the regulator, the CRO presents to the board, and the company files for EU AI Act conformity.

### Why now — three forcing functions in 2026

1. **EU AI Act enforces 2026-08-02.** Non-compliance for "high-risk" AI systems carries **€15M or 3% global turnover** (some articles cite higher tiers up to €35M / 7%). Source: agent-2 EU-AI-Act research (`brainstorm/20`).
2. **The buyer role is being mass-hired.** 2,000+ Director of AI Governance jobs on LinkedIn US. 13K+ "responsible AI" jobs globally. Forrester predicts 60% of Fortune 100 will have a Head of AI Governance by EOY 2026. Source: agent-4 (`brainstorm/22`).
3. **The market is forming RIGHT NOW.** Klaimee (YC), Mount, WSO2 Agent Manager, CORAS.ai all launched products in May 2026. AIUC raised $15M with Orrick/Stanford/MITRE pedigree last July. Fiddler pivoted to "AI Control Plane" in January. OpenAI bought Promptfoo in March. Three observability acquisitions in 6 months. Source: agent-1 (`brainstorm/19`).

### The 6 competitors that matter — what they do, where they leave gaps

| Competitor                                             | What they ship                                                                                                              | Pricing                          | Gap                                                                     |
| ------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------- | -------------------------------- | ----------------------------------------------------------------------- |
| **AIUC** ($15M seed, Jul 2025)                         | "SOC-2 for AI agents" — standard + audit + insurance trifecta. Quarterly probes (1,000+ scenarios). UiPath is first holder. | Enterprise services, undisclosed | Quarterly cadence = 3-month blind spots. Enterprise-only.               |
| **Fiddler AI Control Plane** ($30M Series C, Jan 2026) | Auditable governance for ML+agents                                                                                          | $100K+ ACV                       | Heavyweight enterprise platform; slow self-serve                        |
| **Promptfoo** (acquired by OpenAI, $86M, Mar 2026)     | OSS red-team + eval w/ OWASP/NIST/MITRE presets                                                                             | OSS free + Pro tier              | Pre-deployment only; doesn't watch production; no compliance artifact   |
| **Klaimee** (YC)                                       | Liability INSURANCE for AI agents                                                                                           | Per-policy                       | Insurance — they certify what others audit. They don't BUILD the audit. |
| **WSO2 Agent Manager** (beta, May 2026)                | Enterprise "control plane" to govern AI agents                                                                              | Enterprise license               | Control plane, not auditor.                                             |
| **CORAS.ai** (launched May 2026)                       | Agentic AI Reporting for government/defense (IL5)                                                                           | Government services pricing      | Government-only.                                                        |

**The gap (sharp):**

> _"No continuous, automated, evidence-producing, third-party-independent AI agent audit product that self-serves to Series A/B + mid-market AI-platform leads."_

The big agents (Credo AI, IBM watsonx.governance, Microsoft Purview, OneTrust) all sell at $30K-$300K ACV to F500 procurement. AIUC sits above at top-shelf. **The mid-market — 50-500 person companies that run 1-3 production AI agents — has no good option today.** They stitch Promptfoo + Phoenix + Guardrails + homegrown evidence.

That gap is who we sell to.

---

## 2. The buyer — who actually uses this on Monday

The persona has a name now (Maya in the demo agent's draft; Priya in the buyer-research agent's draft — same shape):

**Priya Sharma. Director of AI Governance. ~5,000-person health-insurance carrier in New Jersey.**

She is real. We have 15 verified open job postings from HPE, Mastercard, Microsoft, AstraZeneca, Citi, BofA, Alight Solutions, Scale AI, Simpson Thacher (cite-able in `brainstorm/22`). 72% of these jobs are at 10K+ employee companies. Vertical mix: Professional Services 51%, Tech 15%, FinServ 9%, plus pharma/healthcare/insurance.

**Her week today, without us:**

- Monday: pulls Phoenix screenshots, exports Jira tickets, copies Slack threads into a Google Doc to build the weekly compliance summary
- Tuesday: meets with the AI Platform team to ask "what changed in the prior-auth agent's prompt this sprint?"
- Wednesday: reviews adversarial-test results from a contracted red-team consultancy ($15K/month)
- Thursday: starts assembling the quarterly board report (2 weeks of work per quarter)
- Friday: 1:1 with the CISO. Tries to answer "if a regulator audits us next week, are we ready?"

**What she'd pay for.** Existing market evidence:

- Credo AI: $30K-$150K/year
- IBM watsonx.governance Enterprise: $120K-$300K
- Microsoft Purview AI: $50K-$200K
- OneTrust large enterprise: $292K
- Red-team-as-a-service: $15K/month continuous subscriptions
- Total category 2025 spend: $2.26B (+28.8% YoY)

Source: `brainstorm/22`. Every figure cited with URL.

**The buying trigger.** The thing that puts our product on her budget:

1. A regulator letter arrives (CMS for healthcare prior-auth, SEC for trading agents, FDA for medical-device AI)
2. A customer requires SOC 2 + AI controls before renewing
3. The CAIO mandates EU AI Act readiness by 2026-08-02
4. An internal incident — the AI agent made a wrong call, the postmortem demands "show me the audit trail"

**THE LOAD-BEARING ASSUMPTION (must respect this):**

Priya is the **champion + user**. The **economic buyer is her boss** — CRO, CISO, or CAIO one level up. Existing vendors win procurement because they ship **one-page board-ready trust attestations the executive can present unedited**.

> **Build for Priya's daily workflow AND the executive-artifact layer. If we only build for Priya, we lose the deal at procurement.**

This is captured in `brainstorm/22` as the riskiest assumption.

---

## 3. The product, plain English

What Priya does Monday morning on our app:

1. Opens `trustauditor.app` (Cloud Run-hosted Next.js)
2. Clicks "Audit my agent." Pastes the Cloud Run URL or uploads ADK `agent.py` or connects via OAuth to her GitLab repo
3. Picks the regulatory frame she's auditing against (EU AI Act / NIST AI RMF / HIPAA / SOC 2 + AI)
4. Clicks "Run audit." The product runs 47 adversarial tests in ~90 seconds, traces all into Phoenix
5. Watches the live progress screen (test count up, pass/fail markers appearing, failed-trace evidence drilling)
6. When the audit completes, sees a 1-page executive summary (the artifact her CRO presents at the board meeting)
7. Drills into failures: each failure is grouped by root cause, with the failing Phoenix span highlighted in the trace tree
8. Clicks "Generate hardening recipe" on any failure cluster — gets a markdown patch with concrete remediation steps
9. Optionally: clicks "File compliance MR" — pushes the patch to her GitLab repo as a real MR via the hybrid python-gitlab + official MCP path
10. Downloads the signed PDF + signed JSON (keyed to commit SHA). Files it in her audit registry.

**The whole flow runs against real services. No mocks anywhere.** Real Phoenix Cloud (or self-hosted Phoenix Docker for offline). Real Gemini-3.5-Flash as the LLM judge. Real GitLab MR. Real Cloud KMS signing. Real GCS signed URL.

---

## 4. The deliverable that sells the demo — EU AI Act Annex IV Pack

This is the headline output. It's also what makes Priya's CRO sign the contract.

**EU AI Act Annex IV Technical Documentation Pack:**

- 9-section dossier required BEFORE any "high-risk" AI system goes to market
- 50-150 pages
- Penalty for non-compliance: €15M or 3% of global turnover (some readings cite €35M / 7%)
- Big-4 consulting firms charge €80K-€250K per pack
- Currently produced over 12-18 months by stitching outputs from legal + ML + risk teams
- Must be kept current through the system's life and retained 10 years post-market
- **Effective 2026-08-02 — 59 days from today**

Our product auto-generates this pack from:

- The customer's agent repo (architecture description)
- Phoenix traces (Article 12 automatic event logs)
- Phoenix annotations (per-decision evidence)
- Our fault-injection results (the systematic adversarial test record Article 9 requires)
- GitLab MR patch history (the change-management audit trail Article 15 requires)

Output: signed `.pdf` + signed `.json`, keyed to a commit SHA, ready to hand to a notified body. **This single artifact satisfies Articles 9, 11, 12, 15, and 72 simultaneously.**

The story that lands the demo: _"Big-4 charges €80K and 18 months for this document. Our agent produces it in 90 seconds, on a real commit, with a real signed audit trail. The same document. With real evidence."_

---

## 5. How we build it — the architecture in one paragraph

Cloud Run-hosted ADK `SequentialAgent` (orchestrator) with four sub-agents:

- **Inspector** — classifies the target via OpenAPI/AgentCard/probe (is it customer support? RAG? coding agent?)
- **Tester** — `LoopAgent`, 12-test adversarial battery × 6 risk categories: prompt injection, role confusion, data exfiltration, tool misuse, hallucination, off-topic drift
- **Judge** — runs Phoenix `run_experiment` with a `ClassificationEvaluator` on `gemini-3.5-flash`, renders PASS/FAIL verdicts per test, writes results back to Phoenix as experiment rows + annotations
- **Reporter** — renders PDF via Jinja+WeasyPrint, signs JSON via Cloud KMS, uploads to GCS with a 7-day V4 signed URL, optionally emits a GitLab MR via the hybrid `python-gitlab` SDK + official MCP path (the same ADR-011 pattern from ChaosLab)

Reads Phoenix via the 27-tool `@arizeai/phoenix-mcp` stdio subprocess (RAT-verified). Writes back via two custom `FunctionTool` wrappers around `phoenix.client.AsyncClient` (`run_experiment` + `log_span_annotations`) per ADR-005. Targets reached via `RemoteA2aAgent(AgentCard.from_url(...))` (Tier 1 ADK) or `httpx`-wrapped HTTP tool (Tier 2/3 LangChain/CrewAI/OAI-Agents/raw).

Full architecture details + every API call signature: `brainstorm/21-trust-auditor-architecture.md` (989 lines, every claim RAT-cited).

### The three honest real-integration risks

1. **Cross-tenant Phoenix ingest** — the customer's target agent must export traces to OUR Phoenix project using OUR API key. Operationally awkward; needs a Day-1 RAT-style verification. Worst case: we host a per-customer Phoenix project.
2. **Phoenix Cloud 25K spans/month free-tier cap** — ~100 spans per audit × 250 audits/month = free-tier saturated. Mitigation: self-hosted Phoenix Docker (`docker run arizephoenix/phoenix`) for dev runs, Cloud only for judging-window demos.
3. **GitLab MCP trial-tier** — same unresolved question from ChaosLab's ADR-011. If trial limits block the official MCP path, we fall back to all-`python-gitlab` (loses official-MCP judging credit but functionally works).

### 8-day build feasibility — yes

| Component                                       | New work | Reuse from existing ChaosLab     |
| ----------------------------------------------- | -------- | -------------------------------- |
| Cloud Run + Next.js web app                     | 12h      | 8h (S7.1 layout)                 |
| Orchestrator (SequentialAgent)                  | 8h       | 6h (S4.2 stub)                   |
| Inspector + Tester + Judge sub-agents           | 20h      | 4h (S5.x fault generators)       |
| Reporter (PDF + KMS signing + GCS)              | 10h      | 0h                               |
| Phoenix MCP read + custom FunctionTool wrappers | 4h       | 8h (RAT + S4.4 already verified) |
| Cross-framework target adapter (Tier 1+2+3)     | 12h      | 4h (story-3.x adapter spec)      |
| BDD tests                                       | 10h      | 0h                               |
| GitLab MR hybrid (optional)                     | 4h       | 0h                               |
| **Total**                                       | **~80h** | **~30h**                         |

Capacity: 8 days × 9h/day = 72h. Tight. Cuts available: drop GitLab MR mode (-4h), defer JSON signing (-3h), trim BDD to integration-only (-4h). Minimum-viable 3-min-demo cut fits ~50h comfortably.

---

## 6. The 3-minute demo arc

| Time      | What's on screen                                                                                                                                                                                                                                                                                                                                               | What the voiceover says (verbatim)                                                                                                                                                                                                                                                                                                          |
| --------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 0:00-0:15 | **The pain.** Priya at her desk, 4 browser tabs open: Phoenix, GitLab, a Google Doc titled "Q3 Compliance Report — DRAFT," a Slack thread with the AI Platform team. Camera pans. Headline overlay: "EU AI Act enforces Aug 2 2026. €15M penalty. Big-4 charges €80K."                                                                                         | "Meet Maya. She's the Director of AI Governance at a health-insurance carrier. In 59 days, her company has to produce an EU AI Act audit pack for the prior-auth agent it shipped last quarter. Today, she's stitching it together from screenshots."                                                                                       |
| 0:15-0:45 | **The product appears.** Web app `trustauditor.app` loads. Maya clicks "Audit my agent." Pastes a Cloud Run URL. Picks "EU AI Act — high-risk system." Clicks Run. The Phoenix project iframe appears in the right pane.                                                                                                                                       | "Trust Auditor connects to her production prior-auth agent via Agent-to-Agent protocol. The agent runs on Google Cloud Agent Builder. Trust Auditor is going to test it for prompt injection, role confusion, tool misuse, and hallucination — all 47 tests, against the live agent."                                                       |
| 0:45-1:30 | **The live audit.** Test count climbs (1/47, 5/47, 12/47…). Phoenix traces appear in the right pane in real time. Pass/fail markers light up. 44 green, 3 red.                                                                                                                                                                                                 | "Each test is a real Phoenix experiment. The Judge agent is `gemini-3.5-flash` grading every response. Annotations are written back via Phoenix MCP. This is real telemetry, not synthetic logs."                                                                                                                                           |
| 1:30-2:15 | **The cascade-flip.** 47/47 done. Dashboard shows 44 pass, 3 fail. Maya clicks the "Failures" tab. The 3 failures collapse into ONE cluster. The Phoenix trace tree expands; the common failed span lights up: `check_formulary` called without first calling `verify_benefits`. Maya clicks "Generate hardening recipe." Markdown patch renders in 4 seconds. | "This is the moment everyone wants their compliance tool to do but nobody has: three failures collapse into one root cause. Trust Auditor isn't just telling Maya the bot's wrong — it's telling her **why** it's wrong, **where in the trace** it went wrong, and **what to change**. Three failures, one root cause, patch in 4 seconds." |
| 2:15-2:45 | **The Annex IV pack.** PDF preview renders. 9 sections visible (Article 9, 11, 12, 13, 14, 15, 72…). Maya clicks "Sign & file." Cloud KMS signing visible in the UI. Signed PDF + signed JSON download.                                                                                                                                                        | "What Maya now has — produced in 90 seconds — is the EU AI Act Annex IV technical documentation pack. Cryptographically signed. Keyed to commit `8a4f2c1`. Costs Big-4 €80,000 and 18 months. Maya did it before her coffee finished."                                                                                                      |
| 2:45-3:00 | **The outro.** URL on screen: `trustauditor.app`. Logos: Arize Phoenix + Google Cloud Agent Builder.                                                                                                                                                                                                                                                           | "Built with Arize Phoenix MCP and Google Cloud Agent Builder. Try it at trustauditor.app."                                                                                                                                                                                                                                                  |

**Headline metric the judges will repeat:** _"3 failures, 1 root cause, patch in 4 seconds."_

**Diff vs the strongest competitor (Klaimee) in one line:**

> _"Trust Auditor sells you the auditable evidence — your Phoenix traces, retrievable forever, signed by your own compliance officer — while Klaimee sells you the insurance certificate, written by the same shop that audited you."_

The conflict-of-interest framing matters: the auditor-and-insurer-as-same-vendor model has problems regulators don't love. Independent evidence is structurally better.

---

## 7. Post-hackathon — the path to real users

After the deadline (2026-06-11), here's what happens between then and "real Priyas running their AI agents through this."

### Week 1 post-submission (Jun 12-18)

- Self-serve onboarding: paste a Cloud Run URL, see an audit run, get a PDF. No login wall for the first audit.
- Add an "Audited by Trust Auditor" badge generator (the kind Klaimee/AIUC sell as insurance certificates, but ours is signed by the customer's own KMS, not ours — no conflict of interest)

### Weeks 2-4 (during judging window, Jun 22 - Jul 6)

- Outreach to the named 2,000 LinkedIn Director-of-AI-Governance posts. Cold email pattern: "I built the EU-AI-Act-Annex-IV auto-generator your team is doing manually. Sandbox URL inside, 30-second demo video. Will it pass your CRO's review?"
- Pick 5 target companies from the verified-JD list (`brainstorm/22`): a regional health insurer, a NYDFS-regulated bank, an AstraZeneca-style pharma, a Series A AI agent startup, a Big-Tech AI red-team contractor
- Goal: 3 paid pilots at $2K-$5K/month (well below Credo AI's floor, accessible to mid-market)

### The 5 first paying customers we target (named shapes, not real names)

1. **A regional health-insurance carrier** (~5K employees, 50-person compliance team, ships 1-3 prior-auth agents). CMS prior-auth rule effective Jan 1 2026 = real pain.
2. **A NYDFS-regulated bank** (small/mid-size). Regulator already published guidance on AI risk management.
3. **A Series A AI agent startup** (5-30 person team). Their first F500 customer demands SOC 2 + AI controls before signing the contract.
4. **A pharma R&D unit** running internal ChatGPT-like assistants on proprietary trial data. Real PHI/IP risk.
5. **A Big-Tech AI red-team-as-a-service contractor** who wants to white-label our agent into their delivery pipeline.

### The 5 features we deliberately CUT for the hackathon (build later)

1. Multi-tenant auth + SSO (single shared free-tier instance for judging window)
2. Billing + pricing tiers (free pilot until first paying customer)
3. x509 signing of the audit certificate (Cloud KMS signing is enough for v1; x509 chain is v2)
4. Support for >1 agent runtime in MVP demo (ADK + Tier 2 LangChain is enough; CrewAI/OAI-Agents documented as roadmap)
5. Continuous-monitoring mode (one-shot audit at submission; cron-driven continuous mode is v2)

---

## 8. What we're betting on (riskiest assumptions, honest list)

In order of how badly each one bites if wrong:

1. **The economic buyer (CRO/CISO/CAIO) signs the check, not Priya.** Mitigation: ship an executive-artifact layer (the 1-page board-ready PDF). If we don't, we lose at procurement. This is the LOAD-BEARING assumption per the buyer-persona agent.
2. **Phoenix Cloud free tier holds during the 90-second live demo.** Mitigation: pre-warm + record twice + self-hosted Phoenix Docker fallback (same Cloud Run cluster, only the iframe source changes).
3. **The cross-tenant Phoenix ingest model works** (customer's traces flowing into our project). If it doesn't, we host a per-customer Phoenix and the architecture grows by one component. Day-1 RAT step needed.
4. **AIUC doesn't pre-empt us in mid-market in the next 30 days.** They're enterprise-only today but could ship a self-serve tier. Watch their Series A announcement.
5. **EU AI Act actually enforces August 2 with audit teeth** (vs. soft grace period). If enforcement gets delayed 6 months, the urgency softens — but the buyer ROLE has already been hired (2,000 LinkedIn jobs), and the EU regulator stake is enough.

---

## 9. The bet, restated

**We are not betting on a hypothesis. We are betting on a market that is already forming.**

- Nat Friedman put $15M into the category leader 11 months ago
- Three observability acquisitions in 6 months
- OpenAI bought the OSS red-team play for $86M three months ago
- 2,000 buyer-role job postings open today
- $2.26B 2025 spend (+28.8% YoY)
- A regulatory deadline 59 days from today with €15M teeth
- A category leader (AIUC) that is structurally quarterly + enterprise-only — the mid-market wedge is open

What we add: **continuous, Phoenix-native, self-serve, no auditor/insurer conflict-of-interest, with a regulator-ready Annex IV pack as the headline deliverable.**

We can ship the MVP in 8 days. We can keep building after the hackathon.

---

## 10. Open decisions before we start S1.4

Before I touch any cloud infra (which I paused for this research), I need three calls from you:

1. **Track lock.** Final answer: Arize. Confirm? (alternatives surfaced: Dynatrace for CI-Doctor pivot; we discussed and ruled out)
2. **Product name.** "Trust Auditor" is my working name. I don't love it — too generic, sounds like a SaaS template. Better candidates we could land on: **Certify**, **Attest**, **Trace-of-Truth**, **Aegis**, **Witness**, **Probe**, **Hallmark**, **Ledger**. Want to brainstorm together or pick one?
3. **Scope decision.** I recommend going with the FULL architecture (4 sub-agents + Annex IV pack + Cloud KMS + optional GitLab MR), targeting ~70-80h of build, cutting room reserved. Alternative: a TIGHTER MVP (Inspector + Tester + Judge + simpler PDF, no signing, no GitLab MR) at ~50h with more demo polish budget. Which?

When you've answered these three, I move to S1.4 (the GCP IAM bootstrap I paused). Spec rewrite is contained — the PRD + architecture.md + ADR-005 stay; ADR-006 stays (Apache-2.0 NOTICE re-purposes attribution); ADR-012 stays. We rewrite epics.md + stories/\* to reflect the Trust Auditor product (not chaos engineering). Same engine, sharper pitch, sharper user.
