# Saturation Map — What's Already Been Built in the Agent-Hackathon Space

**Date:** 2026-06-03 (T-8 days to submission)
**Hackathon:** Google Cloud Rapid Agent Hackathon (rapid-agent.devpost.com)
**Method:** Direct WebFetch attempts + WebSearch when Devpost endpoints refused. Where direct gallery scrape failed, prior-hackathon proxies are used. All projects have URLs (gallery URL or aggregator URL).

---

## TL;DR — Rapid Agent gallery is still dark

The `rapid-agent.devpost.com/project-gallery` and `/submissions` pages still respond either with **"hackathon managers haven't published this gallery yet"** (confirmed 2026-06-02 in `03-project-gallery.md`) or refuse the connection from this tool environment today. Devpost convention: galleries unlock either day-of-deadline or 1–2 weeks after.

**Submission count visible: 0. Registered participants: 2,777+ (as of June 2026 — note: the prior `03-project-gallery.md` cited 12,582; that figure appears stale or was a different counter. The hackathon page itself reports 2,777+ today.)**

Because the host gallery is empty, this report leans on **proxy saturation** from comparable agent hackathons whose galleries ARE published:

| Proxy hackathon                              | Submissions | Why it's a proxy                             |
| -------------------------------------------- | ----------: | -------------------------------------------- |
| Google Cloud ADK Hackathon (2025)            |         477 | Same sponsor, same stack family, agent focus |
| Vertex AI Agent Builder Hackathon (2024)     |        ~200 | Direct Google Cloud predecessor              |
| AI Accelerate (Elastic + Fivetran, 2025)     |     n/a yet | Same two partner tracks, just-closed         |
| GitLab AI Hackathon (Feb–Mar 2026)           |        600+ | Same GitLab track shape, 7,000 devs          |
| Great Agent Hack 2025 (Holistic AI x UCL)    |          51 | Has Iron-Man + Glass-Box + red-team tracks   |
| AWS AI Agent Global Hackathon (Sep–Oct 2025) |  >$45K pool | Same agent-builder framing                   |
| Microsoft AI Agents Hackathon 2025           |         570 | Same framing                                 |
| WeaveHacks (W&B agent protocols)             |   n/a count | Observability track shape (Phoenix analog)   |

---

## How to read this doc

- **PROJ-NN** rows are the highest-signal individual prior projects (named publicly, URL exists). They are NOT a complete list — they are the projects most-relevant to the six Rapid Agent tracks (Arize / Elastic / Fivetran / GitLab / MongoDB / Dynatrace).
- "Idea shape" is the higher-level grouping that determines whether YOUR project will look like a duplicate or a fresh angle.
- 🔴 / 🟡 / 🟢 ratings = saturation across all observed agent hackathons in the last 12 months, NOT just this hackathon.

---

# PART 1 — Per-track entry count for rapid-agent.devpost.com

Because the gallery is hidden, these are **predicted** distributions extrapolated from registered-participant count + typical 5% completion rate + brand-recognition skew (per prior analysis in `03-project-gallery.md`):

| Track     |                      Predicted submissions | Predicted saturation | Notes                                                                   |
| --------- | -----------------------------------------: | -------------------- | ----------------------------------------------------------------------- |
| MongoDB   | 150–300 (capped if 2,777 reg holds: 40–80) | RED (predicted)      | Best-known brand of the six; default "agent + vector RAG" lane          |
| GitLab    |                         100–200 (or 30–60) | RED (predicted)      | Active GitLab AI Hackathon community already trained on the pattern     |
| Elastic   |                          80–150 (or 25–50) | YELLOW (predicted)   | Mid-tier name recognition; search/RAG well-trodden                      |
| Dynatrace |                          50–100 (or 15–30) | YELLOW (predicted)   | Observability is niche but trending in agent ops                        |
| Fivetran  |                           40–80 (or 10–25) | YELLOW (predicted)   | Data-pipeline angle is narrow; fewer hackers know it                    |
| Arize     |                            30–70 (or 8–20) | GREEN (predicted)    | Smallest dev mindshare; specialist tool (LLM obs/evals). **OUR TRACK.** |

If the lower-bound (matching the 2,777-participant figure) holds, **Arize will see roughly 8–20 submissions in total** — winnable with a top-3 of 8.

