# Refactor Candidates for google-cloud-rapid-agent-2026

**Generated:** 2026-06-04
**Target ecosystem:** Google Cloud Agent Builder + Gemini + Vertex AI + Cloud Run + ADK; partner MCP server from one of Arize / Elastic / Fivetran / GitLab / MongoDB / Dynatrace.
**Themes:** AI agent observability, closed-loop self-improvement, AI cost guardrail, vertical-specific agent products (healthcare prior-auth, insurance SIU fraud, legal contract review, compliance audit), team-velocity coaching, living documentation.
**Constraints (explicit only, per principle #4):** Avoid 🔴 saturated shapes (code-review/MR agents, vector-RAG bots, agent observability dashboards, generic prompt-injection red-team). Lean toward Arize / Dynatrace / Elastic / Fivetran tracks (Arize least crowded per saturation map; MongoDB/GitLab most crowded — avoid). Apply immediate-utility filter (named non-engineer day-1 user per `feedback-immediate-utility-bias`).
**Adapt budget:** ~80-120h net solo (Jun 4 → Jun 11; 8 days × 12h max useful per day).

---

## Honest finding before the candidates

**The local cross-corpus (51K Devpost winners + 17K ETHGlobal projects) has STRUCTURAL MISMATCH with this hackathon's themes.** Empirically, all 10 batch queries against vertical-specific AI-agent shapes returned **top Jaccard scores of 0.05-0.18** with the same crypto-flavored projects (`Ai Trading Agent`, `Maru`, `Empty Project`) recurring as token-overlap noise.

What this means concretely:

1. **The corpus is dominated by crypto/DeFi/Web3 projects.** ETHGlobal is exclusively crypto. The AlphaHack Devpost snapshot (March 2026) skews toward crypto-adjacent Devpost events. Non-crypto enterprise AI-agent hackathons (Microsoft AI Agents, Anthropic Build, OpenAI Open Model, Bedrock) are underindexed.
2. **The most impactful Google Cloud Rapid Agent ideas surfaced by the 5-agent research (Postmortem Buddy, Insurance SIU fraud triage, AI Coding Agent Budget Guardrail, Living Documentation, Healthcare prior-auth) have ALMOST NO MEANINGFUL PRIOR ART in this corpus.** That's actually a POSITIVE signal — those shapes are whitespace per the saturation map, and there's no winner-to-port-from in the rebuild library either.
3. **The ecosystem-refactor alpha is therefore LIMITED for this specific hackathon.** This is the genuinely-greenfield case where the rebuild strategy applies less than usual. Surfacing the 5 viable port candidates below honestly with this caveat.

Per operating principle #10 ("performance over breadth"), Apify-actor fallback for hackathons not yet in corpus (Microsoft AI Agents 2025, Bedrock 2026, Anthropic 2026) could supplement — but at this point, all 5-agent-research's named winners (zenith.chat, Vigil AI, RoboChef, Gitdefender, etc.) are already captured in `research/google-cloud-rapid-agent/brainstorm/09-hackathon-winner-patterns-2025-2026.md`, so the supplementary value of paid actors is limited.

---

## Filter pass (principle #6 — kill early, score survivors)

Started with ~50 candidates surfaced across 15 batched queries. Applied filters:

| Filter                                                                                                                             | Dropped                                                                                            |
| ---------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| **Already deployed on Google Cloud Agent Builder / ADK / Vertex AI**                                                               | 0 (none of the surfaced projects were on GC)                                                       |
| **Smart-contract-specific primitives that can't port** (e.g., E.M.X hardhat, ZK KYC zk-proofs, GitVault on-chain dev reputation)   | 8 — pure crypto plays with no enterprise-portable shape                                            |
| **🔴 Saturated shape per agent 5 saturation map** (code-review/MR agents, vector-RAG, observability dashboards, generic jailbreak) | 12 — including most "AuditGPT-style" smart-contract auditor variants when pitched as "code-review" |
| **Score < 0.05 token-overlap noise**                                                                                               | ~25 — recurring "Ai Trading Agent", "Maru", "Empty Project" noise hits                             |

**Survivors: 5.** Scored below.

---

## Ranked candidates (top 5)

### 1. SupportLens — score 0.88

- **Source:** Automated Customer Support — https://devpost.com/software/automated-customer-support
- **Original prize:** Won at YB Hackathon (1 prize, exact prize name unrecorded in corpus)
- **Original ecosystem:** Devpost generic
- **What it does (1 sentence):** Auto-analyzes, categorizes, and assigns incoming customer-support messages to appropriate handlers.
- **Primitives used:** LLM classification + rules-based routing + ticket-system integration. No memory/learning layer.

- **What stays in the port:**
  - Inbound ticket parsing + intent classification taxonomy
  - Routing logic (which agent / queue / human gets it)
  - Confidence-thresholded escalation pattern
- **What changes:**
  - Rewrite as ADK `SequentialAgent`: `IntentClassifier` → `MemoryRetriever` → `Responder` → `Annotator`
  - **MemoryRetriever queries Phoenix MCP** for the agent's own past traces, finds 3 nearest-neighbor tickets by intent + outcome, and uses those resolutions as in-context shots
  - **Annotator writes back to Phoenix** via the annotations API after each resolution: tags as "escalated" / "resolved" / "wrong-route", with evidence pointer to the customer's next message
  - Every Nth ticket triggers a Phoenix experiment: replay last 50 ambiguous tickets against current prompt vs a candidate; keep the winner
- **Wedge we add (target-ecosystem-specific):**
  Phoenix MCP closed-loop self-improvement. The source had NO observability/memory layer — every ticket was independent. **Arize Devpost partner brief verbatim:** "Bonus points for agents that use their own observability data to improve over time." This wedge is literally the sponsor's published criteria.
- **Named day-1 user:** Support team lead at any SaaS with 50+ tickets/day where new hires need to learn the playbook. They install the agent on their Zendesk/Intercom inbox; after one week, the agent has annotated 200+ resolved tickets and starts visibly nudging escalation patterns toward proven solves. They use it on day 1 because every ticket goes through it.
- **Scope check (explicit constraints):** ✅ Arize track (least crowded). ✅ Closed-loop self-improvement is whitespace per saturation map. ✅ Immediate-utility filter — named support lead uses Day 1.
- **Demo translation:** 3 tickets in 90 seconds. Ticket 1: agent guesses wrong, gets corrected. Ticket 2 (similar shape): agent queries own Phoenix traces, finds ticket 1's correction, gets it right. Ticket 3: agent shows the trace chain that led to its decision. **Visual cascade-flip = visible improvement.**
- **Adaptability:** 0.85 | **Wedge:** 0.90 | **Execution risk:** 0.80 | **Team recompete risk:** 0.90 | **Sponsor-fit boost:** 0.95
- **Geometric mean:** **0.88**

### 2. InsurFraudTriage — score 0.80

- **Source:** Decoded: Unmasking Credit Card Fraud — https://devpost.com/software/decoded-unmasking-credit-card-fraud
- **Original prize:** Won at DataQuest '24 (1 prize, exact prize name unrecorded)
- **Original ecosystem:** Devpost data-analysis hackathon
- **What it does (1 sentence):** Classical-ML credit-card fraud detection ("Unraveling the Mystery of Credit Card Fraud") — feature engineering + classification on a transaction dataset.
- **Primitives used:** Pandas/sklearn pipeline. Static dataset analysis, not an agent.

- **What stays in the port:**
  - Fraud-feature taxonomy (transaction velocity, geo anomaly, amount distribution, merchant category)
  - Synthetic-data flow (credit-card → insurance claim translation is mechanical)
- **What changes:**
  - Wrap as an ADK agent — the static classifier becomes a TOOL the agent calls
  - Add **`InvestigationAgent`** that pulls supporting evidence (policy history, claim photos, witness reports — all synthetic) when the classifier flags a claim
  - **Every fraud determination annotated via Phoenix annotations API** with: features that contributed, evidence the InvestigationAgent retrieved, confidence band, and a Phoenix-experiment-generated counterfactual ("if this claim had photo evidence X, the decision would have flipped")
  - Audit panel: claims adjuster opens Phoenix UI → sees every fraud decision the agent made + can challenge any one. Phoenix prompt-registry stores the prompt that made the decision so the auditor knows EXACTLY what reasoning was used.
- **Wedge we add (target-ecosystem-specific):**
  Phoenix-backed audit trail for regulated fraud determinations. The source was a static analysis notebook with NO explainability layer. Insurance SIU is the **most-underserved vertical** per agent-4 research — 6-9 month payback, $1.13B Q1 2025 funding (+90% QoQ), no $1B+ incumbent.
- **Named day-1 user:** Claims fraud analyst at any P&C insurer (Avallon-tier or larger) processing 50+ flagged claims/day. They open the agent, paste a suspicious claim, get a triage decision PLUS the evidence chain. Most importantly: when the regulator audits 6 months later, the analyst can pull up every decision the agent ever made with full reasoning.
- **Scope check:** ✅ Arize track (least crowded). ✅ Most-underserved vertical per agent-4. ✅ Immediate-utility filter — named adjuster uses Day 1. ⚠ Regulated-data demo needs PUBLIC synthetic — use the Kaggle insurance fraud dataset (https://www.kaggle.com/datasets/buntyshah/auto-insurance-claims-data) or synthesize.
- **Demo translation:** 1 flagged claim in 2 min. Show: agent classifies → InvestigationAgent retrieves 4 evidence pieces → Phoenix experiment runs counterfactual → decision rendered with full audit trail visible. Quantified headline candidate: "Triages 95% of insurance fraud claims in <5 seconds with full Phoenix audit trail for regulator review."
- **Adaptability:** 0.70 | **Wedge:** 0.85 | **Execution risk:** 0.70 | **Team recompete risk:** 0.95 | **Sponsor-fit boost:** 0.85
- **Geometric mean:** **0.80**

### 3. AgentAuditGPT — score 0.76 (META-RECURSIVE — adjacent to existing ChaosLab wedge)

- **Source:** AuditGPT — https://ethglobal.com/showcase/auditgpt-0fti1
- **Original prize:** Won **3 prizes** at ETHGlobal Singapore (the most decorated AI-audit project in the entire corpus)
- **Original ecosystem:** ETHGlobal — smart-contract-only
- **What it does (1 sentence):** AI agent that audits Solidity smart contracts before deployment, returns ranked vulnerability findings with remediation guidance.
- **Primitives used:** Static analysis + LLM-driven vulnerability reasoning + Solidity-specific rule library.

- **What stays in the port:**
  - The agent ARCHITECTURE (parse → analyze → score → recommend → annotate)
  - The "ranked findings with remediation" output contract
  - The audit-report templating
- **What changes:**
  - Replace Solidity-specific vulnerability taxonomy with **AI-AGENT-PROMPT vulnerability taxonomy**: prompt injection susceptibility, tool-call hallucination risk, runaway loop susceptibility, memory poisoning susceptibility, ungrounded factual claim density
  - Audit target shifts from `.sol` files to ADK agent definitions (`agent.py` + tools.py + prompt templates)
  - Phoenix MCP wires in as the **historical-audit memory**: agent queries its own previous audits to find similar prompt patterns it has scored before
  - Phoenix experiments serve as the **A/B engine**: when the auditor proposes a prompt fix, it runs the original vs the fix on a corpus of adversarial inputs and shows comparative safety scores
- **Wedge we add (target-ecosystem-specific):**
  Two compounding wedges. First, the domain shift (smart contracts → AI agent code) is novel — nobody has ported AuditGPT's audit-recommend loop to AI agent code yet. Second, Phoenix MCP gives us a **historical comparison fabric** that ETHGlobal smart-contract audits don't have. **CAUTION:** This shape is adjacent to ChaosLab's existing wedge (chaos-injection-based hardening). The question of whether AgentAuditGPT IS ChaosLab is real — see "Cross-reference to ChaosLab" section below.
- **Named day-1 user:** AI Platform Lead at any company shipping production agents (Cohere Health, Sierra AI, etc.). They run AgentAuditGPT against their staging agent before each deploy. Audit report is a Phoenix dataset they can diff over time. Used Day 1 because every new agent commit triggers an audit.
- **Scope check:** ✅ Arize track. ✅ Not on saturation map (smart-contract-audit-port-to-AI-agent-audit is whitespace). ⚠ **Risk:** Could be perceived as too similar to "ChaosLab as existing wedge" — if we already pivoted to "agent-hardener", the audit angle is the static-analysis cousin of our dynamic-chaos approach.
- **Demo translation:** Show real ADK agent code with a subtle prompt injection vulnerability → AgentAuditGPT scans → flags 2 issues → suggests fix → re-audit shows clean. Phoenix UI shows audit history of this codebase over the last 5 commits.
- **Adaptability:** 0.70 | **Wedge:** 0.80 | **Execution risk:** 0.60 | **Team recompete risk:** 0.90 | **Sponsor-fit boost:** 0.85
- **Geometric mean:** **0.76**

### 4. PriorAuthFiller — score 0.72

- **Source:** sidekick.ai — https://ethglobal.com/showcase/sidekick-ai-votxi
- **Original prize:** Won prizes at ETHGlobal Singapore
- **Original ecosystem:** ETHGlobal — crypto-adjacent form filler
- **What it does (1 sentence):** Client-side LLM agent that automates form-submission journeys (the source is generic — could be any form).
- **Primitives used:** LLM-driven form-field-mapping + browser automation hints.

- **What stays in the port:**
  - The form-mapping mental model (semantic understanding of what each field wants)
  - The "agent walks the user through the form" UX pattern
- **What changes:**
  - Target form shifts to **CMS-1500 health insurance claim form** + payer-specific prior-auth attachments
  - Add **`EvidenceRetrieval` subagent** that pulls medical records (Synthea/MIMIC-IV synthetic) and matches them to required prior-auth fields
  - **Every field-fill annotated via Phoenix** with the source evidence (which record, which line) — this IS the audit trail CMS requires under the Jan 1 2026 rule
- **Wedge we add (target-ecosystem-specific):**
  CMS prior-auth rule effective 2026-01-01 (regulatory forcing function per agent-4). Phoenix audit-trail for every field-fill creates a regulator-ready paper trail that no form-filler has today.
- **Named day-1 user:** Prior-authorization nurse at any payer or large hospital. Their job today: 4-7 minutes per claim, hundreds per week. With PriorAuthFiller, they paste the patient's record bundle, the form auto-fills with cited evidence, they review + submit. Used Day 1 because every claim goes through this.
- **Scope check:** ✅ Arize. ⚠ Risk — healthcare domain knowledge is specialist; demo CONVICTION risk is real. PHI-safe via Synthea/MIMIC-IV public synthetic data.
- **Demo translation:** 1 prior-auth claim in 2:30. Patient record on left, CMS-1500 form on right, agent fills field-by-field with hover-cited evidence; Phoenix UI shows the trail.
- **Adaptability:** 0.65 | **Wedge:** 0.85 | **Execution risk:** 0.50 | **Team recompete risk:** 0.90 | **Sponsor-fit boost:** 0.80
- **Geometric mean:** **0.72**

### 5. InternalConcierge — score 0.65 (saturation penalty applied)

- **Source:** Personal Assistant for CapitalOne — https://devpost.com/software/financial-bot-vandyhacks
- **Original prize:** Won at VandyHacks V (1 prize)
- **Original ecosystem:** Devpost generic
- **What it does (1 sentence):** React/Flask personal assistant for CapitalOne customers, answering account / product questions.
- **Primitives used:** Simple retrieval over CapitalOne FAQs/product docs.

- **What stays in the port:** Q&A pattern, multi-turn dialog handling.
- **What changes:** Target audience shifts from CUSTOMERS to INTERNAL EMPLOYEES. Corpus becomes IT/HR/Finance docs. Wedge: Elastic memory layer — agent WRITES BACK its enriched answer to ES, building a self-updating internal KB.
- **Wedge we add:** Living-doc write-back (agent 3 finding: nobody has built this combo with Elastic Workflows + ES write-back).
- **Named day-1 user:** Engineering manager at any 100+ eng org. Day 1: every employee question that hits the IT/HR helpdesk first goes to the agent, which answers OR writes a perma-doc. Helpdesk volume drops 30% in week 1.
- **Scope check:** ⚠ **Saturation penalty.** Vector-RAG knowledge bot is 🔴 HIGH per saturation map (30+ priors). The write-back wedge differentiates BUT we'd be judged against 30 other RAG demos. Honest score adjusted from raw 0.80 to **0.65** to reflect this.
- **Adaptability:** 0.85 | **Wedge:** 0.50 (saturation penalty) | **Execution risk:** 0.85 | **Team recompete risk:** 0.95 | **Sponsor-fit boost:** 0.70
- **Geometric mean:** **0.65**

---

## Recommendation

**Pick #1 — SupportLens (score 0.88).** It is the ONLY candidate where the geometric-mean score crosses 0.85 ("commit and ship" threshold per skill rubric), AND every dimension is independently strong (lowest is execution-risk at 0.80, which is still solid). The wedge (Phoenix-MCP closed-loop self-improvement) is verbatim the sponsor's published bonus criteria — "agents that use their own observability data to improve over time." The named Day-1 user (support team lead) passes the immediate-utility filter without strain.

**Honorable mention: #2 InsurFraudTriage (0.80)** — if you want to lean into vertical-impact (insurance is the most-underserved vertical per agent-4 research) instead of "perfect-sponsor-language-match." Higher business-impact score, slightly more risk on execution and corpus.

---

## Cross-reference to ChaosLab (existing built-up wedge)

This memo was generated FRESH without anchoring on ChaosLab per Abu's 2026-06-03 push-back. But honest analysis says:

- **SupportLens IS NOT ChaosLab.** Different shape — learn-from-past-tickets vs inject-faults-and-harden. Could potentially co-exist as 2 distinct projects (but rules forbid multi-submission of the same wedge, so we pick one).
- **AgentAuditGPT IS ChaosLab-adjacent.** Static-audit cousin of dynamic-chaos. If we're keeping ChaosLab, AgentAuditGPT is REDUNDANT scope; don't double-build.
- **InsurFraudTriage IS NOT ChaosLab.** A vertical-specific fraud-triage agent has nothing to do with chaos engineering for agents. Genuinely different wedge.

**Implication:** if Abu wants to PIVOT entirely off ChaosLab, SupportLens > InsurFraudTriage > PriorAuthFiller are the data-backed alternatives in score order. If Abu wants to KEEP ChaosLab, no port candidate in this memo is structurally additive — the data says ChaosLab's closed-loop hardener shape is already a whitespace play (per saturation map), the Devpost partner language match is already in place, and the refactor library doesn't surface anything stronger to swap in.

---

## Sources of original-team-recompete risk

- **AuditGPT team** (ETHGlobal Singapore, 2024) — crypto-native, no public signal of switching to Google Cloud Agent Builder. Low risk.
- **sidekick.ai team** (ETHGlobal Singapore, 2024) — crypto-native, no public signal of Google Cloud entry. Low risk.
- **Automated Customer Support team** (YB Hackathon, undated) — student/early-career profile typical of YB events; very low risk of competing in this hackathon.
- **Decoded team** (DataQuest '24) — student data-analysis hack; near-zero risk.
- **Personal Assistant for CapitalOne team** (VandyHacks V, ~2017) — old project, team probably long-dispersed; zero risk.

---

## Cross-references

- Target hackathon primer: `/Users/abu/dev/hackathon/rapid-agents/research/google-cloud-rapid-agent/HACKATHON-PRIMER.md`
- Pain points (agent 1): `brainstorm/08-current-pain-points-2026.md`
- Winner patterns (agent 2): `brainstorm/09-hackathon-winner-patterns-2025-2026.md`
- Sponsor hidden capabilities (agent 3): `brainstorm/10-sponsor-hidden-use-cases.md`
- Vertical demand (agent 4): `brainstorm/11-vertical-agent-gaps.md`
- Saturation map (agent 5): `brainstorm/12-saturation-map.md`
- Theme keyword set: customer-support self-improvement, insurance SIU fraud, healthcare prior-auth, AI cost guardrail, compliance audit, team-velocity coaching, living documentation, live policy enforcement
