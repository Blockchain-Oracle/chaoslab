# Epics — ChaosLab

**Hackathon:** Google Cloud Rapid Agent Hackathon
**Status:** DRAFT — pending Abu approval
**Total epics:** 8
**Total stories:** ~38
**Project name (CONFIRMED):** ChaosLab — see `CONTEXT.md` and `brainstorm/06-idea-rankings.md` §W1

---

## Epic overview (dependency order)

| Epic | Title | Stories | Estimate | Depends on |
|---|---|---|---|---|
| **E1** | **Repo + CI/CD foundation (FIRST per Abu)** | 7 | ~8h | None |
| **E2** | Target agent (the victim) | 4 | ~4h | E1 |
| **E3** | Cross-framework target adapter layer | 5 | ~6h | E2 |
| **E4** | ChaosLab orchestrator + Phoenix tool wrappers | 6 | ~6h | E1, E2 |
| **E5** | Fault injection (4 fault classes) | 7 | ~7h | E3, E4 |
| **E6** | Judge + clustering + hardening recipe | 6 | ~6h | E4, E5 |
| **E7** | chaoslab-web frontend | 12 | ~10h | E1 (can run parallel with E4-E6) |
| **E8** | README + Submission polish | 4 | ~3h | All other epics |

**Total estimated work:** ~50 hours. AI coding agents at 3-5× human speed → fits within the 9-day window with comfortable buffer.

---

## Epic 1 — Repo + CI/CD foundation

**Business value:** Every later story ships into a CI/CD pipeline. Without this epic locked first, every story retrofits discipline. Abu explicitly required CI/CD first.

**Dependencies:** None

**Stories:**
- S1.1 — Initialize `uv` + `pnpm` monorepo structure
- S1.2 — Configure pre-commit hooks (ruff, ty, eslint, prettier, 400-line, gitleaks, conventional-commits)
- S1.3 — Custom 400-line enforcement script (`scripts/check_max_lines.py`)
- S1.4 — Workload Identity Federation + Secret Manager bootstrap scripts (`infra/`)
- S1.5 — GitHub Actions `pr-checks.yaml` (lint + test + 400-line + type-check + gitleaks)
- S1.6 — GitHub Actions `staging-deploy.yaml` (build once, push, deploy to Cloud Run staging)
- S1.7 — GitHub Actions `prod-promote.yaml` + `visual-tests.yaml`

**Estimate:** ~8h

Story files:
- `docs/stories/story-1.1-monorepo-init.md`
- `docs/stories/story-1.2-precommit-hooks.md`
- `docs/stories/story-1.3-max-lines-script.md`
- `docs/stories/story-1.4-gcp-iam-bootstrap.md`
- `docs/stories/story-1.5-pr-checks-workflow.md`
- `docs/stories/story-1.6-staging-deploy-workflow.md`
- `docs/stories/story-1.7-prod-promote-and-visual-tests.md`

---

## Epic 2 — Target agent (the victim)

**Business value:** ChaosLab needs something to attack. The naive customer-support agent is the canonical demo target. Without it, the demo has nothing to break.

**Dependencies:** Epic 1 complete

**Stories:**
- S2.1 — Naive ADK customer-support agent: 3 tools (lookup_order, refund, escalate), weak prompt, no input validation
- S2.2 — Expose target agent via `to_a2a(agent, port=8001)` — A2A peer interface
- S2.3 — OpenInference auto-instrumentation → Phoenix Cloud trace export
- S2.4 — Target agent Cloud Run deploy (`target-agent` service)

**Estimate:** ~4h

Story files:
- `docs/stories/story-2.1-naive-target-agent.md`
- `docs/stories/story-2.2-target-a2a-exposure.md`
- `docs/stories/story-2.3-target-phoenix-instrumentation.md`
- `docs/stories/story-2.4-target-cloud-run-deploy.md`

---

## Epic 3 — Cross-framework target adapter layer

**Business value:** ChaosLab's market gap (per `context/03 §13`) is supporting agents from ANY framework, not just ADK. The adapter layer is what differentiates ChaosLab from every existing red-team product. Three tiers covering ADK, popular Python frameworks, and HTTP black-box.

**Dependencies:** Epic 2 complete

**Stories:**
- S3.1 — Adapter interface contract (`TargetAdapter` ABC + `AdapterResult` schema)
- S3.2 — Tier 1: ADK adapter (`adk_adapter.py`) — uses `RemoteA2aAgent`
- S3.3 — Tier 2: LangChain adapter (`langchain_adapter.py`) via OpenInference + custom orchestrator wrapping
- S3.4 — Tier 2: CrewAI adapter (`crewai_adapter.py`)
- S3.5 — Tier 2: OpenAI Agents SDK adapter (`openai_sdk_adapter.py`)
- S3.6 — Tier 3: HTTP black-box adapter (`http_blackbox_adapter.py`) — AgentCard discovery + behavioral fingerprinting

