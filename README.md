# ChaosLab

**Chaos engineering for AI agents** — adversarial resilience testing. Inject 4 fault classes (malformed tool output, prompt injection, context poisoning, latency spike), watch any LLM agent fail via Phoenix traces, and autonomously emit a hardening recipe as a GitLab MR.

> Built for the Google Cloud Rapid Agent Hackathon (Arize track). Deadline 2026-06-11.

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
make dev   # starts chaoslab-agent + target-agent + chaoslab-web locally
```

> Note: the `make dev` target itself lands in story-8.4. Until then, run each app individually — see `apps/*/README.md`.

For more: `docs/cicd.md` (cloud deploy), `docs/PRD.md` (what it is), `CLAUDE.md` (development workflow).

---

## Cross-framework target support

ChaosLab can attack ANY agent (not just ADK):

| Tier | Frameworks | How |
|---|---|---|
| **1** (native) | Google ADK | `RemoteA2aAgent` over A2A protocol |
| **2** (instrumented) | LangChain, LangGraph, CrewAI, OpenAI Agents SDK | OpenInference instrumentor + adapter |
| **3** (black-box) | Any HTTP agent | AgentCard discovery + behavioral fingerprinting |

See `docs/architecture.md` ADR-002 + `docs/stories/story-3.*` for the adapter layer.

---

## Repo layout

- `apps/chaoslab-agent/` — orchestrator (ADK; SequentialAgent w/ Injector, Judge, Patcher)
- `apps/chaoslab-web/` — frontend (Next.js 16 + Tailwind 4 + visx + Framer Motion)
- `apps/target-agent/` — the naive customer-support agent under test
- `docs/` — full spec (PRD, architecture w/ 12 ADRs, cicd, coding-standards, ux-spec, 52 stories)
- `research/google-cloud-rapid-agent/` — 30k+ lines of context (brainstorm, audit, RAT-results)
- `infra/` — IAM + Secret Manager + Cloud Run setup _(scaffolded in S1.4)_
- `scripts/` — utilities: 400-line guard _(S1.3)_, demo seed _(S8.2)_
- `.github/workflows/` — CI: pr-checks _(S1.5)_, staging-deploy _(S1.6)_, prod-promote _(S1.7)_, visual-tests _(S7.x)_

---

## License

[Apache License 2.0](./LICENSE).

Attributions: see [`NOTICE`](./NOTICE). Architectural inspiration from `deepankarm/agent-chaos` (Apache-2.0) — no code copied; ADR-006 amended.
