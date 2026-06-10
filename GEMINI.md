# Phoenix Audit — Gemini CLI Project Operating Manual

**Project:** Phoenix Audit — an AI agent that audits other AI agents for safety and EU AI Act compliance (Google Cloud Rapid Agent Hackathon, Arize track). Production AI agent (customer-support bot, prior-auth bot, coding agent) gets pointed to Phoenix Audit; agent runs adversarial test battery; produces a cryptographically signed regulator-ready audit report in 90 seconds. Same closed-loop engine as the prior ChaosLab working name (renamed repo-wide 2026-06-10), reframed: from "chaos engineer's testing tool" to "compliance officer's audit machine." Day-1 user: Director of AI Governance at a 5K+ employee company.

**Deadline:** 2026-06-11 14:00 PT. **Judging window:** 2026-06-22 → 2026-07-06.

> ⚠ **Deadline is NOT a barrier to quality.** AI coding gives us speed — that speed is meant to ship the right thing, not to justify mock integrations / half-built features / cut corners. Never mock the hot path to ship faster. If the right thing takes longer, do the right thing. Per Abu 2026-06-03: _"by using AI coding…a deadline is not a barrier. I don't want this to go; I've been doing mock integration and something like that."_

---

## Read these first (in this order)

1. `docs/audit-notes.md` — the "Day-3 audit amendments" section overrides anything older. Read it before trusting other spec text.
2. `docs/PRD.md` + `docs/architecture.md` — what we're building + 12 ADRs. ADR-005 / ADR-006 / ADR-007 / ADR-011 / ADR-012 are amended; the amended versions are canonical.
3. The story file you're implementing: `docs/stories/story-<id>.md`
4. `docs/sprint-status.yaml` — canonical DAG (single source of truth for `Depends on`).

For domain depth: `research/google-cloud-rapid-agent/READING-ORDER.md`.

---

## Development workflow (TDD, one story at a time)

1. **Pick the next ready story** from `docs/sprint-status.yaml` (`status: PENDING` AND all `depends_on` are `COMPLETE`).
2. **Read the story file in full** — BDD criteria, file modification map, Notes, any `AMENDED` headers.
3. **Create a feature branch:** `git checkout -b story/<slug>` (if not already on it).
4. **Write the BDD acceptance criteria as runnable failing tests** — pytest / vitest / shell. Don't write source yet.
5. **Implement** until tests pass.
6. **Run all gates locally** before committing (commands below).
7. **Perform PR review / Verification using Gemini CLI Sub-Agents:**
   - Invoke `codebase_investigator` to review the changed files, check architectural consistency, or run test analysis.
   - Address any findings (type-design, trace structure, test coverage, max lines) to ensure zero silent failures.
8. **Commit changes** (if explicitly requested by the user, or as part of completing a story):
   - Always run `git status` first to stage only specific files.
   - Use conventional commit messages following the project's style (e.g. `feat(phoenix-audit-agent): S5.2 — F1 MalformedToolOutputFault via ADK callback`).
   - Run pre-commit checks locally via git hooks or pre-commit command.
9. **Update sprint-status** — edit `docs/sprint-status.yaml` flipping story to `COMPLETE` and commit.

**Autonomy rule:** don't ask Abu permission for each change or implementation step. Run sub-agents to verify work, address findings, and advance. **Escalate to Abu only when**: (a) a blocker appears that requires project-level judgment, (b) a fix would touch an amended ADR (005/006/007/011/012), (c) a hot-path mock would be required to ship (forbidden — re-research and find the real path), or (d) something genuinely contradicts the spec.

One story at a time. Focus entirely on the active story to guarantee depth and validation.

---

## Hard rules (enforced by pre-commit + CI)

- **No file >400 lines** in `apps/`, `packages/`, `scripts/` (extensions per `scripts/check_max_lines.py`). Split before 350. Skipped paths: `__init__.py`, `.d.ts`, `_vendored/`, generated dirs (`node_modules/`, `.next/`, `dist/`, `build/`). Exempt root dirs: `docs/`, `tests/` (spec completeness > brevity for orchestrator + coding-agent comprehension).
- **TDD: failing test first.** No exceptions.
- **Trace-as-assertion** for agent code — assert on Phoenix span tree structure, not natural-language output (see `best-practices/06 §5.1`).
- **No mocks in submitted hot path** (§14). Real Phoenix, real Gemini, real target.
- **Conventional commits:** `feat(scope): subject` / `fix(scope): …` / `chore(scope): …`.
- **Pin model IDs:** `gemini-3.5-flash` (JUDGE_LLM, mandatory), `gemini-3.1-pro-preview` (if used). Never `gemini-pro` / `gemini-3.1-pro`.
- **Don't import `google.adk.*` outside `phoenix_audit_agent.adk_types`** (quarantine module; keeps the dynamic-typing boundary controlled).
- **`gemini-2.0-flash` is deprecated** — never use it.

