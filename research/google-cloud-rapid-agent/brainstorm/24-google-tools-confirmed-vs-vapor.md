# Google Tool Ecosystem Audit — Confirmed vs Vapor

**Audit date:** 2026-06-04
**Build target:** AI Trust Auditor (ChaosLab) — Google Cloud Rapid Agent Hackathon, Arize track
**Deadline:** 2026-06-11
**Budget:** $100 Google Cloud credit
**Baseline (locked, not re-researched here):** Google ADK 2.1.0, Arize Phoenix Cloud, OpenInference instrumentors, Cloud Run, Gemini 3.5 Flash, Next.js 16 + Tailwind 4 + visx

**Method:** For each candidate, answer the same 6 questions. Plain English. Verdict per tool. No mush.

---

## How to read this doc

- **Use it** = wire in this week. ROI clear, integration cheap, on free tier.
- **Skip it** = don't wire in. Integration cost > benefit, OR doesn't fit our shape, OR overkill for v1.
- **Maybe later** = parking lot. Useful if we extend post-hackathon or find spare time.
- **Alpha — verify** = looks great on paper but needs a 10-minute hands-on before we commit.

---

## GROUP A — Agent runtime / building blocks

### A1. Vertex AI Agent Engine (now "Gemini Enterprise Agent Platform Runtime")

