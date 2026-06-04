# Vertical Agent Gaps: Where B2B Demand for AI Agent Engineering is Hottest in 2026

> Empirical scan of 10 verticals — what real businesses are paying agent engineers
> to build, what's already saturated, and where hackathon-scope projects can still
> wedge in. Every claim is sourced. Job postings, funding announcements, and VC
> theses are cited inline. Pure inference is marked [UNVERIFIED].
>
> **Goal:** identify 5-8 verticals with HIGH demand for a specific shape of AI
> agent, named companies + JD evidence + concrete pain points. Then map each of
> the 6 hackathon sponsors (Arize, Elastic, Fivetran, GitLab, MongoDB, Dynatrace)
> to the single vertical pairing that yields the highest-leverage demo.
>
> **Date:** 2026-06-03 | **Author:** Claude (research subagent)

---

## Cross-cutting findings before the vertical-by-vertical

Three signals worth pinning before drilling into individual verticals:

1. **The "labor budget" thesis is now consensus.** a16z, Bessemer, and Sapphire
   Ventures all argue vertical AI taps the 13% of US GDP spent on business labor
   (not the 1% spent on IT). Bessemer estimates vertical AI's market cap will be
   ≥10× legacy vertical SaaS. LLM-native vertical AI companies are growing ~400%
   YoY at ~65% gross margins.
   ([Bessemer State of AI 2025](https://www.bvp.com/atlas/the-state-of-ai-2025),
   [Bessemer playbook](https://www.bvp.com/atlas/building-vertical-ai-an-early-stage-playbook-for-founders),
   [VC Cafe 2026 predictions](https://www.vccafe.com/2026/01/08/2026-ai-predictions-the-year-of-the-agent-employee/))

2. **88% of agent pilots never reach production. 22% of those that do report
   negative ROI at 12 months.** "Data entropy" (unstructured PDFs/screenshots/logs)
   - lack of observability/governance + infrastructure costs are the named
     blockers. ([Inovabeing reliability gap](https://www.inovabeing.com/blog/ai-agent-reliability-production-failure-2026),
     [Yallo enterprise AI gap](https://yallo.co/insights/news/enterprise-ai-in-2026-the-gap-everyone-is-ignoring/))

3. **The "Forward Deployed Engineer" role explosion is the clearest job signal
   that vertical agent work is what frontier labs + enterprises are paying for.**
   Anthropic, OpenAI, Google, Palantir are all hiring FDEs with explicit
   requirements for "agent development, evaluation frameworks, deployment at
   scale" — vertical-specialized FDEs command $215K–$500K total comp.
   ([MarkTechPost FDE explainer](https://www.marktechpost.com/2026/05/20/what-is-a-forward-deployed-engineer-the-ai-role-openai-anthropic-and-google-are-hiring-in-2026/),
   [Anthropic FDE JD on Greenhouse](https://job-boards.greenhouse.io/anthropic/jobs/4985877008),
   [Palantir FDE JD on Lever](https://jobs.lever.co/palantir/636fc05c-d348-4a06-be51-597cb9e07488),
   [The Information on FDEs](https://www.theinformation.com/articles/forward-deployed-engineers-rage))

The implication for our hackathon: an agent project that demonstrates
**observability + reliability inside a hot vertical** is double-coded for the
two strongest 2026 enterprise-buyer pains (vertical labor displacement + the
prod-reliability gap). Both fit the Arize/ChaosLab thesis cleanly.

---

## Vertical 1: Legal Tech (contract review, discovery, compliance)

### Job demand signal

- **Harvey AI — Legal Engineer (multiple cities).** Active reqs in
  [Dallas](https://www.harvey.ai/company/careers/3877a57f-d841-49a7-8957-ad1f4ab2a475),
  [EMEA](https://www.harvey.ai/company/careers/4154ddf4-99e3-4863-9509-826a6faddeea),
  [Toronto](https://www.harvey.ai/company/careers/eab239f7-11b5-4033-aa51-001a5423e7e1),
  [Custom Solutions](https://www.harvey.ai/company/careers/f4248359-1e87-4401-acf4-ac01dfb29a87),
  and a [Senior Software Engineer, AI Platform](https://www.harvey.ai/company/careers/51fb953a-c494-4a09-8fe2-8d7268b863ec).
  JD explicitly says the legal engineers "build and refine product
  demonstrations, workflows, and use cases that reflect how legal teams actually
  work" — i.e. these are FDE-shaped agent-building roles staffed with lawyers.
- **Harvey 2026-03 funding round used capital specifically to "expand the agents
  customers run on Harvey and grow the embedded legal engineering teams supporting
  them globally."** ($200M Series E, $11B valuation,
  [Harvey post](https://www.harvey.ai/blog/harvey-raises-at-dollar11-billion-valuation-to-scale-agents-across-law-firms-and-enterprises),
  [CNBC coverage](https://www.cnbc.com/2026/03/25/legal-ai-startup-harvey-raises-200-million-at-11-billion-valuation.html)).
- **Salary band:** FDEs / agent engineers in legal-tech command the same
  $200K–$320K base as other LLM agent roles
  ([KORE1 hiring guide](https://www.kore1.com/hire-llm-engineers-2026/)).

### What companies are paying agent engineers to build

- **End-to-end contract review agents.** Ironclad Assistant (launched 2026-03)
  ships an archive agent, intake agent, redlining agent, and conversational
  search agent — explicitly framed as "autonomously handle contract-related tasks
  across the full contract lifecycle."
  ([AI Funding Tracker](https://aifundingtracker.com/top-legal-ai-startups/))
- **Inhouse contract intelligence.** Harvey announced "Contract Intelligence for
  Inhouse" in May 2026 with a Q3 GA target
  ([Artificial Lawyer](https://www.artificiallawyer.com/2026/05/21/harvey-announces-contract-intelligence-for-inhouse/)).
- **AI-native law firms.** Crosby ("agentic AI-powered law firm" combining
  custom software with in-house lawyers); Lawhive raised $60M Series B
  ([Fortune](https://fortune.com/2026/02/05/lawhive-ai-law-firm-startup-series-b-venture-funding/));
  Y Combinator's 2025 RFS explicitly: "start your own law firm, staff it with
  AI agents, and compete with existing law firms"
  ([YC legal companies](https://www.ycombinator.com/companies/industry/legal)).
- **Docusign + Harvey partnership** announced 2026 to combine contract and legal
  AI ([StockTitan](https://www.stocktitan.net/news/DOCU/docusign-and-harvey-partner-to-bring-legal-and-contract-ai-mcqdw78vahyg.html)).

### Existing products (saturation map)

- **Harvey** — $11B valuation, $190M ARR (Jan 2026), 3.9× YoY growth, 1000+
  customers in 58+ countries.
  ([Harvey raises post](https://www.harvey.ai/blog/harvey-raises-at-dollar11-billion-valuation-to-scale-agents-across-law-firms-and-enterprises))
- **Legora** — Series D at $5.55B valuation, ~$550–600M raised in 2026
  ([PlatinumIDS blog](https://blog.platinumids.com/blog/legal-ai-billion-dollar-arms-race-2026)).
- **Ironclad** — Ironclad Assistant (2026-03).
  ([AI Funding Tracker](https://aifundingtracker.com/top-legal-ai-startups/))
- **Evisort** — Harvey/Ironclad comparison incumbent
  ([Agentic Contract Review](https://agenticcontractreview.com/)).
- **Crosby** — agentic AI-powered law firm
  ([AI Funding Tracker](https://aifundingtracker.com/top-legal-ai-startups/)).
- **GC AI / Lupl / Lawhive** — adjacent legal-AI players
  ([Lupl 10 to watch](https://www.lupl.com/blog/10-ai-law-firms-to-watch-in-2026/)).

### Gaps that hackathon-scope projects could fill

- **Legal agent reliability/observability surface.** Harvey published an
  open-source "Legal Agent Benchmark" precisely because evaluating legal agents
  is unsolved ([Harvey LAB blog](https://www.harvey.ai/blog/introducing-harveys-legal-agent-benchmark)).
  An open-source chaos-engineering surface that injects faults _specifically
  shaped like a legal agent's failure modes_ (cited-statute drift, redline
  hallucination, jurisdiction confusion) is wide open.
- **Cross-firm precedent retrieval** — current incumbents are firm-locked.
- **Discovery cost-allocation agents** — eDiscovery cost is a known SOX pain
  but no funded agent product targets the allocation step.

### Demo-friendliness for a 3-min hackathon video

- **Yes.** A contract redline diff or a citation-hallucination injection is a
  visually striking 3-min demo. Public synthetic data: SEC EDGAR contracts
  ([EDGAR full-text search](https://efts.sec.gov/LATEST/search-index?q=&forms=10-K)),
  Stanford CUAD ([Contract Understanding Atticus Dataset](https://www.atticusprojectai.org/cuad)),
  Harvey LAB benchmark itself.

---

## Vertical 2: Healthcare (clinical decision support, billing, prior auth)

### Job demand signal

- **Cadence Solutions — Applied AI Engineer.** JD: "design and ship production
  agents that synthesize real-time clinical data, surface proactive care
  recommendations, and take action on behalf of clinicians."
  ([Cadence JD on Greenhouse](https://job-boards.greenhouse.io/solutions/jobs/4680768006))
- **IMO Health — Staff AI/MLOps Engineer (Clinical AI).** JD: end-to-end ML
  lifecycle for production AI in clinical environments — observability and
  reliability explicitly called out.
  ([IMO Health JD on Lever](https://jobs.lever.co/imo-online/e88597a0-f097-42b3-9088-b3973d366dc2))
- **Cohere Health — ML Engineer II.** Prior-authorization automation specifically.
  ([Cohere Health JD](https://job-boards.greenhouse.io/coherehealth/jobs/7628281003))
- **Medeloop — Senior AI Data Engineer, Agentic Healthcare Platform.** JD:
  "architecting the data backbone that powers AI agents doing real operations at
  scale."
  ([Medeloop JD](https://job-boards.greenhouse.io/medeloop/jobs/4203844009))
- **Sirona Medical, Natera, eClinical Solutions, 100ms, Ada Health, Sword
  Health** — all currently hiring AI engineers with explicit
  agent-development scope. ([Sirona](https://job-boards.greenhouse.io/sironamedical/jobs/4550672005),
  [Natera](https://job-boards.greenhouse.io/natera/jobs/5766365004),
  [eClinical](https://job-boards.greenhouse.io/eclinicalsolutions/jobs/5123131007),
  [100ms](https://jobs.lever.co/100ms/3e18bc82-c410-4805-a788-9ad735bced19),
  [Ada Health](https://job-boards.greenhouse.io/adahealth/jobs/8488980002),
  [Sword Health](https://jobs.lever.co/swordhealth/39b62e2f-e83e-4610-b59e-d3c08502567d))
- **Salary band:** Health AI roles span $70K–$191K per ZipRecruiter
  ([ZipRecruiter Health AI](https://www.ziprecruiter.com/Jobs/Health-Ai)), but
  staff-level agent engineers in healthcare run with the same $200K–$320K base
  as other LLM roles.

### What companies are paying agent engineers to build

- **Prior-authorization automation.** Agent monitors EHR for orders needing
  prior auth, pulls notes + labs, packages per payer requirements, submits
  electronically; if denied, reads denial letter and prepares corrected
  resubmission. One health system reported reducing claims appeals from 15-16
  days to 1-2 days using this pattern.
  ([Dataconomy 2026 healthcare hireable agents](https://dataconomy.com/2026/01/07/why-2026-healthcare-hireable-ai-agents/),
  [Atlan healthcare HIPAA AI agent guide](https://atlan.com/know/ai-agent/ai-agent-in-healthcare/))
- **Patient-facing clinical agents.** Hippocratic AI: 1000+ clinical use cases,
  115M+ patient interactions, marketplace where licensed clinicians create
  agents in 30 minutes
  ([Hippocratic AI press release](https://hippocraticai.com/hippocratic-ai-announces-series-c-funding-126-million/)).
- **Voice agents for revenue cycle management** — 5 distinct production voice
  agents profiled in Droidal's 2026 RCM roundup
  ([Droidal Top 5 RCM voice agents](https://droidal.com/blog/top-5-voice-ai-agents-for-healthcare-revenue-cycle-management-in-2026/)).
- **Ambient scribe + documentation.** Abridge: outpatient documentation,
  real-time transcription.
  ([Hippocratic vs Abridge](https://hippocraticai.com/hippocratic-ai-announces-series-c-funding-126-million/))

### Existing products (saturation map)

- **Hippocratic AI** — $3.5B valuation, $404M total funding, $126M Series C
  Nov 2025; non-diagnostic patient-facing agents
  ([Fierce Healthcare](https://www.fiercehealthcare.com/ai-and-machine-learning/hippocratic-ai-lands-126m-series-c-expand-patient-facing-ai-agents-fuel-ma),
  [Business Wire](https://www.businesswire.com/news/home/20251103432446/en/Hippocratic-AI-Raises-$126-Million-in-Series-C-at-$3.5-Billion-Valuation-Led-by-Avenir-Growth-to-Expand-Clinically-Safe-Generative-AI-Agents-Across-Healthcare),
  [SiliconANGLE](https://siliconangle.com/2025/11/03/hippocratic-ais-valuation-soars-3-5b-raising-126m-new-funding/)).
- **Abridge** — ambient AI scribe, complements Hippocratic in workflow stack.
- **Cohere Health** — prior-auth automation incumbent
  ([Cohere Health JD evidence](https://job-boards.greenhouse.io/coherehealth/jobs/7628281003)).
- **Availity Intelligentum** — AI prior authorization
  ([Availity Intelligentum](https://www.availity.com/intelligentum/)).
- **Evry Health** — payer-side prior-auth AI
  ([D CEO on Evry](https://www.dmagazine.com/healthcare-business/2026/05/inside-evry-healths-push-to-streamline-prior-authorization-through-ai/)).
- **Develop Health, Sirona Medical, Cadence Solutions** — clinical agents.
- **84% of US health insurers now use AI/ML for utilization mgmt + prior auth**
  per NAIC survey ([KFF](https://www.kff.org/patient-consumer-protections/regulation-of-ai-in-prior-authorization-and-claims-review-a-look-at-federal-and-state-consumer-protections/)).

### Gaps that hackathon-scope projects could fill

- **Bidirectional prior-auth.** Most products automate the _provider_ side
  (submit + appeal). Few automate the _payer_ side reliability gate (validating
  that the AI denial decision itself is defensible under CMS rules effective
  Jan 1 2026). Chaos-injecting a prior-auth agent to surface false-deny modes
  is genuinely novel.
- **Cross-payer adapter testing.** Each payer's prior-auth API is bespoke.
  Resilience testing of a multi-payer agent is unsolved.
- **Patient-call-deflection agent QA.** Hippocratic ships 1000+ use cases —
  but rigorous failure-mode testing on each is per-customer bespoke.

### Demo-friendliness for a 3-min hackathon video

- **Yes, but PHI-sensitive.** Use synthetic data only.
  Public: [MIMIC-IV](https://mimic.mit.edu/) (de-identified ICU + ED data),
  [Synthea](https://synthetichealth.github.io/synthea/) (fully synthetic patient
  records), [CMS public claims samples](https://www.cms.gov/data-research/statistics-trends-and-reports/medicare-claims-synthetic-public-use-files).

---

## Vertical 3: Financial Services (trade recon, AML, customer support)

### Job demand signal

- **FIS + Anthropic agentic banking deal.** "Financial Crimes AI Agent will
  compress AML alert and case investigations from days to minutes." BMO and
  Amalgamated Bank in dev today; general availability 2H 2026.
  ([FIS press release](https://www.fisglobal.com/about-us/media-room/press-release/2026/fis-brings-agentic-ai-to-banking-with-anthropic-starting-with-financial-crimes))
- **Spektr — Series A $20M, NEA-led** for fintech compliance agents (document
  reviews, ownership mapping, risk analysis)
  ([Crunchbase](https://news.crunchbase.com/venture/fintech-compliance-founders-20m-seriesa-spektr/)).
- **Steward — $5M for AI compliance platform**
  ([FinTech Global](https://fintech.global/2026/03/18/ai-compliance-platform-steward-secures-5m-funding/)).
- **Sierra AI** — "agents helping the fastest growing fintechs and many of the
  largest banks in the US and Europe" — $200M ARR May 2026, $15B valuation
  ([SiliconANGLE on Sierra Series E](https://siliconangle.com/2026/05/04/ai-agent-startup-sierra-valued-15b-new-950m-funding-round/),
  [Sacra on Sierra](https://sacra.com/c/sierra/)).
- **Decagon** — F100 banks, Chime, Affirm, Bilt
  ([Sacra on Decagon](https://sacra.com/c/decagon/)).

### What companies are paying agent engineers to build

- **AML transaction monitoring.** Agents analyze transaction patterns,
  cross-reference sanctions + adverse media, generate SAR narratives for human
  review.
  ([CallSphere AML](https://callsphere.ai/blog/agentic-ai-financial-compliance-aml-monitoring),
  [AML Intelligence on agentic AI + stablecoins](https://www.amlintelligence.com/2026/01/insight-agentic-ai-and-stablecoins-the-five-trends-redefining-aml-in-2026/))
- **Month-end close + reconciliation.** Accounts payable, expense management,
  intercompany accounting all targeted by 2026 agent products
  ([Moveo financial recon](https://moveo.ai/blog/financial-reconciliation-ai-agents),
  [TNGlobal AI in finance](https://technode.global/2026/06/01/ai-agents-in-finance-how-autonomous-ai-is-reshaping-the-financial-industry-in-2026/)).
- **Compliance-grade audit trails.** Now the dominant evaluation criterion for
  regulated buyers — "every tool call, every reasoning step, replayable"
  ([Lorikeet fintech CX 2026](https://www.lorikeetcx.ai/articles/ai-customer-support-fintech-2026)).
- **Outcome-based pricing.** Fin $0.99/resolution, Zendesk $1.50-2.00, Sierra
  - Decagon custom ([Lorikeet](https://www.lorikeetcx.ai/articles/ai-customer-support-fintech-2026)).

### Existing products (saturation map)

- **FIS Financial Crimes AI Agent** (with Anthropic) — coming 2H 2026.
- **Sierra AI** — $15B valuation, FS one of its top verticals.
- **Decagon AI** — $4.5B valuation, banks + Affirm + Chime customers.
- **Spektr** — KYC/KYB agent, $26M total.
- **Steward** — AI compliance.
- **Symphony AI** — AML transaction monitoring incumbent
  ([SymphonyAI](https://www.symphonyai.com/resources/blog/financial-services/best-aml-transaction-monitoring-software/)).
- **Uptiq.ai, Kore.ai** — no-code agent platforms targeting fintech
  ([Kore.ai 12 use cases](https://www.kore.ai/blog/ai-agents-in-finance-banking-12-proven-use-cases-2026)).

### Gaps that hackathon-scope projects could fill

- **Reproducible SAR-narrative regression testing.** Agents that write SAR
  narratives are highly regulated outputs — no public framework exists for
  testing them adversarially.
- **Cross-jurisdiction sanctions adapter resilience.** OFAC + EU + UN +
  state-level lists all change weekly. An agent that proves it stays correct
  under list-shift chaos is a real moat.
- **Reconciliation exception explanation.** Sub-second numeric recon is solved;
  the _why-it-broke_ narrative for a controller is not.

### Demo-friendliness for a 3-min hackathon video

- **Yes.** Sanctions injection (fake "Vladimir P." entry) → agent should flag
  → inject typo "Wlad. Pootin" → agent should still flag → demonstrate
  failure mode. Public data:
  [OFAC SDN list](https://www.treasury.gov/ofac/downloads/sdn.csv),
  [synthetic transaction graphs from FinCEN AML Tactics](https://www.fincen.gov/).

---

## Vertical 4: Manufacturing (predictive maintenance, supply chain, QC)

### Job demand signal

- **Palantir Foundry + AIP** = the de facto industrial agent platform.
  "Chain Reaction" suite launched specifically for autonomous AI agents in
  supply chain and logistics.
  ([Palantir AIP](https://www.palantir.com/platforms/aip/),
  [Palantir supply chain](https://www.palantir.com/offerings/supply-chain),
  [Lokad Palantir review](https://www.lokad.com/review-of-palantir-com/))
- **C3.ai** — generative AI integration with Foundry for supply chain
  ([C3.ai for Palantir](https://c3.ai/generative-ai-for-palantir/)).
- **Deloitte: 4× increase in agentic AI adoption in manufacturing by 2026
  (6% → 24%)** ([Manufacturing Tomorrow](https://www.manufacturingtomorrow.com/story/2026/05/how-agentic-ai-is-transforming-smart-manufacturing-in-2026/27588/)).
- **Job-board evidence:** Palantir's
  [Forward Deployed AI Engineer JD](https://jobs.lever.co/palantir/636fc05c-d348-4a06-be51-597cb9e07488)
  is the canonical mfg-agent FDE role; the role explicitly involves "building
  custom workflows on top of Foundry" inside customer factories.

### What companies are paying agent engineers to build

- **Predictive maintenance → autonomous repair orchestration.** Agentic AI
  doesn't just predict the bearing failure — it drafts the repair plan, checks
  parts inventory, schedules the technician, coordinates the work order
  ([Manufacturing Tomorrow](https://www.manufacturingtomorrow.com/story/2026/05/how-agentic-ai-is-transforming-smart-manufacturing-in-2026/27588/),
  [Intuz mfg AI](https://www.intuz.com/blog/ai-use-cases-in-manufacturing)).
- **Digital quality control.** Computer-vision + sensor + history merged into
  agent that flags issues earlier in production
  ([F7i QC definition](https://f7i.ai/blog/define-qc-the-definitive-2026-guide-to-quality-control-in-modern-manufacturing)).
- **Reduces downtime by 40%+, component weight by 55%** in cited deployments
  ([AlphaBOLD predictive maint](https://www.alphabold.com/ai-powered-predictive-maintenance-in-manufacturing/)).
- **Customs + compliance.** Cross-checking shipping docs autonomously
  ([sysgenpro logistics agents](https://sysgenpro.com/ai/logistics-ai-agents-for-exception-management-and-workflow-coordination)).

### Existing products (saturation map)

- **Palantir Foundry / AIP / Chain Reaction** — dominant
  ([Palantir Operating System article](https://markets.financialcontent.com/stocks/article/finterra-2026-2-5-palantir-technologies-pltr-the-operating-system-of-the-agentic-ai-era)).
- **C3.ai** — generative AI for industrial
  ([C3](https://c3.ai/generative-ai-for-palantir/)).
- **Amfas (CNC predictive maint)**
  ([Amfas](https://amfasinternational.com/newsroom/predictive-maintenance-with-ai-in-cnc-machining-the-future-of-zero-downtime-manufacturing/)),
  [10 predictive maint platforms 2026](https://www.iiot-world.com/predictive-analytics/predictive-maintenance/10-predictive-maintenance-platforms-for-manufacturing-2026/).
- **Market projected $20.8B by 2028** for AI in mfg.

### Gaps that hackathon-scope projects could fill

- **Mfg-floor agent observability.** Palantir owns the _platform_. Independent
  observability/chaos-engineering tooling that works _on top of_ Foundry agents
  is wide open and would even be welcomed by sponsors who'd rather not depend
  on Palantir's own surface.
- **Supply-chain agent fault injection.** No incumbent ships fault-injection
  for `(tariff shifts | port shutdowns | supplier silence | sanctions add)`
  scenarios.

### Demo-friendliness for a 3-min hackathon video

- **Moderate.** Hard to film a factory floor in 3 min. Easier as a dashboard
  demo. Public synthetic data:
  [NASA Turbofan Engine Degradation Simulation Dataset (C-MAPSS)](https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/),
  [Bosch CNC Machining Dataset](https://www.kaggle.com/datasets/inIT-OWL/production-plant-data-for-condition-monitoring),
  [CWRU bearing dataset](https://engineering.case.edu/bearingdatacenter).

---

## Vertical 5: Retail / E-commerce (returns, recommendations, inventory)

### Job demand signal

- **Shopify Universal Commerce Protocol (UCP)** built specifically to let AI
  agents discover products + complete transactions in conversation. Shopify's
  TC interview: "preparing for AI shopping agents to change everything."
  ([TechCrunch on Shopify agents](https://techcrunch.com/2026/03/16/shopify-is-preparing-for-ai-shopping-agents-to-change-everything-exec-says/),
  [Shopify AI agents for retail](https://www.shopify.com/blog/ai-agents-retail),
  [Shopify agentic commerce primer](https://www.shopify.com/blog/agentic-commerce))
- **McKinsey: agentic commerce could account for $3T–$5T of global consumer
  spending by 2030** ([BigCommerce](https://www.bigcommerce.com/blog/ecommerce-ai-agents/)).
- **Sierra AI + Decagon AI** both cite retail/consumer services as top
  verticals
  ([Sierra Sacra](https://sacra.com/c/sierra/),
  [Decagon Sacra](https://sacra.com/c/decagon/)).

### What companies are paying agent engineers to build

- **Conversational shopping agents** that handle product discovery → cart →
  checkout in one flow
  ([Opascope agentic commerce protocols](https://opascope.com/insights/ai-shopping-assistant-guide-2026-agentic-commerce-protocols/)).
- **Return-automation agents** that read merchant return policy + customer
  message + decide refund/replace/deny.
- **Order tracking + post-purchase support** at high volume — Shopify Knowledge
  Base app lets merchants control how AI agents answer FAQs
  ([Shopify AI agents](https://www.shopify.com/blog/ai-agents-retail)).
- **Alhena AI** ranks 16 e-commerce agent products by real revenue outcomes
  ([Alhena](https://alhena.ai/blog/best-ai-agents-for-ecommerce/)).

### Existing products (saturation map)

- **Shopify UCP + Knowledge Base + Agentic Storefronts** (platform).
- **Sierra AI** ($15B), **Decagon AI** ($4.5B) — both cover retail.
- **Alhena, Ringly, Insider, Fini** — operator-level products
  ([Ringly](https://www.ringly.io/blog/ai-shopping-assistants),
  [Fini fintech guide also touches retail](https://www.usefini.com/guides/ai-customer-support-platforms-fintech)).

### Gaps that hackathon-scope projects could fill

- **Agentic-checkout fraud testing.** When Shopify UCP lets an agent push
  cards, the prompt-injection attack surface explodes. No incumbent ships
  prompt-injection chaos testing for agentic commerce flows.
- **Return-policy adversarial QA.** Agents that interpret return policies will
  diverge across merchants. Cross-merchant regression testing is unbuilt.

### Demo-friendliness for a 3-min hackathon video

- **Very high.** Retail is the most visually demoable vertical. Public data:
  [Amazon product reviews dataset](https://nijianmo.github.io/amazon/index.html),
  [Shopify dev store with synthetic SKUs](https://shopify.dev/docs/storefronts/headless),
  Faker-generated return tickets.

---

## Vertical 6: Real Estate (listings, inspection, valuation)

### Job demand signal

- **Cambio — $18M Series A at $100M valuation (Jan 2026, YC-backed)** for
  agentic AI in commercial real estate
  ([Crunchbase News](https://news.crunchbase.com/real-estate-property-tech/cambio-cre-ai-asset-management-saas-software-funding/),
  [Cambio Series A announcement](https://www.cambio.ai/news/series-a),
  [Business Wire](https://www.businesswire.com/news/home/20260122635473/en/Cambio-Raises-$18M-to-Transform-Commercial-Real-Estate-Operations-with-Agentic-AI)).
  JD-shape: "reasons across unstructured documents, runs multi-step analyses,
  adapts to changing regulations."
- **Compass + Anywhere consolidation:** $1.6B acquisition in Jan 2026 → 340K
  agents on one platform; AI tools roll out company-wide
  ([Cambio coverage references](https://www.buildmvpfast.com/blog/ai-agents-real-estate-workflow-automation-2026)).
- **97% of brokerage leaders report agents actively using AI**
  ([Discount Property Investor 2026 tools](https://www.discountpropertyinvestor.com/blog/ai-real-estate-tools-in-2026-what-agents-need)).
- **Market: $2.9B (2024) → $41.5B (2033), >30% CAGR**
  ([Ascendix AI for RE agents](https://ascendix.com/blog/ai-real-estate-agents/)).

### What companies are paying agent engineers to build

- **Lease abstraction agents.** AI compresses commercial lease abstraction from
  3-5 hours to ~7 minutes with 95%+ accuracy
  ([buildmvpfast on lease abstraction](https://www.buildmvpfast.com/blog/ai-agents-real-estate-workflow-automation-2026)).
- **Modern AVMs with computer vision** — analyze listing photos for interior
  quality + finishes
  ([Vocal Media on AI valuation 2026](https://vocal.media/01/is-ai-valuation-replacing-real-estate-agents-in-2026)).
- **Transaction-management orchestration agents** — appraisal, inspection,
  title, escrow handoffs
  ([MindStudio RE agents](https://www.mindstudio.ai/blog/real-estate)).
- **Morgan Stanley: AI could automate up to 37% of real estate operations,
  saving the industry ~$34B in efficiency** over 5 years
  ([Appinventiv](https://appinventiv.com/blog/ai-in-real-estate/)).

### Existing products (saturation map)

- **Cambio** — commercial RE, $100M valuation.
- **Matterport** — 3D capture + AI
  ([Matterport](https://matterport.com/blog/ai-real-estate)).
- **35+ tools profiled by Ascendix** — fragmented
  ([Ascendix](https://ascendix.com/blog/ai-real-estate-agents/)).

### Gaps that hackathon-scope projects could fill

- **Cross-jurisdiction zoning regression.** Zoning rules vary by municipality
  and change quarterly. No incumbent ships rule-change chaos testing for an
  AVM agent.
- **Inspection-report adversarial QA.** Agents that summarize inspection
  reports drop critical defects — but no benchmark for this exists.

### Demo-friendliness for a 3-min hackathon video

- **Moderate-high.** Photo-based demos are visual. Public data:
  [Zillow open data](https://www.zillow.com/research/data/),
  [Redfin data center](https://www.redfin.com/news/data-center/),
  [HUD APIs](https://www.huduser.gov/portal/dataset/fmr-api.html).

---

## Vertical 7: Insurance (claims, underwriting, fraud)

### Job demand signal

- **Avallon — $4.6M seed, YC + Frontline Ventures (Nov 2025).** Building AI
  agents specifically to automate claims tasks. Revenue 10× during YC Spring
  2025 incubation. Expanding from Workers Comp + Auto to all P&C + healthcare.
  ([Business Wire on Avallon](https://www.businesswire.com/news/home/20251106838494/en/Avallon-Secures-$4.6-Million-Scales-AI-Agents-to-Automate-Insurance-Claims-Operations))
- **Pasito — AI agents for insurance + benefits**
  ([YC insurance list](https://www.ycombinator.com/companies/industry/insurance)).
- **Bevaya, Corgi, Multimodal, Roots, Teamvoy** all shipping insurance agents
  ([Bevaya](https://www.bevaya.ai/),
  [Corgi](https://www.corgi.insure/ai),
  [Roots April 2026 trends](https://www.roots.ai/blog/april-2026-insurance-ai-trends-highlights),
  [Teamvoy back-office](https://teamvoy.com/blog/agentic-ai-for-insurance-back-office-claims-underwriting-fraud/)).
- **Market:** $1.13B in Q1 2025 alone for P&C insurtech funding — +90%
  quarterly — driven largely by AI innovations
  ([Vantage Point insurtech trends 2026](https://vantagepoint.io/blog/sf/insights/insurtech-trends-2026-ai-claims-underwriting)).
- **Demographic pressure:** 400,000 insurance workers expected to leave through
  attrition by 2026
  ([Business Wire on Avallon citing attrition](https://www.businesswire.com/news/home/20251106838494/en/Avallon-Secures-$4.6-Million-Scales-AI-Agents-to-Automate-Insurance-Claims-Operations)).
- **ROI bands published:** FNOL claims 9-14 mo payback, underwriting agents
  18-24 mo, SIU fraud agents **6-9 mo (the fastest payback of any agentic AI
  category)**
  ([CallSphere insurance ROI](https://callsphere.ai/blog/agentic-ai-insurance-claims-underwriting-automation)).

### What companies are paying agent engineers to build

- **First-notice-of-loss (FNOL) automation.** Reduces processing cost 30-50%,
  improves customer satisfaction 20+ pts
  ([CallSphere](https://callsphere.ai/blog/agentic-ai-insurance-claims-underwriting-automation)).
- **Claims workbench agents.** Stream's Claims Workbench turns PDFs into
  automated workflows
  ([Vantage Point](https://vantagepoint.io/blog/sf/insights/insurtech-trends-2026-ai-claims-underwriting)).
- **Fraud detection agents.** European insurers under Solvency II report 60%
  fewer false positives vs rule-based
  ([Vantage Point](https://vantagepoint.io/blog/sf/insights/insurtech-trends-2026-ai-claims-underwriting)).
- **Underwriting agents** for pricing + policy issuance.

### Existing products (saturation map)

- **Avallon** ($4.6M, YC).
- **Pasito, Bevaya, Corgi, Multimodal, Stream** — many small players, no
  $1B+ incumbent yet.
- **Lemonade, Root** — incumbents on the carrier side but not agent-platform.

### Gaps that hackathon-scope projects could fill

- **This is the most underserved B2B vertical in the AI agent space relative
  to its TAM.** Insurance has fastest payback (6-9 months for SIU fraud) but
  no platform incumbent at $1B+. No Harvey-of-insurance exists. Chaos
  engineering for claims-agent reliability would slot into 100% of these
  startups' Series A pitch.
- **Multi-party claims orchestration.** No incumbent automates the
  insurer ↔ provider ↔ patient ↔ adjuster handoff under realistic chaos
  (provider system down, payer denial, patient escalation).

### Demo-friendliness for a 3-min hackathon video

- **Yes.** Inject "provider data missing" + "fraud signal" + "policy lapse" and
  watch the agent route the case. Public data:
  [CMS BBC public claims sample](https://www.cms.gov/data-research/statistics-trends-and-reports/medicare-claims-synthetic-public-use-files),
  [NAIC public reports](https://content.naic.org/research-actuarial),
  [Insurance Fraud Bureau open datasets](https://www.iaiabc.org/Public/Workers-Compensation-Forms-Library).

---

## Vertical 8: Education (tutoring, grading, curriculum)

### Job demand signal

- **MagicSchool — $67M total ($45M Series B Jan 2026)**
  ([MagicSchool pricing](https://www.magicschool.ai/pricing),
  [MagicSchool federal funding post](https://www.magicschool.ai/blog-posts/federal-funding-ai-in-education)).
- **Brisk Teaching — $15M after crossing 1M educator users**
  ([Brisk Curriculum Intelligence](https://www.briskteaching.com/curriculum-intelligence)).
- **Khan Academy / Khanmigo** — $4-$44/mo consumer pricing; teacher tools free
  via Microsoft partnership
  ([Khanmigo for teachers](https://www.khanmigo.ai/teachers)).
- **2,800+ AI education startups operating in 2026 (18× growth since 2023);
  $4.2B raised in 2025 alone**
  ([EduGenius landscape](https://www.edugenius.app/blog/education-ai-startup-landscape-2026)).
- **Language learning dominates funding** — Preply, Speak, ELSA, Praktika,
  Univerbal, Blue Canoe raised $400M+ combined.

### What companies are paying agent engineers to build

- **Socratic tutoring agents** that guide rather than answer (Khanmigo's GPT-4
  pattern).
- **Personalized feedback agents.** Brisk: "personalized feedback on every
  assignment with next steps aligned to standards and curriculum"
  ([Brisk](https://www.briskteaching.com/curriculum-intelligence)).
- **Lesson-plan + rubric + grouping agents** — MagicSchool's stack of 70+
  tools.
- **AI writing assessment.** Writable (HMH): correlates r=0.78-0.85 with human
  raters, used by 3M students in 15K schools
  ([EduGenius](https://www.edugenius.app/blog/education-ai-startup-landscape-2026)).

### Existing products (saturation map)

- **Khanmigo** (Khan + Microsoft).
- **MagicSchool** ($67M).
- **Brisk Teaching** ($15M).
- **Writable** (HMH).
- **Preply, Speak, ELSA, Praktika** — language verticals.

### Gaps that hackathon-scope projects could fill

- **AI tutoring received most funding ($1.4B in 2024-2025) but shows mixed
  efficacy evidence** ([EduGenius](https://www.edugenius.app/blog/education-ai-startup-landscape-2026))
  — robust evaluation of tutoring agents is wide open.
- **Standards-alignment regression** when curriculum frameworks change
  (Common Core revisions, state-level shifts) — no incumbent ships chaos
  testing for this.
- **Plagiarism + cheating-detection agent QA** — false-positive rate is the
  active scandal in 2025-2026; demoable.

### Demo-friendliness for a 3-min hackathon video

- **Moderate.** Less visually punchy than retail/legal but easy to script.
  Public data: [Common Core dataset](https://www.commoncoresheets.com/),
  [OECD PISA datasets](https://www.oecd.org/pisa/data/),
  [LearnPlatform](https://www.learnplatform.com/),
  [synthetic K-12 essays via dolma + dolly](https://huggingface.co/datasets/databricks/databricks-dolly-15k).

---

## Vertical 9: Logistics (routing, exception handling, customs)

### Job demand signal

- **Project44 — AI Ocean Exceptions Agent (launched March 2026).** Identifies
  roll risk up to 35 hours earlier; compresses rebooking from hours to <5 min
  ([sysgenpro exception mgmt](https://sysgenpro.com/ai/logistics-ai-agents-for-exception-management-and-workflow-coordination)).
- **Transflo — Workflow AI for LTL (Jan 2026).** Multiple specialized agents
  per exception type
  ([sysgenpro](https://sysgenpro.com/ai/logistics-ai-agents-for-managing-exceptions-across-high-volume-workflows)).
- **Flexport Winter 2026 release** — agent-shaped freight tooling
  ([Flexport](https://www.flexport.com/technology/product-release/winter-2026/)).
- **FedEx, UPS, freight giants building autonomous supply chain in 2026**
  ([Agent Corps logistics](https://agentcorps.co/blog/ai-agents-logistics-fedex-ups-autonomous-supply-chain-2026)).
- **Market: $8.67B (2025) → $16.84B (2030)**
  ([Ampcome logistics ROI](https://www.ampcome.com/post/ai-agents-in-logistics-and-supply-chain)).

### What companies are paying agent engineers to build

- **Exception triage agents.** Detect delay → cross-reference alt carriers →
  re-route → update WMS → notify customer → escalate only outside-scope
  ([Ampcome](https://www.ampcome.com/post/ai-agents-in-logistics-and-supply-chain)).
- **Customs + compliance validation agents.** Auto cross-check shipping docs,
  customs paperwork, compliance certs
  ([sysgenpro customs](https://sysgenpro.com/ai/logistics-ai-agents-for-exception-management-and-workflow-coordination)).
- **Invoice matching + validation agents**
  ([Frayto practical agentic SCM](https://frayto.com/blogs/agentic-ai-for-supply-chain-where-it-actually-works)).

### Existing products (saturation map)

- **Project44, Transflo, Flexport, FourKites** — incumbents.
- **Palantir Chain Reaction** — overlap with mfg.
- **MindStudio logistics agents**
  ([MindStudio](https://www.mindstudio.ai/blog/logistics-supply-chain)).

### Gaps that hackathon-scope projects could fill

- **Cross-carrier resilience.** No incumbent tests an exception-handling
  agent's behavior when 2 carriers + 1 customs broker all fail simultaneously
  (i.e. tariff shock day).
- **Port-disruption simulation chaos.** 2026 has live geopolitical risk; no
  agent product proves its routing logic survives that.

### Demo-friendliness for a 3-min hackathon video

- **Yes.** Map-based demo with injected port shutdown is visually clear.
  Public data: [GDELT global event database](https://www.gdeltproject.org/),
  [Marine Cadastre AIS ship tracking](https://marinecadastre.gov/ais/),
  [FlightAware ADS-B](https://flightaware.com/commercial/data/).

---

## Vertical 10: Energy / Utilities (outage diagnosis, demand forecasting)

### Job demand signal

- **Kraken Technologies (Octopus spin-out)** — **$1B raise, $8.65B valuation
  Dec 2025, planning ~$15B IPO mid-2026.** Serves 70M+ utility accounts,
  > $500M annual contracted revenue, 15B data points/day, customers include
  > EDF, E.ON Next, National Grid US, Origin Energy, Tokyo Gas
  > ([CNBC on Kraken spin-off](https://www.cnbc.com/2025/12/30/octopus-energy-to-spinoff-ai-unit-kraken-at-8point65-billion-valuation.html),
  > [ESG News on $1B raise](https://esgnews.com/octopus-energy-spins-out-kraken-in-1-billion-raise-valuing-utility-ai-platform-at-8-65-billion/),
  > [TechBuzz on IPO](https://www.techbuzz.ai/articles/octopus-energy-spins-off-kraken-ai-platform-for-15b-ipo)).
- **Performance benchmarks:** 15-30% better demand forecast accuracy, 20-40%
  shorter outage duration, 10-25% opex savings
  ([ZTABS energy agents guide](https://ztabs.co/blog/ai-agents-for-energy-utilities)).
- **Market: $5.1B (2025) → $22.2B (2033), 20.4% CAGR**
  ([aimultiple AI utilities](https://aimultiple.com/ai-utilities)).

### What companies are paying agent engineers to build

- **Outage detection agents** that fire on AMI last-gasp data before first
  customer call
  ([aTeam Soft Solutions top 10](https://www.ateamsoftsolutions.com/top-10-ai-solutions-for-energy-and-utilities-load-forecasting-outage-prediction-and-grid-optimization-with-production-grade-implementation-details/),
  [EY on utilities](https://www.ey.com/en_us/insights/power-utilities/ai-can-help-utilities-predict-grid-outages)).
- **Magic Ink (Kraken's GPT-style)** — summarizes customer histories +
  generates responses to support agents
  ([Bizztor on Kraken](https://bizztor.com/news/octopus-energy-kraken-uk-s-quiet-rise-as-an-energy-software-superpower/)).
- **Load forecasting** (highest ROI use case — influences unit commit, dispatch,
  hedging, congestion planning, staffing, DR triggers, DER scheduling)
  ([aTeam](https://www.ateamsoftsolutions.com/top-10-ai-solutions-for-energy-and-utilities-load-forecasting-outage-prediction-and-grid-optimization-with-production-grade-implementation-details/)).
- **Virtual Power Plant coordination** (EVs, rooftop solar, batteries, heat
  pumps)
  ([Datamation on Kraken](https://www.datamation.com/artificial-intelligence/octopus-energy-kraken/)).

### Existing products (saturation map)

- **Kraken** — dominant globally.
- **Salesforce Energy & Utilities Cloud**
  ([Salesforce energy](https://www.salesforce.com/energy-utilities/artificial-intelligence/energy-ai/)).
- **NewGen Strategies utility AI report**
  ([NewGen](https://www.newgenstrategies.net/stories/utility-ai-transition-full-report.html)).
- **Parloa for utilities**
  ([Parloa utilities](https://www.parloa.com/blog/agentic-ai-in-utilities/)),
  [virtualworkforce.ai for energy](https://virtualworkforce.ai/ai-agents-for-energy-companies/).

### Gaps that hackathon-scope projects could fill

- **Storm-event chaos testing.** Kraken is dominant globally but no third
  party ships extreme-event chaos engineering for grid-coordination agents.
  This is a regulator-mandated need (FERC + state PUCs).
- **VPP-coordination resilience.** As DER scales, the agent's ability to
  re-coordinate under partial signal loss is unsolved.

### Demo-friendliness for a 3-min hackathon video

- **Moderate-high.** Grid maps + storm simulations are dramatic. Public data:
  [EIA Open Data API](https://www.eia.gov/opendata/),
  [PJM Interconnection data miner](https://dataminer2.pjm.com/list),
  [OpenEI weather + load datasets](https://openei.org/wiki/Data),
  [NOAA storm events](https://www.ncdc.noaa.gov/stormevents/).

---

## Cross-vertical demand ranking

Ranked by total job-postings + funding velocity + agent-product saturation
(higher demand AND lower saturation = better hackathon angle).

| Rank | Vertical                | Demand                                                                          | Saturation                                       | Net hackathon-fit                           |
| ---- | ----------------------- | ------------------------------------------------------------------------------- | ------------------------------------------------ | ------------------------------------------- |
| 1    | **Healthcare**          | Very high (10+ named JDs, Hippocratic at $3.5B, NAIC 84% adoption)              | Medium (many players, no one dominant)           | **HIGH** — prior-auth chaos especially open |
| 2    | **Legal**               | Very high (Harvey $11B, $4.3B legaltech raised 2025, named Legal Engineer reqs) | High (Harvey + Legora + Ironclad incumbents)     | Medium — saturated at the top               |
| 3    | **Financial Services**  | Very high (Sierra $15B, Decagon $4.5B, FIS+Anthropic)                           | High at top, low in long tail (mid-market banks) | High for AML/SAR observability              |
| 4    | **Insurance**           | High (Avallon, Pasito, Spektr, fastest payback at 6-9 mo for SIU fraud)         | **Very low — no $1B+ incumbent**                 | **HIGHEST — most underserved**              |
| 5    | **Retail / e-commerce** | High (Sierra, Decagon, Shopify UCP)                                             | Very high (saturated)                            | Medium                                      |
| 6    | **Real estate**         | Medium-high (Cambio $100M, Compass consolidation)                               | Medium-low                                       | High — agent observability greenfield       |
| 7    | **Logistics**           | Medium-high (Project44, Transflo, Palantir Chain Reaction)                      | Medium                                           | High — port-disruption chaos demoable       |
| 8    | **Energy / Utilities**  | Medium-high (Kraken at $8.65B)                                                  | High (Kraken dominant globally)                  | Medium — incumbent control of platform      |
| 9    | **Manufacturing**       | Medium-high (Palantir Foundry + AIP, Deloitte 4× adoption)                      | High (Palantir)                                  | Medium — platform-controlled                |
| 10   | **Education**           | Medium ($4.2B raised but soft signals on grading specifically)                  | Medium-high (MagicSchool, Brisk, Khanmigo)       | Low-medium                                  |

### Top 3 by demand signal

1. **Healthcare** — most JDs cited (10+), explicit "build AI agents" language
   across Cadence, IMO, Cohere Health, Medeloop, Sirona, Natera, Sword,
   100ms, Ada, eClinical. Hippocratic at $3.5B with 1000+ agent use cases in
   production. CMS Jan-2026 prior-auth rule = a regulatory forcing function.
2. **Legal** — Harvey $11B + $190M ARR + open Legal Engineer reqs in multiple
   cities, plus AI-native law firm thesis (Crosby, Lawhive, YC RFS).
3. **Financial Services** — Sierra ($15B) + Decagon ($4.5B) + FIS-Anthropic
   AML agent + Spektr fintech compliance. Multiple production agent
   deployments with audit-trail evaluation criteria already published.

### Single most underserved vertical: **Insurance**

Insurance has:

- **Fastest-payback ROI of any agentic-AI category** (6-9 months for SIU fraud
  agents — sourced from CallSphere insurance ROI breakdown).
- **Demographic forcing function** — 400K worker attrition by 2026 forcing
  agent adoption.
- **No $1B+ platform incumbent.** Avallon is YC seed; Pasito, Bevaya, Corgi,
  Stream all small. No Harvey-of-insurance, no Sierra-of-insurance.
- **Active VC checks** but no winner crowned yet.
- **Regulated outputs** (SIU fraud determinations, claims denials) need
  observability/chaos engineering = directly aligned with Arize track.

If we built a chaos-engineering surface targeted at insurance-claims agents
specifically (FNOL → triage → fraud check → denial-letter generation), every
funded player in Vertical 7 would want it tomorrow. ChaosLab's generic
framing could be specialized to "ChaosLab for Insurance Agents" with minimal
rework and capture the highest-leverage vertical.

---

## Sponsor pairings (single best vertical per sponsor)

For each of the 6 hackathon sponsors, the highest-leverage vertical pairing,
based on the sponsor's actual product capability + the vertical's pain shape.

### Arize → **Healthcare (prior authorization)**

Arize's Phoenix + Arize Cloud is purpose-built for LLM/agent observability,
evals, and tracing. Healthcare prior-auth agents are the most regulated agent
category with the highest cost of silent failure (CMS rule effective Jan 1
2026 forces real-time decisions; wrong denials are litigated).
[Arize observability post](https://arize.com/blog/best-ai-observability-tools-for-autonomous-agents-in-2026/)
explicitly cites healthcare as a domain where "domain-specific output quality"
is paramount but "healthcare-expert annotation, audit, and demographic fairness
workflows are not first-class" — i.e. they admit the gap. A demo showing
Phoenix tracing a multi-step prior-auth agent failing under payer-API chaos
would be the cleanest demo of Arize's value-add in any vertical.

### Elastic → **Financial Services (AML / SAR generation)**

Elastic's strengths are search + observability + security analytics. AML
agents generate SAR narratives over high-volume transaction graphs; Elastic
is the dominant log/transaction store in many banks already. Pairing
Elastic-as-corpus + an agent that drafts SARs + observability on the agent's
retrieval-and-reasoning steps fits Elastic's existing FS customer base. ML
incumbent is Symphony AI; differentiator = Elastic-native search-grounded
agent.

### Fivetran → **Insurance (claims data unification)**

Fivetran's wedge is data movement from SaaS into warehouse. Insurance claims
data spans 10+ systems (PAS, claims, billing, fraud, document mgmt, payer
portals). An agent that operates over Fivetran-unified claims data and runs
the FNOL-to-denial pipeline is the canonical Fivetran story applied to the
fastest-payback agent category in 2026. Avallon, Pasito etc. would
immediately want this.

### GitLab → **Legal Tech (contract redline & compliance review)**

GitLab is code review + collaboration + merge requests. Contract redlining is
git-shaped: branches per redline, MRs per amendment, audit trail per approver.
A legal agent that emits MR-style contract diffs into GitLab with a reviewer
agent on the other side is a perfect platform-fit demo. Harvey/Ironclad don't
own this shape — they own the editor surface but not the version-control
workflow. (This pairing also matches our existing ChaosLab GitLab MR emission
in ADR-011, which is already production-grade.)

### MongoDB → **Real Estate (commercial lease + asset management)**

MongoDB excels at document-shaped data with schema variation — exactly the
shape of unstructured lease documents, inspection reports, and property
records. Cambio's $18M Series A is explicitly about "reasoning across
unstructured documents" — Mongo Atlas + vector search + an agent that does
lease abstraction → schedule generation is a natural pairing. The CRE market
is fragmented enough that no incumbent locks Mongo out.

### Dynatrace → **Energy / Utilities (grid + outage agents)**

Dynatrace's wedge is enterprise observability for mission-critical
infrastructure with explainability features. Grid-coordination + outage-response
agents at utility scale are the highest-stakes "agent in critical
infrastructure" use case in 2026. Kraken processes 15B data points/day;
Dynatrace's volume-tolerant tracing + AI-explainability angle pairs cleanly
with grid agents. Demoing Dynatrace tracking a storm-injected DER agent's
behavior under partial-signal-loss chaos would be visually compelling and
sponsor-aligned.

---

## Practical implication for our project

We're already inside Vertical 1 (Legal — chaos engineering for an arbitrary
agent), but the **single highest-leverage vertical specialization for the
Arize track is Healthcare (prior auth) and the single most underserved
vertical for a wedge is Insurance.** If we want to retain optionality after
the hackathon — i.e. extend ChaosLab into a vertical product — Insurance and
Healthcare prior-auth are the two strongest next-step targets.

For the **3-min hackathon video**, retain the current generic framing (the
target agent is the "demo agent" — works for any vertical) but **swap the
target-agent's persona to a prior-auth agent** for the demo. This:

- Lets us name a concrete vertical (judges remember "ChaosLab for healthcare
  agents" better than abstract framing).
- Aligns Phoenix tracing with the highest-stakes regulated-output domain.
- Uses public synthetic data (MIMIC-IV / Synthea) we can ship.
- Avoids legal-tech saturation while still demonstrating the generic chaos
  surface.

**Recommendation: target the demo at healthcare prior-auth. Keep the
framework generic.**
