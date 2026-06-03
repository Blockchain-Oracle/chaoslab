# 05 — Ecosystem Refactor: Winning Projects From Other Ecosystems We Can Port to Google Cloud Agent Platform

> **Purpose.** Abu has won 3 of his last 4 hackathons by rebuilding winning projects from OTHER ecosystems with a material differentiator. This file is the candidate pool for that move at the Google Cloud Rapid Agent Hackathon (`rapid-agent.devpost.com`, deadline 2026-06-11, 9 days from compile).
>
> **What you'll find here.** 12 winning agent projects mined from non-Google ecosystems (ETHGlobal, Microsoft Azure, AWS, UiPath, TiDB, Agno, Forum Ventures), each scored on portability to Google Cloud Agent Platform + at least one of 6 partner MCPs (Arize, Elastic, Fivetran, GitLab, MongoDB, Dynatrace).
>
> **Constraint inherited from `CONTEXT.md` §2 and `07-pre-commit-checklist.md`:** primary track recommendation is Arize, backup Fivetran. Rebuild has to fit ≤9 days. Banned in submitted code: Claude/Cursor/Copilot as runtime, LangChain/LangGraph/LlamaIndex as primary orchestrator. Allowed in dev workflow.

---

## Methodology

**Sources mined (all in the last hour, 2026-06-02):**

