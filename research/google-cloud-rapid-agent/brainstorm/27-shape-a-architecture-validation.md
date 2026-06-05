# 27 — Shape A Architecture Validation: Is Phoenix Audit's On-Demand Audit Architecture Sound?

**Date:** 2026-06-05
**Author:** research sub-agent
**Purpose:** Pressure-test the Phoenix Audit Shape A architecture (on-demand, URL-pointed, one-shot signed PDF) against how the actual OSS audit/eval/red-team field builds these things in June 2026. Not new ideation — validation of an existing decision before we sink another 30+ stories into a shape that might be wrong.
**Inputs:** 10 sub-questions from Abu, plus implicit constraint: cite every claim with a URL fetched today; mark `[UNVERIFIED]` where I couldn't.
**Companion files:** `25-persistent-monitor-vs-on-demand.md` (commercial map), `26-oss-monitoring-landscape.md` (OSS map). This file is the deep dive on **one shape, ten dimensions**.

---

## TL;DR (read this, skip the rest if pressed)

- **Verdict: Shape A is sound, but 3 of the 10 dimensions are underspecified in ways that will bite us mid-build.** None of the gaps are reasons to throw away the design. All three can be patched in <1 story each before they become rework.
- **Where we're aligned with OSS best practice (3):** (1) HTTP + framework-native target adapters (matches Promptfoo, DeepTeam, Garak), (2) trace-as-assertion via OpenInference (matches Phoenix's own pipeline + the LLM-judge field at large), (3) Ed25519-signed PDF + verifier (matches AIR Blackbox + Asqav).
- **Where we're misaligned or underspecified (3):** (1) **Side-effect prevention on the target's tool calls is silent in our spec** — no OSS auditor solved this either, but they document it; we don't, and our S2.1 target has a `refund()` tool that our adversarial battery will fire 6 times for real. (2) **Stateful-vs-stateless audit session contract is undefined** — we ship 6 isolated prompts today; OWASP LLM01 is materially weaker in single-turn isolation; Promptfoo's Crescendo/GOAT/Hydra strategies are explicit multi-turn; we should declare which we are. (3) **Trace-tenancy model is unstated** — does the customer's Phoenix project hold the audit traces, or ours? The "customer signs with THEIR Cloud KMS key" claim implies their tenancy; the architecture doc currently routes everything to ours.
- **One architectural change worth making BEFORE S2.x:** add a single header convention (`X-Phoenix-Audit: dry-run` + `X-Phoenix-Audit-Run-Id: <uuid>`) that the target adapter sets on every probe. Target-side honoring is the customer's choice — but emitting it costs nothing and gives us a defensible answer to "did your audit blow up my production?"
- **One non-change worth confirming:** PDF-first report is right. Promptfoo defaults to HTML, Inspect AI defaults to log files + browser viewer, DeepTeam to a `RiskAssessment` object. Compliance officers want a signed PDF. Our differentiator is correct.

Detailed per-dimension findings below.

---

## Sub-question 1 — Target connection model

### What Phoenix Audit does

Three-tier target-adapter strategy per `docs/architecture.md` lines 60-67:

- **Tier 1:** Google ADK A2A protocol (`adk_adapter.py`)
- **Tier 2:** LangChain, CrewAI, OpenAI Agents SDK via OpenInference
- **Tier 3:** HTTP black-box (`http_blackbox_adapter.py`)

### What OSS does

