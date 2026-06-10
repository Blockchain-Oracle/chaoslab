# Phoenix Audit — Project Operating Manual

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
- **Don't import `google.adk.*` outside `phoenix_audit_agent.adk_types`** (quarantine module; keeps the dynamic-typing boundary controlled).
- **`gemini-2.0-flash` is deprecated** — never use it.

---

## Stack (locked)

- **Python 3.12** + `uv` (workspace) + `ruff` lint+format + `ty` typecheck (primary; `mypy strict` fallback if `ty` blocks)
- **TypeScript 5.x** + `pnpm` + **Next.js 16** + Tailwind 4 (`@theme` CSS-first) + shadcn/ui (New York) + visx + Framer Motion 12
- **Tests:** pytest + pytest-asyncio + respx + hypothesis (BE); vitest (FE; Playwright e2e not yet wired — do not document gates that don't exist)
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

## Silent-failure patterns (recurring review findings — watch for these)

These shapes look correct in review but silently corrupt the regulator-facing audit. Surfaced across PRs #42, #44, #45, #66, #67, #68, #69. If you write code that looks like any of these, the silent-failure-hunter reviewer WILL find it — fix at write-time instead.

1. **Empty-string fallback masks missing data.** `span.attributes.get("input.value", "")` forwards an empty payload to the LLM, which returns `passed=True` because there's nothing to disagree with. Use a `require_attr()` helper that raises on missing/empty — never default to `""` for audit-input fields.

2. **`dict.get(key, default)` returns `None` (not the default) when the key is _present with null_.** `body.get("prompt_patches", [])` on `{"prompt_patches": null}` is `None`, not `[]`. The next `for p in None` raises `TypeError`, which escapes `asyncio.gather` and torpedoes the whole audit run. Use `body.get(key) or []`.

3. **Schema drift not enforced by CI.** A committed generated artifact (JSON Schema, OpenAPI, etc.) drifts from its source-of-truth pydantic model the moment someone edits the model and forgets to re-run the export. Add a `git diff --exit-code` CI step after regenerating — see `.github/workflows/pr-checks.yaml`'s `recipe-schema-drift` job.

4. **Audit metadata doesn't distinguish real LLM output from fallback.** A fallback patch (Gemini died → emit a generic patch) flows into the signed `HardeningRecipe.prompt_patches` indistinguishable from a real one. A regulator reading the MR can't tell pseudoknowledge from real fixes. Always add a `metadata.fallback_*` marker when a path uses a fallback.

5. **`Settings.X == "literal"` lets variants slip past the runtime guard.** `settings.JUDGE_LLM == "gemini-3.5-flash"` rejects `"gemini-3.5-flash-002"` but the `Literal["gemini-3.5-flash"]` on a Pydantic field would also reject it, producing a confusing late-stage `ValidationError`. Use `settings.JUDGE_LLM.startswith("gemini-3.5-flash")` for the runtime guard; keep the `Literal` tight.

6. **List `min_length=1` is checked on the wrapper, not the bare list.** `HardeningRecipe.cluster_set: list[FailureCluster]` silently accepts an empty/duplicated/over-max partition because the partition invariants live on `FailureClusterSet._mutually_exclusive_partition`, not on the list type. Type with `FailureClusterSet` (the wrapper) not `list[FailureCluster]`.

7. **Phoenix `async_evaluate()` returns `List[Score]`, not a single `Score`.** Calling `.label` on the result throws `AttributeError: 'list' object has no attribute 'label'`. Unwrap with `(await async_evaluate(...))[0]` AND check for empty list (rate-limit/safety-block) before indexing.

8. **`asyncio.gather(..., return_exceptions=False)` propagates the first exception** — even ones from helpers, not just the awaited tasks. A future `prompt.format` `KeyError` would kill the whole batch. Use `return_exceptions=True` + per-cluster outcome-loop fallback handling.

9. **`# type: ignore[...]` is mypy syntax; this project uses `ty`.** Use `# ty: ignore[<rule>]` (with the specific rule, never blanket). `# type: ignore` is silently inert — the error stays masked from mypy but visible to ty, which then fails CI.

10. **The "fixture regenerates before asserting" anti-pattern.** A test fixture that does `subprocess.run("export.py")` BEFORE calling assertions on the file always passes, even when the committed copy is stale. The actual drift check belongs in a CI step (#3) and/or a separate test that reads bytes-from-disk BEFORE regenerating.

---

## Local gate commands

```bash
# Python (run from repo root)
uv sync                                            # install
uv run pytest apps/phoenix-audit-agent/tests/unit apps/target-agent/tests/unit  # per-app, like CI (combined-tree root run has a known tests-package collision)
uv run pytest -m online                            # cost-incurring; skip on PR
uv run ruff check . && uv run ruff format --check .
uv run ty check apps/

# TypeScript
pnpm install
pnpm --filter phoenix-audit-web dev                     # local Next.js
pnpm --filter phoenix-audit-web test                    # vitest
pnpm lint && pnpm typecheck

# Cross-language
python3 scripts/check_max_lines.py                 # 400-line guard

# Pre-commit (auto-runs on git commit; manual:)
pre-commit run --all-files
```

**Pre-commit hooks** run on every commit (configured in `.pre-commit-config.yaml`). They mirror CI: ruff, ruff-format, ty, ESLint, Prettier, gitleaks, markdownlint, conventional-commits, and the 400-line guard. To bypass in genuine emergency: `git commit --no-verify` — but every PR must still pass full CI which re-runs all hooks via `pre-commit/action@v3.0.1` (once S1.5's CI workflow lands). The escape hatch buys nothing once CI is wired.

**PR checks** (S1.5) run via `.github/workflows/pr-checks.yaml`. 8 jobs must be green before merge: `detect-changes`, `python-quality` (ruff + ty), `ts-quality` (eslint + tsc), `max-lines-check`, `python-tests` (pytest + cov), `ts-tests` (vitest), `gitleaks`, `conventional-commits`. Identical gates to pre-commit — a green local pre-commit + green CI is the merge contract.

**GCP IAM bootstrap** (S1.4) is a MANUAL ONE-TIME step. Run via `bash infra/workload-identity-federation.sh && bash infra/secret-manager-setup.sh` after setting the env vars listed in `infra/README.md`. CI workflows in `.github/workflows/*.yaml` assume this has happened (WIF pool + service accounts + Secret Manager secrets are all live).

**Staging deploys** (S1.6) fire on every push to `main` via `.github/workflows/staging-deploy.yaml`. The "build once, promote everywhere" invariant (ADR-008) means the `:${{ github.sha }}` image tag is the unit of promotion — prod (S1.7) uses the SAME image hash via `prod-promote.yaml`. The workflow uses a matrix over 3 services (phoenix-audit-agent, target-agent, phoenix-audit-web) with `paths-filter` skipping unchanged services. WIF auth via S1.4's `chaoslab-deploy` SA; runtime SA is `chaoslab-runtime`. Blue/green: deploy with `--no-traffic --tag=candidate`, smoke-test the candidate URL, then `update-traffic --to-latest=100` on success.

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
- Cloud Run `min-instances=1` on `phoenix-audit-web` + `phoenix-audit-agent` ONLY during judging window (Jun 22 → Jul 6). Bring to 0 outside.

---

## Memory

Session memory at `~/.claude/projects/-Users-abu-dev-hackathon-rapid-agents/memory/`. Auto-loads via `MEMORY.md` index. Don't bloat — only persist (a) Abu's preferences, (b) cross-session project state, (c) external system pointers.
