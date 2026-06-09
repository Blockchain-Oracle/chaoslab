# Phoenix Audit — Designer Brief

A complete domain-knowledge handoff for the designer. **No visual direction inside this doc** — no colors, fonts, layout, components, libraries, or animation suggestions. The brief surfaces the product, the user, the artifacts, and every screen + data field that has to exist so you have full creative freedom on the visual answer.

If anything below is unclear, ambiguous, or under-specified for what you need, ask. Don't infer — invent.

---

## 1. The product in one paragraph

**Phoenix Audit is an AI agent that audits other AI agents** for safety, behavior, and EU AI Act compliance. A company points us at one of their production AI agents (a customer-support bot, a healthcare prior-authorization agent, an internal coding copilot, a voice agent — any AI agent reachable over the internet). We run an adversarial test battery against it, watch what the agent does internally as it answers each test, cluster the failures into root causes, produce a concrete fix recipe, and deliver a **cryptographically signed regulator-ready audit report** — all in roughly 90 seconds. The signed report is the durable artifact. The fix recipe optionally lands as a merge request in the customer's repo. The compliance officer files the signed report in their audit registry and presents it to regulators when asked.

> Same engine reframed: this used to be pitched as a "chaos engineering" tool for engineers. It's now pitched as a "compliance audit machine" for the Director of AI Governance at a regulated company. The product surfaces, the language, and the artifacts all speak to a compliance officer — not an engineer.

---

## 2. Who uses Phoenix Audit (the persona we design for)

There are three people in the buying / using picture. The product must work for all three at the same time.

### The Operator — the human who actually uses Phoenix Audit day-to-day

Name we use internally: **Maya** (or Priya).
Job title: **Director of AI Governance** / **Head of Responsible AI** / **AI Safety Officer**.
Company shape: a 5,000+ employee organization in a regulated industry (health insurance, fintech, hospital network, large enterprise).
What's on her desk Monday morning:

- A Slack thread with the AI Platform team asking when she'll review their new prompt-injection guardrails
- A Google Doc titled "Q3 Compliance Report — DRAFT" with three sections unfilled
- A reminder that the EU AI Act enforces in 59 days
- An email from her CRO asking for "the AI audit pack" she promised last quarter

Her current tooling: she takes screenshots of Datadog dashboards, copies and pastes them into Confluence pages, asks the AI Platform team to email her PDF exports, and stitches all of it together into a 70-page Word document her CRO never reads. She knows it's beneath her job, and she knows the regulator will ask for something more rigorous.

What she will do with Phoenix Audit: open it, paste the address of an AI agent her company runs in production, click one button, wait ~90 seconds, download a signed PDF, file the PDF in her audit registry, and (when relevant) send a fix recipe to the engineering team that owns the agent.

She's smart, senior, compliance-fluent. She knows what "GDPR Article 28" means. She does not write Python. She does not want to read a debugger trace. She wants the screen to tell her **"Here's what's wrong, here's the regulatory framework article it violates, here's what to change, here's a signed certificate of the audit."**

### The Economic Buyer — the executive one level above Maya

Title: CRO / CISO / Chief AI Officer.
Signs the procurement contract.
Will look at the audit report exactly once: when Maya forwards them the **executive summary one-pager**. That one-pager has to read as board-ready without Maya editing it.

### The ML Platform / DevSecOps team — secondary

The engineering team that actually owns the AI agent being audited. They'll be the ones who receive the fix recipe (markdown patch / GitLab merge request) and apply it. They are not on the product daily; they get a notification, click the link, review the recipe, accept or reject it in their normal code-review tool.

**Design implication of having all three:** Maya's daily workflow needs to be fast and confident. The audit report itself needs an "executive summary" section that works without Maya editing it. The fix recipe needs to look like something an engineer would take seriously (real code patches, regression tests, a real merge request).

---

## 3. What the product actually does (the moment it's built around)

The killer demo moment — the thing the product is designed to make happen on screen — has a name we use internally: **the cascade-flip**.

The story it tells, in plain English:

> Maya opens the product. She pastes her company's production prior-authorization agent address. She picks "EU AI Act — high-risk system." She clicks Run.
>
> A live progress view appears. Six adversarial tests fire against her agent. Six tests means six discrete probe-and-response interactions she can watch happen in real time. Each test cites the industry-standard framework it's drawn from (HarmBench / OWASP LLM01 / MITRE ATLAS / CARES) right there in the test header, so a regulator reading later sees "these are not tests we invented, these are tests the security community has agreed on."
>
> Three pass. Three fail.
>
> The three failures get analyzed. The product notices all three failures share a single underlying cause — the agent calls one of its tools without first calling another tool that's supposed to validate the request. Three independent surface-level failures collapse into ONE root cause. This collapse is the **cascade-flip**: visually, three distinct failure indicators converge into one.
>
> Maya clicks "Generate hardening recipe." A markdown patch appears in 4 seconds: change this line of the system prompt, add this input validator to this tool. One more click sends it as a merge request to the engineering team's GitLab repo, with regression tests included.
>
> Maya clicks "Sign and file." A cryptographic signature operation runs (visible in the UI). A signed PDF + signed JSON download. Maya files it. Done.

