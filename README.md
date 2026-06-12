<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/Blockchain-Oracle/phoenix-audit/main/apps/phoenix-audit-web/public/brand/banner-dark.svg">
    <img alt="Phoenix Audit" src="https://raw.githubusercontent.com/Blockchain-Oracle/phoenix-audit/main/apps/phoenix-audit-web/public/brand/banner-light.svg" width="100%">
  </picture>
</p>

# Phoenix Audit

**The AI agent that audits your other AI agents — regulator-ready signed report in 90 seconds.**

Point Phoenix Audit at any production AI agent, it runs an adversarial test battery, watches the agent's internal execution via Arize Phoenix, collapses independent failures into one root cause, and emits a cryptographically signed audit report — keyed to a commit SHA, ready to hand to a compliance officer.

What a Big-4 audit pack costs **€80K–€250K** and takes **12–18 months** for, Phoenix Audit ships in **98 seconds**. Same Phoenix telemetry. Same evidence chain. Different artifact.

→ **[Live demo](https://phxaudit.xyz/replay)** · **[Run an audit](https://phxaudit.xyz/new)** · **[Sample signed report](https://raw.githubusercontent.com/Blockchain-Oracle/phoenix-audit/main/docs/examples/sample-signed-report.pdf)**

## How we hit the Arize Rapid Agent rubric

| Tracing                                                                                                                                            | MCP                                                                                                                                                                 | Self-improvement loop                                                                                                                                                   | Impact                                                                                                                                                                                                               |
| -------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Every probe span emitted to Phoenix Cloud via OpenInference + ADK instrumentor; evidence joined across services via W3C `traceparent` propagation. | `phoenix-mcp` for dataset + experiment operations; custom ADK `FunctionTool`s wrap the SDK calls that aren't MCP-native (`run_experiment`, `log_span_annotations`). | Failures cluster by root cause → Patcher drafts a hardening recipe → optional GitLab MR with regression tests → next audit re-runs the same dataset to confirm the fix. | EU AI Act Article 15 + 26 evidence: signed, hash-chained PDF + JSON pack per audit, Cloud-KMS-signed, verifiable offline. Targeted at the 2,000+ Director of AI Governance roles enforcing the August 2026 deadline. |

---

## Architecture

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/Blockchain-Oracle/phoenix-audit/main/docs/images/architecture-dark.svg">
    <img alt="Phoenix Audit end-to-end architecture — Injector → Judge → Patcher → Cloud KMS signed report" src="https://raw.githubusercontent.com/Blockchain-Oracle/phoenix-audit/main/docs/images/architecture-light.svg" width="100%">
  </picture>
</p>

Three Cloud Run services in concert:

- **[`apps/phoenix-audit-web/`](./apps/phoenix-audit-web/)** — Next.js 16 operator surface. Authenticate, point at a target, watch the live audit chamber, download the signed report. Talks to the agent service over `/api/agent/*` proxied with a server-minted GCP ID token.
- **[`apps/phoenix-audit-agent/`](./apps/phoenix-audit-agent/)** — Google ADK orchestrator. Runs `Injector → Judge → Patcher` sub-agents in a SequentialAgent. The Injector fires the adversarial battery via A2A, the Judge fetches Phoenix spans and clusters failures by root cause (with `gemini-3.5-flash`), the Patcher drafts the hardening recipe.
- **[`apps/target-agent/`](./apps/target-agent/)** — sacrificial demo bot, a deliberately naive customer-support agent. The same audit pipeline can also point at any ADK / LangChain / CrewAI / OpenAI-Agents-SDK / generic-HTTP target (see ADR-002 in [`docs/architecture.md`](./docs/architecture.md)).

The orchestrator joins the trace context onto every probe so the Judge can read the target's own internal execution from Phoenix. The final report is signed against the operator's Cloud KMS key, stored in GCS with a 7-day signed URL, and (optionally) filed as a hardening-recipe merge request against the target's repository.

**Full detail in [`docs/architecture.md`](./docs/architecture.md)** — 12 ADRs covering target adapter tiers, Phoenix Cloud + ADK wiring, the hybrid hosting model, the cryptographic signing chain, and the GitLab MR shape.

---

## Built on

- **Google Cloud** — Cloud Run (3 services), Cloud KMS (Ed25519 signing), Cloud Firestore (run + dataset index), Cloud Storage (signed reports), Secret Manager (Phoenix + Resend + GitLab OAuth), Artifact Registry (build-once-promote-everywhere), Workload Identity Federation (CI auth), Cloud Build.
- **Arize Phoenix** — span telemetry + OpenInference instrumentation; Phoenix Cloud is where the evidence chain lives (self-hosted Phoenix supported via ADR-017).
- **Vertex AI + Gemini** — `gemini-3.5-flash` as the judge LLM (locked to Flash for cost discipline per ADR-007); Vertex AI is the inference plane for the target's own model calls.
- **Google ADK + A2A** — agent orchestration and the cross-agent wire protocol.
- **Web stack** — Next.js 16, Tailwind 4, Firebase Authentication, shadcn/ui, visx, Framer Motion.
- **Backend stack** — Python 3.12, `uv`, `pytest`, `ty`.
- **Integrations** — GitLab (OAuth + MR filing per ADR-011), Resend (transactional email), WeasyPrint (PDF signing pipeline).

---

## Folder structure

```
phoenix-audit/
├── apps/
│   ├── phoenix-audit-web/         Next.js operator surface (auth + chamber + reports)
│   ├── phoenix-audit-agent/       ADK orchestrator (Injector → Judge → Patcher)
│   └── target-agent/              Sacrificial customer-support demo bot
├── docs/
│   ├── PRD.md                     Product vision · day-1 user · competitive moat
│   ├── architecture.md            System overview + 12 ADRs
│   ├── demo-strategy.md           "Three failures · one root cause" demo flow
│   ├── data-retention-policy.md   GDPR Art. 28 · 24h erasure · KMS attestation
│   ├── cicd.md                    Cloud Run deploy · WIF · Secret Manager
│   ├── env-vars.md                Master env-var reference (all 4 apps)
│   ├── run-config-schema.md       JSON Schema for audit run config
│   ├── assets.md                  Designer briefs (banner · architecture · ecosystem)
│   ├── images/                    Architecture SVG (light + dark)
│   └── examples/                  Sample signed report PDF
├── infra/                         GCP bootstrap (Workload Identity Federation + Secret Manager + KMS)
│   ├── workload-identity-federation.sh
│   ├── secret-manager-setup.sh
│   └── phoenix-self-host/         Optional self-hosted Phoenix on Docker / Cloud Run
├── scripts/                       400-line guard · schema export · dataset seed · signature verify
└── .github/workflows/             CI: pr-checks · staging-deploy · prod-promote
```

---

## Quickstart

```bash
git clone https://github.com/Blockchain-Oracle/phoenix-audit && cd phoenix-audit
uv sync && pnpm install
cp apps/phoenix-audit-web/.env.example apps/phoenix-audit-web/.env.local
cp apps/phoenix-audit-agent/.env.example apps/phoenix-audit-agent/.env
cp apps/target-agent/.env.example apps/target-agent/.env
```

Then populate the six env vars marked **must-have** in [`docs/env-vars.md`](./docs/env-vars.md) and start each app in its own terminal:

```bash
pnpm --filter phoenix-audit-web dev                                            # http://localhost:3000
uv run --package phoenix-audit-agent uvicorn phoenix_audit_agent.main:app      # :8080
uv run --package target-agent target-agent                                     # :8001
```

Open `http://localhost:3000` and follow the onboarding wizard.

For Cloud Run deployment, see [`docs/cicd.md`](./docs/cicd.md). For the local-auth limitation that affects `pnpm dev` testing, see [`apps/phoenix-audit-web/README.md`](./apps/phoenix-audit-web/README.md).

---

## Documentation

| Document                                                           | What it covers                                                          |
| ------------------------------------------------------------------ | ----------------------------------------------------------------------- |
| [`docs/PRD.md`](./docs/PRD.md)                                     | Product vision · day-1 user · competitive position                      |
| [`docs/architecture.md`](./docs/architecture.md)                   | System architecture · 12 ADRs · evidence chain                          |
| [`docs/demo-strategy.md`](./docs/demo-strategy.md)                 | The "three failures · one root cause · patch in four seconds" demo flow |
| [`docs/data-retention-policy.md`](./docs/data-retention-policy.md) | GDPR Article 28 · 24h trace retention · cryptographic erasure           |
| [`docs/cicd.md`](./docs/cicd.md)                                   | CI/CD pipeline · Cloud Run deploy · Workload Identity Federation        |
| [`docs/env-vars.md`](./docs/env-vars.md)                           | Master env-var reference — every variable across every app              |
| [`docs/run-config-schema.md`](./docs/run-config-schema.md)         | JSON Schema for audit run configuration                                 |
| [`docs/assets.md`](./docs/assets.md)                               | Designer briefs (banner · architecture SVG · tool ecosystem image)      |

Per-app README files:

- [`apps/phoenix-audit-web/README.md`](./apps/phoenix-audit-web/README.md) — Next.js operator surface (Firebase setup, env, tests, local-auth limitation)
- [`apps/phoenix-audit-agent/README.md`](./apps/phoenix-audit-agent/README.md) — ADK orchestrator (endpoints, deploy, evidence chain)
- [`apps/target-agent/README.md`](./apps/target-agent/README.md) — demo target (A2A surface, `PUBLIC_URL`, observability)
- [`infra/README.md`](./infra/README.md) — GCP bootstrap (Workload Identity Federation, Secret Manager)

---

## License

[Apache License 2.0](./LICENSE).

Attributions: see [`NOTICE`](./NOTICE). Architectural inspiration from `deepankarm/agent-chaos` (Apache-2.0) — no code copied.
