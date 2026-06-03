# Best-Practices Corpus — Reading Guide

> **PURPOSE.** This folder is the **factual best-practices reference** for ChaosLab's implementation: project layout, CI/CD, code quality enforcement, frontend stack, BDD format, test strategy. Every file describes what production teams do in 2026, sourced from canonical docs and reference implementations.
>
> **NOT.** Not project-specific decisions. Not "ChaosLab should X" statements. The downstream `sahil-spec-writer` reads this corpus + the `context/` corpus and makes ChaosLab-specific decisions in `docs/`.

---

## Files

| # | File | Lines | Focus |
|---|---|--:|---|
| 01 | `01-python-project-layout.md` | 1,499 | uv + ruff + ty (Astral monoculture confirmed in 2026), agent-starter-pack canonical layout, recommended Python libraries with pinned versions, full `pyproject.toml` template |
| 02 | `02-cicd-github-actions.md` | 1,368 | 4 paste-ready workflows (PR checks, staging deploy, prod promote, visual tests), Workload Identity Federation step-by-step + top-5 failure modes, "build once promote everywhere" pattern |
| 03 | `03-code-quality-enforcement.md` | 1,403 | Custom 400-line enforcement script (ruff has no module-level line-count rule), strict ruff/ty/ESLint/Prettier configs, pre-commit hooks, conventional commits, structlog with Phoenix trace propagation |
| 04 | `04-nextjs-production.md` | 531 | Next.js 15 App Router, Tailwind 4 CSS-first, shadcn/ui, visx + Framer Motion for the Attack Matrix cascade-flip, SSE for trace streaming, Cloud Run Dockerfile |
| 05 | `05-bdd-bmad-stories.md` | 477 | Gherkin canonical format, BMad story file template, **trace-as-assertion pattern for non-deterministic LLM acceptance criteria**, sample stories, GitHub issue mapping |
| 06 | `06-test-strategy.md` | 1,285 | pytest patterns for ADK, **trace-as-assertion pattern**, ADK's built-in `AgentEvaluator` (ROUGE-1, no second LLM), LLM-as-judge cost control, Playwright + sahil-visual-loop integration |
| **Total** | | **6,563** | |

Files 04 and 05 were written directly after sub-agent retries hit Anthropic API "Overloaded" errors. They're more focused (500ish lines vs 1,300+ for the others) but cover the load-bearing patterns.

---

## Cross-cutting decisions surfaced

These are factual observations, not project decisions:

| Topic | Observation | Source |
|---|---|---|
| **Package manager** | uv has clearly won. Google's `agent-starter-pack` uses uv natively; `uv.lock` committed; entry point is `uvx agent-starter-pack create`. | 01 |
| **Type checker** | Google's agent-starter-pack canonized **`ty` (Astral)**, not mypy, in 2026. Lint chain: `ruff check && ruff format --check && ty check`. mypy is the more mature alternative. | 01, 03 |
| **400-line rule enforcement** | Ruff has NO module-level line-count rule (only per-function). Enforcement requires a custom pre-commit hook + CI bash mirror. ESLint has built-in `max-lines` for TS/JS. | 03 |
| **CI/CD highest-leverage pattern** | "Build once, promote everywhere" — build Docker image with `:${{ github.sha }}` in staging, promote that exact hash to prod. Eliminates entire class of staging-vs-prod bugs. | 02 |
| **WIF failure modes** | Top 5 ranked: missing `permissions: id-token: write`; attribute condition excludes repo; `principalSet` uses REPO not OWNER/REPO; missing `roles/iam.serviceAccountUser`; gcloud flag drift. | 02 |
| **Trace-as-assertion for LLM tests** | Don't assert on natural-language output — assert on the Phoenix span tree structure. Catches wrong tool sequencing, missing tool calls, wrong arguments, latency regressions. Deterministic up to model variability. | 05, 06 |
| **LLM-as-judge cost trap** | Running on every PR is the biggest cost trap. Reserve for nightly. Trace-as-assertion + ADK's `AgentEvaluator` (ROUGE-1) carry per-PR signal load. | 06 |
| **Phoenix wiring** | `openinference-instrumentation-google-adk` + `arize-phoenix-otel` is the single line that wires ADK traces into Phoenix in OpenInference format. | 01 |
| **`@arizeai/phoenix-mcp` is partial** | (Cross-ref to `context/03-redteam-products-deep.md` and `architecture/02-phoenix-deep-dive.md`) MCP server has read-only experiments + annotations. Need 2 custom ADK FunctionTool wraps for write ops. | 01, cross-ref |
| **Tension to resolve** | Agent #24 says use `ty` (per agent-starter-pack). Agent #26 says use `mypy strict`. Both valid; downstream picks. | 01 vs 03 |

---

## How downstream agents (spec-writer, coding agents) should use this corpus

**`sahil-spec-writer`** reads files 01-06 alongside the `context/` corpus and:
1. Picks a type-checker (`ty` per starter-pack vs `mypy` per code-quality file) — documents the choice in `docs/architecture.md`
2. Copies relevant config blocks into `docs/coding-standards.md` (ruff, ESLint, pre-commit, pytest)
3. Copies CI/CD workflow templates into `docs/cicd.md` adapted for ChaosLab's 3-service deploy
4. Uses the BMad story template from §4 of `05-bdd-bmad-stories.md` for every story in `docs/stories/`
5. Applies the trace-as-assertion pattern when writing Gherkin acceptance criteria for agent code
6. References the test pyramid from `06-test-strategy.md` when authoring `docs/architecture.md` "Testing" section

**Coding agents** reading a single story:
1. The story's `Implementation Tasks` reference files in this folder for config (e.g., "follow `best-practices/03 §2` for ruff config")
2. The 400-line check is enforced at commit + CI — every file written must respect it
3. Type-checker rules apply (whichever the spec picks)
4. BDD acceptance criteria are non-negotiable contract

---

## Cross-references

- `context/00-README.md` — domain knowledge corpus (what agents look like in the wild + competitive landscape)
- `architecture/00-synthesis.md` — exploratory architecture research (banner: NOT locked decisions)
- `brainstorm/06-idea-rankings.md` — the locked wedge (W1 ChaosLab, Arize track)
- `READING-ORDER.md` (top-level) — sequenced reading guide for any downstream agent
- `CONTEXT.md` (top-level) — master entrypoint

---

**Total folder size: 6,563 lines.** Combined with `context/` (9,642) + `architecture/` (5,800) + `brainstorm/` (4,500) + top-level (≈3,600) = **30,171 lines of research feeding the spec.**
