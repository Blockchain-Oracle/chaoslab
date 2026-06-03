# Context Corpus — Reading Guide for Downstream Agents

> **PURPOSE.** This folder is a **domain knowledge corpus** for AI agents that will design and build ChaosLab — a system that runs adversarial fault injection against OTHER PEOPLE'S AI agents and emits hardening recipes.
>
> **WHAT THIS IS NOT.** This is not a spec. This is not architecture. There are no "ChaosLab should..." statements in this folder. Every file is descriptive — what EXISTS in the wild, what's TRUE about a standard, what failed in production, what red-team products ship today. Downstream agents read this corpus and make architectural decisions for themselves.
>
> **READ THIS FIRST. THEN READ THE FILES BELOW IN ANY ORDER.** Each file is self-contained and cross-references the others.

---

## Goal alignment (re-read before designing)

**ChaosLab is for ANYONE'S agent.** Not just ADK agents. A real user shows up with a LangChain agent, or a CrewAI agent, or a browser-use agent, or a voice agent at Vapi, or a custom Python function-calling loop — and ChaosLab should have an answer. Earlier passes (brainstorm + architecture) assumed ADK-only targets. That assumption was wrong. This corpus exists to fill the gap.

The hackathon (Google Cloud Rapid Agent, deadline 2026-06-11, Arize track) lets us build ChaosLab with full Gemini + Agent Builder ecosystem + Phoenix MCP — but the AGENTS BEING TESTED can come from anywhere.

---

## The 6 files in this folder

### `01-agent-shapes-taxonomy.md` — 1,384 lines

**What it is:** the canonical taxonomy of "what kinds of agents exist in 2026." 25 canonical shapes catalogued (customer-support chat, voice agents at Vapi/Retell, Cursor-style coding, Devin-style autonomous coding, browser-use research agents, sales/CRM agents like Lindy/Clay, multi-agent CrewAI pipelines, ADK SequentialAgent + LoopAgent, LangChain legacy, LangGraph, AutoGen, Mastra, RAG-over-docs, n8n/Zapier nodes, browser-extensions, Slack/Discord bots, email auto-reply, custom OpenAI function-calling loops, ChatGPT custom GPTs, etc.).

**Why downstream agents need it:** ChaosLab cannot be designed without knowing what kinds of agents it might be pointed at. Each shape has different primitives, deployment shape, failure surface, instrumentation surface, and fault-injection accessibility. Without this taxonomy, every architectural decision is shooting blind.

**Structure:** 8 taxonomy axes → 25 shapes (each with examples + primitives + deployment + failure surface + instrumentation surface + fault-injection accessibility) → discovery surfaces → interface contracts → 60+ catalogued failure modes IDed (`F-LLM-*`, `F-TOOL-*`, `F-STATE-*`, `F-LG-*`, `F-V-*`, `F-B-*`, `F-R-*`, `F-E-*`, `F-D-*`) → population data → framework-agnostic chaos-testing factual surface area → ~100 cited sources.

**Key data downstream will care about:**
- The shape-vs-injectability matrix in §7 (which shapes admit which fault classes)
- The 5 hardest-to-inject shapes vs 5 most-amenable (§7 closing matrix)
- The discovery surfaces table (§3) — what's publicly readable per shape

### `02-production-failures.md` — 984 lines

**What it is:** real-world AI agent failures catalogued — Air Canada chatbot, DPD swearing, Microsoft Tay, Bard demo, NYC MyCity chatbot, Chevy $1 Tahoe, Anthropic agentic-misalignment cases, OpenAI Operator unintended actions, Replit prod-DB delete, Cursor file-rewrite incidents — plus GitHub issues from agent framework repos (LangChain, LangGraph, CrewAI, AutoGen, AutoGPT, ADK), X failure threads, red-team research papers, AI Incident Database review, slopsquatting/supply-chain incidents.

**Why downstream agents need it:** the fault-class catalog ChaosLab ships should be informed by what actually breaks in production, not by what's theoretically possible. Real incidents give a ground truth signal — "this is what happens when X fault hits agent of shape Y."

**Structure:** methodology → famous public incidents → AI Incident Database review → GitHub framework issues per repo (with issue IDs + URLs) → X case studies → red-team research papers → failure pattern convergence → "what would have caught this in pre-prod chaos testing" lens → sources.

**Key data downstream will care about:**
- Top 10 most-common failure root causes across all incidents (§7)
- Top 5 failure modes hardest to detect in dev/test (§7) — these are the ones ChaosLab's value prop depends on
- Per-incident "what fault class would have caught this" mapping (§8)

