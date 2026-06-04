# PRD — Phoenix Audit

**Project name:** Phoenix Audit (LOCKED 2026-06-04; working names through 2026-06-03 were "ChaosLab" then "Trust Auditor")
**Hackathon:** Google Cloud Rapid Agent Hackathon
**Track:** Arize (Phoenix observability)
**Deadline:** 2026-06-11, 2:00 PM Pacific Time
**Status:** DRAFT — pending Abu approval
**Approved by Abu:** [ ] pending

---

## Goal

**Phoenix Audit is an AI agent that audits other AI agents — for safety, behavior, and EU AI Act compliance.** Companies are shipping production AI agents (customer-support bots, healthcare prior-auth, fintech copilots, coding helpers) faster than they can prove those agents behave correctly. When the regulator asks "show me every decision your AI made last quarter and prove it didn't violate GDPR / HIPAA / EU AI Act," the compliance team's answer today is "we have logs in Datadog, slides in Confluence, and a stack of screenshots." Phoenix Audit produces the answer instead — a cryptographically signed, regulator-ready audit report generated in 90 seconds from real Phoenix traces.

Same closed-loop engine as the prior ChaosLab working name, reframed: from "chaos engineer's testing tool" to **"compliance officer's audit machine."** Point Phoenix Audit at any agent (ADK, LangChain, CrewAI, browser-use, voice, or HTTP black-box). It runs a tailored adversarial battery, watches the agent in Phoenix traces, uses LLM-as-judge to cluster failures, generates a hardening recipe MR, and produces an EU AI Act Annex IV pack keyed to a commit SHA.

**One-line pitch (judge-facing):**

> Phoenix Audit — the AI agent that audits your other AI agents. Continuous, signed, regulator-ready, Phoenix-native.

**The headline demo metric (per Bedrock/Microsoft winner pattern):**

> "3 failures, 1 root cause, patch in 4 seconds."

**Sponsor-native fit:**
Phoenix Audit is the only Arize-track submission that uses Phoenix as the substrate for closed-loop self-improvement _applied to compliance evidence_ — read traces via MCP → cluster failures with LLM-as-judge → write findings back as Phoenix experiments + annotations → render a regulator-ready signed PDF. The Arize Devpost section explicitly bonuses agents that "use their own observability data to improve over time"; Phoenix Audit makes that bonus the entire product, not a feature.

**Direct competitive cut:** AIUC ($15M seed, the category leader) sells quarterly enterprise audits + an insurance certificate written by the same shop that did the audit. Phoenix Audit sells continuous, self-serve, signed evidence keyed to the customer's OWN compliance officer's Cloud KMS key — zero auditor/insurer conflict of interest. See `research/google-cloud-rapid-agent/brainstorm/19-ai-agent-governance-competitive-landscape.md` for the full landscape.

---

## Target users + value prop

- **Primary user:** Director of AI Governance / AI Safety Officer / Head of Responsible AI at a 5K+ employee company running production AI agents (2,000+ such roles open on LinkedIn US per `brainstorm/22`)
- **Economic buyer (one level up):** CRO / CISO / Chief AI Officer who signs the procurement contract (LOAD-BEARING: every Phoenix Audit artifact must work both for the daily-user workflow AND a board-ready 1-pager — per `brainstorm/22` riskiest-assumption analysis)
- **Secondary user:** ML platform / DevSecOps team running production agents needing continuous pre-deploy + post-deploy audit evidence (uses Phoenix Audit in their CI pipeline)
- **Value prop:** Phoenix Audit reduces the EU AI Act Annex IV documentation cycle from "Big-4 consulting €80K-€250K + 12-18 months" to "90 seconds, signed, keyed to a commit SHA, continuously updatable"
- **Measurable outcome demonstrated in demo:** 47 adversarial tests run against a target prior-auth agent; 3 fail; root-cause clustering collapses them into 1 cluster; hardening recipe generated in 4 seconds. Headline: _"3 failures, 1 root cause, patch in 4 seconds."_

---

## Demo moment (90-second judge walkthrough)

1. Judge lands on the hosted demo URL (no login). Sees a clean dashboard with one button: "Run ChaosLab against target agent."
2. Judge clicks. The page shows the target agent (a deliberately-naive customer-support agent — 3 tools, weak prompt, no input validation) with a "Healthy: 24/25 baseline runs passing" indicator.
3. **The attack starts.** A 5×5 grid (Attack Matrix) renders. Each cell represents one fault-injection run. As ChaosLab fires 25 attacks (combining 4 fault classes), cells turn red one by one — pass rate drops from 96% to 40%. Below the matrix, a Resilience Curve line plots the live pass rate.
4. **The patch fires at 1:50.** A "PATCH GENERATED" badge appears. The Patcher sub-agent has clustered 15 failures into 3 root causes (no input validation, no retry policy, no prompt-injection defense) and emitted a hardening recipe.
5. **The wow moment at 2:15:** ChaosLab runs the same 25 attacks against the patched agent. The Attack Matrix cells cascade-flip red → green (Framer Motion stagger). The Resilience Curve jumps from 40% to 92%. The PATCH marker is literally the wedge in the chart. A 1.5-second hold + slow zoom into the PATCH line is the Devpost cover screenshot.
6. **The receipt at 2:45.** Final card: "Agent ran 50 attacks. 4 fault classes. Identified 3 root causes. Generated 1 hardening recipe (MR #42 opened on GitLab). Total cost: $0.34. Time: 2m 47s." Plus a "Run against your own agent" CTA.

