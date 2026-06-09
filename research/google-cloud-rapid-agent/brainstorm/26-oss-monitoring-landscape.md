# 26 — OSS AI Agent Monitoring / Observability / Safety Landscape (June 2026)

**Date:** 2026-06-05
**Author:** research sub-agent (for Phoenix Audit scope-expansion decision)
**Question:** Before we expand Phoenix Audit to include a continuous-monitoring layer on top of customer production agents, what has the OSS community actually built? What patterns have converged? What can we depend on directly? Where is the gap we still fill?

> Method. Every claim below is anchored to a URL pulled today. Where the project's own README is thin, I noted that. Nothing is from training data. Phoenix Audit's own competitor map for **commercial** products lives in `25-persistent-monitor-vs-on-demand.md` — this file is the OSS-only complement.

---

## TL;DR for Abu (read this even if you skip the rest)

1. **The OSS wedge has gotten significantly more crowded in the last ~90 days.** When `25-persistent-monitor-vs-on-demand.md` ran on the commercial side it concluded "no vendor combines continuous monitoring + cryptographically signed regulator-ready report." That gap **still holds for paid SaaS**, but on the OSS side at least three projects shipped that exact shape since March 2026: **AIR Blackbox** (Apache-2.0, OpenAI-compatible reverse proxy + EU AI Act articles 9-15 scanner + signed `.air-evidence` ZIP bundles), **Asqav** (MIT, ML-DSA-65 quantum-safe signing + hash chain + 10+ framework integrations including Google ADK), and **Microsoft Agent Governance Toolkit** (MIT, 4K+ stars, OWASP Agentic 10/10 + EU AI Act + NIST AI RMF + SOC2 mappings + Merkle audit trails). None of them is a "polished SaaS"; all are early (AIR is 17-stars-on-gateway alpha v0.1, Asqav is 169-star v0.5.5, MS AGT is 4K+ but month-old). The wedge isn't gone — it's racing.

2. **The dominant OSS architecture for "continuous monitoring + audit" has converged on the same shape AIR Blackbox uses:** OpenAI-compatible reverse proxy (Helicone-style) + tamper-evident hash chain on every record + offline-verifier script bundled with the evidence. AIR happens to be the most explicit about regulator-readiness, but the gateway-proxy pattern is shared by Helicone, AIR, Future AGI's gateway, and Asqav-MCP. The **in-process tracer** pattern (Phoenix, OpenLLMetry, Langfuse, AgentOps, TruLens) dominates observability but doesn't natively give you tamper-evident signing. The **offline test-runner** pattern (Inspect AI, Garak, DeepEval, Promptfoo, Inspect Evals, PydanticAI Evals) dominates adversarial-battery work — that's where our v1 lives.

3. **For Phoenix Audit's v2 continuous-monitoring scope:** the OSS landscape strongly suggests we should NOT build a proxy/gateway from scratch in 6 days. We have two real options: **(a)** lean on Phoenix's own trace pipeline + add a scheduled-eval job that re-runs our judge on recent spans (lowest build cost, ~1-2 stories, but no signed-record-per-action), or **(b)** integrate Asqav as a dependency for the cryptographic-receipt primitive and have our ADK agent emit signed receipts during the audit run (mid build cost, ~2-3 stories, gets us "real" tamper-evident audit trail without inventing crypto). Option (b) is the better long-term position but requires committing to a 169-star external dep. **The least-work path to "real continuous monitoring + real signed reports in v1" is option (a)** — Phoenix dashboard becomes the monitoring UI, our cron eval becomes the watchdog, our PDF generator already does the signed-report side. We'd add ~6h of work to S5 or insert a thin S6.

4. **The gap Phoenix Audit still credibly fills, post-OSS-scan:** "agent-native span-tree-aware adversarial audit + cryptographically signed regulator-ready PDF, glued into the Arize/OpenInference ecosystem already used by the day-1 buyer." None of AIR / Asqav / MS AGT do **adversarial test battery + judge-LLM scoring + signed PDF** as a single deliverable. They each cover one column — proxy-and-record (AIR), sign-every-action (Asqav), policy-enforcement (MS AGT). Our wedge becomes the **scoring + reporting layer that sits on top of any of them**, not a replacement. That reframing is good for the demo.

5. **Hackathon scope verdict (revised):** ship Shape A (on-demand audit) as v1 plus the "tiny Shape B taste" the prior brainstorm recommended. **Do NOT try to build a proxy/gateway.** If we want to credibly claim continuous-monitoring in the v2 roadmap, point to AIR Blackbox or Asqav as the substrate we'd integrate with, not something we'd reinvent. Frame Phoenix Audit as the scoring + signed-report layer on top of any OSS substrate.

---

## Per-project teardowns

### 1. Arize Phoenix (Elastic License 2.0)