### `03-redteam-products-deep.md` — 1,823 lines

**What it is:** technical deep-dive on every meaningful red-team / agent-testing product in market — Lakera Guard + Red, Mindgard, HiddenLayer, NVIDIA Garak (45 probe families with literature citations), Microsoft PyRIT (PAIR/TAP/Crescendo attacks + DuckDB memory schema), promptfoo (157-plugin catalog), DeepEval/DeepTeam, TruLens, Phoenix evaluators with verbatim source code.

**Why downstream agents need it:** ChaosLab is in this market category. Knowing what leaders do — their fault libraries, UX patterns, report formats, agent-interface contracts, score concepts — is the difference between "yet another red-team tool" and a genuinely differentiated submission.

**Structure:** product-by-product deep dive → comparative matrix on 8 axes → UX patterns across all products → 10 named market gaps (each sourced) → standards mapping (OWASP LLM Top 10, MITRE ATLAS) → appendices on agent-under-test interface table and attack-location cross-reference.

**Key data downstream will care about:**
- The comparative matrix (§11) — what does each product's "agent under test" interface look like?
- The 10 market gaps (§13) — especially the two biggest:
  - **No product treats a multi-agent A2A topology as a first-class target** (every existing tool assumes single endpoint). Uncrowded category.
  - **No product runs the "production trace → red-team regression corpus" curation loop** (Phoenix has the primitives, nobody wired them).

### `04-cross-framework-instrumentation.md` — 1,959 lines

**What it is:** for every major agent framework (ADK Python/TS/Java/Go, LangChain, LangGraph, CrewAI, AutoGen/AG2, Mastra, Vercel AI SDK, OpenAI Agents SDK, Anthropic with tools, browser-use, Vapi, Retell, LiveKit Agents, Pipecat, n8n, Zapier AI, Make.com, custom Python, ChatGPT custom GPTs, Claude Projects + MCP, black-box production agents) — the native tracing story, OpenInference path, Phoenix integration code, tool-call injection surface, prompt-mutation injection surface, latency-injection surface, discovery mechanism.

**Why downstream agents need it:** if ChaosLab is meant to test "anyone's agent," it needs a clear story for HOW to instrument each framework. This file is the matrix. Without it, designs default to ADK-only (the original blind spot).

**Structure:** framework-by-framework (~20 frameworks) → cross-framework summary matrix → minimum "agent under test" interface levels with which-frameworks-supported per level.