**Estimate:** ~6h

Story files:
- `docs/stories/story-3.1-adapter-interface.md`
- `docs/stories/story-3.2-adk-adapter.md`
- `docs/stories/story-3.3-langchain-adapter.md`
- `docs/stories/story-3.4-crewai-adapter.md`
- `docs/stories/story-3.5-openai-sdk-adapter.md`
- `docs/stories/story-3.6-http-blackbox-adapter.md`

---

## Epic 4 — ChaosLab orchestrator + Phoenix tool wrappers

**Business value:** The brain of ChaosLab. Without the orchestrator, the sub-agents have no spine; without the Phoenix wrappers, the closed loop doesn't close (Phoenix MCP is read-only for experiments + annotations per ADR-005).

**Dependencies:** Epic 1 + Epic 2 complete

**Stories:**
- S4.1 — `chaoslab-agent` FastAPI/ADK entry (`main.py` with `/run`, `/stream`, `/health`, `/agents/{id}` endpoints)
- S4.2 — SequentialAgent orchestrator scaffolding (Injector → Judge → Patcher composition)
- S4.3 — Custom Phoenix `run_experiment` FunctionTool (wraps Python SDK per ADR-005)
- S4.4 — Custom Phoenix `write_span_annotation` FunctionTool (wraps Python SDK)
- S4.5 — `chaoslab_agent.observability` + `chaoslab_agent.adk_types` (structlog + Phoenix trace ID + ADK quarantine)
- S4.6 — `chaoslab-agent` Cloud Run deploy (build, push, deploy with secrets)

**Estimate:** ~6h

Story files:
- `docs/stories/story-4.1-agent-entrypoint.md`
- `docs/stories/story-4.2-sequential-orchestrator.md`
- `docs/stories/story-4.3-phoenix-run-experiment-tool.md`
- `docs/stories/story-4.4-phoenix-write-annotation-tool.md`
- `docs/stories/story-4.5-observability-and-types.md`
- `docs/stories/story-4.6-chaoslab-agent-deploy.md`

---

## Epic 5 — Fault injection (the 4 fault classes)

**Business value:** The active "doing" of ChaosLab. Each fault class is a distinct attack vector. The 4 MVP fault classes (F1-F4) cover 4 different injection mechanisms AND 4 different layers, giving the demo diverse failure modes.

**Dependencies:** Epic 3 + Epic 4 complete

**Stories:**
- S5.1 — Vendor `deepankarm/agent-chaos` (Apache-2.0) fault primitives + NOTICE attribution
- S5.2 — F1: `MalformedToolOutputFault` (decorator pattern, before_tool_callback)
- S5.3 — F2: `PromptInjectionFault` (LiteLlm proxy, before_model_callback)
- S5.4 — F3: `ContextPoisoningFault` (retriever monkey-patch + context attribute mutation)
- S5.5 — F4: `LatencySpikeFault` (network shim — asyncio sleep + httpx timeout)
- S5.6 — Pre-flight baseline check (Chaos Toolkit steady-state-hypothesis pattern — abort if baseline <80%)
- S5.7 — Injector sub-agent wiring (selects fault, configures adapter, captures trace)

**Estimate:** ~7h

Story files:
- `docs/stories/story-5.1-vendor-agent-chaos.md`
- `docs/stories/story-5.2-fault-malformed-tool.md`
- `docs/stories/story-5.3-fault-prompt-injection.md`
- `docs/stories/story-5.4-fault-context-poisoning.md`
- `docs/stories/story-5.5-fault-latency-spike.md`
- `docs/stories/story-5.6-preflight-baseline.md`
- `docs/stories/story-5.7-injector-sub-agent.md`

---

## Epic 6 — Judge + clustering + hardening recipe

**Business value:** The "intelligence" of ChaosLab. Takes raw failures and produces actionable hardening recipes. Without this epic, ChaosLab is just a fault injector — every red-team tool has that. The closed-loop hardening is the moat.

**Dependencies:** Epic 4 + Epic 5 complete