- **What it does:** Open-source AI observability — tracing, evals, datasets, experiments, prompt management. Self-hostable, OpenTelemetry-based, with native auto-instrumentation for Google ADK via `openinference-instrumentation-google-adk` ([repo](https://github.com/Arize-ai/openinference/tree/main/python/instrumentation/openinference-instrumentation-google-adk)).
- **Architecture pattern:** Trace-collector + in-process auto-instrumentor. Agents register a tracer provider, OpenInference instrumentors auto-capture spans, Phoenix's OTLP collector ingests them.
- **Continuous monitoring?:** PARTIAL on the OSS side. Phoenix OSS gives you traces + evals you can run as scripts, but **online evals with alerting and threshold-based triggers are an Arize AX (paid) feature**. The OSS docs explicitly defer: "For continuous monitoring of application performance — evals on production traffic with alerting and threshold-based triggers — see Arize AX Online Evals" ([source](https://arize.com/docs/phoenix/evaluation/concepts-evals/evals-online-vs-offline)). The Phoenix client SDK exposes `client.experiments.run_experiment(...)` which is synchronous, in-script, no built-in scheduler ([source](https://arize.com/docs/phoenix/datasets-and-experiments/how-to-experiments/run-experiments)).
- **Signed-report / audit-trail capability?:** NEITHER on OSS Phoenix. Arize AX has an "Audit Log" feature ([source](https://arize.com/docs/ax/security-and-settings/compliance/arize-audit-log)) but that's an internal user-action log of the AX SaaS, not regulator-facing signed evidence.
- **Adversarial-test battery?:** NO — Phoenix evals are scoring primitives (LLM-as-a-judge, code-based), not red-team probes.
- **Maturity:** 10K stars, v17.2.0 (June 3, 2026), 712 releases ([repo](https://github.com/Arize-ai/phoenix)). Battle-tested. Active.
- **Critical primitives we can borrow:** (a) `arize-phoenix-otel.register(auto_instrument=True)` for one-line ADK instrumentation; (b) the trace dataset abstraction — we can pull recent spans into a dataset and run evals on them as a "scheduled audit"; (c) the OpenInference attribute conventions are our trace-as-assertion contract.
- **Licensing constraint:** Elastic License 2.0 on the Phoenix server. We're already using it as our substrate, so this is fine — but ELv2 prohibits SaaS-reselling Phoenix itself. We're not reselling Phoenix; we're shipping a separate auditor agent that _uses_ Phoenix. No constraint hit.
- **URL:** https://github.com/Arize-ai/phoenix

### 2. OpenLLMetry / Traceloop (Apache 2.0)

- **What it does:** OSS LLM observability built on OpenTelemetry. Instruments 15+ LLM providers + 7+ vector DBs + LangChain / LangGraph / CrewAI / Haystack / LlamaIndex / LiteLLM / Langflow via `Traceloop.init()`.
- **Architecture pattern:** In-process auto-instrumentor (OTel SDK + their instrumentor packages). Same shape as Phoenix's OpenInference.
- **Continuous monitoring?:** NO native feature. They emit OTel; you point at any OTel backend (Phoenix, Jaeger, Datadog, etc.). Monitoring/alerts are downstream.
- **Signed-report / audit-trail capability?:** NO.
- **Adversarial-test battery?:** NO.
- **Maturity:** 7.2K stars, v0.61.0 (May 31, 2026), 1,397 commits on main ([repo](https://github.com/traceloop/openllmetry)). Actively maintained.
- **Critical primitives we can borrow:** Their instrumentor packages are independent of Phoenix's OpenInference set. If we ever needed an instrumentor Phoenix doesn't ship (e.g., Haystack), Traceloop has it. Two coexisting instrumentor stacks both write OTel — no conflict, just additive coverage.
- **Licensing constraint:** Apache 2.0 — fine to depend on or learn from.
- **URL:** https://github.com/traceloop/openllmetry

### 3. Langfuse (MIT + `ee/` proprietary)

- **What it does:** OSS LLM engineering platform — observability, metrics, evals, prompt management, playground, datasets. YC W23.
- **Architecture pattern:** In-process tracer + self-hostable server. Docker Compose in 5 minutes. SDK-based instrumentation (Langchain + OpenAI auto-instrumentation built in).
- **Continuous monitoring?:** YES — explicitly supports running evals on live production traffic with model-based judges. Their docs describe "scoring live traces in production" and ship a "Code evaluator dispatcher and execution worker" for self-hosted deployments. For scheduled runs the recommendation is "schedule a Cron task in your chosen environment with the rule `cron(0 5 * * ? *)`" — i.e. you bring your own cron ([source](https://langfuse.com/guides/cookbook/example_external_evaluation_pipelines)).
- **Signed-report / audit-trail capability?:** NO. Reports are dashboards + exports, not cryptographically signed.
- **Adversarial-test battery?:** NO.
- **Maturity:** 28.5K stars (largest in this list outside DSPy), v3.178.0 (June 2, 2026), 567 releases ([repo](https://github.com/langfuse/langfuse)). Best-in-class polish.
- **Critical primitives we can borrow:** Their "external evaluation pipeline" cookbook is the cleanest documented pattern for scheduled-eval-on-traces — exact shape we'd want for continuous monitoring on Phoenix. Read the cookbook for the loop logic, reimplement against Phoenix's `client.spans` API.
- **Licensing constraint:** MIT for the main codebase; `ee/` folders are commercial-only. Stay out of `ee/`. Reading the main codebase for inspiration is free.
- **URL:** https://github.com/langfuse/langfuse

### 4. Helicone (Apache 2.0)

- **What it does:** AI gateway + LLM observability. Sits between your app and 100+ LLM providers. Logs every request, allows routing/caching/prompt versioning.
- **Architecture pattern:** Gateway interceptor. One-line change: swap `baseURL` to `https://ai-gateway.helicone.ai` (or your self-hosted endpoint).
- **Continuous monitoring?:** YES with caveats. Has [Alerts](https://docs.helicone.ai/features/alerts) that "monitor error rates and costs on LLM requests to catch issues before they impact users" with configurable 30-minute / 24-hour windows. **Scheduled eval-on-traffic is not advertised.** This is closer to "anomaly detection on metrics" than "judge LLM running on every conversation."
- **Signed-report / audit-trail capability?:** NO.
- **Adversarial-test battery?:** NO.
- **Maturity:** 5.8K stars, 5,477 commits ([repo](https://github.com/Helicone/helicone)). Apache 2.0 throughout, fully self-hostable.
- **Critical primitives we can borrow:** The gateway pattern itself — Go reverse proxy that captures every LLM call without any SDK change in the customer's agent. Helicone is the reference implementation for this pattern; AIR Blackbox borrows the same shape. If we ever build a proxy, read Helicone's request-handling code first.
- **Licensing constraint:** Apache 2.0 — free to study or depend on.
- **URL:** https://github.com/Helicone/helicone

### 5. Guardrails AI (Apache 2.0)

- **What it does:** Python framework for input/output validators on LLM responses + structured-output extraction. RAIL spec is the core DSL. Optional Guardrails Server (Flask) for HTTP-based integration.
- **Architecture pattern:** Inline validator. Wraps the LLM call: input passes through validators → LLM → output passes through validators.
- **Continuous monitoring?:** NO — the framework is for blocking bad outputs in real time, not for monitoring history.
- **Signed-report / audit-trail capability?:** NO.
- **Adversarial-test battery?:** PARTIAL — the **Guardrails Index** is a benchmark of "24 guardrails across 6 most common categories" published Feb 2025 ([repo](https://github.com/guardrails-ai/guardrails)). Not an adversarial scanner; a benchmark of defensive guardrails. Could inform our judge rubric for "agent under test resisted X attack" scoring.
- **Maturity:** 7K+ stars, v0.10.2 (June 4, 2026), 617 forks. Active.
- **Critical primitives we can borrow:** Their library of pre-built validators (`guardrails-ai/profanity-free`, `guardrails-ai/toxic-language`, etc.) is reusable as detector functions in our judge rubric. The RAIL spec format itself is not a fit for our shape.
- **Licensing constraint:** Apache 2.0.
- **URL:** https://github.com/guardrails-ai/guardrails

### 6. NeMo Guardrails (Apache 2.0)

- **What it does:** NVIDIA's programmable conversation rails for LLM apps. Uses Colang DSL (Python-like) to define dialog flows + input/output/dialog/retrieval/execution rails.
- **Architecture pattern:** In-process runtime library + optional proxy server mode. Sits between the user and the LLM.
- **Continuous monitoring?:** PARTIAL. Anonymous usage telemetry by default + supports distributed tracing to a user's observability backend.
- **Signed-report / audit-trail capability?:** NO.
- **Adversarial-test battery?:** PARTIAL — bundles LLM vulnerability scanning, jailbreak/injection detection, self-checking (fact-checking, hallucination detection). The "scan" framing is dev-time, not runtime.
- **Maturity:** 6.4K stars, 710 forks, 31 releases ([repo](https://github.com/NVIDIA/NeMo-Guardrails)). Active.
- **Critical primitives we can borrow:** The Colang attack-detection rails (jailbreak, injection) are MIT-equivalent and reusable as detector logic. The Colang DSL itself is not a fit for our shape.
- **Licensing constraint:** Apache 2.0.
- **URL:** https://github.com/NVIDIA/NeMo-Guardrails

### 7. AgentOps (MIT)

- **What it does:** Observability specifically for AI agents (vs. LLM monitoring) — session replay, execution tracking, performance analytics. Primitives: sessions, spans (agent/operation/task/workflow), events, traces.
- **Architecture pattern:** In-process — integrates via decorators and SDK initialization, not as a proxy.
- **Continuous monitoring?:** YES via hosted dashboard or self-hosted `/app`.
- **Signed-report / audit-trail capability?:** NO mention of formal audit trails, cryptographic signing, or compliance reports.
- **Adversarial-test battery?:** NO.
- **Maturity:** 5.6K stars, 108 releases, 810+ commits ([repo](https://github.com/AgentOps-AI/agentops)).
- **Critical primitives we can borrow:** Their session/span hierarchy taxonomy (agent / operation / task / workflow) is the cleanest articulation I've seen of "what's a meaningful unit of agent execution." Our judge rubric should score at the same granularity. Read their `tracer.py` for the taxonomy.
- **Licensing constraint:** MIT — free.
- **URL:** https://github.com/AgentOps-AI/agentops

### 8. Inspect AI (MIT — UK AISI)

- **What it does:** LLM evaluation framework from the UK AI Security Institute. 200+ pre-built evals. Web UI for results. Used by national safety institutes — strong pedigree.
- **Architecture pattern:** Offline test runner. Batch evals against models / agents in controlled test harness.
- **Continuous monitoring?:** NO — explicitly batch eval.
- **Signed-report / audit-trail capability?:** NO.
- **Adversarial-test battery?:** YES — extensible architecture for custom elicitation + scoring. Safety, capability, agent evals.
- **Maturity:** 2.2K stars, 5,888 commits, 542 forks, 234 tags ([repo](https://github.com/UKGovernmentBEIS/inspect_ai)). Apache-grade activity.
- **Critical primitives we can borrow:** The `Solver → Scorer` execution model is the cleanest framing of "run a scenario against the agent, score the response" we'll find in OSS. Read their `_eval/eval.py` and `_eval/loader.py` for the pattern.
- **Licensing constraint:** MIT — free.
- **URL:** https://github.com/UKGovernmentBEIS/inspect_ai

### 9. Garak (Apache 2.0 — NVIDIA)

- **What it does:** LLM vulnerability scanner. Closest thing OSS has to "adversarial battery" — probes/detectors/generators/harnesses/evaluators.
- **Architecture pattern:** Offline scanner. Sends probe prompts at the target LLM, detectors check outputs, JSONL report comes out.
- **Continuous monitoring?:** NO — scan-and-report only.
- **Signed-report / audit-trail capability?:** NO. JSONL reports + hit logs.
- **Adversarial-test battery?:** YES — 17+ probe families: DAN, prompt injection, encoding attacks, toxicity, malware generation, misleading claims, package hallucination, XSS, glitch tokens, leakage replay.
- **Maturity:** 8K+ stars, 991 forks ([repo](https://github.com/NVIDIA/garak)). The reference adversarial scanner in OSS.
- **Critical primitives we can borrow:** **The probe class structure.** Each probe has `primary_detector` + `extended_detectors` attributes. Reading `garak/probes/encoding.py`, `garak/probes/dan.py`, etc. is the highest-ROI study for our F1-F4 adversarial classes. We do NOT depend on garak as a runtime dep (per ADR-006 we reimplement natively for ADK integration), but we **read garak as our blueprint**.
- **Licensing constraint:** Apache 2.0 — free to read + free to reimplement.
- **URL:** https://github.com/NVIDIA/garak

### 10. DeepEval (Apache 2.0 — Confident AI)

- **What it does:** Pytest-like framework for LLM testing. Metrics: G-Eval, answer relevancy, hallucination detection.
- **Architecture pattern:** Offline test runner that integrates with Confident AI's hosted platform for production monitoring.
- **Continuous monitoring?:** PARTIAL — "monitor responses in production" via Confident AI (their hosted SaaS layer).
- **Signed-report / audit-trail capability?:** NO. "Generate & share testing reports" but no signing.
- **Adversarial-test battery?:** Listed as future roadmap ("Red-Teaming"), not shipped.
- **Maturity:** 15.9K stars, 9,570 commits on main ([repo](https://github.com/confident-ai/deepeval)). Very active.
- **Critical primitives we can borrow:** G-Eval is a published methodology for LLM-as-a-judge scoring with chain-of-thought + form-filling. Read their `deepeval/metrics/g_eval.py` to make sure our judge prompts are at parity.
- **Licensing constraint:** Apache 2.0.
- **URL:** https://github.com/confident-ai/deepeval

### 11. TruLens (MIT — Truera, now Snowflake)

- **What it does:** Eval + tracking for LLM apps + agents. OTel-based instrumentation. Sends spans to Jaeger, Grafana Tempo, Datadog.
- **Architecture pattern:** In-process OTel instrumentor + offline evaluator.
- **Continuous monitoring?:** PARTIAL — supports batch + inline evaluation modes.
- **Signed-report / audit-trail capability?:** NO.
- **Adversarial-test battery?:** NO.
- **Maturity:** 3.4K stars, 2.8.1 release, 119 releases, 1,750+ commits ([repo](https://github.com/truera/trulens)). Now owned by Snowflake (Truera acquired). Maintenance pace appears intact.
- **Critical primitives we can borrow:** Their **Selector API** for targeting span attributes is a thoughtful abstraction we could mirror in our judge rubric — instead of writing tree-walking code, declare "evaluate every span where `openinference.span.kind == 'TOOL'` and `tool_call.function.name in ['delete_record']`."
- **Licensing constraint:** MIT.
- **URL:** https://github.com/truera/trulens

### 12. Promptfoo (MIT — now OpenAI)

- **What it does:** CLI + library for evaluating and red-teaming LLM apps. Test runner. Security vulnerability reports.
- **Architecture pattern:** CLI test runner with local eval + web viewer.
- **Continuous monitoring?:** Enterprise tier per the prior brainstorm; OSS portion is run-on-demand.
- **Signed-report / audit-trail capability?:** NO native signing.
- **Adversarial-test battery?:** YES — red teaming + vulnerability scanning are core. Used by OpenAI + Anthropic ([repo](https://github.com/promptfoo/promptfoo)).
- **Maturity:** 21.9K stars, v0.121.14 (June 2, 2026), 8,881 commits.
- **Critical primitives we can borrow:** Their YAML-based test spec format is the cleanest "declarative adversarial test case" format I've seen. If we ever need a way for customers to write their own additional adversarial probes, copy promptfoo's spec shape.
- **Licensing constraint:** MIT — free to depend on or reimplement.
- **URL:** https://github.com/promptfoo/promptfoo

### 13. Lakera OSS (Apache 2.0 — Lakera)

- **`lakera-chainguard`** ([repo 404'd on direct fetch but `pip install lakera-chainguard`](https://lakeraai.github.io/chainguard/tutorials/tutorial_rag/)): LangChain wrapper that routes LLM calls through Lakera Guard's commercial API for prompt-injection / jailbreak detection. **It's a client SDK to Lakera's paid endpoint, not standalone protection.**
- **`pint-benchmark`** ([repo](https://github.com/lakeraai/pint-benchmark)): The Prompt Injection Test benchmark. **4,314 inputs across 30+ languages**, MIT-licensed dataset. 5 categories: prompt injections (5.2%), jailbreaks (0.9%), hard negatives (20.9%), chat conversations (36.5%), public documents (36.5%). 188 stars.
- **Continuous monitoring?:** NO for either.
- **Signed-report?:** NO.
- **Adversarial-test battery?:** YES — PINT is **directly usable as our F1 (prompt injection) ground-truth dataset**. We can `git clone lakeraai/pint-benchmark`, sample N inputs, fire them at the target agent, score with our judge. This is the cleanest OSS adversarial dataset we have for prompt injection.
- **Licensing constraint:** MIT for PINT.
- **URL:** https://github.com/lakeraai/pint-benchmark

### 14. Pillar Security OSS

- **Status:** Pillar publishes research (LLMjacking, OWASP Top 10 commentary) but does not appear to ship a standalone OSS scanner. Their public output is research blog posts and contributions to OWASP, not a tool to depend on. ([source](https://www.pillar.security/blog/operation-bizarre-bazaar-first-attributed-llmjacking-campaign-with-commercial-marketplace-monetization))
- **Critical primitives:** Research signal only. Cite their LLMjacking work in the threat-model section of our docs if we want to demonstrate awareness of post-2025 attacker behavior. Not a build dep.
- **URL:** https://www.pillar.security/ (no public GitHub org with a scanner that I could verify)

### 15. Inspect Evals (MIT — UK AISI + Arcadia + Vector Institute)

- **What it does:** Community-contributed library of evals built on Inspect AI. Three categories: capability evals (HumanEval, MBPP, SWE-Bench, GSM8K, MMLU), safety evals (adversarial robustness, jailbreak susceptibility, bias, harmful refusals), agent/assistant evals (tool-use, web browsing, multi-step task completion).
- **Architecture pattern:** Library of test cases on top of Inspect AI's offline runner.
- **Continuous monitoring?:** NO.
- **Signed-report?:** NO.
- **Adversarial-test battery?:** YES — the safety subset is directly aligned to our F-class taxonomy.
- **Maturity:** 525 stars, 342 forks ([repo](https://github.com/UKGovernmentBEIS/inspect_evals)). Less starred than Inspect AI itself but the eval catalog is the meat.
- **Critical primitives we can borrow:** Pick 2-3 safety evals from this catalog and **cite them as the ground truth our adversarial battery is calibrated against** — gives us "AISI-traceable" provenance for the demo. The MIT license lets us copy individual eval definitions wholesale; we just need to credit upstream.
- **Licensing constraint:** MIT.
- **URL:** https://github.com/UKGovernmentBEIS/inspect_evals

### 16. PydanticAI Evals (MIT)

- **What it does:** Pydantic's eval framework for agents. Code-first, in-process. Datasets / Cases / Evaluators / Experiments. Built-in evaluators + LLM-as-judge + **span-based evaluation using OpenTelemetry traces**.
- **Architecture pattern:** Offline test runner in-process. Optional Logfire integration for cloud viz.
- **Continuous monitoring?:** NO native — Logfire (paid SaaS, MIT SDK) handles the production-monitoring side.
- **Signed-report?:** NO.
- **Adversarial-test battery?:** NO native.
- **Maturity:** Part of PydanticAI ([docs](https://pydantic.dev/docs/ai/evals/evals/)).
- **Critical primitives we can borrow:** **Their "span-based evaluation" model is the closest published thing to our "trace-as-assertion" principle.** Cite it in our docs as prior art for the pattern. They claim it lets you "analyze agent execution flow" by asserting on span structure rather than text output — exactly the contract `best-practices/06` describes.
- **Licensing constraint:** MIT.
- **URL:** https://pydantic.dev/docs/ai/evals/evals/

### 17. DSPy (MIT — Stanford NLP)

- **What it does:** Framework for compositional LLM programs with prompt + weight optimizers.
- **Architecture pattern:** Offline optimization framework — compiles prompts/programs against a training set.
- **Continuous monitoring?:** NO — DSPy is not a monitoring tool. It's an optimization framework.
- **Signed-report?:** NO.
- **Adversarial-test battery?:** NO native.
- **Maturity:** 34.8K stars, v3.2.1, 1.8K projects depending on it, 4,547 commits ([repo](https://github.com/stanfordnlp/dspy)).
- **Critical primitives we can borrow:** **DSPy Assertions** (the "Computational Constraints for Self-Refining Language Model Pipelines" mechanism). They're an assertion library for constraining LLM outputs — could inform how we write our judge's pass/fail predicates. Not a runtime dep for us, just a pattern to study.
- **Licensing constraint:** MIT.
- **URL:** https://github.com/stanfordnlp/dspy

### 18. OWASP LLM Top 10 (CC BY-SA 4.0)

- **What it is:** Documentation project, not a scanner. The OWASP Foundation publishes the standard (now in 2025 edition + 2026 Agentic Top 10 extension). No official reference scanner ships from OWASP. ([source](https://github.com/OWASP/www-project-top-10-for-large-language-model-applications))
- **Third-party reference implementations exist but are weak.** `PaulDuvall/owasp_llm_top10` covers only 4 of 10 risks, explicitly described as "a teaching artifact, not a scanner" with 3 stars ([source](https://github.com/PaulDuvall/owasp_llm_top10)). It points readers to Garak / Promptfoo for production use.
- **Licensing constraint:** Documentation is CC BY-SA 4.0. We can copy + adapt the risk taxonomy verbatim with attribution. **This is what our F-class taxonomy should pin to** — name each F-class with its OWASP code (e.g., F1=LLM01, F4=LLM06). Buyer-side legibility.
- **URL:** https://github.com/OWASP/www-project-top-10-for-large-language-model-applications

### 19. Things we didn't have on the original list but found (CRITICAL)

These four projects appeared in searches for "open source AI agent continuous audit signed report 2026" and **collectively redefine the OSS landscape since April 2026**.

#### 19a. AIR Blackbox (Apache 2.0) — the closest direct shape competitor we have

- **What it does:** "Flight recorder for AI agents." OpenAI-compatible reverse proxy in Go. Sits between your code and the LLM provider (one line: `base_url=localhost:8080`). Records every prompt, completion, **and tool call** with HMAC-SHA256 tamper-evident chains. Ships `.air-evidence` ZIP bundles containing audit chain + scan results + manifest + standalone `verify.py` — auditor can verify without installing dependencies. Maps to EU AI Act articles 9, 10, 11, 12, 14, and 15. ([landing](https://airblackbox.ai/), [platform repo](https://github.com/airblackbox/air-platform), [gateway repo](https://github.com/nostalgicskinco/air-blackbox-gateway))
- **Architecture pattern:** Gateway interceptor + scanner + evidence packager.
- **Continuous monitoring?:** YES — proxy records everything, by definition.
- **Signed-report / audit-trail capability?:** YES — `.air-evidence` ZIP with verify.py, mapped to EU AI Act article numbers. Plus Ed25519-signed handoffs in `air-trust` package. **This is the closest existing thing to Phoenix Audit's regulator-PDF deliverable.**
- **Adversarial-test battery?:** PARTIAL — they ship a scanner for EU AI Act gap analysis, not a red-team attack battery in the Garak/Promptfoo sense.
- **Framework support:** v1.12.0 (May 2026) added LangChain, CrewAI, OpenAI Agents SDK, **Google ADK**, Claude Agent SDK, AutoGen, Haystack.
- **Maturity:** **Alpha v0.1.0 on the platform repo (9 stars, Feb 23 2026)** + **v1.8.0 on the gateway repo (17 stars, May 5 2026)**. Two separate orgs (`airblackbox/` and `nostalgicskinco/`). Early but active.
- **Critical primitives we can borrow OR depend on:** This is a real fork in the road. **Option (A)**: depend on AIR Blackbox as our continuous-monitoring substrate. Stand up the AIR gateway in front of the target agent, let it produce `.air-evidence` ZIPs, have Phoenix Audit consume those + emit our scored signed PDF. Their evidence already covers EU AI Act articles 9-15; we add the scoring + judge-LLM reasoning layer + the adversarial-battery side they don't do. **Option (B)**: study their HMAC-SHA256 chain implementation as a blueprint and roll our own (Apache 2.0 lets us copy code with attribution).
- **Licensing constraint:** Apache 2.0 throughout — free.
- **Critical caveat for the demo:** If AIR Blackbox's marketing reads "EU AI Act-ready flight recorder," our pitch has to differentiate clearly. **Our differentiator is the scoring + adversarial probe + judge-reasoned PDF**, not the act of recording. Phrasing matters.
- **URL:** https://github.com/airblackbox/air-platform

#### 19b. Asqav (MIT) — quantum-safe signing primitive we can depend on

- **What it does:** Python SDK that wraps agent actions with **ML-DSA-65 (FIPS 204, NIST post-quantum standard)** signatures + RFC 3161 timestamps + hash chain. Integrates with LangChain, CrewAI, LiteLLM, Haystack, OpenAI Agents SDK, LlamaIndex, smolagents, **DSPy, PydanticAI, Letta, Instructor** via Hooks API. Also exposes pytest plugin (`pytest --asqav`). Also ships an MCP server (`asqav-mcp`) so ADK agents can call `sign_action`, `verify_signature`, `gate_action`, `enforced_tool_call`, etc. as MCP tools. ([sdk repo](https://github.com/jagmarques/asqav-sdk), [mcp repo](https://github.com/jagmarques/asqav-mcp))
- **Architecture pattern:** In-process SDK + companion MCP server. **NOT a proxy** — it's library-level instrumentation.
- **Continuous monitoring?:** PARTIAL — Asqav records every action you sign; whether that's continuous depends on whether you wrap every action.
- **Signed-report / audit-trail capability?:** YES — this is its sole purpose. Receipts are hash-chained and individually verifiable. Quantum-safe (ML-DSA-65), which **matters for the EU AI Act 6-month retention + Article 12 long-horizon verifiability angle** since Ed25519 will be quantum-broken before the 10-year statute period elapses.
- **Adversarial-test battery?:** NO.
- **Maturity:** 169 stars, v0.5.5 (May 30, 2026). MIT. Pre-1.0 but active.
- **Critical primitives we can borrow OR depend on:** **Option (A)**: `pip install asqav` and call `agent.sign(action, params)` on every tool invocation in our ADK agent — gives us hash-chained signed receipts for free, with verify URLs. **Option (B)**: ignore Asqav's hosted-verify service (since `verify_url` points at `asqav.com/verify/<id>`) and study their hash-chain serialization format then roll our own offline-verifiable equivalent. **Option (B) is what we should do** — depending on a 169-star pre-1.0 service for our cryptographic chain creates a single point of failure for our regulator-facing artifact. Read Asqav's code, ship our own implementation, cite Asqav as inspiration.
- **Licensing constraint:** MIT.
- **URL:** https://github.com/jagmarques/asqav-sdk

#### 19c. Microsoft Agent Governance Toolkit (MIT) — the most credible "OWASP Agentic Top 10 coverage" claim

- **What it does:** Runtime governance for autonomous AI agents. Intercepts tool calls / API requests / agent actions at the application middleware layer. **Covers all 10 OWASP Agentic Top 10 risks** with deterministic policy enforcement. Multi-language SDKs (Python, TypeScript, .NET, Rust, Go). YAML policy DSL + OPA + Cedar. Compliance mappings for **OWASP, NIST AI RMF 1.0, EU AI Act, SOC 2**. Merkle audit trails. Microsoft-signed production builds. ([repo](https://github.com/microsoft/agent-governance-toolkit), [blog](https://opensource.microsoft.com/blog/2026/04/02/introducing-the-agent-governance-toolkit-open-source-runtime-security-for-ai-agents/))
- **Architecture pattern:** In-process middleware (recommend separate container per agent for OS-level isolation). No proxy/sidecar mode.
- **Continuous monitoring?:** YES — "SLO monitoring, chaos testing" via Agent SRE package; kill switch; red-teaming scanner for prompt injection.
- **Signed-report / audit-trail capability?:** PARTIAL — Merkle audit trails are tamper-evident **at the log level**, but per the comparison post they "do NOT cryptographically sign each individual action" the way Asqav does. Ed25519 is the algorithm — quantum-vulnerable for the 10-year horizon.
- **Adversarial-test battery?:** PARTIAL — bundled red-teaming scanner for prompt injection.
- **Maturity:** **4,000+ stars** (highest in the agent-governance space), 546 forks, 1,892 commits, 112 contributors, **9,500+ tests**. Microsoft-backed.
- **Critical primitives we can borrow:** **The OWASP Agentic Top 10 mapping is the gold-standard buyer-facing artifact.** Read `docs/compliance/owasp-agentic-top10.md` (or equivalent) for the canonical mapping. Their YAML policy DSL is also worth studying as a comparison point for our F-class taxonomy.
- **Licensing constraint:** MIT.
- **URL:** https://github.com/microsoft/agent-governance-toolkit

#### 19d. Vijil Dome (Apache 2.0) — closest OSS analog for the auditor-as-product

- **What it does:** Open-source Python library that "secures AI agents at runtime" — content detection (20+ detectors: prompt injections, jailbreaks, toxicity, PII), access control (SPIFFE/mTLS identity attestation), mandatory access control (MAC) enforcement, structured event logging. **Native support for Google ADK + LangGraph + Strands via single `secure_agent()` wrapper.**
- **Architecture pattern:** In-process runtime wrapper.
- **Continuous monitoring?:** PARTIAL.
- **Signed-report / audit-trail capability?:** NO native signing; just structured logging.
- **Adversarial-test battery?:** NO at runtime. **But Vijil's parent product** (commercial, [Vijil Evaluate](https://vijil.ai/evaluate)) does the closest commercial analog of Phoenix Audit's Shape A — adversarial test harness, "9 dimensions of trust," produces "Vijil Trust Report" with optional Vijil Trust Certificate after mitigations. Closest commercial overlap.
- **Maturity:** Vijil Dome 2 stars, v1.7.0 (May 22 2026), 35 releases ([repo](https://github.com/vijilAI/vijil-dome)). The company is well-funded; the OSS arm is a freemium funnel.
- **Critical primitives we can borrow:** Their `secure_agent()` ADK wrapper API is a clean reference. Their `agent-audit-samples` repo ([source](https://github.com/vijilAI/agent-audit-samples)) gives us **malicious / benign / edge-case ADK agents we can use as test targets in our demo** — saves us from building target agents from scratch.
- **Licensing constraint:** Apache 2.0.
- **URL:** https://github.com/vijilAI/vijil-dome

### 20. Honorable mentions from the broader sweep

These are sub-1K-star projects in the same shape — recorded for completeness, not as build deps.

- **AgentMint** ([repo](https://github.com/aerf-spec/agentmint-python)): MIT, 17 stars, v0.1.0 (March 23 2026). Decorator-based notary: `@notarise` wraps agent tool calls, produces Ed25519-signed receipts. Customer holds the keys, verify offline with openssl. Has an **AERF v0.1 open spec** with published JSON Schema — potentially copyable as a receipt format reference.
- **Future AGI** ([repo](https://github.com/future-agi/future-agi)): Apache 2.0, **1.1K stars**. End-to-end Django + Go + ClickHouse self-hosted platform with tracing, 50+ evals, simulations, OpenAI-compatible gateway (~29k req/s, P99 ≤ 21ms), 18 guardrail scanners. **The most ambitious OSS scope in the list — basically "Helicone + Langfuse + Garak fused."** No regulator-signed-report deliverable. Worth tracking; not adopting in 6 days.
- **Unworldly** ([repo](https://github.com/DilawarShafiq/unworldly)): MIT, 8 stars. "Flight recorder for AI agents." Records **file changes + shell commands**, not LLM API calls. SHA-256 hash chain + `unworldly verify`. ISO 42001 mapped. **Wrong layer for us** — they're capturing OS-level side effects of coding agents (Claude Code, Cursor, etc.), not the LLM semantic layer.
- **agent-audit-trail-mcp** ([repo](https://github.com/AiAgentKarl/agent-audit-trail-mcp)): MIT, 1 star, 3 commits. MCP server with `log_event` / `get_trail` / `verify_integrity` / `export_report` / `search_events` / `get_statistics` tools. Append-only JSONL, SHA-256 hash chain. EU AI Act Article 12 framing. **Very early — minimal codebase but the tool API is a clean reference for what MCP-side audit primitives look like.**
- **HeadyZhang/agent-audit** ([repo](https://github.com/HeadyZhang/agent-audit)): MIT, 178 stars. **Static** security scanner for LLM agents — 53 rules across all 10 OWASP Agentic categories. Prompt injection / MCP config / taint analysis. 94.6% recall on Agent-Vuln-Bench. **Static analysis only, no runtime.** Could be a complementary "pre-deploy" companion to our runtime audit but is orthogonal.
- **ARSIA Protocol** ([repo](https://github.com/arsialabs/arsia-protocol)): Protocol spec for compliance-embedded agent messaging. EdDSA-signed envelopes, 31 JSON Schemas, 613 test vectors. **Spec-level effort, not a runtime.** 1 star. Worth citing as "people are trying to standardize this" but not adopting.
- **VAP Framework** (Verifiable AI Provenance, CC BY 4.0): 5-layer provenance spec from VeritasChain Standards Organization ([source](https://medium.com/@veritaschain/ai-needs-a-flight-recorder-introducing-the-verifiable-ai-provenance-framework-e7a506cec0d2)). Spec, not a runtime.
- **Predicate-Secure** ([source](https://medium.com/@selfradiance/three-open-source-projects-are-quietly-building-the-agent-security-stack-nobody-s-talking-about-3dd5e76ebaf1)): YAML-policy wrapper for agent frameworks. Hard checks, not LLM-based. Niche.
- **AgentGate**: Bond-and-slash economic-accountability framework. Niche / wrong shape for our wedge.
- **Greywall**: Linux kernel sandbox for coding agents (Landlock + seccomp BPF). Wrong layer for us.
- **MetapriseAI/OrgKernel** ([repo](https://github.com/MetapriseAI/OrgKernel)): Ed25519 identity + SHA-256 hash-chained log + SSO/SCIM. Trust-layer infrastructure. Closer to enterprise-IAM than our wedge.

---

## Cross-cutting patterns (what the OSS community converges on)

### Architecture: three dominant shapes

Looking at all 19+ projects, the OSS community has converged on three architecture patterns:

1. **In-process tracer + collector** — used by Phoenix, OpenLLMetry, Langfuse, AgentOps, TruLens, PydanticAI, Asqav, Microsoft AGT, Vijil Dome (9 of 19). The agent imports an SDK; the SDK auto-instruments; spans flow to a backend. This is the dominant pattern.
2. **Gateway / proxy interceptor** — used by Helicone, AIR Blackbox, Future AGI gateway, Asqav-MCP partially (4 of 19). The agent doesn't change; it just talks to a different `base_url`. This pattern is winning the compliance-audit subset because **every LLM call is captured by definition, without the customer having to instrument anything**, which is a strong demo story.
3. **Offline test runner** — used by Inspect AI, Garak, DeepEval, Promptfoo, Inspect Evals, PydanticAI Evals (6 of 19). The agent runs in a test harness, scored by a runner, produces a report. This is the dominant pattern for adversarial / red-team work.

**Inline validator** (Guardrails AI, NeMo Guardrails) is a fourth pattern but it's specifically for runtime safety, not monitoring or audit, and it's less crowded.

### Crypto: hash chains have won; signing algorithm is contested

- **Hash chains using SHA-256 or HMAC-SHA256** are the universal primitive for tamper-evident logs. Asqav, AIR Blackbox, Unworldly, agent-audit-trail-mcp, OrgKernel, AgentMint, MS AGT (Merkle variant) all use a chained-hash approach. Reading any one of their implementations is sufficient — they're nearly identical.
- **Per-action signing algorithm** is contested. Ed25519 is the popular pick (AIR Blackbox handoff layer, MS AGT, AgentMint, OrgKernel, ARSIA). Asqav stands alone in arguing this is wrong for 10-year retention because of quantum risk and uses **ML-DSA-65 (FIPS 204)**. For the EU AI Act 6-month minimum + 10-year practical regulator-question horizon, Asqav's argument is correct on paper but Ed25519 is what every other project ships. **Honest take:** Ed25519 is fine for 2026; quantum break of 256-bit ECC is still 5-10 years out per NIST consensus; ML-DSA is the conservative play but not the urgent play.
- **RFC 3161 timestamping** appears in Asqav, AgentMint, Aira. This binds a hash to a third-party-attested time — useful for "the regulator asks when this happened" defensibility. None of Phoenix / OpenLLMetry / Langfuse natively does this.

### Compliance framework mappings: convergence on EU AI Act articles 9-15 + OWASP Agentic Top 10

- **EU AI Act articles 9-15** (risk management, data governance, technical documentation, record-keeping, transparency, human oversight, accuracy/robustness/cybersecurity) is the most-named regulatory mapping across projects. AIR Blackbox is the most explicit (scans for compliance per article). Arsia Protocol, Microsoft AGT, Asqav docs, AgentMint COMPLIANCE.md all name these articles.
- **OWASP Agentic Top 10** (released Dec 10 2025) is the second-most-named. MS AGT claims 10/10 coverage. HeadyZhang/agent-audit also claims 10/10. Inspect Evals safety subset partially covers.
- **NIST AI RMF 1.0** and **ISO 42001** and **SOC 2** appear less often but consistently as third-tier mappings.

This is good for us — it means our F-class taxonomy should pin to **OWASP Agentic Top 10** (most precise for agent failure modes) + **EU AI Act articles 9-15** (most relevant to the regulator-facing buyer) as the dual reference. This is what audit-notes.md should reflect.

### Adversarial battery: Garak is the OSS gold standard; PINT is the cleanest dataset

- **Garak's probe/detector architecture** is the most-studied adversarial harness in OSS (8K stars, used by industry). Reading garak/probes/\*.py is the highest-ROI study for our F1-F4 implementations.
- **Lakera PINT dataset** (4,314 inputs, MIT, 30+ languages) is the cleanest standalone adversarial dataset for prompt injection. Direct dependency candidate — we can sample from it.
- **Inspect Evals safety subset** gives us AISI-traceable provenance — citing them in our docs ladders our credibility cheaply.

---

## The "continuous monitoring layer" — which of the three architectures does OSS converge on?

Restating the options Abu defined:

- **A. Inline proxy / gateway** (Helicone-style)
- **B. In-process instrumentor** (Phoenix / OpenLLMetry style)
- **C. Pull from trace store** (read spans from Phoenix; run scheduled audits)

### Honest assessment

**Architecture B (in-process instrumentor) is what the OSS observability community converges on** — 9 of 19 projects use this pattern. It's also the pattern Phoenix natively gives us via OpenInference + ADK.

**Architecture A (gateway proxy) is what the OSS compliance / audit community converges on** — 4 of 19 projects use this pattern. AIR Blackbox is the most direct ancestor of what Abu is proposing for v2. **The reason A wins for compliance specifically is that it captures the full conversation without any cooperation from the agent code.** That matters when the customer's agent is in production and the compliance team can't ask engineering to add tracing instrumentation.

**Architecture C (pull from trace store) is uncommon as a standalone pattern but it's natural inside Phoenix's substrate.** Langfuse's "external evaluation pipeline" cookbook is the cleanest documented version. Effectively this is "C wrapping B" — the instrumentor does the capture, the cron job does the audit.

### Recommendation for Phoenix Audit's continuous-monitoring layer

**Architecture C — pull from Phoenix's trace store on a schedule.**

Reasons:

1. **It costs us the least new work.** Phoenix already collects the spans (S1 already wires this). All we add is a scheduled job that re-runs our judge over the most recent N spans every M minutes. That's a single new file + a Cloud Scheduler trigger, not a new service.
2. **It composes with our existing demo.** Same judge, same signed PDF, same scoring rubric — just running on a different input slice. The story is "the engine works the same whether you point it at synthetic attacks or at live spans." That's a powerful demo line.
3. **Architecture A (gateway) requires us to ship a Go reverse proxy or borrow AIR Blackbox.** If we ship our own gateway in 6 days, we'll fail. If we depend on AIR Blackbox, we're betting on a 17-star alpha v0.1 alpha external project for our v2 critical path, which violates "no mocking the hot path" — we'd be relying on someone else's hot path.
4. **Architecture B (in-process) is what Phoenix already does.** We're not in the "add an instrumentor" business; we're in the "score an instrumented thing" business.

**The killer demo line:** "Phoenix Audit runs the same scoring engine on Friday's synthetic adversarial battery and on Monday's live customer conversations. Same evidence, same signed PDF, only the input slice changes." That's earned credibility, not vapor.

### What we DO NOT do

- **Do not build a reverse proxy.** That's a separate-process Go service. Not 6 days.
- **Do not adopt AIR Blackbox as a runtime dep.** Cite it in `docs/architecture.md` as the canonical OSS reference for the proxy-based variant of this pattern, and note that Phoenix Audit's architecture (C) is complementary, not competing. ("If your compliance team needs full LLM-API-level capture, run AIR Blackbox in front of your agent; Phoenix Audit's signed-evidence PDF then ingests AIR's `.air-evidence` ZIP alongside Phoenix span data.") That positions us as the **scoring + reporting layer that sits on top of either substrate**.
- **Do not adopt Asqav as a runtime dep for the cryptographic chain.** Study their hash-chain format, study their ML-DSA-65 vs Ed25519 argument, ship our own simpler Ed25519 hash chain. The amended ADR in `docs/audit-notes.md` should reflect Ed25519 + SHA-256 chain as the v1 choice with a roadmap note that ML-DSA-65 is the post-quantum upgrade path.

---

## What we can borrow / reimplement / depend on directly

| Project                                  | Mode                  | What                                                                      | Why                                                |
| ---------------------------------------- | --------------------- | ------------------------------------------------------------------------- | -------------------------------------------------- |
| Phoenix + OpenInference ADK instrumentor | **DEPEND**            | `pip install arize-phoenix-otel openinference-instrumentation-google-adk` | Already our substrate per S1                       |
| Lakera PINT dataset                      | **DEPEND**            | `git submodule` or copy the JSON, MIT-licensed                            | F1 (prompt injection) ground-truth inputs          |
| Inspect Evals safety subset              | **BORROW**            | Copy 2-3 eval definitions with attribution                                | AISI-traceable provenance citation                 |
| Garak probe taxonomy                     | **STUDY**             | Read `garak/probes/*.py`                                                  | Blueprint for F1-F4 implementations                |
| AIR Blackbox `verify.py` pattern         | **STUDY**             | Read their evidence-bundle code                                           | How offline auditor verification works             |
| Asqav hash-chain serialization           | **STUDY**             | Read their SDK source                                                     | How to structure tamper-evident receipts           |
| Microsoft AGT OWASP mapping doc          | **STUDY**             | Read `docs/compliance/owasp-agentic-top10.md`                             | Buyer-facing taxonomy alignment                    |
| Vijil agent-audit-samples                | **DEPEND**            | Use ADK target agents from this repo as our demo targets                  | Saves us from building target agents from scratch  |
| Langfuse external-eval cookbook          | **STUDY**             | Read the cookbook                                                         | Cron-driven eval pattern                           |
| AgentOps span hierarchy                  | **STUDY**             | Read their tracer.py                                                      | Session/operation/task/workflow taxonomy           |
| TruLens Selector API                     | **STUDY**             | Read their selectors module                                               | Declarative span-attribute targeting               |
| PydanticAI Evals span-based eval         | **STUDY**             | Read their span evaluator                                                 | Prior art for trace-as-assertion                   |
| Promptfoo YAML spec                      | **STUDY**             | Read their config schema                                                  | Future "customer writes own adversarial test" path |
| DSPy Assertions                          | **STUDY**             | Read the assertions module                                                | Judge pass/fail predicate pattern                  |
| OWASP LLM Top 10 taxonomy                | **DEPEND** (citation) | Map F-classes to OWASP codes                                              | Buyer-side legibility                              |

The high-leverage moves are: (1) Vijil agent-audit-samples for demo targets, (2) Lakera PINT for F1 dataset, (3) Inspect Evals for AISI credibility citation, (4) study garak / AIR Blackbox / Asqav for the patterns we'll reimplement natively.

---

## The gap Phoenix Audit fills, revised

**Before this OSS scan,** Phoenix Audit's wedge was framed as: "continuous monitoring + cryptographically signed regulator-ready report — nobody combines these."

**After this OSS scan,** that framing needs to be more precise. AIR Blackbox combines exactly those two things in the proxy/gateway architecture. Microsoft AGT combines them with policy enforcement instead of adversarial testing. Asqav combines signing + framework integration but not monitoring.

**Phoenix Audit's actual, defensible wedge after the OSS scan:**

> **The agent-native adversarial scoring engine + signed regulator-ready PDF, designed to work on top of any agent-tracing substrate (Phoenix-native + complementary to gateway-style OSS like AIR Blackbox).** What's specifically ours: (a) ADK-native instrumentation via OpenInference rather than reverse-proxy capture, (b) **adversarial test battery** (which AIR / Asqav / MS AGT do not ship), (c) **judge-LLM-reasoned scoring** (which the audit-trail projects don't do — they record but don't score), (d) **single-button signed PDF** as the regulator deliverable (which most OSS leaves as "you assemble it from the dashboard"), (e) **demo legibility for the Arize judging track** — we're literally built on the sponsor's substrate.

This reframing is honest and defensible. We're not the only signed-audit-trail project anymore. We're **the only adversarial-battery + judge-scored + signed-PDF + Phoenix-native** project — which is still a single point in space nobody else occupies. The wedge held; the framing got sharper.

---

## Scope verdict on the continuous-monitoring expansion

### Is "continuous monitoring + signed PDF" achievable in 6 days IF we lean on OSS primitives?

**Yes, but only via architecture C (pull from Phoenix trace store on a schedule).**

What that looks like, concretely:

1. The S1-S5 work already in plan ships Shape A (on-demand audit) end-to-end.
2. A new story — call it S5.5 or S6 — adds: (a) a scheduled job runner (Cloud Scheduler + a tiny Cloud Run endpoint that triggers the audit agent), (b) a "live mode" flag in our orchestrator that pulls the last N hours of spans from Phoenix's `client.spans` API instead of running synthetic attacks, (c) the same judge + same PDF generator run over that input slice.
3. The PDF stamps "Live mode: spans from <start> to <end>" instead of "Synthetic battery: F1-F6" and the signing chain extends naturally.
4. Demo says: "the engine runs Friday on a synthetic test battery and Monday on Monday's actual customer conversations — same evidence pipeline."

Estimated work: 1 new file (~200 lines), 1 story, plus a Cloud Scheduler config in `infra/`. Fits in the remaining 6 days.

### Can Phoenix's own dashboard serve as the continuous-monitoring UI?

**Yes.** Phoenix already shows the live trace stream + eval results. Our role is not to replace that UI — it's to add the auditor agent that re-runs the adversarial-class scoring rubric over the live spans on a schedule and emits the signed PDF. Phoenix's dashboard answers "what happened?"; Phoenix Audit's PDF answers "is what happened compliant, and can we prove it?"

### Or do we need to build a sidecar / proxy / gateway from scratch?

**No, and we should explicitly NOT do that.** The OSS community already has AIR Blackbox as the proxy-pattern reference. Reinventing in 6 days = mocked hot path = forbidden. If we want a proxy-shaped story in the future, we partner with or integrate AIR Blackbox in v3.

### Least-work path to "real continuous monitoring + real signed reports in v1"

1. Finish S1-S5 as already planned (Shape A end-to-end).
2. Add S5.5 (Shape B taste via Phoenix scheduled eval). ~1 story, ~6h of careful work.
3. Demo Shape A live + show the scheduled job firing on captured live spans + same PDF. ~30 seconds of demo for the "what's next" beat.
4. Roadmap full Shape B (gateway-pattern, with optional AIR Blackbox integration) for v2 in the `docs/PRD.md` Future Work section.

This is the same recommendation `25-persistent-monitor-vs-on-demand.md` arrived at on the commercial side. The OSS scan confirms it — we're not missing a quick win by skipping the proxy build; we'd be drowning in scope.

---

## Open questions for Abu

1. **Should we cite AIR Blackbox in `docs/architecture.md` as the canonical OSS proxy-pattern reference?** It's the closest thing to our v2 vision and acknowledging it builds credibility ("we know what's out there; here's how we differ"). Risk: makes the wedge feel narrower. Recommendation: yes, with explicit "we're complementary, not competing" framing.

2. **Do we want to use the Vijil `agent-audit-samples` repo as our demo target agents?** Their malicious/benign/edge-case ADK agents are MIT-licensed and would save us building target agents from scratch. Risk: anchors us to Vijil's framing of agent failure modes (which may not match our F-class taxonomy 1:1). Need to spot-check. Recommendation: yes for at least one target, with our own additional targets for the F-classes Vijil doesn't cover.

3. **For the signing chain — Ed25519 (default in 5+ OSS projects) or ML-DSA-65 (Asqav's quantum-safe pick)?** Per the prior brainstorm we mentioned "cryptographically signed" without picking. ADR-014 needs to make this call. Recommendation: Ed25519 + SHA-256 chain for v1 (universal tooling, every OSS project uses it), ML-DSA-65 on the roadmap with a note about EU AI Act 10-year horizon. If pressed by a judge, defensible.

4. **Should we credit OWASP Agentic Top 10 (released Dec 10 2025) by mapping each F-class to an ASI-NN code?** The F-class taxonomy in our spec predates OWASP Agentic Top 10. If we re-pin the taxonomy now, F1=ASI-01 Goal Hijack, F2=ASI-02 Tool Misuse, etc. That gives the buyer-side OWASP-fluent compliance officer instant comprehension. Risk: small refactor across docs. Recommendation: yes — it's a 10-line change in `docs/PRD.md` and `audit-notes.md` and it pays for itself in demo legibility.

5. **Are we comfortable depending on `lakera-ai/pint-benchmark` as a dataset submodule for F1?** Pros: MIT, neutral, 30+ languages, 4,314 inputs. Cons: it's a benchmark of detection systems, not necessarily a clean fit for an agent-level injection battery (some inputs assume a chatbot context). Recommendation: yes for F1, but cherry-pick — don't blanket-include all 4,314.

6. **Do we want a roadmap line in `docs/PRD.md` about "AIR Blackbox compatibility — Phoenix Audit ingests `.air-evidence` ZIPs as an additional evidence stream"?** Would position us cleanly above whoever runs AIR Blackbox at their org. Recommendation: yes in the Future Work section, not as v1.

7. **The Asqav MCP server (`asqav-mcp`) — should we expose Phoenix Audit findings via an MCP server analogous to it?** AIR Blackbox already does this (`air-blackbox-mcp`). If we ship an MCP server alongside Phoenix Audit, our scoring + PDF is consumable by Claude Code / Cursor / Claude Desktop directly. **This is a hackathon-judge-visible "shipped multi-channel" signal** but adds scope. Recommendation: defer to v2 unless we finish S1-S6 with time to spare.

8. **Is "Phoenix Audit" the right name now that we've seen "AIR Blackbox" + "Asqav" + "MS AGT" in the same space?** Naming check from `feedback_naming_ecosystem_anchored.md` says ecosystem + function-noun. "Phoenix Audit" already follows this (Phoenix is the substrate, Audit is the function). No change needed unless we want to rename to "Phoenix Compliance" or similar. Recommendation: keep "Phoenix Audit."

---

## Sources (consolidated)

Core projects on the list:

- https://github.com/Arize-ai/phoenix
- https://arize.com/docs/phoenix/evaluation/concepts-evals/evals-online-vs-offline
- https://arize.com/docs/phoenix/evaluation/llm-evals
- https://arize.com/docs/phoenix/datasets-and-experiments/how-to-experiments/run-experiments
- https://arize.com/docs/ax/security-and-settings/compliance/arize-audit-log
- https://github.com/Arize-ai/openinference/tree/main/python/instrumentation/openinference-instrumentation-google-adk
- https://pypi.org/project/openinference-instrumentation-google-adk/
- https://google.github.io/adk-docs/integrations/phoenix/
- https://github.com/traceloop/openllmetry
- https://github.com/langfuse/langfuse
- https://langfuse.com/guides/cookbook/example_external_evaluation_pipelines
- https://langfuse.com/docs/evaluation/evaluation-methods/llm-as-a-judge
- https://github.com/Helicone/helicone
- https://docs.helicone.ai/features/alerts
- https://docs.helicone.ai/getting-started/quick-start
- https://github.com/guardrails-ai/guardrails
- https://github.com/NVIDIA/NeMo-Guardrails
- https://github.com/AgentOps-AI/agentops
- https://github.com/UKGovernmentBEIS/inspect_ai
- https://github.com/UKGovernmentBEIS/inspect_evals
- https://github.com/NVIDIA/garak
- https://github.com/confident-ai/deepeval
- https://github.com/truera/trulens
- https://github.com/promptfoo/promptfoo
- https://lakeraai.github.io/chainguard/tutorials/tutorial_rag/
- https://github.com/lakeraai/pint-benchmark
- https://www.pillar.security/blog/operation-bizarre-bazaar-first-attributed-llmjacking-campaign-with-commercial-marketplace-monetization
- https://pydantic.dev/docs/ai/evals/evals/
- https://pydantic.dev/logfire
- https://github.com/stanfordnlp/dspy
- https://github.com/OWASP/www-project-top-10-for-large-language-model-applications
- https://github.com/PaulDuvall/owasp_llm_top10

Additional projects discovered:

- https://airblackbox.ai/
- https://github.com/airblackbox/air-platform
- https://github.com/nostalgicskinco/air-blackbox-gateway
- https://github.com/jagmarques/asqav-sdk
- https://github.com/jagmarques/asqav-mcp
- https://www.helpnetsecurity.com/2026/04/09/asqav-ai-agent-audit-trail/
- https://dev.to/jagmarques/asqav-vs-microsoft-agent-governance-toolkit-what-is-the-difference-598d
- https://dev.to/jagmarques/5-open-source-tools-for-ai-agent-governance-in-2026-54le
- https://dev.to/jagmarques/ai-agent-governance-tools-compared-2026-landscape-53hm
- https://github.com/microsoft/agent-governance-toolkit
- https://opensource.microsoft.com/blog/2026/04/02/introducing-the-agent-governance-toolkit-open-source-runtime-security-for-ai-agents/
- https://github.com/vijilAI/vijil-dome
- https://github.com/vijilAI/agent-audit-samples
- https://vijil.ai/evaluate
- https://vijil.ai/dome
- https://vijil.ai/trust-audit
- https://github.com/aerf-spec/agentmint-python
- https://github.com/aniketh-maddipati/agentmint
- https://agentmint.run/
- https://github.com/future-agi/future-agi
- https://github.com/DilawarShafiq/unworldly
- https://github.com/AiAgentKarl/agent-audit-trail-mcp
- https://github.com/HeadyZhang/agent-audit
- https://github.com/arsialabs/arsia-protocol
- https://medium.com/@veritaschain/ai-needs-a-flight-recorder-introducing-the-verifiable-ai-provenance-framework-e7a506cec0d2
- https://medium.com/@selfradiance/three-open-source-projects-are-quietly-building-the-agent-security-stack-nobodys-talking-about-3dd5e76ebaf1
- https://github.com/MetapriseAI/OrgKernel