[UNVERIFIED] until 2026-06-12 publication.

---

# PART 2 — Notable individual projects from proxy hackathons

Each row has a URL. Where the project isn't yet on a public gallery, the hackathon gallery URL is given as the find-it pointer.

### PROJ-01: Voltaros

- **Hackathon:** Google Cloud ADK Hackathon (2025)
- **Track / sponsor:** Google Cloud (no per-partner tracks at ADK)
- **One-line pitch:** Automates chaos engineering with ADK agents — stress-tests GKE apps with pod crashes and latency triggers.
- **Tech stack hints:** Google ADK, GKE, fault injection
- **URL:** https://googlecloudmultiagents.devpost.com/project-gallery (project listed in winner highlights)
- **Idea shape:** **Chaos engineering for infrastructure, agent-driven**

### PROJ-02: SalesShortcut

- **Hackathon:** ADK Hackathon (Grand Prize)
- **One-line pitch:** AI-powered SDR system for automated lead-gen / outreach with multi-agent architecture.
- **Tech stack hints:** Google ADK, multi-agent
- **URL:** https://github.com/shubhamprajapati7748/google-adk-apps/tree/main/SalesShortcut
- **Idea shape:** Vertical sales/SDR agent

### PROJ-03: Energy Agent AI

- **Hackathon:** ADK Hackathon (North America Regional Winner)
- **One-line pitch:** Multi-agent energy management for customer engagement.
- **URL:** https://github.com/shubhamprajapati7748/google-adk-apps/tree/main/energyagentai
- **Idea shape:** Vertical utility/energy agent

### PROJ-04: Edu.AI

- **Hackathon:** ADK (Latin America Regional Winner)
- **One-line pitch:** Multi-agent educational platform — evaluates Brazilian ENEM essays, generates study plans.
- **URL:** https://github.com/shubhamprajapati7748/google-adk-apps/tree/main/edu-ai-adk
- **Idea shape:** Vertical education agent

### PROJ-05: AgriFlow Nexus

- **Hackathon:** ADK
- **One-line pitch:** Multi-agent platform to cut SADC farm-to-market costs, price-predict, grade sustainability.
- **URL:** https://googlecloudmultiagents.devpost.com/project-gallery
- **Idea shape:** Vertical agri/supply-chain agent

### PROJ-06: GuardianOS

- **Hackathon:** ADK
- **One-line pitch:** Multi-agent compliance + monitoring for privacy-preserving blockchain transactions.
- **URL:** https://googlecloudmultiagents.devpost.com/project-gallery
- **Idea shape:** Compliance + monitoring agent (regulatory)

### PROJ-07: TradeSage AI

- **Hackathon:** ADK
- **One-line pitch:** Multi-agent financial analysis for trading hypothesis evaluation.
- **URL:** https://github.com/shubhamprajapati7748/google-adk-apps/tree/main/tradesage-mvp
- **Idea shape:** Finance / trading agent

### PROJ-08: BleachAgentBuilder

- **Hackathon:** ADK
- **One-line pitch:** Visual no-code platform for creating custom AI agents through natural-language prompts.
- **URL:** https://github.com/shubhamprajapati7748/google-adk-apps/tree/main/bleachAgentBuilder
- **Idea shape:** Agent-builder meta-tool

### PROJ-09: NewHire Onboarding Assistant

- **Hackathon:** ADK
- **One-line pitch:** Multi-agent system for engineer onboarding (production-ready).
- **URL:** https://github.com/shubhamprajapati7748/google-adk-apps/tree/main/newhire_onboarding_assistant
- **Idea shape:** Internal-tool / HR agent

### PROJ-10: InsuraIQ

- **Hackathon:** ADK
- **One-line pitch:** Virtual health-insurance agent guiding policy selection.
- **URL:** https://github.com/shubhamprajapati7748/google-adk-apps/tree/main/insuraiq
- **Idea shape:** Vertical insurance agent (RAG variant)

### PROJ-11: Particle Physics Agent

- **Hackathon:** ADK
- **One-line pitch:** Multi-agent system generating TikZ Feynman diagrams from text.
- **URL:** https://github.com/shubhamprajapati7748/google-adk-apps/tree/main/Particle-Physics-Agent
- **Idea shape:** Vertical scientific / niche-domain agent