---

## Stack (locked)

- **Python 3.12** + `uv` (workspace) + `ruff` lint+format + `ty` typecheck (primary; `mypy strict` fallback if `ty` blocks)
- **TypeScript 5.x** + `pnpm` + **Next.js 16** + Tailwind 4 (`@theme` CSS-first) + shadcn/ui (New York) + visx + Framer Motion 12
- **Tests:** pytest + pytest-asyncio + respx + hypothesis (BE); vitest + RTL + `@playwright/test` (FE)
- **Agent:** `google-adk>=2.1.0,<3.0.0` (pin major — uses deprecated `SequentialAgent`/`LoopAgent`/`ParallelAgent` per ADR-012)
- **Observability:** `arize-phoenix-otel` + `arize-phoenix-client` + `openinference-instrumentation-google-adk` (Tier 1) + `-langchain` / `-crewai` / `-openai-agents` (Tier 2)
- **Deploy:** 3 Cloud Run services. Services `phoenix-audit-web` / `phoenix-audit-agent` / `target-agent` (renamed from chaoslab-\* 2026-06-10; GCP identities keep legacy names: SAs `chaoslab-deploy`/`chaoslab-runtime`, bucket `chaoslab-recipes` — live IAM/storage rename judged churn-without-benefit); deployed via GitHub Actions @v3 + Workload Identity Federation.

---

## Load-bearing gotchas (from audit; ignore at your peril)

- **Phoenix MCP is partial.** `experiments.run_experiment` + `spans.log_span_annotations` are NOT MCP tools. Wrap via `phoenix.client.AsyncClient()` as custom ADK `FunctionTool`. See ADR-005 + RAT-results.md.
- **`a2a-sdk` — do NOT pin explicitly.** `google-adk[a2a]>=2.1.0` resolves `a2a-sdk<0.4` transitively. Explicit pin breaks `uv sync`.
- **GitLab MR emission is HYBRID.** `python-gitlab` SDK for branches+files; `create_merge_request` via official `https://gitlab.com/api/v4/mcp` only (preserves judging credit). The official MCP does NOT expose `create_branch` / `create_or_update_file`. See ADR-011.
- **`--cpu-boost` only.** Do NOT use `--startup-cpu-boost` — that gcloud flag does not exist.
- **OpenInference attribute names:** `tool_call.function.name` (not `tool_call.name`); `openinference.span.kind` (not `instrumentation.library`).
- **Vertex Agent Engine + Phoenix:** if ever ported off Cloud Run, must call `register(set_global_tracer_provider=False, batch=False)` or traces silently vanish. We're on Cloud Run, so this is just FYI.
- **Don't vendor `deepankarm/agent-chaos`.** Attribution-only NOTICE entry — F1-F4 reimplement natively. See ADR-006.

---

## Local gate commands

```bash
# Python (run from repo root)
uv sync                                            # install
.venv/bin/pytest                                   # unit + integration (no online)
.venv/bin/pytest -m online                         # cost-incurring; skip on PR
.venv/bin/ruff check . && .venv/bin/ruff format --check .
uv run ty check apps/

# TypeScript
pnpm install
pnpm --filter phoenix-audit-web dev                     # local Next.js
pnpm --filter phoenix-audit-web test                    # vitest
pnpm --filter phoenix-audit-web test:e2e                # playwright
pnpm lint && pnpm typecheck

# Cross-language
python3 scripts/check_max_lines.py                 # 400-line guard

# Pre-commit (auto-runs on git commit; manual:)
pre-commit run --all-files
```

**Pre-commit hooks** run on every commit (configured in `.pre-commit-config.yaml`). They mirror CI: ruff, ruff-format, ty, ESLint, Prettier, gitleaks, markdownlint, conventional-commits, and the 400-line guard.

---

## Cost discipline ($100 GCP credit; ~$72 projected)

- `JUDGE_LLM=gemini-3.5-flash` is the env var. Pro is ~1.33× cost. Flash-Lite (`gemini-3.1-flash-lite`) is 8-11× cheaper — fallback if budget overruns appear (untested for our eval rubrics, default Flash).
- `@pytest.mark.online` tests cost money — run on nightly schedule, not every PR.
- Cloud Run `min-instances=1` on `phoenix-audit-web` + `phoenix-audit-agent` ONLY during judging window (Jun 22 → Jul 6). Bring to 0 outside.

---

## Memory & System Prompts

Session memory at `/Users/abu/.gemini/tmp/rapid-agents/memory/MEMORY.md`. Loaded automatically in every session. Keeps track of Abu's personal preferences, cross-session project state, and external system pointers.
