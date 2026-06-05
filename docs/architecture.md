# Architecture — Phoenix Audit

**Status:** DRAFT — pending Abu approval (LOCKS upon approval; no post-approval changes)
**Last updated:** 2026-06-04 (rebranded from "ChaosLab" / "Trust Auditor" working names to **Phoenix Audit**; same closed-loop technical engine, reframed product for the compliance-officer persona — see `research/google-cloud-rapid-agent/PLAN-AI-TRUST-AUDITOR.md`)

---

## Product framing (read first; rest of doc is technical)

**What Phoenix Audit IS:** an AI agent that audits other AI agents for safety + EU AI Act compliance. Produces a cryptographically signed regulator-ready report keyed to a commit SHA.

**Same engine, swapped framing:** the "chaos engineering" framing pre-2026-06-04 was technically correct but commercially weak. The exact same code paths (test injector → Phoenix trace observer → LLM-judge → patcher) now serve a _compliance auditor_ persona instead of a _chaos engineer_ persona. Internal package directories (`apps/chaoslab-agent`, `apps/chaoslab-web`) remain unchanged as codenames pending S1.6 deploy rename; the product is Phoenix Audit in every user-facing surface.

---

## Stack (locked)

- **Language (backend):** Python 3.12
- **Language (frontend):** TypeScript 5.x
- **Agent framework:** Google Agent Development Kit (ADK) — `google-adk` (latest verified)
- **Frontend framework:** Next.js 16 (App Router, server components default — bumped per audit; v15 patterns still work)
- **Styling:** Tailwind 4 (CSS-first config) + shadcn/ui (New York style)
- **Charts:** visx (`@visx/group`, `@visx/scale`, `@visx/shape`, `@visx/grid`, `@visx/axis`, `@visx/responsive`)
- **Animation:** Framer Motion v12+
- **State (FE):** Zustand v5 (run state) + TanStack Query v5 (server) + `nuqs` (URL)
- **Observability + eval:** Arize Phoenix (Phoenix Cloud during demo / judging; Docker self-host for dev)
- **LLM:** Gemini 3.5 Flash (default + judge LLM) — `JUDGE_LLM = "gemini-3.5-flash"` is mandatory (see ADR-007)
- **Deploy:** Google Cloud Run × 3 services (chaoslab-web, chaoslab-agent, target-agent)
- **Build registry:** Google Artifact Registry
- **Secrets:** Google Secret Manager (Phoenix API key, GitLab PAT)
- **Auth (CI → GCP):** Workload Identity Federation (no JSON keys)
- **Package manager (Python):** `uv`
- **Package manager (TS):** `pnpm`
- **Lint/format (Python):** `ruff` (lint + format) + `ty` (type-check, primary) with `mypy strict` fallback if `ty` blocks build (ADR-001)
- **Lint/format (TS):** ESLint 9 (flat config) + Prettier + Tailwind plugin
- **Test framework (BE):** `pytest` + `pytest-asyncio` + `respx` + `hypothesis`
- **Test framework (FE):** `vitest` + React Testing Library + `@playwright/test`
- **CI:** GitHub Actions (Workload Identity Federation to GCP)
- **Pre-commit:** `pre-commit` framework (ruff, ty, eslint, prettier, markdownlint, gitleaks, conventional-commits, **custom 400-line guard**)

---

## Repo structure