**Stories:**
- S6.1 — Judge sub-agent + LLM-as-judge rubrics (Phoenix `tool_invocation` + `hallucination` + 2 custom for F2/F4)
- S6.2 — Failure clustering via Gemini 3.5 Flash as clusterer + annotation writeback
- S6.3 — `HardeningRecipe` pydantic schema + JSON Schema export to `packages/shared-types/`
- S6.4 — Patcher sub-agent (reads clusters, generates recipe object)
- S6.5 — Markdown emitter (writes recipe to GCS, exposes signed URL)
- S6.6 — GitLab MR emitter (via `gitlab.com/api/v4/mcp`) — emits real MR with regression test cases

**Estimate:** ~6h

Story files:
- `docs/stories/story-6.1-judge-rubrics.md`
- `docs/stories/story-6.2-failure-clustering.md`
- `docs/stories/story-6.3-recipe-schema.md`
- `docs/stories/story-6.4-patcher-sub-agent.md`
- `docs/stories/story-6.5-markdown-emitter.md`
- `docs/stories/story-6.6-gitlab-mr-emitter.md`

---

## Epic 7 — chaoslab-web frontend

**Business value:** The demo IS the judging surface. Without a polished frontend, the entire ChaosLab story is invisible to judges. The hero visual (Attack Matrix + Resilience Curve cascade-flip) is the 25% Design score lever.

**Dependencies:** Epic 1 (CI/CD). Can run in PARALLEL with Epics 4, 5, 6. (Frontend stubs the agent backend until real backend lands.)

**Stories:**
- S7.1 — Next.js 16 scaffold + Tailwind 4 CSS-first + shadcn/ui init
- S7.2 — Design tokens (`@theme` in globals.css) — 5-agent color palette, OKLCH
- S7.3 — `lib/env.ts` zod-validated env + Cloud Run Dockerfile
- S7.4 — Run store (Zustand) + `useTraceStream` SSE hook
- S7.5 — `<AttackMatrix>` component (5×5 grid + Framer Motion stagger cascade-flip)
- S7.6 — `<ResilienceCurve>` component (visx LinePath + PATCH marker)
- S7.7 — `<AgentPipeline>` component (multi-agent A2A visualization)
- S7.8 — `<ReceiptCard>` component (final summary card)
- S7.9 — `/` landing page + header + footer
- S7.10 — `/replay` canonical pre-recorded run route + seed-data fetcher
- S7.11 — `/attack` live attack route with SSE + cascade-flip orchestration
- S7.12 — `sahil-visual-loop` integration (anchor screenshots + Playwright + vision reviewer)

**Estimate:** ~10h

Story files:
- `docs/stories/story-7.1-nextjs-scaffold.md`
- `docs/stories/story-7.2-design-tokens.md`
- `docs/stories/story-7.3-env-and-dockerfile.md`
- `docs/stories/story-7.4-run-store-and-sse.md`
- `docs/stories/story-7.5-attack-matrix.md`
- `docs/stories/story-7.6-resilience-curve.md`
- `docs/stories/story-7.7-agent-pipeline.md`
- `docs/stories/story-7.8-receipt-card.md`
- `docs/stories/story-7.9-landing-page.md`
- `docs/stories/story-7.10-replay-route.md`
- `docs/stories/story-7.11-attack-route.md`
- `docs/stories/story-7.12-visual-loop-integration.md`

---

## Epic 8 — README + Submission polish

**Business value:** Judges read README before they demo. README is a direct 25% Tech Implementation + 25% Design scoring lever. Submission polish prevents Stage-1 automated disqualification.

**Dependencies:** All other epics complete

**Stories:**
- S8.1 — README + LICENSE (Apache-2.0) + NOTICE (vendoring attribution)
- S8.2 — Demo seed script (`scripts/seed_demo_data.py`) — populates Phoenix Cloud canonical replay project
- S8.3 — Mermaid architecture diagram + Open Graph image generation
- S8.4 — Final §14/§13/§12 audit + Devpost submission form completion checklist

**Estimate:** ~3h

Story files:
- `docs/stories/story-8.1-readme-license-notice.md`
- `docs/stories/story-8.2-demo-seed-script.md`
- `docs/stories/story-8.3-arch-diagram-og-image.md`
- `docs/stories/story-8.4-submission-audit.md`

---

## Implementation order (for `sahil-hackathon-orchestrator`)

The orchestrator dispatches stories per the dependency DAG. Initial dispatch queue:

```yaml
# After Epic 1 lands (sequential within E1 because each depends on prev)
dispatch_queue:
  - story-1.1-monorepo-init          # E1 — no deps, FIRST
  - story-1.2-precommit-hooks        # E1 — depends on 1.1
  - story-1.3-max-lines-script       # E1 — depends on 1.1 (parallel with 1.2 ok)
  - story-1.4-gcp-iam-bootstrap      # E1 — depends on 1.1 (parallel ok)
  - story-1.5-pr-checks-workflow     # E1 — depends on 1.2 + 1.3
  - story-1.6-staging-deploy-workflow # E1 — depends on 1.4 + 1.5
  - story-1.7-prod-promote-and-visual-tests # E1 — depends on 1.6

# After E1 done: E2 + E7 parallel-safe
  - story-2.1-naive-target-agent     # E2 — depends on 1.7
  - story-7.1-nextjs-scaffold        # E7 — depends on 1.7 (parallel with E2)
  - story-7.2-design-tokens          # E7 — depends on 7.1 (parallel with E2)
  - story-7.3-env-and-dockerfile     # E7 — depends on 7.1 (parallel)

# E2 continues; E7 continues; E4 can start after S2.1
  - story-2.2-target-a2a-exposure
  - story-4.1-agent-entrypoint       # E4 — depends on 2.1
  - story-4.5-observability-and-types # E4 — depends on 4.1
  - story-7.4-run-store-and-sse      # E7
  - story-7.5-attack-matrix          # E7 (parallel with E4)
  - story-7.6-resilience-curve       # E7 (parallel)
  - story-7.7-agent-pipeline         # E7 (parallel)
  - story-7.8-receipt-card           # E7 (parallel)

# E3 + E4 continue; E5 starts after both done
  - story-2.3-target-phoenix-instrumentation
  - story-2.4-target-cloud-run-deploy
  - story-3.1-adapter-interface
  - story-3.2-adk-adapter
  - story-4.2-sequential-orchestrator
  - story-4.3-phoenix-run-experiment-tool
  - story-4.4-phoenix-write-annotation-tool
  - story-4.6-chaoslab-agent-deploy
  - story-3.3-langchain-adapter
  - story-3.4-crewai-adapter
  - story-3.5-openai-sdk-adapter
  - story-3.6-http-blackbox-adapter
  - story-7.9-landing-page
  - story-7.10-replay-route
  - story-7.11-attack-route
  - story-7.12-visual-loop-integration

# E5 fires after E3+E4
  - story-5.1-vendor-agent-chaos
  - story-5.2-fault-malformed-tool      # parallel within E5
  - story-5.3-fault-prompt-injection
  - story-5.4-fault-context-poisoning
  - story-5.5-fault-latency-spike
  - story-5.6-preflight-baseline
  - story-5.7-injector-sub-agent

# E6 fires after E5
  - story-6.1-judge-rubrics
  - story-6.2-failure-clustering
  - story-6.3-recipe-schema
  - story-6.4-patcher-sub-agent
  - story-6.5-markdown-emitter
  - story-6.6-gitlab-mr-emitter

# E8 fires last
  - story-8.1-readme-license-notice
  - story-8.2-demo-seed-script
  - story-8.3-arch-diagram-og-image
  - story-8.4-submission-audit
```

---

## Story sizing audit

Per `best-practices/05 §5` — every story ≤2h. Stories that risk overflow:

- **S3.6 (HTTP black-box adapter):** ambitious. Includes AgentCard discovery + behavioral fingerprinting + inter-token timing. **Mitigation:** ship discovery + AgentCard parsing in S3.6; behavioral fingerprinting is a tagged sub-task that can be cut without breaking the demo (the demo uses Tier 1 ADK target).
- **S6.2 (failure clustering):** clustering + annotation writeback + cluster-set schema. **Mitigation:** if the writer agent needs more than 2h estimate, split into S6.2a (cluster generation) + S6.2b (annotation writeback).
- **S7.11 (attack route):** orchestrates the full SSE stream + cascade-flip orchestration. **Mitigation:** S7.5 + S7.6 deliver the components in isolation; S7.11 only wires them.

If a coding agent reports >2h actual on any story, the orchestrator's next action is to split, not to grind.

---

## Confirmed project name

Per `sahil-spec-writer` Step 0 (mandatory): **PROJECT_NAME = "ChaosLab"**

- Source 1: `research/google-cloud-rapid-agent/brainstorm/06-idea-rankings.md` §W1 — "W1: ChaosLab for Agents"
- Source 2: `research/google-cloud-rapid-agent/brainstorm/07-novelty-gate.md` — locked recommendation: "Build W1 (ChaosLab for Agents). Submit under the Arize track."
- Source 3: `research/google-cloud-rapid-agent/CONTEXT.md` §2 — "Primary recommendation: 🟢 Arize" with "W1: ChaosLab for Agents" as the locked wedge

Formal name: "ChaosLab for Agents" (full). Short name: "ChaosLab" (used in URLs, container names, file paths, branding).

No mismatch with memory or prior session. **Verified.**
