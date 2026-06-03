# 03 — Agent Landscape Scan (Mid-2026)

> Maps the deployed AI agent landscape as of 2026-06-02 so that the wedge-ideation step for the Google Cloud Rapid Agent Hackathon (rapid-agent.devpost.com, deadline 2026-06-11) lands on a gap, not on something that already exists.
>
> Feeds into `07-pre-commit-checklist.md` Q2 (the wedge sentence) and downstream `sahil-idea-generator`.

---

## Methodology

**Sources used** (in priority order):

1. WebSearch — 12 targeted queries covering horizontal agents, vertical SaaS agents, frameworks, hackathon winners, UX patterns, and underserved niches. Results from June 2026 only.
2. Cross-referenced market analyses (Lindy, Vellum, Carly, StackOne, SignalFire blog) which aggregate competitive landscapes.
3. Official press / blog posts where available (Reflection AI / Sequoia, Manus blog, Google Developers Blog, Anthropic news).
4. Devpost hackathon project galleries (ADK 2025, GKE 2025, AI in Action 2025, AgentHacks).
5. Existing `CONTEXT.md` for hackathon constraints.

**Source quality** — mixed. Tier-1 (official launches, named founders, dated $-figures) marked inline. Tier-2 (aggregator blogs with corroborating quotes) used for shape signal but specific claims marked [UNVERIFIED] where the underlying primary source is missing. Tier-3 (SEO content farms) treated as weak signal only.

**Scope cut** — did not deep-dive on every product listed; focus is on (a) what each product DOES at the level needed to identify gaps, (b) UX shape, and (c) what it doesn't attempt. Goal is gap analysis, not competitor matrix.

**Bias disclosure** — landscape inevitably overrepresents English-language US/EU products. Asia / LATAM vertical-agent ecosystems (e.g., the Brazilian Edu.AI ADK hackathon winner) likely larger than search results surface.

---

## Section 1: Horizontal consumer-grade agents

The "general-purpose agent that does everything" category. Heavily contested. Mostly browser- or desktop-takeover shaped.

