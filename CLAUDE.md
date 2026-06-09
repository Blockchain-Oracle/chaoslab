# Phoenix Audit — Project Operating Manual

**Project:** Phoenix Audit — an AI agent that audits other AI agents for safety and EU AI Act compliance (Google Cloud Rapid Agent Hackathon, Arize track). Production AI agent (customer-support bot, prior-auth bot, coding agent) gets pointed to Phoenix Audit; agent runs adversarial test battery; produces a cryptographically signed regulator-ready audit report in 90 seconds. Same closed-loop engine as the prior ChaosLab working name, reframed: from "chaos engineer's testing tool" to "compliance officer's audit machine." Day-1 user: Director of AI Governance at a 5K+ employee company.

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

1. **Pick the next ready story** from `docs/sprint-status.yaml` (`status: PENDING` AND all `depends_on` are `COMPLETE`)
2. **Read the story file in full** — BDD criteria, file modification map, Notes, any `AMENDED` headers
3. **Create a feature branch:** `git checkout -b story/<slug>`
4. **Write the BDD acceptance criteria as runnable failing tests** — pytest / vitest / shell. Don't write source yet.
5. **Implement** until tests pass.
6. **Run all gates locally** before committing (commands below).
7. **Open PR** via `gh pr create` with conventional-commit title; reference the story file.
8. **Run PR review via subagent** — invoke `pr-review-toolkit:review-pr` skill (or `sahil-pr-audit` as fresh-context fallback) against the open PR. Review surfaces silent-failure / type-design / test-coverage / comment-accuracy issues a fresh context catches that you miss.
9. **Address findings** — for each finding: either (a) amend the PR with a fix commit, or (b) document explicit rejection in a follow-up PR comment with rationale (some findings are noise; use judgment).
10. **Merge** — `gh pr merge --squash --delete-branch` once CI green (when CI exists post-S1.5) AND PR review verdict acceptable.
11. **Pull main, update sprint-status** — `git checkout main && git pull && <edit sprint-status.yaml flipping story to COMPLETE> && git commit -am "chore(spec): mark story-<id> COMPLETE" && git push`. Then start the next story.

**Autonomy rule:** don't ask Abu permission for each PR. Run the review subagent, address findings, merge, advance. **Escalate to Abu only when**: (a) the PR review surfaces a BLOCKER you can't address without project-level judgment, (b) a fix would touch an amended ADR (005/006/007/011/012), (c) a hot-path mock would be required to ship (forbidden — re-research and find the real path), or (d) something genuinely contradicts the spec.

One PR per story. No parallel implementation. Eggs in one basket — your focus stays on the story you're in.

---

## Hard rules (enforced by pre-commit + CI)

- **No file >400 lines** in `apps/`, `packages/`, `scripts/` (extensions per `scripts/check_max_lines.py`). Split before 350. Skipped paths: `__init__.py`, `.d.ts`, `_vendored/`, generated dirs (`node_modules/`, `.next/`, `dist/`, `build/`). Exempt root dirs: `docs/`, `tests/` (spec completeness > brevity for orchestrator + coding-agent comprehension).
- **TDD: failing test first.** No exceptions.
- **Trace-as-assertion** for agent code — assert on Phoenix span tree structure, not natural-language output (see `best-practices/06 §5.1`).
- **No mocks in submitted hot path** (§14). Real Phoenix, real Gemini, real target.
- **Conventional commits:** `feat(scope): subject` / `fix(scope): …` / `chore(scope): …`. PR title regex-checked in CI.
- **Pin model IDs:** `gemini-3.5-flash` (JUDGE_LLM, mandatory), `gemini-3.1-pro-preview` (if used). Never `gemini-pro` / `gemini-3.1-pro`.
- **Don't import `google.adk.*` outside `chaoslab_agent.adk_types`** (quarantine module — note: internal package directory still uses `chaoslab_agent` as codename pending S1.6 deploy refactor; product name is Phoenix Audit).
- **`gemini-2.0-flash` is deprecated** — never use it.

---

## Stack (locked)

