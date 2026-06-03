# 06 — Idea Rankings (Multiplicative-Floor Scored)

**Skill:** `sahil-idea-generator` running the `idea-generation` workflow with hackathon adaptation. Multiplicative-floor scoring — **one catastrophic dimension kills the score**. No compensation across axes.

**Input:** 15 candidates from `00-synthesis.md`
**Output:** scored ranking + top-3 decision-memo + handoff to `sahil-novelty-gate`
**Compiled:** 2026-06-02 (9 days before submission deadline)

---

## 1. Scoring methodology

Per the skill's hackathon adaptation, the catastrophic dimensions for THIS hackathon (Google Cloud Rapid Agent, June 11) are:

| #     | Axis                                | Why catastrophic                                          | 1 =                                         | 5 =                                             |
| ----- | ----------------------------------- | --------------------------------------------------------- | ------------------------------------------- | ----------------------------------------------- |
| **B** | Build feasibility (9-day solo)      | Can't ship → can't win                                    | Impossible in 9 days                        | Doable in 5 days with margin                    |
| **D** | Domain authenticity for Abu         | Per 05 anti-pattern #5, judges sniff fake demos           | Hard weak spot (healthcare, SPED, mall ops) | Abu's home turf (agent infra, web3, data infra) |
| **V** | Demo-ability in 3 minutes           | Per 05, demo video is judging insurance                   | Can't visually demo                         | Screen-stoppingly clear "wow" moment            |
| **T** | Track-EV math (saturation × payout) | Per 06-hidden-field, same $10K but different denominators | RED predicted track, $10K                   | GREEN predicted track, $10K                     |
| **N** | Differentiation in predicted field  | Same payout; differentiation = win-odds                   | Lazy default everyone picks                 | Almost no entrant will think of this            |
| **J** | Judging-criteria coverage (4 equal) | All 4 must clear or you lose                              | Barely passes 1-2 criteria                  | Hits all 4 maximally                            |

**Score = B × D × V × T × N × J** (max 5⁶ = 15,625; expressed as percentile of theoretical max)

**RAT threshold (per skill):** any candidate scoring **>30% of max (>4,687 raw)** earns a Riskiest Assumption Test in the top-3 deep-dive.

---

## 2. The 15 candidates scored

Sorted by raw multiplicative score. **Three tracks deliberately preserved in the top-3** (Arize / Fivetran / cross-track) per Abu's explicit anti-bias request.

| Rank  | Wedge                              |  B  |   D   |  V  |  T  |  N  |  J  |   Score    |    %    | Verdict                               |
| :---: | ---------------------------------- | :-: | :---: | :-: | :-: | :-: | :-: | :--------: | :-----: | ------------------------------------- |
| **1** | **W1 ChaosLab for Agents**         |  4  |   5   |  5  |  5  |  5  |  5  | **12,500** | **80%** | 🏆 TOP CANDIDATE — RAT below          |
| **2** | **W8 DataContract Sentinel**       |  3  |   5   |  4  |  4  |  5  |  5  | **6,000**  | **38%** | 🥈 RAT below                          |
| **2** | W6 World Cup Concierge             |  5  |   3   |  5  |  4  |  4  |  5  |   6,000    |   38%   | 🎖 Honorable mention                  |
| **4** | **W12 Field-Service x402**         |  3  |   5   |  5  |  3  |  5  |  5  | **5,625**  | **36%** | 🥉 RAT below                          |
|   5   | W3 Receipt→Refund→Restock          |  4  |   3   |  5  |  3  |  5  |  5  |   4,500    |   29%   | Borderline — see "why this dies"      |
|   6   | W9 Cross-Observability Self-Tuning |  2  |   4   |  4  |  5  |  5  |  5  |   4,000    |   26%   | Dies on build feasibility             |
|   7   | W2 Retail Ops Command Bridge       |  2  |   2   |  5  |  5  |  5  |  5  |   2,500    |   16%   | Dies on build × domain                |
|   8   | W11 Adaptive Triage Nurse          |  3  |   2   |  5  |  3  |  5  |  4  |   1,800    |   12%   | Dies on domain                        |
|   9   | W10 Multi-Source Knowledge         |  3  |   4   |  3  |  3  |  4  |  4  |   1,728    |   11%   | Mid on all axes, no peak              |
|   9   | W15 FIFA Phishing-Defense          |  3  |   3   |  4  |  3  |  4  |  4  |   1,728    |   11%   | Mid on all axes, no peak              |
|  11   | W4 Prior-Auth Coordinator          |  3  |   2   |  4  |  3  |  4  |  5  |   1,440    |   9%    | Dies on domain (healthcare)           |
|  12   | W7 Hospital Denials                |  3  |   2   |  4  |  3  |  3  |  5  |   1,080    |   7%    | Dies on domain                        |
|  13   | W5 Fraud Analyst Conveyor          |  3  |   2   |  4  |  3  |  3  |  4  |    864     |   5%    | Dies on domain (FinServ)              |
|  13   | W13 Mall GM Marketing              |  3  |   2   |  4  |  3  |  3  |  4  |    864     |   5%    | Dies on domain (mall ops)             |
|  15   | W14 IEP Drafting Co-Pilot          |  3  | **1** |  4  |  3  |  4  |  5  |    720     |   4%    | **CATASTROPHIC fail on domain (D=1)** |