**Key data downstream will care about:**
- The 5 cleanest injection paths (ADK Python, Vercel AI SDK, CrewAI, Pipecat, OpenAI Agents SDK)
- The 5 worst injection paths (ADK Java/Go, closed-source black-box, ChatGPT GPT Actions, Zapier/Make.com, voice agents at Vapi/Retell hosted)
- One-line operational traps (e.g., Vertex Agent Engine's `register(batch=False, set_global_tracer_provider=False)` requirement)

### `05-agent-interfaces-fingerprinting.md` — 1,633 lines

**What it is:** agent interface contracts (AgentCard spec, OpenAPI for agents, MCP server metadata, ChatGPT Custom GPT manifests, LangServe routes, Mastra interfaces, browser-agent endpoints, voice-agent dispatch, Slack bot interactions, email webhooks, CLI agents) AND fingerprinting techniques for closed-source agents (system-prompt extraction, behavioral fingerprinting, inter-token timing identification, DNS-canary tool-call probing, capability probing).

**Why downstream agents need it:** ChaosLab has to accept "an agent" as input. The shape of that input — what info is required, what's discovered, what's fingerprinted — determines the UX, the API, the auth surface, the breadth of supported targets.

**Structure:** each interface standard → black-box fingerprinting techniques → practical discovery workflow (fallback chain) → authentication considerations → MCP-vs-HTTP question → capability negotiation patterns → the "consenting agent" / ToS problem.

**Key data downstream will care about:**
- The discovery fallback chain (`agent-card.json` → `mcp.json` → MCP `initialize` → `/openapi.json` → `/input_schema` → `/swagger-ui`)
- The inter-token timing fingerprinting technique (arXiv 2502.20589) — model identification without privileged access
- The ToS / consent question and how OSS chaos tools handle it (Garak/PyRIT use user-supplied targets + ship vulnerable lab environments)

### `06-open-standards.md` — 1,859 lines

**What it is:** spec-level technical reference for every open standard relevant to agents — MCP 2025-11-25, A2A v1.0 (full spec), OpenInference (10 span kinds with attribute namespaces), OpenTelemetry GenAI conventions, AP2 v0.2 (three-mandate model), UCP, A2UI v0.8/v0.9, OWASP LLM Top 10 (2025), OWASP Agentic ASI Top 10 (2026), MITRE ATLAS (16 tactics), NIST AI RMF + AI 600-1, agent benchmarks (ARC-AGI-2, AgentBench, SWE-Bench Verified, Tau-Bench, BrowseComp, WebArena, Mind2Web), red-team attack technique papers (GCG, AutoDAN, PAIR, TAP, Crescendo).

**Why downstream agents need it:** the standards are the contracts ChaosLab must speak to be maximally compatible AND credible. OWASP/MITRE mapping in reports earns Tech Implementation judging points. Knowing the OTel→OpenInference conversion is the difference between native traces and broken ones.

**Structure:** 16 sections at spec-level depth, organized by standard, with full citation and version-pinning.

**Key data downstream will care about:**
- The 3 standards most-affecting ChaosLab's reach: MCP 2025-11-25, A2A v1.0, OpenInference
- The 1 standard most-likely-to-evolve during build-and-judging-window: OWASP Agentic ASI Top 10 (still in community comment phase as of late 2025-12)
- The unified trace story across MCP+A2A+AP2+OpenInference in §15

---

## Cross-cutting threads across all 6 files

When designing ChaosLab, these recurring themes appear in multiple files. Downstream agents should treat them as factual signals, not recommendations.

| Thread | Files | What's converged on |
|---|---|---|
| **A2A multi-agent attack surface is unowned** | 03 §13 (market gap), 04 §10 (AutoGen injection), 06 §2 (A2A spec), 05 §1 (AgentCard) | Every red-team product assumes single-endpoint targets; the multi-agent layer is open territory. |
| **Phoenix MCP is partial** | (referenced in `architecture/02`, supported by 03 §9 and 06 §3) | Read-side experiment/annotation tools only. Need custom Python SDK FunctionTool wraps. |
| **OpenInference as the unifying substrate** | 04 §all, 06 §3, 02 §6 | Most agent frameworks have an OpenInference instrumentor — this is the cross-framework hook. |
| **Black-box agents need fingerprinting** | 01 §3, 05 §12, 03 §13 | A growing share of agents in 2026 are closed-source SaaS; chaos testing them needs behavioral fingerprinting. |
| **OWASP Agentic Top 10 (ASI) is the new vocabulary** | 06 §9, 03 §14, 02 §6 | Released 2025-12, judges will recognize the labels. Map fault classes to ASI01-ASI10. |
| **Voice + browser agents are hard targets** | 01 §2, 04 §11-13, 05 §8-9 | Limited tracing, limited callback hooks, but high-value because rapidly growing share of deployments. |

---

## Recommended reading order for downstream agents

Different downstream agents have different needs. Pick whichever ordering matches your task:

### For `sahil-spec-writer` writing the PRD / architecture / UX-spec
1. **`01-agent-shapes-taxonomy.md`** — understand the universe of targets
2. **`04-cross-framework-instrumentation.md`** — understand the integration matrix
3. **`05-agent-interfaces-fingerprinting.md`** — understand the input contract
4. **`03-redteam-products-deep.md`** — understand the competitive landscape + market gaps
5. **`02-production-failures.md`** — ground the fault-class catalog in reality
6. **`06-open-standards.md`** — pin the protocol versions, OWASP labels

### For a coding agent implementing a specific feature
1. **`04-cross-framework-instrumentation.md`** — the code patterns
2. **`06-open-standards.md`** — the wire formats
3. **`05-agent-interfaces-fingerprinting.md`** — the discovery mechanism
4. The other files only as needed

### For the demo / UX design agent
1. **`03-redteam-products-deep.md` §12** — UX patterns across all red-team products
2. **`02-production-failures.md`** — narrative-grade incident stories for demo
3. **`01-agent-shapes-taxonomy.md` §5** — failure modes worth visualizing
4. **`06-open-standards.md` §10-13** — benchmarks for "we hit X% on Y" claims

### For an agent doing competitive positioning
1. **`03-redteam-products-deep.md` §11 (matrix) and §13 (gaps)**
2. **`02-production-failures.md` §8 (what would have been caught)**
3. **`01-agent-shapes-taxonomy.md` §7 (framework-agnostic thesis)**

---

## What's NOT in this corpus (deliberate omissions)

Downstream agents should be aware of these gaps so they don't assume coverage:

- **No specific decisions about ChaosLab's UI mockups.** The earlier `architecture/05-ux-and-demo.md` has Option A-D mockups but those are exploratory — downstream agents should design fresh from `03-redteam-products-deep.md §12` (UX patterns inventory).
- **No specific decisions about deployment topology.** The earlier `architecture/06-deployment-ops.md` proposed 3 Cloud Run services — downstream agents may reconsider given the multi-agent-A2A-mesh gap surfaced by `03-redteam-products-deep.md §13`.
- **No specific decisions about which agent shapes ChaosLab targets first.** `01-agent-shapes-taxonomy.md §7` lists the matrix; downstream chooses based on `02-production-failures.md` impact data + `03-redteam-products-deep.md` competitive analysis.
- **No specific RAT runbook updates.** The Phoenix MCP partial-surface finding is in `architecture/02-phoenix-deep-dive.md` and the RAT runbook was patched accordingly — but downstream agents should re-evaluate whether the RAT covers the right risks given the broader-target reframing.
- **No spec-writer-ready outputs.** This corpus is raw input. The spec-writer's job is to read it and produce `docs/PRD.md`, `docs/architecture.md`, `docs/ux-spec.md`, `docs/epics.md`, `docs/stories/*.md`.

---

## How this corpus relates to the other research folders

```
research/google-cloud-rapid-agent/
├── CONTEXT.md                              ← master entrypoint (read this first if you've never been here)
├── 00-overview.md                          ← human-readable one-pager
├── 01-prizes-tracks.md                     ← hackathon rules + judging
├── 02a-google-cloud-stack.md               ← ADK / Cloud Run / Agent Runtime / Gemini code
├── 02b-gemini-enterprise-agent-platform.md ← full Google platform map
├── 03-project-gallery.md                   ← Devpost field state
├── 05-prior-winners.md                     ← prior Google AI hackathon winner patterns
├── 06-hidden-field.md                      ← per-track competition density
├── 07-pre-commit-checklist.md              ← (now superseded by this corpus)
├── mcp-primer.md                           ← MCP overview (06-open-standards.md goes deeper)
├── partner-{arize,elastic,fivetran,gitlab,mongodb,dynatrace}.md ← per-partner deep dives
├── RAT-runbook.md                          ← tomorrow's Day-1 validation (already patched)
├── refs/                                   ← raw transcripts + link directories
├── brainstorm/                             ← wedge selection (W1 ChaosLab locked)
│   ├── 00-synthesis.md
│   ├── 01-first-principles-capabilities.md
│   ├── 02-pain-points.md
│   ├── 03-agent-landscape.md
│   ├── 04-protocol-wedges.md
│   ├── 05-ecosystem-refactor.md
│   ├── 06-idea-rankings.md
│   └── 07-novelty-gate.md
├── architecture/                           ← exploratory build research (synthesis is PRELIMINARY)
│   ├── 00-synthesis.md                     ← ⚠ banner says these are NOT locked decisions
│   ├── 01-reference-implementations.md
│   ├── 02-phoenix-deep-dive.md             ← rich; Phoenix MCP partial finding
│   ├── 03-multi-agent-patterns.md
│   ├── 04-fault-injection-eval.md
│   ├── 05-ux-and-demo.md
│   └── 06-deployment-ops.md
└── context/                                ← THIS FOLDER — pure domain knowledge corpus
    ├── 00-README.md                        ← (this file)
    ├── 01-agent-shapes-taxonomy.md
    ├── 02-production-failures.md
    ├── 03-redteam-products-deep.md
    ├── 04-cross-framework-instrumentation.md
    ├── 05-agent-interfaces-fingerprinting.md
    └── 06-open-standards.md
```

**Folder roles:**

- `brainstorm/` — answers **WHAT to build** (locked: W1 ChaosLab for Agents, Arize track). Opinionated by design.
- `architecture/` — early exploratory research on **HOW we might build it**. The synthesis there is preliminary. Treat as data, not decisions.
- `context/` — pure descriptive **DOMAIN KNOWLEDGE** about agents in the wild. No opinions. Downstream agents read this to make their own architectural decisions.

Total corpus: ~24,000 lines across 22 files. Coverage is now end-to-end: market, technical, standards, competition, failures, frameworks, interfaces. Downstream `sahil-spec-writer` has everything it needs to produce a spec without "going outside to research themselves."
