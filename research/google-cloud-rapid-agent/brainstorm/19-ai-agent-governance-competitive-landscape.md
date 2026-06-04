# AI Agent Governance / Audit Competitive Landscape — 2026-06-04

**Research date:** 2026-06-04
**Scope:** Who is selling "AI agent governance / audit / compliance / insurance" RIGHT NOW (category emerged in last ~6 months)
**Purpose:** Identify whitespace for ChaosLab-reframed-as-AI-Trust-Auditor positioning

---

_Profiles will be added incrementally as research completes. Final synthesis at bottom._

---

## Tier 1 — Deep Profiles

### Klaimee

- **Founded:** 2026 (YC Spring 2026 / P26 batch)
- **Funding stage + latest round:** YC seed (standard YC deal, undisclosed beyond standard YC check). 2 employees, SF-based.
- **What their product ACTUALLY does (1 paragraph, plain English):** Klaimee sells liability insurance specifically for AI agents — the kind of coverage that traditional E&O ("errors & omissions") and cyber insurance policies are now actively carving OUT. Their underwriting flow has three blocks: (1) a public-data scan of the deploying company; (2) a 30-question governance questionnaire about the agent; (3) behavioral testing where they fire 100+ probes at the agent to map its failure modes. Output is a liability policy + financial guarantee + a "certification" document + procurement paperwork, delivered in <24h. So they're underwriting agent risk by lightly red-teaming it themselves, then selling the policy.
- **Who buys it (named role + company shape):** Risk / Procurement / GC at mid-market and enterprise companies deploying AI agents in production — particularly verticals where agents touch money (lending, hiring decisions, contract generation, financial actions). The procurement angle is real: enterprises require liability coverage before they'll let a vendor's agent into their stack, and Klaimee is targeting BOTH the deploying company AND vendors who need to satisfy that procurement gate.
- **Pricing model (if visible):** Not publicly disclosed. Site does not show pricing — insurance-style "talk to us" model. Quote-based after underwriting.
- **Their explicit positioning vs other AI safety/audit tools:** They are NOT positioning as a guardrails / observability tool. Positioning is "the insurance carrier" — they sit on the financial-coverage side. Their wedge: Berkshire/Chubb/Travelers got state approval (filings July 2025, effective Jan 2026) to EXCLUDE AI agent liability from standard commercial policies. Klaimee fills that exclusion. Auditing is incidental — it's underwriting due diligence, not the product.
- **Strong points (their moats):** (a) Real insurance product, not a SaaS posing as one — implies actual capital / fronting carrier (though unverified, see Mount note below). (b) YC distribution. (c) Forced-by-regulation tailwind — every commercial AI deployer needs SOMETHING to fill the exclusion gap. (d) The certification artifact doubles as a procurement door-opener for vendors.
- **Gaps (what they DON'T do that someone could):** (a) No continuous monitoring — the 100-probe assessment is point-in-time at underwriting. Agent behavior drifts; their evidence does not. (b) Their "certification" is internal/unbranded — not a recognized industry standard, no auditor independence. (c) They have a conflict of interest: same company that audits is selling the insurance, so the rigor of their probes is bounded by what makes their book underwritable. (d) Their probes are likely lightweight by hackathon standards — 100 probes vs. systematic chaos engineering on a Phoenix trace tree is a different thing entirely.
- **URLs:**
  - Website: https://www.klaimee.ai/ (also https://www.klaimee.co/ — both surface as live)
  - YC profile: https://www.ycombinator.com/companies/klaimee
  - LinkedIn launch: https://www.linkedin.com/posts/y-combinator_klaimee-yc-p26-is-the-insurance-for-your-activity-7457428900369846272-zOB6
- **Recent signal (last 90 days):** YC P26 batch launch ~Feb 2026; LinkedIn / X announcement push end of Feb 2026. Founders: Ines Boutemadja, Julien Catonnet. No press hires / Series A announced as of 2026-06-04.

---

### Mount

- **Founded:** 2026 (YC Spring 2026 / P26 batch)
- **Funding stage + latest round:** YC standard check (closed March 2026). Sam Altman publicly endorsed on YC Launches page. Actively hiring GTM, AI engineering, underwriting.
- **What their product ACTUALLY does (1 paragraph, plain English):** Mount is the second YC-backed AI agent insurance carrier. Pitch is "secure, then insure": they scan and red-team the customer's agent workflow, work with the customer to reduce failure modes, then write a liability policy on the residual risk. Coverage triggers: unauthorized actions, erroneous outputs, data misuse, prompt manipulation. Positioning is closer to "we sell remediation + risk transfer as a bundle" rather than just an insurance product.
- **Who buys it (named role + company shape):** Same buyer cluster as Klaimee — Risk officers / CISO / GC at enterprises deploying production agents in regulated workflows. Founders are coming at it from a cyber-insurance-evolution angle ("AI insurance is the new cyber insurance" — their explicit framing on the blog).
- **Pricing model (if visible):** Not publicly disclosed. Quote/underwriting model.
- **Their explicit positioning vs other AI safety/audit tools:** "AI insurance is the new cyber insurance" — explicit analogy to how cyber insurance evolved as a coverage category after major insurers started carving out cyber from commercial. They want to BE the standalone AI coverage line. Differs from Klaimee in framing: Mount foregrounds the workflow security / remediation, Klaimee foregrounds the speed-of-cert-issuance.
- **Strong points (their moats):** (a) Sam Altman endorsement is a real distribution moat in YC-land — buyers and investors will both bias toward them. (b) Same regulatory tailwind as Klaimee — AIG, Great American, WR Berkley AI carve-outs effective Jan 2026. (c) Workflow-security-then-insurance bundle is stickier than pure underwriting because they touch the agent code.
- **Gaps (what they DON'T do that someone could):** (a) Carrier status undisclosed — no public regulatory filings, no fronting carrier or reinsurance partnership surfaced. If they're a fronted MGA they're at the mercy of the fronting carrier's appetite. This is a real risk for buyers. (b) Same point-in-time audit problem as Klaimee. (c) Same conflict-of-interest as Klaimee — auditor and underwriter are the same shop. (d) Not framing themselves as an independent auditor — so the "evidence" they produce is not portable to a regulator or to a procurement team that doesn't trust the carrier.
- **URLs:**
  - Website: https://mount.insure/
  - Product page: https://mount.insure/insurance
  - Blog framing: https://mount.insure/blogs/ai-insurance-is-the-new-cyber
  - YC profile: https://www.ycombinator.com/companies/mount
  - YC X announcement: https://x.com/ycombinator/status/2058956261132222917
- **Recent signal (last 90 days):** Public launch May 22, 2026 (founders Fabian Amherd, John Bachmann). Founderland coverage same week. Actively hiring as of June 2026.

---

### WSO2 Agent Manager

- **Founded:** WSO2 founded 2005 (Sri Lanka / US enterprise middleware co); Agent Manager beta launched May 5, 2026
- **Funding stage + latest round:** WSO2 is a mature open-source middleware company — acquired by EQT in March 2024 ($600M+ deal). Agent Manager is a product launch, not a separate company.
- **What their product ACTUALLY does (1 paragraph, plain English):** Agent Manager is an OPEN CONTROL PLANE for enterprise AI agents — think "Kubernetes for agents." Five capabilities: (1) federated management across frameworks (LangChain, ADK, CrewAI, custom) and environments, (2) agent identity + access delegation (an agent gets its own OAuth-style identity it can use to call APIs on behalf of a user), (3) centralized governance/guardrails with policy enforcement, (4) end-to-end tracing/visibility, (5) Kubernetes-native runtime with isolation and lifecycle controls. Released Apache 2.0 — explicitly anti-vendor-lock-in. GA targeted June 2026.
- **Who buys it (named role + company shape):** Platform engineering / SRE leads at Fortune-2000 enterprises already running WSO2 API Manager or Choreo. The buyer is the central platform team trying to bring order to "agent sprawl" — multiple business units each deploying their own LangChain / ADK agents with no shared identity, audit log, or policy engine.
- **Pricing model (if visible):** Apache 2.0 open source for the runtime. WSO2's monetization is via Choreo (their managed cloud) and enterprise support contracts. Pricing for managed/support not publicly listed — enterprise sales model.
- **Their explicit positioning vs other AI safety/audit tools:** Positioned as INFRASTRUCTURE, not audit. Cites Gartner ("40% of agentic AI projects will be canceled by 2027 due to insufficient risk controls"). They want to be the API Manager equivalent for the agent era. Not competing with insurance plays — competing with each cloud provider's "agent platform" pitch (Vertex Agent Engine, Bedrock Agents, Azure AI Foundry).
- **Strong points (their moats):** (a) Existing WSO2 enterprise install base — easy upsell. (b) Apache 2.0 license is a wedge against cloud-provider lock-in (Vertex / Bedrock are walled gardens). (c) Identity/access for agents is a hard problem and they own it natively (WSO2 Identity Server). (d) Kubernetes-native fits big-enterprise platform stories.
- **Gaps (what they DON'T do that someone could):** (a) Beta product — much "visibility and traceability" is brochure-grade right now. (b) Heavy infrastructure lift — small teams won't deploy a control plane. (c) No emphasis on systematic fault injection / chaos / pre-prod failure testing — they catch issues at policy-enforcement time, not in pre-prod. (d) No explicit compliance/audit-evidence artifact — they generate traces, but no "here's your SOC 2 / ISO 42001 evidence package" output.
- **URLs:**
  - Press release: https://wso2.com/about/news/wso2-launches-agent-manager/
  - Product page: https://wso2.com/agent-platform/agent-manager/
  - SiliconANGLE coverage: https://siliconangle.com/2026/05/05/wso2-launches-agent-manager-help-enterprises-tame-ai-agent-sprawl/
- **Recent signal (last 90 days):** Beta launch May 5, 2026. WSO2Con North America May 20-22 in Austin showcased it. GA planned June 2026. Also launched "Agent Identity" + forward-deployed engineers program same week.

---

### CORAS.ai

- **Founded:** CORAS founded 2014 (originally CorasCloud, work-management for DoD); rebranded / refocused as CORAS.ai in 2024-2025; Agentic AI Reporting capabilities released May 5, 2026
- **Funding stage + latest round:** Private; funding details not in public sources surfaced. Per Crunchbase profile (https://www.crunchbase.com/organization/corascloud) — not a VC-funded growth-stage company; bootstrapped/services-funded with government contracts.
- **What their product ACTUALLY does (1 paragraph, plain English):** CORAS sells the only IL5-certified, FedRAMP-High, NIPR/SIPR-deployable agentic AI decision intelligence platform to the US Department of Defense (now "Department of War" in their wording) and federal agencies. The May 2026 release adds "Agentic Reporting": users describe a desired outcome in natural language and CORAS agents fuse data, generate reports, dashboards, and decision artifacts — replacing legacy BI tools (Tableau / Power BI / Cognos) inside classified environments. Not an audit / governance tool — it's a vertical agent product for defense.
- **Who buys it (named role + company shape):** DoD program offices, contracting officers, defense primes. Buyer = government PM. Use case = decision support inside classified networks where commercial agent platforms can't legally operate.
- **Pricing model (if visible):** Government contracts. Not publicly listed.
- **Their explicit positioning vs other AI safety/audit tools:** Not really competing in the audit category — they're a vertical defense agent platform whose moat is FedRAMP-High / IL5 accreditation. They're listed here because they got bundled into the same "May 5, 2026" news cycle as WSO2 Agent Manager and several governance plays.
- **Strong points (their moats):** (a) IL5 / FedRAMP High accreditation is multi-year, multi-million-$ — near-uncopyable for a startup. (b) Existing DoD contracts. (c) Multi-model (works with whatever LLM is accredited).
- **Gaps (what they DON'T do that someone could):** Not relevant for our comparison — they're not in the auditor/insurance/governance whitespace. Flagged as adjacent but out-of-scope.
- **URLs:**
  - Website: https://coras.ai/
  - Release coverage: https://orangeslices.ai/coras-ai-releases-agentic-ai-reporting-capabilities-eliminating-the-need-for-bi-tools/
  - Crunchbase: https://www.crunchbase.com/organization/corascloud
- **Recent signal (last 90 days):** May 5, 2026 — Agentic Reporting GA. May 2026 — PAE Maritime deployment announcement.

---

### Lakera Guard (now Cisco AI Defense)

- **Founded:** 2021, Zurich
- **Funding stage + latest round:** Raised ~$12M seed. **Acquired by Cisco May 2025** — now part of Cisco AI Defense portfolio. (Some sources mention Check Point but the Cisco acquisition is the verified live one — see Crunchbase + appsecsanta references.)
- **What their product ACTUALLY does (1 paragraph, plain English):** Real-time API that you put in front of an LLM call. Lakera classifies the prompt + the model output for prompt injection, jailbreak, PII leakage, hallucination flags. Sub-50ms latency, 100+ languages, 98%+ detection rates (their numbers, from G2 + their own page). Trained heavily on the Gandalf dataset (the prompt-injection CTF they ran which generated millions of attack examples). Sister product Lakera Red is offline red-teaming. Sold to enterprises building consumer-facing or internal LLM apps.
- **Who buys it (named role + company shape):** AppSec / CISO at enterprises shipping LLM features (banking, healthcare, customer-support). Now distributed via Cisco enterprise sales. Buyer is the security org, not the AI/ML org.
- **Pricing model (if visible):** Free tier (self-serve, low request volume). Enterprise quote-based. Custom policies + on-prem deployment in enterprise tier.
- **Their explicit positioning vs other AI safety/audit tools:** "AI-native security platform." Positions as runtime defense (the WAF analogy for LLMs) — NOT as an auditor, NOT as governance. Acquisition into Cisco AI Defense puts them in direct competition with Palo Alto, CrowdStrike's incipient AI security plays.
- **Strong points (their moats):** (a) Best-known prompt-injection dataset (Gandalf). (b) Cisco distribution + bundling. (c) Latency is real — sub-50ms means you can actually deploy inline. (d) Multi-language detection is unusually strong.
- **Gaps (what they DON'T do that someone could):** (a) They protect the LLM call, not the agent's TOOL EXECUTION — an agent that's hijacked into calling the wrong tool with the right arguments slips past prompt classifiers. (b) Point-in-time runtime — no compliance artifact, no audit log packaging. (c) No fault injection on the agent's reasoning loop. (d) Becoming a Cisco product means roadmap is now Cisco-aligned — startup agility lost.
- **URLs:**
  - Website: https://www.lakera.ai/
  - Product: https://www.lakera.ai/lakera-guard
  - Pricing: https://platform.lakera.ai/pricing
  - Crunchbase: https://www.crunchbase.com/organization/lakera-ai
- **Recent signal (last 90 days):** Continuing integration into Cisco AI Defense; Zurich research team retained per acquisition terms. No standalone product launches in last 90 days — all news is Cisco-routed.

---

### CalypsoAI (now F5)

- **Founded:** 2018, Dublin
- **Funding stage + latest round:** Raised $43.2M across 3 rounds from 14 investors (Paladin Capital Group, Lockheed Martin Ventures, Hakluyt Capital). **Acquired by F5 Networks for $180M on Sep 11, 2025.**
- **What their product ACTUALLY does (1 paragraph, plain English):** CalypsoAI Inference Platform sits between an enterprise's apps and any model (OpenAI, Anthropic, internal). It enforces guardrails, red-teams agents at scale, and provides real-time threat defense for agentic workflows. They explicitly market "agentic red-teaming" as a category — automated adversarial probing of multi-step agent workflows, not just single-prompt classification. Now F5 distributes it through their app/API/agent security suite.
- **Who buys it (named role + company shape):** Enterprise CISOs at Fortune-500 / government-adjacent shops. Strong defense-industry roots via Lockheed Martin Ventures backing. F5 distribution = telco, finserv, federal.
- **Pricing model (if visible):** Subscription, tiered by inference request volume + data volume + features. Not publicly listed. Quote-based.
- **Their explicit positioning vs other AI safety/audit tools:** "Adaptive AI security" — they explicitly position agentic red-teaming as a distinct capability vs. Lakera's prompt-classifier model. Post-acquisition framing is "F5 for the AI age" — they sit alongside F5's WAF/APM products.
- **Strong points (their moats):** (a) Real, mature agentic-red-teaming product — they've been building this since 2018 from a defense-DoD origin. (b) F5 enterprise distribution + bundling. (c) Lockheed Martin / Paladin Capital network → defense contracts. (d) Inference-platform positioning (intercept-the-model-call) makes it the natural enforcement point.
- **Gaps (what they DON'T do that someone could):** (a) F5 acquisition = startup speed gone, roadmap aligned to F5's. (b) Their red-teaming is internal/offensive — not packaged as a third-party audit artifact a buyer can show a regulator. (c) Heavily enterprise — smaller AI teams can't / won't deploy it. (d) Not Phoenix/OTEL-native (they have their own observability).
- **URLs:**
  - Website: https://calypsoai.com/
  - F5 acquisition press: https://www.f5.com/company/news/press-releases/f5-to-acquire-calypsoai-to-bring-advanced-ai-guardrails-to-large-enterprises
  - Crunchbase: https://www.crunchbase.com/organization/calypso-ai
  - SiliconANGLE: https://siliconangle.com/2025/09/11/f5-acquires-ai-security-provider-calypsoai-180m/
- **Recent signal (last 90 days):** Integration into F5 product line ongoing. Gartner Peer Insights reviews surfacing the F5-CalypsoAI Inference Platform as a real product. No new standalone launches.

---

### Guardrails AI

- **Founded:** 2023 (Shreya Rajpal, ex-Apple ML, ex-Pioneer); company spun out of the OSS project
- **Funding stage + latest round:** $7.5M seed (April 2024, Zetta Venture Partners + Pear VC + Bloomberg Beta + Github). No public Series A as of June 2026 surfaced.
- **What their product ACTUALLY does (1 paragraph, plain English):** Open-source Python framework you wrap around LLM calls. You compose "validators" (toxicity check, PII check, hallucination grounding, schema validation, etc.) into a "guard" that runs on inputs and outputs. v0.9.2 shipped March 2026. Guardrails Hub is the validator marketplace. Snowglobe (newer product) generates synthetic-data evals. Guardrails Pro = managed/hosted version with team features.
- **Who buys it (named role + company shape):** OSS is used by individual engineers + AI/ML teams at all sizes (6.6k GitHub stars). Guardrails Pro buyer = AI platform leads at scale-ups / enterprises who want managed + audit logs without self-hosting.
- **Pricing model (if visible):** OSS: free (Apache 2.0). Pro: not publicly listed, contact-sales. Some sources cite $0/$Pro/$Enterprise pattern but specifics aren't on the site.
- **Their explicit positioning vs other AI safety/audit tools:** "Composable validation framework." Closer to a library than a platform. They positioning themselves as the OSS standard for output validation, with Pro as the managed wrap. Direct competitor analogues: NVIDIA NeMo Guardrails, OpenAI's just-released openai-guardrails-python.
- **Strong points (their moats):** (a) OSS distribution + Andrew Ng partnership course = top-of-funnel. (b) Composability model is genuinely clean — easier to extend than NeMo Guardrails. (c) Snowglobe (synthetic eval generation) is a sticky adjacent product. (d) Shreya Rajpal has strong personal brand in the AI safety space.
- **Gaps (what they DON'T do that someone could):** (a) Single-call validation, NOT multi-step agent reasoning audit. A multi-step agent with 12 tool calls — Guardrails will catch a leaky output on call #12 but not why the agent decided call #12 was needed. (b) No compliance certification artifact. (c) OpenAI launching their own openai-guardrails-python is a direct threat to their relevance. (d) No fault injection / chaos testing — purely defensive runtime validation.
- **URLs:**
  - Website: https://guardrailsai.com/
  - GitHub: https://github.com/guardrails-ai/guardrails
  - Docs: https://guardrailsai.com/docs/
  - OpenAI's competing OSS: https://openai.github.io/openai-guardrails-python/
- **Recent signal (last 90 days):** v0.9.2 release in March 2026. Snowglobe ongoing. Andrew Ng partnership course running. No funding news.

---

### Promptfoo (now OpenAI)

- **Founded:** 2023 (Ian Webster ex-Discord, ex-Smile Identity)
- **Funding stage + latest round:** **Acquired by OpenAI ~March 9, 2026 for ~$86M.** Previously raised $18.4M Series A (July 2025, Insight Partners led, a16z participation). Remains open-source under MIT post-acquisition.
- **What their product ACTUALLY does (1 paragraph, plain English):** CLI + library for evaluating and red-teaming LLM apps. Two halves: (1) eval — declarative YAML config that runs N prompts × M models × K test cases and outputs a comparison matrix. CI/CD integratable. (2) red-team — auto-generates thousands of adversarial inputs across 50+ vulnerability types (prompt injection, PII leak, RBAC bypass, excessive agency, etc.) and includes OWASP LLM Top 10 / NIST AI RMF / MITRE ATLAS presets. Used by 25%+ of Fortune 500.
- **Who buys it (named role + company shape):** OSS used by individual ML engineers, AI app teams, and security teams at scale-ups and Fortune 500. Cloud/Enterprise buyer = AI platform leads + AppSec teams who want the team / shared-results / managed-probes features.
- **Pricing model (if visible):** Community OSS free (10k probes/month). Cloud Team plan: $50/month. Enterprise: custom. Now under OpenAI ownership, pricing trajectory is uncertain.
- **Their explicit positioning vs other AI safety/audit tools:** "DAST for your LLM pipeline" — explicitly framed as dynamic application security testing analog. Positioning is pre-prod + CI/CD, not runtime. Compares directly to Lakera (runtime) by being PRE-deployment. Now-OpenAI-blessed gives them de-facto standard status.
- **Strong points (their moats):** (a) OpenAI ownership = distribution moat. (b) Used by OpenAI + Anthropic internally (was true pre-acquisition). (c) 18k GitHub stars, 350k users, F500 saturation. (d) Compliance preset library (OWASP/NIST/MITRE) is the most complete in the category. (e) OSS + MIT = sticky.
- **Gaps (what they DON'T do that someone could):** (a) Pre-deployment testing — does NOT continuously monitor production. (b) Eval is on outputs, not the agent's INTERNAL reasoning / tool-call graph — they treat the agent as a black box you probe externally, not as a traced reasoning system. (c) OpenAI ownership creates conflict-of-interest worries for buyers running multi-model stacks (Claude + Gemini + open models). (d) No compliance attestation packaging — you still need someone else to package the evals into auditor-ready evidence.
- **URLs:**
  - Website: https://www.promptfoo.dev/
  - GitHub: https://github.com/promptfoo/promptfoo
  - Pricing: https://www.promptfoo.dev/pricing/
  - Acquisition coverage: https://www.paperclipped.de/en/blog/promptfoo-ai-agent-red-teaming/
- **Recent signal (last 90 days):** OpenAI acquisition March 9, 2026. Continued OSS releases. New presets being added. Cloud product redirecting under OpenAI infra likely in progress.

---

### AIUC (Artificial Intelligence Underwriting Company) — the critical incumbent

> **This is the company that most directly occupies the "AI Trust Auditor" positioning we'd be reaching for.** Profile in extra depth.

- **Founded:** 2024-2025 (emerged from stealth July 23, 2025)
- **Funding stage + latest round:** $15M seed (July 2025) led by Nat Friedman's NFDG. Participation: Emergence, Terrain, Ben Mann (Anthropic cofounder), ex-CISOs of Google Cloud + MongoDB. No Series A yet as of June 2026.
- **What their product ACTUALLY does (1 paragraph, plain English):** AIUC sells a **trifecta of (a) the AIUC-1 STANDARD, (b) independent AUDIT against that standard, (c) liability INSURANCE** priced on audit results. AIUC-1 is a 50+-control framework across 6 domains (Safety, Security, Reliability, Accountability, Data & Privacy, Society) mapping to MITRE ATLAS + OWASP Agentic Top 10 + EU AI Act + NIST AI RMF + ISO 42001. Audit involves quarterly adversarial testing across 1,000+ enterprise risk scenarios. Certificate is valid 12 months, technical testing required every 3 months. They explicitly position AIUC-1 as "SOC-2 for AI agents" — a procurement-friendly trust signal that vendors get to show buyers. Co-developed with Orrick (law firm), Stanford, Cloud Security Alliance, MIT, MITRE. UiPath is a public founding contributor + certified holder.
- **Who buys it (named role + company shape):** TWO buyers. (1) AI agent VENDORS who need to clear enterprise procurement (UiPath is the case study — they got certified to make sales easier). (2) Enterprise BUYERS who want a procurement-friendly checkbox to require from vendors. Direct buyer = CISO / GC / Chief Risk Officer / Head of AI Procurement at F500.
- **Pricing model (if visible):** Not publicly listed. Insurance pricing scales with audit score (safer agents = lower premiums). Certification is quote-based.
- **Their explicit positioning vs other AI safety/audit tools:** Distinct from Klaimee/Mount because AIUC is positioning as a STANDARD + AUDITOR FIRST, insurance second. Distinct from observability players (Arize/Phoenix, Langfuse, Fiddler) because they're not selling tooling — they're selling assessment outcomes. Distinct from Lakera/CalypsoAI because those are runtime defense; AIUC is pre-deployment + recurring attestation.
- **Strong points (their moats):** (a) AIUC-1 framework with founding contributors UiPath + co-development with Stanford/MITRE/Orrick = standards-body credibility from day 1. (b) Nat Friedman + ex-Anthropic + ex-METR (Rajiv Dattani led OpenAI/Anthropic pre-deployment model evals at METR) = unmatched safety credibility. (c) Bundling standard+audit+insurance is novel and creates lock-in. (d) The "SOC-2 analogy" is sticky — every enterprise procurement person understands it instantly. (e) 12-month certificate = recurring revenue.
- **Gaps (what they DON'T do that someone could):** (a) They're services-heavy — quarterly testing isn't automated, it's done by their staff (likely). Hackathon-shippable continuous-audit tooling could undercut them on cost. (b) AIUC-1 is a NEW framework — they don't have ten years of installed base like ISO. A buyer can ask "why your standard not someone else's?" (c) Their audit is BLACK-BOX — they probe the agent externally. They don't audit the agent's PHOENIX TRACE TREE / internal reasoning. (d) Quarterly cadence means a 3-month blind spot during which an agent could drift, get jailbroken, or hit a new failure mode. (e) Their probe library (1,000+ scenarios) is a fixed dataset — not synthesized from chaos-engineering principles tailored to your agent's specific tool graph. (f) Heavy enterprise sales motion — they're not selling self-serve.
- **URLs:**
  - Standard: https://aiuc.com/research/introducing-aiuc-1
  - Team: https://aiuc.com/team
  - VentureBeat coverage: https://venturebeat.com/ai/former-anthropic-exec-raises-15m-to-insure-ai-agents-and-help-startups-deploy-safely
  - Fortune coverage: https://fortune.com/2025/07/23/ai-agent-insurance-startup-aiuc-stealth-15-million-seed-nat-friedman/
  - UiPath certification: https://www.uipath.com/newsroom/uipath-achieves-aiuc-1-certification
- **Recent signal (last 90 days):** UiPath certified as first AIUC-1 holder (announced as case study by both parties). UiPath becomes "founding contributor" to AIUC-1 standard. Continued framework development. No Series A yet — that's the obvious next signal to watch.

---

## Tier 2 — Lighter Profiles

### Portkey

- **Founded:** 2023, San Francisco / Bangalore
- **Funding stage + latest round:** Series A (~$13M total across rounds per public Crunchbase data); no major new round announced in 2026 surfaced in search.
- **What their product ACTUALLY does:** AI gateway + observability + guardrails + prompt management. One API to call 1,600+ LLMs with built-in caching, routing, fallbacks, guardrails (50+), governance, cost controls. Open-sourced the gateway in March 2026 after processing 1T+ tokens/day. Production positioning: "control panel for production AI."
- **Pricing:** Developer Free, Production $49/mo, Enterprise custom. Pro-tier capped at 3M logs/mo which is restrictive at scale.
- **Positioning vs others:** AI Gateway category leader for self-serve / mid-market — competes with Helicone, Cloudflare AI Gateway, Kong AI Gateway, TrueFoundry, Aporia.
- **Strong points:** Mature gateway product, multi-provider routing, OSS distribution (March 2026).
- **Gaps:** Not pitched as an audit/compliance tool. No attestation/certification artifacts. Observability is request-log-shaped, not agent-trace-tree-shaped.
- **URLs:** https://portkey.ai/ — Pricing: https://portkey.ai/pricing — OSS: https://github.com/portkey-ai/gateway — TheNewStack on OSS launch: https://thenewstack.io/portkey-gateway-open-source/
- **Recent signal:** Open-sourced full gateway March 2026.

---

### Helicone

- **Founded:** 2023 (YC W23)
- **Funding stage + latest round:** **Acquired by Mintlify, March 2026** — after 14.2T tokens processed.
- **What their product ACTUALLY does:** Open-source LLM observability platform — one line of code to monitor + evaluate + experiment. AI Gateway w/ 100+ providers, intelligent routing, fallbacks, unified observability.
- **Pricing:** Free (10k req/mo, 7-day retention), Pro $79/mo, Team $799/mo (SOC-2, HIPAA), Enterprise custom (on-prem available).
- **Positioning vs others:** Cost-tracking + observability for AI builders. Mintlify acquisition reshapes roadmap toward developer-docs-adjacent use cases.
- **Strong points:** OSS, simple integration, cost tracking.
- **Gaps:** Now part of a docs company — uncertain agent-governance roadmap. No audit-evidence packaging. Not pitching governance.
- **URLs:** https://www.helicone.ai/ — https://github.com/helicone/helicone
- **Recent signal:** Mintlify acquisition March 2026.

---

### Langfuse

- **Founded:** 2023 (YC W23, Berlin)
- **Funding stage + latest round:** **Acquired by ClickHouse, January 2026.** Previously seed-stage.
- **What their product ACTUALLY does:** Open-source LLM engineering platform — tracing, evals, prompt management, playground, datasets, human annotation. 28k GitHub stars (top OSS LLM observability). Integrates with OpenTelemetry, LangChain, OpenAI SDK, LiteLLM.
- **Pricing:** Generous free tier, Pro tiers, Enterprise + self-hosted.
- **Positioning vs others:** Most-adopted OSS observability — competes with Arize Phoenix (similar OSS positioning), Helicone, Laminar.
- **Strong points:** OSS, OTEL-native, ClickHouse-backed scale post-acquisition.
- **Gaps:** Now part of a database company — uncertain roadmap as it gets absorbed. No audit-evidence packaging. Doesn't certify or attest — they just observe.
- **URLs:** https://langfuse.com/ — https://github.com/langfuse/langfuse
- **Recent signal:** ClickHouse acquisition January 2026.

---

### Arize Phoenix / Arize AX

- **Founded:** 2020 (Arize AI, Berkeley CA)
- **Funding stage + latest round:** $131M total over 4 rounds. Series C Feb 2025 (12 investors participated). No newer rounds surfaced.
- **What their product ACTUALLY does:** TWO products. (1) **Phoenix** = OSS AI observability + eval platform (Elastic License 2.0, ~9k+ GitHub stars, OpenTelemetry-native via OpenInference). (2) **Arize AX** = enterprise commercial product with session/span tracing, LLM-as-judge evals, real-time alerts (PagerDuty + Slack), drift detection, "Alyx" AI debugging assistant. SOC 2 / GDPR / HIPAA / RBAC for regulated industries.
- **Pricing:** Phoenix free OSS. AX Free + AX Pro ($50/mo). Enterprise AX ~$50K-$100K+/yr.
- **Positioning vs others:** "The Datadog for AI" — observability-first. Owns the OpenInference standard. Sponsors of the Rapid Agent Hackathon track we're building for.
- **Strong points:** OpenInference is the de-facto OTEL semantic conventions standard for AI. MCP server (`@arizeai/phoenix-mcp`) launched Q1 2026. Strongest tracing data model for agents (span tree captures tool calls, retrievals, eval scores). Big customer base.
- **Gaps:** Not an audit/cert play — they observe + alert + eval, they don't issue attestation artifacts. No "compliance bundle" output. Trust is built by tooling, not by an independent auditor stamp. **This is the WHITESPACE for ChaosLab — Phoenix is the substrate, but doesn't ship the audit-product wrapper.**
- **URLs:** https://arize.com/phoenix/ — https://github.com/arize-ai/phoenix — https://arize.com/docs/ax
- **Recent signal:** Continued Phoenix releases, Phoenix MCP shipped Q1 2026 (this is what our hackathon is built on top of).

---

### TruEra (acquired by Snowflake)

- **Founded:** 2019; **acquired by Snowflake May 2024** (tech assets + key employees, terms undisclosed).
- **Funding stage + latest round:** Pre-acquisition raised ~$45M total (Series B 2022).
- **What their product ACTUALLY does:** Was an AI/ML model observability + monitoring platform. Now folded into Snowflake's AI Observability inside Cortex.
- **Positioning vs others:** No longer a standalone competitor — Snowflake-only.
- **Gaps:** Tied to Snowflake ecosystem. Customers running outside Snowflake have no access.
- **URLs:** https://www.snowflake.com/en/blog/snowflake-acquires-truera/ (per Snowflake's own announcement)
- **Recent signal:** No standalone product line.

---

### Fiddler AI

- **Founded:** 2018
- **Funding stage + latest round:** **$30M Series C, January 27, 2026** (led by RPS Ventures; Lightspeed, Lux, Insight, Capgemini Ventures, Mozilla Ventures, LG Technology Ventures). Total funding $100M.
- **What their product ACTUALLY does:** Fiddler AI Control Plane = observability + guardrails + governance for the agentic lifecycle. Differentiates "AI Observability" (passive) vs. "AI Control Plane" (prescriptive — blocks bad inputs, stops harmful outputs, requires human approvals for high-risk decisions). Standardized telemetry + reliable evaluation + continuous monitoring + enforceable policy + auditable governance.
- **Pricing:** Per-unit data ingested. Not publicly listed.
- **Positioning vs others:** "The Control Plane for AI Agents" — directly competes with WSO2 Agent Manager, Aporia, TrueFoundry, Databricks Unity AI Gateway. Has explicitly pivoted from ML observability to agentic AI control plane.
- **Strong points:** $100M total raised, mature ML-observability heritage, January 2026 Series C reinforces the agent pivot. Has an auditable-governance pitch already.
- **Gaps:** Sells to large enterprises, not self-serve. Auditable governance is a feature, not a packaged certification artifact. Still positions as platform, not auditor.
- **URLs:** https://www.fiddler.ai/ — Series C announcement: https://www.fiddler.ai/press-releases/fiddler-raises-30m-series-c — BusinessWire: https://www.businesswire.com/news/home/20260127042634/en/Fiddler-Raises-$30M-Series-C-to-Power-the-Control-Plane-for-AI-Agents
- **Recent signal:** $30M Series C January 27, 2026 with pivot to "Control Plane for AI Agents" branding.

---

### Credo AI

- **Founded:** 2020
- **Funding stage + latest round:** Series A ($12.8M, 2022, Sands Capital). No newer round surfaced.
- **What their product ACTUALLY does:** Enterprise AI governance, risk, compliance (GRC) platform. AI Agent Registry product. Ready-to-deploy policy packs for EU AI Act, NIST AI RMF, ISO 42001, SOC 2, HITRUST with automated evidence generation. Discovery → registration → risk assessment → deployment gates → runtime monitoring for agents.
- **Pricing:** Not publicly listed. Enterprise sales motion.
- **Positioning vs others:** "Trusted leader in AI Governance" — closest in spirit to AIUC, but Credo doesn't issue independent certifications or sell insurance. They tool the customer's INTERNAL governance program. Ranked #6 in Fast Company's "Most Innovative Companies of 2026 — Applied AI."
- **Strong points:** Policy packs library (EU AI Act / NIST / ISO 42001 mappings already done), mature platform, ranked #6 by Fast Company. Built for regulated industries before agents got hot.
- **Gaps:** They equip the customer to self-govern — they're not an independent third party. An AIUC-style "independent stamp" is not their product. Heavier RIM/GRC platform, not nimble agent-specific testing.
- **URLs:** https://www.credo.ai/ — Agent Registry: https://www.credo.ai/ai-agent-registry — EU AI Act: https://www.credo.ai/eu-ai-act
- **Recent signal:** Fast Company #6 ranking 2026. Continued policy pack expansion. No funding news.

---

### Robust Intelligence (now Cisco)

- **Founded:** 2019
- **Funding stage + latest round:** $44M raised across 2019-2021. **Acquired by Cisco August 2024**, terms undisclosed. Folded into Cisco AI Defense.
- **What their product ACTUALLY does:** AI application security platform — automated testing for safety + security in AI models. Detects + assesses model vulnerabilities pre-prod + in-prod.
- **Positioning vs others:** Was pre-Lakera in the AI security category. Now both Robust Intelligence + Lakera are inside Cisco AI Defense, giving Cisco a strong consolidated AI security stack.
- **Strong points:** Cisco distribution, Gartner 2024 Cool Vendor.
- **Gaps:** Same Cisco roadmap issues as Lakera. Pre-2024 architecture predates agents — was built for ML model security, agent capabilities bolted on.
- **URLs:** Cisco blog: https://blogs.cisco.com/news/fortifying-the-future-of-security-for-ai-cisco-announces-intent-to-acquire-robust-intelligence — SiliconANGLE: https://siliconangle.com/2024/08/27/cisco-snaps-ai-model-data-security-startup-robust-intelligence/
- **Recent signal:** Continued integration into Cisco AI Defense alongside Lakera.

---

### Adjacent / additional players surfaced

- **HiddenLayer** (Series A $50M Sep 2023, $56M total) — ML/AI model threat detection. Austin TX. https://www.hiddenlayer.com/ — Static (no new 2026 funding surfaced).
- **Aporia** — Israeli AI control platform; AI policy gateway w/ no-code "no-go zones" for agents. $30M raised. https://aporia.com/
- **TrueFoundry** — Enterprise PaaS, just launched "Agent Gateway" June 2, 2026 (very fresh) to address agent governance. https://www.businesswire.com/news/home/20260602233322/en/TrueFoundry-Launches-Agent-Gateway-to-Close-the-Enterprise-AI-Governance-Gap
- **InfiniteWatch** — $4M pre-seed (April 2026, ex-CoverWallet, Base10 led). "Observability for the agentic internet." Real-time observe + measure + manage. https://techfundingnews.com/infinitewatch-4m-ai-agent-observability/
- **InsightFinder AI** — $15M Series B (April 2026, Yu Galaxy led). "Autonomous Reliability Insights" — figures out where AI agents go wrong. https://techcrunch.com/2026/04/16/insightfinder-raises-15m-to-help-companies-figure-out-where-ai-agents-go-wrong/
- **Honeycomb Agent Observability** (May 2026 launch) — Honeycomb extends its observability platform with agent-specific tracing. Incumbent observability vendor expanding into agents.
- **Databricks Unity AI Gateway** — Databricks-native agent governance layer. Walled-garden customers.
- **Corgi** — AI liability insurance launched May 5, 2026 (Artificial Lawyer coverage). Third entrant in the AI insurance space alongside Klaimee + Mount.
- **agent-chaos** (deepankarm OSS) — Open-source chaos engineering for AI agents. **THIS IS THE THING OUR PROJECT EXPLICITLY DOES NOT VENDOR (per ADR-006).** Integrates with DeepEval + Pydantic Evals.

---

## Synthesis — The Market Map (2026-06-04)

### Five distinct positioning camps have emerged

1. **Insurance carriers** — Klaimee, Mount, Corgi, AIUC. Sell financial-coverage policies for AI agent failures. Tailwind: major insurers (Berkshire, Chubb, Travelers, AIG, Great American, WR Berkley) excluded AI from commercial policies effective Jan 2026.
2. **Standards bodies + certification auditors** — AIUC-1 (de facto). Sell the trust artifact itself. Conflict-of-interest issue is being papered over with "founding contributor" branding (UiPath et al).
3. **Runtime defense** — Lakera (Cisco), CalypsoAI (F5), Robust Intelligence (Cisco), Aporia, HiddenLayer. Sit inline, classify + block. Mostly inside big-co umbrellas now.
4. **Observability + eval platforms** — Arize Phoenix+AX, Langfuse (ClickHouse), Helicone (Mintlify), Portkey, Fiddler, TruEra (Snowflake). Observe + monitor + eval but don't issue attestation. Heavy consolidation in 2025-2026.
5. **Control planes / governance platforms** — WSO2 Agent Manager, Fiddler Control Plane, Credo AI, TrueFoundry, Databricks Unity. Identity + policy + lifecycle. Enterprise-platform-style, slow to deploy.

### The market gap (1-2 paragraphs)

**The whitespace:** There is no **continuous, automated, evidence-producing, third-party-independent AI agent audit product that small-and-mid-size AI teams can self-serve.** AIUC owns the credibility seat but charges enterprise-services prices and runs quarterly cadence (3-month blind spots). Klaimee + Mount run point-in-time underwriting probes only. The observability players (Phoenix, Langfuse, Fiddler) capture the trace data but stop short of issuing attestation. The runtime defense players (Lakera, Calypso) protect inline but produce no audit-evidence artifact.

**The specific underserved buyer:** the **AI-platform lead at a Series A/B startup or a mid-market company deploying agents into a regulated workflow**, who needs to produce auditor-grade evidence for their next SOC 2 / ISO 42001 / EU AI Act / customer-procurement review — but cannot afford a $150K AIUC engagement and cannot wait for AIUC's quarterly cadence. Today they're stitching together Promptfoo (red-team) + Arize Phoenix (traces) + Guardrails AI (runtime) + a homegrown markdown evidence file. There's no tool that closes the loop: inject systematic faults → observe via Phoenix → score via LLM judge → output an attestation-grade compliance bundle.

### Specific to our hackathon — would ChaosLab-reframed-as-AI-Trust-Auditor be differentiated?

**Yes, on FOUR specific axes — but only if we explicitly reframe and ship the attestation artifact:**

1. **Phoenix-trace-tree as audit evidence (vs. external-probe black-box auditing).** AIUC + Klaimee + Mount probe agents externally. Our wedge: assert on Phoenix span trees (per `best-practices/06 §5.1` and our `CLAUDE.md` hard rule "trace-as-assertion"). That's a structural moat — we're auditing the agent's INTERNAL REASONING TREE, not its outputs. Buyers who understand OpenTelemetry will pay more for this evidence.
2. **Systematic chaos-engineering fault classes (vs. ad-hoc probe libraries).** AIUC fires 1,000+ probes from a fixed scenario library. Our 4 fault classes (per the spec — F1-F4 native-reimplemented per ADR-006) are SYSTEMATIC — chaos-engineering-derived, not scenario-curated. Reproducible across any agent. This is what AIUC's audit team would actually want.
3. **Continuous self-serve cadence (vs. quarterly enterprise services).** AIUC's quarterly testing is human-bottlenecked. We can ship a service that re-audits on every PR / every deploy, with results piped into a SOC2/ISO42001 evidence bundle. Same trust artifact, 100x the cadence, 10x cheaper.
4. **Closed-loop hardening (vs. fail-the-test).** Our spec includes the GitLab MR emission — when an audit fails, we open a hardening PR. That's a product loop nobody in this list has. AIUC tells you you failed; ChaosLab tells you + fixes you.

**Reframing the wedge:** Instead of "chaos engineering for AI agents" (engineer-flavored, eval-flavored), pitch as **"the AI Trust Auditor: continuous, Phoenix-native, attestation-grade agent audits for compliance officers."** Same hot-path code, different demo + landing-page narrative. The Arize judges will respond strongly because (a) it makes their Phoenix + Phoenix-MCP central, (b) it has a clearer buyer than "chaos engineering," (c) it has a clear comparison story vs. AIUC where we win on cadence + transparency.

**Risks to the reframing:**

- AIUC could ship a self-serve product (their 5+1 founding team has the technical chops). Watch for Series A announcement.
- Phoenix itself could ship "compliance bundle export" (low-hanging fruit for Arize given OpenInference data model). Watch their roadmap.
- The "audit" framing forces a sales motion (CISO buyer) that's slower than the "developer tool" motion. For HACKATHON JUDGING, the audit framing is unambiguously stronger (Arize's customers are CISO-shaped). For post-hackathon GTM, the developer-tool framing might convert faster.

### Top 3 most-credible competitors (ranked by direct positioning overlap)

1. **AIUC** — 90% positioning overlap. They occupy "auditable framework + independent assessment + attestation artifact" already. Our differentiation is technical (Phoenix-trace-as-evidence + chaos-engineering systematics + continuous cadence + closed-loop hardening). They have the standards-body credibility we can't replicate in 8 days; we have automation + speed they can't easily replicate.
2. **Fiddler AI Control Plane** — 60% overlap. Their "auditable governance" pitch overlaps our audit framing. Differentiation: we're chaos-engineering-native + Phoenix-native + ship a portable attestation artifact, while Fiddler is platform-resident governance.
3. **Promptfoo** (now OpenAI) — 50% overlap. Pre-deployment red-teaming + compliance-preset library competes with our fault-injection layer. Differentiation: we close the loop with traces + judge + auto-hardening PR; Promptfoo stops at "here are the failing tests."

### Verdict

**Defensible angle: YES, on technical axis + cadence axis, NOT on credibility axis.**

We will NOT out-credibility AIUC in 8 days — they have Anthropic + METR + Orrick + Stanford + UiPath. But we can out-engineer them with Phoenix-trace-tree assertions, systematic 4-class fault injection, continuous-cadence self-serve audits, and a closed-loop hardening MR. The pitch to the Arize track judges is:

> "AIUC sells the trust artifact. We sell the system that produces the trust artifact continuously, transparently, Phoenix-native, and at developer cadence. Same buyer (compliance officer + head of AI platform), different price point, different velocity, and zero conflict-of-interest because we're not also the insurer."

The hackathon win condition is showing the judges that the chaos→trace→judge→MR loop is differentiated, demo-able in under 2 minutes, and obviously useful for any team running production agents. The AIUC comparison gives us the credibility-of-category — we don't have to convince judges that "AI agent audit" is a real category; AIUC already did that with $15M from Nat Friedman. We just have to show we're the technical-first, developer-cadence, Phoenix-native answer.
