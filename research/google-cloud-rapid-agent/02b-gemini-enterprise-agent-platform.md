# 02b — Gemini Enterprise Agent Platform: The Complete Map

**Source:** Holt Skinner (Google Cloud AI DevRel) — official platform overview video.
Full transcript at `refs/holt-skinner-gemini-enterprise-agent-platform-transcript.md`.

This file is the **canonical map** of every component in the Agent Platform, organized by Google's own mental model: the **4-phase agent development lifecycle**. Read `02a-google-cloud-stack.md` first if you want the SDK code and pricing detail; read THIS file if you want to understand what the platform IS and how the pieces fit together.

---

## The mental model: Build → Scale → Govern → Optimize

Google has organized 19 distinct components into 4 lifecycle phases. Once you internalize this map, the alphabet soup of "Agent X / Agent Y / Agent Z" stops being confusing.

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   1. BUILD   │───▶│   2. SCALE   │───▶│  3. GOVERN   │───▶│ 4. OPTIMIZE  │
│              │    │              │    │              │    │              │
│ How you      │    │ How it runs  │    │ How you keep │    │ How you make │
│ create the   │    │ in           │    │ it safe and  │    │ it better    │
│ agent        │    │ production   │    │ accountable  │    │ over time    │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
   ADK              Agent Runtime       Agent Identity       Agent Observability
   Agents CLI       Agent Sessions      Agent Registry       Agent Topology
   Agent Studio     Memory Bank         Agent Policies       Agent Evaluation
   Agent Garden     Agent Sandbox       Model Armor          Agent Simulation
                                        Agent Gateway        Agent Optimizer
                                        Anomaly Detection
                                        Security Dashboard
