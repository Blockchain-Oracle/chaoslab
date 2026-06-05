# 25 — Persistent Monitor vs On-Demand Audit: Empirical Competitor Map

**Date:** 2026-06-05
**Author:** research sub-agent (for Phoenix Audit v1/v2 scope decision)
**Question:** Does any current product own the "continuous monitoring + regulator-ready signed audit report" combo? If not, should Phoenix Audit ship Shape A (on-demand scanner) or Shape B (always-on monitor) for the hackathon, given the 7-day deadline?

> Method: every claim below is anchored to a URL fetched on 2026-06-05. Where the vendor's own site is vague (which is most of them), the line is marked. Nothing here is from training data — only from pages crawled today.

---

## Shape definitions (Abu's framing, restated)

- **Shape A — On-demand scanner.** Operator points Phoenix Audit at their agent. Battery of 6 adversarial tests runs synthetically. One-shot signed PDF audit report. Like running an SCA scan before a release.
- **Shape B — Always-on monitor.** Phoenix Audit sits as a layer in front of (or alongside) the production agent. Every real user conversation is watched live. Anomalies alert in real time. Signed PDF report is generated on demand from the running history (date range = your choice). Like antivirus / runtime EDR.

The question is whether anyone in market today combines (1) continuous monitoring and (2) regulator-ready signed report. That's the whitespace.

---

## Competitor-by-competitor

### Lakera Guard (Lakera AI)