---

## 3. Top 3 deep-dives (with RAT)

### 🏆 #1 — W1: ChaosLab for Agents

**Pitch (the wedge sentence):** _"A solo developer ships an LLM agent under deadline; it works in dev but breaks in unknown ways in production. ChaosLab is a meta-agent that runs your agent through a battery of LLM-specific fault classes (malformed tool output, prompt injection, context poisoning, latency spike), watches it fail via Phoenix traces, clusters the failure modes, generates a hardening recipe (prompt patch + tool-validation diff), and emits a regression-tested MR — autonomously, overnight."_

**Score breakdown:** B=4 (4-fault MVP scoped, 12 ambitious), D=5 (agent infra is Abu's home turf), V=5 (before/after resilience curve is screen-stopping), T=5 (Arize predicted GREEN), N=5 (4-source convergence in synthesis), J=5 (matches Arize's explicit bonus criterion + multi-Google-service composition).

**Track recommendation:** **Arize** (primary). Could flex to GitLab if the MR-emission loop is the hero.

**Why this wins ALL four judging criteria:**

- **Tech Implementation (5/5):** Composes Phoenix MCP + ADK + Agent Runtime + Cloud Run + A2A peer-agents + (stretch) GitLab MCP. The judges have personally written half these SDKs.
- **Design (5/5):** "Trace-as-UI" pattern (03 UX #8) + resilience curve as hero visual.
- **Potential Impact (5/5):** Every team building agents has this pain. The hackathon's own judges have this pain.
- **Quality of Idea (5/5):** Recursive "agent breaks agent" is meme-able + 4-source independent convergence in the brainstorm.

**3-minute demo arc:**

1. **0:00-0:30** — Pain. "Here's a customer-support agent we built in 30 minutes. Looks fine on the happy path." (show normal-input demo)
2. **0:30-1:00** — Setup. "ChaosLab installs in 1 command. Points at any ADK agent." (CLI shot)
3. **1:00-1:45** — Attack. ChaosLab fires 4 fault classes in parallel A2A. Phoenix shows the failures live. (split-screen trace-as-UI)
4. **1:45-2:15** — Reason. LLM-as-judge clusters: "67% of failures are tool-call validation gaps." Hardening recipe generated. (artifact view)
5. **2:15-2:45** — Re-attack. Same 4 faults; resilience curve: 60% fail → 8% fail. (the wow moment)
6. **2:45-3:00** — Receipt. "Agent did X. Used Y tools. Cost $Z. Tested N times." (UX #9)

**Riskiest Assumption Test (≤2 hours to validate, do BEFORE writing the main agent):**

> **Assumption:** Phoenix MCP exposes enough trace inspection AND eval-as-judge primitives that ChaosLab can run end-to-end without hand-rolling significant infra.

**Test (90 minutes):**

1. (30 min) `npm install @arizeai/phoenix-mcp` → connect via ADK `MCPToolset` → list available tools → confirm `phoenix_get_traces`, `phoenix_create_dataset`, `phoenix_run_experiment` exist as advertised
2. (30 min) Build a 3-line throwaway target agent + run one Phoenix trace end-to-end + read it back via MCP into a print statement
3. (30 min) Run one `phoenix_run_experiment` with a single canned eval rubric and confirm it returns scores

**Kill criteria:** If steps 1-3 each take >2x the estimate or Phoenix MCP doesn't expose write access to datasets, kill W1 and pivot to W8 or W12 (which have lower-risk integration paths).

**Reality-check risks:**

- 🟡 Scope creep on fault classes — mitigation: hard-cap at 4 for MVP
- 🟡 GitLab MCP MR-emission is stretch (Day 7) — accept Markdown artifact as fallback
- 🟢 Dynatrace, AP2, UCP NOT required — keeps the dependency surface small

---

### 🥈 #2 — W8: DataContract Sentinel (schema-drift → MR reflex)

**Pitch:** _"Data teams using Fivetran to ingest from 20+ SaaS sources lose days every quarter to schema changes that silently break downstream code. DataContract Sentinel watches Fivetran's schema_change event stream; on every event, the agent uses GitLab's semantic_code_search to find every line of downstream code consuming the changed column, writes the patch in Agent Sandbox, opens an MR with a passing regression test, and pings the right reviewer."_

**Score breakdown:** B=3 (3 MCPs + sandbox composition; moderate), D=5 (data infra is Abu's home turf), V=4 (PR-as-UI is clean; less hero than W1's curve), T=4 (Fivetran predicted YELLOW — trial squeeze but not crowded), N=5 (structurally impossible elsewhere — Airbyte + Copilot can't replicate), J=5 (all 4 criteria hit).

**Track recommendation:** **Fivetran** (primary — they want to see "data pipelines + agent reasoning" loop). Could also enter GitLab track if MR-creation is the hero.

**Why this wins:**

- **Tech (5/5):** Three MCPs composed (Fivetran + GitLab + Sandbox) — exactly what S5 (partner MCPs as primitives) is designed for.
- **Design (4/5):** GitHub-style PR view is universally legible to engineering judges.
- **Impact (5/5):** Every data team >10 ppl has this pain.
- **Idea (5/5):** Per 01-C2, no competitor stack has all three primitives.

**3-minute demo arc:**

1. **0:00-0:30** — Pain. "Stripe added a new column to `charges` last Tuesday. Found out via a Friday outage." (postmortem screenshot)
2. **0:30-1:00** — Setup. Sentinel watches Fivetran events for a connected workspace. (CLI shot)
3. **1:00-1:45** — Trigger. Mock a Stripe schema change → Sentinel fires. Semantic-search finds 7 downstream consumers. (terminal + GitLab UI)
4. **1:45-2:30** — Patch. Sandbox writes the migration in 3 of those files. Generates regression test. (diff view)
5. **2:30-2:50** — MR. Opens MR with diff + test + reviewer ping. CI passes. (GitLab UI)
6. **2:50-3:00** — Receipt. "Caught 7 break-points in 90 seconds. Saved ~6 hours of grep+patch."

**Riskiest Assumption Test:**

> **Assumption:** Fivetran's MCP exposes `schema_change` events as agent-callable polls/streams (not just dashboard-only), AND GitLab's `semantic_code_search` MCP tool is broadly available without needing Premium.

**Test (2 hours):**

1. (45 min) Sign up for Fivetran trial → connect a sample source → trigger a manual schema change → confirm event is visible via MCP `list_schema_changes` or equivalent (verify against `partner-fivetran.md`'s MCP tool inventory)
2. (45 min) Connect to GitLab trial workspace → confirm `gitlab.com/api/v4/mcp` exposes `semantic_code_search` on a free trial (NOT Premium-gated)
3. (30 min) Run one round-trip: "find files referencing `stripe.charges.amount_captured`" → confirm meaningful results

**Kill criteria:** If GitLab semantic_code_search is Premium-gated OR Fivetran schema events are dashboard-only, pivot to GitLab-track-only variant (`Pipeline Doctor` shape) or kill entirely.

**Reality-check risks:**

- 🟡 Fivetran 14-day trial squeeze — start trial Day 1 (before deadline judging starts) and rely on demo video as backstop
- 🟡 GitLab Premium gating on semantic_code_search — verify in RAT
- 🟢 No Dynatrace, AP2, UCP, A2UI dependencies — small surface

---

### 🥉 #3 — W12: Field-Service Pay-on-Completion Agent

**Pitch:** _"Hiring a plumber today means three apps (TaskRabbit, Venmo, email receipts), zero trust enforcement, and no way to verify completion before payment. Field-Service is a two-sided agent system: homeowner agent discovers UCP-listed contractors, A2UI renders role-specific work-order UI on both sides, on completion + photo proof an AP2 mandate triggers an x402 USDC payment instantly to the contractor's wallet. TaskRabbit + Venmo killer with cryptographic settlement."_

**Score breakdown:** B=3 (4 protocols, but Base testnet x402 is reliable + UCP sandboxes ship), D=5 (Abu's web3/AP2/x402 home turf is unique advantage), V=5 ("USDC arrived" live moment is hypnotic on screen), T=3 (cross-track — most likely MongoDB or Elastic, both with some saturation), N=5 (almost zero hackathon entries will go x402), J=5.

**Track recommendation:** **MongoDB** (job state + vendor catalog) — submit there because that bucket is RED-saturated and the protocol differentiation will visibly stand out from MongoDB-as-K/V entries. Alternative: Elastic (vendor search).

**Why this wins:**

- **Tech (5/5):** 4 underexplored protocols composed (UCP + A2UI + AP2 + x402) — unprecedented in any hackathon.
- **Design (5/5):** Different UI rendered per role (homeowner vs plumber phone) via A2UI is genuinely novel.
- **Impact (4/5):** Real TAM (TaskRabbit revenue $250M+/yr) but smaller per-incident than enterprise pains.
- **Idea (5/5):** Cryptographically-settled gig work is bleeding-edge thesis.

**3-minute demo arc:**

1. **0:00-0:30** — Pain. "Sink leaking. Three apps to call a plumber. Pay before they finish. No recourse."
2. **0:30-1:00** — Discovery. Homeowner: "My sink is leaking." Agent UCP-queries 3 nearby plumbers. (map UI)
3. **1:00-1:30** — Pick + dispatch. User picks. A2UI work order populates on plumber phone (different view per role). (split-phone screen)
4. **1:30-2:00** — Work. Plumber marks each step done via A2UI. Snaps "after" photo.
5. **2:00-2:30** — Pay. AP2 mandate triggers x402 → USDC settles on Base testnet. (live block explorer)
6. **2:30-3:00** — Receipt. Both sides see "$240 USDC settled. Tx 0xabc..."

**Riskiest Assumption Test:**

> **Assumption:** Google's `codelabs.developers.google.com/next26/adk-agent-commerce` codelab (AP2+UCP+ADK in 15 min) actually works end-to-end with the open-source UCP merchant sandbox (`steven2030/ucp-merchant`) AND x402 Base testnet rail is reliable for a demo.

**Test (2 hours):**

1. (60 min) Run Google's official AP2+UCP+ADK codelab end-to-end. Get one mock movie-ticket transaction completing.
2. (30 min) Swap codelab's mock payment for x402 Base testnet path. Confirm one USDC settlement happens.
3. (30 min) Clone `steven2030/ucp-merchant` locally → confirm it runs as advertised AND speaks UCP shopping vertical.

**Kill criteria:** If codelab fails OR x402 Base testnet has >1 second per-tx latency OR UCP sandbox merchant doesn't expose return/refund flows, descope to W3 (Receipt→Refund→Restock — same protocols, simpler closed-loop without contractor coordination).

**Reality-check risks:**

- 🟡 Track-EV math is weakest of top-3 (cross-track, no clean GREEN lane) — counteract via differentiation premium
- 🟡 x402 is on-trend but judges may not know it — needs clean explanation in demo opener
- 🟢 Codelab existence dramatically de-risks build (per 04)

---

## 4. Honorable mention — W6: World Cup Hotel Concierge

**Score 6,000 (38%)** — ties #2 but loses tiebreaker because D=3 (not Abu's domain) outweighed by V=5 + uniquely-timed demo.

**Why it might surprise:** The 2026 World Cup STARTS the day after submission deadline. The judging window (Jun 22 - Jul 6) is DURING active tournament group stage. No other idea here gets to time-stamp its demo video against a real-world live event. That's a video-narrative gift.

**Why it's not in the top 3:** Domain authenticity is 3, not 5. Abu doesn't run a hotel. A real concierge will see right through generic agent UX.

**If Abu wants to swap into top 3:** sub for W12 if he doesn't want to lean on the blockchain/x402 angle. Keep W1 + W8 + W6 as the alternate trio.

---

## 5. Why each bottom candidate dies (multiplicative-floor logic)

| Wedge                        | Killer axis      | Multiplier hit                      | Verdict                                                   |
| ---------------------------- | ---------------- | ----------------------------------- | --------------------------------------------------------- |
| W2 Retail Ops Command Bridge | B=2 × D=2        | 4 → 0.16x penalty                   | 4-protocol over-scope + mall-ops weakness compounds       |
| W11 Adaptive Triage Nurse    | D=2              | 0.4x penalty                        | Healthcare authenticity gap is binary for judges          |
| W4 Prior-Auth                | D=2              | 0.4x penalty                        | Same — judges will sniff fake healthcare-admin demo       |
| W7 Hospital Denials          | D=2              | 0.4x penalty                        | Same                                                      |
| W5 Fraud Analyst             | D=2              | 0.4x penalty                        | FinServ explicit weak spot                                |
| W13 Mall GM Marketing        | D=2              | 0.4x penalty                        | Mall-ops explicit weak spot                               |
| **W14 IEP Drafting**         | **D=1**          | **0.2x catastrophic**               | SPED is Abu's hardest-no domain                           |
| W9 Cross-Observability       | B=2              | 0.4x penalty                        | Dynatrace 24-48h warmup eats 25% of 9-day budget          |
| W10 Multi-Source Knowledge   | All mid, no peak | (no single killer but no axis is 5) | "Generally fine" doesn't win — needs ONE peak             |
| W15 FIFA Phishing            | All mid, no peak | Same                                | Browser-extension demos rarely punch through              |
| W3 Receipt→Refund→Restock    | T=3              | Borderline                          | Could move up if track-EV improves — has codelab scaffold |

**The pattern:** 6 of the bottom 11 die on Domain Authenticity. This is the single biggest score-killer for Abu specifically. Per 05 anti-pattern #5, "the judges will sniff out demo-quality from real-domain-knowledge" — and Abu's profile flags healthcare/SPED/mall/FinServ as the explicit weak spots. Multiplicative-floor kills these regardless of how impressive the protocol composition is.

---

## 6. The single highest-EV recommendation

**Build W1 (ChaosLab for Agents).** Submit under the Arize track.

**Math:** 12,500 raw / 80th percentile vs. #2 at 6,000 / 38th percentile. **The gap is 2x.** No tie. Even after applying a 30% "Arize-bias correction" (because Abu asked not to be pre-locked there), W1 still beats every other candidate by margin.

**Why this is honestly track-agnostic, not Arize-pre-locked:**

- W1 scored highest on 5 of 6 axes BEFORE the Track-EV axis was added
- Even if you set T=3 for W1 (treating Arize as YELLOW instead of GREEN), score = 4×5×5×3×5×5 = 7,500 — still #1
- W1 doesn't depend on the Arize TRACK existing — the recursive shape works on ANY observability primitive. We're using Phoenix because it's available; we're submitting Arize because of the saturation math

**If the W1 RAT fails (Phoenix MCP doesn't expose what we need):**

- **First fallback: W8 DataContract Sentinel** (Fivetran track) — moves Abu to a different track entirely, keeps the win path open
- **Second fallback: W12 Field-Service x402** (cross-track flexible) — leans on Abu's blockchain home turf

**Hard deadline for the W1 RAT decision:** **2026-06-03 EOD (Day 1, tomorrow).** If RAT passes, commit. If RAT fails, pivot to W8 Day 2.

---

## 7. What goes to `sahil-novelty-gate` next

Top 3 candidates for novelty validation:

1. **W1 ChaosLab for Agents** — search ETHGlobal corpus, Devpost galleries, DoraHacks for: "chaos engineering AI agent", "agent fault injection", "self-improving agent via trace replay", "Voltaros" (the parent ADK gallery project), "agent-chaos", "fault injection LLM"
2. **W8 DataContract Sentinel** — search for: "Fivetran schema drift agent", "DataContract", "data contract agent", "schema-change MR bot", "Airbyte schema change automation"
3. **W12 Field-Service Pay-on-Completion** — search for: "AP2 field service", "x402 contractor", "agent gig work", "TaskRabbit AI replacement", "UCP commerce agent"

Honorable mention to also check: **W6 World Cup Concierge** — "World Cup 2026 concierge agent", "FIFA 2026 hotel agent", "multilingual voice agent travel" — in case the timing differentiator is even sharper than W12's blockchain angle.

If novelty-gate kills W1, fall back to W8. If W8 also dies, W12. If all three die, swap in W6 and re-run.

---

## 8. Decision memo summary

| Field                              | Value                                                                       |
| ---------------------------------- | --------------------------------------------------------------------------- |
| **Recommended wedge**              | W1: ChaosLab for Agents                                                     |
| **Recommended track**              | Arize                                                                       |
| **Top alternates (track-diverse)** | W8 (Fivetran), W12 (cross-track), W6 (Elastic/Mongo)                        |
| **Build cadence**                  | Per 05 §Appendix C — 9-day plan exists for W1                               |
| **Riskiest assumption**            | Phoenix MCP exposes traces + datasets + experiments as agent-callable tools |
| **RAT deadline**                   | 2026-06-03 EOD                                                              |
| **Hard pivot rule**                | If RAT fails → W8 on Day 2 (no debate, just pivot)                          |
| **Next skill**                     | `sahil-novelty-gate` validates W1/W8/W12 not duplicates                     |

---

**Open the dialogue:** I'm going to fire `sahil-novelty-gate` on W1/W8/W12 next. Once that returns, Abu picks. If novelty kills W1, the recommendation auto-shifts to W8 without further discussion — but Abu can override at any point.