### PROJ-12: Macro Mancer / QuantumFin AI / AI Stock Analyst / Stock Analysis Multi-Agents / Intelligent Investment Agents

- **Hackathon:** ADK (5 separate finance/trading projects in the awesome-list)
- **One-line pitch:** Various flavors of multi-agent financial analysis.
- **URL:** https://github.com/shubhamprajapati7748/google-adk-apps
- **Idea shape:** Finance / trading agent (**high duplicate density even within one hackathon**)

### PROJ-13: Nexora AI

- **Hackathon:** ADK
- **One-line pitch:** Personalized learning platform with AI-assisted course creation.
- **URL:** https://github.com/shubhamprajapati7748/google-adk-apps/tree/main/Nexora
- **Idea shape:** Vertical education agent

### PROJ-14: Blog Generator

- **Hackathon:** ADK
- **One-line pitch:** Transforms YouTube videos into SEO-optimized blog posts.
- **URL:** https://github.com/shubhamprajapati7748/google-adk-apps/tree/main/blog-generator
- **Idea shape:** Content-generation agent

### PROJ-15: Gitdefender

- **Hackathon:** GitLab AI Hackathon (Feb–Mar 2026, Google Cloud Grand Prize)
- **One-line pitch:** Works inside code-review workflow — spots security bugs, writes fix, opens MR. No human in loop.
- **Tech stack hints:** GitLab Duo Agent Platform, MR API
- **URL:** https://about.gitlab.com/blog/gitlab-ai-hackathon-2026-meet-the-winners/
- **Idea shape:** **Code-review / security-fix MR-emission agent** (canonical GitLab winner shape)

### PROJ-16: MR Compliance Auditor

- **Hackathon:** GitLab AI Hackathon (2026)
- **One-line pitch:** Collects evidence across MRs, maps to SOC2 controls, streams scores to dashboard.
- **URL:** https://about.gitlab.com/blog/gitlab-ai-hackathon-2026-meet-the-winners/
- **Idea shape:** **Compliance / audit-MR agent**

### PROJ-17: GraphDev

- **Hackathon:** GitLab AI Hackathon (Anthropic Grand Prize)
- **One-line pitch:** Maps code links, shows system change over time.
- **URL:** https://about.gitlab.com/blog/gitlab-ai-hackathon-2026-meet-the-winners/
- **Idea shape:** Code-graph / dev-intelligence agent

### PROJ-18: Aegis

- **Hackathon:** GitLab AI Hackathon (Google Cloud Runner Up)
- **One-line pitch:** AI-powered explanations for every decision; deployed to Google Cloud production.
- **URL:** https://about.gitlab.com/blog/gitlab-ai-hackathon-2026-meet-the-winners/
- **Idea shape:** **Agent-explainability / decision-trace** (close to Phoenix observability shape)

### PROJ-19: DocSync

- **Hackathon:** GitLab AI Hackathon (Anthropic Runner Up)
- **One-line pitch:** Doc-sync agent — keeps documentation in sync with code via MR.
- **URL:** https://about.gitlab.com/blog/gitlab-ai-hackathon-2026-meet-the-winners/
- **Idea shape:** Docs-auto-update agent

### PROJ-20: PHAROS

- **Hackathon:** Elasticsearch Agent Builder Hackathon (previous edition)
- **One-line pitch:** Drug-safety agent using Elastic for clinical RAG.
- **URL:** https://elasticsearch.devpost.com/
- **Idea shape:** Vertical healthcare RAG agent

### PROJ-21: Gauntlet

- **Hackathon:** Elasticsearch Agent Builder Hackathon (previous edition)
- **One-line pitch:** [Description not captured; appears in winner list]
- **URL:** https://elasticsearch.devpost.com/
- **Idea shape:** Search-RAG agent

### PROJ-22: Kenya HIV Duplicate-Detection Agent

- **Hackathon:** Elasticsearch Agent Builder Hackathon
- **One-line pitch:** Agent that finds duplicate records in Kenya's national HIV program registry.
- **URL:** https://elasticsearch.devpost.com/
- **Idea shape:** Vertical health-records / data-quality agent

### PROJ-23: Alzheimer Expert Bot

- **Hackathon:** MongoDB AI Hackathon: Code for a Cause
- **One-line pitch:** AI + vector search for evidence-based Alzheimer's clinical support.
- **URL:** https://mongodb-ai.devpost.com/project-gallery
- **Idea shape:** Vertical healthcare RAG agent (Mongo vector)