### 1. OpenAI Operator → ChatGPT Agent / Computer-Using Agent
- **Maker:** OpenAI
- **What it does:** Browser-driving agent. Watches DOM screenshots, reasons, controls mouse/keyboard. Now folded into ChatGPT Agent product. ([OpenAI](https://openai.com/index/introducing-operator/), [DualMedia](https://www.dualmedia.fr/en/ai-browsers-2026/))
- **Status:** Operator-as-product was sunset Aug 31, 2025 (failed reliably on CAPTCHA / JS-heavy flows); capabilities live on inside ChatGPT Agent. ([Helicone](https://www.helicone.ai/blog/browser-use-vs-computer-use-vs-operator))
- **Notable techniques:** Vision + mouse-tool loop, takeover mode for credential entry, "watch me work" UX.
- **Gap:** No persistent memory of past sessions surfaced to the user as first-class. No domain priors (treats every site as new). No multi-tenancy / team workspaces.

### 2. Anthropic Claude Computer Use / Claude Cowork / Claude Code
- **Maker:** Anthropic
- **What it does:** API-level computer-use tool (screenshots + mouse/keyboard primitives), packaged into Claude Cowork (paid product, March 2026) and Claude Code (terminal coding agent). ([Anthropic](https://www.anthropic.com/news/3-5-models-and-computer-use), [CNBC](https://www.cnbc.com/2026/03/24/anthropic-claude-ai-agent-use-computer-finish-tasks.html))
- **Notable:** Loop command for cron-style runs; voice mode in 20 languages; phone-remote control of desktop agents.
- **Gap:** Still primarily a single-machine, single-user experience. Doesn't natively handle multi-account / impersonation workflows enterprises need.

### 3. Google AntiGravity
- **Maker:** Google (launched Nov 18, 2025 alongside Gemini 3, version 2.0 at I/O 2026)
- **What it does:** Agent-first IDE built on VS Code. Manager View lets developer dispatch 5+ agents in parallel on different tickets. Combines editor + terminal + browser surface. ([Google Developers Blog](https://developers.googleblog.com/build-with-google-antigravity-our-new-agentic-development-platform/), [Wikipedia](https://en.wikipedia.org/wiki/Google_Antigravity))
- **Notable:** Multi-model (Claude Sonnet 4.6, Opus 4.6, OSS GPT variants alongside Gemini); native parallel-agent fan-out UX.
- **Gap:** Coder-only. Doesn't generalize to non-engineering knowledge workers.

### 4. Manus AI
- **Maker:** Butterfly Effect (Monica AI team), acquired by Meta Q4 2025 for ~$2B but still operates standalone. ([Lindy](https://www.lindy.ai/blog/manus-ai-alternatives))
- **What it does:** Multi-agent general-purpose agent with sub-agents for browsing/data/code/writing. Sandbox = isolated cloud VM per task. Browser Operator chrome extension (Nov 2025, GA'd at scale) takes over the user's local browser session. ([Manus blog](https://manus.im/blog/manus-browser-operator), [E2B blog](https://e2b.dev/blog/how-manus-uses-e2b-to-provide-agents-with-virtual-computers))
- **Notable:** Uses E2B Firecracker microVMs; "Agent Skills" feature for user-defined custom workflows; persistent VM file system.
- **Gap:** Demo-impressive but reliability still weak on long-horizon tasks. No domain specialization — competes on general-purpose breadth.

### 5. Lindy.ai
- **Maker:** Lindy (Flo Crivello)
- **What it does:** No-code agent builder for SMBs. 5,000+ integrations. Triggers + actions. Deep on inbox triage, voice calls, scheduling, lead qualification. ([Lindy](https://www.lindy.ai/blog/best-ai-agents))
- **Notable UX:** "Delegate to AI" inbox pattern — Lindy lives in the user's Gmail / Slack like a coworker.
- **Gap:** Limited deep-reasoning. Strong for workflow automation; weak for one-shot research / artifact-production.

### 6. Reflection AI / Asimov
- **Maker:** Reflection AI (Sequoia-backed, ex-Google DeepMind founders, $2B Series B late 2025) ([Sequoia](https://sequoiacap.com/article/reflection-ai-asimov/), [Pulse2](https://pulse2.com/reflection-ai-secures-2-billion-series-b-for-building-autonomous-coding-agents-and-frontier-models/))
- **What it does:** Code-comprehension agent. Ingests not just code but Slack, email, Jira, GitHub threads. Persistent "Asimov Memories" let the team teach it. Many small retrievers + one short-context combiner.
- **Notable:** Beat Cursor Ask and Claude Code on blind OSS-maintainer eval. VPC-deployed (privacy-first).
- **Gap:** Read-only by design. Doesn't WRITE code or take action. Pure comprehension layer.

### 7. HyperWrite Personal Assistant
- **Maker:** OthersideAI — older entry, still operating but lost mindshare. [UNVERIFIED] current status; not surfaced prominently in 2026 round-ups.
- **Gap:** Outflanked by Lindy on no-code, by Operator/Manus on browser takeover.

### 8. MultiOn
- **Maker:** MultiOn — web-action agent. [UNVERIFIED] active product status as of June 2026 — not appearing in major comparison articles surveyed; possibly absorbed or sunset.

### 9. Adept
- **Maker:** Adept Labs. **DEFUNCT** — talent + tech acquired by Amazon mid-2024. No standalone product. Confirmed by absence from every 2026 comparison.

### 10. ChatGPT (Atlas / agentic browsing surfaces)
- **Maker:** OpenAI
- **What it does:** ChatGPT now ships a Computer mode and agentic browsing inside the consumer product (announced/expanded throughout 2026). Spaces-style team workspaces. ([Releasebot](https://releasebot.io/updates/perplexity-ai))
- **Gap:** Closed ecosystem — can't custom-wire MCP servers from arbitrary partners (well, post-MCP-adoption announcement, can, but UX still locked).

### 11. Perplexity (Spaces + Comet browser)
- **Maker:** Perplexity AI
- **What it does:** Research-focused agent with Spaces (team research workspaces), inline diffs, plan approvals, Snowflake/Databricks workflows, GPT-5.5 default orchestration. ([Releasebot](https://releasebot.io/updates/perplexity-ai))
- **Gap:** Strong on read-only research, weak on writing/action — pages are research outputs, not workflow executions.

**Saturation verdict:** Horizontal general-purpose agents are SATURATED. Any hackathon entry framed as "general agent that does X, Y, and Z" loses to incumbents on capability breadth and to vertical agents on depth. Avoid.

---

## Section 2: Vertical agent products

The hot market. 2026 = "vertical AI eats SaaS" (consensus across SignalFire, ScrumLaunch, Lindy, ACTGSYS coverage).

### Coding agents — SATURATED-HOT

| Product | Maker | Shape | Gap |
|---|---|---|---|
| **Cursor** | Anysphere | Local-first IDE, pair-programmer mode | Limited team coordination |
| **Devin** | Cognition Labs | Fully autonomous PR-to-merge, "junior eng" framing walked back; Devin 3.0 ships re-planning | Reliability still inconsistent on real production code |
| **Codeium Windsurf** | Codeium | IDE with Cascade agent, auto-lint-fix, terminal exec | Smaller integration surface than Cursor |
| **Replit Agent (Agent 4)** | Replit | Browser cloud IDE + agent; March 2026 release; full-stack from prompt | Hits ceilings on complex business logic |
| **Bolt.new** | StackBlitz | Fastest prompt-to-preview; JS-only | Frontend-rich, weak backend |
| **Lovable** | Lovable Labs | Most-polished end-to-end app gen with auth + DB | TypeScript-bound; design opinionated |
| **Claude Code** | Anthropic | Terminal-first agentic coder | UX limited to CLI users |
| **Google AntiGravity** | Google | Multi-agent IDE with Manager View | Coder-only |
| **Asimov** | Reflection AI | Read-only comprehension over code+docs+chat | Doesn't write |

Sources: [Vellum](https://www.vellum.ai/blog/best-ai-coding-agents), [Builder.io](https://www.builder.io/blog/devin-vs-cursor), [Blink](https://blink.new/blog/best-ai-coding-agents-2026).

**Saturation verdict:** Coding agents = no room. Skip unless you find a sliver (e.g., "agent that fixes flaky tests in legacy Rails apps via tracing-driven reproduction"). Watch for: niche language ecosystems (Elixir, Clojure, OCaml) still underserved.

### Sales / SDR / CRM agents — HOT, BUT INCUMBENT-DOMINATED

- **Clay + Claygent** ([Clay](https://www.clay.com/)) — research agent over 75+ data sources, ran 1B+ tasks by 2025. MCP-connected.
- **Apollo.io** — added agentic outbound 2025-2026.
- **Outreach AI** — sequence orchestration with agentic optimization.
- **SalesShortcut** (ADK Hackathon Latin America regional winner) — multi-agent SDR built end-to-end on ADK. Validates that "SDR agent" is a winning hackathon shape but also that it's been done.
- **Avoca** (voice AI for trades — HVAC/plumbing) — $125M funding April 2026, $1B in bookings on-track for 2026 alone. ([Avoca via 8seneca](https://www.8seneca.com/en/blog/technology/vertical-ai-agents-enterprise-2026))

**Gap:** Vertical SDR for non-tech industries with no CRM (trades, healthcare clinics, professional services). Inbound-call-first is more underserved than outbound-cold-email-first.

### Customer support / CX agents — DOMINATED BY THE BIG 3

- **Sierra** (Bret Taylor, Clay Bavor) — $15.8B valuation May 2026 after $950M Series C. Brand-aware custom agents. SiriusXM, WeightWatchers, Sonos as customers. ([Retell](https://www.retellai.com/blog/sierra-vs-decagon), [eesel](https://www.eesel.ai/blog/decagon-vs-sierra))
- **Decagon** — $4.5B valuation Jan 2026. ([Contrary Research](https://research.contrary.com/company/decagon))
- **Maven AGI** — enterprise integration wedge (Salesforce, Zendesk, HubSpot custom). Willing to be measured on resolution rate. ([Maven AGI](https://www.mavenagi.com/))
- **Fin (Intercom)** — incumbent. ([Fin](https://fin.ai/learn/ai-customer-service-agents-compared))
- **Forethought, Cognigy** — older entrants.

**Gap:** SMB-tier support agents that DON'T require Salesforce/Zendesk. Most existing players assume enterprise tooling.

### Healthcare agents — TURBO-HOT

- **Hippocratic AI** — $1.6B in 2025. Non-diagnostic conversational agents (pre-op education, med reminders). 25+ health system partners. NVIDIA partnership.
- **Abridge** — clinical documentation. Microsoft partnership noise.
- **Ambience Healthcare** — $243M Series C 2025. Operates-on / ambient-scribing.
- **Paratus Health** — outpatient clinic front-desk agent. Epic + Athena integration. ([ACTGSYS](https://actgsys.com/en/blog/vertical-ai-agents-industry-specific-2026))
- **OpenEvidence** — clinical evidence Q&A agent.

**Gap:** Mid-size practices (dental, optometry, mental-health independent practitioners) without Epic. Prior-auth automation is still mostly humans. Caregiver-facing (not clinician-facing) agents underserved.

### Legal agents — INCUMBENT WAR

- **Harvey** — $8B valuation (a16z $150M round). Just launched Legal Agent Benchmark with NVIDIA/OpenAI/Anthropic/Mistral/DeepMind. ([Artificial Lawyer](https://www.artificiallawyer.com/2026/05/06/harvey-launches-legal-agent-bench/))
- **Spellbook** — contract drafting.
- **EvenUp** — personal injury law specialist.
- **CaseText (Thomson Reuters)** — incumbent.

**Gap:** Small law firms / solo practitioners without Westlaw/Lexis seats. Compliance for niche regulatory domains (HIPAA audit, GDPR DPIA, SOC2 prep) is still mostly humans.

### Finance / wealth / accounting — UNDER-COVERED

- **Domo, Sapient, RegoX** — [UNVERIFIED] specific 2026 status; not surfaced in major aggregator coverage.
- **TradeSage AI** — ADK Hackathon GRAND PRIZE WINNER, multi-agent trading hypothesis evaluation. Confirms judges reward this domain.

**Gap:** Bookkeeping for solo founders / micro-SaaS / creators. Crypto-tax for retail. Treasury agents for non-VC startups. Accounting close (month-end) automation for tiny shops.

### HR / recruiting — MEDIUM

- **HireVue** — async video interview incumbent.
- **Eightfold** — talent intelligence.
- Lindy + others run recruiting agents as a feature, not flagship.

**Gap:** Reference-checking automation, candidate sourcing on niche platforms (Discord/Telegram dev communities), DEI auditing for hiring pipelines.

### Marketing / content — MEDIUM

- **Jasper, Copy.ai** — legacy generators with agentic features bolted on.
- **ContentHaven** — [UNVERIFIED] current status.

**Gap:** Brand-voice-aware content agents that watch competitor moves and react. Distribution agents (post-and-monitor across X/LinkedIn/Reddit with reply triage).

### Research agents — DOMINATED

- **Elicit** — 138M papers, 545k clinical trials, semantic search. Academic depth.
- **Perplexity Spaces** — team research workspaces.
- **Exa** — developer-API research, 100s QPS, agentic reasoning tasks. ([DigitalOcean](https://www.digitalocean.com/resources/articles/perplexity-alternatives))
- **You.com** agentic search.
- **OpenAI Deep Research** — folded into ChatGPT.

**Gap:** Research agents bound to private corpora (a company's internal docs + their support tickets + their engineering wiki). Most existing tools are web-public-corpus only.

### Field service / trades — RECENT OPENING

- **Avoca** — $125M, voice AI for HVAC/plumbing.
- **BuildOps, Simpro Lightning** — verticalized OS for contractors. ([BusinessWire](https://www.businesswire.com/news/home/20260513010148/en/Simpro-Group-Launches-Lightning-A-Purpose-Built-AI-Native-Operating-Platform-for-the-Field-Service-Trades))
- 25% residential contractor adoption — ~75% room. ([SignalFire](https://www.signalfire.com/blog/vertical-ai-in-trades-and-construction))

**Gap:** Permit-pulling, code-compliance, supplier price-comparison. Most contractors still email & call.

---

## Section 3: Developer infrastructure for agents

Context-setting only. Hackathon mandates Google ADK, so these are NOT competitors but landscape signals.

- **LangChain / LangGraph** — LangGraph the production winner, state-machine durable execution. Klarna, Uber, JPMorgan use cases. ([Speakeasy](https://www.speakeasy.com/blog/ai-agent-framework-comparison))
- **CrewAI** — role-based ("crew of agents with backstories"). Wider adoption pre-2026, plateaued.
- **AG2 (ex-AutoGen)** — Microsoft Research-origin.
- **Mastra** — TypeScript-native, ex-Gatsby team, 22k+ stars, 300k weekly npm. Native E2B / Modal / Cloudflare sandbox.
- **VoltAgent** — TS framework. Newer, smaller.
- **Inkeep** — RAG-shaped agent infra.
- **Composio** — tool-marketplace shape. 250+ integrations as connectors.
- **E2B** — Firecracker microVM sandbox-as-a-service. Backbone of Manus, used by many.
- **Google ADK** — what we're building on. Python-first, MCPToolset class, Agent Engine deployment.
- **OpenAI Agents SDK** — competing framework.
- **Microsoft Agent Framework** — competing.
- **Claude Agent SDK** — competing.

**Key signal:** Frameworks have CONVERGED. Production agents in 2026 all look like: orchestrator + tool registry + memory store + observability + sandbox. The differentiation is in the WORKLOAD, not the framework. Pick ADK, ship the workload.

---

## Section 4: Hackathon winner patterns (2024-2026)

Mining what actually wins, drawn from primary winner announcements.

### ADK Hackathon (Google, Jun 23 2025 deadline, 476 submissions, $50K pool)

Source: [Google Cloud blog](https://cloud.google.com/blog/products/ai-machine-learning/adk-hackathon-results-winners-and-highlights/)

| Project | Shape | What won |
|---|---|---|
| **TradeSage AI** (Grand prize) | Multi-agent financial trading hypothesis evaluator | Hyper-specific domain, multi-agent, ADK + Agent Engine + Cloud Run + Vertex AI (uses MULTIPLE Google services) |
| **Energy Agent AI** (NA winner) | Energy customer mgmt | Vertical domain |
| **Bleach** (EMEA winner) | Visual ADK agent builder, plain English | META — builds tools for ADK developers |
| **Edu.AI** (APAC winner) | Multi-agent Brazil education system | Local-language vertical with social impact |
| **SalesShortcut** (LATAM winner) | Multi-agent SDR | Productized B2B vertical |

### GKE Hackathon 2025

Source: [Google Cloud blog](https://cloud.google.com/blog/topics/developers-practitioners/winners-and-highlights-from-gke-hackathon)

| Project | Shape |
|---|---|
| **cart-to-kitchen AI assistant** (grand prize, Amie Wei) | Grocery→recipe agent, GKE + ADK + A2A |
| **Voice Teller** | AI phone agent for banking (replaces IVR) — Julian Hecker |
| **CO2-Aware Shopping Assistant** | 6 specialized agents, ADK + MCP + A2A |
| **Vigil AI** | Hierarchical multi-agent for Bank of Anthos fraud detection |

### Google Cloud Gen AI Exchange Hackathon (India, 2025, 270K developers)

Source: [Outlook Business](https://www.outlookbusiness.com/artificial-intelligence/google-cloud-gen-ai-hackathon-2025-winners-use-cases-and-what-270000-developers-built)

- **YouthMind** — confidential mental-health support for young people. Empathetic conversational design.
- **ArtisanGully** — agentic assistant for craftsmen to digitize and reach buyers.
- **Legal SahAI** — simplifies legal documents for laypeople.

### ETHGlobal Cannes 2026 (web3 but agent-shaped)

Source: [crypto.news](https://crypto.news/ai-agents-privacy-and-prediction-markets-define-ethglobal-cannes-2026-finalists/)

- **ENShell** — defends agents from prompt-injection malicious transactions.
- **DIVE** — AI swarm verifying real-world truth for prediction markets.
- **VEIL VPN** — verifiable encrypted internet w/ no-log proofs.

### AgentHacks (research-focused)

- **From Match to Money** — cold-outreach-to-warm-intro converter.

### Cross-cutting winner pattern (CONFIRM `05-prior-winners.md`)

1. **Hyper-specific domain.** "Agent for X workflow at Y kind of org" beats "agent that helps with productivity."
2. **Multi-step real-world action producing a TANGIBLE artifact** (a PR, a placed order, a generated report, a phone call made).
3. **Uses multiple Google services together** (ADK + Agent Engine + Cloud Run + Vertex AI was the TradeSage winning combo). Not one service.
4. **Demo video shows the AGENT acting**, not the team explaining.
5. **Social-impact / accessibility shape disproportionately rewarded.** Edu.AI Brazil, YouthMind, ArtisanGully — all winners. Google judges over-index on impact.
6. **Voice-agent demos punch above weight.** Voice Teller (banking), Avoca pattern, YouthMind. Voice + agent = visceral demo.
7. **A2A / multi-agent protocols feature in ~50% of winners.** Single-agent submissions are competing in the saturated middle.

---

## Section 5: GAP ANALYSIS — what's NOT being attempted

The most important section. 12 agent shapes that are (a) technically feasible on today's stacks, (b) not productized by a major player, (c) not yet a Devpost / ETHGlobal winner I've found, (d) demoable in 3 minutes, (e) high-impact.

### Gap 1: The "Agent That Watches Other Agents And Fires Bad Ones"

- **Gap:** A meta-agent that ingests Arize Phoenix / OpenTelemetry traces from a fleet of agents (yours or third-party), scores their performance, and AUTOMATICALLY rotates underperforming agents out of production. Today, eval is something humans do manually after the fact.
- **Why no one has built it:** Until OpenInference + ADK auto-instrumentation matured (late 2025/early 2026), the trace data was too noisy to grade reliably. Now it's clean.
- **Why it could work now:** Phoenix MCP server (announced for this hackathon track) exposes trace querying as MCP tools. Gemini 3.5 Flash can reason over them cheaply.
- **Adjacent:** Arize Phoenix itself (observability only — doesn't ACT). LangSmith (same — observe, not act). Honeycomb Canvas Agent (May 2026, observability surfaces agentic surfaces but doesn't enforce).
- **Why it could win:** Recursive — "agent that fires bad agents" is meme-able. Fits Arize track. Demoable: show a multi-agent system, kill the bad one live on stage.

### Gap 2: The Permitting / Inspection / Code-Compliance Agent for Trades

- **Gap:** An agent that, given a job description (e.g., "replace water heater at 123 Main St"), pulls the local jurisdiction's plumbing/electrical code, fills out the permit application PDF, files it electronically where possible, and tracks inspection scheduling.
- **Why no one has built it:** Code is fragmented across thousands of jurisdictions. Building this requires patient data wrangling per jurisdiction. Unsexy.
- **Why now:** PDF-extraction LLMs (Gemini 3.1 Pro vision) are good enough. Many jurisdictions now have API endpoints for permit filing.
- **Adjacent:** Avoca (voice for trades, not paperwork). BuildOps, Simpro Lightning (job mgmt, not permits).
- **Why win:** Tangible artifact (the filed permit). Massive real-world impact. Demo: voice-to-filed-permit in 2 minutes.

### Gap 3: The Prior-Authorization Agent for Mid-Size Healthcare

- **Gap:** US healthcare prior-auth is still 90% phone + fax. An agent that takes a patient case, finds the payer's prior-auth requirements, fills the form, submits, and chases status.
- **Why no one has built it (well):** HIPAA + payer-API access is hard. Existing players (Cohere Health, Olive AI) target enterprise health systems with $100K+ deals.
- **Why now:** Faxing-via-API services + ePA APIs from major payers shipped 2024-2025.
- **Adjacent:** Hippocratic AI (patient-facing only). Ambience (scribing only). Cohere Health (enterprise sales cycle locks out small practices).
- **Why win:** Brutally specific. "Agent that gets your insurance approval in under 30 minutes" is a 3-min demo. Strong impact narrative.

### Gap 4: The "Agent That Audits Your SOC2 / GDPR DPIA / HIPAA Readiness From Live System Telemetry"

- **Gap:** Compliance audits today = humans interviewing engineers + screenshots. An agent that wires up to Cloud Run logs, GitLab repo audit, MongoDB Atlas config, Dynatrace telemetry, and produces an evidence-collected compliance posture report continuously.
- **Why no one has built it:** Vanta + Drata + Secureframe own this but THEY don't use agents — they use form-questionnaires and screenshots.
- **Why now:** Dynatrace / Elastic / GitLab all expose MCP servers (this hackathon!) that an agent can query directly for evidence.
- **Adjacent:** Vanta (form-based, no agent). Drata (same). [UNVERIFIED] whether any have shipped real agentic continuous-audit by June 2026.
- **Why win:** Wraps multiple partner MCPs together (cross-track viability — Dynatrace OR Elastic OR GitLab + Arize for self-audit). Tangible artifact = the SOC2 evidence packet.

### Gap 5: The Reference-Checking Agent

- **Gap:** Hiring requires 3 reference calls per finalist. Most companies skip or rush them. An agent that, given a reference's contact info + the role, calls them, runs a structured interview, and produces a synthesis.
- **Why no one has built it:** Voice-agent UX was clunky until Gemini 3.x voice + Vapi/Retell-style infra matured 2025-2026. Trust barrier (will references talk to an AI?).
- **Why now:** Voice quality is past the uncanny-valley threshold. Trust hack: agent opens with "I'm calling on behalf of $hiring_manager and can hand off if you'd prefer."
- **Adjacent:** HireVue (candidate-facing video, not reference calls). Eightfold (sourcing, not reference). Avoca (trades-specific voice).
- **Why win:** Voice agents win demos. Tangible artifact = the reference report. Recruiters pay for this.

### Gap 6: The "Recurring-Bill Negotiator" Agent

- **Gap:** Trim / BillFixers do this manually. An agent that, given a user's bills (internet, phone, insurance), calls the provider, navigates the IVR, threatens to cancel, gets a retention discount, reports back.
- **Why no one has built it (as an agent):** Trim / Rocket Money are human-ops. No one has trusted an agent to handle account credentials + retention conversations end-to-end.
- **Why now:** AP2 protocol for payment authorization mandates means agents can hold limited credentials. Computer-use + voice tools mature.
- **Adjacent:** Rocket Money (manual). Trim (manual). DoNotPay (chatbot, no real automation despite claims).
- **Why win:** "Saved you $300 in 5 minutes" demo is unforgettable. Consumer-mass-market.

### Gap 7: The Closing-Documents Diligence Agent for SMB Acquisitions

- **Gap:** SMB acquisition (think microacquire.com, smb-buyers) due diligence = 20 hours of human work per deal. An agent that reads the data room, cross-references claims against tax returns + revenue exports + GitLab repo activity, flags inconsistencies.
- **Why no one has built it:** SMB M&A is fragmented; no consolidated buyer. Harvey targets BigLaw.
- **Why now:** Long-context Gemini 3.1 Pro handles the data room as a single input.
- **Adjacent:** Harvey (enterprise legal). Sourcery (acquisitions platform, not agent). DealRoom (data-room software, no agent layer).
- **Why win:** Real workflow with measurable hour-savings.

### Gap 8: The "Agent for One Specific Indie Hacker Stack" (Vertical-of-Vertical)

- **Gap:** An agent that lives inside Beehiiv / Ghost / ConvertKit / Lemonsqueezy and handles the entire growth-loop ops: subscriber segmenting, A/B testing email subjects via Gemini, retention-trigger drips, refund handling.
- **Why no one has built it:** Each indie-creator stack is too small for VCs. But aggregated it's a real ICP.
- **Why now:** MCP servers proliferating (Beehiiv shipped one). ADK + MCPToolset trivial.
- **Adjacent:** ConvertKit's own automation (no agent). Customer.io.
- **Why win:** Niche but loud. Indie hackers will tweet about it.

### Gap 9: The Personal Health-Record Agent

- **Gap:** A consumer-facing agent that ingests your medical records (Apple Health, manually-uploaded PDFs, FHIR endpoints), tracks symptoms over time, flags anomalies, prepares pre-visit summaries for your next appointment.
- **Why no one has built it:** Liability. Big companies won't ship it because diagnosis = regulated.
- **Why now:** Carefully framed as "appointment prep" (NOT diagnosis) sidesteps liability. Apple Health + FHIR APIs mature.
- **Adjacent:** Hippocratic AI (clinician-side). Abridge (clinician-side). No consumer-side player.
- **Why win:** Universal pain ("you have 8 minutes with your doctor and forget half"). Tangible artifact = the pre-visit one-pager.

### Gap 10: The "Vibe-Coded SaaS Lifecycle" Agent (Build → Sell → Sunset)

- **Gap:** Solo founders use Lovable/Bolt to build. Then need an agent to launch (Product Hunt, ads), measure, iterate, sunset gracefully. No one has built the WHOLE lifecycle agent.
- **Why no one has built it:** Each phase (deploy, measure, sunset) has its own tool. No connecting tissue.
- **Why now:** With AP2 + Stripe + AppStore MCPs proliferating, payments + analytics + posting are all MCP-able.
- **Adjacent:** Lovable (build only). Vercel Analytics (measure only).
- **Why win:** Meta — agent that runs an indie SaaS business. Loud demo (show the agent shutting itself off when revenue drops below $100/mo).

### Gap 11: The Multi-Source Internal-Knowledge Resolution Agent

- **Gap:** An agent that, when asked an internal question, retrieves from Slack history + GitLab MRs + Linear tickets + Notion + the running app's Dynatrace telemetry simultaneously to construct an answer with verifiable provenance.
- **Why no one has built it:** Each tool has its own copilot. No cross-tool composer that respects auth + ACL.
- **Why now:** MCP standardizes the auth handshake across all of them.
- **Adjacent:** Glean (enterprise search, not agent). Asimov (code+docs, not Slack ops). Inkeep (RAG-first).
- **Why win:** "How does $internal_thing actually work?" is universal pain. Cross-MCP composition is exactly what this hackathon rewards.

### Gap 12: The Voice Agent For Non-English-Speaking Elders Navigating US Bureaucracy

- **Gap:** USCIS, IRS, Medicare, VA — phone-trees only, often English-only IVRs. An agent that takes a voice question in Tagalog/Vietnamese/Spanish, calls the agency on behalf of the elder, navigates the IVR, gets the answer, returns it.
- **Why no one has built it:** Hard, unsexy, no obvious monetization.
- **Why now:** Gemini 3.x is genuinely multilingual; voice quality is good in 20+ languages.
- **Adjacent:** Avoca (English-only). YouthMind (mental health, not bureaucracy navigation).
- **Why win:** Strongest social-impact narrative possible. Google judges over-index on this (see Edu.AI Brazil winning APAC).

### Gap 13: The "Self-Improving Agent via Trace Replay" Pattern

- **Gap:** An agent that, on every failed run, captures the trace, generates a test case, adds it to its eval suite, and proposes a prompt/tool-call fix. The agent IMPROVES itself overnight.
- **Why no one has built it (as a productized standalone):** Required Phoenix-style observability + MCP-driven trace access + a model good enough to read its own traces. All three converged in 2026.
- **Why now:** Exactly what the Arize track rewards. Phoenix MCP server exposes traces as tools. Gemini 3.5 Flash is cheap enough to run nightly self-improvement.
- **Adjacent:** Arize Phoenix (observability). LangSmith (eval). No single product does the full loop.
- **Why win:** Exactly the recursive / self-improving angle this hackathon's Arize track explicitly calls out (per the partner-arize.md research). The pre-baked wedge.

### Gap 14: The Cross-Calendar Negotiating Agent for Family Logistics

- **Gap:** Coordinating soccer practice + work meetings + grandma's birthday across 4 family calendars + 2 work calendars + the kids' school district calendar. An agent that proposes, negotiates, and books.
- **Why no one has built it:** Consumer market is hard to monetize. Calendly is meetings, not family-logistics.
- **Why now:** Multi-calendar MCP + Gemini long-context.
- **Adjacent:** Calendly (1:1 booking). Family-shared Google Calendars (passive, no agent).
- **Why win:** Universal. Demo = "agent rearranged my whole week to fit my kid's surprise dental appointment."

### Gap 15: The "Hackathon Submission" Agent (Meta-Self-Reference)

- **Gap:** An agent that, given a hackathon's rules + an idea, writes the submission (Devpost form, video script, README), runs through judging criteria, scores itself, suggests improvements.
- **Why no one has built it:** Too niche, too on-the-nose. But it's hilarious and recursive.
- **Why now:** All the pieces are MCP-able (Devpost form via browser MCP, YouTube upload MCP, GitHub README).
- **Adjacent:** None. Pure white space.
- **Why win:** Memorable. Judges' jaws drop when you submit your hackathon submission BY using the agent itself. (Probably too cute to actually win, but worth flagging.)

---

## Section 6: Agent UX patterns that won in 2024-2026

Cataloging the UX shapes that ACTUALLY shipped, ranked by demo-borrowability.

### UX Pattern 1: The "Plan View" / Devin Planning Surface — HIGH BORROW VALUE

Pattern: agent shows a step-by-step plan BEFORE executing. User can edit / approve / reject before agent acts. Then visual progress through the plan with checkmarks + intermediate artifacts.

Where: Devin's signature surface. ChatGPT Agent. AntiGravity Manager View (parallel plans). ([Builder.io](https://www.builder.io/blog/devin-vs-cursor))

Why win demos: judges see exactly what the agent will do, can intervene if dumb, and the visual progress IS the demo.

### UX Pattern 2: Browser Takeover With "Handoff" — HIGH BORROW VALUE FOR VOICE/CONSUMER

Pattern: agent drives the browser. At "trust boundary" (credential entry, payment, irreversible click), agent stops, hands control to user, waits. ([OpenAI](https://openai.com/index/introducing-operator/))

Where: Operator, Manus Browser Operator, Claude Cowork.

Why borrow: solves the trust problem in demos. "Agent does the boring 95%, hands off the scary 5%" is a clean narrative.

### UX Pattern 3: "Delegate to AI" Inbox — MEDIUM BORROW

Pattern: agent appears as a coworker in your Gmail / Slack. You forward / @-mention to delegate. Agent replies as a thread participant.

Where: Lindy (signature), Decagon (in customer Slack), various.

Why borrow: zero new UI. Lives in tools the user already has. Great for B2B demos with no time for custom frontend.

### UX Pattern 4: Multi-Agent Manager View — HIGH BORROW FOR HACKATHON

Pattern: dashboard showing N agents working in parallel on different tasks. Each cell shows status, current step, output. User dispatches and monitors.

Where: AntiGravity Manager View (signature), CrewAI demo UIs, internal LangGraph dashboards.

Why borrow: visually impressive. Multi-agent is what Google judges reward.

### UX Pattern 5: Cursor's Composer — MEDIUM BORROW (CODER-CENTRIC)

Pattern: chat-like agent surface that produces inline diffs against the open file/codebase. User accepts/rejects chunk-by-chunk. ([Vellum](https://www.vellum.ai/blog/best-ai-coding-agents))

Where: Cursor, Windsurf Cascade, Claude Code.

Why borrow: only relevant if your demo is code-shaped.

### UX Pattern 6: Canvas / Artifacts (Persistent Workspace) — HIGH BORROW

Pattern: agent produces a tangible artifact (doc, code, dashboard) in a SEPARATE pane that persists across the conversation. User edits live; agent updates around the edits.

Where: ChatGPT Canvas, Claude Artifacts (live + persistent variants), Honeycomb Canvas Agent, Perplexity Pages. ([MindStudio](https://www.mindstudio.ai/blog/what-is-claude-generative-ui-vs-canvas-artifacts))

Why borrow: the artifact IS the demo. Build the artifact in front of the judges.

### UX Pattern 7: Voice + Live Transcript + Action Log — HIGH BORROW FOR PUNCHY DEMO

Pattern: agent runs voice in/out, but the screen shows the live transcript AND the actions the agent is taking in parallel. Both human (transcript) and machine (action log) views.

Where: Voice Teller (banking, ADK winner), Avoca, Vapi customer demos, YouthMind.

Why borrow: voice demos punch above weight. Showing the action log proves it's actually doing something, not just chatting.

### UX Pattern 8: Trace-as-UI (Phoenix-Driven) — LOW PROD BUT HIGH HACKATHON BORROW

Pattern: the agent's own execution trace IS the user-facing UI. Spans, latency, tool calls visible. User can "rewind" to a span and re-run with edits.

Where: Phoenix Spans view, LangSmith. ([Arize blog](https://arize.com/ai-agents/agent-observability/))

Why borrow: matches Arize track. Differentiator vs every other submission that hides the agent.

### UX Pattern 9: "Receipt" Pattern — UNDERUSED, HIGH BORROW

Pattern: after agent completes an action, it produces a structured RECEIPT — what it did, when, on whose behalf, with what tools, with what cost. Like a real-world receipt.

Where: Lindy has this lightly. AP2 protocol mandates this for payments. Most don't.

Why borrow: simple, novel, builds trust. Easy to add as the last 30 seconds of a demo.

### UX Pattern 10: Parallel Plan Tree (CrewAI / Crew View) — MEDIUM BORROW

Pattern: visual tree showing crew of agents with roles ("Researcher", "Writer", "Critic"), each agent's task graph, A2A handoffs animated.

Where: CrewAI demo videos, AntiGravity (with manager dispatching).

Why borrow: multi-agent is what wins, visualizing it cleanly is rare.

---

## Top 3 UX patterns to borrow for THIS hackathon's demo

Given the rapid-agent hackathon's emphasis on (a) real action, (b) MCP integration, (c) 3-min demo video, (d) Arize observability track:

1. **Trace-as-UI (Pattern 8)** — uniquely fits Arize track. Show the agent's own trace as the UI. Visual win + matches sponsor focus.
2. **Plan View (Pattern 1)** — every winning demo has it. Show plan → approve → execute → checkmarks.
3. **Receipt (Pattern 9)** — close the demo with a "here's what the agent did, here's the trace, here's the cost" receipt. Underused, builds trust, clean ending.

---

## Cross-references

- **`02b-gemini-enterprise-agent-platform.md`** — which Google platform pieces map to which UX pattern (Agent Engine deployment, Studio for plan view, etc.).
- **`05-prior-winners.md`** — corroborates the winner patterns above (4 patterns Sahil's prior research already extracted).
- **`07-pre-commit-checklist.md`** Q2 — the wedge sentence should pick ONE gap from Section 5 + ONE UX pattern from Section 6.
- **Next file expected:** `04-wedge-shortlist.md` (or routed into `sahil-idea-generator`) — narrows Section 5 gaps down to 3-5 specific wedges for Abu's Arize track.

---

## Open questions / [UNVERIFIED]

| Question | Why | How to verify |
|---|---|---|
| Did MultiOn ship anything in 2026? | Affects Section 1 completeness | Check multion.com / @multion_ai |
| Current status of Domo, Sapient, RegoX finance agents | Section 2 finance gap may be smaller than stated | Crunchbase + Sacra |
| Has any startup productized Gap 1 (the "fire bad agents" meta-agent)? | Direct competitor check for the recursive Arize wedge | Search "agent grading agent", "meta-observability agent" via Tavily |
| What did the AI in Action 2025 winners actually demo? | Specific UX-pattern borrow material | Devpost aiinaction.devpost.com project gallery |
| Is there a Devpost gallery for the rapid-agent hackathon itself, locked or visible? | Saturation reality-check | `03-project-gallery.md` already says NO until post-deadline |
