# PRD — Phoenix Audit

**Project name:** Phoenix Audit (LOCKED 2026-06-04; working names through 2026-06-03 were "ChaosLab" then "Trust Auditor")
**Hackathon:** Google Cloud Rapid Agent Hackathon
**Track:** Arize (Phoenix observability)
**Deadline:** 2026-06-11, 2:00 PM Pacific Time
**Status:** DRAFT — pending Abu approval
**Approved by Abu:** [ ] pending

---

## Glossary (so we never mix these up again)

- **Customer** — the company buying Phoenix Audit (e.g., a health-insurance carrier, a fintech startup).
- **Operator** — the human at the customer who actually runs audits day-to-day. Persona name: **Maya / Priya**. Role: Director of AI Governance / AI Safety Officer / Head of Responsible AI.
- **Economic buyer** — the executive one level above the Operator who signs the contract. CRO / CISO / Chief AI Officer.
- **Target agent** — the AI agent the Customer wants audited (their prior-auth bot, their internal copilot, their voice agent). NOT "customer's agent" or "their agent" — call it "target agent" consistently.
- **Phoenix Audit** — our product. An AI agent that audits target agents.

---

## Goal

**Phoenix Audit is an AI agent that audits other AI agents — for safety, behavior, and EU AI Act compliance.** Companies are shipping production AI agents (customer-support bots, healthcare prior-auth, fintech copilots, coding helpers) faster than they can prove those agents behave correctly. When the regulator asks "show me every decision your AI made last quarter and prove it didn't violate GDPR / HIPAA / EU AI Act," the compliance team's answer today is "we have logs in Datadog, slides in Confluence, and a stack of screenshots." Phoenix Audit produces the answer instead — a cryptographically signed, regulator-ready audit report generated in under 90 seconds from real Phoenix traces (6-test demo battery; see Known limitations for the full picture).

Same closed-loop engine as the prior ChaosLab working name, reframed: from "chaos engineer's testing tool" to **"compliance officer's audit machine."**

**One-line pitch (judge-facing):**

> Phoenix Audit — the AI agent that audits your other AI agents. Continuous, signed, regulator-ready, Phoenix-native.

**The headline demo metric (per Bedrock/Microsoft winner pattern):**

> "3 failures, 1 root cause, patch in 4 seconds."

**Sponsor-native fit:**
Phoenix Audit is the only Arize-track submission that uses Phoenix as the substrate for closed-loop self-improvement _applied to compliance evidence_ — read traces via MCP → cluster failures with LLM-as-judge → write findings back as Phoenix experiments + annotations → render a regulator-ready signed PDF. The Arize Devpost section explicitly bonuses agents that "use their own observability data to improve over time"; Phoenix Audit makes that bonus the entire product, not a feature.

**Direct competitive cut:** AIUC ($15M seed, the category leader) sells quarterly enterprise audits + an insurance certificate written by the same shop that did the audit. Phoenix Audit sells continuous, self-serve, signed evidence keyed to the Customer's OWN compliance officer's Cloud KMS key — and the audit traces themselves live in the Customer's Phoenix project under the Customer's data-retention policy, not in Phoenix Audit's tenancy (see ADR-013 in `docs/architecture.md`) — zero auditor/insurer conflict of interest; no persisted cross-tenant evidence (Phoenix Audit reads the Customer's full project span set transiently in-process during the audit window, filters it to the audit run, and holds no copy after report generation — per ADR-013's tradeoff disclosure). See `research/google-cloud-rapid-agent/brainstorm/19-ai-agent-governance-competitive-landscape.md` for the full landscape.

---

## Target users + value prop

