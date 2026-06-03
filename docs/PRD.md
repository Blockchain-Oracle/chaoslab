# PRD — ChaosLab

**Project name:** ChaosLab (formal: "ChaosLab for Agents")
**Hackathon:** Google Cloud Rapid Agent Hackathon
**Track:** Arize (Phoenix observability)
**Deadline:** 2026-06-11, 2:00 PM Pacific Time
**Status:** DRAFT — pending Abu approval
**Approved by Abu:** [ ] pending

---

## Goal

**ChaosLab is chaos engineering for AI agents.** Solo developers ship LLM agents in days using AI coding tools, but those agents break in unknown ways in production — wrong tool selection under malformed input, prompt-injection cascades, context poisoning that silently corrupts answers, latency spikes that trip retries. Every chaos-engineering tool today (Chaos Mesh, Gremlin, Litmus) attacks infrastructure; every red-team tool today (Lakera, Mindgard, Garak, PyRIT) attacks a single LLM endpoint. **No product targets multi-agent agentic systems with closed-loop hardening.** ChaosLab does. Point it at any agent (ADK, LangChain, CrewAI, browser-use, voice, or HTTP black-box) and it runs 4 LLM-specific fault classes, watches the agent fail in Phoenix traces, LLM-as-judges to cluster failures, generates a hardening recipe (prompt patch + tool validation diff), and emits a regression-tested GitLab MR — autonomously, overnight.

**One-line pitch (judge-facing):**
> ChaosLab — adversarial resilience testing for AI agents. Inject 4 fault classes, watch them fail, harden automatically.

**Sponsor-native fit:**
ChaosLab is the only Arize-track submission that uses Phoenix as the substrate for closed-loop self-improvement (read traces via MCP → cluster failures with LLM-as-judge → write back hardening recipes as Phoenix datasets) — the recursive observability use case Arize explicitly bonuses.

---

## Target users + value prop

- **Primary user:** Solo / SMB developer shipping an LLM agent with no time for a dedicated red-team pass
- **Secondary user:** ML platform / SRE team running production agents needing pre-deploy fault-injection
- **Value prop:** ChaosLab reduces mean-time-to-harden from "hours of manual reproduction + custom patching" to "overnight autonomous resilience curve + reviewable MR"
- **Measurable outcome demonstrated in demo:** target agent failure rate 60% → 8% across 25 fault-injection runs after one ChaosLab loop

---

## Demo moment (90-second judge walkthrough)

1. Judge lands on the hosted demo URL (no login). Sees a clean dashboard with one button: "Run ChaosLab against target agent."
2. Judge clicks. The page shows the target agent (a deliberately-naive customer-support agent — 3 tools, weak prompt, no input validation) with a "Healthy: 24/25 baseline runs passing" indicator.
3. **The attack starts.** A 5×5 grid (Attack Matrix) renders. Each cell represents one fault-injection run. As ChaosLab fires 25 attacks (combining 4 fault classes), cells turn red one by one — pass rate drops from 96% to 40%. Below the matrix, a Resilience Curve line plots the live pass rate.
4. **The patch fires at 1:50.** A "PATCH GENERATED" badge appears. The Patcher sub-agent has clustered 15 failures into 3 root causes (no input validation, no retry policy, no prompt-injection defense) and emitted a hardening recipe.
5. **The wow moment at 2:15:** ChaosLab runs the same 25 attacks against the patched agent. The Attack Matrix cells cascade-flip red → green (Framer Motion stagger). The Resilience Curve jumps from 40% to 92%. The PATCH marker is literally the wedge in the chart. A 1.5-second hold + slow zoom into the PATCH line is the Devpost cover screenshot.
6. **The receipt at 2:45.** Final card: "Agent ran 50 attacks. 4 fault classes. Identified 3 root causes. Generated 1 hardening recipe (MR #42 opened on GitLab). Total cost: $0.34. Time: 2m 47s." Plus a "Run against your own agent" CTA.

**The wow moment:** *The cascade-flip from red to green at 2:15 — same agent, same attacks, completely different outcome, with the PATCH line as the literal wedge in the chart. Tells the entire story in one frame.*

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

| Criterion | Weight | How we score |
|---|---|---|
| **Technological Implementation** | 25% | Phoenix MCP + Phoenix Python SDK + Google ADK + Agent Runtime/Cloud Run + A2A peer + GitLab MCP + OpenInference instrumentation + LLM-as-judge clustering. 7+ Google + partner primitives composed in one closed loop. Judges (Arize + Google DevRel) have written half these SDKs. |
| **Design** | 25% | Trace-as-UI hero pattern (per `architecture/05` §2). Attack Matrix + Resilience Curve hybrid, generated-per-anomaly. Per-agent color palette. Framer Motion cascade-flip. No template look — Pattern D production polish (per `brainstorm/05-prior-winners.md`). |
| **Potential Impact** | 25% | Every team building agents in 2026 has this pain. Real-world incidents (Air Canada chatbot, Replit prod DB delete, Cursor unintended edits — see `context/02-production-failures.md`) would have been caught by pre-prod fault injection. Market gap: no existing red-team product (Lakera, Mindgard, HiddenLayer, Garak, PyRIT) treats multi-agent A2A topology as first-class (per `context/03 §13`). |
| **Quality of Idea** | 25% | 4-source convergence in the brainstorm (first-principles, landscape, protocol, ecosystem refactor — all surfaced variants of "agent breaks agent"). Novelty gate top match: 0.062 in 17,000+ project corpus — zero close duplicates. Arize-track-aligned recursive angle. |

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
