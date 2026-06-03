# 07 — Novelty Gate Verdict

**Skill:** `sahil-novelty-gate` running Jaccard token-overlap against:
- ETHGlobal corpus: **17,180 projects** (all events 2019 → ETHGlobal Buenos Aires + Cannes 2026)
- Devpost local cache: 17 projects (light — sparse pre-deadline)
- DoraHacks local cache: 24 projects (including AWS Prompt The Planet — relevant comp)

**Threshold:** 0.15 (Jaccard). Any candidate above kills on "Quality of Idea" judging criterion.
**Compiled:** 2026-06-02

---

## TL;DR verdicts

| Wedge | Top match | Score | Verdict | Differentiator action |
|---|---|---|---|---|
| **W1 ChaosLab for Agents** | AWS AI Obs SLO Dashboard (DoraHacks) | **0.062** | 🟢 **GREEN — ship** | None needed. Truly novel shape. |
| **W8 DataContract Sentinel** | Orbit (RWA treasury, ETHGlobal) | **0.068** | 🟢 **GREEN — ship** | None needed. Schema-drift agent unrepresented anywhere. |
| **W12 Field-Service x402** | Agent Pay (ETHGlobal Cannes 2026) | **0.109** | 🟡 **YELLOW — pivot pitch** | Lean HARD on UCP+A2UI+photo-proof; protocol composition alone has prior art. |
| **W6 World Cup Concierge** | Community Host (ETHGlobal) | **0.062** | 🟢 **GREEN — ship** | Lean on World Cup timing + multilingual; "concierge-shaped agent" exists adjacently. |

**Outcome:** Three of four candidates pass cleanly. **W1 remains the top recommendation** by both multiplicative-floor scoring AND novelty (cleanest gate). The novelty gate does NOT change the W1 → W8 → W12 fallback order from `06-idea-rankings.md`.

---

## W1 — ChaosLab for Agents

**Token-overlap top matches:**

| # | Score | Project | Gallery | Why not a duplicate |
|---|---|---|---|---|
| 1 | 0.062 | AWS AI Observability SLO Dashboard | DoraHacks (awsprompttheplanet) | SLO dashboard for AI ops — **observes**, doesn't **attack**. Reactive, not active chaos engineering. |
| 2 | 0.060 | 0G-Gang | ETHGlobal Cannes 2026 | Context-as-NFT on 0G network. Entirely different domain (data sovereignty). |
| 3 | 0.059 | RoboAdvisor ERC-8004 | ETHGlobal New Delhi | Trustless on-chain robo-advisor. Different shape entirely. |
| 4 | 0.055 | AVS Scout | ETHGlobal Agentic Ethereum | DeFAI agent platform. Adjacent ("agent infrastructure") but different shape. |
| 5 | 0.054 | Amorphic | ETHGlobal London | "CAPTCHA for AI agents" — verifies agent vs human. Adjacent. Different problem. |

**Out-of-corpus check (from brainstorm 05 §Appendix):** Closest GitHub-shaped competitor is `deepankarm/agent-chaos` — a research repo, not a productized agent, not a hackathon submission. Not a duplicate.

**Verdict: 🟢 GREEN**

ChaosLab is genuinely novel. The corpus has 0 projects doing **active fault-injection against other LLM agents** with a closed-loop hardening output. The closest shape (AWS SLO dashboard) is observability without action; the next closest (AVS Scout) is agent infrastructure without resilience focus. Ship as-is.