```
rapid-agents/                                      # project root
├── apps/
│   ├── chaoslab-agent/                            # Python ADK orchestrator (Cloud Run service #1)
│   │   ├── pyproject.toml
│   │   ├── src/chaoslab_agent/
│   │   │   ├── __init__.py
│   │   │   ├── main.py                            # FastAPI/ADK entry, exposes /run, /stream, /health
│   │   │   ├── orchestrator.py                    # SequentialAgent: Injector → Judge → Patcher
│   │   │   ├── injector/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── agent.py                       # Injector sub-agent
│   │   │   │   ├── faults/
│   │   │   │   │   ├── malformed_tool_output.py   # F1
│   │   │   │   │   ├── prompt_injection.py        # F2
│   │   │   │   │   ├── context_poisoning.py       # F3
│   │   │   │   │   └── latency_spike.py           # F4
│   │   │   │   └── target_adapters/
│   │   │   │       ├── adk_adapter.py             # Tier 1: ADK target via A2A
│   │   │   │       ├── langchain_adapter.py       # Tier 2: LangChain via OpenInference
│   │   │   │       ├── crewai_adapter.py          # Tier 2: CrewAI
│   │   │   │       ├── openai_sdk_adapter.py      # Tier 2: OpenAI Agents SDK
│   │   │   │       └── http_blackbox_adapter.py   # Tier 3: HTTP black-box
│   │   │   ├── judge/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── agent.py                       # Judge sub-agent
│   │   │   │   ├── rubrics/                       # LLM-as-judge eval rubrics per fault class
│   │   │   │   └── clustering.py                  # failure clustering via LLM-as-clusterer
│   │   │   ├── patcher/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── agent.py                       # Patcher sub-agent
│   │   │   │   ├── recipe.py                      # HardeningRecipe pydantic schema
│   │   │   │   ├── markdown_emitter.py            # Markdown artifact path
│   │   │   │   └── gitlab_emitter.py              # GitLab MCP MR-emission path
│   │   │   ├── phoenix_tools/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── run_experiment.py              # custom ADK FunctionTool wrapping phoenix Python SDK
│   │   │   │   └── write_annotation.py            # custom ADK FunctionTool wrapping span annotation write
│   │   │   ├── adk_types.py                       # quarantine module (pydantic wrappers over ADK primitives)
│   │   │   ├── observability.py                   # OpenInference + structlog setup
│   │   │   └── config.py                          # pydantic-settings env loader
│   │   ├── tests/
│   │   │   ├── unit/
│   │   │   ├── integration/
│   │   │   └── e2e/
│   │   ├── Dockerfile
│   │   └── README.md
│   ├── chaoslab-web/                              # Next.js 16 frontend (Cloud Run service #2)
│   │   ├── package.json
│   │   ├── next.config.ts
│   │   ├── tsconfig.json
│   │   ├── postcss.config.mjs
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx                           # demo landing
│   │   │   ├── globals.css                        # Tailwind 4 + @theme tokens
│   │   │   ├── (demo)/
│   │   │   │   ├── attack/page.tsx                # live attack run UI
│   │   │   │   └── replay/page.tsx                # canonical pre-recorded run
│   │   │   ├── api/
│   │   │   │   └── stream/route.ts                # SSE → proxy from chaoslab-agent
│   │   │   └── _components/
│   │   │       ├── attack-matrix.tsx              # 5x5 grid + Framer Motion stagger
│   │   │       ├── resilience-curve.tsx           # visx LinePath with PATCH marker
│   │   │       ├── agent-pipeline.tsx             # multi-agent A2A visualization
│   │   │       └── receipt-card.tsx               # final cost/time/MR receipt
│   │   ├── components/ui/                         # shadcn primitives
│   │   ├── lib/
│   │   │   ├── api-client.ts
│   │   │   ├── env.ts                             # zod-validated env
│   │   │   └── utils.ts
│   │   ├── stores/
│   │   │   └── run-store.ts                       # Zustand
│   │   ├── tests/
│   │   │   ├── unit/                              # Vitest
│   │   │   └── e2e/                               # Playwright
│   │   ├── Dockerfile
│   │   └── README.md
│   └── target-agent/                              # naive ADK target (Cloud Run service #3)
│       ├── pyproject.toml
│       ├── src/target_agent/
│       │   ├── main.py                            # ADK agent exposed via `to_a2a()`
│       │   ├── agent.py                           # naive customer-support agent
│       │   └── tools.py                           # lookup_order, refund, escalate (3 tools, no validation)
│       ├── tests/
│       ├── Dockerfile
│       └── README.md
├── packages/
│   └── shared-types/                              # cross-language types (JSON schemas + TS d.ts)
│       └── hardening-recipe.json
├── infra/
│   ├── workload-identity-federation.sh            # one-time GCP setup
│   ├── secret-manager-setup.sh
│   ├── cloud-run-deploy.sh
│   └── README.md
├── .github/
│   └── workflows/
│       ├── pr-checks.yaml                         # lint + tests + 400-line + type-check
│       ├── staging-deploy.yaml                    # deploy on merge to main
│       ├── prod-promote.yaml                      # manual promotion (same image hash)
│       └── visual-tests.yaml                      # Playwright against staging URL
├── scripts/
│   ├── check_max_lines.py                         # 400-line enforcer (Python+TS+MD)
│   └── seed_demo_data.py                          # canonical-replay seeding for Phoenix
├── .pre-commit-config.yaml
├── pyproject.toml                                 # workspace root (uv workspace)
├── pnpm-workspace.yaml
├── package.json                                   # workspace root
├── CLAUDE.md
├── README.md
├── LICENSE                                        # Apache-2.0
├── NOTICE                                         # for vendored deepankarm/agent-chaos attribution
├── docs/                                          # this folder — spec artifacts
└── research/                                      # the 30k-line corpus
```

---

## Required external libraries (use these — do not reinvent)

### Python (backend — `chaoslab-agent`, `target-agent`)

| Library                                             | Purpose                                                                                                | How to add                                                                                                                            |
| --------------------------------------------------- | ------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------- |
| `google-adk`                                        | The agent framework                                                                                    | `uv add google-adk`                                                                                                                   |
| `arize-phoenix`                                     | Phoenix client + eval framework                                                                        | `uv add arize-phoenix`                                                                                                                |
| `arize-phoenix-otel`                                | OpenInference → Phoenix exporter                                                                       | `uv add arize-phoenix-otel`                                                                                                           |
| `arize-phoenix-client`                              | Python client for Phoenix Cloud (experiments, datasets, annotations)                                   | `uv add arize-phoenix-client`                                                                                                         |
| `openinference-instrumentation-google-adk`          | Auto-instruments ADK with OpenInference spans                                                          | `uv add openinference-instrumentation-google-adk`                                                                                     |
| `openinference-instrumentation-langchain`           | Tier 2 LangChain target instrumentation                                                                | `uv add openinference-instrumentation-langchain`                                                                                      |
| `openinference-instrumentation-crewai`              | Tier 2 CrewAI target instrumentation                                                                   | `uv add openinference-instrumentation-crewai`                                                                                         |
| `pydantic` v2 + `pydantic-settings`                 | Schemas + env-based config                                                                             | `uv add pydantic pydantic-settings`                                                                                                   |
| `httpx`                                             | Async HTTP client                                                                                      | `uv add httpx`                                                                                                                        |
| `respx`                                             | Mock httpx in tests                                                                                    | `uv add --dev respx`                                                                                                                  |
| `structlog`                                         | Structured logging with Phoenix trace ID propagation                                                   | `uv add structlog`                                                                                                                    |
| `typer`                                             | CLI (`chaoslab run`, `chaoslab status`, etc.)                                                          | `uv add typer`                                                                                                                        |
| `python-gitlab`                                     | GitLab MR emission (until official GitLab MCP Python SDK exists)                                       | `uv add python-gitlab`                                                                                                                |
| `mcp`                                               | Official MCP Python SDK for the Phoenix MCP client side                                                | `uv add mcp`                                                                                                                          |
| `google-cloud-secret-manager`                       | Read secrets at runtime                                                                                | `uv add google-cloud-secret-manager`                                                                                                  |
| `pytest` + `pytest-asyncio` + `pytest-cov`          | Tests                                                                                                  | `uv add --dev pytest pytest-asyncio pytest-cov`                                                                                       |
| `hypothesis`                                        | Property-based tests                                                                                   | `uv add --dev hypothesis`                                                                                                             |
| **Vendored:** `deepankarm/agent-chaos` (Apache-2.0) | Fault primitive library — saves 3-4 days of build (per `architecture/01-reference-implementations.md`) | Copy `src/agent_chaos/chaos/{llm,tool,user}.py` into `chaoslab-agent/src/chaoslab_agent/injector/faults/_vendored/`; add NOTICE entry |