**The wow moment:** _The cascade-flip from red to green at 2:15 — same agent, same attacks, completely different outcome, with the PATCH line as the literal wedge in the chart. Tells the entire story in one frame._

---

## Out of scope

Per Abu's directive: "no MVP-vs-stretch framing — ship everything." But these are genuinely orthogonal and excluded:

- Production-grade scaling (>1 concurrent demo session) — Cloud Run min-instances=1 sufficient for judging window
- Tier-3 (HTTP black-box target) full behavioral fingerprinting — included as a clearly-marked beta path with inter-token-timing model identification (per `context/05 §12`); doesn't gate the demo
- Multi-language target support beyond Python — covered by tier-3 HTTP for any-language agent
- On-premise / self-hosted Phoenix — Phoenix Cloud only for the demo; dev uses self-hosted Docker
- Authenticated multi-tenant ChaosLab as a service — single-tenant judging-window demo only
- Real customer data / PII processing — synthetic target agent only
- A2UI / AP2 / UCP protocol integration — not the wedge (those are commerce-adjacent)

---

## Judging criteria alignment

| Criterion                        | Weight | How we score                                                                                                                                                                                                                                                                                                                                                                                            |
| -------------------------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Technological Implementation** | 25%    | Phoenix MCP + Phoenix Python SDK + Google ADK + Agent Runtime/Cloud Run + A2A peer + GitLab MCP + OpenInference instrumentation + LLM-as-judge clustering. 7+ Google + partner primitives composed in one closed loop. Judges (Arize + Google DevRel) have written half these SDKs.                                                                                                                     |
| **Design**                       | 25%    | Trace-as-UI hero pattern (per `architecture/05` §2). Attack Matrix + Resilience Curve hybrid, generated-per-anomaly. Per-agent color palette. Framer Motion cascade-flip. No template look — Pattern D production polish (per `brainstorm/05-prior-winners.md`).                                                                                                                                        |
| **Potential Impact**             | 25%    | Every team building agents in 2026 has this pain. Real-world incidents (Air Canada chatbot, Replit prod DB delete, Cursor unintended edits — see `context/02-production-failures.md`) would have been caught by pre-prod fault injection. Market gap: no existing red-team product (Lakera, Mindgard, HiddenLayer, Garak, PyRIT) treats multi-agent A2A topology as first-class (per `context/03 §13`). |
| **Quality of Idea**              | 25%    | 4-source convergence in the brainstorm (first-principles, landscape, protocol, ecosystem refactor — all surfaced variants of "agent breaks agent"). Novelty gate top match: 0.062 in 17,000+ project corpus — zero close duplicates. Arize-track-aligned recursive angle.                                                                                                                               |

---

## README shape (§13 — required ordering)

The shipped `README.md` must contain in this order:

1. Project name + one-line pitch
2. Demo URL (Cloud Run-hosted, NOT localhost)
3. Screenshot/GIF of the cascade-flip moment (above the fold) — auto-generated from the Devpost OG image
4. Run-locally: 3 commands max (`uv sync && pnpm install && make dev`)
5. Cross-framework target support matrix (1-line summary, link to docs)
6. License (Apache-2.0)

---

## Research references

- Master research folder: `research/google-cloud-rapid-agent/`
- Entry guide: `research/google-cloud-rapid-agent/READING-ORDER.md`
- Locked wedge: `research/google-cloud-rapid-agent/brainstorm/06-idea-rankings.md` §W1
- Novelty validation: `research/google-cloud-rapid-agent/brainstorm/07-novelty-gate.md`
- Agent shapes: `research/google-cloud-rapid-agent/context/01-agent-shapes-taxonomy.md`
- Competitive landscape + market gap: `research/google-cloud-rapid-agent/context/03-redteam-products-deep.md` §13
- Cross-framework integration: `research/google-cloud-rapid-agent/context/04-cross-framework-instrumentation.md`
- Phoenix MCP technical: `research/google-cloud-rapid-agent/architecture/02-phoenix-deep-dive.md`
- Hero UX: `research/google-cloud-rapid-agent/architecture/05-ux-and-demo.md`
- 4 MVP fault classes: `research/google-cloud-rapid-agent/architecture/04-fault-injection-eval.md`
- Vendoring opportunity: `research/google-cloud-rapid-agent/architecture/01-reference-implementations.md` (`deepankarm/agent-chaos`, Apache-2.0)