1. **ETHGlobal Agentic Ethereum 2025** — 10 finalists from 518 submissions ([X announcement](https://x.com/ETHGlobal/status/1890448806975795550), [showcase](https://ethglobal.com/showcase?events=agents))
2. **ETHGlobal Cannes 2026** — 10 finalists ([crypto.news writeup](https://crypto.news/ai-agents-privacy-and-prediction-markets-define-ethglobal-cannes-2026-finalists/))
3. **Microsoft AI Agents Hackathon 2025** — 18,000 devs, 570 submissions, category winners published ([winners showcase](https://techcommunity.microsoft.com/blog/azuredevcommunityblog/ai-agents-hackathon-2025-%E2%80%93-category-winners-showcase/4415088))
4. **AWS AI Agent Global Hackathon 2025** — winners announced at re:Invent ([Devpost update](https://aws-agent-hackathon.devpost.com/updates/38140-congratulations-to-the-winners-of-the-aws-ai-agent-global-hackathon))
5. **UiPath AgentHack 2025** — 400+ submissions, 50+ countries ([UiPath community](https://community.uipath.com/community-blog/community-news/uipath-community-annual-global-hackathon-2025))
6. **TiDB AgentX Hackathon 2025** — $30K+ in prizes, agentic AI focus ([Devpost](https://tidb-2025-hackathon.devpost.com/))
7. **Google ADK Hackathon 2025** — INCLUDED as reference (predecessor; rebuilds here are in-ecosystem inheritors, not refactors, but still useful for "what they like")
8. **AI in Action Hackathon 2025** — direct predecessor multi-partner Google Cloud + MongoDB + GitLab hackathon ([GitLab blog](https://about.gitlab.com/blog/ai-in-action-hackathon-celebrating-the-gitlab-innovations/))
9. **Agno Global Agent Hackathon May 2025** — open-source agent framework hackathon ([results](https://www.agno.com/blog/global-agent-hackathon-winners))
10. **Forum Ventures × Anthropic Agentic AI Hackathon** — zero-to-one company-building agents

**Ranking criteria (informs §"Top 5 ranked" below):**

- **Demo-ability (1-5):** can you show a 3-min agent-in-action video that wins on the "agent ACTING not narrating" pattern from `05-prior-winners.md` Pattern C?
- **Differentiator strength (1-5):** how sharp is the wedge Abu can add when porting? Cross-ecosystem novelty alone is not enough — there has to be a material delta.
- **Build feasibility in 9 days (1-5):** can a solo dev who has zero Google Cloud agent platform experience finish this without overrun? Sources: `02b-gemini-enterprise-agent-platform.md` decision matrix, partner MCP free-tier paths.
- **Track fit / EV (1-5):** does it cleanly slot into one of the 6 partner buckets where it can win? Bonus if it fits Arize (green lane, recommended in CONTEXT.md §2).
- **Sharpness of pain point (1-5):** is the user pain visceral and explainable in 10 seconds? Winning ADK projects all had this (Pattern A, `05-prior-winners.md`).

**Overall score = product of all five** (multiplicative-floor; if any axis is ≤2 the project is filtered out).

### What each ecosystem contributes to this refactor pool

A quick map for orientation before the candidate dossier — what FLAVOR of winning project each ecosystem ships, and what's worth porting:

- **ETHGlobal (Agentic Ethereum 2025 + Cannes 2026):** ships agent-with-on-chain-action projects, frequently focused on AI safety (ENShell), oracle consensus (DIVE), automated smart contract execution (Shaman), and prediction markets (PvPvAI). **Port value:** the AI safety + oracle-consensus + agent-shell patterns translate cleanly to enterprise environments — strip the wallet primitives, keep the policy/consensus logic. The crypto-native ones (token launchers, yield-finders) don't translate.
- **Microsoft AI Agents Hackathon 2025:** ships enterprise-shaped winners — supply chain risk (RiskWise), incident management (WorkWizee), tax/forms (Tariffed), research (Apollo), knowledge transfer (Konveyor). **Port value:** highest-EV ecosystem to mine because winners shipped here look exactly like what wins on Google Cloud's enterprise-judging panel. Concrete pain, multi-agent, real workflow output.
- **AWS AI Agent Global Hackathon 2025:** ships AgentCore/Bedrock-shaped winners — insurance claims (AegisAgent), tax filing (Province), waste management (EcoLafaek). **Port value:** the AgentCore patterns + Kiro-style agent specs translate one-to-one to ADK; only the runtime swaps. AWS judges loved "5-day-100%-AI-generated-code" — Google judges value more authentic engineering. Pick carefully.
- **UiPath AgentHack 2025:** ships RPA-flavored winners — TrialIQ (clinical regulatory), and many enterprise-workflow agents. **Port value:** strong for "regulatory + multi-doc" patterns, but UiPath's drag-and-drop visual primitive doesn't map; Abu re-writes everything in ADK.
- **TiDB AgentX Hackathon 2025:** ships streaming-data agent winners (PetFitAI), multi-modal + real-time. **Port value:** the streaming-multi-modal pattern is valuable; the TiDB-native moat ISN'T portable, has to be replaced with MongoDB Atlas Vector Search.
- **Agno Global Agent Hackathon May 2025:** ships open-source-framework-flavored winners (Likeminds, AdGenius, Beifong). **Port value:** Agno is "LangChain-but-better" — banned as primary orchestrator. The IDEAS port (semantic-social network agent, personalized podcast) but the FRAMEWORK can't.
- **Forum Ventures × Anthropic Agentic AI Hackathon Sept 2025:** ships zero-to-one-company-building agents (zenith.chat). **Port value:** the "agent that IS the company" pattern is creative; less Devpost-rubric-fit because it leans on narrative, not multi-step engineering.
- **Direct predecessor (AI in Action 2025 + ADK Hackathon 2025):** ships exactly what wins THIS hackathon — Edu.AI, SalesShortcut, Energy Agent AI, Pipeline Doctor, GitLab Guardian Army. **Port value:** highest possible (judging culture is identical). But these aren't "refactor" in the strict sense — they're in-ecosystem; you're choosing which MCP/partner to recompose with.

---

## The 12 candidates

### 1. SalesShortcut → "AI Outbound Ops Agent for fintech sponsors using Fivetran-piped CRM signals"

- **Original ecosystem:** Google ADK Hackathon 2025 (Grand Prize — in-ecosystem reference, not pure refactor, but the wedge is which MCP it integrates and which buyer it talks to).
- **What it did:** Multi-agent SDR system. Lead Finder Agent scours Google Maps for businesses without websites in a target city. SDR Agent runs deep research on the prospect, analyzes competitors, identifies pain points, generates a personalized website-development proposal. Voice-call Agent (powered by ElevenLabs) actually phones the lead. Email Agent does follow-up. Lead Manager Agent stores everything in BigQuery and orchestrates the funnel. End-to-end autonomous — no human in the loop after pointing at a city. ([Devpost](https://devpost.com/software/salesshortcut), [Medium long-form](https://medium.com/@sernur213/salesshortcut-building-an-autonomous-ai-sales-team-with-multi-agent-ai-architecture-using-google-e794c2c72152))
- **Original tech stack:** Google ADK + Gemini 2.0 Flash + Cloud Run + BigQuery + Google Maps API + Cloud Pub/Sub (inter-agent comms) + ElevenLabs voice.
- **Why it won:** Grand Prize, ADK Hackathon (10,400 participants, 477 submissions). Hit all four winner patterns from `05-prior-winners.md`: (A) specific domain — B2B SDR for SMBs without websites; (B) 4-step autonomous pipeline producing concrete artifacts (call transcripts + signed proposals); (C) demo video showed agents actually making phone calls; (D) production polish — multi-service GCP stack with custom UI.
- **Why it ports to Google Cloud Agent Platform:** It's literally on the platform already. The port replaces Google Maps as the cold prospect source with **Fivetran MCP** ([official repo](https://github.com/fivetran/fivetran-mcp)) sucking from HubSpot, Salesforce, Stripe, Pipedrive — i.e., the team's WARM pipeline. The agent now reasons over "Stripe MRR dropped 12% in 30 days for account X → churn risk → trigger save-call campaign," not "this restaurant has no website → cold-call them about it."
- **Material differentiator:**
  - **Better data:** warm CRM + intent signals beats cold Google Maps every time. The demo showing a real-feeling churn-risk account auto-escalated is more visceral than "this restaurant has no website."
  - **Fresher 2026 timing:** AP2 (Agent Payments Protocol) integration so the agent can actually issue an invoice + take payment within the same conversation. SalesShortcut couldn't do this in 2025; the protocol was June 2026.
  - **Multi-partner composition:** Fivetran (data ingest) + Arize Phoenix (eval-graded outreach quality so the agent doesn't send terrible emails) — most submissions use one partner.
- **Rebuild time:** 6-7 days. ADK SDR loop pattern is documented in [Dev.to ADK SDR guide](https://dev.to/koolkamalkishor/building-an-ai-sdr-agent-with-adk-a-developers-guide-to-sales-automation-2jhl). 3-agent reduction (Researcher / Personalizer / Closer), 1 Fivetran MCP wire, 1 AP2 webhook.
- **Track fit:** **Fivetran** (yellow lane, backup from CONTEXT.md §2). Could pivot to **GitLab** if redirected to dev-tools sales (HubSpot → GitLab CRM signals).
- **Risk:** (a) Fivetran 14-day trial squeeze — must activate within 7 days of submission window. (b) Demo content quality depends on a realistic-feeling CRM dataset; Abu doesn't have one, will need to synthesize. (c) ElevenLabs voice gets expensive. (d) Differentiation from SalesShortcut is narrow — judges who saw the original may say "we've seen this." **Mitigation:** lean hard on the AP2 angle (literally no one else has it; first-mover wins notice). Demo synthesized CRM through a Postgres + Fivetran connector pipeline that's transparent in the architecture diagram.

---

### 2. Edu.AI → "AI Tutor Ops Agent for textbook publishers, with MongoDB-stored personalized learning paths"

- **Original ecosystem:** Google ADK Hackathon 2025 (LATAM regional winner).
- **What it did:** Multi-agent system that evaluates Brazilian ENEM essays, generates personalized study plans, and creates interdisciplinary mock exams. 8 specialized ADK agents. ([Devpost](https://devpost.com/software/edu-ai-multi-agent-educational-system-for-brazil))
- **Original tech stack:** Google ADK, Gemini, custom frontend.
- **Why it won:** Specific domain (Brazilian K-12 ENEM prep), specific population (public school students without tutors), tangible artifact (graded essay + study plan + mock exam). Pattern A + B fit.
- **Why it ports to Google Cloud Agent Platform:** Already on it, but the port is **switching the persona from student → textbook publisher / curriculum designer** and adding **MongoDB MCP** for the structured curriculum DB. Publishers want to know "which questions in my catalog correlate with concept mastery? Which study plans actually move the needle?" That's RAG + analytical queries over their catalog — MongoDB Atlas Vector Search territory.
- **Material differentiator:** **Better domain** (B2B publisher pain vs B2C student) — publishers PAY for tools, students don't. Plus the agent acts on the _catalog metadata layer_ not the student layer, which is a fresher, less crowded angle. The student-tutor agent space is now saturated; the _curriculum-design-loop agent_ space is barely touched.
- **Rebuild time:** 7 days. The 8-agent shape is heavy but most can be collapsed into 3 — generator, evaluator, optimizer.
- **Track fit:** **MongoDB** (RED lane per CONTEXT.md §2 — but with a B2B angle that most submissions won't have, lane saturation matters less).
- **Risk:** MongoDB lane is the most crowded; the differentiator has to be loud. Without real publisher data, demo authenticity suffers. **Mitigation:** synthesize a realistic textbook catalog using public OpenStax content as the source.

---

### 3. Particle Physics Agent → "NL-to-Validated-Output Domain-Pivot Agent" (compilable-output pattern)

- **Original ecosystem:** Google ADK Hackathon 2025 (Honorable Mention from a 477-submission field — i.e., a top-tier outcome the judges specifically called out).
- **What it did:** Natural language ("electron-positron annihilation producing two photons") → validated, compilable TikZ-Feynman LaTeX. 6 specialized AI agents working collaboratively:
  - Validator agent (checks particle interactions against the Particle Data Group database)
  - Knowledge-base agent (searches through 150+ curated examples)
  - LaTeX-codegen agent (emits TikZ)
  - Compile agent (tries to compile, captures errors)
  - Correction agent (iterates up to 3 refinement attempts)
  - Orchestrator
  - **95%+ success rate at producing compilable diagrams.** ([Devpost](https://devpost.com/software/particle-physics-agent))
- **Original tech stack:** Google ADK, Gemini, LaTeX toolchain, custom Particle-Data-Group validation against authoritative source.
- **Why it won (honorable mention):** Pattern A excellence (physics PhDs writing papers — hyper-specific buyer with name and face). Pattern B (multi-agent w/ auto-correction loop = visible orchestration). Tangible artifact (compilable LaTeX diagram — instantly demoable, binarily valid or not). Pattern D (deep ADK use). Authoritative-source-validation is the secret sauce (Shape 3 from Appendix A).
- **Why it ports to Google Cloud Agent Platform:** Same platform; the PORT is the _pattern_, not the project. Pattern = NL → compilable/validated output, with auto-correction against an authoritative source. Pivot the domain to:
  - **Kubernetes manifests validated against the cluster's actual schema:** Dynatrace MCP tells you what services exist, what their actual config schemas look like, what other services depend on them.
  - **Legal-citation-correct contract clauses:** Elastic MCP indexes statutes/case law; the validator checks every cited case is real and applicable.
  - **SQL queries validated against MongoDB collection schema:** MongoDB MCP exposes the live schema; validator checks the agent's emitted query against actual collections + types.
  - **CI/CD pipeline YAML validated against GitLab project structure:** GitLab MCP exposes existing pipelines + variables + runners; validator checks the agent's YAML compiles.
- **Material differentiator:**
  - **Sharper demo:** "NL → compiled manifest deploys to my cluster" is a 30-second wow.
  - **Better domain (depending on pivot):** the LaTeX-for-physics-PhDs market is small; the K8s-manifest-for-platform-engineers market is huge. Same pattern, larger TAM.
  - **Auto-correction loop using OBSERVABILITY data:** the recursive twist. Phoenix MCP for self-introspection ("which fault classes did my emitted manifest hit in CI?") OR Dynatrace MCP ("did this manifest actually deploy cleanly?"). Original validated against a STATIC physics DB; Abu validates against a LIVE SYSTEM THE AGENT ITSELF INSTRUMENTS. That's the meta-recursion play (cousin of #9 ChaosLab).
- **Rebuild time:** 5-6 days. Pattern is small; only the validation source changes. Estimate breakdown: 1d ADK + Gemini scaffolding, 2d for the auto-correction loop in the pivot domain, 1d Phoenix or Dynatrace MCP wire, 1d demo polish.
- **Track fit:** **Arize** (green lane). Pattern fits perfectly because Phoenix evals ARE the validation source for the auto-correction loop. Alternative: **Dynatrace** if pivoted to k8s.
- **Risk:**
  - Domain pivot needs to land. "Compilable LaTeX" was great because it's tangibly broken or not. "Compilable K8s manifest" is good. "Hallucination-free legal clause" is harder to demo (no compile button).
  - "Compilable K8s manifest" has prior art (e.g., k8sgpt, KubeGPT) — must be aware.
- **Mitigation:**
  - Pick a domain where validity is BINARY AND VISIBLE in the demo (manifest deploys / doesn't; SQL returns results / errors; pipeline runs / fails).
  - Differentiator vs k8sgpt: ChaosLab-style recursive self-improvement (the agent reads back its own historical failures and gets better over time). k8sgpt is static.

---

### 4. TradeSage AI → "Hypothesis-Testing Agent for [non-trading domain] with Phoenix-graded confidence"

- **Original ecosystem:** Google ADK Hackathon 2025 (Honorable Mention).
- **What it did:** Multi-agent trading platform; user enters a hypothesis ("oil will rally if China stimulus passes"), 6 agents structure → extract assets → identify risks → score confidence → emit alert with entry/risk levels. Frames trading as scientific hypothesis testing. ([Devpost](https://devpost.com/software/tradesage-ai), [Medium](https://medium.com/google-cloud/building-tradesage-ai-a-multi-agent-trading-analysis-platform-with-googles-agent-development-kit-d14ec7c381e1))
- **Original tech stack:** ADK + Agent Engine + Cloud Run + Vertex AI.
- **Why it won:** Pattern A (specific role: retail trader trying to be institutional), Pattern B (6-step pipeline), Pattern D (multi-Google-Cloud-service stack). Recognized as honorable mention.
- **Why it ports to Google Cloud Agent Platform:** Pivot the pattern from trading-hypothesis → **clinical-research-hypothesis**, or **product-management-hypothesis**, or **incident-RCA-hypothesis**. The "scientific hypothesis tester" pattern is domain-agnostic.
- **Material differentiator:** **A2A protocol composition + better domain**. Use A2A (Agent-to-Agent) to spawn parallel verification agents that each take a contradicting POV (e.g., bull/bear). Each agent emits a confidence score graded by **Phoenix evals**. The "judge of judges" lives in Arize. That's a recursive observability angle that's directly the Arize bonus criterion.
- **Rebuild time:** 6-8 days. The 6-agent shape is real work; A2A wiring is new in 2026.
- **Track fit:** **Arize** (green lane).
- **Risk:** "Hypothesis tester" is abstract. Domain has to be concrete enough that the user feels the pain. Trading was concrete; "incident RCA hypothesis testing" is concrete; "PM hypothesis testing" is fuzzy. **Mitigation:** pick a domain where the hypothesis can be live-tested in the demo (e.g., a fake incident hits, the agent generates 3 hypotheses, scores them, and the correct one wins).

---

### 5. AegisAgent → "Claim/Coverage Decision Agent with AP2 disbursement" (AWS → GCP port)

- **Original ecosystem:** AWS AI Agent Global Hackathon 2025 (winner, announced at re:Invent).
- **What it did:** Transforms manual insurance claim reviews into automated, explainable decisions. AWS Kiro orchestrates specialized agents for evidence curation (read PDFs, photos, doctor notes), policy interpretation (read policy language, identify applicable clauses), and compliance reasoning (debate which clauses apply, surface ambiguities, generate audit trail). Built in 5 days, 100% AI-generated code. Output: a "transparent, defensible coverage decision workflow" that effectively debates and resolves ambiguities in claim artifacts and policy documents. ([Devpost winners update](https://aws-agent-hackathon.devpost.com/updates/38140-congratulations-to-the-winners-of-the-aws-ai-agent-global-hackathon))
- **Original tech stack:** AWS Kiro (spec-driven agentic IDE), Amazon Bedrock with Claude 3.5 Sonnet, semantic indexing on Bedrock, multi-agent orchestration via AgentCore.
- **Why it won:** Pattern A (insurance claims, $1.2T US market, regulated domain), Pattern B (multi-agent debate → decision pipeline), Pattern D (deep AWS Bedrock + Kiro stack signaling platform breadth). The "explainable decision workflow" angle resonates strongly because insurance is regulated and audit-bearing.
- **Why it ports to Google Cloud Agent Platform:** Replace Kiro with ADK; replace Bedrock-Claude with Gemini 3.1 Pro (needed for reasoning depth on policy clause interpretation — Gemini 2.5 Flash too shallow). Use **Elastic MCP** to semantic-search policy documents (Elastic's ELSER is genuinely best-of-breed for legal/policy text retrieval; Bedrock's RAG is generic). Then add **AP2 (Agent Payments Protocol)** for actually disbursing the approved claim payment — closing the loop the original couldn't.
- **Material differentiator:**
  - **AP2 integration:** original couldn't pay out claims; Abu's can. AP2 is 2026-new; no incumbent has it baked in.
  - **Better protocol composition:** Elastic (semantic) + ADK (orchestration) + AP2 (payment) + A2UI (claim-adjuster co-edits the decision in a structured component) — 3 of 5 protocols, vs the rubric's likely "just MCP" baseline.
  - **Better RAG:** Elastic + ELSER on policy docs > Bedrock-generic RAG on policy docs (this is provable in side-by-side eval).
- **Rebuild time:** 7-8 days. 1 day Elastic trial + cluster setup, 2 days ADK + policy-doc-RAG, 2 days multi-agent debate pattern, 1 day AP2 wire, 2 days demo polish.
- **Track fit:** **Elastic** (yellow lane). Note: Elastic was filtered OUT in CONTEXT.md §2 for trial-squeeze reasons. If we pick this one, mitigate by activating the Elastic trial exactly 8 days before deadline so the trial covers submission and demo recording but doesn't waste days.
- **Risk:**
  - Elastic 14-day trial timer pressure
  - Insurance domain authenticity bar is high; without real-feeling policy docs the demo fails
  - Claim-decision agents have several commercial entrants (CCC, Tractable, EvolutionIQ); judges may be aware
  - AP2 maturity — protocol may have rough edges in June 2026
- **Mitigation:**
  - Use publicly-available CMS Medicare policy PDFs as the corpus (real, weighty, authoritative — 2,000+ pages indexed)
  - Demo on a synthesized but realistic claim packet (auto-claim PDF, repair shop photos, body shop estimate, policy excerpt)
  - Activate Elastic trial on Day 1 (2026-06-04) so it covers through 2026-06-18 (covers submission deadline 06-11 + 7-day judging buffer for follow-up demos)

---

### 5b. Pipeline Doctor (predecessor mention)

- **Original ecosystem:** AI in Action 2025 (predecessor hackathon featured project).
- **What it did:** AI for advanced root cause analysis to swiftly diagnose CI/CD pipeline anomalies by analyzing logs and changes, explaining security issues, and predicting bottlenecks. Specifically called out in [GitLab's AI in Action blog](https://about.gitlab.com/blog/ai-in-action-hackathon-celebrating-the-gitlab-innovations/) as exemplary "agentic CI/CD."
- **Why it's flagged here:** Same ecosystem as the Rapid Agent Hackathon (AI in Action is the direct predecessor); same Google + GitLab + MongoDB partner DNA; if Abu picks GitLab lane, this is THE reference shape to be aware of (and differentiate from).
- **Not a refactor candidate (would be duplicate-fishing):** in-ecosystem, not cross-ecosystem. Skip as a port target — but understand it deeply if pitching anything in the GitLab lane.

---

### 6. ENShell → "Prompt-Injection-Hardened Agent Gateway with GitLab/Dynatrace policy enforcement"

- **Original ecosystem:** ETHGlobal Cannes 2026 (10-finalist from blockchain ecosystem).
- **What it did:** Prevents AI agents from executing malicious transactions caused by prompt injection. Agent transaction flows wrapped inside an ENS-aware shell that checks proposed actions against policy before a signature hits a wallet. ([crypto.news](https://crypto.news/ai-agents-privacy-and-prediction-markets-define-ethglobal-cannes-2026-finalists/))
- **Original tech stack:** ENS resolver, Ethereum wallets, policy engine.
- **Why it won:** Sharp pain point (prompt injection is the #1 enterprise concern about agents in 2026), genuinely novel (most agent frameworks don't have this layer), defensible position.
- **Why it ports to Google Cloud Agent Platform:** Replace ENS with **GitLab identity** (every dev has a GitLab account; policies tied to GitLab groups). Every Gemini agent's proposed tool call goes through the shell, which checks against a GitLab-stored policy DAG. If the agent tries to `DELETE FROM production`, the shell sees the GitLab project's policy and blocks/quarantines.
- **Material differentiator:** **Better protocol composition** (UCP — Unified Context Protocol — gives the shell standardized context to make decisions; AP2 lets approved actions trigger payments). **Better domain** (devops, not crypto — bigger market). The crypto version was niche; the dev/data tools version is universal.
- **Rebuild time:** 6-7 days. The shell pattern is small; the policy DAG is the work.
- **Track fit:** **GitLab** (RED lane per CONTEXT.md, but the angle is differentiated). Could also be Dynatrace (policy = runtime tracing) or Arize (policy = trace-based eval).
- **Risk:** GitLab lane is saturated; the "AI safety / agent shell" angle has been built before (in crypto, by enterprise AI safety startups). **Mitigation:** lean hard on the _demo_ — show a live prompt injection in a Gemini agent that ATTEMPTS to drop a production table; ENShell stops it; without ENShell, table gone. That visceral side-by-side is winning material.

---

### 7. DIVE → "AI Swarm Verification Agent for Exec-Dashboard Truth-Claims" (with Phoenix-traced consensus)

- **Original ecosystem:** ETHGlobal Cannes 2026 finalist (10 from a several-hundred field).
- **What it did:** AI swarm engine verifying real-world truth for prediction markets + autonomous on-chain settlement. Multi-agent oracle layer where each agent independently fetches external data (news APIs, on-chain data, X/Twitter sentiment) about a claim, agents converge via consensus on a verified outcome, and only THEN is the on-chain settlement transaction signed. Prevents "wrong-oracle" exploits in prediction markets. ([crypto.news writeup](https://crypto.news/ai-agents-privacy-and-prediction-markets-define-ethglobal-cannes-2026-finalists/))
- **Original tech stack:** Multi-agent swarm (likely 3-5 agents), external data feeds (oracle data, news), Ethereum smart-contract integration for settlement, consensus reconciliation logic.
- **Why it won (finalist tier):** Concrete problem (prediction-market oracle accuracy is a known $50M+ exploit class), multi-agent consensus pattern (visible Pattern B), autonomous settlement (Pattern B closure), AI safety/security adjacency (the 2026 hot theme at ETHGlobal Cannes — see "AI agents, privacy and prediction markets define Cannes 2026 finalists").
- **Why it ports to Google Cloud Agent Platform:** The PATTERN is multi-agent fact-checking with consensus. Pivot domain to **enterprise data quality / exec-dashboard truth-claims**:
  - The CFO says "ARR is up 20% QoQ." The marketing VP says "MQL→SQL conversion is up 30%." The PM says "DAU is up 15%."
  - The Truth-Swarm agent spawns N independent verifier agents.
  - Each verifier agent pulls from a different source-of-truth: Stripe MRR via Fivetran, Salesforce pipeline via Fivetran, Mixpanel events via Fivetran, the warehouse (BigQuery) directly, etc.
  - Each agent independently computes the claim from raw data.
  - Phoenix traces every agent's reasoning chain.
  - The Reconciler agent reads the per-source results, identifies divergences, and emits a confidence interval ("ARR claim verified at 95% confidence, lower bound 18%, upper bound 22%") or a discrepancy ("CFO's number doesn't match Stripe; difference is $X attributable to revenue recognition policy on contracts signed in this quarter but starting next").
- **Material differentiator:**
  - **Better domain:** enterprise board-deck truth-verification > niche crypto prediction markets. The "did our team's number really go up?" question is a $1B+ pain (every public company's CFO + investor relations stack).
  - **Fivetran MCP fit:** the original ETHGlobal version couldn't pull from 100s of SaaS sources; Fivetran's MCP enables exactly this composition.
  - **Phoenix-graded consensus:** every agent's reasoning chain is auditable. That's compliance-grade and SOX-friendly — a real moat.
  - **A2A composition:** spawning parallel verifiers is exactly what A2A is for.
- **Rebuild time:** 7-8 days. The agent swarm is small (3-5 agents); the Fivetran setup is the bulk of effort.
- **Track fit:** **Fivetran** (yellow lane).
- **Risk:**
  - "Data quality / observability" is a saturated commercial space — Monte Carlo, Anomalo, Lightup, BigEye are all there.
  - The "exec dashboard truth-verify" framing is fresh, but easy to dismiss as a clever wrapper around analytics tools.
  - 14-day Fivetran trial squeeze.
- **Mitigation:**
  - Lean on the AGENTIC angle — multiple agents _debating_ each other and emitting a confidence interval is genuinely new vs the static-rule-engine incumbents (Monte Carlo is rule-based, not agentic).
  - Demo SHOULD show divergence: agent A says ARR is up 22%, agent B says 18%, agent C says 25%, Reconciler agent goes "wait — the difference is revenue recognition on multi-year contracts; here's the audit trail." That's the wow.

---

### 8. TrialIQ Agents → "Regulatory Intelligence Agent for [non-pharma vertical]"

- **Original ecosystem:** UiPath AgentHack 2025 (Grand Prize "Agent of the Future").
- **What it did:** Multi-agent system that helps pharmaceutical organizations analyze regulatory guidelines, clinical documentation, and approval workflows. Transforms Clinical Trial Data Review (CTDR) by eliminating manual document review. ([UiPath forum](https://forum.uipath.com/t/our-team-trialiq-agents-wins-the-agent-of-the-future-grand-prize-at-uipath-agenthack-2025/5675900))
- **Original tech stack:** UiPath Agent Builder, Maestro, Coded Agents.
- **Why it won:** Specific high-value vertical (pharma regulatory = $200/hr consulting time saved per doc), tangible artifact (annotated regulatory report), real customer pain.
- **Why it ports to Google Cloud Agent Platform:** Replace UiPath with ADK; use **Elastic MCP** for the document index (Elastic is the dominant tech in legal/regulatory RAG). Pivot vertical: pharma is high-prize but consulting-firm-saturated; **financial-services compliance** (SOX, MiFID II) or **product-safety compliance** (FDA 510(k), CE marking) are wider markets.
- **Material differentiator:** **Better protocol composition** — use A2UI (Agent-to-UI protocol) to let the regulatory agent OPEN a structured form in front of the compliance officer where they can co-edit the annotated document live. The original was batch-process; Abu's is conversational + structured-UI. That's the 2026 differentiator.
- **Rebuild time:** 8 days. Document parsing + regulatory grounding is real engineering work.
- **Track fit:** **Elastic** (yellow). Also **MongoDB** if we go vector-only.
- **Risk:** Regulatory domain authenticity is high-bar; without real-feeling docs the demo fails. **Mitigation:** use a publicly-available reg corpus (e.g., SEC EDGAR filings, FDA 510(k) database) as the index.

---

### 9. Voltaros → "Chaos-Engineering Agent for AI Agent Reliability (meta-loop)"

- **Original ecosystem:** Google ADK Hackathon 2025 (gallery featured, not top winner — but exactly the kind of niche-but-loved project that wins partner-specific tracks where judges are domain experts).
- **What it did:** Automated chaos engineering using ADK agents. Stress-tests GKE apps by triggering pod crashes and latency injections via Chaos Mesh-style fault injection. Multiple agents coordinate: scout (find resources to attack), injector (cause the fault), watcher (record what broke), reporter (generate resilience scorecard). ([ADK gallery](https://googlecloudmultiagents.devpost.com/project-gallery))
- **Original tech stack:** ADK + GKE + Chaos Mesh + custom monitoring.
- **Why it won (gallery feature, not top prize):** Strong "agent ACTING not narrating" demo (agent literally breaks things and watches). Unique vertical (SRE / chaos engineering). Hit Pattern B (multi-step autonomous workflow producing a concrete artifact — the resilience report). What it didn't fully hit: Pattern A authenticity at the level of an industry-specific PhD-team project. That's the gap Abu's port closes.
- **Why it ports to Google Cloud Agent Platform:** Same platform — but the PIVOT is from **chaos engineering for distributed systems → chaos engineering FOR AI AGENTS THEMSELVES.** The agent under test is itself an agent. The chaos agent injects LLM-specific faults: malformed tool outputs, latency spikes, hallucinated context, partial MCP server failures, prompt-injection probes, context-window-overflow stuffing. Phoenix observes the test agent's behavior under stress and grades reliability per-fault-class via LLM-as-judge.
- **Material differentiator:**
  - **Meta-recursive wow factor:** "an agent that breaks other agents to make them more resilient." This is the kind of project that wins "Most Creative" categories and gets featured in the Arize blog post-event.
  - **Phoenix MCP integration is best-of-breed:** Phoenix MCP exposes traces, evals, datasets, experiments — exactly what a chaos-for-agents tool needs to read back the test agent's failure modes ([Phoenix MCP server docs](https://arize.com/docs/phoenix/sdk-api-reference/typescript/mcp-server)).
  - **2026 timing:** every team is shipping an agent in 2026 and has zero confidence it'll hold up in prod. This is THE pain point judges feel personally.
  - **OpenInference auto-instrumentation:** Arize's OpenInference instruments Google ADK out of the box (per `partner-arize.md`), so the wiring cost is minimal.
- **Rebuild time:** 6-7 days. The fault-injection harness is small (~12 fault classes, can ship with 4); Phoenix wire-up is `register()` + decorator pattern; the test-target agent is 100 LOC of deliberately-naive customer-support code.
- **Track fit:** **Arize** (green lane per CONTEXT.md §2) — this is THE most Arize-aligned project in this list. The Arize bonus criterion ("agents that use observability data to improve over time") is LITERALLY ChaosLab's core loop. Could also fit **Dynatrace** if pivoted to runtime fault injection instead of semantic faults.
- **Risk:** (a) Niche audience — only AI infra teams care deeply. **Mitigation:** AI infra is what the Arize lane judges DO; they're the buyer. (b) Demo has to land "wow" in 30s. **Mitigation:** open with a deliberately fragile customer-support agent. Chaos agent injects 3 fault classes. Before-chaos-train: agent fails 60% of fault classes. After one ChaosLab loop: 8%. Show the curve. Curve goes brrr. (c) Risk that someone else also picks this angle. **Mitigation:** the recursive meta-twist (Phoenix MCP for self-introspection of the chaos agent itself, not just the agent under test) is a second-order angle few others will land. See §"highest-EV port candidate" below for the full spec.

---

### 10. RiskWise → "Cyber-Supply-Chain Risk Intelligence Agent with Fivetran + Dynatrace dual sourcing"

- **Original ecosystem:** Microsoft AI Agents Hackathon 2025 ($20K Best Overall winner — beat 570 submissions across 18,000 developers).
- **What it did:** Supply chain risk analysis. Continuously monitors geopolitical events, labor conditions, tariffs, logistics disruptions. Surfaces early warnings to analysts via natural-language query interface. Flags risks — from port delays to geopolitical events — that might impact production or delivery. Multi-agent (likely 4-5 agents). ([Microsoft showcase](https://techcommunity.microsoft.com/blog/azuredevcommunityblog/ai-agents-hackathon-2025-%E2%80%93-category-winners-showcase/4415088), [project issue](https://github.com/microsoft/AI_Agents_Hackathon/issues/526))
- **Original tech stack:** Python (AI logic) + Azure AI Agent Service + Semantic Kernel + SQL (data) + React/Next.js front-end.
- **Why it won:** Won Best Overall ($20K) at Microsoft hackathon (568-submission field). Concrete pain (supply chain disruption costs measured in $100M-class events), multi-source intelligence aggregation, real C-suite buyer who already pays for this (Resilinc, Everstream Analytics, Interos, etc. — proven $B+ market). NL query UI = good demo.
- **Why it ports to Google Cloud Agent Platform:** Replace Azure AI Agent Service with ADK + Gemini 3.1 Pro. **Pivot domain from physical supply chain → cyber supply chain.** Why pivot: (a) physical supply chain has commercial competitors with proprietary data feeds Abu can't replicate; (b) cyber supply chain is fresher 2026 pain (post-xz-utils backdoor, post-Pillar registry attacks, post-shai-hulud NPM worm); (c) cyber supply chain data is PUBLIC (CVEs, GitHub Advisory, npm audit, OSV) — Abu can pull it.
- **The architecture:**
  - **Fivetran MCP** to ingest from: NVD CVE feed, GitHub Security Advisory database, npm audit feeds, OSV.dev, Snyk's public advisories, Dependabot alerts.
  - **MongoDB MCP** as the index (Atlas free-tier; subscribe via GCP Marketplace per `partner-mongodb.md`).
  - **Dynatrace MCP** to overlay real runtime telemetry — "is the vulnerable package actually loaded in MY prod?" That's the differentiator from every other CVE-feed-monitor on the market.
  - ADK multi-agent: Discovery (Fivetran-side) → Index (MongoDB-side) → Exposure (Dynatrace-side) → Triage (Gemini reasoning) → Alert.
- **Material differentiator:**
  - **Multi-partner MCP integration:** Fivetran + MongoDB + Dynatrace. Most submissions will use one partner. Very few will compose three well. This is a "platform breadth" signal Pattern D rewards.
  - **Better domain:** cyber-supply-chain risk is 2026's hottest enterprise security pain. Every CISO board update mentions it.
  - **Sharper question:** the agent doesn't just say "CVE-2026-12345 affects log4j-1.2.17"; it says "your prod is loading log4j-1.2.17 on the customer-checkout service, the exploit path is reachable, here's the patch PR." That's the differentiator from `dependabot`.
- **Rebuild time:** 8-9 days (upper limit). Dual-partner MCP is real complexity. Triple-partner is "stretch."
- **Track fit:** **Fivetran** (data ingest is the headline) OR **Dynatrace** (runtime overlay is the headline). Could submit to either. Per CONTEXT.md §2: Fivetran is yellow lane, Dynatrace yellow-green. Dynatrace edges Fivetran on lane-EV.
- **Risk:**
  - (a) cyber supply chain is competitive — incumbents like Snyk, Endor Labs, OX Security are present. Judges might know them.
  - (b) Dual-MCP wiring eats time.
  - (c) Dynatrace needs OneAgent collecting telemetry from a real app (hard in 9 days).
- **Mitigation:**
  - Ship single-MCP first (Fivetran + MongoDB), wire Dynatrace as a stretch goal Day 7+.
  - For Dynatrace, deploy a small "fake prod" demo app (Node.js with intentionally-vulnerable deps) on Cloud Run, instrument with OneAgent, and use that as the "this is what my real prod telemetry looks like" demo target. ~4 hours of setup.
  - Differentiate from Snyk/Endor by stressing the _agentic + runtime-grounded_ combo — they're static or rule-based, ChaosLab-style RiskWise is reasoning over runtime evidence.

---

### 11. PetFitAI → "Real-Time Multi-Modal Health-Signal Agent for SaaS metric monitoring"

- **Original ecosystem:** TiDB AgentX Hackathon 2025 (winner; featured by Devpost; team is Aishwarya Nathani & Nikhil Mankani — same team that won ADK Hackathon APAC with GreenOps, i.e., serial hackathon winners).
- **What it did:** Smart pet collar → Kafka streaming pipeline → TiDB SQL Sink → multi-agent system (vitals agent using Chat2Query API on TiDB; skin-disease agent doing image-vector-search; report agent generating health summaries). Vector embeddings of pet images stored alongside structured time-series vitals. Real-time, multi-modal, owner-facing. ([Devpost](https://devpost.com/software/petfit-ai))
- **Original tech stack:** TiDB (vector + time-series), Kafka, multi-agent ADK-like orchestration, embeddings + Chat2Query API for NL→SQL, Python visualization for report agent.
- **Why it won:** Real-time streaming + multi-modal (vitals + images), tangible artifact (health report), demo-friendly (cute pet collar angle), TiDB-platform-deep (Pattern D platform-breadth signal for TiDB judges).
- **Why it ports to Google Cloud Agent Platform:** Strip the pet domain; keep the _real-time multi-modal streaming health-signal_ pattern. Apply it to **SaaS product-metric monitoring**:
  - Every product event (signup, churn, error, support ticket, screenshot upload) flows through **Pub/Sub** → **MongoDB Atlas** (storing both structured events AND embeddings of error messages + dashboard screenshots).
  - Multi-agent: vitals agent watches MRR / DAU / NPS, anomaly agent watches error logs (semantic search via Atlas Vector Search), screenshot agent processes dashboard screenshots via Gemini Vision, report agent emits weekly summary.
- **Material differentiator:**
  - **Better data:** SaaS metrics > pet health for the Devpost-judging C-suite.
  - **Better domain:** B2B product-led-growth teams pay for this; pet owners don't.
  - **MongoDB Atlas Vector Search** as the index — partner-aligned, and genuinely SOTA for vector + time-series mix in 2026 (Atlas Vector Search GA'd in 2024).
  - **Multi-modal angle:** the agent processes screenshots of dashboards (Gemini Vision) ALONGSIDE structured metrics. "What a PM sees" = the dashboard + the metrics + the support tickets, all at once. Truly multi-modal MongoDB indexing is novel for a hackathon submission.
- **Rebuild time:** 7-8 days. Streaming Pub/Sub pipeline is the real cost.
- **Track fit:** **MongoDB** (RED lane — most-saturated per CONTEXT.md §2). Need a SHARP wedge to stand out.
- **Risk:** RED lane is brutal; "product analytics agent" is competitive (Mixpanel, Amplitude shipping their own AI in 2026). **Mitigation:** lean entirely on the MULTI-MODAL angle. "Every other agent does metrics OR logs OR screenshots. Mine does all three with one vector store." Demo shows agent looking at a screenshot of a churn dashboard + the underlying MRR metric + the most-recent 3 support tickets, then narrating "DAU is down 8% concentrated in the iOS app, support tickets cluster around 'app crashes when uploading photos', recent dashboard screenshot shows the upload-rate-anomaly graph hitting 0 for iOS users." That's a 30-second demo that lands hard.

---

### 11b. ENS-DIVE-Smol convergence note (ETHGlobal pattern)

A pattern across multiple ETHGlobal 2025/2026 finalists is **agent-as-on-chain-identity**: agents have wallets, names (via ENS), reputation, payment rails. This translates to Google Cloud Agent Platform via:

- **GitLab MCP** as identity layer (every dev/agent has a GitLab account → GitLab ID → permissions DAG)
- **AP2** as payment rail
- **A2A** as agent-mesh / discovery

For any GitLab-track refactor, this convergence is worth borrowing — agents that PAY each other (AP2) for sub-task delegation, with identity provenance via GitLab user/group structure, is genuinely 2026-new and impossible at any prior hackathon.

---

### 12. GitLab Guardian Army → "SDLC Multi-Specialist Fleet for AI Agent Repositories (meta-agent angle)"

- **Original ecosystem:** AI in Action 2025 (direct predecessor hackathon).
- **What it did:** 11 specialist agents + 1 BOSS commander + 1 monitoring agent (BUDDY) coordinate code review, security scanning, debugging, testing, docs, deployment on every MR. Zero human input on the auto-flow. ([Devpost](https://devpost.com/software/gitlab-guardian-army-ai-multi-agent-devsecops-system))
- **Original tech stack:** GitLab Duo Agent Platform, YAML, Python.
- **Why it won:** Featured in AI in Action wrap-up (direct hackathon ancestor of Rapid Agent). Hits the "multi-agent orchestration" + "deep partner integration" patterns judges reward.
- **Why it ports to Google Cloud Agent Platform:** Replace GitLab Duo with ADK + Gemini; integrate via **GitLab MCP** (`gitlab.com/api/v4/mcp`) as the partner. Pivot the meta-twist: instead of guarding general repos, **guard AI agent repos specifically** — the BOSS agent reviews MRs for prompt-injection vulns, malicious tool registrations, hallucination test coverage, and Phoenix-eval regression.
- **Material differentiator:** **Better domain (AI repos specifically)**, **A2A protocol** (each specialist agent is independently addressable), **Arize Phoenix MCP wired** for eval-regression-blocking-merge. The recursive "agents that review the AI agents' own MRs" angle is timely — every team is shipping agents in 2026.
- **Rebuild time:** 8-9 days. 11 agents is heavy — can collapse to 5: code, prompt-safety, eval-regression, tool-registry, docs. 5 is enough.
- **Track fit:** **GitLab** (RED lane) — but a sharp angle. Backup: **Arize** if the eval-blocking-merge is the headline.
- **Risk:** Building 5+ agents in 9 days is the upper limit; over-scoped risk. **Mitigation:** ship 3 agents (prompt-safety, eval-regression, code-review) and lean on the meta-angle in pitch.

---

### 13. Quick-scan candidates (not deep-dived but flagged for completeness)

These are projects mined during this research pass that the multiplicative-floor filter killed early. Listed here so a future pass can revisit if Top 5 fall through:

- **Energy Agent AI / WattsWise** (David Babu, ADK Hackathon NA winner) — multi-agent for retail energy customer management with 7 XGBoost models on GCS, BigQuery, SHAP. ([Devpost](https://devpost.com/software/energy-agent-ai)) Port to **Fivetran** as a utility-data-pipeline agent. **Filter kill:** requires actual retail-energy domain knowledge + 100K simulated customer dataset. Score: D=4 / Df=3 / B=2 / T=4 / P=4. Build feasibility floored it.
- **GreenOps** (ADK Hackathon APAC winner) — AI team that audits, forecasts, and optimizes cloud infra for sustainability. FinOps agent + scout + profiler + recommender + forecaster. ([Devpost](https://devpost.com/software/greenops-gzp4aj)) Port to **Dynatrace** since the live telemetry is the data. **Filter kill:** Dynatrace 15-day trial squeeze + needs OneAgent collecting real telemetry from day 1. (Same risk as CONTEXT.md §2's reasoning for ruling Dynatrace out.)
- **Apollo Deep Research Meta Agent** (Microsoft Hack, Best C# Agent) — orchestrates Athena (research engine) and Hermes (analyzer) via Semantic Kernel; self-reflective RAG with PostgreSQL/pgvector. ([Apollo GitHub](https://github.com/manasseh-zw/apollo)) Port to **MongoDB Atlas Vector Search** + ADK. **Filter kill:** "deep research agent" is the single most-shipped pattern in 2026; lane is fully saturated.
- **Konveyor** (Microsoft Hack, Best Python Agent) — knowledge-transfer agent for software-eng onboarding, Semantic Kernel, vector DB. ([Konveyor GitHub](https://github.com/anwarchk/konveyor-AI)) Port to **GitLab MCP** to pull from repo READMEs, MR comments, runbooks. **Filter kill:** needs a real organization's internal corpus to demo authentically; generic-Wikipedia version loses on Pattern A.
- **Province** (AWS Hackathon, tax filing agent) — multi-agent extract/explain/auto-fill IRS forms via Bedrock + Claude 3.5 Sonnet + autonomous FormMapping pipeline. ([writeup](https://aws-agent-hackathon.devpost.com/updates/38140-congratulations-to-the-winners-of-the-aws-ai-agent-global-hackathon)) Port to ADK + **MongoDB MCP** as the structured-extraction store, or **Elastic MCP** as the policy-document index. **Filter kill:** US tax season is in April, not June; demo timing is awkward. Also banned-runtime concern (Claude 3.5 is the brain in the original; replacing with Gemini 3.1 Pro is doable but loses some of the reasoning crispness).
- **EcoLafaek** (AWS Hackathon, waste-management agent in Timor-Leste) — citizen mobile reporting + Bedrock Nova-Pro multi-modal reasoning + AgentCore tool-chaining + real-time pollution-hotspot data viz. Port pattern to civic-tech or municipal data agents on **Fivetran** ingest. **Filter kill:** requires a citizen-reported dataset Abu doesn't have.
- **PatchPilot** (Devpost autonomous AI engineer that reads GitHub issues and ships PRs) ([Devpost](https://devpost.com/software/patchpilot-me96bs)) — port to **GitLab MCP** (the only partner that's a CI/CD platform). **Filter kill:** literally what Copilot Coding Agent / Cursor already do; differentiator has to be VERY sharp. Plus the agent in the original is Claude-powered, which is banned in submitted code.
- **TripCraft AI** (Agno Hackathon honorable mention, AI-powered journey planning by Amit Wani). Port pattern to enterprise travel + expense ops. **Filter kill:** travel-planning is the single most-saturated AI agent demo on the planet; differentiator non-existent.
- **Smol Universe** (ETHGlobal Agentic Ethereum finalist — AI Twitter clones in a virtual world). ([Devpost showcase](https://ethglobal.com/showcase/smol-universe-nqh0z)) **Filter kill (anti-pattern §3):** loses on the rubric's "Potential Impact" weight; toy/cute project in an enterprise-judged hackathon.
- **AIMen** (ETHGlobal finalist — NL → on-chain interaction). **Filter kill:** crypto-native primitive; doesn't translate.
- **Bouncer.ai** (ETHGlobal finalist — token-launch with AI access control via voice-quality scoring). Port pattern to **A2UI voice-gated form** for any compliance flow (KYC interview agent for fintech). **Filter kill:** voice-interview compliance is plausible but execution risk is huge in 9 days; needs voice infra Abu doesn't have set up.

---

## Top 5 refactor candidates ranked

Scoring on the 5 axes (1-5 each), multiplied. Higher = better.

| #   | Candidate                                                      | Demo-ability | Differentiator | Build feasibility | Track fit / EV | Pain sharpness |    Score |
| --- | -------------------------------------------------------------- | -----------: | -------------: | ----------------: | -------------: | -------------: | -------: |
| 1   | **#9 Voltaros → Chaos for AI Agents**                          |            5 |              5 |                 4 |              5 |              4 | **2000** |
| 2   | **#6 ENShell → Prompt-Injection Shell**                        |            5 |              4 |                 4 |              3 |              5 | **1200** |
| 3   | **#3 Particle Physics Agent → Domain-Pivot Compilable-Output** |            4 |              4 |                 5 |              5 |              3 | **1200** |
| 4   | **#4 TradeSage → Hypothesis-Tester for Incident RCA**          |            4 |              4 |                 4 |              5 |              4 | **1280** |
| 5   | **#10 RiskWise → Cyber-Supply-Chain Risk Agent**               |            4 |              5 |                 3 |              4 |              5 | **1200** |

### Per-candidate scoring rationale

**#9 Voltaros → ChaosLab for Agents (2000):**

- Demo-ability 5: agent literally breaks another agent on camera — Pattern C maximum. Before/after curve is visceral.
- Differentiator 5: meta-recursive, multi-protocol-composing, hits the Arize bonus criterion harder than any conceivable submission.
- Build feasibility 4: 4-class fault catalog + Phoenix wire + naive test-agent fits in 6-7 days. -1 for "12 fault classes" being ambitious.
- Track fit 5: PERFECTLY Arize-shaped. Green lane × highest possible alignment with bonus criterion.
- Pain sharpness 4: every team is shipping agents in 2026; -1 because the buyer ("AI infra/SRE-for-agents") is narrower than e.g. "compliance officer."

**#4 TradeSage → Incident-RCA Hypothesis Tester (1280):**

- Demo-ability 4: hypothesis-test pattern is structured; fake-incident demo with 3 competing hypotheses converging on the right one is doable but needs choreography.
- Differentiator 4: A2A parallel-skeptic-agents + Phoenix grading = novel. -1 because the "agent that does RCA" lane has some competition.
- Build feasibility 4: 6 → 3 agent collapse is doable.
- Track fit 5: hits Arize bonus criterion (eval-graded confidence scores ARE Phoenix's product).
- Pain sharpness 4: incident RCA is universal pain across every SaaS team.

**#6 ENShell → Prompt-Injection-Hardened Agent Gateway (1200):**

- Demo-ability 5: live prompt-injection that ATTEMPTS to drop a production table is the most demo-friendly security pitch imaginable.
- Differentiator 4: domain pivot from crypto-wallets → devops-policies is sharp. -1 because "AI safety / agent shell" has commercial entrants (Lakera Guard, Robust Intelligence) — judges aware of these may grade strictness vs novelty.
- Build feasibility 4: policy DAG + tool-call interceptor is small; the GitLab MCP integration is the real cost.
- Track fit 3: GitLab is RED lane (CONTEXT.md §2). Need the angle to overcome saturation. Could re-target to Arize via policy-as-eval framing.
- Pain sharpness 5: prompt injection is THE enterprise-AI fear in 2026.

**#3 Particle Physics Agent → Domain-Pivot Compilable-Output (1200):**

- Demo-ability 4: NL-in, compilable-out is satisfying. Whether it pops in demo depends on the chosen domain.
- Differentiator 4: pattern is portable; the wedge is choosing a domain that's genuinely useful + binary-validatable.
- Build feasibility 5: 6-agent → 3-agent reduction with explicit auto-correction loop is the simplest of the top 5.
- Track fit 5: Arize green lane fits perfectly (validation source is Phoenix evals or partner-MCP).
- Pain sharpness 3: -2 because "compilable X" is abstract; needs a domain that makes the pain concrete. K8s manifests = 5; LaTeX = 3.

**#10 RiskWise → Cyber-Supply-Chain Risk Agent (1200):**

- Demo-ability 4: dashboard of risks lighting up live as Fivetran pulls fresh CVE data is solid; -1 because the agent action ("alert") isn't as visceral as ChaosLab's chaos.
- Differentiator 5: multi-partner MCP composition (Fivetran + Dynatrace) is rare. Cyber-supply-chain is 2026's hot domain post-xz-utils, post-shai-hulud.
- Build feasibility 3: dual-MCP wiring is real complexity. -2 risk of overrun.
- Track fit 4: Fivetran (yellow) or Dynatrace (yellow-green); both reasonable.
- Pain sharpness 5: every CISO in 2026 lost sleep over supply-chain.

### Honorable mentions just outside top 5

- **#1 SalesShortcut-fintech (score 720):** Demo-ability 4, Diff 3, Build 4, Track 3, Pain 5. Differentiator weakness pulls it down; "SDR but warmer" feels iterative not novel. Pain is real though.
- **#12 Guardian Army for AI repos (960):** Demo-ability 4, Diff 4, Build 3, Track 4, Pain 5. Build feasibility floored at 3 (5+ agents in 9 days is upper limit).
- **#5 AegisAgent → AP2-paid claim agent (900):** Demo-ability 4, Diff 5, Build 3, Track 3, Pain 5. AP2 is the win; Elastic trial squeeze is the risk.

### Filtered out by multiplicative floor (any axis ≤ 2)

- **#2 Edu.AI → publisher pivot:** build feasibility 2 (8-agent original is heavy; even reduced to 3 the B2B publisher data is hard to fake).
- **#7 DIVE → enterprise data QA:** pain sharpness 3 (data quality is real but the agent angle vs Monte Carlo / Anomalo is fuzzy).
- **#8 TrialIQ → regulatory:** build feasibility 2 (regulatory authenticity bar is too high in 9 days for a solo dev who isn't in regulatory).
- **#11 PetFitAI → SaaS metric monitoring:** track fit 2 (MongoDB RED lane × competing with Mixpanel/Amplitude AI), demo-ability 3 (the streaming pipeline doesn't demo as a curve, just as a dashboard).

---

## The single highest-EV port candidate

### **#9 Voltaros → "ChaosLab for Agents: a meta-recursive agent that hardens other agents via fault injection, graded by Phoenix"**

**Pitch sentence (the Q2 wedge from `07-pre-commit-checklist.md`):**

> _"ChaosLab is an Arize-graded chaos-engineering agent: every team shipping an agent in 2026 lacks confidence the agent will hold up in prod; ChaosLab autonomously injects 12 classes of LLM-specific faults (malformed tool outputs, latent context poisoning, MCP server flakiness, prompt-leak attempts), records every span in Phoenix, runs eval-as-judge on the response, and emits a per-fault-class resilience score with a hardening recipe."_

**Target track:** **Arize**. The bonus criterion explicitly rewards agents that "use observability data to improve over time" — ChaosLab IS that loop.

**Partner MCP:** **`@arizeai/phoenix-mcp`** as the primary. Maybe **GitLab MCP** as secondary to register hardening recipes as PRs against the agent under test.

**What the rebuilt agent does end-to-end:**

1. **Onboard:** user points ChaosLab at any ADK-built agent (or via A2A, any agent). ChaosLab introspects the agent's tool registry + prompt template via Phoenix MCP.
2. **Fault catalog:** ChaosLab generates a per-agent fault catalog — for each tool, what malformed input could it receive? for each prompt step, what injection class applies?
3. **Inject:** ChaosLab spawns parallel test runs (A2A protocol), each with one fault injected. Phoenix traces every span.
4. **Grade:** Phoenix LLM-as-judge eval scores every output against correctness, refusal-when-appropriate, and graceful-degradation rubrics.
5. **Diagnose:** ChaosLab reads the failed spans back via Phoenix MCP, clusters failure modes, identifies systemic weaknesses.
6. **Harden:** generates a markdown "hardening recipe" (prompt edit + tool-validation code + new eval-regression dataset) and optionally opens a PR via GitLab MCP.
7. **Re-test:** runs the same fault battery against the patched agent. Plots before/after resilience curve.

**The material differentiator:**

- **Cross-ecosystem novelty:** chaos-eng-for-agents has been thought-about (Anthropic talks about agent red-teaming; OpenAI evals exist) but nobody has shipped the _closed-loop autonomous fault-inject + Phoenix-grade + auto-harden_ pattern.
- **Multi-protocol composition:** MCP (Phoenix wires) + A2A (parallel test agents) + UCP (the hardening recipe is a structured context object).
- **Demo wow:** the before/after curve is visceral — agent fails 60% of fault classes, after one ChaosLab loop it fails 8%. Plus a live "watch the chaos agent break the agent" subscreen.
- **Recursive judging fit:** Arize judges are the people most likely to value chaos-eng-for-LLMs as a primitive. They'll feel seen.

**What the 3-min demo shows:**

- **0:00-0:20** — "Every team is shipping an agent in 2026. Every team has zero confidence it'll hold up in prod." Cut to a screenshot of an "AI agent caused a $1M loss" headline. Pain.
- **0:20-0:40** — A naive customer-support agent runs. Looks fine. ChaosLab points at it.
- **0:40-1:30** — Split screen: left, the agent under test, drowning in 12 fault classes (malformed tool outputs flash red, prompt-injection attempts in green). Right, Phoenix lighting up with traces, evals red. "60% fail rate."
- **1:30-2:20** — ChaosLab reads the failed traces (Phoenix MCP), clusters into 4 failure modes, autonomously edits the agent's prompt + adds 3 input validators, opens a PR via GitLab MCP.
- **2:20-2:50** — Same fault battery runs again on the patched agent. 8% fail rate. Curve goes brrr.
- **2:50-3:00** — "ChaosLab. Phoenix-graded chaos-eng for agents. Built on ADK." Logo + GitHub link.

**The architecture in one paragraph:**

ChaosLab runs on **Cloud Run** as an ADK-built agent with Gemini 3.1 Pro as the brain (reasoning depth needed for fault catalog generation + clustering). It exposes itself as an **A2A endpoint** so other agents (including itself) can be invoked in parallel. The **Phoenix MCP server** (`@arizeai/phoenix-mcp` via `npx`) is registered as a tool source via ADK's `MCPToolset` — this gives ChaosLab access to its own (and the test agent's) traces, datasets, and experiments. The **target-agent registration** flow accepts any ADK agent URL or A2A endpoint; OpenInference auto-instruments incoming agents to emit traces to the same Phoenix project. The **fault-injection layer** is a Python module with 12 fault classes (4 shipped); each fault is a decorator-pattern wrapper around the test agent's tool registry. The **eval layer** uses Phoenix's LLM-as-judge with three rubrics (correctness, refusal-when-appropriate, graceful-degradation). The **hardening layer** reads failed spans back, asks Gemini 3.1 Pro to cluster + propose patches, and (optional stretch goal) opens a PR via the GitLab MCP server (`gitlab.com/api/v4/mcp`).

**The 5-line wedge sentence (for `07-pre-commit-checklist.md` Q2):**

> ChaosLab is a Phoenix-graded chaos-engineering agent for AI agents. Point it at any ADK agent or A2A endpoint, and it autonomously injects 12 classes of LLM-specific faults (malformed tool outputs, latent prompt injections, context-poisoning, MCP server flakiness), records every span in Phoenix, runs eval-as-judge per-fault-class, then reads failed traces back via the Phoenix MCP server, clusters the failures, and opens a hardening PR on GitLab. Before/after resilience curve in the same dashboard. The Arize bonus criterion says "agents that use observability data to improve over time get bonus consideration" — ChaosLab IS that loop, applied to OTHER agents.

**Why this wins Arize (predicted):**

- Hits **Pattern A** (specific role: AI infra/SRE for agents). Sharp.
- Hits **Pattern B** (6+ step autonomous loop, real artifact = hardened agent + PR).
- Hits **Pattern C** (agent literally breaks another agent on camera — pure spectacle).
- Hits **Pattern D** (ADK + Phoenix + GitLab MCP + Cloud Run + A2A = breadth).
- Hits the **Arize bonus criterion** (uses observability to improve over time) BETTER than any submission likely to.

**Risk:**

- **Scope risk:** 12 fault classes is ambitious. **Mitigation:** ship with 4 fault classes (malformed tool output, latency injection, prompt-leak probe, context-poisoning); 4 is enough for the demo curve to look impressive.
- **Demo target risk:** the "agent under test" has to be plausible enough that breaking it feels meaningful. **Mitigation:** ship a deliberately-naive customer-support agent (Gemini + 3 tools, no input validation) as the demo subject; that's 1 hour of work, max.
- **Judging risk:** if the Arize lane somehow becomes red (CONTEXT.md §2 has it as green prediction, not certainty), the meta-agent angle is so strong it still wins on differentiator.

---

## Anti-patterns: 5 patterns of bad refactor candidates to avoid

### 1. Projects that depended on a blockchain primitive that doesn't translate

E.g., **YieldSeeker** (ETHGlobal — AI yield-finder on Ethereum) and **Streme.fun** (AI token launcher) lean on on-chain settlement and crypto-asset trading. Without crypto primitives (smart contracts, wallets, on-chain composability), they collapse into "another LangChain trading bot," which is banned (LangChain-as-primary-orchestrator) AND saturated. **Skip.**

### 2. Projects that need a specific proprietary dataset Abu can't access

E.g., **Konveyor** (Microsoft hack — knowledge transfer agent for software-eng onboarding) requires a "real organization's internal docs corpus." Without that, the demo is a Wikipedia knowledge transfer agent. Generic. Loses on Pattern A (no specific domain authenticity). Same problem with **WattsWise/Energy Agent AI** without the 100K simulated customers + 7 XGBoost models built on real retail energy data. **Skip unless** you happen to have a real corpus.

### 3. Projects that win on cuteness or zeitgeist, not pain

E.g., **Smol Universe** (ETHGlobal — AI Twitter clones in a virtual world) and **Outdraw AI** (Gemini Comp — game where humans draw to confuse AI). Fun, viral-worthy, but the Rapid Agent rubric weights "Potential Impact" + "Idea Quality" heavily (per `01-prizes-tracks.md`). Toy projects lose to enterprise-pain projects on this rubric. **Skip.**

### 4. Projects whose original tech stack is the entire moat

E.g., **PetFitAI** (TiDB hackathon — heavily leans on TiDB's Chat2Query + native vector search). The original's competitive edge IS the data primitive. Porting away means re-architecting around MongoDB's Atlas Vector Search — doable but you're trading TiDB's moat for MongoDB's, and the result feels generic. If the original "wow" was a vendor-specific feature, the refactor has to find a NEW wow, not just transplant. **Skip** unless the wow translates cleanly.

### 5. Projects that require domain-specific authenticity Abu can't fake in 9 days

E.g., **AegisAgent** (insurance/compliance) and **TrialIQ** (pharma regulatory). The judges will sniff out demo-quality from real-domain-knowledge. Insurance policy interpretation that's clearly hallucinated will rate worse than a sparser, more honest agent in a domain Abu actually knows. **The "Particle Physics Agent" team had PhDs in particle physics.** If you don't have the domain inside your head, pick a domain you do — or pivot. Mitigation: pick a domain Abu has lived (blockchain, data infra, agent infra). That's #9 Voltaros (agent infra). That's why it wins this list.

---

## Appendix A: Cross-ecosystem patterns that consistently win (extracted)

After mining ~40 winning + finalist projects across 9 hackathons, four cross-ecosystem patterns recur. These are independent of the specific Pattern A-D notes in `05-prior-winners.md`; they describe what the WINNERS' SHAPES have in common.

### Shape 1: Closed-loop self-improvement

Winners ship agents that not only ACT but also OBSERVE their own actions and IMPROVE. SalesShortcut's Lead Manager Agent tracks conversion and re-tunes outreach copy. GreenOps' forecaster feeds the recommender. Edu.AI's evaluator feeds the study-planner. **The 2026 Rapid Agent Hackathon's Arize bonus criterion ("agents that use observability data to improve over time") makes this shape PARTICULARLY rewarded.** Abu's #9 ChaosLab is the purest expression of this.

### Shape 2: Multi-step pipeline with VISIBLE handoffs

ADK Hackathon judges explicitly rewarded "visible orchestration of multiple steps" (per `05-prior-winners.md`). SalesShortcut's 4-step pipeline, TradeSage's 6-agent pipeline, AegisAgent's debate-then-resolve pattern — all SHOW the agents handing off, often with visible labels. **Implication for Abu's submission:** the demo video should make the agent-to-agent handoffs VISUALLY CLEAR (animated arrows, color-coded agents, etc.).

### Shape 3: Authoritative-source validation

Particle Physics Agent validates against the Particle Data Group database. AegisAgent validates against the policy corpus. TrialIQ validates against regulatory guidelines. **The winning pattern is NL-to-validated-output, where validation pulls from an authoritative source.** Phoenix MCP, Elastic MCP, and GitLab MCP all can serve as the authoritative-source side of this loop. Abu's port should explicitly name what the authoritative source is.

### Shape 4: Production-feel polish AND a domain-specific moat

Winners feel like "v1 of a startup," not "hackathon prototype." Edu.AI had nexora-ai.de domain. ArthaRaksha had the Indian-fraud-prevention pitch. Even gallery-tier projects like Voltaros had Chaos-Mesh integration that screamed "engineer wrote this." **Implication:** Abu's submission needs (a) custom domain, (b) clean architecture diagram, (c) Cloud Run deployment URL that just works, (d) sensible README, (e) a 30-sec opening pitch that conveys domain authenticity. None of this is optional.

---

## Appendix B: The 5 open protocols → refactor leverage map

The hackathon's 5 open protocols (MCP, A2A, A2UI, AP2, UCP) are 2026-new. Every refactor in this file can claim novelty by composing protocols the original couldn't. Mapping:

| Protocol                           | What it enables                                         | Refactor candidates that benefit                                                                                                                                                  |
| ---------------------------------- | ------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **MCP** (Model Context Protocol)   | Tool-server interop                                     | All 12 candidates — required by hackathon rules anyway.                                                                                                                           |
| **A2A** (Agent-to-Agent)           | Parallel agent invocation, agent-discovery, agent-mesh  | #4 TradeSage (parallel bull/bear agents), #9 Voltaros/ChaosLab (parallel fault-injection runs), #12 Guardian Army (specialist fleet), #7 DIVE (swarm consensus)                   |
| **A2UI** (Agent-to-UI)             | Agent renders structured UI components, not just text   | #8 TrialIQ (regulatory officer co-edits annotated doc), #5 AegisAgent (claim adjuster co-edits the decision), #1 SalesShortcut (sales rep approves outreach in a structured form) |
| **AP2** (Agent Payments Protocol)  | Agent can issue + receive payments inline               | #1 SalesShortcut (charge for the proposal), #5 AegisAgent (disburse claim), #10 RiskWise (auto-pay for premium threat intel feeds)                                                |
| **UCP** (Unified Context Protocol) | Standardized context object passed between agents/tools | #6 ENShell (policy = UCP-formed context), #12 Guardian Army (each specialist gets a UCP-shaped task brief), #9 ChaosLab (hardening recipe is a UCP artifact)                      |

**Strategic implication:** mentioning protocol composition in the wedge sentence is cheap differentiation. Most submissions will use only MCP. Submissions that use MCP + A2A + one of (A2UI / AP2 / UCP) signal "this person read the platform docs all the way through." That's a 2026-fresh shibboleth the judges will notice.

---

## Appendix C: 9-day build cadence for the top candidate (#9 ChaosLab)

If Abu commits to ChaosLab Day 0 (2026-06-02 today), here's the back-of-envelope cadence to hit the 2026-06-11 14:00 PT deadline. Lifted patterns from `02b-gemini-enterprise-agent-platform.md` decision matrix and `02a-google-cloud-stack.md` ADK quickstart.

| Day | Date       | Focus                                 | Concrete deliverable                                                                                                                                              |
| --: | ---------- | ------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
|   0 | 2026-06-02 | Spec lock + scaffold                  | Q1-Q7 from `07-pre-commit-checklist.md` answered. Repo init. ADK installed. `$100 GCP credit` claimed (deadline 06-04). Phoenix Cloud account live.               |
|   1 | 2026-06-03 | Naive target agent + Phoenix wiring   | Customer-support agent (3 tools, no validation) on Cloud Run. OpenInference auto-instrumented. First traces flowing into Phoenix Cloud.                           |
|   2 | 2026-06-04 | Fault catalog v1 (2 fault classes)    | Malformed-tool-output decorator + prompt-injection probe. Run target agent through each fault 10x. Phoenix shows red.                                             |
|   3 | 2026-06-05 | Phoenix MCP wired + eval-as-judge     | `@arizeai/phoenix-mcp` registered via ADK MCPToolset. ChaosLab can list spans, fetch traces. 3 LLM-as-judge eval rubrics deployed. Per-fault-class score visible. |
|   4 | 2026-06-06 | Add 2 more fault classes + clustering | Context-poisoning + MCP-server-flakiness faults. ChaosLab clusters failures using Gemini 3.1 Pro.                                                                 |
|   5 | 2026-06-07 | Hardening recipe generator            | ChaosLab reads failed spans → generates prompt edit + tool-validation code patch. Saves to artifact storage.                                                      |
|   6 | 2026-06-08 | Re-test loop + UI                     | Patched-agent re-test. Before/after dashboard (Streamlit or Next.js). Resilience curve plotted.                                                                   |
|   7 | 2026-06-09 | GitLab MCP wire (stretch) + polish    | Optional: open PR via GitLab MCP. Custom domain, README, architecture diagram.                                                                                    |
|   8 | 2026-06-10 | Demo video shoot + cuts               | Record the 3-min demo. Tight, agent-acting-not-narrating per Pattern C.                                                                                           |
|   9 | 2026-06-11 | Submit + safety margin                | Submit by 12:00 PT (2h margin before 14:00 PT).                                                                                                                   |

**Critical-path risks per day:**

- **Day 1:** ADK + Phoenix wiring is the riskiest single step. Mitigation: copy from `partner-arize.md` §4 directly; OpenInference instruments ADK automatically.
- **Day 3:** Phoenix MCP via `npx` from inside an ADK runtime on Cloud Run — keep-alive behavior is UNVERIFIED per CONTEXT.md §7 OQ-3. Mitigation: test locally first; fall back to stdio if Streamable HTTP misbehaves.
- **Day 6:** Resilience curve must look real, not synthetic. Mitigation: real 30-injection runs, not handpicked.

**What gets cut if Abu is behind on Day 5:**

- GitLab MCP wire-up (Day 7) → cut first; hardening recipe becomes a Markdown artifact instead of a PR.
- 4th fault class (Day 4) → cut second; demo runs with 3 fault classes still hits the curve.
- Custom domain (Day 7) → cut third; rapid-agent-chaoslab.cloudshell.dev URL works.

**What does NOT get cut, ever:**

- Phoenix wiring (the entire Arize differentiator)
- Before/after resilience curve in the demo (the wow moment)
- 3-min demo video edit (Pattern C is mandatory for winning)

---

## Final note

The shortest path from this file to the wedge sentence (`07-pre-commit-checklist.md` Q2) is **#9 Voltaros → ChaosLab for Agents**, submitted to the **Arize** track. This is the recommended commit.

Second-best if Abu wants to bail from the meta-recursive lane: **#3 Particle Physics → Compilable-Output domain pivot**, also Arize (pick a domain like "Kubernetes manifest agent validated by Dynatrace runtime").

Third-best if Abu wants to move to Fivetran's data-warm lane: **#10 RiskWise → Cyber-Supply-Chain Risk Agent**, Fivetran.

All three are 1-line away from a Q2 wedge sentence. The rest of the file is back-pocket if these three feel wrong after Abu reads `partner-arize.md` end-to-end.

**Synthesis on the ecosystem-refactor alpha applied here:** Abu's prior pattern (rebuild winners from other ecosystems) is BLUNTED slightly by the fact that the Rapid Agent Hackathon's direct predecessor (ADK Hackathon 2025, AI in Action 2025) shares Google's exact judging culture — so the "highest signal" winners to study are IN-ECOSYSTEM (SalesShortcut, Edu.AI, TradeSage, Particle Physics, Voltaros), not OUT-OF-ECOSYSTEM. The cross-ecosystem mining still surfaces useful patterns (the Microsoft hackathon's "RiskWise" enterprise shape, the ETHGlobal "ENShell" safety angle, the UiPath "TrialIQ" regulatory shape, the AWS "AegisAgent" claim-decision shape) — and the BEST refactor candidate (#9 ChaosLab) is meta-loop pattern from a Voltaros gallery-tier project that wasn't a winner but had a winnable shape if pushed harder. This is the standard "find the project that almost won, find why it didn't, fix that" play. ChaosLab is the project Voltaros could have been if pointed at agents instead of pods. That's the alpha.

**Downstream:** when this file feeds into `sahil-idea-generator` or `sahil-novelty-gate`, the chained question is: "is there an ETHGlobal project from 2024-2025 that shipped 'chaos eng for AI agents' specifically?" My searches suggest no — the closest is `deepankarm/agent-chaos` on GitHub (a research repo, not a hackathon submission). Confirm via novelty-gate. If clean, ChaosLab is the build target.

---

## Sources

- [ETHGlobal Agentic Ethereum 2025 finalists — X announcement](https://x.com/ETHGlobal/status/1890448806975795550)
- [ETHGlobal Cannes 2026 finalists — crypto.news](https://crypto.news/ai-agents-privacy-and-prediction-markets-define-ethglobal-cannes-2026-finalists/)
- [ADK Hackathon results blog](https://cloud.google.com/blog/products/ai-machine-learning/adk-hackathon-results-winners-and-highlights/)
- [Microsoft AI Agents Hackathon 2025 winners showcase](https://techcommunity.microsoft.com/blog/azuredevcommunityblog/ai-agents-hackathon-2025-%E2%80%93-category-winners-showcase/4415088)
- [AWS AI Agent Global Hackathon winners update](https://aws-agent-hackathon.devpost.com/updates/38140-congratulations-to-the-winners-of-the-aws-ai-agent-global-hackathon)
- [UiPath AgentHack 2025 — TrialIQ grand prize](https://forum.uipath.com/t/our-team-trialiq-agents-wins-the-agent-of-the-future-grand-prize-at-uipath-agenthack-2025/5675900)
- [TiDB AgentX Hackathon 2025 — PetFitAI](https://devpost.com/software/petfit-ai)
- [Agno Global Agent Hackathon May 2025 winners](https://www.agno.com/blog/global-agent-hackathon-winners)
- [AI in Action GitLab innovations — Pipeline Doctor + Guardian Army](https://about.gitlab.com/blog/ai-in-action-hackathon-celebrating-the-gitlab-innovations/)
- [SalesShortcut Devpost](https://devpost.com/software/salesshortcut) + [Medium writeup](https://medium.com/@sernur213/salesshortcut-building-an-autonomous-ai-sales-team-with-multi-agent-ai-architecture-using-google-e794c2c72152)
- [Edu.AI Devpost](https://devpost.com/software/edu-ai-multi-agent-educational-system-for-brazil)
- [Particle Physics Agent Devpost](https://devpost.com/software/particle-physics-agent)
- [TradeSage AI Devpost](https://devpost.com/software/tradesage-ai) + [Medium](https://medium.com/google-cloud/building-tradesage-ai-a-multi-agent-trading-analysis-platform-with-googles-agent-development-kit-d14ec7c381e1)
- [Energy Agent AI Devpost](https://devpost.com/software/energy-agent-ai)
- [GreenOps Devpost](https://devpost.com/software/greenops-gzp4aj)
- [GitLab Guardian Army Devpost](https://devpost.com/software/gitlab-guardian-army-ai-multi-agent-devsecops-system)
- [bouncerAI ETHGlobal showcase](https://ethglobal.com/showcase/bouncer-ai-1sd06)
- [PVPVAI ETHGlobal showcase](https://ethglobal.com/showcase/pvpvai-d66a8)
- [Synapze ETHGlobal showcase](https://ethglobal.com/showcase/synapze-vijh5)
- [Smol Universe ETHGlobal showcase](https://ethglobal.com/showcase/smol-universe-nqh0z)
- [Konveyor — Microsoft Hackathon issue](https://github.com/microsoft/AI_Agents_Hackathon/issues/645)
- [Apollo Deep Research — Microsoft Hackathon issue](https://github.com/microsoft/AI_Agents_Hackathon/issues/681) + [Apollo GitHub](https://github.com/manasseh-zw/apollo)
- [RiskWise — Microsoft Hackathon issue](https://github.com/microsoft/AI_Agents_Hackathon/issues/526)
- [Phoenix MCP server docs (Arize)](https://arize.com/docs/phoenix/sdk-api-reference/typescript/mcp-server)
- [Fivetran MCP official repo](https://github.com/fivetran/fivetran-mcp)
- [GitLab official MCP endpoint](https://gitlab.com/api/v4/mcp)
- [Phoenix Cloud (free tier)](https://app.phoenix.arize.com)
- Internal: `CONTEXT.md`, `05-prior-winners.md`, `06-hidden-field.md`, `07-pre-commit-checklist.md`, `partner-arize.md`, `partner-fivetran.md`, `partner-dynatrace.md`