### TypeScript (frontend — `chaoslab-web`)

| Library                                      | Purpose                 | How to add                                                                                       |
| -------------------------------------------- | ----------------------- | ------------------------------------------------------------------------------------------------ |
| `next` (15.x)                                | Framework               | `pnpm add next`                                                                                  |
| `react` + `react-dom` (19.x)                 | UI runtime              | `pnpm add react react-dom`                                                                       |
| `tailwindcss` (4.x) + `@tailwindcss/postcss` | Styling                 | `pnpm add -D tailwindcss @tailwindcss/postcss`                                                   |
| `shadcn/ui` (CLI)                            | Component generation    | `pnpm dlx shadcn@latest add button card badge dialog tabs scroll-area separator toast tooltip`   |
| `@visx/*`                                    | Chart primitives        | `pnpm add @visx/group @visx/scale @visx/shape @visx/grid @visx/axis @visx/responsive @visx/text` |
| `framer-motion`                              | Animation               | `pnpm add framer-motion`                                                                         |
| `zustand` (v5)                               | Client state            | `pnpm add zustand`                                                                               |
| `@tanstack/react-query` (v5)                 | Server state            | `pnpm add @tanstack/react-query`                                                                 |
| `nuqs`                                       | URL state               | `pnpm add nuqs`                                                                                  |
| `zod`                                        | Env + schema validation | `pnpm add zod`                                                                                   |
| `@playwright/test`                           | E2E + visual regression | `pnpm add -D @playwright/test`                                                                   |
| `vitest` + `@testing-library/react`          | Unit tests              | `pnpm add -D vitest @testing-library/react @testing-library/jest-dom jsdom`                      |

### Context7 library research rule (mandatory)

Before implementing anything from scratch:

```bash
mcp__plugin_context7_context7__resolve-library-id libraryName="<what you need>"
mcp__plugin_context7_context7__query-docs context7CompatibleLibraryID="<id>" topic="<area>" tokens=5000
```

**If a library exists, use it. Do not build it yourself.**

---

## Banned patterns

- `from-purple-500 to-pink-500` Tailwind gradient — generic AI slop
- `text-gray-600` body text on white — low contrast
- `font-sans` without explicit font import — defaults to Inter slop
- Hardcoded mock data in agent hot path — real Gemini, real Phoenix, real target
- `useState` for state shared across 3+ components — use Zustand
- `console.log` / `print()` for production logging — use structlog (Python) or built-in console + Cloud Logging
- `requests` library in Python — use `httpx` (async-native)
- `mypy` global type-check — use `ty` (ADR-001); use mypy strict only in fallback mode if `ty` blocks build
- Naked `gemini-pro` / `gemini-2.5-pro` / `gemini-3.1-pro-preview` for judge LLM — Pro is ~1.33× more expensive than Flash (revised from "17×" per audit A10). JUDGE_LLM must be `gemini-3.5-flash` (ADR-007). Flash-Lite (`gemini-3.1-flash-lite`) is the 8-11× cheaper alternative if budget pressure appears.
- LangChain / LangGraph / LlamaIndex as PRIMARY orchestrator in the SUBMITTED code (per hackathon rules) — these are PERMITTED as target-instrumentation libraries (Tier 2) but never as the orchestrator
- Claude / OpenAI / Anthropic SDKs as runtime LLM in the agent — Gemini only in submitted code
- Module-level imports of `google-adk` outside of `chaoslab_agent.adk_types` quarantine — keeps the dynamic typing boundary controlled

---

## Architecture decisions (ADRs)

### ADR-001: Use `ty` (Astral) as the primary type checker, `mypy strict` as fallback

**Decision:** Primary: `ty`. Fallback: `mypy strict` if `ty` blocks builds.

**Rationale:** Google's `agent-starter-pack` (canonical template) canonized `ty` in 2026 — the lint chain is `ruff check . && ruff format . --check && ty check .`, three Rust binaries, all Astral. mypy is not in the template's `[project.optional-dependencies.lint]`. Going with `ty` aligns with the canonical convention. The Astral monoculture is the 2026 default and the fastest toolchain. **Risk:** `ty` is still alpha in mid-2026. **Mitigation:** if `ty` produces false positives or fails on a specific ADK pattern that mypy passes, switch the CI step to mypy. Document in `CLAUDE.md`. (Source: `best-practices/01 §11`, `best-practices/03 §3-4`.)

### ADR-002: Hybrid multi-agent architecture (Candidate B from `architecture/03`) with cross-tier target adapter layer

**Decision:** Orchestrator (Python ADK on Cloud Run) contains 3 in-process sub-agents (Injector, Judge, Patcher via `SequentialAgent`). Target agent is OUT-OF-PROCESS, called via A2A (`RemoteA2aAgent`). Target adapter layer (`injector/target_adapters/*.py`) supports 3 tiers: Tier 1 (ADK native), Tier 2 (LangChain/CrewAI/OpenAI Agents SDK via OpenInference instrumentors), Tier 3 (HTTP black-box with behavioral fingerprinting).