The voiceover line we want the screen to support, without saying it: **"Three failures. One root cause. Patch in four seconds."**

That phrase is the product. Every screen the user touches between "paste URL" and "signed PDF in hand" should serve that story.

---

## 4. The four artifacts the product produces

Every audit run produces these. The designer needs to know they exist so the result-side screens have somewhere to send the user.

### Artifact 1 — The signed audit report

The hero artifact. A PDF, cryptographically signed with the customer's compliance officer's Cloud KMS key. Also delivered as a parallel signed JSON for machine consumption.

Contents (sections the PDF has):

- Cover page with audit metadata (audit run ID, target agent's URL, target agent's commit SHA if available, regulatory framework chosen, timestamp, signing key fingerprint)
- A cover-page paragraph about data residency. **Two variants exist**, picked automatically based on which hosting mode the customer chose (see §10 below). The cover-paragraph language is legally locked verbatim — the designer does not rewrite it; it renders as-is into the PDF template.
- Executive summary one-pager (this is the page the CRO reads)
- Six adversarial-test entries, each entry showing: test source citation, the prompt that was sent, the agent's response, judge verdict (pass / fail), regulatory framework article violated if fail
- Failure-cluster section: each root-cause cluster with the spans it explains
- Hardening recipe section: the prompt patch + tool validation diff that was generated
- An optional "header convention" warning paragraph (legally locked verbatim) that appears IF the target agent didn't signal it honored Phoenix Audit's audit-mode protocol — see §11 below
- Regulatory framework mapping appendix (EU AI Act articles, NIST AI RMF, HIPAA, SOC 2 — depending on which framework the customer picked)

Maya downloads this. Files it in her audit registry. This is the product.

### Artifact 2 — The hardening recipe