1. **What is it?** A managed runtime where you upload an ADK agent and Google hosts/scales it for you — no Dockerfile, no Cloud Run config.
2. **Exists today?** Yes. Rebranded at Google Cloud Next 2026 from "Vertex AI Agent Engine" to "Gemini Enterprise Agent Platform Runtime." GA for the core runtime; Sessions + Memory Bank GA Feb 2026; code-interpreter tool GA Jan 2026. ADK 2.x is fully supported.
3. **What does it do for us?** Could replace our `chaoslab-agent` Cloud Run service with a managed deploy. BUT — our spec is locked on Cloud Run, our trace stack is OpenInference→Phoenix Cloud (not Google Cloud Trace), and we already paid the architecture cost on Cloud Run. Switching now = burning days re-validating Phoenix instrumentation inside Agent Engine.
4. **Pricing?** Runtime: ~$0.0864/vCPU-hour + $0.0090/GB-hour. Sessions free tier: 50 vCPU-hours + 100 GB-hours/month. That's _enough_ for our judging-window load. But total cost during dev would be 2-3× a Cloud Run min-instances=1 setup.
5. **Verdict — SKIP for v1.** Locked architecture is Cloud Run; switching mid-build burns time and we lose nothing by staying. Re-evaluate post-hackathon if we want a managed runtime.
6. **URLs:** [Agent Engine overview](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/overview) · [Agent Platform pricing](https://cloud.google.com/vertex-ai/generative-ai/pricing) · [ADK Agent Engine deploy guide](https://google.github.io/adk-docs/deploy/agent-engine/)

### A2. Agent Garden

1. **What is it?** Google's curated library of pre-built agent samples (RAG agent, customer-support agent, research synthesis agent, etc.) you can clone and modify.
2. **Exists today?** Yes — live in the Agent Platform console at `console.cloud.google.com/agent-platform/agent-garden`. Samples cover RAG, customer support, industry-specific research.
3. **What does it do for us?** Nothing directly. None of the Garden samples are "agent that audits other agents" — closest is the research-synthesis sample which is the wrong shape. Could be useful as a _target agent_ (the thing we audit) if we want a realistic non-trivial demo target, but our `target-agent` service is already scoped as a deliberately-vulnerable stub.
4. **Pricing?** Free to clone. Running them costs whatever Gemini calls cost.
5. **Verdict — SKIP** for the auditor itself; **maybe later** as a richer demo target (clone Garden's RAG agent into `target-agent` for a more interesting on-stage demo). Filed under "polish if time."
6. **URLs:** [Agent Garden docs](https://docs.cloud.google.com/gemini-enterprise-agent-platform/build/agent-garden) · [Console](https://console.cloud.google.com/agent-platform/agent-garden) · [Google blog announce](https://developers.googleblog.com/agent-garden-samples-for-learning-discovering-and-building/)

### A3. Agent Starter Pack (`GoogleCloudPlatform/agent-starter-pack`)

1. **What is it?** A Google-published GitHub repo (`uvx agent-starter-pack create`) that scaffolds a complete agent project — backend, Terraform, CI/CD, observability, eval harness.
2. **Exists today?** Yes. Latest release v0.41.3 on April 25, 2026. Six templates including `adk`, `adk_a2a`, `adk_live` (multimodal RAG with audio/video), `agentic_rag`, `langgraph`, `adk_java`.
3. **What does it do for us?** Real but limited value at this stage — we've already built our scaffold (story S1.1-S1.5 are done or near-done). Where it COULD save us hours: cribbing the Terraform/CI patterns for `adk` template, especially the Cloud Build + Workload Identity Federation YAML. Lifting one or two GitHub Actions workflows is fair game.
4. **Pricing?** Free. Open source (Apache 2.0).
5. **Verdict — MAYBE LATER, narrow use.** Don't re-scaffold; do skim the `adk` template's `.github/workflows/` and `terraform/` directories for patterns we can lift. 30-minute task max.
6. **URLs:** [Repo](https://github.com/GoogleCloudPlatform/agent-starter-pack) · [Templates README](https://github.com/GoogleCloudPlatform/agent-starter-pack/tree/main/agents)

### A4. Agent Builder visual UI

1. **What is it?** The web-based, no-code/low-code agent builder inside Google Cloud Console. Drag-drop tool selection, prompt editing, deploy button.
2. **Exists today?** Yes, but rebranded as part of Gemini Enterprise Agent Platform UI. Still functional.
3. **What does it do for us?** Per the Devpost rules for the Arize track, the agent must be code-built (we already knew this) — the hackathon explicitly requires ADK code, not Builder no-code. Builder cannot be instrumented with OpenInference the way the spec requires, and the trace shape won't include the assertions we need. Confirmed ruled out.
4. **Pricing?** Same as Agent Platform Runtime.
5. **Verdict — SKIP, locked out by rules.** Just confirming the existing decision.
6. **URLs:** [Gemini Enterprise Agent Platform](https://cloud.google.com/products/gemini-enterprise-agent-platform)

### A5. Agentspace (now "Gemini Enterprise")

1. **What is it?** Google's enterprise "ChatGPT-for-your-company" — a search/chat agent with pre-built connectors to Workspace, Salesforce, Jira, etc.
2. **Exists today?** Yes. Rebranded into Gemini Enterprise at Next '26. Per-user SaaS product, not a developer SDK.
3. **What does it do for us?** Nothing. It's a packaged end-user product for enterprises, not a building block for our agent. Different shape entirely — there's no SDK we'd consume.
4. **Pricing?** $25/user/month for search; $45/user/month for expert agents. Wrong shape for us.
5. **Verdict — SKIP, wrong shape.** Not a developer tool; can't integrate.
6. **URLs:** [Gemini Enterprise pricing](https://cloud.google.com/products/gemini-enterprise-agent-platform/pricing)

### A6. A2A protocol + RemoteA2aAgent

1. **What is it?** Open protocol for agent-to-agent communication; `RemoteA2aAgent` is the ADK client class that talks to any A2A-compliant server over JSON-RPC.
2. **Exists today?** Yes — A2A v1.2 shipped March 2026, in production at 150+ orgs per Google. SDKs in Python, JS, Java, Go, .NET. Linux Foundation governed.
3. **What does it do for us?** Massive lift potential — if our auditor can spawn a `RemoteA2aAgent` against a customer's running A2A endpoint, we can interrogate their agent without needing source code. This makes the auditor SHAPE more compelling: "give us your A2A URL, get a trust report." For the demo, our `target-agent` should expose an A2A endpoint so the auditor can use a real cross-process call (rather than in-process imports).
4. **Pricing?** Free (open protocol).
5. **Verdict — USE IT.** Wire the `target-agent` as an A2A server, have the auditor connect via `RemoteA2aAgent`. Realistic cross-process trace shape, plus story fit ("we audit any A2A agent"). Implementation cost: ~half day.
6. **URLs:** [ADK A2A docs](https://google.github.io/adk-docs/a2a/intro/) · [A2A v1.2 announcement](https://cloud.google.com/blog/products/ai-machine-learning/agent2agent-protocol-is-getting-an-upgrade) · [Codelab](https://codelabs.developers.google.com/intro-a2a-purchasing-concierge)

---

## GROUP B — Evals + observability native to Google

### B1. Vertex AI Gen AI Evaluation Service

1. **What is it?** Google's managed eval framework for LLMs and agents. Computes "trajectory" metrics (exact match, in-order match, precision/recall) and "final response" metrics (correctness, tone, safety) against a labeled dataset.
2. **Exists today?** Yes — GA. Pricing changed April 2025. Native ADK support; LangChain/LangGraph/CrewAI also work.
3. **What does it do for us?** It's directly competitive with what we're doing with Phoenix evals — same shape (trajectory + response evaluation). For the Arize track specifically, Phoenix is the locked-in eval system, and the entire judging story is Phoenix-centric. Adding Vertex Eval as a second eval pipeline would muddle the narrative ("are you evaling with Phoenix or Vertex?") and cost time. There's a narrow case for using it as a _cross-validation_ layer ("Phoenix says fail, Vertex Eval also says fail — both judges agree") but that's polish.
4. **Pricing?** $0.00003/1k input chars + $0.00009/1k output chars for computation metrics. Cheap. A full battery would be ~$1 of credit.
5. **Verdict — SKIP for v1, MAYBE for the demo "second-judge" narrative.** Phoenix is the Arize-track story; adding Vertex Eval risks confusing it. Park as a stretch goal: if we want a "trust score validated by two independent eval systems" claim, wire this as a 30-min add-on the last day.
6. **URLs:** [Eval blog](https://cloud.google.com/blog/products/ai-machine-learning/introducing-agent-evaluation-in-vertex-ai-gen-ai-evaluation-service) · [Docs](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/evaluation-agents) · [Pricing](https://cloud.google.com/vertex-ai/generative-ai/pricing)

### B2. Vertex AI Pipelines

1. **What is it?** Kubeflow-based managed pipeline runner for ML/data workflows. Each "pipeline run" is a DAG of containers.
2. **Exists today?** Yes — GA. ~$0.03/pipeline run + compute costs.
3. **What does it do for us?** Wrong shape. Pipelines are for batch ML training/eval workflows. Our audit job is a real-time interactive request triggered by the web UI — Cloud Run handles it natively. Wrapping it in Pipelines adds 5+ min of overhead per audit (container cold starts) and no benefit.
4. **Pricing?** $0.03/run + Vertex compute. Cheap, but the integration cost is the problem.
5. **Verdict — SKIP.** Wrong shape entirely. Pipelines = batch ML; we're real-time interactive.
6. **URLs:** [Vertex AI pricing](https://cloud.google.com/vertex-ai/pricing)

### B3. Cloud Logging + Cloud Monitoring

1. **What is it?** Google's infra observability stack — stdout/stderr from Cloud Run gets logged automatically; Cloud Monitoring tracks CPU/memory/request metrics.
2. **Exists today?** Yes — both GA, default-on for Cloud Run.
3. **What does it do for us?** Phoenix is our _agent_ tracing system (spans, tool calls, LLM I/O). Cloud Logging is our _infrastructure_ observability — when Cloud Run OOMs, when GitHub Actions fails, when the request returns 500. They DON'T overlap — they're complementary. We get this free anyway because Cloud Run ships logs by default. The actionable add: a single Cloud Monitoring uptime check pointing at `/healthz` on each service, plus a budget alert at $80 of $100 spend.
4. **Pricing?** Free tier: 50 GiB log ingest/month + 150 MiB metrics + 1M API requests. We will not exceed this during the hackathon — probably 100× under. Free.
5. **Verdict — USE IT (it's already on; just add 2 alerts).** Zero integration cost; just wire one uptime check per service and a billing alert.
6. **URLs:** [Observability pricing](https://cloud.google.com/products/observability/pricing) · [Logging quotas](https://docs.cloud.google.com/logging/quotas)

### B4. Vertex AI Model Monitoring v2

1. **What is it?** Drift detection and prediction-quality monitoring for deployed ML models — feature distribution drift, output distribution drift, training-serving skew.
2. **Exists today?** Yes — in **Preview** as of June 2026. Centralizes monitoring config on model versions; supports models served outside Vertex.
3. **What does it do for us?** Wrong shape. Model Monitoring is for ML model drift (numeric/categorical features). Our agent is an LLM agent; we don't have a "training distribution" to drift from. Phoenix evals are the right tool for agent-quality monitoring.
4. **Pricing?** Per-monitoring-job cost; not relevant given shape mismatch.
5. **Verdict — SKIP.** Wrong shape — this is for tabular/vision ML model drift, not agent quality.
6. **URLs:** [Model Monitoring docs](https://docs.cloud.google.com/vertex-ai/docs/model-monitoring/set-up-model-monitoring)

---

## GROUP C — Storage, state, queue

### C1. Cloud Storage signed URLs (already in arch)

1. **What is it?** Cryptographically-signed time-limited URLs for downloading or uploading objects in a Cloud Storage bucket without needing IAM auth.
2. **Exists today?** Yes — GA for years, no risk.
3. **What does it do for us?** Per architecture, our signed audit PDFs are written to GCS and served via signed URL — the customer downloads from a short-lived link instead of us proxying the bytes. Cheap, secure, standard pattern.
4. **Pricing?** Free tier: 5 GiB standard storage + 5,000 Class A ops + 50,000 Class B ops/month. We're well under. Egress: $0.12/GiB after first 1 TB — PDFs are small (~500 KB) so even 1000 audits = 500 MB. Free in practice.
5. **Verdict — USE IT (already locked in arch).**
6. **URLs:** [Signed URLs docs](https://docs.cloud.google.com/storage/docs/access-control/signed-urls) · [Storage pricing](https://cloud.google.com/storage/pricing)

### C2. Firestore

1. **What is it?** Serverless NoSQL document database. Per-doc reads/writes, real-time listeners, transactional.
2. **Exists today?** Yes — GA. Free quota: 50k reads/day, 20k writes/day, 1 GiB storage.
3. **What does it do for us?** Stores per-audit metadata: audit ID, customer info, target agent endpoint, started/finished timestamps, PDF URL, pass/fail score, the trace IDs we reference into Phoenix. Cleaner than wedging this into Cloud Storage object metadata. Plus the audit-history page on `chaoslab-web` becomes a one-query Firestore read.
4. **Pricing?** Free tier covers our entire judging window comfortably (we'd need 50k audits to bust it).
5. **Verdict — USE IT.** Lightest-weight option for audit history; alternative is wedging history into a JSON file in GCS which is worse. Native Python SDK + Next.js SDK = fast wire-in.
6. **URLs:** [Firestore pricing](https://cloud.google.com/firestore/pricing)

### C3. Cloud Tasks

1. **What is it?** Managed queue for HTTP/RPC tasks. Push tasks to it, workers (Cloud Run services) get them delivered with retries, rate limits, scheduling.
2. **Exists today?** Yes — GA. Free: 1M operations/month. $0.40/M after.
3. **What does it do for us?** If the audit job is synchronous (web request → audit completes in 60s → return PDF URL), we don't need a queue. If it's async (request → "your audit is queued, check back" → background completes → email/notify), we do. Our current spec is synchronous-ish — agent runs inline, finishes, returns. So Cloud Tasks is overkill unless we want a polished "background processing" demo gloss.
4. **Pricing?** Free for hackathon load.
5. **Verdict — SKIP for v1, MAYBE LATER.** Don't add async complexity unless the demo actually needs it. If audits start taking >30 sec we may want this; track it.
6. **URLs:** [Cloud Tasks pricing](https://cloud.google.com/tasks/pricing)

### C4. Eventarc + Pub/Sub

1. **What is it?** Pub/Sub = managed message queue. Eventarc = the bridge that routes events (from GCS uploads, Audit Log entries, custom Pub/Sub topics) to Cloud Run.
2. **Exists today?** Yes — both GA. Pub/Sub free: 10 GiB/month message delivery. Pub/Sub Lite is being deprecated March 2026; use standard Pub/Sub.
3. **What does it do for us?** Could drive "when a customer uploads an OpenAPI spec to a GCS bucket, automatically trigger an audit." That's a nice-shape demo but it's a different UX than our web-UI-triggered audit. Adds wiring, doesn't add story.
4. **Pricing?** Free tier covers everything we'd do.
5. **Verdict — SKIP for v1.** Web-UI trigger is fine; event-driven is polish not pivotal. Park for post-hackathon.
6. **URLs:** [Pub/Sub pricing](https://cloud.google.com/pubsub/pricing)

### C5. Cloud SQL / AlloyDB

1. **What is it?** Cloud SQL = managed Postgres/MySQL. AlloyDB = Google's higher-performance Postgres-compatible variant.
2. **Exists today?** Yes — both GA.
3. **What does it do for us?** Nothing we need that Firestore doesn't cover. Our data model is tiny per-audit JSON docs, not relational. Adding a full Postgres instance costs us setup time AND a real monthly bill.
4. **Pricing?** Cloud SQL minimum (`db-f1-micro`) ~$10/month. AlloyDB minimum ~$250/month — way too expensive. Even Cloud SQL is wrong-shape.
5. **Verdict — SKIP, overkill.** Firestore is the right pick. AlloyDB would eat 2.5× our entire $100 credit per month — absolutely not.
6. **URLs:** [Cloud SQL pricing](https://cloud.google.com/sql/pricing) · [AlloyDB pricing](https://cloud.google.com/alloydb/pricing)

---

## GROUP D — Security, signing, identity

### D1. Cloud KMS (already in arch)

1. **What is it?** Google's managed key service. Stores asymmetric (RSA / EC) signing keys; you call `asymmetricSign` to produce a signature without ever holding the private key.
2. **Exists today?** Yes — GA for years. Stable.
3. **What does it do for us?** Our auditor produces PDF reports the customer can show their compliance officer. We sign the report's content hash with a KMS key so a third party can verify "this audit was produced by ChaosLab and hasn't been tampered with." Without signing, the PDFs are just PDFs — anyone could edit them. The signature is the trust artifact.
4. **Pricing?** ~$0.06 per 10,000 signing operations + ~$0.06/month per active asymmetric key version. Effectively $0.06 for the whole hackathon.
5. **Verdict — USE IT (already locked in arch).** This is what makes the audit "trust" instead of "vibes."
6. **URLs:** [Cloud KMS pricing](https://cloud.google.com/kms/pricing)

### D2. Workload Identity Federation (already in arch)

1. **What is it?** GitHub Actions → GCP authentication without long-lived service account keys. GitHub's OIDC token gets exchanged for short-lived GCP credentials.
2. **Exists today?** Yes — GA. `google-github-actions/auth@v2` is the standard action.
3. **What does it do for us?** Per architecture, the CI/CD pipeline uses WIF instead of a JSON service-account key in GitHub Secrets. Why it matters: judges have spotted unsigned/keyed CI before — WIF is the modern-correct pattern and one of the small details that signals "this team builds production-grade infra."
4. **Pricing?** Free.
5. **Verdict — USE IT (already locked in arch).**
6. **URLs:** [`google-github-actions/auth`](https://github.com/google-github-actions/auth) · [Official WIF deployment guide](https://docs.cloud.google.com/iam/docs/workload-identity-federation-with-deployment-pipelines)

### D3. Secret Manager (already in arch)

1. **What is it?** Managed secret store. Each secret has versions; access controlled by IAM.
2. **Exists today?** Yes — GA. Always-free tier: 6 active secret versions + 10k access ops/month.
3. **What does it do for us?** Holds the Phoenix API key, Gemini API key, GitLab token, KMS key references. Cloud Run mounts them at runtime as env vars (no hard-coded secrets in the container image).
4. **Pricing?** Free tier covers us trivially.
5. **Verdict — USE IT (already locked in arch).**
6. **URLs:** [Secret Manager pricing](https://cloud.google.com/secret-manager/pricing)

### D4. Binary Authorization / Artifact Registry vulnerability scanning

1. **What is it?** Binary Auth = "only signed/attested container images may deploy to prod." Artifact Registry scanning = automatic CVE check on every container image push.
2. **Exists today?** Yes — GA. Scanning: $0.26/image scan.
3. **What does it do for us?** Binary Authorization is heavyweight (you need to set up attestor keys, attestation policies, etc.) and overkill for a 3-service hackathon. Artifact Registry vulnerability scanning is one-click: enabling it costs ~$0.78 for a 3-service hackathon (3 images × $0.26) and gives us a "CVE scan clean" badge we can mention in the demo without doing real work.
4. **Pricing?** Vulnerability scanning ~$0.26 per image. Trivial. Binary Auth is free per se but operationally expensive.
5. **Verdict — USE Artifact Registry vulnerability scanning (one-flag enable); SKIP Binary Authorization (overkill).** The scanning is essentially free demo polish; Binary Auth setup eats a half-day for no judging credit.
6. **URLs:** [Artifact Analysis pricing](https://cloud.google.com/artifact-analysis/pricing) · [Container scanning](https://docs.cloud.google.com/artifact-analysis/docs/container-scanning-overview)

---

## GROUP E — UI/UX accelerators (frontend)

### E1. Cloud Workstations

1. **What is it?** Google's managed cloud dev environment — basically a browser-based VS Code on a VM with persistent disk.
2. **Exists today?** Yes — GA.
3. **What does it do for us?** Nothing useful at the hackathon stage. Abu codes locally with Claude Code on his own machine. Cloud Workstations are designed for enterprise security teams that need to lock down dev environments to corp-managed VMs.
4. **Pricing?** ~$0.20/cluster/hour control plane + $0.05/vCPU/hour. Eats ~$70/month per dev minimum — would consume the budget for zero gain.
5. **Verdict — SKIP.** Wrong shape (enterprise security tooling, not hackathon dev tooling).
6. **URLs:** [Cloud Workstations pricing](https://cloud.google.com/workstations/pricing)

### E2. Gemini Code Assist

1. **What is it?** Google's coding-assistant IDE plugin (VS Code, JetBrains) — code completion, chat, multi-file refactor.
2. **Exists today?** Yes — GA. Made free for individuals March 2026: 180k completions/month, 240 daily chat sessions, free PR review.
3. **What does it do for us?** Per the hackathon rules already noted in our spec, Code Assist is ALLOWED as a dev-time accelerator but the _runtime_ agent must use ADK directly (not Code Assist's output as the agent). So it's just an IDE plugin we could use alongside Claude Code. But we're already using Claude Code for dev — adding Code Assist is redundant.
4. **Pricing?** Free for individuals.
5. **Verdict — SKIP, redundant with Claude Code.** No conflict with hackathon rules but no marginal benefit.
6. **URLs:** [Free Code Assist blog](https://blog.google/innovation-and-ai/technology/developers-tools/gemini-code-assist-free/)

### E3. Genkit

1. **What is it?** Google's alternative agent SDK — TypeScript/Go/Python toolkit for plugging GenAI into apps. Different shape from ADK.
2. **Exists today?** Yes — Node SDK is GA (Feb 2025), Go is Beta, Python is Alpha.
3. **What does it do for us?** Nothing. Our orchestrator is locked on ADK SequentialAgent per spec — the whole instrumentation chain (`openinference-instrumentation-google-adk`) depends on that. Genkit is for app developers adding GenAI features, not for building agents — wrong shape and would require throwing out the spec.
4. **Pricing?** Free.
5. **Verdict — SKIP, wrong shape and locked out by spec.**
6. **URLs:** [Genkit vs ADK comparison](https://medium.com/@nozomi-koborinai/genkit-vs-agent-development-kit-adk-choosing-the-right-google-backed-ai-framework-1744b73234ac)

### E4. Mesop

1. **What is it?** Python web UI framework by Google engineers (not officially Google-supported product). Build web apps in pure Python, no JS needed.
2. **Exists today?** Yes — v1.3.0 May 13, 2026. Actively maintained. 6.6k stars. Apache 2.0.
3. **What does it do for us?** Tempting on the surface — could replace Next.js+Tailwind+visx with a pure-Python UI. BUT: (a) our spec is locked on Next.js 16 + visx + Tailwind 4; (b) Mesop is "not an officially supported Google product" — Devpost judges may see that as a yellow flag rather than a green one; (c) Mesop's chart libs are weaker than visx; (d) tearing out our frontend stack now costs 2 days. Compelling only if we were building from scratch.
4. **Pricing?** Free (open source).
5. **Verdict — SKIP, locked out by existing frontend stack.** Park as a thought experiment for an internal admin/debug page if we needed one in 30 minutes.
6. **URLs:** [Mesop GitHub](https://github.com/google/mesop)

---

## GROUP F — Document parsing

### F1. Document AI

1. **What is it?** Google's managed OCR + structured-document parser. Specialized "processors" for invoices, forms, ID docs, etc.
2. **Exists today?** Yes — GA. $1.50 to $30 per 1,000 pages depending on processor.
3. **What does it do for us?** Wrong shape entirely. Our auditor reads OpenAPI YAML/JSON and Python source files — these are already structured text, no OCR or "extract fields from a scanned PDF" needed. A regex + a YAML parser + Gemini does everything Doc AI would do, for free.
4. **Pricing?** Wouldn't bust $100 credit but pure waste.
5. **Verdict — SKIP.** Wrong shape (Doc AI is for unstructured scanned documents, not source code).
6. **URLs:** [Document AI pricing](https://cloud.google.com/document-ai/pricing)

### F2. Cloud Functions (now "Cloud Run functions")

1. **What is it?** Event-triggered serverless functions. As of Gen 2 they're built on Cloud Run under the hood — basically "Cloud Run with the Dockerfile written for you."
2. **Exists today?** Yes — GA.
3. **What does it do for us?** Same compute substrate as Cloud Run. The only narrow use case would be: a tiny Pub/Sub-triggered function (e.g., "when an audit finishes, send a Slack/email notification"). That's a 10-line function. But our spec already uses Cloud Run services, so there's no point introducing a second compute primitive for one tiny job.
4. **Pricing?** Same as Cloud Run; free tier 2M invocations/month + 400k GB-seconds.
5. **Verdict — SKIP for v1, MAYBE LATER for a notify-on-completion glue.** Don't add a second compute primitive; use a Cloud Run endpoint if we need a webhook.
6. **URLs:** [Cloud Run functions comparison](https://docs.cloud.google.com/run/docs/functions/comparison)

---

## GROUP G — Networking / API management

### G1. Cloud Endpoints + Apigee

1. **What is it?** API gateways. Cloud Endpoints is the lightweight version (Extensible Service Proxy in front of your service). Apigee is the full enterprise API management platform.
2. **Exists today?** Yes — both GA.
3. **What does it do for us?** Nothing. We have 3 services; Cloud Run already gives us per-service URLs and IAM. We don't have an API product to govern — we have one demo. Apigee starts at $500/month for the Standard tier, pay-as-you-go is $20/M calls. Massive overkill.
4. **Pricing?** Apigee Standard $500/month minimum. Endpoints is cheap but adds proxy complexity for no value.
5. **Verdict — SKIP, obvious overkill.**
6. **URLs:** [Apigee pricing](https://cloud.google.com/apigee/pricing)

### G2. Cloud Run jobs (not services)

1. **What is it?** Cloud Run jobs run a container to completion (then exit) — for batch tasks. Cloud Run services serve HTTP requests continuously. Same platform, different runtime mode.
2. **Exists today?** Yes — GA.
3. **What does it do for us?** Potentially useful if we want a CLI-style audit entry point. Imagine: customer runs `chaoslab audit https://target.example.com` from their terminal — that could be a Cloud Run job invocation. But our spec is web-UI-triggered, so the audit logic lives in a service handler. No need to duplicate the orchestrator into a job. ALSO useful for nightly batch eval runs against a "golden corpus" of agents — that's polish, not v1.
4. **Pricing?** Same as services; pay per container second.
5. **Verdict — SKIP for v1, MAYBE LATER for a `chaoslab audit` CLI demo.**
6. **URLs:** [Cloud Run jobs vs services](https://docs.cloud.google.com/run/docs/overview/what-is-cloud-run)

---

## GROUP H — Data / analytics

### H1. BigQuery

1. **What is it?** Google's serverless data warehouse. Query petabytes of data with SQL.
2. **Exists today?** Yes — GA. Free: 1 TiB queries/month + 10 GiB active storage.
3. **What does it do for us?** Audit-history analytics: "across all our audits, what % of agents fail on prompt injection?" That's a real story for a sales pitch. BUT: our entire dataset for the hackathon is at most a few dozen audits — Firestore can answer those queries directly. BigQuery overkill until we have 10k+ audits.
4. **Pricing?** Free tier covers everything.
5. **Verdict — SKIP for v1, MAYBE LATER.** Firestore queries are sufficient at hackathon scale; BigQuery is the right answer at SaaS scale.
6. **URLs:** [BigQuery pricing](https://cloud.google.com/bigquery/pricing)

### H2. Looker Studio

1. **What is it?** Google's free BI/dashboarding tool — drag-drop dashboard builder, embeddable via iframe.
2. **Exists today?** Yes — GA, free.
3. **What does it do for us?** Could give us a "customer admin dashboard" without writing React. BUT: (a) our spec already has the dashboard inside `chaoslab-web` (Next.js + visx); (b) embedding a Looker Studio iframe into our own app would look amateurish next to the visx dashboard we're already building; (c) Looker Studio dashboards look corporate/generic, not premium.
4. **Pricing?** Free.
5. **Verdict — SKIP, would _downgrade_ the design quality.**
6. **URLs:** [Looker Studio](https://valiotti.com/technologies/looker-studio/)

---

## GROUP I — Things I might have missed

### I1. `google/agents-cli` (Agents CLI) — **the surprise find**

1. **What is it?** A Google-published CLI that packages "skills" for any coding agent (Claude Code, Cursor, Gemini CLI) covering ADK code patterns, eval methodology, deployment workflows, Cloud Trace observability, and Gemini Enterprise registration.
2. **Exists today?** Yes — v0.3.0 released June 1, 2026. Marked Pre-GA. Open source. Repo at `github.com/google/agents-cli`.
3. **What does it do for us?** This is exactly the kind of thing Claude Code-in-this-repo could lean on. The "ADK code patterns" skill knows the SDK's gotchas (the same kind of stuff `docs/audit-notes.md` records by hand for us). The "deployment" skill knows the Cloud Run + WIF dance we're already doing. Worth a 20-minute install + skim. If even one skill saves us 1 hour, it's a win.
4. **Pricing?** Free (Apache 2.0).
5. **Verdict — VERIFY THIS WEEK (alpha-risk).** Pre-GA = the API surface could shift. 20-minute confirmation: install, run, check if the `adk` and `observability` skills actually help us. If yes, integrate into the dev loop.
6. **URLs:** [agents-cli repo](https://github.com/google/agents-cli) · [I/O '26 announcement](https://cloud.google.com/blog/topics/developers-practitioners/io26-news-for-agent-developers-on-google-cloud)

### I2. Agent Observability dashboard (built into Gemini Enterprise Agent Platform)

1. **What is it?** Google's own built-in agent observability dashboard inside Agent Platform — token consumption, error rates, latency, trace viewer.
2. **Exists today?** Yes — GA-ish (announced at Next '26, generally accessible). OpenTelemetry-compliant per Google's marketing.
3. **What does it do for us?** Direct competitor to Phoenix Cloud. But we're locked into Phoenix for the Arize track — that's the whole point of the track. Adding Google's Agent Observability would split our trace stream and confuse the judging story.
4. **Pricing?** Built into Agent Engine; included.
5. **Verdict — SKIP, the Arize track requires Phoenix.** Cannot use both as primary; Phoenix wins by track rule.
6. **URLs:** [Agent observability docs](https://docs.cloud.google.com/stackdriver/docs/observability/agent-observability)

### I3. Cloud Build (CI/CD)

1. **What is it?** Google's managed CI/CD runner — runs container builds on push, deploys to Cloud Run, integrates with Artifact Registry.
2. **Exists today?** Yes — GA. Free: 120 build-minutes/day.
3. **What does it do for us?** Alternative to GitHub Actions for CI. Our spec uses GitHub Actions + Workload Identity Federation. Switching to Cloud Build = re-writing all CI for no marginal benefit. Cloud Build's main edge is "no GitHub Actions cost," but GitHub Actions on a public repo is also free.
4. **Pricing?** Free up to 120 min/day.
5. **Verdict — SKIP, GitHub Actions already locked in.**
6. **URLs:** [Cloud Build](https://cloud.google.com/build)

### I4. Google Cloud Starter Tier (NEW, May 2026)

1. **What is it?** Brand-new Google Cloud tier announced at I/O '26 — first two apps deploy free without billing setup.
2. **Exists today?** Yes — live as of May 2026.
3. **What does it do for us?** If we wanted a zero-billing-friction demo URL we could share, Starter Tier handles it. But we already have $100 credit + a proper GCP project. The Starter Tier is for "I'm a hobbyist, never used GCP" — not us.
4. **Pricing?** Free.
5. **Verdict — SKIP, we're past the friction this targets.**
6. **URLs:** [Starter Tier docs](https://docs.cloud.google.com/docs/starter-tier)

### I5. Cloud Trace (alpha-risk if we leaned in)

1. **What is it?** Google's distributed tracing service (the Stackdriver Trace successor). OpenTelemetry-compatible.
2. **Exists today?** Yes — GA. Free: 2.5M spans ingested/month.
3. **What does it do for us?** Could give us infrastructure-level tracing (HTTP request flow through `chaoslab-web` → `chaoslab-agent` → `target-agent`) separately from Phoenix's agent-level tracing. Two layers of observability. The risk: setup time, and split-brain ("did we look at Cloud Trace or Phoenix for that 500 error?"). Could be 30-min add or 4-hour rabbit hole. **Verify before relying.**
4. **Pricing?** Free.
5. **Verdict — MAYBE LATER, verify time-cost first.** If we have a quiet evening, see if a single `OTEL_EXPORTER_OTLP_ENDPOINT` env var splits traces to both Phoenix and Cloud Trace cleanly. If yes, free win. If not, skip.
6. **URLs:** [Cloud Trace](https://cloud.google.com/trace/docs)

---

## SYNTHESIS — Decisions in plain English

### The 5 Google tools we should DEFINITELY add to the build

1. **A2A protocol + `RemoteA2aAgent`** — wire the `target-agent` as an A2A server and have the auditor connect via `RemoteA2aAgent` to make the trace shape realistic (cross-process) instead of fake (in-process). Half-day implementation; strong story fit.
2. **Firestore** — store per-audit metadata (customer, target, score, PDF URL, trace IDs). Free tier covers us 1000× over; native SDKs in both Python and Next.js; alternative is wedging history into GCS object metadata which is worse.
3. **Cloud Logging + Cloud Monitoring** — already on by default for Cloud Run; we just need to add one uptime check per service plus a $80 billing alert. Zero integration cost, catches Cloud Run OOMs we'd otherwise miss.
4. **Artifact Registry vulnerability scanning** — one-flag enable, ~$0.78 total for 3 service images, gives us a "CVE-clean container scan" line for the demo. Real and effectively free.
5. **Cloud Storage signed URLs + Cloud KMS + Secret Manager + Workload Identity Federation** — bundled together because they're the same "spec already locked them in, confirm they're correct" check. All four are confirmed live, free or near-free, and load-bearing. KMS specifically is what makes our PDF "signed audit" instead of "just a PDF."

(That's 5 logical adds; #5 counts the four already-locked security pieces collectively. The new things to actually wire this week are A2A, Firestore, the two Cloud Monitoring alerts, and the vulnerability scan flag.)

### The 3 we're going to SKIP and why

1. **Vertex AI Agent Engine (Gemini Enterprise Agent Platform Runtime)** — we're locked on Cloud Run for the agent service. Switching mid-build burns days re-validating Phoenix instrumentation inside Agent Engine, with no judging benefit (the Arize track scores the agent code, not the runtime).
2. **Vertex AI Gen AI Evaluation Service** — direct competitor to Phoenix evals. Adding it would muddle the Arize-track narrative ("are you evaling with Phoenix or Vertex?"). Phoenix is the locked story.
3. **Mesop / Genkit / Cloud Workstations / Apigee / AlloyDB** — all wrong-shape or wrong-cost. Mesop and Genkit can't replace our locked Next.js + ADK stack without a rewrite; Cloud Workstations is enterprise security tooling; Apigee starts at $500/month; AlloyDB minimum eats 2.5× our entire credit budget.

### The 2 "alpha — verify hands-on before relying"

1. **`google/agents-cli` v0.3.0 (Pre-GA, June 1 2026)** — Google-published CLI of agent-building skills for any coding agent (Claude Code, etc.). The `adk` and `observability` skills could shortcut hours of doc-diving. 20-min install + verify it actually fires useful guidance on our codebase. If yes, integrate into the loop. If the API is too fresh to trust, skip.
2. **Cloud Trace as a second tracing layer** — could give us infrastructure-level tracing (HTTP flow across our 3 Cloud Run services) running side-by-side with Phoenix's agent-level traces. The risk is split-brain debugging. 30-min experiment: see if one `OTEL_EXPORTER_OTLP_ENDPOINT` config routes traces to both Phoenix and Cloud Trace cleanly. If yes, free win. If not, kill.

### The 1 surprise tool I didn't expect to find but is genuinely good

**`google/agents-cli`** — listed above as alpha-verify, but the surprise is that Google shipped (June 1, 2026, 3 days ago) a CLI that's essentially "context skills for any coding agent working on Google Cloud agents." The seven skill modules (workflow, ADK code patterns, scaffolding, eval, deploy, Gemini Enterprise registration, observability) overlap perfectly with what we're doing manually. If the `adk` skill knows the same gotchas we documented in `docs/audit-notes.md`, that's leverage we didn't have a week ago. Worth the 20-min install today.

### Vapor / things we'd otherwise have wasted time on

- **Agent Builder visual UI / Agentspace / Gemini Enterprise** — all the rebranded packaged products. None expose a developer-grade integration; they're end-user SaaS shapes. Don't burn time exploring.
- **Model Monitoring v2** — Preview status AND wrong shape (tabular ML drift, not agent quality). Looks promising in marketing material but irrelevant.
- **Vertex AI Pipelines** — Kubeflow batch pipelines. Wrong shape for real-time audits.
- **Document AI for OpenAPI / source-code parsing** — wrong shape; Doc AI is for scanned PDFs and forms, not structured text we already have.
- **Apigee Pay-as-you-go** — sounds free-ish but operationally heavyweight; nothing to govern at our scale.

### Quick-reference verdict table

| Tool                           | Verdict                              | Cost in $100 budget | Wire-in cost      |
| ------------------------------ | ------------------------------------ | ------------------- | ----------------- |
| Vertex AI Agent Engine         | SKIP                                 | n/a                 | (would burn days) |
| Agent Garden samples           | SKIP / maybe later as demo target    | $0                  | n/a               |
| Agent Starter Pack             | MAYBE LATER (crib CI patterns)       | $0                  | 30 min            |
| Agent Builder UI               | SKIP (rules-locked)                  | n/a                 | n/a               |
| Agentspace / Gemini Enterprise | SKIP (wrong shape)                   | n/a                 | n/a               |
| A2A + RemoteA2aAgent           | **USE**                              | $0                  | half day          |
| Vertex Gen AI Eval             | SKIP / maybe later as "second judge" | <$1                 | half day          |
| Vertex Pipelines               | SKIP                                 | n/a                 | n/a               |
| Cloud Logging/Monitoring       | **USE (already on)**                 | $0 (free tier)      | 20 min            |
| Model Monitoring v2            | SKIP                                 | n/a                 | n/a               |
| Cloud Storage signed URLs      | **USE (locked)**                     | <$1                 | (done)            |
| Firestore                      | **USE**                              | $0 (free tier)      | half day          |
| Cloud Tasks                    | SKIP / maybe later if async          | $0                  | n/a               |
| Eventarc + Pub/Sub             | SKIP / maybe later                   | $0                  | n/a               |
| Cloud SQL / AlloyDB            | SKIP                                 | $250+/mo (NO)       | n/a               |
| Cloud KMS                      | **USE (locked)**                     | <$1                 | (done)            |
| Workload Identity Federation   | **USE (locked)**                     | $0                  | (done)            |
| Secret Manager                 | **USE (locked)**                     | $0 (free tier)      | (done)            |
| Artifact Registry scanning     | **USE**                              | ~$0.78              | 5 min             |
| Binary Authorization           | SKIP (overkill)                      | n/a                 | n/a               |
| Cloud Workstations             | SKIP                                 | $70+/mo             | n/a               |
| Gemini Code Assist             | SKIP (redundant w/ Claude Code)      | $0                  | n/a               |
| Genkit                         | SKIP (wrong shape)                   | n/a                 | n/a               |
| Mesop                          | SKIP (stack locked)                  | n/a                 | n/a               |
| Document AI                    | SKIP (wrong shape)                   | n/a                 | n/a               |
| Cloud Functions                | SKIP / maybe later                   | $0                  | n/a               |
| Apigee / Endpoints             | SKIP (overkill)                      | $500+/mo            | n/a               |
| Cloud Run jobs                 | SKIP / maybe later for CLI           | $0                  | n/a               |
| BigQuery                       | SKIP / maybe later                   | $0                  | n/a               |
| Looker Studio                  | SKIP (downgrades UI)                 | $0                  | n/a               |
| **`google/agents-cli`**        | **ALPHA — VERIFY**                   | $0                  | 20 min            |
| Cloud Trace                    | **ALPHA — VERIFY**                   | $0                  | 30 min            |
| Cloud Build                    | SKIP (GHA locked)                    | $0                  | n/a               |
| Starter Tier                   | SKIP (past friction)                 | $0                  | n/a               |

---

## End — actionable list for this week

In priority order:

1. **Right now:** add Cloud Monitoring uptime checks + billing alert at $80. (20 min, zero risk, catches blowups.)
2. **Right now:** enable Artifact Registry vulnerability scanning on the 3 service images. (5 min, ~$0.78, demo polish.)
3. **This week:** wire the `target-agent` as A2A server + auditor uses `RemoteA2aAgent`. Realistic cross-process traces. (Half day.)
4. **This week:** add Firestore for audit history. Replaces ad-hoc JSON-in-GCS pattern. (Half day.)
5. **Tonight (20 min spike):** install `google/agents-cli` v0.3.0, verify the `adk` and `observability` skills actually help on our codebase. If yes, leave installed. If alpha-fragile, uninstall and move on.
6. **One spare evening (30-min spike):** see if dual-export OTEL → Phoenix + Cloud Trace works with one env var. If yes, free infrastructure-tracing layer. If no, drop it.
7. **Park for after hackathon:** Cloud Tasks for async, Cloud Functions for notification glue, Cloud Run jobs for a `chaoslab audit` CLI, BigQuery for analytics, Vertex Gen AI Eval as a second-judge gloss, Agent Garden RAG sample as a richer target-agent demo.

The point of the audit is to confirm the locked architecture is _correct_ and to find the small free wins (1, 2) and the genuine accelerators (3, 4, 5). No surprise that most of the candidates skip — Google's surface is enormous and most tools target enterprises, not hackathons.