**Strategic implication:** The 4-source convergence in the brainstorm (01-C5, 03-Gap-13, 03-Gap-1, 05-#9) suggested this would be the obvious hackathon wedge for the Arize track. The novelty gate confirms that obviousness has NOT materialized into actual submissions yet. We have unilateral first-mover advantage in the corpus.

---

## W8 — DataContract Sentinel

**Token-overlap top matches:**

| # | Score | Project | Gallery | Why not a duplicate |
|---|---|---|---|---|
| 1 | 0.068 | Orbit | ETHGlobal HackMoney 2026 | Autonomous RWA treasury on Arc + Circle custody. Different domain (DeFi treasury, not data pipelines). |
| 2 | 0.068 | Negravis | ETHGlobal Cannes | AI-native oracle system with multi-agent verification. Adjacent (multi-agent + AI) but different. |
| 3 | 0.068 | Optimism ATST Subgraph | Scaling Ethereum 2023 | Attestation indexing subgraph. Different — passive indexing, not active patching. |

**Verdict: 🟢 GREEN**

Schema-drift-to-MR-reflex agents do not exist anywhere in the corpus. The closest adjacent ideas are all blockchain-data-pipeline-shaped, not ELT-data-contract-shaped. Airbyte+Copilot, dbt, and Monte Carlo all have related products but none has the **agent-driven, MCP-composed, autonomous MR-emission shape**. Ship as-is.

**Strategic implication:** The Fivetran track is YELLOW saturation per `06-hidden-field.md` (trial squeeze deters builders). W8 is a sharp, structurally-impossible-elsewhere wedge in a low-saturation track. Strong fallback if W1 RAT fails.

---

## W12 — Field-Service Pay-on-Completion (the 🟡 YELLOW case)

**Token-overlap top matches:**

| # | Score | Project | Gallery | Shape overlap |
|---|---|---|---|---|
| 1 | 0.109 | **Agent Pay** | ETHGlobal Cannes 2026 | "Decentralized API database for AI agents, payable with crypto. Agents discover and pay for services via x402." Same primitive (agent + x402 discovery + payment), **different application** (agent-buys-API, not human-hires-human-via-agent). |
| 2 | 0.100 | **DealMint** | ETHOnline 2025 | "Negotiation-first checkout. A2A → AP2 mandate. PYUSD payment, Avail cross-chain." **Same protocol composition (A2A + AP2 + on-chain settlement), different checkout shape — no field service, no completion-proof, no role-specific UI.** |
| 3 | 0.080 | Jurex Network | ETHGlobal Cannes 2026 | "Court for the agent economy. Agents hire each other, disputes resolve onchain." Adjacent — escrow + x402, but for agent-to-agent commerce, not human-to-human. |
| 4 | 0.078 | Cannes Dance | ETHGlobal Cannes 2026 | USDC booking marketplace with Dynamic embedded wallets. Different application (social booking). |
| 5 | 0.077 | Jarvis | ETHGlobal Buenos Aires | "x402 to pay or buy any service, request an uber from chatgpt." Same primitive (x402 for arbitrary commerce), different application (LLM-driven retail purchases). |

**Verdict: 🟡 YELLOW — protocol composition has prior art; SPECIFIC APPLICATION is unique**

The honest truth from the data: **4 of the top 5 matches are from ETHGlobal Cannes 2026 alone**. The hard-tech primitives (A2A + AP2 + x402 + USDC + on-chain settlement) are now well-trafficked in the agentic-crypto world. If W12 is submitted as "an agent that pays via x402," the Arize judges have likely seen the shape before.

**What's still genuinely novel about W12:**

1. **UCP (Universal Commerce Protocol) for contractor discovery** — NONE of the prior projects use UCP. They use ENS, decentralized API registries, or hard-coded service catalogs. UCP is brand-new and almost no one has built with it.
2. **A2UI rendering DIFFERENT views per role** — homeowner sees discovery + work-order tracker; contractor sees task + photo-upload + completion. Per the 04 protocol-wedges agent, A2UI is dogfooded by Google in Opal but adoption is still ~zero in hackathons.
3. **Photo-proof as the AP2 mandate trigger condition** — none of the prior projects use vision-based completion verification as the payment trigger. They settle on time-locks (DealMint), API responses (Agent Pay), or dispute resolution (Jurex).
4. **Pay-on-completion model** — opposite of DealMint's pay-on-acceptance. Solves a different trust-direction problem.
5. **Two-sided HUMAN-to-HUMAN coordination with agents as intermediary** — every prior project is agent-to-agent or human-to-API. None is human-hires-human-with-agent-as-witness.

**Differentiator action if Abu picks W12:**

The pitch sentence must NOT lead with "x402 + AP2" — judges have heard it. Lead with the **physical-world-verification + role-specific A2UI** angle:

> "Hiring a plumber today means three apps (TaskRabbit, Venmo, email receipts), zero trust enforcement, no way to verify completion before payment. Field-Service is a two-sided agent: UCP-discovers contractors, A2UI renders role-specific work-order UI on both sides (homeowner gets discovery + tracking; contractor gets task + photo-upload), and on **photo-verified completion**, an AP2 mandate triggers x402 USDC settlement. Cryptographic completion proof for physical work."

**Reality check:** The yellow flag is real. If Abu picks W12, expect to spend Day 1 RAT testing whether the photo-proof + A2UI angle is achievable in 9 days — because without those, W12 collapses into "another A2A+AP2+x402 demo" the Cannes judges have seen 6 of.

---

## W6 — World Cup Hotel Concierge (honorable mention)

**Token-overlap top matches:**

| # | Score | Project | Gallery | Why not a duplicate |
|---|---|---|---|---|
| 1 | 0.062 | **Community Host** | ETHGlobal | *"AI agent. It plays a welcoming and assistive role, much like the concierge of a hotel."* **Same persona shape (concierge-like agent)** — adjacent but not multilingual, not World Cup, not action-shaped. |
| 2 | 0.056 | Airbnb-DApp | ETHGlobal | Decentralized booking platform. Different — UI for booking, not voice-agent concierge. |
| 3 | 0.045 | ScoutX | ETHGlobal | Unspecified — low overlap. |

**Verdict: 🟢 GREEN with one footnote**

"Concierge-shaped agent" exists adjacently (Community Host). But the differentiators are strong:
- **Multilingual voice (7 languages)** — Community Host is text + English-only
- **2026 World Cup timing** — demo recorded against live tournament during judging window
- **Action-shaped (real tool calls to OpenTable / Uber / luggage / transit)** — Community Host is conversational

Ship as-is if Abu pivots from W12 → W6.

---

## What this novelty pass found, but the brainstorm missed

Reading the closest matches surfaces useful intelligence beyond pure yes/no novelty:

1. **ETHGlobal Cannes 2026 (May 2026) is the dominant prior-art source.** 4 of W12's top 5 matches + W1's #2 + W8's #2 are from Cannes 2026. The agentic-crypto world is actively shipping in this protocol space. **Implication:** any web3-leaning wedge (W12) is competing with builders who shipped 30 days ago. Non-web3 wedges (W1, W8) are unaffected.

2. **"Jarvis" (ETHGlobal Buenos Aires)** — x402 agent that pays for arbitrary services from ChatGPT — is conceptually a thin slice of what W12 wants to be. If Abu picks W12, **read Jarvis end-to-end first** to make sure W12's pitch frames itself differently.

3. **No corpus project does cross-LLM-trace × production-APM-trace fusion** (W9 — which scored low on build feasibility anyway). The shape remains novel; just not buildable in 9 days solo.

4. **"AWS AI Observability SLO Dashboard" (DoraHacks)** — closest W1 match — is observability-for-AI but in the SLO direction. If we ever pivot W1 toward "SLO Sentinel for Agents" that's adjacent territory; the current ChaosLab framing avoids overlap.

---

## Final recommendation (unchanged from idea-generator)

**Build W1 (ChaosLab for Agents). Submit under the Arize track.**

| Decision input | Value |
|---|---|
| Multiplicative-floor score (06) | 12,500 / 80% (clear runaway) |
| Novelty gate verdict | 🟢 GREEN — no semantic duplicates in 17,000+ projects |
| Track-EV math (06-hidden-field) | Arize predicted GREEN (least-crowded) |
| Build feasibility | 9-day plan exists at `05 §Appendix C` |
| RAT deadline | 2026-06-03 EOD (tomorrow) |
| Fallback if RAT fails | W8 DataContract Sentinel (also GREEN gate, also strong score) |

**The novelty gate did NOT shuffle the recommendation order:**

1. W1 (12,500 + GREEN gate) — primary, ship
2. W8 (6,000 + GREEN gate) — fallback 1
3. W6 (6,000 + GREEN gate w/ footnote) — fallback 2 if Abu rejects the meta-recursion vibe
4. W12 (5,625 + 🟡 YELLOW gate) — fallback 3, only if Abu wants to pay the differentiator-pivot tax

---

## Handoff to next step

This file ends the brainstorm pipeline. Next decisions are Abu's:

1. **Approve W1 as the wedge?** If yes → fire `sahil-spec-writer` to produce the PRD/architecture/UX-spec/epics/stories artifact set.
2. **Run W1's RAT first?** Per `06-idea-rankings.md` §3, the 90-min RAT is: install `@arizeai/phoenix-mcp`, connect via ADK MCPToolset, run one trace + one experiment end-to-end. If it works → commit. If not → pivot to W8 Day 2.
3. **Want to brainstorm more?** If yes, the brainstorm files are persistent — we can re-run `sahil-idea-generator` with a different bias (e.g., "track-lock to MongoDB", "ignore Arize entirely") and regenerate rankings.

The brainstorm folder (`brainstorm/00-synthesis.md` + `06-idea-rankings.md` + `07-novelty-gate.md`) is the durable record of how this decision was made. Abu can always re-open and challenge it.