### PROJ-24: RedBot

- **Hackathon:** AI Agents Hackathon NYC (Oct 2025)
- **One-line pitch:** Autonomous agent that attacks chatbot endpoints with 140+ jailbreak templates; detects PII leaks + prompt injection.
- **Tech stack hints:** ClickHouse Cloud, OpenHands, DeepL
- **URL:** https://github.com/yli12313/AI-Agents-Hackathon-2025
- **Idea shape:** **Red-team / chatbot-attack agent** (closest in spirit to ChaosLab F1 prompt-injection class)

### PROJ-25: EcoLafaek

- **Hackathon:** AWS AI Agent Global Hackathon (winner)
- **One-line pitch:** Waste-management agent for Timor-Leste using AgentCore + Amazon Bedrock Nova-Pro multi-modal.
- **URL:** https://aws-agent-hackathon.devpost.com/updates/38140-congratulations-to-the-winners-of-the-aws-ai-agent-global-hackathon
- **Idea shape:** Vertical environment / public-impact agent

### PROJ-26: Frontline

- **Hackathon:** WeaveHacks (W&B agent protocols, MCP/A2A)
- **One-line pitch:** Gives coding agents context to debug+validate features by running frontend apps in real browser. Trace monitoring via Weave.
- **URL:** https://devpost.com/software/frontline-agent
- **Idea shape:** **Agent-for-coding-agents meta tool** with observability

### PROJ-27: Product Mate

- **Hackathon:** WeaveHacks (Tavily Sponsor Prize)
- **One-line pitch:** Self-improving RL agent generating personalized factual action items.
- **URL:** https://devpost.com/software/product-mate
- **Idea shape:** **Self-improving agent** (RL feedback loop)

### PROJ-28: Nuroxa — Dementia Risk Assistant

- **Hackathon:** Microsoft AI Agents Hackathon 2025 (notable winner)
- **One-line pitch:** AI health assistant assessing dementia risk.
- **URL:** https://techcommunity.microsoft.com/blog/azuredevcommunityblog/ai-agents-hackathon-2025-%E2%80%93-category-winners-showcase/4415088
- **Idea shape:** Vertical healthcare RAG

### PROJ-29: Great Agent Hack 2025 — 51 projects

- **Hackathon:** Holistic AI x UCL (Nov 2025)
- **Tracks:** Iron Man (robustness), Glass Box (observability), Dear Grandma (red-team / prompt injection)
- **URL:** https://hai-great-agent-hack-2025.devpost.com/project-gallery?page=1
- **Notable family** (Glass Box track per Towards Data Science writeup): observability pipelines, explainability tools, governance + safety layers, expert-discovery, traceability tools — built on LangSmith / LangFuse / CloudWatch / X-Ray / AgentGraph / AgentSeer / Who_and_When dataset.
- **Idea shape:** **Agent observability / red-team is now mainstream and saturated.** This 51-project pool is the single best evidence that "agent test/observe/red-team" is a crowded category at non-Rapid-Agent hackathons.

### PROJ-30: AgentHacks 2025 — red-teaming projects

- **Hackathon:** AgentHacks 2025
- **One-line pitch:** Multiple submissions in the agentic-research gallery do red-team eval / safety boundary testing for GPT/Claude/Gemini.
- **URL:** https://agenthacks.devpost.com/project-gallery
- **Idea shape:** Red-team / safety eval agent

### PROJ-31: ai-agents-hackathon-gtc submissions

- **Hackathon:** NVIDIA GTC AI Agents Hackathon (Vertex Ventures US + CreatorsCorner, 2025)
- **URL:** https://ai-agents-hackathon-gtc.devpost.com/project-gallery?page=1
- **Idea shape:** Mixed — gallery published, contains finance / healthcare / coding-assistant / RAG submissions

### PROJ-32: Autonomous Agents Hackathon submissions

- **URL:** https://autonomous-agents-hackathon.devpost.com/project-gallery
- **Idea shape:** Mixed agent gallery — Lux Capital / Modal / Cognition stack

### PROJ-33: 100 Agents Hackathon submissions

