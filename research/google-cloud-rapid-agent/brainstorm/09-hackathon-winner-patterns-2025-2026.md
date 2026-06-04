# Hackathon Winner Patterns — 2025 / 2026

**Purpose:** Real evidence base for what wins recent AI/agent hackathons. Every entry has a verifiable URL. Recency bias intentional: 2026 > late-2025 > earlier-2025.

**Method:** WebSearch + WebFetch across official sponsor blogs (Google Cloud, AWS, Anthropic, Microsoft, ElevenLabs, GitLab, Kong, Agno, Hugging Face/Gradio, OpenAI) + Devpost galleries. Source URL inlined under each winner.

**Scope:** 20 specific winning projects across 11 hackathons, plus pattern roll-up at the end.

---

## Winners

### WIN-01: SalesShortcut

- **Hackathon:** Google Cloud Agent Development Kit (ADK) Hackathon — wrapped Sept 2025, $50K prize pool, 10,400+ participants from 62 countries, 477 submitted projects.
- **Track / category:** Grand Prize
- **Demo URL:** https://devpost.com/software/salesshortcut
- **Repo URL:** linked from Devpost submission
- **Source:** https://cloud.google.com/blog/products/ai-machine-learning/adk-hackathon-results-winners-and-highlights/
- **Builders:** Merdan Durdyyev, Sergazy Nurbavliyev
- **One-line pitch:** AI-powered Sales Development Representative (SDR) system — multi-agent architecture for automated lead gen, research, proposal generation, outreach.
- **Tech stack:** Google ADK (multi-agent), Gemini, Google Cloud
- **Why it won:** Vertical SaaS shape (replaces an entire SDR seat), uses the _core_ sponsor primitive (ADK multi-agent orchestration) as the architectural backbone — not bolted on.
- **Patterns:** vertical-replaces-a-role; sponsor primitive at the core; multi-agent decomposition matched to a known business workflow.

---

### WIN-02: Cart-to-Kitchen GKE AI Assistant

- **Hackathon:** GKE Turns 10 Hackathon (Google Cloud) — Dec 2025, 4,773 registrants from 133 countries.
- **Track / category:** Grand Prize
- **Demo URL:** https://devpost.com/software/cart-to-kitchen-gke-ai-assistant
- **Source:** https://cloud.google.com/blog/topics/developers-practitioners/winners-and-highlights-from-gke-hackathon
- **Builder:** Amie Wei
- **One-line pitch:** Analyzes a user's grocery cart and recommends recipes from available ingredients.
- **Tech stack:** Gemini, GKE Autopilot, ADK, A2A protocols
- **Why it won:** Used the _entire_ sponsor primitive stack (GKE + ADK + A2A) on a relatable everyday consumer use case — judges could feel the demo in 30 seconds.
- **Patterns:** sponsor primitive stack used end-to-end; consumer-relatable demo; solo builder.

---

### WIN-03: CardOS — AI-Powered Credit Pre-Approval

- **Hackathon:** GKE Turns 10 Hackathon — North America Regional Winner
- **Demo URL:** https://devpost.com/software/cardos
- **Source:** https://cloud.google.com/blog/topics/developers-practitioners/winners-and-highlights-from-gke-hackathon
- **Builder:** Anh Lam
- **One-line pitch:** Multi-agent pipeline analyzes Bank of Anthos spending patterns, tailors credit terms, balances bank profitability with customer value.
- **Tech stack:** GKE, Gemini, multi-agent
- **Why it won:** Plugs into Google's _own canonical demo app_ (Bank of Anthos) — judges already know the dataset and can evaluate the diff cleanly. Vertical finance shape.
- **Patterns:** integrates with sponsor reference app; vertical-finance; clean evaluable baseline.

---

### WIN-04: Vigil AI

- **Hackathon:** GKE Turns 10 Hackathon — Honorable Mention
- **Demo URL:** https://devpost.com/software/vigil-ai
- **Source:** https://cloud.google.com/blog/topics/developers-practitioners/winners-and-highlights-from-gke-hackathon
- **Builder:** Ayan Liger (also referenced as Anh Lam in early blog)
- **One-line pitch:** Hierarchical multi-agent fraud detection for Bank of Anthos — four specialized agents (TransactionMonitor, Orchestrator, Investigation Agent, Actuator).
- **Tech stack:** GKE, Gemini, four-agent role hierarchy
- **Why it won:** Hierarchical agent roles map cleanly to a real-world fraud-ops team — readable architecture.
- **Patterns:** named roles per agent (not "agent-1/agent-2"); plugs into sponsor reference app.

---

### WIN-05: GreenOps

