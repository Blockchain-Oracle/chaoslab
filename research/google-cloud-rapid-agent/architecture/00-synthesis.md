# 00 — Architecture Synthesis (How We Build ChaosLab)

> ⚠️ **THIS FILE IS PRELIMINARY THINKING — NOT LOCKED DECISIONS** ⚠️
>
> **PATCH 2026-06-02 (later same day):** Abu pushed back on this synthesis for good reason. It tried to lock architectural decisions BEFORE we had enough domain knowledge about (a) the full variety of agent shapes ChaosLab might target, (b) cross-framework instrumentation, (c) real production failure modes, and (d) what other red-teaming products do. The "locked decisions" below were premature — they assumed ADK-only target agents, used artificial MVP-vs-stretch framing (irrelevant since the team uses AI coding agents, not human dev time), and asked binary questions that couldn't be answered without more domain depth.
>
> **The corrected approach is in `context/` (new folder).** Downstream agents (e.g., `sahil-spec-writer`) should read `context/` for domain knowledge AND `architecture/01-06` for exploratory research, then make architectural decisions themselves — not inherit decisions from this file.
>
> **What's still useful below:** the research findings (Phoenix MCP partial surface, agent-chaos vendoring opportunity, Cloud Run vs Agent Runtime tradeoff, fault class taxonomy, hero-visual design, cost projection). Treat as **data**, not as recommendations.
>
> **What to ignore:** the "L1-L12 LOCKED" labels, the "O1-O6 open decisions" survey, the 9-day cadence (which assumed human dev speed not AI coding speed), and any "MVP vs stretch" language.

---

**Compiled:** 2026-06-02
**Source:** 6 parallel architecture research agents producing files 01–06 (~5,500 lines total)
**Status:** PRELIMINARY — see banner above. Decisions are not locked. Downstream agents make their own architectural calls informed by `context/` + `architecture/01-06`.

---

## 1. The ChaosLab system in one diagram

```
                      ┌────────────────────────────────────┐
                      │   chaoslab-web (Next.js + visx)    │
                      │       Cloud Run service #1         │
                      │       no-login sandbox demo URL    │
                      └────────────────────┬───────────────┘
                                           │ HTTP / Server-Sent Events
                                           ▼
       ┌───────────────────────────────────────────────────────────────────┐
       │                  chaoslab-agent (orchestrator)                    │
       │                     Cloud Run service #2                          │
       │                                                                   │
       │   ┌──────────────────────────────────────────────────────────┐   │
       │   │  SequentialAgent (the orchestrator's brain)              │   │
       │   │                                                          │   │
       │   │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │   │
       │   │   │  Injector   │→ │   Judge     │→ │   Patcher   │    │   │
       │   │   │ (sub-agent) │  │ (sub-agent) │  │ (sub-agent) │    │   │
       │   │   └─────────────┘  └─────────────┘  └─────────────┘    │   │
       │   │         │                 ▲                 │           │   │
       │   └─────────┼─────────────────┼─────────────────┼───────────┘   │
       │             │                 │                 │               │
       │     A2A     ▼      reads      │     reads       ▼  writes       │
       │   ┌────────────┐    traces  ┌──────────────┐   patch artifact  │
       │   │  Target    │            │   Phoenix    │   → GCS / Mongo    │
       │   │ (RemoteA2a)│            │     Cloud    │                   │
       │   └────────────┘            │ (or self-host│   stretch: GitLab │
       │         ▲                   │  Docker dev) │   MCP → open MR   │
       │         │                   └──────────────┘                   │
       └─────────┼───────────────────────────────────────────────────────┘
                 │
                 │ A2A JSON-RPC
                 ▼
       ┌──────────────────────────────┐
       │   target-agent (the victim)  │
       │     Cloud Run service #3     │
       │   deliberately-naive support │
       │   agent w/ 3 tools, no input │
       │   validation, weak prompt    │
       └──────────────────────────────┘
```