- **Python 3.12** + `uv` (workspace) + `ruff` lint+format + `ty` typecheck (primary; `mypy strict` fallback if `ty` blocks)
- **TypeScript 5.x** + `pnpm` + **Next.js 16** + Tailwind 4 (`@theme` CSS-first) + shadcn/ui (New York) + visx + Framer Motion 12
- **Tests:** pytest + pytest-asyncio + respx + hypothesis (BE); vitest + RTL + `@playwright/test` (FE)
- **Agent:** `google-adk>=2.1.0,<3.0.0` (pin major — uses deprecated `SequentialAgent`/`LoopAgent`/`ParallelAgent` per ADR-012)
- **Observability:** `arize-phoenix-otel` + `arize-phoenix-client` + `openinference-instrumentation-google-adk` (Tier 1) + `-langchain` / `-crewai` / `-openai-agents` (Tier 2)
- **Deploy:** 3 Cloud Run services. Internal package names `chaoslab-web` / `chaoslab-agent` / `target-agent` (codenames pending S1.6 rename to `phoenix-audit-web` / `phoenix-audit-agent`); deployed via GitHub Actions @v3 + Workload Identity Federation.

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
uv run pytest                                      # unit + integration (no online)
uv run pytest -m online                            # cost-incurring; skip on PR
uv run ruff check . && uv run ruff format --check .
uv run ty check apps/

# TypeScript
pnpm install
pnpm --filter chaoslab-web dev                     # local Next.js
pnpm --filter chaoslab-web test                    # vitest
pnpm --filter chaoslab-web test:e2e                # playwright
pnpm lint && pnpm typecheck

# Cross-language
python3 scripts/check_max_lines.py                 # 400-line guard

# Pre-commit (auto-runs on git commit; manual:)
pre-commit run --all-files
```

**Pre-commit hooks** run on every commit (configured in `.pre-commit-config.yaml`). They mirror CI: ruff, ruff-format, ty, ESLint, Prettier, gitleaks, markdownlint, conventional-commits, and the 400-line guard. To bypass in genuine emergency: `git commit --no-verify` — but every PR must still pass full CI which re-runs all hooks via `pre-commit/action@v3.0.1` (once S1.5's CI workflow lands). The escape hatch buys nothing once CI is wired.

**PR checks** (S1.5) run via `.github/workflows/pr-checks.yaml`. 8 jobs must be green before merge: `detect-changes`, `python-quality` (ruff + ty), `ts-quality` (eslint + tsc), `max-lines-check`, `python-tests` (pytest + cov), `ts-tests` (vitest), `gitleaks`, `conventional-commits`. Identical gates to pre-commit — a green local pre-commit + green CI is the merge contract.

---

## When to research mid-implementation

If a spec claim doesn't match reality (and `docs/audit-notes.md` hasn't already amended it):

1. **SDK / API shape question** → Context7 first (`mcp__plugin_context7_context7__resolve-library-id` → `query-docs`). Fast, cached, authoritative for any documented library.
2. **Production pattern question** → WebSearch / WebFetch, or the `tavily` / `exa` skills.
3. **Spawn a research sub-agent ONLY** when the question is wide enough to benefit from going off in parallel while you continue implementing. Frame it: "research X, write findings to `/tmp/<note>.md`, summarize in 200 words." Never use sub-agents for parallel coding.
4. **When you learn something:** patch `docs/audit-notes.md` ("Implementation findings" section) so the next story doesn't re-hit the same wall. Update this CLAUDE.md if the finding is workflow-level.

---

## Cost discipline ($100 GCP credit; ~$72 projected)

- `JUDGE_LLM=gemini-3.5-flash` is the env var. Pro is ~1.33× cost. Flash-Lite (`gemini-3.1-flash-lite`) is 8-11× cheaper — fallback if budget overruns appear (untested for our eval rubrics, default Flash).
- `@pytest.mark.online` tests cost money — run on nightly schedule, not every PR.
- Cloud Run `min-instances=1` on `chaoslab-web` + `chaoslab-agent` ONLY during judging window (Jun 22 → Jul 6). Bring to 0 outside.

---

## Memory

Session memory at `~/.claude/projects/-Users-abu-dev-hackathon-rapid-agents/memory/`. Auto-loads via `MEMORY.md` index. Don't bloat — only persist (a) Abu's preferences, (b) cross-session project state, (c) external system pointers.