- **What they sell:** Inline runtime firewall for GenAI / agents. Blocks prompt injection, data leakage, policy violations in real time. Sub-50ms latency, SaaS or self-hosted.
- **Continuous monitoring?:** YES (it's inline, so by definition every request is screened).
- **Generates regulator-ready signed audit reports?:** NO. They expose "detailed logs and dashboards, export logs for SIEM integration, track policy edits with full audit history." No mention of PDF / signed / tamper-evident / regulator-ready report. The operator's compliance team must assemble the artifact from raw logs.
- **Pricing:** Not on public site. "Book a demo."
- **URL:** https://www.lakera.ai/lakera-guard ; https://www.lakera.ai/risk/compliance-regulatory-risks
- **Why this matters for Phoenix Audit:** They own the runtime-protection slot. They do NOT own the signed-report slot. If we ship a signed report, we're filling a gap they leave open. We are NOT trying to outrun their inline protection — different product.

### Guardrails AI (Guardrails + Snowglobe)

- **What they sell:** Runtime guardrails (block bad outputs), plus Snowglobe synthetic data, plus eval datasets. Open-source core + commercial cloud.
- **Continuous monitoring?:** PARTIAL. Runtime guardrails are inline, but the site doesn't describe a long-horizon production monitor with history / dashboards. The pitch is "block bad outputs before they reach users," not "watch every conversation forever."
- **Generates regulator-ready signed audit reports?:** NO. Site doesn't mention compliance reports, audit artifacts, or any signed output.
- **Pricing:** Not displayed.
- **URL:** https://www.guardrailsai.com/
- **Why this matters for Phoenix Audit:** They're a guardrail vendor, not an audit vendor. No overlap on the report side.

### WhyLabs

- **What they sell:** Nothing. **"WhyLabs, Inc. is discontinuing operations."** They open-sourced whylogs and langkit on the way out.
- **Continuous monitoring?:** N/A (out of business).
- **Generates regulator-ready signed audit reports?:** N/A.
- **Pricing:** N/A.
- **URL:** https://whylabs.ai/
- **Why this matters for Phoenix Audit:** One fewer competitor on the runtime-observability side. Cite this if anyone says "WhyLabs already does it." They do not — the company is dead.

### Robust Intelligence → Cisco AI Defense

- **What they sell:** End-to-end AI security suite spanning model validation (the old Robust Intelligence stack) + runtime protection across the AI lifecycle. Marketed for enterprises building AI applications and agents.
- **Continuous monitoring?:** YES. Cisco's own collateral references continuous risk assessment and "summary reports through compliance dashboards" for audit readiness.
- **Generates regulator-ready signed audit reports?:** UNCLEAR. The phrase "summary reports through compliance dashboards" implies dashboards-that-export, not pre-signed regulator artifacts. No language about "signed", "tamper-evident", or specific frameworks like EU AI Act / ISO 42001 found on the indexed product pages today.
- **Pricing:** Enterprise sales motion. Not displayed.
- **URL:** https://www.cisco.com/c/en/us/products/collateral/security/ai-defense/ai-defense-so.html (product page returned 403 to direct fetch today, but the Cisco solution-overview PDF is the canonical source)
- **Why this matters for Phoenix Audit:** Closest "incumbent" in shape but their slot is "Cisco's security stack add-on for Cisco shops." They sell to networking buyers, not to the AI / agent product owner. Different buyer = different deal cycle = different design.

### AIUC (Artificial Intelligence Underwriting Company) / AIUC-1

- **What they sell:** A certification standard (AIUC-1) for agentic applications + an underwriting/insurance angle. UiPath is their flagship cert customer (announced March 2026).
- **Continuous monitoring?:** NO — they don't ship a runtime product themselves. Certification model is: technical testing at least quarterly (every 3 months) + annual re-audit of operational/legal controls. Certificate valid 12 months. Updated quarterly to track MCP security, third-party risk, agent identity/permissions.
- **Generates regulator-ready signed audit reports?:** YES — but as a CERTIFICATION (the AIUC-1 cert itself), issued by an accredited auditor (Schellman is the first one), not as a software-generated artifact. The cert is the deliverable, not a per-request report.
- **Pricing:** Custom quote.
- **URL:** https://aiuc.com/ ; https://www.aiuc-1.com/aiuc-1-certification ; https://www.schellman.com/blog/news/schellman-becomes-the-first-accredited-auditor-for-aiuc-1
- **Why this matters for Phoenix Audit:** This is the **adjacent shape that matters most for our positioning**. AIUC-1 is the heavyweight cert. They do quarterly tests, not always-on. They explicitly leave a gap: "what does the operator do between quarters?" Phoenix Audit's continuous-monitor + signed-report combo could literally be marketed as "the system of record between your AIUC-1 audits." That's a real wedge.

### CalypsoAI → F5 AI Guardrails

- **What they sell:** Acquired by F5; product rebranded as "F5 AI Guardrails." Real-time protection for AI models/agents + connected data. Detect/prevent data leakage, compliance failures, policy violations at runtime. **Ships "automated auditing templates for GDPR, HIPAA, EUAIA, and more."**
- **Continuous monitoring?:** YES. Site explicitly claims "continuous visibility and traceability across all AI interactions."
- **Generates regulator-ready signed audit reports?:** PARTIAL. "Audit-ready observability, scanning, and logging tools" + the preset compliance templates including EU AI Act. The word "signed" or "tamper-evident" doesn't appear on the page. They appear to generate audit-ready evidence; not clear if it's a single-button signed PDF.
- **Pricing:** Not displayed.
- **URL:** https://www.f5.com/products/ai-guardrails
- **Why this matters for Phoenix Audit:** **The closest direct competitor on shape.** They claim continuous + audit-ready + named EU AI Act template. The unknowns: (a) does the artifact come out signed/tamper-evident, (b) is this F5-shop-only because the buyer is F5's networking sales motion, (c) does it cover AGENT-specific failure modes (tool-call abuse, MCP scope creep, role-confusion) or just LLM input/output. Our pitch needs to be: agent-native + cryptographically signed + standalone (not an F5 stack add-on).

### Promptfoo (now within OpenAI per public reports of an $86M acquisition)

- **What they sell:** Red Teaming, Guardrails, Model Security, Evaluations, Code Scanning, MCP Proxy. Originally synthetic test focused — now spans dev-time + runtime.
- **Continuous monitoring?:** YES — Enterprise tier explicitly lists "Continuous monitoring" and "Real-time alerts and automated evaluations" under "Reports & Continuous Monitoring."
- **Generates regulator-ready signed audit reports?:** PARTIAL. Lists "Centralized security/compliance dashboard" and "Verify compliance with industry frameworks and standards." No verbatim mention of signed / PDF / tamper-evident.
- **Pricing:** Community = Free Forever. Enterprise = Custom. On-Premise = Custom.
- **URL:** https://www.promptfoo.dev/ ; https://www.promptfoo.dev/pricing/
- **Why this matters for Phoenix Audit:** Promptfoo Enterprise IS the most direct shape-match for Shape A (synthetic adversarial test battery) AND has crept toward Shape B with continuous monitoring on the Enterprise tier. Their open-source distribution gave them 156 of the Fortune 500 — that's the threat. Our differentiator can't be "we run red-team tests" (commodity). It has to be the signed-artifact lock-in: regulator-ready PDF with cryptographic chain. Promptfoo doesn't publish that today.

### Credo AI

- **What they sell:** Enterprise AI governance platform. Discover/assess/govern every AI agent, model, application "continuously and in context." Named products: AI Governance Platform, AI Registry, Risk Intelligence, Policy Engine, GAIA (Govern AI Assistant).
- **Continuous monitoring?:** YES — Risk Intelligence explicitly markets "Continuous monitoring" + "Real-time alerts," contrasted with "point-in-time snapshots." Continuous bias/security/privacy/compliance assessment.
- **Generates regulator-ready signed audit reports?:** PARTIAL. Pre-built policy packs named for EU AI Act, NIST AI RMF, ISO 42001. They claim "audit-ready documentation" and "evidence generation." Whether the output is a signed PDF or a dashboard-of-evidence is not explicit on their site.
- **Pricing:** Not displayed.
- **URL:** https://www.credo.ai/
- **Why this matters for Phoenix Audit:** **Closest pure-governance competitor.** They own continuous + policy-pack-per-framework. The gap they leave: they monitor at the GOVERNANCE layer (registries, policies, evidence), not at the AGENT BEHAVIOR layer (tool calls, MCP scopes, span trees). Phoenix Audit can position underneath them as the data source: "Credo aggregates the policy evidence; Phoenix Audit emits the cryptographically signed behavioral trace that feeds the evidence."

### Holistic AI

- **What they sell:** End-to-end AI governance platform. "Guardian Agents" (Sentinel + Operative) provide real-time oversight, observe behaviour, evaluate against policies, intervene in real time.
- **Continuous monitoring?:** YES — explicitly "Continuously monitor deployed models for drift, degradation, and adversarial threats."
- **Generates regulator-ready signed audit reports?:** PARTIAL. "Continuous audit trails, evidence collection, and compliance reporting — audit-ready from day one." No explicit "signed" / "PDF" / "tamper-evident" language found.
- **Pricing:** Not displayed.
- **URL:** https://www.holisticai.com/
- **Why this matters for Phoenix Audit:** Almost identical positioning to Credo AI. Two governance suites occupy this slot now. Both stop short of saying "signed cryptographic PDF report." That language is the gap.

### Fiddler AI

- **What they sell:** Control Plane for Agents + Fiddler Centor Models + Guardrails + AI Governance/Risk/Compliance.
- **Continuous monitoring?:** YES — real-time monitoring, alerts, MTTI/MTTR reduction.
- **Generates regulator-ready signed audit reports?:** PARTIAL. "Generate evidence needed for audit trails aligned with enterprise governance and regulatory requirements (GDPR, HIPAA, NAIC, SR 11-7)." No EU AI Act, NIST AI RMF, or ISO 42001 mentioned by name on the product page indexed. No "signed" / "PDF" / "tamper-evident" language.
- **Pricing:** Not displayed.
- **URL:** https://www.fiddler.ai/ai-observability
- **Why this matters for Phoenix Audit:** Banking/insurance-leaning (SR 11-7 is a Fed model-risk-mgmt rule). Lighter on the AI-Act / agent-native angle. Less direct competitor than F5 or Credo/Holistic.

### Klaimee (YC) — AI agent insurance

- **What they sell:** Liability insurance for AI agents. Risk evaluation across 8 dimensions (scope, data exfiltration, unauthorized action, output integrity, adversarial manipulation, behavioral stability, etc.). Application ~10 min; full eval report in days. 24-hour bind.
- **Continuous monitoring?:** NO — based on the public site, the model is point-in-time eval + a "free adversarial playground" you can hit whenever. **No continuous telemetry requirement is published** for underwriting.
- **Generates regulator-ready signed audit reports?:** NEITHER — they generate an insurance evaluation report (their own format), not a regulator-facing audit doc.
- **Pricing:** Not displayed.
- **URL:** https://www.klaimee.ai/
- **Why this matters for Phoenix Audit:** Their public posture does NOT require continuous monitoring data — but a continuous signed audit trail is what an insurer would actually want once a claim is filed. There's a real partnership angle: "Phoenix Audit is the underwriting feed Klaimee doesn't have yet." Not a competitor; potential channel.

### Adjacent but worth naming — Arize AX (the sponsor)

- **What they sell:** Arize AX + Phoenix OSS. Continuous LLM/agent observability. "Online Evals" run evals on production traffic with alerting + thresholds. AX has an Audit Log feature.
- **Continuous monitoring?:** YES.
- **Generates regulator-ready signed audit reports?:** NO — they ship the observability primitive (traces, evals, audit log) but do not market a signed compliance report SKU.
- **URL:** https://arize.com/docs/ax/security-and-settings/compliance/arize-audit-log ; https://arize.com/blog/new-in-arize-ax-january-2026-updates/
- **Why this matters for Phoenix Audit:** This is the substrate we sit on. Arize ships the data plane; Phoenix Audit ships the regulator-facing artifact on top. Cleanest possible track narrative.

### Bonus finds from broader search ("AI agent runtime monitoring signed/tamper-evident audit report 2026")

- **Aegis** — pre-execution firewall for AI agents that generates "tamper-evident audit trails, with every intercepted tool call receiving a signed, hash-chained record." Research project — ACL 2026 KnowFM workshop. Not a commercial product, but it proves the technique and primes the academic-validation citation.
- **OpenKedge** — protocol formalizing agent governance with "cryptographic evidence chains linking intent to execution to outcome." Standards work, not a product.
- **nono** — kernel-enforced sandbox; cryptographic audit trail of every binary executed / filesystem change. Different layer (OS), not the LLM/agent semantic layer.
- **TierZero** (blog post: "Your AI Agents Are Changing State. There's No Audit Trail.") — confirms the market pain narrative. No shipped product line surfaced.
- **Compliora** — explicit "AI Decision Audit Trail" positioning aligned to EU AI Act + HIPAA. Visited briefly via search-result title; needs deeper dive if we want to claim full coverage. Marked PARTIAL.

URLs:
- https://nono.sh/blog/secure-agent-audit
- https://www.kiteworks.com/regulatory-compliance/ai-agent-audit-trail-siem-integration/
- https://www.tierzero.ai/blog/ai-agent-audit-trail/
- https://compliora.co/

---

## EU AI Act Article 12 — the timing question

This is the load-bearing regulatory fact for Shape A vs Shape B. The sources disagree.

**The regulation itself (Article 12, official text):**
> "High-risk AI systems shall technically allow for the automatic recording of events (logs) over the lifetime of the system."

The text says "automatic." It does NOT say "real-time," "streaming," or "continuous emission." It does NOT prescribe storage, transmission frequency, or architecture. (Source: https://artificialintelligenceact.eu/article/12/)

**Article 26(6)** — minimum 6 months retention for automatically generated logs.

**Practitioner interpretation (FireTail blog, April 2026):**
> "Automatic means logs are generated without operator intervention at the moment events occur. Scheduled exports do not count. Human-triggered captures do not count."
(Source: https://www.firetail.ai/blog/article-12-and-the-logging-mandate-what-the-eu-ai-act-actually-requires)

**Counter-take (Help Net Security, April 2026):**
> "There's no finalized technical standard for Article 12 logging yet."
> Two draft standards (prEN 18229-1 and ISO/IEC DIS 24970) remain incomplete.
(Source: https://www.helpnetsecurity.com/2026/04/16/eu-ai-act-logging-requirements/)

**Honest conclusion.** The regulation is silent on real-time vs batch. The compliance vendor consensus (FireTail, CleanAim, others) is converging on the strict interpretation: continuous emission, no batch. Standards bodies have NOT ratified anything yet. Enforcement starts 2026-08-02 for high-risk AI.

For Phoenix Audit's marketing copy: it would be irresponsible to claim "EU AI Act mandates real-time logging." The honest line is: "EU AI Act mandates automatic logging from deployment to decommission, with 6-month minimum retention; the practitioner consensus in 2026 is that batch export does not satisfy 'automatic,' but no final standard has been ratified." That nuance is defensible to a lawyer. The over-claim is not.

---

## Synthesis — answers to Abu's four questions

### 1. Does any current product combine continuous monitoring + regulator-ready signed audit reports?

**No vendor crawled today combines both with explicit cryptographic signing.**

- **Continuous monitoring** is widely owned: Lakera, Promptfoo Enterprise, F5 AI Guardrails, Credo, Holistic, Fiddler, Cisco AI Defense, Arize AX — eight vendors with shipping product.
- **Regulator-ready audit artifacts** are owned in PARTIAL form by F5 (preset EU AI Act template), Credo (policy packs by framework), Holistic ("audit-ready from day one"). None publishes a signed, cryptographically chained, tamper-evident, single-PDF report as a marketed SKU.
- **AIUC-1** issues a signed certificate but quarterly, by humans, not continuously by software.
- **Aegis** (research) proves the technique but isn't a product.

**The whitespace is real but narrower than Abu's initial framing.** It is NOT "nobody does continuous monitoring." It IS "nobody combines continuous AGENT-NATIVE monitoring with a software-generated cryptographically signed PDF that's framed as the regulator-facing artifact." That combo is open.

### 2. If we add a continuous tier to Phoenix Audit v2, who do we compete with directly?

In order of risk:
1. **F5 AI Guardrails (ex-CalypsoAI)** — closest shape, has continuous + EU AI Act preset template. Constrained by F5 sales motion.
2. **Promptfoo Enterprise (now OpenAI)** — distribution beast (OSS → 156 F500), creeping into continuous. Likely to formalize signed reports next.
3. **Credo AI + Holistic AI** — policy-pack governance with continuous monitoring; sit above the agent rather than inside the trace.
4. **Cisco AI Defense** — bundled into Cisco security; competes on procurement, not product.

The defensible Phoenix Audit moat against all four: **agent-native (span-tree level), Arize-pedigreed, signed-PDF-as-deliverable**. Not "yet another guardrail."

### 3. Hackathon scope decision — Shape A only? Shape B too? Or a hybrid?

**Recommendation: ship Shape A as v1, demo a 30-second Shape B taste, roadmap Shape B as v2.**

Reasoning:
- **7 days to deadline.** Shape B (always-on monitor) requires a deployable sidecar/proxy, persistence, alerting, dashboards. That's 3-4 weeks of careful work, not 7 days. Trying to do both = mock-the-hot-path = forbidden per CLAUDE.md.
- **Shape A is judge-legible.** "Point at agent → run 6 adversarial classes → signed PDF" is a 90-second demo. Judges score what they can see.
- **Shape B is the v2 story.** It's the answer to "what's next?" — and demonstrating that you've thought through it scores judging dimensions on vision/durability.
- **The "tiny Shape B demo" that adds credibility cheaply:** during the Shape A run, the agent under test is already being traced live via Phoenix. Add ONE thing: after the synthetic battery passes, leave the trace pipeline ON for 60 seconds, replay a couple of real prompts from a captured production trace file, show the same scoring logic firing on live data, regenerate the signed PDF with the additional spans included. That's ~1 extra story (probably 4-6h) and it visually proves "the engine is the same; v2 is just leaving it on." This is the **single highest-leverage scope expansion** available.
- **DO NOT** try to ship: real-time alerting, anomaly detection, dashboards, multi-tenant pipelines, sidecar deployment. All v2.

### 4. EU AI Act real-time requirement?

Article 12 itself is silent on real-time vs batch. It mandates "automatic recording of events over the lifetime of the system." Article 26(6) sets 6-month minimum retention. The compliance-vendor consensus in 2026 is converging on "batch doesn't count," but **no ratified technical standard exists** (prEN 18229-1 + ISO/IEC DIS 24970 are still drafts). Penalty exposure is up to €15M / 3% global turnover.

**Marketing-safe line for Phoenix Audit:** "Generates the automatic, retained, six-month-minimum event log that EU AI Act Article 12 requires of high-risk AI systems, in a signed format that survives an independent auditor's review." That's true today and doesn't over-claim on real-time language that's still being standardized.

---

## TL;DR for Abu

- Whitespace exists, but it's not "nobody monitors continuously" — eight vendors do. It's "nobody ships a software-generated, cryptographically signed, agent-native PDF report as a deliverable SKU."
- Closest direct competitors on Shape B if/when we go there: **F5 AI Guardrails** (ex-CalypsoAI) and **Promptfoo Enterprise** (now OpenAI).
- AIUC-1 is the cert-side analog. They leave a wide gap "what happens between quarters?" — that's our v2 pitch.
- Klaimee (insurance) is a channel partner, not a competitor.
- For the 7-day hackathon: **ship Shape A clean. Add a 4-6h "Shape B taste" extension that replays captured live spans through the same pipeline. Roadmap full continuous monitor as v2.**
- EU AI Act marketing: stay on the safe interpretation. Don't claim "real-time is required" — the standard isn't ratified.

---

## Sources (consolidated)

- https://www.lakera.ai/lakera-guard
- https://www.lakera.ai/risk/compliance-regulatory-risks
- https://www.guardrailsai.com/
- https://whylabs.ai/
- https://www.cisco.com/c/en/us/products/collateral/security/ai-defense/ai-defense-so.html
- https://aiuc.com/
- https://www.aiuc-1.com/aiuc-1-certification
- https://www.uipath.com/newsroom/uipath-achieves-aiuc-1-certification
- https://www.schellman.com/blog/news/schellman-becomes-the-first-accredited-auditor-for-aiuc-1
- https://www.f5.com/products/ai-guardrails
- https://www.promptfoo.dev/
- https://www.promptfoo.dev/pricing/
- https://www.credo.ai/
- https://www.holisticai.com/
- https://www.fiddler.ai/ai-observability
- https://www.klaimee.ai/
- https://www.ycombinator.com/companies/klaimee
- https://artificialintelligenceact.eu/article/12/
- https://www.firetail.ai/blog/article-12-and-the-logging-mandate-what-the-eu-ai-act-actually-requires
- https://www.helpnetsecurity.com/2026/04/16/eu-ai-act-logging-requirements/
- https://arize.com/docs/ax/security-and-settings/compliance/arize-audit-log
- https://arize.com/blog/new-in-arize-ax-january-2026-updates/
- https://nono.sh/blog/secure-agent-audit
- https://www.kiteworks.com/regulatory-compliance/ai-agent-audit-trail-siem-integration/
- https://www.tierzero.ai/blog/ai-agent-audit-trail/
- https://compliora.co/