- **URL:** https://100agents.devpost.com/
- **Idea shape:** Mixed — pushing limits of agentic AI, open-source frameworks. Includes self-improving + observability themes.

---

# PART 3 — Saturation map by idea shape

## Idea shape: Vertical-domain agent (finance / trading / portfolio)

- **Count of projects already pursuing this:** **15+** (TradeSage AI, Macro Mancer, QuantumFin AI, AI Stock Analyst, Stock Analysis Multi-Agents, Intelligent Investment Agents, several others in MongoDB / Microsoft galleries)
- **Examples:** TradeSage AI, Macro Mancer, QuantumFin AI
- **Saturation rating:** 🔴 HIGH (15+)
- **Why teams gravitate here:** Easy to demo; well-known evaluation criteria; "if I lose, I still learn finance".
- **Differentiation difficulty:** HIGH. To stand out you need novel data ingest or actual paper-trading P&L, not just "agent looks at CNBC".

## Idea shape: Vertical-domain agent (healthcare / clinical RAG)

- **Count:** **6+** (PHAROS, Kenya HIV agent, InsuraIQ, Alzheimer Expert Bot, Nuroxa, Edu.AI does education-not-health but parallel)
- **Examples:** PHAROS (drug safety), Alzheimer Expert Bot, Nuroxa
- **Saturation rating:** 🔴 HIGH (6+ at top of mind; many more long-tail)
- **Why teams gravitate here:** Sympathetic story for judges; obvious public-good angle.
- **Differentiation:** HARD without domain partner / real clinician on team. Demo videos all look the same.

## Idea shape: Vertical-domain agent (education / tutor)