**Three Cloud Run services, one orchestrator agent with three sub-agents, one A2A peer target, Phoenix for trace + eval substrate, optional GitLab MCP for the stretch "open MR" finale.**

---

## 2. Locked architectural decisions (≥2 agents converged)

### L1. Three Cloud Run services, NOT Agent Runtime
Source: `06-deployment-ops.md` § primary; `02b §5` for tradeoff context.

- `chaoslab-web` — Next.js frontend, `min-instances=1` during judging
- `chaoslab-agent` — ADK orchestrator (Sequential + 3 sub-agents), `min-instances=1` during judging
- `target-agent` — naive ADK agent exposed via `to_a2a(agent, port=8001)`, `min-instances=0`

**Why not Agent Runtime:** ChaosLab's workload is request/response in 60-180s windows. Cloud Run's 60-minute HTTP timeout fits. Agent Runtime's 7-day continuous reasoning is a red herring for this wedge.

### L2. Hybrid orchestrator + A2A target (Candidate B from #12)
Source: `03-multi-agent-patterns.md` § §5.2 (SalesShortcut won with this shape).

- 3 sub-agents (in-process): Injector, Judge, Patcher
- 1 A2A peer: Target (`RemoteA2aAgent` pointing at the target-agent Cloud Run service)
- One A2A hop per chaos step. Fault isolation ONLY where it matters (target genuinely crashes without taking the orchestrator down).
- Wired as `SequentialAgent(sub_agents=[Injector, Judge, Patcher], ...)` per ADK's canonical pipeline pattern.

### L3. Vendor `deepankarm/agent-chaos` for fault primitives
Source: `01-reference-implementations.md` § top-1 finding.

Apache-2.0, ~25KB of glue. Vendor with attribution:
- `src/agent_chaos/chaos/llm.py` (LLM fault injection — rate limit, server error, timeout, stream interrupt)
- `src/agent_chaos/chaos/tool.py` (tool fault injection — error, timeout, mutate)
- `src/agent_chaos/chaos/user.py` (prompt injection, malformed JSON)
- `src/agent_chaos/patch/` (hardening recipe scaffold)

**Saves 3-4 days of build time.** Add ADK integration + Phoenix instrumentation + autonomous-harden loop on top.

### L4. The 4 MVP fault classes
Source: `04-fault-injection-eval.md` § §8 — final pick.

| # | Fault | Injection mechanism | Layer | Judge eval | LOC |
|---|---|---|---|---|---|
| F1 | Malformed tool output | Decorator on tool return | Tool | Phoenix `tool_invocation` (built-in) | ~20 |
| F2 | Direct prompt injection | LiteLlm proxy mutating system prompt | Prompt | Custom rubric | ~25 |
| F3 | Context/RAG poisoning | Retriever monkey-patch | Context | Phoenix `hallucination` + custom overlay | ~25 |
| F4 | Latency spike / timeout | Network shim (asyncio sleep + httpx timeout) | Network | Custom rubric | ~25 |

Each one covers a different injection mechanism AND a different layer. Demo diversity guaranteed.

### L5. Phoenix Cloud for judging window, self-host Docker Phoenix for dev
Source: `02-phoenix-deep-dive.md` § §7 + `06-deployment-ops.md` § §3.

- Free tier: 25k spans/month, 15-day retention, 1GB. ~1,250 runs/month — tight for active dev.
- Self-hosted Phoenix via Docker in dev = infinite + free.
- Push only the canonical demo subset to Phoenix Cloud during judging window.

### L6. Phoenix MCP is partial — supplement with 2 custom Python tools
Source: `02-phoenix-deep-dive.md` § §1, §9.5-9.6 (this changes the RAT runbook).

The MCP server has read-only experiment + annotation surface. To close the ChaosLab loop, we need 2 custom ADK `FunctionTool` wrappers around the Phoenix Python SDK:

1. `run_phoenix_experiment(dataset_id, eval_rubric)` — wraps `client.experiments.run_experiment(...)`
2. `write_span_annotation(span_id, score, reason)` — wraps `client.spans.log_span_annotations(...)`

Both ~15-20 LOC. Pre-written in `02-phoenix-deep-dive.md` §9.5-9.6.

**This invalidates the RAT runbook's Step 3 as originally written.** See §6 below for the revised runbook.

### L7. JUDGE_LLM = "gemini-2.5-flash" (or 3.5 Flash, verified during RAT)
Source: `04-fault-injection-eval.md` § §4 cost analysis.

Phoenix tutorials default to Gemini Pro which is **17× more expensive**. Setting the judge model to Flash is the difference between $5 vs $85 of credit consumed across the eval cycle.

### L8. Hero visual: Attack Matrix + Resilience Curve hybrid (Option D)
Source: `05-ux-and-demo.md` § §1.

5×5 grid of red/green cells (each cell = one fault-injection run) ABOVE a pass-rate line chart, sharing x-axis with a vertical PATCH marker. Cascade-flip red→green at 1:50, curve jumps 40% → 92% below. Same story told two ways. **Frame held 1.5s at 2:15 = Devpost cover screenshot + replay-anchor.**

### L9. Frontend stack: Next.js + React + Tailwind + shadcn/ui + visx + Framer Motion
Source: `05-ux-and-demo.md` § §6.

~16 hours of frontend build. Pattern D (production polish) wins judging. `sahil-visual-loop` is built for Playwright + Next.js — automated visual-quality enforcement included. Hard fallback: Streamlit + heavy CSS if Day 6 EOD doesn't have demoable UI. **Never Studio** (control surface too small).

### L10. Phoenix integration via custom rendering, NOT iframe
Source: `05-ux-and-demo.md` § §2.

Phoenix Cloud blocks via `X-Frame-Options`. Demo URL renders Phoenix data via custom React components reading from Phoenix MCP tools. Reuses Phoenix's color/shape vocabulary but is our own UI.

### L11. Cost projection: ~$72 total under $100 credit
Source: `06-deployment-ops.md` § §5.

- ~$45 dev (9 days, Cloud Run + Vertex AI calls)
- ~$27 judging (4-week judging window, intermittent traffic)
- Two optimizations applied: Flash-Lite for judge LLM (L7), prompt-cache the target system prompt
- $28 margin under $100. Naive worst-case is $108 (overruns by $8.50 — needs both optimizations to hold).
- **Counter-intuitive:** `min-instances=1` warm-pool ($7/service/month × 2 services = ~$14) costs more than judging-window token usage ($25). Naive intuition (tokens dominate) is wrong at hackathon scale.

### L12. Pin Gemini model ID + screenshot baseline traces Day 2
Source: `06-deployment-ops.md` § §9 (risk register).

The "naive" target agent might silently become less naive when Gemini 3.5 Flash auto-updates mid-judging — flattens the resilience curve (= kills the wow moment). Pin exact model ID (`gemini-3.5-flash-001` or similar versioned tag). Day 2: screenshot baseline target-agent traces so we have an "originally failed at 60%" reference.

---

## 3. The 9-day build cadence — REVISED with the new findings

Original plan was `brainstorm/05-ecosystem-refactor.md` §Appendix C. Updated with the architecture findings:

| Day | Date | Original focus | REVISED focus | Why |
|----:|------|----------------|---------------|-----|
| 0 | 2026-06-02 | Spec lock + scaffold | ✅ Done. Brainstorm + architecture research complete. | — |
| **1** | **2026-06-03** | **RAT + Day-1 deploy** | **REVISED RAT (see §6) + Day-1 ADK + Cloud Run + Phoenix Cloud hello-world per `06-deployment-ops.md` §10** | Phoenix MCP partial discovery → RAT must verify Python SDK path works |
| 2 | 2026-06-04 | Fault catalog v1 (2 fault classes) | **Vendor `deepankarm/agent-chaos`** + integrate F1 (decorator). Pin model ID. Screenshot baseline target traces. | Saved 1 full day via vendoring (L3) |
| 3 | 2026-06-05 | Phoenix MCP + 3 eval rubrics | F2 + F3 fault classes integrated. Phoenix MCP + 2 custom Python FunctionTools wired. F1+F2+F3 emitting traces. | Vendored chaos primitives means F2/F3 are config not code |
| 4 | 2026-06-06 | 2 more fault classes + clustering | F4 + LLM-as-judge clustering. SequentialAgent skeleton built. | Now ahead of schedule on faults |
| 5 | 2026-06-07 | Hardening recipe generator | Hardening recipe (vendored from agent-chaos/patch + customized). Artifact JSON format locked. | — |
| 6 | 2026-06-08 | Re-test loop + UI | Re-test loop closes. **Day 6 = frontend main build** (Next.js + visx attack matrix + curve). | Frontend critical-path |
| 7 | 2026-06-09 | GitLab MCP (stretch) + polish | GitLab MCP MR emission (stretch goal, can be cut). Polish frontend + Mermaid arch diagram + README. | — |
| 8 | 2026-06-10 | Demo video shoot | Record demo. Pattern C (agent-acting-not-narrating). Three takes, picking best. | — |
| 9 | 2026-06-11 | Submit + safety margin | Submit by 12:00 PT (2h margin). | — |

**What got CUT relative to original plan:** Nothing critical. Vendoring agent-chaos accelerates Days 2-3 by ~1 full day, which buys us margin on the frontend (Day 6 was the highest-risk single day).

---

## 4. Open architectural decisions — Abu's call

These are NOT locked. They each affect the spec materially. Want Abu's input on each before firing `sahil-spec-writer`.

### O1. Single-target demo vs multi-target demo
**Question:** Does ChaosLab demo against ONE deliberately-naive target agent, or against 2-3 different target shapes (a Q&A bot + a tool-using agent + a multi-step agent)?

**Tradeoff:**
- Single target: simpler build, cleaner narrative ("here's how ChaosLab hardens this specific kind of agent")
- Multi-target: stronger judging "potential impact" signal ("ChaosLab generalizes")

**Recommendation:** Single target for the MVP, optionally swap target via dropdown in the UI for stretch. Lower scope risk.

### O2. Stretch goal: GitLab MCP MR emission
**Question:** Do we ship the autonomous MR-emission to GitLab as part of the demo, or as Markdown artifact only?

**Tradeoff:**
- GitLab MR: stronger Tech Implementation signal (3 partner-domain MCPs composed: Phoenix + GitLab + …), and the original wedge story arc closes cleanly
- Markdown artifact: less risk, same eval-loop closure, but loses the "agent opened a PR autonomously" moment

**Recommendation:** Markdown artifact for MVP, GitLab MR as Day 7 stretch (cut first if behind).

### O3. Frontend ambition level
**Question:** Full Next.js + visx + Framer Motion (16 hrs), or "good enough" Streamlit (4 hrs)?

**Tradeoff:**
- Next.js: hero visual is screen-stopping; demos that look polished win; `sahil-visual-loop` enforces quality
- Streamlit: 12 hours back into Days 5-7; frontend looks "Pythonic dashboard"

**Recommendation:** Commit to Next.js. The hero visual IS the demo. Streamlit fallback only if Day 6 EOD fails.

### O4. Memory Bank for cross-run learning?
**Question:** Wire Memory Bank so ChaosLab remembers "this fault class was already hardened against in run N-1, skip it in run N"?

**Tradeoff:**
- Yes: stronger "self-improving" narrative for Arize judges; demonstrates a deeper Google primitive
- No: scope creep on Day 5-6, increases architectural surface