```

For Abu's hackathon (9-day timeline, solo dev, $10K Arize-track bucket): you'll spend ~70% of your time in **Build**, ~20% in **Scale**, and use **Optimize** primitives to demonstrate sophistication for the judging criteria. **Govern** is mostly cosmetic for a hackathon but worth understanding so the video pitch can name-drop the right concepts.

---

## Naming note (re-confirmed by Google itself)

Holt's video says explicitly: *"If you've been building with Vertex AI, you're in the right place. Agent Platform is an evolution of Vertex AI, including Model Garden and Model Training, that is now restructured as an agent-first ecosystem. You'll see some mixed terminology as we transition, but please be assured that the core Vertex AI functionality remains unchanged."*

| Old | New |
|---|---|
| Vertex AI | Gemini Enterprise Agent Platform (often shortened to "Agent Platform") |
| Vertex AI Model Garden | Model Garden (preserved inside Agent Platform) |
| Vertex AI Model Training | Model Training (preserved) |
| Vertex AI Search & Conversation | Agent Builder / Agent Studio |
| **Agent Engine** / **Reasoning Engine** | **Agent Runtime** (confirmed in Google's README) |
| Generative AI App Builder | Agent Search |
| (no rename) | Agent Sandbox is also called **Code Execution** in tutorials |

`02a-google-cloud-stack.md` §1 has the full rosetta stone — this is just a confirming citation from the platform's own DevRel team.

### Model version note (IMPORTANT correction)

The earlier file `02a-google-cloud-stack.md` §4 documented Gemini **2.5 Flash / 2.5 Pro** as the active models with specific pricing. **The current default per Google's official README (verified 2026-06-02) is the 3.x line:**

- **Gemini 3.5 Flash** ⭐ current default for fast/cheap
- **Gemini 3.1 Pro** for harder reasoning
- **Gemini 3.1 Flash-Lite** for lowest-cost
- **Gemini 3.1 Flash Image (Nano Banana 2 🍌)** for image generation
- **Gemini 3 Pro Image (Nano Banana Pro 🍌)** for higher-quality image
- **Veo 3.1** for video
- **Lyria 3** for music

Gemini 2.x is likely still callable for backward compatibility, but **default new code to `gemini-3.5-flash`** unless you specifically need 3.1 Pro reasoning. Pricing for 3.x must be re-checked at https://ai.google.dev/gemini-api/docs/pricing — the 2.5 prices in `02a` are likely no longer current.

> **Action item:** before locking model choice for the build, re-verify pricing for Gemini 3.5 Flash and 3.1 Pro at the official pricing page. The $100 promo credit calculation depends on this.

---

## Phase 1: BUILD (how you create the agent)

Four ways to build an agent — pick one (or mix):

### 1. **Agent Development Kit (ADK)** — code-first

What it is: Google's primary agent framework. Code-first.

- **Languages:** Python, TypeScript, Java, Go (4 languages — this is broader than most people realize)
- **Patterns supported:** simple sequential agents → multi-agent systems → **NEW: deterministic graph-based agents** (a recent addition that lets you choose dynamic model-led reasoning OR strict deterministic logic — like LangGraph but native)
- **Model-agnostic:** optimized for Gemini, but works with Claude (Anthropic), open-weight models (Ollama), etc. (Note: for the hackathon, you must use Gemini per Section 7B of the rules. ADK's model-agnosticism is irrelevant here.)
- **Where to start:** https://adk.dev

**ADK is the path Abu uses for the Arize track** (Arize requires code-owned runtime for instrumentation).

### 2. **Agents CLI** — agentic-assisted "vibe coding"

What it is: A CLI for coding-agents that automates creating and managing ADK agents. Distinct from the Gemini CLI.

- Provides agent skills for AI-assisted development
- Automated evaluation to measure agent efficacy quickly
- Automated deployment to Agent Runtime and the Gemini Enterprise app

This is Google's official "agent-that-codes-your-agent" tool. **It's probably the fastest path for a solo hackathon dev** — it can scaffold the project, wire up tools, and deploy. If it's stable enough for production, it's stable enough for a 9-day build.

### 3. **Agent Studio** — low-code visual builder

What it is: Drag-and-drop UI in the Google Cloud Console. (This is what the FAQ calls "Agent Platform → Studio".)

- Map out agent flows visually
- Test in real time
- See model reasoning through a conversation
- **Export to ADK code** (so you can start visual, switch to code) → deploy to Cloud Run, GKE, anywhere
- Or deploy directly to Agent Runtime

For Abu's track (Arize): Studio is NOT enough on its own because Arize needs code-owned runtime for tracing. But you can prototype in Studio, then export to ADK and continue from there. Don't dismiss this path even if you end up in code.

### 4. **Agent Garden** — prebuilt templates

What it is: A library of high-quality enterprise-pattern templates. Examples Holt mentions:

- Financial analysis agent
- Marketing campaign agent

Clone a template, customize, deploy. This is the "don't start with a blank IDE" option.

**For the hackathon:** Worth checking the Agent Garden gallery before writing any code from scratch — there may be a template that's 70% of what you want, and that's a 6-day shortcut.

### Tool connection: FIVE open protocols (not just MCP/A2A)

Holt's video covers MCP + A2A. Google's own README adds **three more** agent-related open protocols (see `refs/agent-platform-readme.md`):

| Protocol | What it connects | Best for | URL |
|---|---|---|---|
| **MCP (Model Context Protocol)** | Agent ↔ external tools | Calling partner data/APIs (Phoenix, Atlas, Elastic, etc.) | https://modelcontextprotocol.io/ |
| **A2A (Agent-to-Agent)** | Agent ↔ other agents | Multi-agent collaboration as microservices | https://a2a-protocol.org |
| **A2UI (Agent-to-UI)** | Agent ↔ dynamic UIs | Agent-generated user interfaces (vs. fixed UI) | https://a2ui.org |
| **AP2 (Agent Payments)** | Agent ↔ payment rails | Automated financial transactions by agents | https://ap2-protocol.org |
| **UCP (Universal Commerce)** | Agent ↔ e-commerce systems | Retail/commerce operations | https://ucp.dev/ |

**Hackathon implications:**

- **MCP** is mandatory for the partner integration. `mcp-primer.md` covers this.
- **A2A** is the right choice if the wedge involves multiple specialized agents (e.g., one agent fetches Phoenix traces, another runs Agent Optimizer). Don't roll custom orchestration. Holt confirms: *"Most agent frameworks, like LangGraph, CrewAI, and AG2, have built-in support for A2A."*
- **A2UI** is a sleeper feature — if the wedge demo benefits from "the agent generates its own UI for the user" (e.g., a different dashboard per query), A2UI lets you do that. Most hackathon entries will miss this. Big differentiation potential.
- **AP2** is uniquely relevant if Abu picks a Financial Services demo — the agent doesn't just analyze, it can transact. This converts "interesting demo" → "actually does the work" and is judging-criteria gold for Potential Impact.
- **UCP** is the equivalent if the wedge is brick-and-mortar retail (one of the Devpost example domains).

> **Strategic takeaway:** every hackathon entrant will use MCP. Most will skip A2A. Almost none will use A2UI/AP2/UCP — which means a wedge that includes one of those three is a differentiation gift. If Abu wants to LOSE the lazy-default pack, having an AP2 or A2UI angle in the demo separates from the field.

---

## Phase 2: SCALE (how it runs in production)

Four components — how the agent operates once deployed:

### 5. **Agent Runtime** — managed PaaS for agents

> ⚠️ **Naming aliases:** This component is also called **Agent Engine** and **Reasoning Engine** in older tutorials. All three names refer to the same product. The official tutorial notebook is even named `intro_agent_engine.ipynb` — don't get confused by the URL not matching "Agent Runtime."

What it is: Google's managed platform-as-a-service designed specifically for enterprise-ready agents.

**Two non-obvious specs Holt highlights:**

- **<1 second cold starts** (critical for hackathon demos — judges won't wait through a 30s cold start before the agent responds)
- **Up to 7 days of continuous reasoning** for long-running agents

- **Framework-agnostic:** optimized for ADK, but accepts LangGraph, LangChain, custom stacks (subject to hackathon rules — LangChain as primary orchestrator is banned)

**For Abu's deployment story:** Agent Runtime is the default hosted path. Alternative: Cloud Run if you want full container control. See `02a-google-cloud-stack.md` §5 for the decision matrix.

### 6. **Agent Sessions** — multi-user conversation tracking

What it is: Tracks interactions between users and agents.

- Auto-handled if using ADK on Agent Runtime
- **Custom session IDs** let you map interactions to internal customer/project records

For the hackathon: useful if your demo has multiple personas (e.g., "judge plays the user role, agent maintains session state across multiple turns"). Probably auto-handled — don't over-engineer.

### 7. **Memory Bank** — long-term memory across sessions

What it is: Adds persistent memory so the agent remembers things across user interactions. User doesn't have to re-provide context every time.

**Strategic call for the hackathon:** If your wedge benefits from memory (e.g., "agent learns my preferences over multiple sessions"), Memory Bank is the right primitive. **Don't roll your own memory store** when this exists natively.

### 8. **Agent Sandbox** — safe execution environment

> ⚠️ **Naming alias:** Agent Sandbox is referred to as **Code Execution** in the official tutorial notebooks. The intro notebook is `tutorial_get_started_with_code_execution.ipynb`. Same product.

What it is: A safe sandboxed environment for the agent to:
- Execute code
- Interact with a UI (e.g., legacy applications that don't have APIs)
- "Do whatever it needs to do"

For the hackathon: relevant if your agent needs to **run code on behalf of the user** (a data-analysis agent, a code-generation agent that tests its output, etc.). Most hackathon ideas don't need this — but if yours does, use Agent Sandbox, not a hand-rolled subprocess.

---

## Phase 3: GOVERN (safety + accountability)

Seven components. **For a 9-day hackathon, you'll likely demonstrate awareness of these via the video narrative, not implement all of them.** But you should know what each one is so you can name-drop credibly.

### 9. **Agent Identity** — IAM principle per agent

Every agent deployed to Agent Runtime gets its own IAM principle. Answers: *which agent took this specific action?*

For the hackathon: free with Agent Runtime. Mention it in the video as "the agent runs under its own IAM identity for audit trail" — earns Tech Implementation points.

### 10. **Agent Registry** — auto-catalog of all agents and MCP servers

What it is: Automatically catalogs:
- Agents deployed to Agent Runtime, GKE, Gemini Enterprise, Google Workspace
- First-party MCP servers + MCP servers from Apigee
- Third-party A2A agents and MCP servers (when you register them)

**Why this matters:** When you wire a partner's MCP server (e.g., Phoenix MCP for Arize), Agent Registry is the system that lets your agent securely discover and call it. This is the "secure access" layer.

### 11. **Agent Policies** — IAM for agents

> ⚠️ **PRIVATE PREVIEW** — likely not accessible to hackathon participants without explicit access. Awareness only.

What it is: Set IAM policies on agents, tools, and the registry itself.

For the hackathon: cosmetic unless your demo specifically shows "agent A can call tool X but not tool Y." Skip for the agent itself, but understand it exists.

### 12. **Model Armor** — input/output sanitization

What it is: Templates to sanitize:
- **Input prompts** → blocks prompt injections
- **Output responses** → blocks PII leaks
- Combined with Sensitive Data Protection

For the hackathon: **high-value demo flex if your domain is sensitive** (finance, healthcare). One line in the demo video: "We use Model Armor to sanitize all PII before it reaches the LLM" earns serious Tech Implementation points. Easy to wire if Vertex AI is already configured.

### 13. **Agent Gateway** — single ingress/egress chokepoint

> ⚠️ **PRIVATE PREVIEW** — likely not accessible to hackathon participants. Awareness only.

What it is: Single entry point that intercepts ALL ingress and egress calls. Audits or enforces the Agent Policies.

For the hackathon: too heavyweight to bother with. Awareness only.

### 14. **Anomaly Detection** — LLM-as-judge for weird behavior

What it is: An LLM-as-a-judge framework that watches reasoning patterns and flags weird or stalled behavior.

For the hackathon: useful in the demo narrative — "Anomaly Detection caught my agent looping on a malformed tool call and stopped the run before it burned credits." But implementing it is overkill for 9 days.

### 15. **Agent Security Dashboard** — curated threat view

For the hackathon: awareness only.

---

## Phase 4: OPTIMIZE (continuous improvement)

Five components. **This is where the Arize track positioning gets interesting.**

### 16. **Agent Observability** — visibility into decision making

What it is: Turnkey dashboards + automatic tracing showing:
- Why the agent made each decision
- What tools it called
- Where the logic went sideways

**HEADS UP — this competes with Arize Phoenix.** Both Agent Observability and Phoenix do tracing. But the distinction is:

| | Agent Observability (native) | Arize Phoenix (track partner) |
|---|---|---|
| **Audience** | Humans (operators, devs) | Both humans AND agents (via MCP) |
| **Distinguisher** | Native dashboards | Phoenix MCP exposes traces *back to the agent* for self-reflection |
| **Hackathon implication** | Free, basic | The recursive "agent reads its own traces and self-improves" wedge needs Phoenix MCP — Agent Observability alone can't do this because humans, not the agent, are the consumer |

**This actually STRENGTHENS the Arize wedge.** The recursive self-debug angle (recommended for Abu in `CONTEXT.md` §2) becomes more defensible: "Agent Observability gives operators visibility; Phoenix MCP gives the agent visibility into ITSELF. That's a categorically different primitive." Demo this and the Arize judges will love it.

### 17. **Agent Topology** — graph-view of agents + MCP servers

What it is: A graph-like view of all agents and MCP servers in a system, with aggregated traces.

For the hackathon: if you have a multi-agent or multi-MCP demo, Topology is the visualization that sells the architecture in the demo video. Screenshot worth one frame.

### 18. **Agent Evaluation** — auto-evaluate multi-step interactions

What it is: Automated evaluation of complex, multi-step interactions. Because LLMs are non-deterministic, regular unit tests don't work.

**HEADS UP — also competes with Arize Phoenix.** Same dynamic as Observability — Phoenix is more developer-experience-y around datasets, experiments, prompt versioning, while Agent Evaluation is the native lightweight option.

For an Arize wedge: use Phoenix Datasets + Experiments (richer eval ergonomics, exposable to the agent via MCP) instead of Agent Evaluation.

### 19. **Agent Simulation** — auto-generated edge case tests

What it is: Auto-generates thousands of sample interactions to test before pushing to prod.

For the hackathon: useful for the video narrative — "We ran 1,000 simulated interactions and the agent succeeded on 94% of them." Real demonstration of sophistication.

### 20. **Agent Optimizer** — instruction refinement loop

What it is: Refines agent instructions based on failure signals — continuous feedback loop to improve agents over time.

**For the Arize wedge specifically:** Agent Optimizer + Phoenix MCP = a powerful pairing. The agent reads its Phoenix traces, identifies failure patterns, and uses Agent Optimizer to refine its own instructions. **This is a viable wedge sentence for Abu's Q2 (`07-pre-commit-checklist.md`):**

> *"A solo developer shipping under deadline wastes hours debugging why their LLM agent went off the rails. My agent ingests Phoenix traces from a target agent, identifies the failure class, uses Phoenix Datasets to assemble a regression set, runs Agent Optimizer to propose an instruction fix, then runs a Phoenix Experiment comparing baseline vs optimized — all autonomously."*

This wedge uses 3+ Phoenix MCP tools AND a native Agent Platform primitive (Agent Optimizer), demonstrating both partner integration depth AND Google Cloud integration depth. Hits all 4 judging criteria.

---

## Decision matrix: which components to actually use in the 9-day build

| Component | Use? | Why |
|---|---|---|
| **ADK** | ✅ Required (Arize track) | Code-first runtime mandatory for Phoenix tracing |
| **Agents CLI** | 🟡 Strongly consider | Fastest scaffold; reduces "blank IDE" overhead |
| **Agent Studio** | 🟡 Optional | Could prototype here, export to ADK |
| **Agent Garden** | 🟢 Check before coding | Maybe a template gets you 70% there |
| **MCP support in ADK** | ✅ Required | This is how you wire Phoenix MCP |
| **A2A** | 🔵 Only if multi-agent | Skip if single-agent design |
| **Agent Runtime** | ✅ Default deployment | <1s cold start matters for demo |
| **Cloud Run** | 🟡 Alternative | Use if you need a custom container or Streamlit frontend |
| **Agent Sessions** | ✅ Free (auto via ADK) | No code needed |
| **Memory Bank** | 🟢 Use if wedge benefits | Don't roll custom memory |
| **Agent Sandbox** | 🔵 Only if agent runs code | Skip otherwise |
| **Agent Identity** | ✅ Free with Runtime | Mention in video |
| **Agent Registry** | ✅ Auto-catalogs MCP servers | Behind the scenes |
| **Model Armor** | 🟢 If demo is sensitive-data | Free judging points |
| **Agent Observability** | 🟡 Complement to Phoenix | Mention as "human-facing" vs Phoenix MCP as "agent-facing" |
| **Agent Evaluation** | 🔴 Skip in favor of Phoenix Datasets | Arize differentiation |
| **Agent Simulation** | 🟢 Use in demo video | "We ran N simulated interactions, here's the success rate" |
| **Agent Optimizer** | 🟢 USE | Best paired with Phoenix → strongest wedge |
| **Agent Policies / Gateway / Anomaly Detection / Security Dashboard / Topology** | 🔵 Awareness only | Skip implementation, name-drop if relevant |

Legend: ✅ required / 🟢 high-value / 🟡 useful / 🔵 awareness only / 🔴 skip

---

## How this changes the Arize wedge

`CONTEXT.md` §2 and `07-pre-commit-checklist.md` recommended an Arize wedge along the lines of "agent that observes/grades/debugs other agents." After this transcript, that wedge gets sharper:

**Refined wedge candidate:**

> *"A solo dev shipping an AI agent under deadline pressure spends hours debugging why their agent went off the rails — they can SEE the traces in Agent Observability, but can't act on them at LLM speed. My agent ingests Phoenix traces from the target agent (via Phoenix MCP), identifies failure classes, assembles a regression dataset, uses Agent Optimizer to propose an instruction fix, runs a Phoenix Experiment to A/B test baseline vs optimized, and writes a Markdown report with the recommended diff. The user reviews and merges. Time-to-fix drops from 4 hours to 90 seconds."*

What makes this strong:
1. **Hyper-specific role + pain** (solo dev under deadline)
2. **3+ step autonomous workflow** (read traces → identify → assemble → optimize → A/B → report)
3. **Multiple Phoenix MCP tools** used (traces, prompts, datasets, experiments — matches Q4 in `07-pre-commit-checklist.md`)
4. **Pairs partner-MCP with Google-native primitive** (Phoenix + Agent Optimizer) → demonstrates Tech Implementation depth on BOTH sides
5. **Measurable outcome** for the video (time-to-fix metric)
6. **Recursively self-relevant** — the agent could even debug ITSELF, dogfooding the demo

Open question for Abu: do you want to commit to this wedge, or generate more candidates with `sahil-idea-generator` constrained to Arize + the new Agent Platform knowledge?

---

## Sources

- **Primary:** [Holt Skinner video — Gemini Enterprise Agent Platform](https://youtu.be/j8qW5poBkEU) (full transcript at `refs/holt-skinner-gemini-enterprise-agent-platform-transcript.md`)
- **Master link directory:** `refs/agent-platform-readme.md` (Google's official README at github.com/Google-Cloud-AI/agent-platform — fetched 2026-06-02)
- **Quick-link card:** `refs/official-links.md` (resolved short-links + most-used URLs)
- **Onboarding:** https://goo.gle/agent-platform-onboard (Google's official quickstart — start here)
- **ADK docs:** https://adk.dev
- **Agents CLI docs:** https://google.github.io/agents-cli/
- **Tutorial notebooks:** https://github.com/GoogleCloudPlatform/generative-ai (the actual code samples live here, not in the `Google-Cloud-AI/agent-platform` repo which is just a README directory)
- **Protocol specs:** MCP (https://modelcontextprotocol.io/), A2A (https://a2a-protocol.org), A2UI (https://a2ui.org), AP2 (https://ap2-protocol.org), UCP (https://ucp.dev/)
- Companion file: `02a-google-cloud-stack.md` (SDK code, deployment patterns — **note: Gemini 2.5 pricing in §4 is stale; default to 3.5 Flash now**)
- Companion file: `mcp-primer.md` (MCP protocol details)
- Companion file: `partner-arize.md` (Phoenix MCP deep dive — pairs with §16 above)