**Rationale:** SalesShortcut won the ADK Hackathon Grand Prize with this exact shape — orchestrator with in-process sub-agents + A2A peer. Fault isolation only where it matters (target genuinely crashes without killing the orchestrator). Multi-tier target adapter is the differentiator: per `context/03 §13`, **no existing red-team product treats multi-agent A2A topologies as first-class** and no product supports more than one framework natively. ChaosLab covers all 3 tiers and the multi-agent A2A case (target itself can be a multi-agent system, A2A peer is opaque to the orchestrator). (Source: `architecture/03 §8 Candidate B`, `context/03 §13`, `context/04`.)

### ADR-003: Three Cloud Run services (NOT Agent Runtime)

**Decision:** Deploy as 3 separate Cloud Run services: `chaoslab-web`, `chaoslab-agent`, `target-agent`. Use `min-instances=1` on web + agent during the judging window for cold-start mitigation. Target stays at `min-instances=0`.

**Rationale:** ChaosLab's workload is request/response in 60-180 second windows. Cloud Run's 60-minute HTTP timeout easily fits. Agent Runtime's 7-day continuous reasoning capability is a red herring for this wedge. Cloud Run gives full container control needed for the `npx @arizeai/phoenix-mcp` subprocess invocation. Cost projection: ~$72 over 9-day dev + 4-week judging window (Per `architecture/06 §5`). **Counter-intuitive cost note:** min-instances warm pool ($7/svc/mo) costs more than tokens ($25 judging window) at this scale. (Source: `architecture/06`.)

### ADR-004: Phoenix Cloud (free tier) for demo + judging, self-hosted Docker Phoenix for dev

**Decision:** Demo URL writes traces to Phoenix Cloud at `app.phoenix.arize.com`. Local dev uses `docker run arize-phoenix:latest`. Push only the canonical replay traces to Phoenix Cloud during judging (≤5k spans).

**Rationale:** Phoenix Cloud free tier is 25k spans/month / 15-day retention / 1GB — tight for active dev (~1,250 runs/month cap). Self-hosted Docker is unlimited + free for dev iteration. Judging window only needs the canonical replay subset visible. (Source: `architecture/02 §7`, `best-practices/01 §4`.)

### ADR-005: Phoenix MCP is partial — wrap Python SDK as ADK `FunctionTool` for write operations

**Decision:** Use `@arizeai/phoenix-mcp` (stdio transport) for trace reads, span queries, dataset reads, prompt reads. Wrap `phoenix.client.AsyncClient().experiments.run_experiment(...)` and `phoenix.client.AsyncClient().spans.log_span_annotations(...)` as custom ADK `FunctionTool` instances in `chaoslab_agent.phoenix_tools/`. Both wrappers are ≤30 LOC each.

**Rationale:** The Phoenix MCP server exposes `list-experiments-for-dataset` and `get-experiment-by-id` but NOT `run-experiment` or `create-experiment`. Same for span annotations (`list-annotation-configs` only). To close the ChaosLab loop, we wrap the Python SDK for write ops. RAT runbook Step 3 (revised) validates this path on Day 1. (Source: `architecture/02 §1, §9.5-9.6`, `RAT-runbook.md` Step 3.)

### ADR-006: Attribution-only credit to `deepankarm/agent-chaos`; do NOT vendor (AMENDED 2026-06-03 per audit A5)

**Decision:** Add `NOTICE` file entry crediting `github.com/deepankarm/agent-chaos` (Apache-2.0) as architectural inspiration. **Do NOT copy or vendor any source files.** Implement `MalformedToolOutputFault`, `PromptInjectionFault`, `ContextPoisoningFault`, `LatencySpikeFault` natively against ADK callbacks per `architecture/04 §8`.