**Recommendation:** Skip for MVP. Note as v0.2 future work in README. Memory Bank is a Day 7 stretch at the earliest.

### O5. Three-agent architecture vs `AgentTool` pattern
**Question:** From `03-multi-agent-patterns.md`, ADK actually ships THREE patterns: sub-agents, A2A, AND `AgentTool` (agent-as-tool). The Patcher might be cleaner as `AgentTool` (called once per run) rather than a sub-agent (full conversational handoff).

**Tradeoff:**
- Sub-agent: standard ADK pipeline pattern, demo-clear handoff
- AgentTool: tighter integration, less ceremony, but loses the "visible handoff" winning pattern

**Recommendation:** Keep Patcher as sub-agent (per L2). Visible handoff matters for the demo narrative ("Patcher agent active" indicator in the multi-agent dashboard).

### O6. ETHGlobal-style Showcase repo metadata
**Question:** Submit only to Devpost, or also add the project to ETHGlobal Showcase + ETHGlobal corpus for visibility (since Abu's web3 community is on ETHGlobal)?

**Tradeoff:**
- Both: amplified reach, doesn't conflict with hackathon rules
- Devpost-only: less Day 9 admin burden

**Recommendation:** Both. ETHGlobal Showcase is free; Abu's community is there.

---

## 5. Updated risk register

Top 8 risks for the 9-day build + 4-week judging window. Sorted by `probability × blast-radius`:

| # | Risk | Prob | Blast | Mitigation | Source |
|---|---|---|---|---|---|
| 1 | Phoenix MCP `npx` keep-alive on Cloud Run breaks mid-judging | M | 🔴 | Verify Day 2 locally; pre-build stdio fallback path; min-instances=1 reduces cold-start frequency | 02, 06 |
| 2 | Naive target agent stops being naive (Gemini auto-updates) | L | 🔴 | Pin exact model ID; Day 2 screenshot baseline traces; pre-record canonical attack run | 06 |
| 3 | Frontend slips on Day 6, no time for hero visual | M | 🟡 | Streamlit fallback path; vendor visx + shadcn components Day 4-5 to de-risk | 05 |
| 4 | Phoenix Cloud 25k-span free tier exhausted before judging | L | 🟡 | Self-host Phoenix for dev; push only canonical demo set to Cloud (~5k spans) during judging | 02, 06 |
| 5 | `JUDGE_LLM` accidentally Pro instead of Flash → $85 in token spend | M | 🟡 | Hard-code Flash model in config; CI assert before deploy | 04 |
| 6 | Vendored agent-chaos has incompatible Python version | L | 🟡 | Verify Day 2; fall back to re-implementing ~150 LOC if needed | 01 |
| 7 | Cloud Run cold start eats first-impression in judging window | L | 🟡 | min-instances=1 for web + agent services ($14/mo budget already allocated) | 06 |
| 8 | A2A target hop adds latency the demo can't hide | M | 🟢 | A2A is ~50-200ms per hop locally; not a problem at hackathon scale; mention in caveats | 03 |

**Most important single insight:** the Phoenix MCP `npx` keep-alive risk (#1) is the same OQ-3 we identified in CONTEXT.md §7 four phases ago. It's the consistent biggest single risk. RAT Day 1 validates it.

---

## 6. REVISED RAT runbook (must update — Step 3 fix)

The original `RAT-runbook.md` Step 3 said "agent runs an experiment via MCP." That tool doesn't exist on the MCP server (confirmed by reading the source). Replace Step 3 with:

### Step 3 (REVISED) — Python SDK wrap test (30 min)

**Goal:** Verify that wrapping `phoenix.client.AsyncClient().experiments.run_experiment(...)` as a custom ADK `FunctionTool` actually works end-to-end.

```python
# /tmp/phoenix-rat/run_experiment_via_tool.py
import os
from google.adk import Agent
from google.adk.tools import FunctionTool
from phoenix.client import AsyncClient

phoenix = AsyncClient(
    base_url="https://app.phoenix.arize.com",
    api_key=os.environ["PHOENIX_API_KEY"],
)

async def run_phoenix_experiment(dataset_name: str) -> dict:
    """Runs a Phoenix experiment with a built-in tool-invocation eval."""
    dataset = await phoenix.datasets.get_dataset(name=dataset_name)
    result = await phoenix.experiments.run_experiment(
        dataset=dataset,
        task=lambda ex: {"output": "stub"},  # placeholder task
        evaluators=["tool_invocation"],
        experiment_name="rat-test",
    )
    return {"experiment_id": result.id, "metrics": result.metrics}

agent = Agent(
    name="phoenix_runner",
    model="gemini-3.5-flash",
    tools=[FunctionTool(run_phoenix_experiment)],
)

result = agent.run("Run the experiment on the 'rat-test' dataset.")
print(result)
```

- [ ] Run it. Verify experiment appears in Phoenix Cloud dashboard.
- [ ] Verify the agent's tool call returned a non-empty `experiment_id`.

**PASS CRITERIA:** experiment shows up in Phoenix server-side + tool returns structured result.
**KILL TRIGGER:** if SDK call fails or experiment doesn't materialize, pivot to W8.

Everything else in `RAT-runbook.md` stays as written. I'll patch the file after Abu confirms the synthesis.

---

## 7. Files in this folder

| File | Purpose |
|---|---|
| **`00-synthesis.md`** (this file) | Master architecture decision document. Spec-writer input. |
| `01-reference-implementations.md` (629 lines) | Voltaros, agent-chaos, Chaos Mesh/Gremlin/LitmusChaos, LLM red-teaming, eval frameworks, ADK winner architectures |
| `02-phoenix-deep-dive.md` (1,038 lines) | Phoenix MCP tool inventory (25 tools w/ Zod signatures), Python SDK, ADK auto-instrument, 6 ready-to-use code snippets |
| `03-multi-agent-patterns.md` (1,336 lines) | Sub-agents vs A2A vs AgentTool, design patterns, 3 candidate architectures, code skeletons |
| `04-fault-injection-eval.md` (1,033 lines) | OWASP/MITRE ATLAS fault taxonomy, 4 MVP fault classes with code, LLM-as-judge rubrics, failure clustering |
| `05-ux-and-demo.md` (732 lines) | Hero visual (Option D), Trace-as-UI, multi-agent viz, demo arc, frontend stack |
| `06-deployment-ops.md` (834 lines) | 3 Cloud Run services, Phoenix Cloud vs self-host, $72 cost projection, 4-week judging-window survival plan |

## 8. Open questions for `sahil-spec-writer`

Once Abu signs off on O1-O6, the spec-writer has all inputs it needs:
- ✅ Locked architecture (§2 + §3 cadence)
- ✅ Locked fault catalog (L4)
- ✅ Locked hero visual (L8)
- ✅ Locked frontend stack (L9)
- ✅ Locked cost model (L11)
- ✅ Risk register (§5)
- ✅ Updated RAT (§6)
- ⏸ Open decisions (§4) — pending Abu

After Abu picks O1-O6, fire `sahil-spec-writer` with this synthesis + the brainstorm + the locked wedge as inputs. It produces docs/PRD.md, docs/architecture.md, docs/ux-spec.md, docs/epics.md, docs/stories/*.md.

---

**Bottom line:** The architecture is well-defined. We borrow heavily (agent-chaos vendoring, Voltaros 3-agent skeleton, Chaos Toolkit steady-state hypothesis, Phoenix built-in evals). The novel work concentrates in the closed-loop wiring + the hero visual. 9-day cadence has a full day of margin thanks to vendoring. Cost fits. Risks are known.

The single Day-1 thing that still gates the build: **the revised RAT.** If Step 3 (Python SDK wrap) works, commit. If not, pivot to W8.