- **Count:** **5+** (Edu.AI, Nexora AI, multiple Microsoft hackathon winners, education-RAG agents in 100 Agents)
- **Saturation rating:** 🔴 HIGH (5+)
- **Differentiation:** Brazilian / non-English market angle is one wedge (Edu.AI's). Otherwise crowded.

## Idea shape: Code-review / security-fix MR-emission agent

- **Count:** **20+** (Gitdefender + MR Compliance Auditor + 600+ entries in GitLab AI Hackathon, of which at least dozens pursued code-review / sec-fix angle)
- **Examples:** Gitdefender, MR Compliance Auditor, GraphDev, DocSync
- **Saturation rating:** 🔴 HIGH
- **Why teams gravitate:** GitLab's last hackathon trained 7,000 devs on exactly this pattern; muscle-memory carries over.
- **Differentiation:** **VERY HARD.** Anyone going GitLab track at Rapid Agent will be compared to Gitdefender as the canonical winner.

## Idea shape: Sales / SDR / outreach agent

- **Count:** **3+** (SalesShortcut + several lead-gen agents in Microsoft + AWS hackathons)
- **Saturation rating:** 🟡 MEDIUM (3+, but Grand Prize at ADK)
- **Differentiation:** Hard — winner already exists in the same ecosystem.

## Idea shape: Multi-agent compliance / audit / regulatory

- **Count:** **4+** (GuardianOS, MR Compliance Auditor, several SOC2/compliance agents)
- **Saturation rating:** 🟡 MEDIUM (4+)
- **Differentiation:** Possible with a real partner framework (e.g., Dynatrace + actual SRE incident data) but moat is thin.

## Idea shape: Vector-RAG knowledge bot (generic)

- **Count:** **30+** (every "MongoDB / Elastic / Vertex AI knowledge-bot" submission. Vertex AI Hackathon explicitly had "Knowledge Bot" as one of 4 categories.)
- **Saturation rating:** 🔴 HIGH (default pattern)
- **Differentiation:** Hopeless without unique corpus.

## Idea shape: Chaos engineering for infrastructure (NOT for agents)

- **Count:** **1** confirmed (Voltaros) + the existence of dedicated "Production Engineering Hackathon" with chaos-engineering theme
- **Examples:** Voltaros
- **Saturation rating:** 🟡 MEDIUM (1 in agent hackathons, but a known pattern in DevOps space)
- **Differentiation:** Voltaros is GKE-pod-crash flavor — infra layer. **ChaosLab is at the AGENT layer (prompt/tool/MCP/output)** — fundamentally different target. Not a duplicate.

## Idea shape: Red-team / jailbreak / prompt-injection attack agent

- **Count:** **8+** (RedBot, AgentHacks 2025 red-team submissions, Great Agent Hack "Dear Grandma" track submissions, HackAPrompt 2.0)
- **Examples:** RedBot (140+ jailbreak templates), Dear Grandma track entries
- **Saturation rating:** 🔴 HIGH (8+)
- **Why teams gravitate:** Security framing scores well with judges; LLM safety is hot.
- **Differentiation:** **Important** for ChaosLab F1 (prompt-injection class) — this means F1 alone is NOT differentiated. ChaosLab's wedge has to be the **closed loop** (inject → observe → harden via auto-fix), not the injection itself.

## Idea shape: Agent observability / tracing dashboard

- **Count:** **15+** (most of Great Agent Hack Glass Box track + WeaveHacks observability submissions + Splunk Agentic Ops Observability track + Frontline + scattered submissions everywhere)
- **Examples:** Frontline (WeaveHacks), Aegis (GitLab AI), Glass Box track (51 projects total, ~third in this shape)
- **Saturation rating:** 🔴 HIGH (15+)
- **Why teams gravitate:** Every observability tool wants a "show me the agent" demo; easy hackathon points.
- **Differentiation:** **Critical concern for ChaosLab on Arize track.** "Build a Phoenix dashboard" alone is duplicate-shape. ChaosLab's differentiation is that it USES Phoenix to drive harden-loop, not just to display traces.

## Idea shape: Self-improving / self-healing agent

- **Count:** **5+** (Product Mate, two dedicated hackathons running in 2026: Self Improving Agents Hack + Ruya AI Hackathon 2026, plus various entries)
- **Saturation rating:** 🟡 MEDIUM (5+)
- **Differentiation:** **Adjacent to ChaosLab's harden-loop** — but the chaos+harden combination is unique. Self-improving alone is crowded; chaos→harden is not.

## Idea shape: Agent-builder / no-code agent platform

- **Count:** **3+** (BleachAgentBuilder + a few others scattered)
- **Saturation rating:** 🟡 MEDIUM (3+)
- **Differentiation:** Crowded among non-hackathon products (Langflow, n8n, Vertex AI Agent Builder itself). Hard to ship a hackathon-MVP that beats those.

## Idea shape: Data-pipeline / ingest agent (Fivetran-flavored)

- **Count:** **2+** (AI Accelerate Fivetran Challenge submissions — exact count unknown without gallery)
- **Saturation rating:** 🟡 MEDIUM (2+, low ceiling expected)
- **Differentiation:** Possible. Fivetran is least well-known of the partner names → smaller crowd, but also narrower judge-appeal story.

## Idea shape: Content-generation agent (blog / video / SEO)

- **Count:** **3+** (Blog Generator, multiple Microsoft hackathon winners)
- **Saturation rating:** 🟡 MEDIUM (3+)
- **Differentiation:** Crowded, hard to score on "potential impact".

## Idea shape: Niche scientific / specialty agent

- **Count:** **1+** (Particle Physics Agent)
- **Saturation rating:** 🟢 LOW (1)
- **Differentiation:** Easy IF you actually have the domain. Hard for generalists.

## Idea shape: HR / onboarding / internal-tool agent

- **Count:** **2+** (NewHire Onboarding Assistant + scattered)
- **Saturation rating:** 🟡 MEDIUM (2+)
- **Differentiation:** Possible but story is dry.

## Idea shape: Environment / public-good / agri / waste

- **Count:** **3+** (AgriFlow Nexus, EcoLafaek, scattered)
- **Saturation rating:** 🟡 MEDIUM (3+)
- **Differentiation:** Sympathetic story but increasingly common.

---

# PART 4 — Whitespace section

A "whitespace" claim is falsifiable only when I describe what I searched for and didn't find. Each item below lists the search terms used.

## Whitespace W-1: Closed-loop chaos engineering for AGENTS (not infrastructure)

- **Searched for:** "agent" + "chaos engineering" / "fault injection" on Devpost gallery URLs (Great Agent Hack, ADK, Microsoft AI Agents, AWS AI Agent, WeaveHacks, 100 Agents, AgentHacks, NVIDIA GTC, Autonomous Agents).
- **What found:** Voltaros (chaos for INFRA — pod crashes/latency at GKE layer). RedBot (red-team attack but no harden-loop). Dear Grandma track entries (attack only, no fix).
- **What NOT found:** Anything that does the full **inject 4 fault classes (prompt-injection / tool-noise / context-poisoning / output-malform) → observe via Phoenix traces → auto-harden via patch loop**. The closest is Product Mate's RL self-improvement, which has no chaos-injection front-end.
- **Why this is whitespace:** Chaos+observe+harden as a SINGLE pipeline at the agent-prompt/tool layer is a unique combination. The components exist separately; the assembly does not.
- **This is ChaosLab's claim.** ✅

## Whitespace W-2: Adversarial-co-evolution / red-team-as-eval-suite for agents

- **Searched for:** "self-improving agent" + "red-team" + "fault" + "adversarial eval suite" combos.
- **What found:** Self Improving Agents Hack + Ruya AI Hackathon themes (not yet judged), Product Mate.
- **What NOT found:** A project that pairs an attacker-agent (gets stronger over time) with a defender-agent (also gets stronger) such that fault discovery is closed-loop adversarial. Most current red-team work is one-shot.
- **Why this is whitespace:** Adversarial co-evolution is academically rich but no hackathon project ships it as a working closed system.

## Whitespace W-3: Per-fault-class auto-patch for agents (with diff emission to repo)

- **Searched for:** "agent" + "auto-patch" / "auto-fix" + "MR" / "PR" on hackathon galleries.
- **What found:** Gitdefender (security-fix MR for HUMAN code), DocSync (docs MR). Not for AGENT prompts/tools.
- **What NOT found:** An agent that, having detected a chaos failure in its OWN prompt or tool config, opens an MR against ITS OWN repo. This is exactly the wedge ChaosLab GitLab-hybrid emits.
- **Why this is whitespace:** Recursive self-patching of agent code IS the meta-level move that ChaosLab uniquely owns.

## Whitespace W-4: Dynatrace + agent chaos / SRE-style fault drill

- **Searched for:** "Dynatrace" + "agent" / "chaos" / "fault drill" on Devpost.
- **What found:** Dynatrace is a brand-new partner at Rapid Agent — appears in no prior published gallery. Their MCP server is also new.
- **What NOT found:** Any project pairing Dynatrace OpenTelemetry agent observability with deliberate fault injection.
- **Why this is whitespace:** Dynatrace MCP is so new that NO hackathon project exists for it yet. Lowest-population partner space.

## Whitespace W-5: Fivetran + agent + data-quality chaos

- **Searched for:** "Fivetran" + "agent" + "data quality" / "schema drift" / "chaos" on Devpost.
- **What found:** AI Accelerate had a Fivetran Challenge (build a connector, load to BigQuery, build agent on top). Submissions not enumerated in search results.
- **What NOT found:** Any project that uses Fivetran to ingest data, then **deliberately corrupts it / injects schema drift** to test an agent's resilience.
- **Why this is whitespace:** Fivetran's pipeline angle naturally extends to chaos testing of downstream agents — no one is doing this yet.

## Whitespace W-6: Multi-track + cross-partner integration (Arize + Dynatrace double-instrument)

- **Searched for:** Projects that use TWO partner MCPs at once.
- **What found:** None observed yet; Rapid Agent rules require ONE partner track but allow multi-MCP.
- **Why this is whitespace:** Cross-MCP integration story is judge-bait but no proxy hackathon has had this exact constraint.

## Whitespace W-7: Agent benchmark / leaderboard for production failure modes

- **Searched for:** "agent benchmark" + "production failure" + "hackathon" + Devpost.
- **What found:** Academic benchmarks (Who_and_When, AgentGraph). No hackathon-built leaderboard.
- **Why this is whitespace:** A live leaderboard ranking commercial agent frameworks by chaos-resilience score is a sticky-content / SEO play.

---

# PART 5 — Summary recommendation table

| Idea-shape consideration                              | Rating  | What ChaosLab does                                                  |
| ----------------------------------------------------- | ------- | ------------------------------------------------------------------- |
| Already a vertical-domain agent (finance/health/edu)? | 🔴 HIGH | NO — ChaosLab is a meta-tool                                        |
| Already a code-review MR-emission agent?              | 🔴 HIGH | NO — ChaosLab emits MR but for agent-self-patching, not human code  |
| Already an agent-observability dashboard?             | 🔴 HIGH | PARTIAL — Phoenix is used, but as drive-loop not display            |
| Already a red-team / prompt-injection attack agent?   | 🔴 HIGH | PARTIAL — F1 is prompt-injection, BUT closed-loop is differentiator |
| Already chaos-for-infrastructure (GKE/pods)?          | 🟡 MED  | NO — ChaosLab is at PROMPT/TOOL/MCP layer, not infra layer          |
| Already chaos-for-agents (4 classes + harden loop)?   | 🟢 LOW  | **YES — this is the wedge, and it is empty in priors.**             |
| Already a Dynatrace-agent project?                    | 🟢 LOW  | (FYI — could also fit Dynatrace track if Arize crowds)              |
| Already a Fivetran-data-chaos project?                | 🟢 LOW  | (FYI — could expand to Fivetran track in future)                    |

---

# PART 6 — Sources

- [Rapid Agent landing page](https://rapid-agent.devpost.com/) — gallery still unpublished as of 2026-06-03
- [Rapid Agent submissions page](https://rapid-agent.devpost.com/submissions) — "gallery not yet published"
- [Rapid Agent Arize resources](https://rapid-agent.devpost.com/details/arize-resources)
- [Rapid Agent Dynatrace resources](https://rapid-agent.devpost.com/details/dynatrace-resources)
- [Rapid Agent Fivetran resources](https://rapid-agent.devpost.com/details/fivetran-resources)
- [Rapid Agent MongoDB resources](https://rapid-agent.devpost.com/details/mongodb-resources)
- [ADK Hackathon project gallery](https://googlecloudmultiagents.devpost.com/project-gallery)
- [ADK Hackathon awesome-list (15 projects mirrored)](https://github.com/shubhamprajapati7748/google-adk-apps)
- [ADK Hackathon results blog](https://cloud.google.com/blog/products/ai-machine-learning/adk-hackathon-results-winners-and-highlights/)
- [Vertex AI Hackathon updates](https://googlevertexai.devpost.com/updates)
- [AI Accelerate (Elastic+Fivetran)](https://ai-accelerate.devpost.com/)
- [AI in Action (multi-partner Google Cloud)](https://ai-in-action.devpost.com/)
- [GitLab AI Hackathon 2026 winners](https://about.gitlab.com/blog/gitlab-ai-hackathon-2026-meet-the-winners/)
- [Elasticsearch Agent Builder Hackathon](https://elasticsearch.devpost.com/)
- [MongoDB AI Hackathon: Code for a Cause gallery](https://mongodb-ai.devpost.com/project-gallery)
- [Great Agent Hack 2025 gallery](https://hai-great-agent-hack-2025.devpost.com/project-gallery?page=1)
- [Great Agent Hack 2025 Towards Data Science writeup](https://towardsdatascience.com/multi-agent-arena-london-great-agent-hack-2025/)
- [WeaveHacks Devpost](https://weavehacks-1.devpost.com/)
- [Frontline (WeaveHacks observability submission)](https://devpost.com/software/frontline-agent)
- [Product Mate (WeaveHacks self-improving submission)](https://devpost.com/software/product-mate)
- [Splunk Agentic Ops Hackathon](https://splunk.devpost.com/)
- [AWS AI Agent Global Hackathon winners](https://aws-agent-hackathon.devpost.com/updates/38140-congratulations-to-the-winners-of-the-aws-ai-agent-global-hackathon)
- [Microsoft AI Agents Hackathon 2025 winners showcase](https://techcommunity.microsoft.com/blog/azuredevcommunityblog/ai-agents-hackathon-2025-%E2%80%93-category-winners-showcase/4415088)
- [100 Agents Hackathon](https://100agents.devpost.com/)
- [AgentHacks 2025 gallery](https://agenthacks.devpost.com/project-gallery)
- [NVIDIA GTC AI Agents Hackathon gallery](https://ai-agents-hackathon-gtc.devpost.com/project-gallery?page=1)
- [Autonomous Agents Hackathon gallery](https://autonomous-agents-hackathon.devpost.com/project-gallery)
- [RedBot — red-team agent](https://github.com/yli12313/AI-Agents-Hackathon-2025)
- [Self Improving Agents Hack](https://self-improving-agents-hack.devpost.com/)
- [Ruya AI Hackathon 2026](https://ruyaai-hackathon-2026.devpost.com/)