| Tool | Connection model |
|---|---|
| **Garak** | `rest.RestGenerator` (HTTP) + vendor SDKs (OpenAI/Bedrock/Cohere/Groq/Replicate/HF) + ggml/llama.cpp + NIM. **No browser automation.** [URL](https://github.com/NVIDIA/garak) |
| **Promptfoo** | HTTP provider, WebSocket provider, OpenAI-compat via `apiBaseUrl`, raw-HTTP (Burp-file), custom JS/Python/Go/Ruby script providers, **Playwright browser provider** explicitly for SSO / JS-heavy UIs, `echo` provider for dry tests. [URL](https://www.promptfoo.dev/docs/providers/) [URL](https://www.promptfoo.dev/docs/providers/browser/) |
| **DeepTeam / DeepEval** | "Model callback" — caller writes a Python function that wraps their target; framework treats it as opaque. No native HTTP/A2A awareness. [URL](https://www.trydeepteam.com/docs/red-teaming-introduction) |
| **Inspect AI** | Sits OUTSIDE a sandbox and sends commands in; via Docker Compose / Kubernetes / Proxmox plugin. Designed for sandboxed targets, not arbitrary live production endpoints. [URL](https://www.aisi.gov.uk/blog/the-inspect-sandboxing-toolkit-scalable-and-secure-ai-agent-evaluations) |
| **AIR Blackbox** | OpenAI-compatible reverse proxy at `localhost:8080/v1`; target points its `base_url` at AIR. **Inverts the topology** — AIR sits between target and provider, not in front of target. [URL](https://github.com/nostalgicskinco/air-blackbox-gateway) |
| **Asqav** | Wraps target inline via framework native callbacks (LangChain, CrewAI, LiteLLM, Haystack, OpenAI Agents SDK). No external probing. [URL](https://github.com/jagmarques/asqav-sdk) |
| **Microsoft AGT** | Inline wrapper: `safe_tool = govern(my_tool, policy="policy.yaml")`. 10+ framework adapters incl. ADK. [URL](https://github.com/microsoft/agent-governance-toolkit) |
| **Lakera Guard** | Inline API in front of LLM call; sub-50ms latency. (See `19-...landscape.md`.) |
| **Helicone** | Reverse-proxy gateway like AIR. |

### Verdict — RIGHT direction, missing one thing

The dominant pattern for **external probing** (which is what we are — not an inline wrapper) splits cleanly in two:

1. **HTTP + framework-native adapters** (Promptfoo, DeepTeam, Garak). This is us.
2. **OpenAI-compat reverse proxy** (AIR Blackbox, Helicone). This is a fundamentally different shape — target points at us, not vice versa.

We picked (1). That's correct for our buyer persona: a compliance officer pasting a URL is the workflow we're designing for. Reverse-proxy requires the customer to *redeploy* their agent against our endpoint, which kills the 90-second demo.

**The thing we're missing:** **no browser-automation adapter**. Promptfoo has one because real agents in production sit behind SSO portals and chatbot UIs. Our Tier-3 HTTP adapter assumes the agent has a callable API endpoint. For the day-1 user (Maya/Priya at a 5K-employee company), some of their AI agents are behind Okta SSO + a React chatbot — not directly callable. **This is a v2 gap, not a v1 gap.** Document it. Don't build it.

**Action:** add a short paragraph to `docs/architecture.md` saying "v1 requires a callable API endpoint; SSO-gated UI-only targets are out of scope for v1; Playwright adapter is a v2 roadmap item." This kills the "but my agent is behind a chatbot" objection at demo time.

---

## Sub-question 2 — Stateful vs stateless audit session

### What Phoenix Audit does

`docs/architecture.md` describes the orchestrator as `SequentialAgent: Injector → Judge → Patcher`. The injector "sends test prompts" but the spec is silent on whether the 6 prompts share a conversation thread or are 6 independent ADK sessions.

Looking at `apps/chaoslab-agent/src/chaoslab_agent/injector/faults/prompt_injection.py` (the file name from architecture.md line 56) — `[UNVERIFIED]` from research-side; the file likely exists but I can't read the implementation without leaving research scope. **The architecture doc does not declare this.**

### What OSS does

| Tool | Default |
|---|---|
| **Garak** | Stateless per probe — `atkgen` is "Prototype, mostly stateless." [URL](https://github.com/NVIDIA/garak) |
| **Promptfoo** | Both supported. Multi-turn strategies are **named primitives**: `Crescendo` "gradually escalates prompt harm over multiple turns"; `GOAT` "dynamically generate multi-turn conversations"; `Hydra Multi-turn` "adaptive multi-turn jailbreak agent"; `Mischievous User` "multi-turn conversation between a mischievous user and an agent." Single-turn is also a first-class mode. [URL](https://www.promptfoo.dev/docs/red-team/configuration/) |
| **DeepEval / DeepTeam** | **Multi-turn is a headline feature.** Specific metrics — `Knowledge Retention`, `Conversation Completeness`, `Turn Relevancy`, `Turn Faithfulness`, `Role Adherence` — exist *only* in the multi-turn mode. DeepTeam: "Multi-turn attacks try to probe a target LLM by refining its attack in each turn based on the target LLM's response in previous turn." [URL](https://github.com/confident-ai/deepeval) [URL](https://www.trydeepteam.com/docs/red-teaming-introduction) |
| **TruLens** | Span-based; conversation continuity is the caller's responsibility. [URL](https://github.com/truera/trulens) |
| **Inspect AI** | Multi-turn — explicitly built around "tool-use loops" where the model "make[s] several calls" iteratively. [URL](https://inspect.aisi.org.uk/agents.html) |

### Verdict — WE ARE UNDERSPECIFIED; this matters more than you'd think

OWASP LLM01 (prompt injection) and the equivalent MITRE ATLAS techniques are *materially weaker* as single-turn tests. The most-cited real-world prompt-injection attacks (Crescendo, indirect injection via tool output) require >1 turn of context to land. If our 6-test battery is 6 single-turns, we're testing the easy mode of the attack.

**But:** Phoenix Audit's "90 seconds end-to-end" promise + the empirical 16s/round-trip A2A latency from RAT-2 (Risk A in `RAT-2-results.md`) means multi-turn × 6 prompts = up to 96 seconds *just for the wire*. That alone would break the demo claim.

**The right v1 shape, given this constraint:**

- 3 of the 6 tests run as single-turn (cheap, fast, high signal for direct-injection / harmful-output / PII-leak categories).
- 3 of the 6 tests run as 2-turn (Crescendo-style: establish trust, then escalate). 2 turns × 16s = 32s; still inside budget.
- Declare this in the spec as a deliberate choice. **Do NOT silently ship 6 single-turns and call it "comprehensive."** A compliance officer reading our white paper will notice within 5 minutes.

**Action:** amend the relevant story file (likely the Injector story, currently S2.x) with a "Test session model" subsection that names which probes are single-turn and which are 2-turn. The Promptfoo strategy names (Crescendo, GOAT) are public; cite them as the prior art.

---

## Sub-question 3 — Live target vs sandboxed clone

### What Phoenix Audit does

The architecture doc and `audit-notes.md` are silent on this. The implicit assumption from S2.x stories is "the customer points us at whatever URL they want." Demo target is `apps/target-agent` which is our own subprocess — sandboxed by accident, not by design.

### What OSS does

| Tool | Convention |
|---|---|
| **Inspect AI** | **Sandbox-first by design.** "Inspect itself sits outside of the sandbox and sends commands into it." Docker Compose / Kubernetes / Proxmox plugins. Production targets are not the primary use case. [URL](https://www.aisi.gov.uk/blog/the-inspect-sandboxing-toolkit-scalable-and-secure-ai-agent-evaluations) |
| **Promptfoo** | **Live-target-first.** Explicit guidance: "Testing should use the production agent configuration with the same tools, permissions, and system prompt deployed in production, as restricting the agent's capabilities during red teaming hides real vulnerabilities." [URL search result] But also notes: "Due to lack of completely locked-down sandboxing support, the adversarial nature of red teaming evaluations is controlled to avoid real world impact." Caller's responsibility. |
| **DeepTeam** | Live targets via caller-defined callback. No sandbox primitive. [URL](https://www.trydeepteam.com/docs/red-teaming-introduction) |
| **Asqav** | "The system operates on live targets, not sandboxes. It signs real agent actions as they execute." [URL](https://github.com/jagmarques/asqav-sdk) |
| **MS AGT** | Inline; either dev or prod is the caller's choice. [URL](https://github.com/microsoft/agent-governance-toolkit) |
| **AIR Blackbox** | Reverse proxy; same target whether dev or prod, the proxy doesn't care. [URL](https://github.com/nostalgicskinco/air-blackbox-gateway) |

### Verdict — DOMINANT CONVENTION IS LIVE, WITH A CAVEAT

**The dominant convention is live targets** (Promptfoo, DeepTeam, Asqav, AIR Blackbox). Only Inspect AI (UK AISI; their primary use case is government-grade alignment evals on frontier models) leans sandbox-first.

This is correct for Phoenix Audit too. **A compliance officer who has to spin up a staging clone of their agent to run the audit will not use the product.** The whole demo wins on "I clicked one button and 90 seconds later got a signed PDF."

**But** Promptfoo's caveat is real: live-target probing means the auditor is responsible for not blowing up production. This is sub-question 5's problem and we'll deal with it there.

**Action:** Make the spec explicit: "Phoenix Audit probes the live target the customer points at. The customer is responsible for ensuring the URL is safe to probe, OR for declaring the target as a staging mirror in the audit config." Add this as a single sentence in the run-config schema (the `pointed-at URL` field gets a sibling `environment: production | staging | demo` enum). Audit report includes this verbatim.

---

## Sub-question 4 — Authentication to target

### What Phoenix Audit does

Architecture doc is silent. S2.x demo target is `--allow-unauthenticated` Cloud Run. This is hackathon-grade and we know it.

### What OSS does

| Tool | Auth patterns |
|---|---|
| **Promptfoo HTTP provider** | First-class: bearer token, API key (header or query), Basic, **OAuth 2.0 client_credentials / password grant with auto-refresh**, **mTLS** (`certPath` / `keyPath` / `caPath`), custom file-based auth (JS/TS/Python function). [URL](https://www.promptfoo.dev/docs/providers/http/) |
| **Garak** | `rest.RestGenerator` accepts arbitrary headers; bearer via header. No native OAuth. [URL](https://github.com/NVIDIA/garak) |
| **DeepTeam** | Caller's callback handles auth. No framework opinion. [URL](https://www.trydeepteam.com/docs/red-teaming-introduction) |
| **Google ADK A2A** | "**A2A includes provisions for authentication using standard OAuth 2.0 flows**, ensuring that only authorized agents can communicate." Plus **Signed Agent Cards** in A2A v1.0 — cryptographic signature on the Agent Card so receiving agent verifies issuer. Defaults to `--no-allow-unauthenticated` in canonical Cloud Run deploy guide. [URL](https://google.github.io/adk-docs/a2a/intro/) [URL search result] |

### Verdict — WE'RE FINE FOR V1, BUT THE PATTERN IS WELL-DEFINED

Promptfoo has done the work. For v1 demo we ship Bearer + API key (covers 90% of real targets). For v2 we add OAuth client_credentials (covers most enterprise targets) and mTLS (covers regulated targets like banking). **We don't need to invent anything here — copy Promptfoo's config schema verbatim.**

For the ADK-A2A Tier 1 adapter: A2A's Signed Agent Cards are actually a *positive signal for our pitch* — it means the target's identity is cryptographically established before we probe. Mention this in the README.

**Action:** in the v1 demo run-config, include a typed `target.auth` field with `{type: bearer|api_key|oauth|mtls, ...}`. v1 ships `bearer` and `api_key`; v2 adds `oauth` and `mtls`. Don't ship the demo with `--allow-unauthenticated` as the only option; that signals amateur to a security buyer.

---

## Sub-question 5 — Idempotency + side-effect prevention

### What Phoenix Audit does

**Nothing.** This is the gap. Our S2.1 target has a `refund()` tool. Our adversarial battery sends 6 probes that will, if they succeed, trigger real refunds. The spec is silent on what happens then.

### What OSS does

| Tool | Side-effect handling |
|---|---|
| **Promptfoo** | Explicitly documented as out-of-scope: "Promptfoo does not appear to offer built-in side-effect prevention, dry-run modes, sandboxed targets, or 'test mode' functionality for red-team probes." [URL fetch above] Recommendation is "Use dedicated test environments... Configure mock/stub providers... Implement application-level safeguards." |
| **Garak** | No dry-run mode documented. Side effects are caller's problem. [URL](https://github.com/NVIDIA/garak) |
| **Inspect AI** | Sandbox is the answer — Docker / K8s / Proxmox isolation. [URL](https://www.aisi.gov.uk/blog/the-inspect-sandboxing-toolkit-scalable-and-secure-ai-agent-evaluations) |
| **DeepTeam** | Caller's callback bears responsibility. [URL](https://www.trydeepteam.com/docs/red-teaming-introduction) |
| **AIR Blackbox** | "air-gate pauses, checks a policy, optionally asks a human via Slack, and signs the decision to a tamper-evident audit chain" before agents execute actions. **Human-in-loop approval gate**, not a dry-run flag. [URL](https://github.com/nostalgicskinco/air-blackbox-gateway) |
| **MS AGT** | Policy engine can block: `condition: "action.type in ['drop', 'delete']" → action: deny`. Same shape as AIR — policy at the gate, not a flag on the probe. [URL](https://github.com/microsoft/agent-governance-toolkit) |
| **Industry guidance (search result)** | "Tool misuse can be mitigated by sandboxing all operations, requiring human approval for critical tasks, and enforcing least-privilege access on every tool." Treated as the agent-vendor's responsibility, not the auditor's. |

### Verdict — WE NEED TO PICK A SIDE AND DOCUMENT IT

**No OSS auditor has actually solved this.** Promptfoo punts. Garak punts. DeepTeam punts. AIR/MS-AGT solve it from the *defender's* side (policy gates on the target), not the auditor's side.

There are three honest positions Phoenix Audit can take:

**Option A (the AIUC-1 path):** Require the customer to point us at a staging target. The audit report says "Audit ran against `<URL>` in environment `<staging|production>` per customer declaration." If they point at production and the refund fires, that's documented and on them. **Cost: 0 stories. Risk: a demo target that's literally our own subprocess looks like we never thought about it.**

**Option B (the convention-based path):** Define a header convention. Every probe sets `X-Phoenix-Audit: true`, `X-Phoenix-Audit-Run-Id: <uuid>`, `X-Phoenix-Audit-Dry-Run: <true|false>`. Targets that honor it skip side-effecting tool calls. Targets that don't honor it produce a clear audit-report warning ("Target did not echo the audit headers; side-effecting tool calls may have been executed for real"). **Cost: 1 story (add headers + verify echo + report). Risk: nobody honors the headers in v1, but the convention is documented.**

**Option C (the gate path):** Build a thin proxy in front of the target that intercepts and gates side-effecting tool calls. **Cost: 3+ stories. Risk: we just built AIR Blackbox, and worse, at the wrong layer (we don't see tool calls, we see agent inputs/outputs).** Reject.

**Recommendation: Option B.** It's cheap, it's defensible at the demo, and it gives us a concrete answer to the obvious question "what if my agent actually calls refund() during your audit." The header convention is the auditor's-side analog to AIR's policy gate.

**Action:** add a single new story before S2.x ships: "Define and emit X-Phoenix-Audit-* header set on every probe; verify echo from target; warn in report if absent." Wire into the existing target adapters in `apps/chaoslab-agent/src/chaoslab_agent/injector/target_adapters/`.

---

## Sub-question 6 — Trace ingestion latency

### What Phoenix Audit measured

`RAT-2-results.md` Test 1: **1.37s** emit → server-side visible roundtrip on Phoenix Cloud. Verified empirically 2026-06-04.

### What OSS does

- **Phoenix's own pipeline:** "queue-based bulk insertion pipeline... `BulkInserter` class manages asynchronous persistence, maintaining an internal queue of spans and coordinating database transactions." [URL](https://deepwiki.com/Arize-ai/phoenix/5.1-tracing-and-observability)
- **Phoenix UI live updates:** The preferences store has a `traceStreamingEnabled` flag. **The transport mechanism (polling vs WebSocket vs GraphQL subscriptions) is not documented in public docs.** [URL same as above, mark `[UNVERIFIED]` on transport]
- **Langfuse / Helicone / OpenLLMetry:** Per `26-oss-monitoring-landscape.md`, all use the same OTel-collector + UI pattern. None publish a latency SLA.

### Verdict — 1.37s IS FINE; STREAMING UX IS OUR DESIGN PROBLEM, NOT A BOTTLENECK

1.37s for emit → visible is below human reaction time at the page-load level. For a 90-second audit, that's 1.5% of the budget — irrelevant.

**The real UX question** is not "is the trace there fast enough" — it's **"how does the audit UI show progress while the audit is running."** Phoenix's `traceStreamingEnabled` exists but is undocumented; we should not rely on it. **The right pattern for the Phoenix Audit live UI is:**

- Server-Sent Events (SSE) from `chaoslab-agent` → `chaoslab-web` reporting progress at each orchestrator step (Injector started / probe 3 of 6 / Judge scoring / Patcher emitting MR). This is independent of the trace pipeline.
- Embed a Phoenix project link in the report for the customer's compliance officer to click for full trace tree. Don't try to *re-render* the trace tree ourselves.

This matches the Promptfoo + Inspect AI pattern (built-in viewers point at the underlying tool, not a re-implementation).

**Action:** none on the trace pipeline. For UX, story-S3.x (live audit progress UI) should use SSE from the orchestrator, not WebSocket-to-Phoenix.

---

## Sub-question 7 — Judge LLM choice + cost model

### What Phoenix Audit does

`JUDGE_LLM=gemini-3.5-flash` (mandatory per CLAUDE.md). Per `CLAUDE.md` cost note: 6-test battery × Gemini Flash ≈ $0.10/audit. Pro is ~1.33×; Flash-Lite is 8-11× cheaper.

### What OSS does

| Tool | Default judge |
|---|---|
| **DeepEval** | `GEval` metric — "custom model"; OpenAI is the documented quickstart. No locked-in default. [URL](https://github.com/confident-ai/deepeval) |
| **TruLens** | `Metric` + `Selector` — multi-provider. OpenAI, Azure OpenAI, LiteLLM, Gemini, Bedrock, Snowflake Cortex, HuggingFace, LangChain models all supported. **No default judge.** [URL](https://github.com/truera/trulens) |
| **Promptfoo** | Caller-configured. |
| **Garak** | Caller-configured. |
| **Inspect AI** | Caller-configured. |

### Verdict — GEMINI FLASH IS DEFENSIBLE; ARIZE-TRACK IS THE TIEBREAKER

**Industry pricing (2026):** Gemini 2.5/3.5 Flash is "$0.30/M tokens with 2M context, making it one of the most cost-efficient options." GPT-4o Mini is $0.15 input / $0.60 output per 1M. Claude Sonnet is $3.00/$15.00. [URL](https://www.cloudidr.com/llm-pricing)

**Industry bias note that matters for us:** "Research shows models rate their own outputs 0.5-1.0 points higher than a rival judge would. Using GPT-4o as judge adds bias — it may score its own style higher, so running the same eval with Claude as judge is recommended, and if rankings flip, you have a bias problem." [URL](https://www.vellum.ai/llm-leaderboard or related — paraphrased from search result]

**This is a real issue for Phoenix Audit's reputation:** if our target is itself a Gemini-based agent (which most ADK targets are), and our judge is also Gemini, the judge will systematically over-score the target. For the hackathon demo this doesn't matter — judges aren't going to run a control. For *post-hackathon credibility* this could be ugly when the first independent benchmark drops.

**But the Arize track of the hackathon REQUIRES we use the Google stack.** Gemini Flash is the right judge for v1.

**Mitigation for the white paper:** add a one-paragraph "judge bias note" to the report itself, citing the same self-rating literature, and stating "v2 will support optional dual-judge mode (Gemini + a non-Google model) with disagreement-flagging." Costs nothing now, defuses the eventual critique.

**PINT scaling math:** PINT is 4,314 prompts. At Gemini Flash $0.30/M tokens, with ~500 tokens per judge invocation (prompt + target output + rubric), 4,314 prompts × 2 calls (target + judge) × 500 tokens ≈ 4.3M tokens ≈ $1.30/PINT-full-run. Trivial. We're fine.

**Action:** no code change. Add the "judge bias note" paragraph to the PDF report template (single sentence). Mark dual-judge as v2 backlog item.

---

## Sub-question 8 — Report format

### What Phoenix Audit does

**Cryptographically signed PDF** as the primary deliverable, plus GitLab MR with hardening patches.

### What OSS does

| Tool | Primary format |
|---|---|
| **Promptfoo** | HTML dashboard + JSON. CLI viewer + web interface. No PDF. [URL](https://www.promptfoo.dev/docs/usage/sharing/) |
| **Inspect AI** | Log files in `./logs` + `inspect view` browser viewer + VS Code extension. JSON internal. No native PDF. [URL](https://inspect.aisi.org.uk/) |
| **DeepTeam** | `RiskAssessment` object with `.save(to="./deepteam-results/")`. Format not specified — looks like JSON. [URL](https://www.trydeepteam.com/docs/red-teaming-introduction) |
| **Braintrust** | Dashboard + GitHub Action PR comments. [URL search result] |
| **AIR Blackbox** | "Evidence Bundle" — tamper-evident ZIP with hash-chained records + offline verifier. **Plus signed PDF compliance report:** "The PDF report includes a document hash and Ed25519 signature for integrity verification. Additionally, RFC 3161 trusted timestamping is now included for cryptographic proof-of-existence." [URL](https://airblackbox.ai/blog/eu-ai-act-compliance-tools-compared) [URL search result on signed PDF] |
| **Asqav** | Per-action receipts (ML-DSA-65 + RFC 3161 timestamp + hash chain). No PDF mentioned. [URL](https://github.com/jagmarques/asqav-sdk) |
| **MS AGT** | "Tamper-evident" audit logs + Decision BOM (compliance integration format). **Does not explicitly mention PDF generation.** [URL](https://github.com/microsoft/agent-governance-toolkit) |
| **AIUC-1** | Issued as a formal certification doc by an accredited auditor (Schellman). PDF, signed by the auditor. [URL](https://aiuc.com/) |

### Verdict — PDF-FIRST IS RIGHT; WE'RE IN GOOD COMPANY WITH AIR + AIUC

Most LLM-eval / red-team tools default to HTML or JSON because their buyers are *engineers*. We're not selling to engineers. We're selling to a compliance officer who will literally print the PDF and hand it to a regulator. **PDF-first is the right call.**

The two OSS tools with the same compliance-officer framing — **AIR Blackbox and AIUC-1** — both output signed PDFs. Our Ed25519 + RFC 3161 timestamp + Cloud KMS-backed key matches AIR's pattern exactly.

**Our differentiation vs AIR:** AIR is reverse-proxy; you have to deploy them. We're external probe; you point at a URL. The signed PDF is the deliverable in both cases — but our acquisition cost is 90 seconds, theirs is "redeploy your agent."

**Action:** none. Ship signed PDF. Add JSON sidecar (the same payload but machine-readable) for compliance toolchain integration. This is a 2-hour add inside the existing reporter story.

---

## Sub-question 9 — Result persistence + revisability (trace tenancy)

### What Phoenix Audit does

`docs/architecture.md` says Phoenix is used for both dev (Docker self-host) and demo (Phoenix Cloud). **It does not state which Phoenix project holds the audit traces — ours or the customer's.**

### What OSS does

- **Phoenix Cloud vs self-hosted ownership:** "Arize Cloud stores inference data in their infrastructure, under their data retention policies, in their jurisdiction. In contrast, with self-hosted Phoenix, traces stay in your environment and you keep sensitive data on your own infrastructure." [URL](https://www.statsig.com/perspectives/arize-phoenix-vs-tools-analysis)
- **Phoenix multi-tenancy:** "Currently, Arize Phoenix supports authentication (OAuth2/LDAP) and authorization (ADMIN/MEMBER/VIEWER roles), but **the underlying data layer is global, and a user with VIEWER access can typically see all projects, traces, datasets, and prompts in the instance**." Group-based multi-tenancy was a feature request as of issue #10504, not shipped. [URL](https://github.com/Arize-ai/phoenix/issues/10504)
- **AIR / Asqav / MS AGT** all default to *customer's infrastructure* — they're inline. Tenancy is inherently the customer's.

### Verdict — TENANCY IS UNDERSPECIFIED AND IT CONTRADICTS THE "CUSTOMER SIGNS WITH THEIR KMS" PITCH

This is sub-question #3 of the 3 underspecified-dimensions. **It matters for compliance credibility.**

The pitch (per `CLAUDE.md` + the PLAN doc) implies:
> "the customer's compliance officer signs the report with THEIR Cloud KMS key"

But our current architecture routes traces through **our** Phoenix project (the one we created with credentials in our Cloud Run env). If the customer's audit traces sit in our Phoenix tenancy, two problems:

1. **Data sovereignty:** A regulated customer (banking, healthcare) can't have their probe-and-response data sitting in a vendor's tenancy without a DPA + SCC.
2. **The KMS pitch is hollow:** signing the PDF with the customer's key while the underlying evidence sits in our DB is theater.

**Three honest models:**

- **Model A — Vendor-tenancy (current):** all traces in our Phoenix project. PDF is the *only* customer artifact. KMS sig is the customer's, but the underlying data is ours. **Good for v1 demo. Bad for production sale.**
- **Model B — Customer-tenancy:** customer provides their Phoenix API key in the run config. We emit traces to their project. Read-back happens via their key. **Better for compliance. Phoenix doesn't support per-project key scoping cleanly today (issue #10504).**
- **Model C — Hybrid:** customer's target agent emits traces to *their* Phoenix project (that's already the standard pattern — they instrument their own agent). Phoenix Audit's orchestrator runs in our tenancy but pulls down the relevant trace slice (filtered by audit_run_id span attribute) at report-generation time. **Best of both. Matches RAT-2 Test 1's cross-tenant read pattern.**

**Recommendation: Model C for v1.** It's actually what RAT-2 Test 1 *already demonstrated* works (cross-tenant Phoenix trace ingest with 1.37s latency). The architecture doc doesn't say this; it should.

**Action:** add a section "Trace tenancy and data ownership" to `docs/architecture.md` declaring Model C. Update the run-config schema to accept `customer_phoenix.endpoint` + `customer_phoenix.api_key`. Update the report template to say "Audit traces remain in the customer's Phoenix project (project ID: X)." This is a single-story change.

---

## Sub-question 10 — Re-audit + diff

### What Phoenix Audit does

Not in the v1 spec. Implicit assumption: each audit is a fresh PDF.

### What OSS does

| Tool | Diff support |
|---|---|
| **Promptfoo** | Built-in dashboard: "pass/fail matrix, side-by-side outputs, cost per run, regression tracking over time." [URL search result] |
| **Braintrust** | Most explicit: "GitHub Action evaluates every pull request, posts per-test-case regression diffs, and blocks merges when scores fall below defined thresholds." [URL search result] |
| **Confident AI (DeepEval cloud)** | Regression testing page — green rows for improvement, red rows for regression. Open-source DeepEval doesn't include this. [URL search result] |
| **Phoenix** | "Phoenix allows comparing two agent runs side by side to spot metric differences and identify regressions after prompt or model changes." [URL search result] |

### Verdict — V2 FEATURE; CITE THE PHOENIX PRIMITIVE AS THE GROWTH PATH

Re-audit + diff is industry-standard for *engineer* eval tools. For *compliance* tools (AIUC-1, the EU AI Act audit pattern) the convention is annual full re-audit, not continuous diff. **The day-1 buyer (Maya/Priya) does not need diff in v1.**

**But:** the killer pitch for v2 is "every audit links back to the previous audit by commit SHA, and the report shows which findings were fixed, which regressed, and which are new." That's a 1-story add post-hackathon and a real growth lever.

The OSS primitive we can lean on for free: Phoenix's built-in "compare two agent runs side by side" feature. Our v2 just needs to render that comparison in our PDF format.

**Action:** none for v1. Add to the v2 roadmap section: "Audit-to-audit diff using Phoenix's native compare-runs feature; surface diffs in PDF + render in web UI."

---

## Synthesis — Is Phoenix Audit's Shape A architecture sound?

**Headline: Yes, with three patches.**

Shape A — on-demand, URL-pointed, one-time signed PDF — is the right v1 shape for our buyer persona. The dominant OSS conventions for external auditing converge on:

- HTTP + framework-native target adapters (Promptfoo, DeepTeam, Garak) — we have this.
- Live targets, not sandboxed (Promptfoo, DeepTeam, Asqav, AIR) — we implicitly do this; document it.
- LLM-as-judge with caller-chosen model (TruLens, DeepEval) — we pin Gemini Flash because of the Arize-track requirement; defensible.
- Signed PDF for compliance buyers (AIR Blackbox, AIUC-1) — we have this; we're in good company.
- Customer-tenancy for trace data (Asqav, MS AGT, AIR, and the Phoenix self-host doc itself) — we *implicitly* lean vendor-tenancy; this is the largest gap.

**The three patches we should make BEFORE writing more S2.x stories:**

1. **Side-effect convention (Option B from sub-q 5):** define `X-Phoenix-Audit-*` headers on every probe; warn in report if target doesn't echo them. One story before S2.x ships.

2. **Trace tenancy model (Model C from sub-q 9):** customer's target emits to their Phoenix project; we read cross-tenant. Update architecture doc + run-config schema. Single story.

3. **Multi-turn / single-turn declaration (sub-q 2):** name which of the 6 tests are single-turn vs 2-turn Crescendo-style. Update the relevant Injector story file. No code change required up-front, just spec clarity.

**The three places we're materially aligned with OSS best practice:**

1. External-probe-via-HTTP shape (matches Promptfoo, DeepTeam, Garak — the right call for our buyer).
2. Ed25519-signed PDF + offline verifier + RFC 3161 timestamp (matches AIR Blackbox's pattern exactly).
3. LLM-as-judge over a pinned cost-efficient model with rubric-based scoring (industry standard).

**The two places we're better than OSS:**

1. **Single 90-second deliverable to a named non-engineer buyer.** Promptfoo, Inspect AI, Garak all require engineering competence to operate. Phoenix Audit's "paste URL, click button" is the wedge.
2. **Span-tree-aware adversarial battery + cryptographic signature in one pipeline.** AIR has the proxy + signature half. AIUC-1 has the audit + signature half. Asqav has the receipts. **Nobody has all three integrated** (the conclusion from `26-oss-monitoring-landscape.md` paragraph 4 still holds after this deeper dive).

**The one place we should NOT copy OSS:**

Inspect AI's sandbox-first model. It's the right call for the UK AISI's threat model (sandboxing frontier models for safety eval) and wrong for ours (auditing a customer's deployed agent in 90 seconds). The sandbox-first instinct will produce a tool nobody runs. Live-target, with declared environment + side-effect headers, is the right shape for our buyer.

---

## URLs referenced (consolidated)

- https://github.com/NVIDIA/garak
- https://www.promptfoo.dev/docs/red-team/configuration/
- https://www.promptfoo.dev/docs/providers/
- https://www.promptfoo.dev/docs/providers/browser/
- https://www.promptfoo.dev/docs/providers/http/
- https://www.promptfoo.dev/docs/red-team/agents/
- https://www.promptfoo.dev/docs/usage/sharing/
- https://github.com/confident-ai/deepeval
- https://www.trydeepteam.com/docs/red-teaming-introduction
- https://github.com/truera/trulens
- https://inspect.aisi.org.uk/
- https://inspect.aisi.org.uk/agents.html
- https://www.aisi.gov.uk/blog/the-inspect-sandboxing-toolkit-scalable-and-secure-ai-agent-evaluations
- https://github.com/airblackbox/air-platform
- https://github.com/nostalgicskinco/air-blackbox-gateway
- https://airblackbox.ai/blog/eu-ai-act-compliance-tools-compared
- https://github.com/jagmarques/asqav-sdk
- https://github.com/jagmarques/asqav-mcp
- https://www.helpnetsecurity.com/2026/04/09/asqav-ai-agent-audit-trail/
- https://github.com/microsoft/agent-governance-toolkit
- https://opensource.microsoft.com/blog/2026/04/02/introducing-the-agent-governance-toolkit-open-source-runtime-security-for-ai-agents/
- https://google.github.io/adk-docs/a2a/intro/
- https://deepwiki.com/Arize-ai/phoenix/5.1-tracing-and-observability
- https://arize.com/docs/phoenix/tracing/concepts-tracing/how-tracing-works
- https://github.com/Arize-ai/phoenix/issues/10504
- https://www.statsig.com/perspectives/arize-phoenix-vs-tools-analysis
- https://www.cloudidr.com/llm-pricing
- https://www.skyvern.com/
- https://aiuc.com/

`[UNVERIFIED]` markers in this doc:
- Phoenix UI `traceStreamingEnabled` transport mechanism (polling vs WebSocket vs GraphQL) — not in public docs.
- Whether `apps/chaoslab-agent/src/chaoslab_agent/injector/faults/prompt_injection.py` currently sends 1 turn or N — would require reading implementation code; research-scope-only.
