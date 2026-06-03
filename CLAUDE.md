# ChaosLab — Project Operating Manual

**Project:** ChaosLab — chaos engineering for AI agents (Google Cloud Rapid Agent Hackathon, Arize track). Inject 4 fault classes, watch them fail via Phoenix, harden automatically via the closed loop.

**Deadline:** 2026-06-11 14:00 PT. **Judging window:** 2026-06-22 → 2026-07-06.

> ⚠ **Deadline is NOT a barrier to quality.** AI coding gives us speed — that speed is meant to ship the right thing, not to justify mock integrations / half-built features / cut corners. Never mock the hot path to ship faster. If the right thing takes longer, do the right thing. Per Abu 2026-06-03: *"by using AI coding…a deadline is not a barrier. I don't want this to go; I've been doing mock integration and something like that."*

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
8. **Merge when CI green.** Squash + merge.
9. **Update `docs/sprint-status.yaml`** — flip story `status: PENDING` → `COMPLETE`; commit on main.

One PR per story. No parallel implementation. Eggs in one basket — your focus stays on the story you're in.

---

## Hard rules (enforced by pre-commit + CI)

- **No file >400 lines** (Python, TS, JSX, Markdown). Split before 350.
- **TDD: failing test first.** No exceptions.
- **Trace-as-assertion** for agent code — assert on Phoenix span tree structure, not natural-language output (see `best-practices/06 §5.1`).
- **No mocks in submitted hot path** (§14). Real Phoenix, real Gemini, real target.
- **Conventional commits:** `feat(scope): subject` / `fix(scope): …` / `chore(scope): …`. PR title regex-checked in CI.
- **Pin model IDs:** `gemini-3.5-flash` (JUDGE_LLM, mandatory), `gemini-3.1-pro-preview` (if used). Never `gemini-pro` / `gemini-3.1-pro`.
- **Don't import `google.adk.*` outside `chaoslab_agent.adk_types`** (quarantine module).
- **`gemini-2.0-flash` is deprecated** — never use it.

---

## Stack (locked)

- **Python 3.12** + `uv` (workspace) + `ruff` lint+format + `ty` typecheck (primary; `mypy strict` fallback if `ty` blocks)
- **TypeScript 5.x** + `pnpm` + **Next.js 16** + Tailwind 4 (`@theme` CSS-first) + shadcn/ui (New York) + visx + Framer Motion 12
- **Tests:** pytest + pytest-asyncio + respx + hypothesis (BE); vitest + RTL + `@playwright/test` (FE)
- **Agent:** `google-adk>=2.1.0,<3.0.0` (pin major — uses deprecated `SequentialAgent`/`LoopAgent`/`ParallelAgent` per ADR-012)
- **Observability:** `arize-phoenix-otel` + `arize-phoenix-client` + `openinference-instrumentation-google-adk` (Tier 1) + `-langchain` / `-crewai` / `-openai-agents` (Tier 2)
- **Deploy:** 3 Cloud Run services (`chaoslab-web`, `chaoslab-agent`, `target-agent`) via GitHub Actions @v3 + Workload Identity Federation

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