- **Primary user (Operator):** Director of AI Governance / AI Safety Officer / Head of Responsible AI at a 5K+ employee company running production AI agents (2,000+ such roles open on LinkedIn US per `brainstorm/22`)
- **Economic buyer (one level up):** CRO / CISO / Chief AI Officer who signs the procurement contract (LOAD-BEARING: every Phoenix Audit artifact must work both for the Operator's daily workflow AND a board-ready 1-pager — per `brainstorm/22` riskiest-assumption analysis)
- **Secondary user:** ML platform / DevSecOps team running production target agents needing continuous pre-deploy + post-deploy audit evidence (uses Phoenix Audit in their CI pipeline)
- **Value prop:** Phoenix Audit reduces the EU AI Act Annex IV documentation cycle from "Big-4 consulting €80K-€250K + 12-18 months" to "90 seconds, signed, keyed to a commit SHA, continuously updatable"
- **Measurable outcome demonstrated in demo:** **6 high-signal adversarial tests** run sequentially against a target prior-auth agent (~90 seconds end-to-end at current A2A round-trip latency, see RAT-2 finding IF-14); 3 fail; root-cause clustering collapses them into 1 cluster; hardening recipe generated in 4 seconds. Headline: _"3 failures, 1 root cause, patch in 4 seconds."_

  The 6 tests are NOT invented by us — each is sourced from an industry-standard adversarial dataset and cited by ID in the audit report. Specifically: 2 from **[HarmBench](https://github.com/centerforaisafety/HarmBench)** (MIT — CAIS), 1 from **[OWASP LLM Top 10 (2025) LLM01 — Prompt Injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/)** (CC-BY-SA), 2 from **[MITRE ATLAS v5.1.0](https://atlas.mitre.org/)** (AML.Txxxx technique IDs), and 1 from **[CARES](https://arxiv.org/abs/2505.11413)** (healthcare-specific). Every Phoenix Audit report cites the source dataset + ID per test — judges recognize these frameworks instantly. See `NOTICE` for attribution requirements per each dataset's license.

---

## What kinds of target agents can Phoenix Audit audit?

**Any AI agent that can receive a message from outside.** Phoenix Audit is framework-agnostic, hosting-agnostic, and protocol-agnostic — provided the target exposes some kind of interface.

**Supported frameworks** (verified mapping per `research/google-cloud-rapid-agent/brainstorm/21-trust-auditor-architecture.md`):

| Framework / shape                                                         | How Phoenix Audit connects                                                                                                               |
| ------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| Google ADK agent                                                          | `RemoteA2aAgent(AgentCard.from_url(...))` — A2A protocol (Google's standard for agent-to-agent calls, v1.2 GA March 2026)                |
| LangChain / LangGraph                                                     | HTTP wrapper — Customer exposes their LangChain runnable via FastAPI; Phoenix Audit calls via `httpx`. Tier 2 instrumentor reads traces. |
| CrewAI                                                                    | HTTP wrapper                                                                                                                             |
| OpenAI Agents SDK                                                         | HTTP wrapper                                                                                                                             |
| Custom Python / Node / Go agent                                           | HTTP endpoint that accepts a prompt + returns a response                                                                                 |
| Voice agent (Vapi, ElevenLabs Conversational, LiveKit Agents)             | HTTP API endpoint (most voice agents expose one for test/setup)                                                                          |
| Browser-use / Skyvern / web-automation agents                             | HTTP API endpoint                                                                                                                        |
| Any HTTP endpoint at all (n8n, Zapier AI Action, Make scenario, anything) | Tier 3 black-box                                                                                                                         |

**Where the target agent can be hosted:** anywhere. Google Cloud Run, AWS Lambda, Vercel Edge, self-hosted on a VPS, on-prem behind a corporate VPN, locally on the Operator's laptop. Phoenix Audit just needs to be able to reach the target's address.

**What target agents we CANNOT audit:**

- Agents with no external interface at all (e.g., a LangChain chain that only runs inside another Python script, never exposed via HTTP/A2A). Rare in production because production agents need to receive requests from someone.
- Agents behind a firewall Phoenix Audit can't reach. Workaround: self-host Phoenix Audit inside the Customer's network (later product roadmap, NOT in hackathon scope).

**Where Phoenix Audit itself runs:** Google Cloud Run. The "Google Cloud" part is where WE run from; it has nothing to do with where the target agent runs. This is a key clarification — Phoenix Audit is NOT limited to auditing Google Cloud agents.

---

## Two audit depths the Customer can choose

The amount of detail Phoenix Audit can produce depends on how much access the target agent gives. The Operator picks the depth in the UI before running the audit.

### Depth 1 — Black-box audit (zero setup)

- The Operator pastes the target's URL or A2A address.
- Phoenix Audit sends adversarial prompts via HTTP/A2A, captures the responses, judges them.
- Phoenix Audit only sees the OUTSIDE — input messages + output responses.
- Cannot do trace-tree root-cause clustering across internal failures (the cluster step has nothing to cluster).
- Audit report still produced, but findings list each failure independently.
- Onboarding time: ~30 seconds.
- Use case: Customer wants a fast audit without code changes; or the target is a third-party agent the Customer doesn't own.

### Depth 2 — Instrumented audit (3-line setup)

- The Operator adds a 3-line OpenInference instrumentation snippet to the target agent's startup code, pointing traces at a Phoenix project Phoenix Audit can read.
- Phoenix Audit sees the INTERNAL trace tree of the target — every tool call, every LLM call, every retry.
- Trace-tree clustering becomes possible: 3 surface-level failures that share one upstream span become 1 root cause finding.
- This is the demo path.
- Onboarding time: ~5 minutes (paste 3 lines, redeploy target agent).
- Use case: Customer wants the full Phoenix Audit experience — the cascade-flip moment, the hardening recipe, the regulator-ready evidence with internal trace evidence pointers.

**The 3-line snippet** (illustrative — final form will match the OpenInference instrumentor for the target's framework):

```python
from phoenix.otel import register
register(project_name="acme-prior-auth", auto_instrument=True)
```

**No source code uploads required for either depth.** Phoenix Audit reads runtime behavior — it does NOT do static analysis of `agent.py`. Static analysis is a separate product category (CodeQL, Snyk, Semgrep) and outside Phoenix Audit's scope.

---

## User flow (Operator's actual experience, Monday morning)

Step-by-step, what Maya does when she opens Phoenix Audit:

1. **Lands on the dashboard.** Sees one button: "Start a new audit." Below it, her history (every audit she's ever run, each linked to a signed PDF report).

2. **Clicks "Start a new audit."** A wizard opens with 4 fields:
   - **Target agent address** — URL or A2A address
   - **Audit depth** — Depth 1 (black-box, zero setup) or Depth 2 (instrumented, 3-line snippet — link to instructions)
   - **Regulatory frame** — EU AI Act / NIST AI RMF / HIPAA / SOC 2 + AI / Custom
   - **Override settings** (optional) — pick which adversarial categories to skip, test count cap, etc.

3. **Clicks "Run audit."** Phoenix Audit's Inspector sub-agent first sends a few probe questions to fingerprint the target: "What's your purpose? What tools do you have?" Based on the responses, it classifies the target ("This is a healthcare prior-auth agent with 5 tools") and picks a tailored test battery.

4. **Watches the live audit.** A progress screen shows:
   - Test count (1/6 → 6/6)
   - Pass/fail markers appearing in real time
   - Live Phoenix trace stream on the right (each test = a Phoenix experiment row)
   - Estimated time remaining (~90 seconds for a typical audit)

5. **Sees the result.** 44 tests passed, 3 failed. The 3 failures collapse into 1 root cause cluster via Phoenix MCP trace-tree analysis. ("All 3 failures happen because the agent calls `check_formulary` without first calling `verify_benefits`.")

6. **Reviews the findings.** Each finding has: the failing test prompt, the agent's response, the trace span where it went wrong, the regulatory framework article it violates (e.g., "EU AI Act Article 9 — risk management"), a suggested fix.

7. **Generates the hardening recipe.** One click → a markdown patch is produced in 4 seconds with concrete remediation steps for the engineering team. Optionally, one more click opens a GitLab merge request directly in the target agent's repo (Customer authenticates GitLab once at setup).

8. **Downloads the regulator-ready report.** Cryptographically signed PDF + signed JSON, keyed to the target agent's commit SHA. Maya files it in her audit registry. The CRO can present the executive-summary 1-pager to the board unedited.

This whole flow is end-to-end against real services. No mocks. Real target. Real Phoenix. Real Gemini-3.5-Flash judging. Real Cloud KMS signing. Real Cloud Storage delivery.

---

## Demo moment (90-second judge walkthrough)

What the 3-minute video shows judges:

1. **0:00-0:15 — Cold open.** Maya at her desk, four browser tabs open: Phoenix, GitLab, a Google Doc titled "Q3 Compliance Report — DRAFT," a Slack thread with the AI Platform team. Overlay headline: "EU AI Act enforces August 2 2026. €15M penalty. Big-4 charges €80K per pack."

2. **0:15-0:45 — The product appears.** `phoenixaudit.app` loads. Maya clicks "Start a new audit." Pastes the target prior-auth agent's Cloud Run URL. Picks "Depth 2 — instrumented" and "EU AI Act — high-risk system." Clicks Run.

3. **0:45-1:30 — The live audit.** Test count climbs (1/6, 3/6, 5/6…). Phoenix trace rows appear in the right pane in real time. Pass/fail markers light up. Each test header shows its source citation (e.g., "Test 4 / 6 — MITRE ATLAS AML.T0051"). Final result: 3 pass, 3 fail.

4. **1:30-2:15 — THE CASCADE-FLIP MOMENT.** 6/6 done. Dashboard shows 3 pass / 3 fail. Maya clicks the "Failures" tab. The 3 failures collapse into ONE cluster. The Phoenix trace tree expands; the common failed span lights up: `check_formulary` called without first calling `verify_benefits`. Maya clicks "Generate hardening recipe." Markdown patch renders in 4 seconds. Voiceover: _"This is the moment everyone wants their compliance tool to do but nobody has — three failures collapse into one root cause. Phoenix Audit isn't just telling Maya the bot is wrong — it's telling her **why** it's wrong, **where in the trace** it went wrong, and **what to change**. Three failures, one root cause, patch in four seconds."_

5. **2:15-2:45 — The Annex IV pack.** PDF preview renders. 9 sections visible (EU AI Act Articles 9 / 11 / 12 / 13 / 14 / 15 / 72). Maya clicks "Sign & file." Cloud KMS signing visible in the UI. Signed PDF + signed JSON download. Voiceover: _"What Maya now has — produced in under 90 seconds — is the EU AI Act Annex IV technical documentation pack. Cryptographically signed. Keyed to commit 8a4f2c1. Costs Big-4 €80,000 and 18 months. Maya did it before her coffee finished."_

6. **2:45-3:00 — Outro.** URL on screen: `phoenixaudit.app`. Logos: Arize Phoenix + Google Cloud Agent Builder. _"Built with Arize Phoenix MCP and Google Cloud Agent Builder. Try it at phoenixaudit.app."_

**The wow moment:** _Three independent test failures collapsing into one root-cause cluster via Phoenix MCP trace clustering, with a patch generated in 4 seconds. Tells the entire story — adversarial testing, observability-driven analysis, self-improvement loop, regulator-ready artifact — in one frame._

---

## Known limitations (RAT-2 empirical findings, 2026-06-04)

We ran an architecture validation pass (`RAT-2-results.md`) before locking the spec. Both demo-critical pipelines pass end-to-end, but two real constraints emerged that this PRD acknowledges honestly:

- **A2A round-trip latency is ~16 seconds per call** at current ADK 2.1.0 wire performance (no-LLM, localhost; RAT-2 IF-14 measured 15.87s as the single empirical data point). Two mitigation candidates — connection pooling and `asyncio.gather` parallel execution — are listed in RAT-2 IF-14 but **not yet measured**. For the hackathon we cap the demo at **6 tests** so the audit can fit the 90-second video window if at least one mitigation lands; sequential worst-case is ~144s. The 90s budget is **projected, not measured.** See `docs/session-shape.md` §Latency budget for the per-probe arithmetic (Patch #21 + ADR-016). Investigating the latency further is post-hackathon work (logged as IF-14 in audit-notes).
- **Phoenix Cloud free tier is 25,000 spans/month**, and a single A2A round-trip emits ~41 spans (~1,927 per 47-test audit, ~250 per 6-test audit). We mitigate by running **self-hosted Phoenix in Docker** for all development (see `infra/phoenix-self-host/`) and reserving Phoenix Cloud quota for the final demo recording + judging-window deployment.

The "3 failures, 1 root cause, patch in 4 seconds" headline survives both constraints — Test 3 of RAT-2 empirically verified the cascade-flip mechanic works on real Phoenix data.

---

## Out of scope (and why)

Per Abu's directive: "no MVP-vs-stretch framing — ship everything." But these are genuinely orthogonal and excluded from the hackathon scope:

- **Static source-code analysis of the target agent's `agent.py`** — different product category (CodeQL, Snyk, Semgrep). Phoenix Audit is a RUNTIME audit only. We read behavior, not code.
- **Production-grade scaling** (>1 concurrent audit session) — Cloud Run `min-instances=1` sufficient for judging window
- **On-premise / self-hosted Phoenix** — Phoenix Cloud only for the demo; dev uses self-hosted Phoenix Docker on Abu's VPS (`reference-vps-available` memory entry)
- **Authenticated multi-tenant Phoenix Audit as a service** — single-tenant judging-window demo only; multi-tenant + billing is post-hackathon roadmap
- **Real customer / PHI / PII processing in the demo** — synthetic target agent only (uses MIMIC-IV-style synthetic prior-auth data per `brainstorm/11` healthcare research)
- **A2UI / AP2 / UCP protocol integration** — not the wedge (those are commerce-adjacent)
- **Self-hosted Phoenix Audit inside Customer firewalls** — post-hackathon roadmap for enterprise customers with no-egress policies

---

## Judging criteria alignment

| Criterion                        | Weight | How Phoenix Audit scores                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| -------------------------------- | ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Technological Implementation** | 25%    | Phoenix MCP + Phoenix Python SDK + Google ADK + Cloud Run + A2A peer protocol + GitLab MCP + OpenInference instrumentation + LLM-as-judge clustering + Cloud KMS signing. 8+ Google + partner primitives composed in one closed loop. Judges (Arize + Google DevRel) have written half these SDKs.                                                                                                                                                             |
| **Design**                       | 25%    | Trace-as-UI hero pattern (per `architecture/05` §2). Live audit progress + failure clustering visualization. Per-finding color palette + regulatory-article badges. Framer Motion cascade-flip when 3 failures collapse into 1 root cause. No template look — Pattern D production polish (per `brainstorm/05-prior-winners.md`).                                                                                                                              |
| **Potential Impact**             | 25%    | EU AI Act enforces 59 days from today, €15M penalty. 2,000+ Director-of-AI-Governance jobs open on LinkedIn US TODAY actively buying audit tools at $30K-$300K ACV (Credo AI, Holistic AI, Fiddler, IBM watsonx.governance, OneTrust, Microsoft Purview). Mid-market unserved by AIUC (the leader). Phoenix Audit fits the named buyer's named workflow on Day 1 — see `brainstorm/22-ai-trust-auditor-buyer-persona.md`.                                      |
| **Quality of Idea**              | 25%    | 4-source convergence in the brainstorm + Direction-A research pivot (pain points, winner patterns, sponsor hidden capabilities, vertical demand). No closed-loop chaos-for-agents OR continuous mid-market AI-audit product exists per `brainstorm/12-saturation-map.md` and `brainstorm/19-ai-agent-governance-competitive-landscape.md`. Arize-track-aligned recursive observability — "agent uses its own observability data" is the literal sponsor brief. |

---

## README shape (§13 — required ordering)

The shipped `README.md` must contain in this order:

1. Project name + one-line pitch
2. Demo URL (Cloud Run-hosted, NOT localhost)
3. Screenshot/GIF of the cascade-flip moment (above the fold) — auto-generated from the Devpost OG image
4. Run-locally: 3 commands max (`uv sync && pnpm install && make dev`)
5. Cross-framework target support matrix (1-line summary, link to docs)
6. License (Apache-2.0)

Current `/README.md` already aligned with this ordering as of 2026-06-04 rebrand commit.

---

## Research references

**Phoenix Audit synthesis + direction lock (read these first):**

- Master plan: `research/google-cloud-rapid-agent/PLAN-AI-TRUST-AUDITOR.md` (historical Trust Auditor name; superseded by Phoenix Audit lock)
- Hackathon primer: `research/google-cloud-rapid-agent/HACKATHON-PRIMER.md`
- Competitive landscape: `research/google-cloud-rapid-agent/brainstorm/19-ai-agent-governance-competitive-landscape.md`
- EU AI Act audit artifacts: `research/google-cloud-rapid-agent/brainstorm/20-ai-compliance-artifacts-required.md`
- Phoenix Audit architecture (RAT-cited APIs): `research/google-cloud-rapid-agent/brainstorm/21-trust-auditor-architecture.md`
- Buyer persona deep dive: `research/google-cloud-rapid-agent/brainstorm/22-ai-trust-auditor-buyer-persona.md`
- Demo arc + product launch path: `research/google-cloud-rapid-agent/brainstorm/23-trust-auditor-demo-and-product-path.md`
- Google tool ecosystem (confirmed-vs-vapor): `research/google-cloud-rapid-agent/brainstorm/24-google-tools-confirmed-vs-vapor.md`

**Original wedge research (still relevant for technical decisions):**

- Master research folder: `research/google-cloud-rapid-agent/`
- Entry guide: `research/google-cloud-rapid-agent/READING-ORDER.md`
- Locked wedge (historical ChaosLab framing): `research/google-cloud-rapid-agent/brainstorm/06-idea-rankings.md` §W1
- Novelty validation: `research/google-cloud-rapid-agent/brainstorm/07-novelty-gate.md`
- Agent shapes: `research/google-cloud-rapid-agent/context/01-agent-shapes-taxonomy.md`
- Cross-framework integration: `research/google-cloud-rapid-agent/context/04-cross-framework-instrumentation.md`
- Phoenix MCP technical (RAT-verified): `research/google-cloud-rapid-agent/architecture/02-phoenix-deep-dive.md`
- Hero UX patterns: `research/google-cloud-rapid-agent/architecture/05-ux-and-demo.md`
- Original 4 fault classes (now repositioned as adversarial test categories): `research/google-cloud-rapid-agent/architecture/04-fault-injection-eval.md`
- Attribution context (`deepankarm/agent-chaos`, Apache-2.0 attribution-only per ADR-006 amended): `research/google-cloud-rapid-agent/architecture/01-reference-implementations.md`