**Rationale (AMENDED):** Original ADR-006 claimed vendoring saves 3-4 days. The spec audit (`spec-audit/03-agent-chaos-vendor-audit.md`) verified empirically that this is wrong. The upstream `chaos/llm.py` is Anthropic-only (hardcoded `anthropic.RateLimitError`/`APITimeoutError`); `patch/providers/gemini.py` is a 633-byte `NotImplementedError` stub; the README admits "Planned: Gemini." Stories F1-F4 (S5.2-S5.5) already reimplement fault primitives natively against ADK `before_tool_callback` / `before_model_callback` — actual code reuse is zero. Attribution-only is legally cleaner (Apache-2.0 doesn't require attribution for non-copy use, but we keep it as a courtesy) and removes a brittle vendoring story from the build. Net effort drops from ~1.5h vendoring + integration to ~20 min attribution. **No better Apache-2.0 alternative exists** (audit verified). (Source: `spec-audit/03-agent-chaos-vendor-audit.md`, audit-04.)

### ADR-007: `JUDGE_LLM = "gemini-3.5-flash"` is mandatory (hard config) (RATIONALE AMENDED 2026-06-03 per audit A10)

**Decision:** All LLM-as-judge eval calls use `gemini-3.5-flash`. Configuration via env var `JUDGE_LLM=gemini-3.5-flash` is required. CI gate asserts the config before deploy.

**Rationale (AMENDED):** Original ADR-007 claimed Pro is 17× more expensive than Flash. The spec audit (`spec-audit/06-runtime-audit.md`) verified empirically that **as of mid-2026, Pro is only ~1.33× more than Flash, not 17×**. Flash is still the right pick — Phoenix tutorials default to Pro and using Pro for a continuous eval loop still adds nontrivial cost — but the magnitude is smaller than originally documented. **Flash-Lite (`gemini-3.1-flash-lite`) is the actual 8-11× cheaper alternative** if budget pressure appears; documented as a fallback in cost-overrun scenarios. Flash chosen as the default for safety: Flash-Lite quality on Phoenix's `tool_invocation` + `hallucination` rubrics is unverified for ChaosLab's failure-clustering use case. (Source: `architecture/04 §4`, `best-practices/06 §3`, `spec-audit/06-runtime-audit.md`.)

### ADR-008: "Build once, promote everywhere" CI/CD pattern

**Decision:** GitHub Actions builds each service's Docker image once on staging deploy, tags with `:${{ github.sha }}`, pushes to Artifact Registry. Prod promotion uses `gcloud run services update --image=...@sha256:<same hash>` — never rebuilds. Cloud Run blue/green via `--no-traffic --tag=candidate` + smoke test + `update-traffic --to-latest=100`.

**Rationale:** Eliminates entire class of "works in staging, breaks in prod" bugs from base-image drift, dependency resolution variance, build-arg differences. Free blue/green on Cloud Run. (Source: `best-practices/02 §1`.)

### ADR-009: Workload Identity Federation for GCP auth from GitHub Actions

**Decision:** GitHub Actions auth to GCP via Workload Identity Federation (OIDC token exchange). Zero long-lived JSON keys committed or stored. WIF pool + provider + service account binding set up via `infra/workload-identity-federation.sh`.

**Rationale:** Modern non-secret auth. No JSON key rotation. Least-privilege per-workflow service accounts. Top-5 WIF failure modes from `best-practices/02 §13` documented in `infra/README.md` for future-Abu sanity. (Source: `best-practices/02 §3, §13`.)

### ADR-010: 400-line file enforcement via custom pre-commit + CI script

**Decision:** Custom Python script `scripts/check_max_lines.py` enforces the 400-line rule on every Python, TypeScript, JavaScript, and Markdown file. Wired into `.pre-commit-config.yaml` as a local hook AND `.github/workflows/pr-checks.yaml` as a CI gate. Both hard fail at 401 lines.

**Rationale:** Ruff has no module-level line-count rule (only per-function `PLR0915`). ESLint's `max-lines` works for TS/JS but Python needs the custom script. Belt + suspenders enforcement (local + CI) catches both casual commits and force-pushes. (Source: `best-practices/03 §1.1`.)

### ADR-011: Hybrid GitLab MR emission — official MCP for MR creation, `python-gitlab` SDK for branch + file commits (AMENDED 2026-06-03 per audit A1)

**Decision:** Patcher emits the hardening recipe via THREE artifacts: (a) Markdown artifact to GCS (always succeeds, fallback for non-GitLab judges), (b) GitLab branch creation via `python-gitlab` SDK `POST /projects/:id/repository/branches`, (c) file commits via `python-gitlab` SDK `POST /projects/:id/repository/files/:file_path`, (d) **MR creation via the official `https://gitlab.com/api/v4/mcp` endpoint's `create_merge_request` tool** — this is the call that earns the hackathon's "official MCP" judging credit.

**Rationale (AMENDED):** Original ADR-011 assumed the official GitLab MCP server exposed file-commit tools. The spec audit (`spec-audit/04-gitlab-mcp-audit.md`) verified empirically that the official endpoint exposes only 16 tools and **`create_branch` + `create_or_update_file` are NOT among them**. If S6.6 calls those via MCP it hits "unknown tool" errors at runtime. The hybrid approach preserves the judging credit (MR creation IS via official MCP) while routing the missing capabilities through the `python-gitlab` SDK (already a project dep). **Free-tier vs Premium open question:** official GitLab docs say MCP requires Premium/Ultimate; hackathon FAQ claimed trial-tier sufficient. **Day-1 verification step:** spin up a fresh GitLab.com trial account, test the MCP `initialize` handshake + `create_merge_request` tool. If trial fails, fall back to all-`python-gitlab`-SDK (lose the "official MCP" credit but demo still works). Community MCP servers (`zereight`, `mcpland`, `wadew`) are BANNED — they expose more tools but using them loses the official-MCP judging credit. (Source: `partner-gitlab.md`, `spec-audit/04-gitlab-mcp-audit.md`.)

### ADR-012: Use ADK 2.1.0's deprecated workflow classes (`SequentialAgent`, `LoopAgent`, `ParallelAgent`) for hackathon speed (NEW 2026-06-03 per audit A11)

**Decision:** ChaosLab's orchestrator uses `from google.adk.agents import SequentialAgent` (and `LoopAgent`/`ParallelAgent` where needed). These classes are `@deprecated` in ADK 2.1.0 — the canonical replacement is `from google.adk.workflow import Workflow`. Spec retains the deprecated classes for hackathon speed; `pyproject.toml` `filterwarnings = ["ignore::DeprecationWarning:google.*"]` suppresses the warning.

**Rationale:** The deprecated classes still work in ADK 2.1.0 and have stable APIs documented in every official sample and the `agent-starter-pack` template. The new `Workflow` class requires reorganizing all sub-agent composition (E4 orchestrator + E5 injector + E6 judge/patcher all touch this). Migrating mid-hackathon would consume ~4 hours of refactor + retest budget with zero feature gain. **4-week judging-window risk:** if Google ships ADK 3.0 with the deprecated classes removed before 2026-07-06 (judging end), the demo URL would break. **Mitigation:** pin `google-adk>=2.1.0,<3.0.0` in `pyproject.toml` to lock the major version. Post-hackathon (post-2026-07-06) is the right time to migrate to `Workflow`. (Source: `spec-audit/01-adk-a2a-audit.md`.)

### ADR-013: Trace tenancy = customer-side Phoenix project + cross-tenant read at report time (NEW 2026-06-05 per memo 27 sub-q 9)

**Decision:** Phoenix Audit does NOT centralize audit traces in our vendor Phoenix project. Model C (hybrid) is the locked tenancy model:

- **Customer's target agent** emits OpenInference traces to **the Customer's Phoenix project** (standard ADK instrumentation pattern — `setup_observability()` reads `PHOENIX_API_KEY` + `PHOENIX_COLLECTOR_ENDPOINT` from env, which the Customer controls).
- **Phoenix Audit's orchestrator** runs in our tenancy but holds the Customer's Phoenix credentials only for the duration of one audit run (passed via the run-config, NOT persisted server-side). At report-generation time, it pulls the relevant trace slice — filtered by `phoenix_audit.audit_run_id` span attribute (namespaced; see Tradeoff section below for why bare `audit_run_id` is unsafe) — from the Customer's Phoenix project via `phoenix.client.Client(api_key=customer_phoenix.api_key, endpoint=customer_phoenix.endpoint).spans.get_spans_dataframe(...)`.
- **Audit report** explicitly states: _"Audit traces remain in the Customer's Phoenix project (project ID: X) under the Customer's data-retention policy. Phoenix Audit holds no copy."_

**Rationale:** PRD + CLAUDE.md both claim "the customer's compliance officer signs the report with THEIR Cloud KMS key." That claim is theater if the underlying trace evidence sits in our vendor Phoenix tenancy:

1. **Data sovereignty.** A regulated Customer (banking, healthcare, EU AI Act Annex IV) cannot have probe-and-response data sitting in a vendor tenancy without a DPA + SCC + cross-border transfer review. Routing through their own Phoenix project sidesteps every one of those.
2. **Signature integrity.** A signature over a report whose underlying evidence sits in a different vendor's DB is cryptographically valid but contractually meaningless — the Customer can't audit the chain-of-custody on the evidence side.
3. **Empirical viability — already validated.** RAT-2 Test 1 (`research/google-cloud-rapid-agent/RAT-2-results.md` lines 29-49) measured cross-tenant Phoenix read at **1.37s emit-to-visible roundtrip**. That's fast enough for the live audit UI; no rearchitecture needed. The script at `rat-2-phoenix-audit/test1_cross_tenant_ingest.py` is the canonical reference.

**Run-config schema:** documented in `docs/run-config-schema.md`. The Customer supplies `customer_phoenix.endpoint` (URL, e.g. `https://app.phoenix.arize.com/s/<workspace-slug>`) + `customer_phoenix.api_key` (passed via a one-shot token, NOT persisted). Phoenix Audit's orchestrator (Epic 4) uses these to write spans during the audit + read them back at report time.

**Tradeoff acknowledged:** Phoenix Cloud's authn model today (per https://github.com/Arize-ai/phoenix/issues/10504) doesn't yet support per-project access scoping at the API-key level — the Customer's API key has access to all their projects. Phoenix Audit's v1 mitigation is to namespace the filter attribute as `phoenix_audit.audit_run_id` (NOT bare `audit_run_id`, which a Customer's other observability workload might also set, causing accidental cross-workload bleed into the audit slice). For the realistic threat model (Customer is the protected party, not an adversary), namespace alone closes the accidental-collision risk. Post-hackathon improvement tracked separately (audit-notes TBD-18): a `phoenix_audit.run_signature` = HMAC(audit_run_id, per-run ephemeral key) so the filter is cryptographically tight against malicious cross-tenant injection, not just attribute-equal. Even with the namespaced filter, Phoenix Audit DOES read the full project's span set into memory before filtering — the cover-page paragraph "Phoenix Audit holds no copy" applies only after report generation, NOT during the filter step. Post-hackathon: pursue Phoenix's scoped-key feature OR a server-side filter API so the in-process transient read goes away.

**Source:** `research/google-cloud-rapid-agent/brainstorm/27-shape-a-architecture-validation.md` §"Sub-question 9 — Result persistence + revisability (trace tenancy)". Audit-notes D4-9 records the formal spec landing.

### ADR-015: X-Phoenix-Audit-\* header convention for side-effect prevention (NEW 2026-06-05 per memo 27 sub-q 5)

**Decision:** Phoenix Audit emits a fixed set of HTTP headers on every probe request to the target. Well-behaved targets honor the headers by short-circuiting side-effecting tool calls (refund, payment, ticket-creation, etc.) and signaling acknowledgment via an OpenInference span attribute. Targets that don't honor get a verbatim warning in the audit report so the customer's compliance officer can see the gap.

The three headers (locked schema in `docs/header-convention.md`):

- `X-Phoenix-Audit: true` — flag header; signals this request is an audit probe (not normal traffic).
- `X-Phoenix-Audit-Run-Id: <uuid>` — UUIDv4 identical to the run-config's `audit_run_id` (per `docs/run-config-schema.md`), so the target can correlate every probe in the run.
- `X-Phoenix-Audit-Dry-Run: true|false` — whether side-effecting tools SHOULD be short-circuited (true = audit mode, false = side-effects allowed).

Targets opt into the convention by reading the headers, short-circuiting side-effecting tools when `X-Phoenix-Audit-Dry-Run` is `true`, AND emitting `phoenix_audit.honored = true` as a span attribute on the response. Phoenix Audit's reporter checks for that attribute on every probe-response trace; if absent, the audit report appends the verbatim warning ("Target did not signal it honored the X-Phoenix-Audit-\* headers...") locked in `docs/header-convention.md`.

**Rationale:** memo 27 sub-question 5 surveyed the OSS landscape. **No OSS auditor solves side-effect prevention from the auditor's side** — Promptfoo, Garak, DeepTeam all punt to the customer ("use a staging target, configure mocks, implement application-level safeguards"). AIR Blackbox and Microsoft's Agent Governance Toolkit solve it from the _defender's_ side (policy gates on the target), not the auditor's side.

Three honest options:

- **Option A (the AIUC-1 path):** require customer to point at a staging target; report says "audit ran against `<URL>` in environment `<staging|production>` per customer declaration." Cost 0, but a demo target that's literally our own subprocess looks like we never thought about it.
- **Option B (the convention path — ADOPTED):** define a header convention; cost 1 spec patch; risk = nobody honors headers in v1 but the convention is documented and we have a defensible answer to "what if my agent actually called refund() during your audit?"
- **Option C (the gate proxy):** build a thin proxy in front of the target that intercepts and gates side-effecting tool calls. Cost 3+ stories. **Rejected** — would just be reinventing AIR Blackbox at the wrong layer (we don't see tool calls, we see agent inputs/outputs).

**Tradeoff acknowledged:** the headers are **advisory, not enforced.** A target that ignores them still executes side-effecting tools for real. The acknowledgment span attribute (`phoenix_audit.honored = true`) is self-reported by the target — a malicious target could echo the attribute without actually honoring. For the realistic threat model (Customer wants to audit their own agent; the agent is cooperative or at worst neutral, not adversarial), self-reporting is sufficient. Post-hackathon improvement tracked separately (audit-notes TBD-19): HMAC-bound headers so the convention is cryptographically tight, not just attribute-equal. This is the auditor's-side analog to ADR-013's TBD-18 (HMAC on the trace filter attribute).

**Run-Id correlation:** the `X-Phoenix-Audit-Run-Id` header value MUST equal the run-config's `audit_run_id` field (UUIDv4 generated server-side at orchestrator start). Same UUID across all probes in the run. Targets can correlate probes to the audit run by reading this header; auditor correlates probe→response via the same UUID's appearance on the response span attributes.

**Source:** `research/google-cloud-rapid-agent/brainstorm/27-shape-a-architecture-validation.md` §"Sub-question 5 — Idempotency + side-effect prevention". Audit-notes D4-10 records the formal spec landing.

### ADR-016: Multi-turn session shape — 3 single-turn + 3 two-turn for the 6-probe demo battery (NEW 2026-06-05 per memo 27 sub-q 2)

**Decision:** Phoenix Audit's 6-probe demo battery runs as a mix: **3 single-turn probes + 3 two-turn (Crescendo-style) probes.** The exact per-probe assignment is locked in `docs/session-shape.md`. This is a deliberate budget-vs-coverage tradeoff, not full coverage of any attack category.

The split (full table in `session-shape.md`):

- **Single-turn (3):** HarmBench #1, HarmBench #2, CARES. Harmful-output elicitation + healthcare-safety; direct prompts are high-signal here.
- **Two-turn (3):** OWASP LLM01 (Crescendo prompt-injection), MITRE ATLAS indirect-injection-via-tool-output, MITRE ATLAS trust-establish-then-escalate. The most-cited real-world prompt-injection attacks require >1 turn of context to land.

**Rationale:** memo 27 sub-question 2 surveyed how every OSS auditor handles session statefulness. Promptfoo names multi-turn primitives as first-class (Crescendo, GOAT, Hydra Multi-turn, Mischievous User). DeepEval / DeepTeam make multi-turn a headline feature (Conversation Completeness / Turn Faithfulness only exist in multi-turn mode). Inspect AI is multi-turn-by-design. Garak is mostly stateless (the "easy mode" we don't want to silently ship). The empirical 16s/round-trip A2A latency (RAT-2 Risk A) caps total wire time; running all 6 probes as 2-turn would blow the 90-second demo budget. The 3+3 mix captures the higher-signal Crescendo-style attacks (where single-turn would be materially weaker) while staying inside budget.

**Honest disclosure (locked in session-shape.md):** Single-turn is the **easy mode** of the attack. Compliance officers reading the audit report should treat the 3 single-turn probes as floor-of-difficulty checks, NOT as comprehensive coverage of their categories. The session-mix is a deliberate budget-vs-coverage tradeoff, not full coverage.

**Source:** `research/google-cloud-rapid-agent/brainstorm/27-shape-a-architecture-validation.md` §"Sub-question 2 — Stateful vs stateless audit session". Audit-notes D4-11 records the formal spec landing.

---

## Data flow (one ChaosLab run, narrative)

1. **User hits demo URL.** `chaoslab-web` (Next.js) loads. Server component fetches `/api/health` proxying to `chaoslab-agent`. Page renders with idle state.
2. **User clicks "Run ChaosLab against target agent".** Client POSTs to `chaoslab-web/api/run` which proxies to `chaoslab-agent/run`. Connection upgraded to SSE for live streaming.
3. **Orchestrator starts.** ADK `SequentialAgent` begins: phase = `baseline`. Injector calls Target (`RemoteA2aAgent`) 25 times WITHOUT fault — establishes baseline pass rate. Each call emits an OpenInference trace span to Phoenix.
4. **Pre-flight check (Chaos Toolkit pattern, per `architecture/01 §7`):** if baseline pass rate <80%, abort with error "target is already broken." Otherwise proceed.
5. **Attack phase.** Injector cycles through 4 fault classes × ~6 runs each = 25 runs. For each run: pick fault class, configure target adapter, invoke target, capture span. Cells in the Attack Matrix update via SSE as spans land.
6. **Judge phase.** Judge sub-agent reads the 25 attack-phase traces via Phoenix MCP. Runs LLM-as-judge eval per fault class using ADK's `AgentEvaluator` (ROUGE) + Phoenix's `tool_invocation` evaluator + 2 custom rubrics. Clusters failures using Gemini 3.5 Flash as the clusterer. Writes cluster annotations back to span via custom `write_annotation` tool. Emits structured `FailureClusterSet` object.
7. **Patcher phase.** Patcher reads `FailureClusterSet`. Generates `HardeningRecipe` (Pydantic schema with: cluster_id, root_cause, prompt_patch, tool_validation_diff, regression_test_cases). Markdown emitter writes recipe to GCS. GitLab emitter (if configured) creates MR via `gitlab.com/api/v4/mcp`.
8. **Re-attack phase.** Injector applies the prompt patch + tool validation guards to the target's invocation path. Re-runs the same 25 attacks. New pass rate emerges live in the Attack Matrix (cascade-flip animation) + Resilience Curve.
9. **Receipt.** Final card emitted to frontend: total runs, fault classes, root causes identified, MR URL, cost, time.

---

## Hardening recipe artifact format (locked)

```python
# chaoslab_agent/patcher/recipe.py
from pydantic import BaseModel, Field
from typing import Literal

class FailureCluster(BaseModel):
    cluster_id: str = Field(pattern=r"^cluster_[a-z0-9]{8}$")
    root_cause: str  # one-sentence root-cause description
    failure_count: int = Field(ge=1)
    span_ids: list[str]  # Phoenix span IDs in this cluster
    fault_classes: list[Literal["malformed_tool_output", "prompt_injection", "context_poisoning", "latency_spike"]]

class PromptPatch(BaseModel):
    section: Literal["system_prompt", "tool_description", "few_shot_example"]
    operation: Literal["insert", "replace", "append"]
    before: str | None  # for replace ops
    after: str

class ToolValidationDiff(BaseModel):
    tool_name: str
    operation: Literal["add_input_validator", "add_output_validator", "add_retry_policy", "add_timeout"]
    code_patch: str  # unified diff format

class HardeningRecipe(BaseModel):
    recipe_id: str = Field(pattern=r"^recipe_[a-z0-9]{12}$")
    target_agent_id: str
    generated_at: str  # ISO 8601
    cluster_set: list[FailureCluster]
    prompt_patches: list[PromptPatch]
    tool_validation_diffs: list[ToolValidationDiff]
    regression_test_cases: list[dict]  # Phoenix dataset format
    estimated_resilience_improvement: float = Field(ge=0.0, le=1.0)
    metadata: dict
```

This schema is canonical. Both Markdown emitter and GitLab emitter render from this object. JSON Schema export at `packages/shared-types/hardening-recipe.json` shared across services.

---

## CI requirements

See `docs/cicd.md` for the full spec. Summary: `setup-repo.sh` (called from Story-1.1) drops:

- `.github/workflows/pr-checks.yaml` (lint + tests + 400-line + type-check + coverage threshold)
- `.github/workflows/staging-deploy.yaml` (build + push to Artifact Registry + deploy to Cloud Run staging on merge to main)
- `.github/workflows/prod-promote.yaml` (manually triggered promotion of same image hash to prod)
- `.github/workflows/visual-tests.yaml` (Playwright vs deployed staging URL)

**No PR merges while any CI check is red.** Branch protection rules enforce this.

---

## Submission checklist gates

Coding agent verifies before submission:

### §14 — No mocks in hot path

- [ ] `grep -rE "(mock|fake|dummy|hardcoded|simulated)" apps/chaoslab-agent/src/` returns zero unjustified hits (test files exempt)
- [ ] Target agent uses real Gemini, real ADK tools
- [ ] Phoenix integration hits real Phoenix Cloud / self-hosted instance
- [ ] GitLab MR emission hits real `gitlab.com/api/v4/mcp` if enabled

### §13 — README shape

- [ ] `README.md` has: title, one-line pitch, demo URL (Cloud Run, NOT localhost), screenshot/GIF of cascade-flip, 3-step run-locally, license link, Apache-2.0 attribution to vendored `deepankarm/agent-chaos`
- [ ] `LICENSE` (Apache-2.0) + `NOTICE` (vendoring attribution) present
- [ ] Demo URL actually loads (not localhost)
- [ ] Multiple commits showing iteration (orchestrator handles this naturally via per-story PRs)

### §12 — UI structure

- [ ] Header on every demo route (chaoslab-web)
- [ ] Footer on landing page
- [ ] No placeholder copy ("John Doe", "lorem ipsum")
- [ ] Hover states on all interactive elements
- [ ] Loading + empty states implemented (especially during the 60-180s attack run)
- [ ] Reduced-motion accessibility (per `best-practices/04 §13`)

### CI

- [ ] `.github/workflows/*.yaml` present and green on main
- [ ] `pytest` runs real behavioral tests (≥80 test cases minimum across all 3 apps — coding agents add tests per story)
- [ ] `pnpm test` runs real behavioral tests (≥30 cases for `chaoslab-web`)
- [ ] Coverage ≥80% on changed files (per `best-practices/06 §9`)
- [ ] No file > 400 lines (`scripts/check_max_lines.py` passes)
- [ ] `ty check apps/` passes (or `mypy strict` if fallback active per ADR-001)
- [ ] `ruff check && ruff format --check` passes
- [ ] `pnpm lint` passes

### Phoenix integration

- [ ] Canonical replay traces visible in Phoenix Cloud project `chaoslab-demo`
- [ ] Attack Matrix cells correspond to real Phoenix span IDs (clickable → opens Phoenix span view)
- [ ] HardeningRecipe artifact persisted to GCS and accessible via the demo Receipt card

### Demo

- [ ] Demo URL accessible without login
- [ ] Canonical replay completes in ≤30 seconds (`/replay` route)
- [ ] Live attack run completes in ≤3 minutes (`/attack` route)
- [ ] 3-minute demo video uploaded to YouTube (public, English) — recorded Day 8
- [ ] Devpost submission form complete by 2026-06-11 12:00 PT (2hr safety margin before 2:00 PT deadline)