A separate, complete artifact (not the same as the report's recipe section). Delivered three ways:

- As a markdown file uploaded to Google Cloud Storage. The user gets a downloadable URL. The Markdown is human-readable and engineer-friendly.
- Optionally, as a real merge request opened against the customer's GitLab repository. The MR contains: a new branch with prompt patches applied, tool validation diffs, and regression test cases. The customer authenticated GitLab once during setup. This is real — not a screenshot, not a mock; an actual MR the engineering team can review and merge.
- As JSON (the underlying structured object both renderers consume).

### Artifact 3 — The failure cluster set

The structured output of the analysis phase. Up to 5 clusters per audit. Each cluster has: a cluster ID, a one-sentence root cause, a count of how many failures it explains, a list of Phoenix span IDs (deep-link targets into the agent's internal trace tree), and a list of which adversarial test categories the failures came from.

This is what visually drives the **cascade-flip** on screen. Three failure markers visually converge into one cluster.

### Artifact 4 — The Phoenix trace

Every audit run produces traces of the target agent's internal execution (its tool calls, its LLM calls, its retries, its tool responses). These traces are stored in a Phoenix observability backend (see §10 for which Phoenix instance). The audit report references span IDs from these traces, so a regulator can drill down into "here is the exact internal moment the agent failed" if they want.

In the live audit UI, individual cells / probe markers can be clickable — they open the corresponding Phoenix trace span in a separate Phoenix view. The designer doesn't need to design the Phoenix view itself (that's a third-party tool); just understand that span IDs are first-class clickable things.

---

## 5. Vocabulary the designer should use consistently

The product talks to a compliance officer. Word choice matters as much as visual choice. Use these terms verbatim. Avoid the alternatives in the right column.

| Use this                                           | Not this                                                              |
| -------------------------------------------------- | --------------------------------------------------------------------- |
| Phoenix Audit                                      | ChaosLab, Trust Auditor, audit tool, eval tool                        |
| Target agent                                       | Customer agent, your agent, their agent, the bot, the LLM             |
| Audit                                              | Test run, eval run, scan, check                                       |
| Audit run                                          | Session, job, execution                                               |
| Adversarial test (or just test)                    | Fault, attack, injection, probe (probe is OK inside engineering text) |
| Test battery                                       | Test suite, test plan                                                 |
| Failure                                            | Bug, error, defect                                                    |
| Root cause cluster                                 | Group, bucket, category                                               |
| Hardening recipe                                   | Fix, patch, solution, remediation steps                               |
| Signed audit report                                | PDF, report, document                                                 |
| Regulatory framework                               | Standard, policy, rule set                                            |
| EU AI Act / NIST AI RMF / HIPAA / SOC 2            | "compliance" (alone — always name the framework)                      |
| Customer                                           | User (when referring to the buying company)                           |
| Operator                                           | User (when referring to Maya specifically)                            |
| Compliance officer                                 | Auditor (auditor is what Phoenix Audit is, not the human using it)    |
| Cryptographically signed                           | Verified, certified, validated                                        |
| Continuous monitoring                              | Always-on, live monitoring                                            |
| 90-second audit                                    | Fast audit, real-time audit                                           |
| Open the audit (when clicking into a finished one) | View report                                                           |
| Run audit (the primary action)                     | Start scan, kick off test, launch                                     |

**Terms from real-world frameworks — these are NOT made up; they are recognized industry names. Use them as-is, capitalized as shown:**

- **EU AI Act** — the European Union's AI regulation. Articles 9, 11, 12, 13, 14, 15, and 72 are the ones we map findings to. Annex IV is the documentation pack regulators ask for.
- **NIST AI RMF** — US National Institute of Standards and Technology AI Risk Management Framework.
- **HIPAA** — US healthcare data regulation.
- **SOC 2** — US service organization controls (auditing standard).
- **HarmBench** — an open-source adversarial test dataset from CAIS. We cite specific test rows.
- **OWASP LLM Top 10** — the Open Worldwide Application Security Project's list of top LLM security risks. We cite "OWASP LLM01 — Prompt Injection" by ID.
- **MITRE ATLAS** — MITRE's adversarial threat landscape for AI systems. We cite specific technique IDs like "AML.T0051."
- **CARES** — a healthcare-specific safety benchmark we cite.
- **GDPR Article 28** — defines the "data processor" obligations Phoenix Audit takes on when it hosts trace data on behalf of a customer.
- **Cloud KMS** — Google Cloud's Key Management Service. Where the signing key lives.

The designer should treat these names like brand names: never paraphrase, never translate, capitalize as shown. A compliance officer recognizes them instantly; that recognition is a load-bearing trust signal.

---

## 6. The surfaces (every screen / view / page that has to exist)

Phoenix Audit is a web product. These are the surfaces. Each one is described in terms of what it's for, what data it shows, and what actions a user can take from it — never what it looks like. The designer is free to consolidate, split, or re-route these as the visual answer dictates. If two of these naturally collapse into one view, do it. If one should become a multi-step flow, do it.

### Surface A — Landing page (the public marketing page)

Lives at the root URL of phoenix-audit's hosted domain. Anyone with the URL can see it without logging in. Its purpose is to communicate the product and convert a Director of AI Governance into trying it. It is the page judges will see first (this is a hackathon-submitted product, so judges land here from a Devpost link before any login flow).

What's on it (the things that have to be expressible somewhere on this page; the designer arranges):

- The product name (Phoenix Audit) and one-line description ("the AI agent that audits your other AI agents")
- The "why now" hook: the EU AI Act enforces in 59 days with €15M penalty exposure (this date and number are real and change over time — design it so the number is a content slot, not hardcoded into the design)
- The headline metric / killer story: "three failures, one root cause, patch in four seconds"
- A primary call-to-action that starts an audit (this is the button that pushes the user into Surface B / Surface D)
- A secondary call-to-action for someone who wants to look without running anything yet — a "watch a pre-recorded audit run" path (this goes to Surface D)
- The competitive positioning (one or two sentences): comparison to the Big-4 consulting alternative (€80K-€250K per audit pack, 12-18 months, vs. 90 seconds signed and continuously updatable)
- Logos of the sponsoring technology stack the product is built on: **Arize Phoenix** and **Google Cloud Agent Builder**. These are real partner names; they need to be representable somewhere on the page because they earn judging credit
- A footer with: open-source license (Apache-2.0), attribution to external libraries we cite (`deepankarm/agent-chaos`, Lakera PINT, the HarmBench / MITRE / OWASP / CARES citations), a GitHub link to the source repo
- An Open Graph image for social-link previews (1200×630 pixels). The Open Graph image should communicate the killer demo moment in a single frame because that's what gets posted on X and LinkedIn

### Surface B — "Start a new audit" wizard

The form-shaped path from "I want to run an audit" to "an audit is running."

The user supplies four pieces of information. The designer decides whether this is one screen, four screens, or some intermediate. The four pieces:

1. **Target agent address.** The URL or A2A address of the AI agent the user wants audited. Text input. Validated — must be a reachable HTTPS URL (or an A2A address for ADK-native agents). Common errors to surface: not a URL, not reachable, returned an error to the probe ping.
2. **Audit depth.** Two-way choice: **Depth 1 — Black-box** (zero setup, the audit only sees what comes in and out over HTTP, results are correct but root-cause clustering can't see inside the agent) vs. **Depth 2 — Instrumented** (the operator added a 3-line snippet to their agent's startup that lets Phoenix Audit see the agent's internal trace tree — root-cause clustering works, this is the demo path). Each option has helper copy explaining what the operator has to do; Depth 2 includes a link to "how do I add the snippet" docs.
3. **Regulatory framework.** Single choice among: EU AI Act, NIST AI RMF, HIPAA, SOC 2 + AI, Custom. This selection drives which articles get cited in the audit report.
4. **Override settings (optional, collapsed by default).** Power-user controls: skip specific adversarial categories, cap the number of tests, override the judge model. Most operators will never open this section; it has to be present so power users can adjust, hidden by default so it doesn't intimidate.

Plus, when the customer is in BYO Phoenix mode (see §10), an additional section appears for their own Phoenix endpoint URL, API key, and project name.

Plus, a single "Run audit" button that launches into Surface C.

### Surface C — Live audit progress (the heart of the demo)

The screen the user lands on the moment they hit "Run audit." It streams in real time while the audit happens. This is where the cascade-flip happens. This is the surface where Devpost judges will spend the most attention.

What's happening backstage while this screen is up:

- The orchestrator runs through three phases sequentially: **Injector** (sends the adversarial tests to the target), **Judge** (analyzes pass/fail and clusters failures), **Patcher** (generates the hardening recipe). The current phase is broadcast to this view over a server-sent events stream — every phase change is a discrete event the UI receives.
- For each individual adversarial test sent: a test-started event arrives, then a test-completed event with pass/fail and the Phoenix span ID for drill-down.
- Once the Judge phase runs, the failure cluster set arrives — this is the moment the cascade-flip wants to happen.
- The Patcher phase produces the hardening recipe object.

What the user needs to see (in some form — designer decides shape):

- **What phase are we in?** A clear indicator of "we're sending tests" → "we're analyzing" → "we're generating the fix" → "done." Operator must never feel like the screen has frozen during the ~90-second window.
- **Each test, as it lands.** Some representation of each of the six tests (or however many the customer chose), with its pass/fail outcome appearing as soon as the result arrives. Each test displays its source citation (HarmBench / OWASP LLM01 / MITRE ATLAS [exact AML technique ID] / CARES) so the regulatory provenance is visible at glance.
- **The agent pipeline.** A small visualization showing the three-phase audit pipeline (Injector → Judge → Patcher) and the target agent it talks to. The "active" agent in the pipeline glows / pulses / animates while it's working. This is one of the product's signature visuals — it communicates that Phoenix Audit is itself a multi-agent system. It also gives the user something to watch during the otherwise-silent processing phases.
- **The cascade-flip moment.** When the Judge phase emits the failure cluster set, the visualization should communicate "three failures collapsed into one root cause" by some on-screen movement. Three failure markers visually converging into one cluster is the conceptual hook. This is the 1:30-2:15 moment of the 3-minute demo video.
- **A receipt-like result panel** that slides into view at the end of the run with: total tests, pass/fail breakdown, root causes identified, links to the signed PDF download, link to the markdown recipe file, link to the GitLab MR if it was opened, total cost of the audit run (a small number — pennies of LLM cost), wall-clock duration of the run.

The Phoenix span IDs surfaced for each test are clickable links that open in a new tab into the Phoenix UI (a third-party tool we don't design).

### Surface D — Pre-recorded replay (the "show me without running it" path)

A pre-seeded audit run the user can watch from start to finish without supplying a target. Plays back in ~22 seconds. Used by:

- Judges who want fast gratification without configuring a target
- Marketing visitors who want to understand the product before signing up
- Demo videos that need a deterministic path that won't error mid-recording

Visually identical to Surface C (the live audit view) — same components, same cascade-flip, same receipt — but the data is pre-seeded rather than live. The user can replay, scrub, or restart.

### Surface E — Audit history / dashboard

After Maya runs her first audit and lands back at her home screen, she has a history. Every audit she's ever run is here, listed with: timestamp, target agent (URL), regulatory framework chosen, pass count / fail count, the signed PDF download link, the recipe link (if generated), the merge request link (if opened).

She can:

- Open any past audit (re-render its result view as if she just ran it)
- Search / filter by target agent, by framework, by date
- See an aggregate count for her own management ("47 audits this quarter, 12 with findings, 11 fixed")

Empty state for a brand-new operator: this view exists but contains "you haven't run any audits yet — start your first" with a path back to Surface B.

### Surface F — Target agent setup detail

A view per registered target agent. The customer can register multiple target agents (their prior-auth bot, their support copilot, their voice agent) and audit them on a schedule or on demand. This view shows:

- The agent's URL, framework type (ADK / LangChain / CrewAI / OpenAI Agents SDK / generic HTTP — see §7), depth setup (Depth 1 or Depth 2)
- The audit history just for this agent
- A "run audit now" button
- A "schedule continuous monitoring" toggle (see §8) and the schedule configuration when enabled
- For Depth 2 agents: the 3-line instrumentation snippet, copyable, with the agent's specific configuration filled in
- For Depth 1 agents: a "ready to upgrade to Depth 2 — here's the snippet" promotion

### Surface G — Hardening recipe view

After a hardening recipe is generated, the user (or the engineer the user forwards it to) can view it on screen. Shows:

- The list of root cause clusters this recipe addresses
- For each cluster: the prompt patches it recommends (which section of the system prompt — `system_prompt`, `tool_description`, or `few_shot_example` — and the operation — `insert`, `replace`, or `append`, plus the new text)
- The list of tool validation diffs (which tool, which operation — `add_input_validator`, `add_output_validator`, `add_retry_policy`, `add_timeout`, plus the code patch in unified diff format)
- The regression test cases (each one: an input prompt + the expected output) the engineer should add to their test suite
- An estimated resilience improvement number (between 0.0 and 1.0)
- Buttons to: download as markdown, open the GitLab MR (if it exists), copy as JSON

The view itself doubles as the markdown-recipe preview before download.

### Surface H — Continuous monitoring configuration

(Optional / lower priority — but in scope.) A view where Maya can turn on continuous monitoring against a target agent. Continuous monitoring works by Phoenix Audit waking up on a schedule (hourly, daily, weekly), pulling the last N hours of the target agent's real production traces from its Phoenix project, running the same judge over those real conversations (not synthetic adversarial tests), and producing a signed report. The point: catch real failures that happened in production, not just synthetic ones.

The view needs to express: which agent, what cadence (hourly / daily / weekly / custom cron), what window size (last N hours of traffic), where to deliver the signed report (email it to a list, file it to a registry, both). And it lists the audits that have been produced from this schedule so far.

### Surface I — Signed PDF preview / download

Browser-side preview of the signed PDF before download. The PDF itself is a server-generated artifact (the designer doesn't lay out PDF pages — that's done programmatically — but the preview surface in the web UI is part of the product). The preview shows page thumbnails, lets the user verify the content, and offers download as PDF / download as signed JSON / sign-and-file action.

The "Sign and file" action triggers a Cloud KMS signing operation that the UI surfaces visibly. The user sees a brief signing-in-progress state before download completes.

### Surface J — Settings (account-level)

For Maya's account: profile, organization name, the email address for erasure requests, default regulatory framework, the customer's Cloud KMS key reference (where signed PDFs get signed against), GitLab connection (one-time OAuth), Phoenix Audit hosting mode (default vs. BYO — see §10), and the BYO Phoenix endpoint + project name if BYO is selected.

### Surface K — Error / empty / blocked states

For every surface above:

- An idle / not-yet-started state
- A loading state (especially Surface C, which runs for ~90 seconds)
- An empty state (no audits yet, no recipe yet)
- An error state (target agent unreachable, signing key not configured, GitLab connection broken)
- A blocked state (audit cap reached, key not provisioned)

Critical for Surface C: a **non-anxious loading experience** for the full 90-second window. Maya is standing there watching. The screen has to feel alive even between phase transitions. The agent pipeline visualization (above) is the main mechanism for this; phase-change events are the secondary mechanism.

---

## 7. Cross-framework reality (what kinds of agents Phoenix Audit can audit)

The target agent can come from any of these frameworks. The customer picks the framework when registering the agent. The visual language should not pretend all targets are the same.

| Framework name (use exactly)           | What it is                                                                                                                                  | How Phoenix Audit talks to it                                                         |
| -------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| **Google ADK (Agent Development Kit)** | Google's official agent framework. Tier 1 — Phoenix Audit's native support.                                                                 | A2A protocol (agent-to-agent calls — Google's standard).                              |
| **LangChain / LangGraph**              | Popular open-source framework. Tier 2.                                                                                                      | HTTP endpoint the customer wraps the LangChain runnable in.                           |
| **CrewAI**                             | Open-source multi-agent framework. Tier 2.                                                                                                  | HTTP endpoint.                                                                        |
| **OpenAI Agents SDK**                  | OpenAI's official agents SDK. Tier 2.                                                                                                       | HTTP endpoint.                                                                        |
| **Custom HTTP agent**                  | Any agent at all — Vapi, ElevenLabs voice, Skyvern web-automation, n8n, Zapier AI Action, anything reachable over HTTP. Tier 3 — black-box. | HTTP endpoint. Phoenix Audit doesn't see inside; only what comes in + what comes out. |

**Tier explanation for the designer (relevant because it affects what we promise on which screen):**

- **Tier 1 (ADK)** — fully supported. Full root-cause clustering. Demo path.
- **Tier 2 (LangChain / CrewAI / OpenAI Agents SDK)** — supported via OpenInference instrumentation. Customer adds the instrumentation; we get rich trace data.
- **Tier 3 (HTTP black-box)** — supported, but limited. No internal trace visibility. The audit report still produces — but the failure section is per-test, not per-cluster (we have nothing to cluster across).

The designer should plan for the framework choice being visible on Surface F and labeled appropriately on Surface C (so a Tier 3 audit's lack of root-cause clustering is visible-by-design, not a missing feature).

**The audit depth choice in Surface B (Depth 1 vs Depth 2) cross-cuts framework choice.** A Tier 1 ADK agent can still be audited at Depth 1 (black-box). The customer chooses the depth based on how much trace access they're willing to grant.

---

## 8. The user flow, end to end

Stepping through what Maya does when she opens Phoenix Audit. The designer is welcome to collapse, re-order, or re-shape — but every step needs a home somewhere.

### 8.1. First-time Maya

1. Lands on Surface A (the landing page). Reads the pitch. Clicks "Watch a sample audit" or "Start a new audit."
2. (If she clicked watch-sample): she ends up on Surface D playing a pre-recorded run. She watches the cascade-flip. She clicks "Run one against my own agent" — which routes to Surface B.
3. (If she clicked start-audit): she signs in (or signs up if first-time). Account / billing flow is light-touch — for the hackathon, no payment.
4. She lands on Surface B (the new-audit wizard). Fills in target URL, audit depth, regulatory framework, optional overrides. Clicks "Run audit."
5. She lands on Surface C (the live audit). Watches the 90-second flow play out. Sees the cascade-flip. Sees the receipt at the end.
6. From the receipt, she opens the signed PDF preview (Surface I). She downloads it. She optionally clicks "Open as GitLab MR" — the merge request opens in a new tab (real, against her connected GitLab repo).
7. She's now in Surface E (her audit history) — her first audit is here, listed.

### 8.2. Returning Maya

Lands on Surface E (audit history is now her home). Clicks "Start a new audit" to repeat the loop, or clicks an existing audit row to open it.

### 8.3. Engineering team (downstream)

A platform engineer at Maya's company gets a notification (email / Slack hook) that Maya filed a GitLab MR against their repo. They click the link. They land in their normal GitLab UI (not Phoenix Audit) and review the MR like any other code change. The MR contains: branch with prompt patch + tool validation diffs + regression test cases. They merge or comment.

### 8.4. Continuous monitoring (Maya enables it later)

From Surface F or Surface H, Maya turns on continuous monitoring. She picks a cadence (daily). Every day, a fresh signed audit appears in her audit history without her touching the product. She gets an email summary; if the audit had findings, she opens it and the flow looks identical to a synthetic audit.

---

## 9. What data flows through each surface

For Surface C and Surface D in particular, the designer needs to know the data shape because the surface visualizes streaming data, not static state.

### Server-sent events from `/stream`

The live progress view opens a server-sent event stream. The events that arrive on the wire:

- `hello` — first event when the connection opens. Carries `{ run_id, status: "connected" }`.
- `phase_change` — fires when the orchestrator transitions phase. Carries `{ phase, run_id }` where `phase` is one of: `"queued"`, `"injector"`, `"judge"`, `"patcher"`.
- `complete` — fires when the audit finishes successfully. Carries `{ phase: "succeeded", run_id }`.
- `cancelled` — fires if the user disconnects or cancels mid-run.
- `error` — fires if the audit crashes. Carries `{ run_id, detail }`.

Per-test events (currently being built — Epic 5 wires this) will additionally carry per-probe pass/fail as each test completes, with the test's source citation, the prompt, the response, and the Phoenix span ID.

### The audit run record (what every audit has)

- Run ID — formatted as `run_` + 12 hex characters
- Created-at timestamp (ISO 8601 UTC)
- Target agent URL (or agent ID if the target was pre-registered)
- Regulatory framework chosen
- Phase: queued, injector, judge, patcher, succeeded, failed
- Adversarial test list (the six probes for the demo path) with per-probe pass/fail and citation
- Failure cluster set (up to 5 clusters)
- Hardening recipe (the structured object)
- Signed PDF download URL
- Markdown recipe URL
- GitLab MR URL (optional)
- Cost (USD, typically a few cents)
- Wall-clock duration (seconds)

### The hardening recipe (the structured artifact a designer mocking up Surface G needs)

This schema is locked. Fields:

- `recipe_id` — `recipe_` + 12 hex characters
- `target_agent_id`
- `generated_at` — ISO 8601 timestamp
- `cluster_set` — the failure clusters this recipe addresses. Contains: `clusters` (list of failure-cluster objects, max 5), `total_failures` (integer), `clusterer_model` (the LLM used to cluster — always `gemini-3.5-flash`)
- `prompt_patches` — list. Each patch has: `section` (`system_prompt` | `tool_description` | `few_shot_example`), `operation` (`insert` | `replace` | `append`), `before` (optional — for replace ops), `after` (the new text)
- `tool_validation_diffs` — list. Each diff has: `tool_name`, `operation` (`add_input_validator` | `add_output_validator` | `add_retry_policy` | `add_timeout`), `code_patch` (unified diff format)
- `regression_test_cases` — list. Each test case: `input` (the prompt) + `expected` (the expected output)
- `estimated_resilience_improvement` — float between 0.0 and 1.0
- `metadata` — open-ended dictionary (may include a `fallback_*` marker if the recipe was emitted via a fallback path — see §11)

### Each failure cluster

- `cluster_id` — `cluster_` + 8 hex characters
- `root_cause` — a single sentence
- `failure_count` — how many failures this cluster explains
- `span_ids` — list of Phoenix span IDs (clickable into Phoenix)
- `fault_classes` — which adversarial test categories were involved. Current category names: `malformed_tool_output`, `prompt_injection`, `context_poisoning`, `latency_spike`. **Note:** these category names are being renamed to the OWASP AGT01-AGT10 taxonomy (AGT01 = Prompt Injection, AGT05 = Excessive Agency, etc.) — the visual treatment should not hardcode either name set; treat the category names as content slots.

---

## 10. The hybrid hosting decision (something the wizard has to express)

The customer chooses, when they register, who hosts the Phoenix observability backend that stores their audit traces:

- **Phoenix Audit-hosted (default).** Zero-friction. The customer pastes their agent URL and clicks Run. Phoenix Audit briefly stores trace data on its own infrastructure, then cryptographically erases it 24 hours after the signed report is emitted. Phoenix Audit explicitly acts as a GDPR Article 28 data processor during that 24-hour window.
- **Customer-hosted (BYO).** For regulated industries (banks, hospitals, EU AI Act-bound enterprises). The customer provides their own Phoenix endpoint URL, their own API key, and their own project name. Audit trace data never leaves the customer's tenancy. Phoenix Audit holds no copy after the run completes.

The signed PDF's cover page picks one of two legally-locked paragraphs based on this choice. The customer does not see those paragraphs in the UI — they appear only in the PDF — but the choice they make in the settings drives which one renders.

Where this affects the design: Surface B (the wizard), Surface J (settings), and the cover paragraph of the PDF. The wizard needs a way to express the choice when the customer is in BYO mode. The default mode requires zero extra fields.

---

## 11. Compliance language and protocol the visual language should respect

A few load-bearing details where the engineering and legal sides of the product surface in the UI. The designer should know they exist so the visual language doesn't accidentally hide them.

### The header convention warning

Phoenix Audit sends three special HTTP headers on every probe to the target agent: a flag saying "this is an audit," the audit run ID, and a "dry-run mode" instruction. A well-behaved target agent reads these headers and short-circuits side-effecting tool calls (so it doesn't actually refund a real customer during an audit). It signals it did so by emitting a specific attribute on its response trace.

If the target agent does NOT signal that it honored the headers, the signed audit report includes a warning paragraph (legally locked verbatim) saying "side-effecting tool calls during this audit MAY have been executed for real." This warning is something Maya needs to see on Surface C in real time, ideally — so she knows during the audit whether her agent was a good citizen. Some kind of "honored / not honored" indicator per probe.

### The session-shape disclosure

Of the 6 adversarial tests in the demo battery, 3 are "single-turn" (one prompt, one response) and 3 are "two-turn" (a setup turn followed by an escalation turn). This mix is a deliberate budget-versus-coverage trade-off. The audit report PDF footnotes each test page with its session mode. The live audit view should expose the mode per test as well, so a compliance officer reading the report can see at a glance which tests had which depth.

### Fallback indicators

If an LLM call fails mid-audit (rate limit, safety block, etc.) and a fallback path produced a synthetic output, the signed artifact carries a `metadata.fallback_*` marker. The UI should surface fallback-emitted findings differently from real ones — both still appear in the report, but the regulator (and Maya) need to be able to tell them apart. Some kind of visual marker that says "this finding was produced via a fallback path."

### Regulatory article citations

When a failure is shown, it cites a specific article of the chosen regulatory framework. Examples: "EU AI Act Article 9 — risk management," "NIST AI RMF GOVERN 1.5," "HIPAA §164.312(a)(1)." These citations are first-class — they're not decorative metadata, they're the thing Maya files. The visual language should make citations prominent and credible-looking.

### Right-to-erasure

In default-hosting mode, the audit report's cover page lists an email address (`erasure@phoenix-audit.example`) where the customer can request deletion of their trace data at any point during the 24-hour retention window. The designer doesn't need to design the erasure flow itself (it's an email), but the email address has to appear on the PDF cover page in some visible form.

---

## 12. Where the build is today (so the designer knows what's real, what's coming, and what's stubbed)

The backend is mostly done. The frontend is greenfield — the designer's design is the frontend.

**Done and working (these are real features the designer can rely on):**

- POST `/run` — starts an audit, returns a run ID and SSE URL
- GET `/stream` — server-sent event stream of audit progress
- GET `/health` — health check that returns the hosting mode (default vs. BYO)
- GET `/agents/{id}` — registered target agent details
- The 3-phase orchestrator: Injector → Judge → Patcher
- The 4 adversarial categories: malformed-tool-output, prompt-injection, context-poisoning, latency-spike (being renamed to OWASP AGT01-AGT10 — the visual should treat the category names as content slots so the rename doesn't break the design)
- The 5 target-agent adapters (Tier 1 ADK, Tier 2 LangChain / CrewAI / OpenAI Agents SDK, Tier 3 HTTP black-box)
- The judge with LLM-as-judge rubrics
- Failure clustering via Gemini 3.5 Flash (up to 5 clusters per audit)
- The hardening recipe schema (locked — see §9)
- The Markdown recipe emitter (uploads to Google Cloud Storage, returns a signed URL)
- The GitLab merge request emitter (opens real MRs on real GitLab repos)

**Not yet built (the designer should expect to design these but know they'll be wired up after their work lands):**

- The signed PDF generator (Epic 6 work) — this is the final deliverable artifact. The designer's PDF preview view (Surface I) needs to plan for it.
- Per-probe SSE events with full citation / prompt / response (Epic 5 wires this — the test events will start streaming once the injector sub-agent is integrated)
- Continuous monitoring on a schedule (Surface H — backend uses Cloud Scheduler, not yet wired)
- The audit history view's backing storage (Surface E)
- The settings view's backing storage (Surface J)
- Authentication / accounts (light-touch for the hackathon — no payment)

**Code-name drift the designer might hear in conversation:**

- The product is called **Phoenix Audit**. That's the name. The package directories on disk are still called `chaoslab-agent`, `chaoslab-web`, `target-agent` — these are codenames the engineering team hasn't renamed yet. Anything user-facing says Phoenix Audit.
- The internal "fault classes" (F1, F2, F3, F4 in some older docs) are being renamed to the OWASP AGT01-AGT10 taxonomy. The visual should not commit to either name.

---

## 13. Out of scope (things the designer should NOT solve)

So you don't spend time on these:

- **Designing the PDF layout itself.** The PDF is server-generated by a separate templating pass. The PDF preview surface in the web UI (Surface I) IS in scope; the PDF's internal page layout is not.
- **Designing the Phoenix observability UI.** Phoenix is a third-party tool (Arize Phoenix). When the user clicks a span ID in the audit view, they open the Phoenix UI in a new tab. We don't design Phoenix.
- **Designing the GitLab UI.** Same — we open MRs in the user's own GitLab. We don't design GitLab.
- **Designing the customer's target agent.** The target is the customer's own product. We are auditing it, not designing it.
- **Static source-code analysis screens.** Phoenix Audit is a RUNTIME audit. We do not look at the customer's Python files. There is no "upload your code" surface.
- **Multi-tenant team / organization management** (post-hackathon roadmap). Single operator account is sufficient for the demo and the judging window.
- **Billing.** Free for the judging window.
- **Mobile-first.** Maya uses this on a 15-inch laptop. The product should be responsive and not break on mobile, but the design optimization is desktop-first.

---

## 14. What the designer's deliverables should let us do

When the designer hands work back, the developer (Claude) will use it to build the frontend. The deliverables most useful in that handoff:

- A landing-page design (Surface A)
- A run-audit wizard design (Surface B)
- A live-audit view design (Surface C) — this is the most important surface in the product
- A pre-recorded replay view design (Surface D — visually same as C with seeded data)
- An audit history view (Surface E)
- A target-agent setup detail view (Surface F)
- A hardening recipe view (Surface G)
- A continuous monitoring configuration view (Surface H)
- A PDF preview view (Surface I)
- A settings view (Surface J)
- Error / empty / loading states for each (Surface K guidance)
- The Open Graph image (1200×630) communicating the killer demo moment

Whatever design system, components, color decisions, typography, motion principles, and grid choices you make will become the locked design system for the build. The visual answer is yours.

---

## 15. Reference reading inside this repository (if helpful)

The designer doesn't need to read any of these to do good work, but they exist if it's useful to see how the engineering team thinks:

- `docs/PRD.md` — the product requirements document
- `docs/architecture.md` — engineering architecture and decisions
- `docs/run-config-schema.md` — the run-config payload the wizard produces
- `docs/header-convention.md` — the audit-header protocol
- `docs/session-shape.md` — the single-turn / two-turn probe mix
- `docs/data-retention-policy.md` — the GDPR Article 28 policy for default hosting
- `packages/shared-types/hardening-recipe.json` — the locked schema for the recipe artifact

---

If anything in this brief is under-specified, contradictory, or surprising, ask. The product is mid-build and a few framings are still moving (the OWASP AGT taxonomy rename, the PDF generator wiring) — names of fields and categories may shift. The shapes of the screens, the artifacts they produce, and the user they serve are stable.

Phoenix Audit ships in days. The visual answer is yours.
