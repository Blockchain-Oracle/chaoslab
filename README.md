# Phoenix Audit

**An AI agent that audits other AI agents** — for safety, behavior, and EU AI Act compliance. Point it at any production agent (customer-support bot, healthcare prior-auth, coding helper, internal Copilot). Phoenix Audit runs a battery of adversarial tests, watches the agent fail or pass via Arize Phoenix traces, and produces a cryptographically signed, regulator-ready audit report keyed to a commit SHA. What Big-4 consulting charges €80,000 and 18 months for, Phoenix Audit produces in 90 seconds.

> Built for the Google Cloud Rapid Agent Hackathon (Arize track). Deadline 2026-06-11.

**Day-1 user:** Director of AI Governance / AI Safety Officer at any company running production AI agents. 2,000+ such roles open on LinkedIn today.

**Why now:** EU AI Act enforces 2026-08-02. Penalty for non-compliance is €15M or 3% of global turnover. Companies need automated, continuous, signed audit trails — not quarterly consultant reports.

**Demo URL:** TBD (filled in after Cloud Run deploy — see `docs/cicd.md`)

**Demo GIF / screenshot:** _TBD — cascade-flip moment at 2:15 of the 3-min demo video (see `docs/ux-spec.md` "The hero visual")_

---

## Run locally (3 steps)

```bash
# 1. Install Python + TS deps
uv sync
pnpm install

# 2. Set up secrets (one-time)
cp .env.example .env  # populate PHOENIX_API_KEY, GEMINI_API_KEY, etc.

# 3. Start everything
make dev   # starts agent + target + web locally
```

> Note: the `make dev` target itself lands in story-8.4. Until then, run each app individually — see `apps/*/README.md`.

For more: `docs/cicd.md` (cloud deploy), `docs/PRD.md` (what it is), `CLAUDE.md` (development workflow).

---

## How Phoenix Audit works (in 4 steps)

1. **Connect** — paste your production agent's URL or upload its config. Phoenix Audit inspects the agent's shape (does it answer support tickets? process claims? generate code?) and picks a regulatory framework to test against (EU AI Act / NIST AI RMF / HIPAA / SOC 2 + AI).
2. **Test** — Phoenix Audit runs a tailored adversarial battery (prompt injection, role confusion, data-exfiltration probes, tool misuse, hallucination probes, off-topic drift). Every test runs as a real Phoenix experiment against the live target. Traces flow into Phoenix in real time.
3. **Cluster** — when tests fail, Phoenix Audit reads the trace tree back via Phoenix MCP and clusters failures by root cause. Three independent failures that share one upstream span become one finding, not three. This is the moment everyone wants from a compliance tool but nobody has.
4. **Report** — Phoenix Audit renders a cryptographically signed PDF + JSON regulatory-grade evidence pack (EU AI Act Annex IV format), uploads it to Cloud Storage with a 7-day signed URL, and optionally opens a hardening recipe MR against the agent's GitLab repo. Auditable forever. Signed by your own compliance officer's Cloud KMS key — not by us.

---

## Why this isn't another observability dashboard

Phoenix observability tools (Phoenix itself, Langfuse, Helicone, Portkey) capture traces. They don't produce attestations. AI insurance products (Klaimee, Mount) underwrite the certificate. They don't run the audit. Enterprise governance platforms (AIUC, Credo AI, Fiddler) ship quarterly external audits. Mid-market teams can't afford them.

**Phoenix Audit sells you the auditable evidence — signed by your own compliance officer's Cloud KMS key.** Two hosting modes (per ADR-017): **default zero-friction mode** runs Phoenix Audit-hosted with a 24h trace-retention SLA and cryptographic erasure (paste your agent URL, click audit — no Phoenix Cloud account needed); **BYO-key mode** for regulated industries lets you bring your own Phoenix project so the trace evidence stays in your tenancy end-to-end. Continuous. Self-serve. Phoenix-native. No conflict of interest.

---

## Cross-framework target support

Phoenix Audit can audit ANY agent — not just Google ADK:

| Tier                 | Frameworks                                      | How                                             |
| -------------------- | ----------------------------------------------- | ----------------------------------------------- |
| **1** (native)       | Google ADK                                      | `RemoteA2aAgent` over A2A protocol              |
| **2** (instrumented) | LangChain, LangGraph, CrewAI, OpenAI Agents SDK | OpenInference instrumentor + adapter            |
| **3** (black-box)    | Any HTTP agent                                  | AgentCard discovery + behavioral fingerprinting |

See `docs/architecture.md` ADR-002 + `docs/stories/story-3.*` for the adapter layer.

---

## Repo layout

> Internal package directories still use the `phoenix-audit-*` codename pending S1.6 deploy refactor. The product is Phoenix Audit; the package names are an artifact of where the build started and will be renamed before the final Cloud Run deploy.

- `apps/phoenix-audit-agent/` — Phoenix Audit orchestrator (ADK; SequentialAgent w/ Inspector, Tester, Judge, Reporter sub-agents)
- `apps/phoenix-audit-web/` — Frontend (Next.js 16 + Tailwind 4 + visx + Framer Motion)
- `apps/target-agent/` — A deliberately naive customer-support agent used as the "agent under audit" for the demo
- `docs/` — Full spec (PRD, architecture w/ 12 ADRs, cicd, coding-standards, ux-spec, 52 stories)
- `research/google-cloud-rapid-agent/` — 60K+ lines of context (brainstorm, audit, RAT-results, hackathon primer, plan)
- `infra/` — IAM + Secret Manager + Cloud Run setup _(scaffolded in S1.4)_
- `scripts/` — utilities: 400-line guard _(S1.3)_, demo seed _(S8.2)_
- `.github/workflows/` — CI: pr-checks _(S1.5)_, staging-deploy _(S1.6)_, prod-promote _(S1.7)_, visual-tests _(S7.x)_

---

## License

[Apache License 2.0](./LICENSE).

Attributions: see [`NOTICE`](./NOTICE). Architectural inspiration from `deepankarm/agent-chaos` (Apache-2.0) — no code copied; ADR-006 amended.