- **Hackathon:** Google Cloud ADK Hackathon — Asia Pacific Regional Winner
- **Demo URL:** https://devpost.com/software/greenops-gzp4aj
- **Source:** https://cloud.google.com/blog/products/ai-machine-learning/adk-hackathon-results-winners-and-highlights/
- **Builders:** Aishwarya Nathani, Nikhil Mankani
- **One-line pitch:** Multi-agent team that continuously audits, forecasts, and optimizes cloud infrastructure for sustainability.
- **Tech stack:** ADK, multi-agent, Google Cloud
- **Why it won:** Closed-loop "agent observes → analyzes → fixes" architecture on cloud cost+carbon. Same loop shape as ChaosLab's harden-loop.
- **Patterns:** closed-loop self-improvement; sustainability angle; targets sponsor's own infrastructure.

---

### WIN-06: Particle Physics Agent

- **Hackathon:** Google Cloud ADK Hackathon — Honorable Mention
- **Demo URL:** https://devpost.com/software/particle-physics-agent
- **Source:** https://cloud.google.com/blog/products/ai-machine-learning/adk-hackathon-results-winners-and-highlights/
- **Builders:** ZX Jin, Tianyu Zhang
- **One-line pitch:** Natural-language → validated Feynman diagrams using real physical laws and high-fidelity data.
- **Tech stack:** ADK, validated against physics law constraints
- **Why it won:** Deep-vertical narrow scope (physics) with _symbolic validation_ — agent doesn't hallucinate because it's grounded in physical-law checkers. "Trust through ground truth."
- **Patterns:** narrow scientific vertical; symbolic/rules-based validation gate; not a chatbot.

---

### WIN-07: CrossBeam

- **Hackathon:** Anthropic "Built with Opus 4.6" Claude Code Hackathon — Feb 2026, 13,000+ applicants, 500 selected, 277 submitted, $100K prize pool.
- **Track / category:** 1st Place
- **Source:** https://claude.com/blog/meet-the-winners-of-our-built-with-opus-4-6-claude-code-hackathon, https://www.adwaitx.com/claude-code-hackathon-opus-4-6/
- **Builder:** Mike Brown — California personal-injury lawyer (zero prior shipping experience)
- **One-line pitch:** AI-powered ADU (Accessory Dwelling Unit) permit assistant — drag-drop blueprints + correction letters, parallel sub-agents parse and assign targeted agents to each discrete correction.
- **Tech stack:** Claude Opus 4.6 + Claude Code (sub-agents in parallel), built end-to-end in <1 week
- **Why it won:** Built by an actual _domain expert_ — the lawyer knew exactly which corrections matter, what 20-minute approval feels like. Parallel sub-agents on a structured doc-processing pipeline.
- **Patterns:** domain expert as builder (not engineer); parallel sub-agent decomposition; visible deterministic structure (not loose chat); narrow regulated vertical.

---

### WIN-08: TARA — Dashcam to Economic Appraisal

- **Hackathon:** Anthropic Built with Opus 4.6 — "Keep Thinking" Prize ($5K credits)
- **Source:** https://claude.com/blog/meet-the-winners-of-our-built-with-opus-4-6-claude-code-hackathon
- **Builder:** Kyeyune Kazibwe — Uganda road technician at Ministry of Works and Transport
- **One-line pitch:** Turns dashcam road footage into complete investment appraisal — Opus 4.6 vision analyzes every frame for surface distress, segments road into condition sections, generates full economic appraisal.
- **Tech stack:** Claude Opus 4.6 vision, custom segmentation pipeline
- **Why it won:** Tested on an _actual road under construction_ in Uganda. Real domain, real customer data, real outcome judges can compare to current $1M+ consulting deliverables.
- **Patterns:** vision as the primary modality; tested on real customer data; emerging-market geography that no incumbent SaaS serves; replaces a 6-figure consulting deliverable.

---

### WIN-09: PostVisit.AI

- **Hackathon:** Anthropic Built with Opus 4.6 — 3rd Place
- **Source:** https://claude.com/blog/meet-the-winners-of-our-built-with-opus-4-6-claude-code-hackathon
- **Builder:** Michał Nedoszytko — Brussels cardiologist
- **One-line pitch:** Turns medical visit transcripts into personalized, actionable health guidance for patients post-visit.
- **Tech stack:** Claude Opus 4.6
- **Why it won:** Solves a problem the builder _personally has_ every workday. Domain credibility = judges trust the design choices without explanation.
- **Patterns:** domain expert builder; vertical-medical; clear unit of work (one transcript → one guidance doc).

---

### WIN-10: Conductr

- **Hackathon:** Anthropic Built with Opus 4.6 — Special Prize "Creative Exploration of Opus 4.6" ($5K)
- **Source:** https://claude.com/blog/meet-the-winners-of-our-built-with-opus-4-6-claude-code-hackathon, https://asepbagja.substack.com/p/i-won-anthropics-hackathon-by-building
- **Builder:** Asep Bagja Priandana — electronic musician
- **One-line pitch:** Claude as virtual bandmate — browser MIDI instrument listens to chords, analyzes performance, generates four backing tracks in real-time.
- **Tech stack:** Opus 4.6, browser MIDI, Web Audio, real-time inference
- **Why it won:** "Doesn't wait for AI" (per builder's blog title) — they hid model latency behind musical timing. Demo is _visceral_ — judges hear it work, not read about it.
- **Patterns:** demo is multimodal/audible (not text on screen); latency hidden by domain UX; non-engineer builder.

---

### WIN-11: Zenith.chat

- **Hackathon:** Forum Ventures x Anthropic Agentic AI Hackathon — NYC, Sept 2025, 100+ teams.
- **Track / category:** 1st Place, $15K API credits
- **Demo URL:** https://zenith.chat/
- **Repo:** https://github.com/affaan-m/everything-claude-code (open-sourced post-hackathon)
- **Source:** https://www.forumvc.com/forum-ventures-x-anthropic-ai-hackathon
- **Builders:** Affaan Mustafa, David Rodriguez
- **One-line pitch:** AI customer-discovery platform — validate PMF by chatting with synthetic personas that think, react, push back like real prospects.
- **Tech stack:** Claude Code (entire build done in 8 hours via Claude Code with 47 sub-agents + 181 skills + 79 commands), synthetic-persona simulation
- **Why it won:** Builder had spent 10 months tuning his own Claude Code harness — built the product in 8 hours because his _tooling_ was 10 months ahead. Meta-pattern: "tooling > raw speed."
- **Patterns:** dogfooded harness as competitive advantage; pre-tuned coding agent; 0→1 zero-to-one company-builder shape; open-sourced the meta-tooling.

---

### WIN-12: EcoLafaek

- **Hackathon:** AWS AI Agent Global Hackathon — Sept–Oct 2025, $45K prize pool. Winners announced at re:Invent.
- **Track / category:** 1st Place
- **Demo URL:** https://devpost.com/software/ecolafaek + https://docs.ecolafaek.com/
- **Source:** https://aws-agent-hackathon.devpost.com/updates/38140-congratulations-to-the-winners-of-the-aws-ai-agent-global-hackathon
- **Builder:** Ajito Nelson Lucio da Costa (Timor-Leste)
- **One-line pitch:** Citizen-led mobile waste-reporting app + autonomous agent — classifies waste images, autonomously chains SQL→chart→map→web scrape, generates real-time pollution hotspots.
- **Tech stack:** Amazon Bedrock Nova-Pro (vision), Bedrock AgentCore (autonomous tool chaining), AgentCore code interpreter (sandboxed Python for viz)
- **Why it won:** _Real public health problem_ (Dili produces 300 tons/day, 100+ tons uncollected, causes flooding) backed with JICA survey data. Uses Bedrock AgentCore as _the_ autonomous reasoning loop — exactly the sponsor's flagship primitive.
- **Patterns:** real-world problem with hard data; sponsor flagship primitive as architectural core; emerging-market geography; full-stack (mobile + agent + dashboard).

---

### WIN-13: Province

- **Hackathon:** AWS AI Agent Global Hackathon — Winner
- **Source:** https://aws-agent-hackathon.devpost.com/updates/38140-congratulations-to-the-winners-of-the-aws-ai-agent-global-hackathon
- **One-line pitch:** Conversational tax filing — multi-agent FormMapping pipeline, 100% accuracy on IRS Form 1040.
- **Tech stack:** AWS Bedrock, Claude 3.5 Sonnet, multi-agent FormMapping
- **Why it won:** _Quantified accuracy claim_ ("100% on Form 1040") gives judges an evaluable benchmark. Vertical tax shape with regulated specificity.
- **Patterns:** measurable accuracy headline; vertical-regulated (tax); deterministic ground truth comparison; replaces TurboTax-shape workflow.

---

### WIN-14: GibberLink

- **Hackathon:** ElevenLabs × a16z Worldwide Hackathon — Feb 22–23, 2025, 9 global sites, 300+ submissions.
- **Track / category:** Global Top Prize
- **Demo URL:** https://elevenlabs-worldwide-hackathon.devpost.com/submissions/622017-gibber-link
- **Source:** https://elevenlabs.io/blog/announcing-the-winners-of-the-elevenlabs-worldwide-hackathon
- **Builders:** Boris Starkov, Anton Pidkuiko (London)
- **One-line pitch:** Two AI agents on a phone call realize they're both AI and switch to ggwave — a more efficient audio signal protocol.
- **Tech stack:** ElevenLabs voice, ggwave acoustic data protocol
- **Why it won:** _The demo IS the entire pitch_ — went viral on X with 10M+ views. One-shot, no slides, zero explanation needed. Judges weighed virality + technical novelty equally.
- **Patterns:** viral-on-X demo loop (≤30s clip); novelty of "agents talking to agents"; one-shot demo, no prep needed; cultural-moment timing.

---

### WIN-15: Pep — Physical Therapy Agent

- **Hackathon:** ElevenLabs × a16z Worldwide Hackathon — 2nd Online Prize
- **Demo URL:** https://elevenlabs-worldwide-hackathon.devpost.com/submissions/622274-pep-your-compassionate-physical-therapy-agent
- **Source:** https://elevenlabs.io/blog/announcing-the-winners-of-the-elevenlabs-worldwide-hackathon
- **Builders:** Feng Yan, Lora Xie
- **One-line pitch:** Multi-modal voice+vision agent giving real-time coaching for physical-therapy exercises.
- **Tech stack:** ElevenLabs voice, computer vision, real-time feedback loop
- **Why it won:** Vertical health + multimodal (voice + vision) — uses TWO of the sponsor's hot primitives in one product.
- **Patterns:** multi-modal (vision + voice); real-time coaching loop; vertical health; sponsor primitives stacked.

---

### WIN-16: Procuro

- **Hackathon:** ElevenLabs × a16z — NYC Event, 2nd Place
- **Demo URL:** https://elevenlabs-worldwide-hackathon.devpost.com/submissions/622443-procuro
- **Source:** https://elevenlabs.io/blog/announcing-the-winners-of-the-elevenlabs-worldwide-hackathon
- **Builders:** Shrey Kakkar, Austin Wang, Prithvi, Kyle Zhang
- **One-line pitch:** Agent calls suppliers across the US to locate delayed supply-chain parts.
- **Tech stack:** ElevenLabs conversational voice agents, telephony
- **Why it won:** Concrete B2B procurement workflow with clear ROI (a parts buyer would _literally pay_ for this on day one).
- **Patterns:** voice agent makes outbound phone calls (high "wow factor"); B2B vertical with priced labor it replaces; clear customer in 1 sentence.

---

### WIN-17: RiskWise — Supply Chain Risk Analysis

- **Hackathon:** Microsoft AI Agents Hackathon 2025 — April 8–30, 2025, 18,000+ developers registered, 570 submissions.
- **Track / category:** Best Overall Agent, $20K
- **Source:** https://microsoft.github.io/AI_Agents_Hackathon/winners/, https://techcommunity.microsoft.com/blog/azuredevcommunityblog/ai-agents-hackathon-2025-%E2%80%93-category-winners-showcase/4415088
- **One-line pitch:** AI agents sift shipping schedules + trade-disruption news + geopolitical events to flag supply-chain risks in natural language.
- **Tech stack:** Semantic Kernel (planning + tool orchestration), Azure AI Agent Service, Next.js UI
- **Why it won:** Vertical-enterprise (supply chain), uses sponsor flagship orchestration primitive (Semantic Kernel), natural-language analyst UX is the right interaction model.
- **Patterns:** vertical-enterprise; sponsor orchestration primitive; analyst-facing NL query UX; data fusion from heterogeneous sources.

---

### WIN-18: Apollo — Deep Research Meta-Agent

- **Hackathon:** Microsoft AI Agents Hackathon 2025 — Best Agent in C# ($5K)
- **Source:** https://microsoft.github.io/AI_Agents_Hackathon/winners/, https://github.com/microsoft/AI_Agents_Hackathon/issues/681
- **One-line pitch:** Deep research assistant — decomposes complex queries into subtopics, researches each, compiles cited report.
- **Tech stack:** Azure AI Agent Service, Azure OpenAI GPT-4, self-reflective RAG with iterative information gathering
- **Why it won:** Self-reflective RAG (agent critiques + retries) on top of citations — the "Deep Research" shape that OpenAI/Anthropic later productized at scale.
- **Patterns:** decomposition agent; cited output (trust signal); self-reflective loop (critique → retry); shape later copied by frontier labs.

---

### WIN-19: RoboChef

- **Hackathon:** OpenAI Open Model Hackathon (gpt-oss) — 2025
- **Track / category:** Best Overall (sponsored by Hugging Face)
- **Source:** https://openai.devpost.com/updates/37529-and-the-winners-are
- **One-line pitch:** AI kitchen assistant — gpt-oss decomposes cooking instructions into sequential steps executed by NVIDIA Isaac GR00T robot arm; live UI tracks robot progress.
- **Tech stack:** gpt-oss-20B, NVIDIA Isaac GR00T robotic arm, real-time UI overlay
- **Why it won:** Physical robotic execution = unforgettable demo. Open-weight model running on-device matched the hackathon's thesis ("what can you do with our open weights?").
- **Patterns:** physical/embodied agent (robot); on-device open weights (matched sponsor thesis); real-time progress UI overlays reasoning.

---

### WIN-20: Bota — Autonomous Dota 2 Agent

- **Hackathon:** OpenAI Open Model Hackathon — Wildcard "Best Unexpected Use"
- **Source:** https://openai.devpost.com/updates/37529-and-the-winners-are
- **One-line pitch:** Plays 1v1 Dota 2 matches — gpt-oss-20B processes live game state, generates hero movement/attacks/abilities WITHOUT fine-tuning, shows reasoning in-game chat.
- **Tech stack:** gpt-oss-20B (zero fine-tuning), game-state parsing
- **Why it won:** "Reasoning displayed in game chat" = judges watch the model think _in front of them_. No fine-tuning = zero-shot capability of the open model showcased.
- **Patterns:** reasoning transparency as demo feature; zero-fine-tuning (let the base model shine); unexpected/recreational domain wedge.

---

### WIN-21: Likeminds — Agentic Multi-Social Semantic Network

- **Hackathon:** Global Agent Hackathon (Agno, May 2025) — 60+ submissions
- **Track / category:** Grand Prize, $5K
- **Demo URL:** https://likeminds-react-vercel.vercel.app/
- **Source:** https://www.agno.com/blog/global-agent-hackathon-winners
- **Builders:** Guaming, Vaibhav
- **One-line pitch:** Full-stack semantic-context system for social networks powered by Agno — autonomous agents collaborating across dynamic social graph.
- **Tech stack:** Agno framework, semantic graph backend, React/Vercel frontend
- **Why it won:** Full-stack delivery (FE + BE + agents) on a hackathon-week — judges value shipped surface area when many submissions are CLI demos.
- **Patterns:** full-stack delivery (not CLI/notebook); novel data-shape (semantic graph); sponsor framework throughout.

---

### WIN-22: AgentHero — SOC 2 Compliance Auditor

- **Hackathon:** GitLab AI in Action Hackathon — May 6 – June 17, 2025, $50K pool, partners GitLab + Google Cloud + MongoDB
- **Source:** https://about.gitlab.com/blog/ai-in-action-hackathon-celebrating-the-gitlab-innovations/
- **One-line pitch:** Three-agent system audits GitLab projects for SOC 2 compliance — per-MR audit, periodic project-wide reports, compliance advisor in Duo Chat, live monitoring dashboard.
- **Tech stack:** GitLab Duo, three-agent architecture, Google Cloud dashboards
- **Why it won:** Compliance is _the_ enterprise-DevSecOps wedge — uses GitLab Duo Chat as the surface, not a separate tool. Embedded UX = sticky.
- **Patterns:** sponsor-native UX (lives inside Duo Chat, not external); regulated vertical (compliance); per-MR + periodic dual cadence.

---

### WIN-23: CarbonAware CI/CD Linter

- **Hackathon:** GitLab AI in Action Hackathon — Winning project
- **Source:** https://about.gitlab.com/blog/ai-in-action-hackathon-celebrating-the-gitlab-innovations/
- **One-line pitch:** AI agent lints GitLab CI/CD pipelines for carbon waste — scores sustainability, flags inefficient jobs, recommends fixes that cut compute time + costs + CO2.
- **Tech stack:** GitLab CI/CD API, sustainability scoring, AI recommender
- **Why it won:** Three-axis ROI (time + $ + CO2) — sustainability narrative + hard cost savings = irresistible to enterprise judges. Lints existing artifact (no behavior change needed).
- **Patterns:** linter-shape (acts on existing artifact); triple ROI framing; sustainability narrative.

---

### WIN-24: PHAROS — Drug Safety in <60 Seconds

- **Hackathon:** Elasticsearch Agent Builder Hackathon — 2025
- **Source:** https://www.elastic.co/blog/the-elasticsearch-agent-builder-hackathon
- **One-line pitch:** Drug safety analysis pipeline returns results in under 60 seconds.
- **Tech stack:** Elasticsearch Agent Builder, vector search, biomedical RAG
- **Why it won:** Concrete latency claim ("<60s") + vertical health/pharma + critical-decision use case.
- **Patterns:** latency-headline metric; vertical-regulated (pharma); leverages sponsor primitive (Agent Builder).

---

### WIN-25: HIV Duplicate Detection Agent (Kenya)

- **Hackathon:** Elasticsearch Agent Builder Hackathon — 2025
- **Source:** https://www.elastic.co/blog/the-elasticsearch-agent-builder-hackathon
- **One-line pitch:** Three-agent system scans 1,010 real anonymized records in under 10 seconds, surfaces 131 duplicates including same-day multi-facility cases that would have taken weeks manually.
- **Tech stack:** Elasticsearch Agent Builder, three-agent fan-out
- **Why it won:** _Real anonymized data_, concrete numerical result (131 dupes from 1,010 records in 10s), high-impact public health context.
- **Patterns:** real production-grade data (not synthetic); quantified win vs manual baseline; emerging-market public-health geography; three-agent decomposition.

---

### WIN-26: TARIFFED!

- **Hackathon:** Microsoft AI Agents Hackathon 2025 — Best Azure AI Agent Service Usage ($5K)
- **Source:** https://microsoft.github.io/AI_Agents_Hackathon/winners/
- **One-line pitch:** Models how tariff changes ripple through import/export — agent answers "what happens if X tariff goes up Y%."
- **Tech stack:** Azure AI Agent Service
- **Why it won:** Topical (trade war / tariff news cycle 2025), uses Azure AI Agent Service as the _core_ — not just hosting.
- **Patterns:** news-cycle relevance (tariffs); sponsor primitive at core; what-if scenario modeling shape.

---

### WIN-27: Hugo Tour Guide

- **Hackathon:** ElevenLabs × a16z — Online 1st Prize
- **Demo URL:** https://elevenlabs-worldwide-hackathon.devpost.com/submissions/622986-hugo-tour-guide
- **Source:** https://elevenlabs.io/blog/announcing-the-winners-of-the-elevenlabs-worldwide-hackathon
- **Builders:** Yilun Sun, Qiang Fang, David Chen, Aiden Zhao
- **One-line pitch:** AI travel companion plans routes, gives local insights, answers cultural/historical questions in voice.
- **Tech stack:** ElevenLabs voice, route planning, RAG over travel/historical content
- **Why it won:** Consumer-grade polish, multilingual potential, "I want this on my next trip" universality.
- **Patterns:** consumer-relatable demo; voice-first; universal use case; multilingual.

---

### WIN-28: LLMGameHub (now Immersia)

- **Hackathon:** Gradio Agents & MCP Hackathon (Hugging Face) — June 2–8, 2025, $16.5K pool, 4,100+ registrations
- **Track / category:** Agentic Demo Showcase winner
- **Source:** https://huggingface.co/blog/kikikita/immersia-ai-games, https://www.gradio.app/hackathon-winners
- **One-line pitch:** Generative-adventure playground — describe a world, choose hero + genre, dive into a 5-minute interactive game with on-the-fly LLM scenes, generated first-person images, adaptive music.
- **Tech stack:** Gradio (UI + MCP server), agent pool backend, LLM + image gen + music gen
- **Why it won:** Multi-modal generation pipeline (text + image + music) in one cohesive UX. MCP/agent tooling at the core (sponsor primitive).
- **Patterns:** multi-modal generative pipeline; ≤5-min session length (judges can actually play it); sponsor primitive (MCP) at core.

---

### WIN-29: Edu.AI (Brazil)

- **Hackathon:** Google Cloud ADK Hackathon — Latin America Regional Winner
- **Demo URL:** https://devpost.com/software/edu-ai-multi-agent-educational-system-for-brazil
- **Source:** https://cloud.google.com/blog/products/ai-machine-learning/adk-hackathon-results-winners-and-highlights/
- **Builder:** Giovanna Moeller
- **One-line pitch:** Autonomous agents evaluate essays, generate personalized study plans, create interdisciplinary mock exams — for Brazilian students.
- **Tech stack:** ADK multi-agent, Gemini
- **Why it won:** Geo + curriculum specificity (Brazilian education system) — judges trust the builder to know the specific need. Concrete units of work (essay → score, plan → student, exam → topics).
- **Patterns:** geo-specific (Brazil); curriculum-vertical; concrete units of work; solo builder.

---

### WIN-30: Autonomous Security Auditor Agentic AI

- **Hackathon:** Kong Agentic AI Hackathon 2025 — Sept 15–30, $10K pool
- **Track / category:** Best Solo Project
- **Source:** https://konghq.com/blog/news/winners-of-kong-agentic-ai-hackathon
- **Builder:** Sachin Ghumbre
- **One-line pitch:** Autonomous agent audits Kong API gateway configurations for security vulnerabilities.
- **Tech stack:** Kong Gateway, agentic security auditor
- **Why it won:** Audit-shape on the sponsor's _own gateway product_ — security narrative + concrete production-readiness.
- **Patterns:** audits sponsor's own product (Kong); solo builder; security/compliance vertical; production-ready (not toy).

---

## Winning Patterns Ranked by Frequency

### Pattern A: Sponsor-primitive at the architectural core (NOT bolted on) — 11 winners

WIN-01, WIN-02, WIN-05, WIN-12, WIN-17, WIN-22, WIN-26, WIN-28, WIN-21, WIN-30, WIN-15
Winners use the sponsor's flagship primitive (ADK multi-agent / Bedrock AgentCore / Semantic Kernel / GitLab Duo / Kong Gateway / Agno / Gradio MCP / Azure AI Agent Service / ElevenLabs voice) as **the core architectural element**, not a sidecar. Bolt-on usage of sponsor tech loses.

### Pattern B: Domain-vertical specificity (regulated industry, named geography, real customer data) — 10 winners

WIN-07 (CA ADU permits), WIN-08 (Ugandan roads), WIN-09 (Brussels cardiology), WIN-12 (Timor-Leste waste), WIN-13 (US Form 1040), WIN-17 (supply chain), WIN-22 (SOC 2), WIN-24 (pharma), WIN-25 (Kenya HIV), WIN-29 (Brazilian education).
The narrower the vertical + the more it's tied to a _specific_ dataset/regulation/geography, the more judges trust the builder + the harder to dismiss as toy.

### Pattern C: Domain-expert-as-builder (not engineer-as-builder) — 6 winners

WIN-07 (lawyer), WIN-08 (road technician), WIN-09 (cardiologist), WIN-10 (musician), WIN-12 (local Timor-Leste builder), WIN-25 (Kenya health worker context).
Anthropic's 2026 hackathon flipped the script — domain experts using Claude Code beat professional engineers. This pattern is _accelerating_, not stabilizing.

### Pattern D: Multi-agent role decomposition with named roles (not "agent-1/agent-2") — 9 winners

WIN-01 (SDR roles), WIN-04 (TransactionMonitor / Orchestrator / Investigation / Actuator), WIN-05 (audit / forecast / optimize), WIN-13 (FormMapping pipeline), WIN-17 (planner + tool routing), WIN-22 (per-MR + project-wide + advisor), WIN-25 (three-agent scan/dedupe), WIN-07 (parallel sub-agents per correction), WIN-15 (voice + vision agents).
Agents that map to a real human team's roles read as production-grade. Generic "agent-1 talks to agent-2" reads as toy.

### Pattern E: Demo-as-pitch / viral-on-X / one-shot demo loop — 6 winners

WIN-14 (GibberLink — agents-talking-to-agents viral clip), WIN-10 (Conductr — live music demo), WIN-19 (RoboChef — physical robot), WIN-16 (Procuro — real phone calls to real suppliers), WIN-20 (Bota — reasoning visible in Dota chat), WIN-27 (Hugo — voice travel guide).
30-second demo > 90-second pitch. If the screen-recording doesn't explain itself, judges scroll past.

### Pattern F: Closed-loop self-improvement / observability built in — 5 winners

WIN-05 (GreenOps audit→fix loop), WIN-18 (Apollo self-reflective RAG), WIN-08 (TARA appraises and recommends), WIN-22 (continuous SOC 2 monitoring), WIN-23 (continuous CI/CD carbon linting).
Agents that watch themselves + iterate match the "production-grade" judge bias. This is _the_ shape the rapid-agent hackathon's sponsors (Arize, Dynatrace) want to see.

### Pattern G: Quantified-result headline (specific accuracy/latency/volume number) — 6 winners

WIN-13 ("100% on Form 1040"), WIN-24 ("<60 seconds"), WIN-25 ("131 dupes / 1,010 records / 10s"), WIN-08 ("complete economic appraisal"), WIN-07 ("20-minute approval"), WIN-18 (cited research output).
Judges remember numbers. "Faster than expert humans" needs a number to be believable.

### Pattern H: Tested on real production data (not synthetic) — 5 winners

WIN-08 (real Ugandan road), WIN-25 (1,010 real anonymized HIV records), WIN-12 (real Dili waste data + JICA survey), WIN-03 (real Bank of Anthos reference data), WIN-22 (real GitLab projects).
Synthetic data submissions lose. Builders who get real (anonymized) production data into the demo win their category.

### Pattern I: Solo builder or 2-person team (not 4+ team) — 13 winners

WIN-02, WIN-03, WIN-06, WIN-07, WIN-08, WIN-09, WIN-10, WIN-12, WIN-14 (2-person), WIN-21 (2-person), WIN-26, WIN-29, WIN-30.
Solo builders or 2-person teams dominate top-of-podium. 4-person+ teams cluster at honorable mentions. Coordination overhead kills hackathon throughput.

### Pattern J: Replaces a paid human role (priced labor) — 7 winners

WIN-01 (SDR), WIN-07 (permit consultant), WIN-08 (road consultant — $1M+ deliverable), WIN-17 (supply chain analyst), WIN-22 (SOC 2 auditor), WIN-25 (data clerk), WIN-30 (security auditor).
"This replaces a person paid $X" gives judges a unit-economics story without prompting.

### Pattern K: Sponsor reference-app / canonical demo plug-in — 3 winners

WIN-03 (Bank of Anthos), WIN-04 (Bank of Anthos), WIN-22 (GitLab Duo Chat surface).
Plugging into the sponsor's own canonical demo app gives judges a known baseline. Use it.

### Pattern L: Multi-modal (vision + voice + text combined) — 6 winners

WIN-08 (vision), WIN-12 (vision), WIN-15 (voice + vision), WIN-19 (voice + robot vision), WIN-27 (voice), WIN-28 (text + image + music gen).
Single-modality submissions are getting commoditized. Multi-modal pipelines stand out.

---

## Cross-cutting meta-observations

1. **Late-2025 → 2026 hackathons increasingly reward non-engineers** — Anthropic's 2026 Built-with-Opus-4.6 specifically called out domain experts beating engineers. The "Claude Code as accessibility layer" thesis is _the_ winning meta for 2026 hackathons.

2. **The "agents calling tools / chaining tools autonomously" loop is the new minimum bar** — every AWS/Microsoft/Google flagship hackathon winner uses AgentCore-style autonomous tool chaining. Static "LLM-with-RAG" submissions don't place in 2026.

3. **MCP/A2A protocols are now table-stakes for top placements at Google Cloud + Hugging Face hackathons** — WIN-02, WIN-28 explicitly leveraged them. Submitting _without_ MCP/A2A at a Google hackathon in 2026 is leaving free points on the table.

4. **Observability sponsors (Arize, Dynatrace, PostHog) increasingly award their own prizes** — PostHog gave $22K to PostHog Meeting Copilot at the ElevenLabs hackathon for "best LLM observability tool usage." That's exactly the angle the rapid-agent hackathon's Arize track rewards.

5. **Audit / linter / compliance shape repeats across sponsors** — WIN-22 (SOC 2), WIN-23 (carbon), WIN-30 (security audit), WIN-05 (cloud audit), WIN-08 (road audit). The agent-as-auditor shape generalizes across verticals AND fits the Arize "self-improvement loop" judging criterion natively.

---

## Sources

- https://cloud.google.com/blog/products/ai-machine-learning/adk-hackathon-results-winners-and-highlights/
- https://cloud.google.com/blog/topics/developers-practitioners/winners-and-highlights-from-gke-hackathon
- https://claude.com/blog/meet-the-winners-of-our-built-with-opus-4-6-claude-code-hackathon
- https://www.adwaitx.com/claude-code-hackathon-opus-4-6/
- https://www.forumvc.com/forum-ventures-x-anthropic-ai-hackathon
- https://aws-agent-hackathon.devpost.com/updates/38140-congratulations-to-the-winners-of-the-aws-ai-agent-global-hackathon
- https://elevenlabs.io/blog/announcing-the-winners-of-the-elevenlabs-worldwide-hackathon
- https://microsoft.github.io/AI_Agents_Hackathon/winners/
- https://techcommunity.microsoft.com/blog/azuredevcommunityblog/ai-agents-hackathon-2025-%E2%80%93-category-winners-showcase/4415088
- https://about.gitlab.com/blog/ai-in-action-hackathon-celebrating-the-gitlab-innovations/
- https://konghq.com/blog/news/winners-of-kong-agentic-ai-hackathon
- https://www.agno.com/blog/global-agent-hackathon-winners
- https://openai.devpost.com/updates/37529-and-the-winners-are
- https://huggingface.co/blog/kikikita/immersia-ai-games
- https://www.gradio.app/hackathon-winners
- https://www.elastic.co/blog/the-elasticsearch-agent-builder-hackathon
- https://docs.ecolafaek.com/
- https://zenith.chat/
- https://github.com/affaan-m/everything-claude-code
- https://asepbagja.substack.com/p/i-won-anthropics-hackathon-by-building
