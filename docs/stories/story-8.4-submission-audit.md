# Story — Submission audit script + pre-submit make target

**ID:** story-8.4-submission-audit
**Epic:** Epic 8 — README + Submission polish
**Depends on:** story-8.1-readme-license-notice + story-8.2-demo-seed-script + story-8.3-arch-diagram-og-image (audits artifacts those stories produce); transitively depends on all other epics being complete since the audit walks the full repo
**Estimate:** ~2h
**Status:** PENDING

**Tags:** `[docs, p0, submission]`

---

## User story

**As a** the Day-8 Abu running the final pre-submission checklist 2 hours before the 2026-06-11 2:00 PT deadline, AND as the Stage-1 Devpost automated AI-driven repo scanner (per `research/01-prizes-tracks.md` §"Stage 1") that ingests the public repo,
**I want to** run one command (`make submit-audit`) that mechanically asserts every §14, §13, §12, and CI-gate item from `docs/architecture.md` §"Submission checklist gates" — no mocks in hot paths, README shape correct, LICENSE + NOTICE present, demo URL reachable, no file >400 lines, lint clean, type-check clean, ≥80 backend tests, ≥30 frontend tests — and prints a categorized pass/fail report,
**So that** I never submit a repo that fails Stage-1 viability for a fixable mechanical reason, and a single red line in the audit output blocks the Devpost form submission until I fix it

---

## File modification map

Exact files the coding agent creates or modifies for this story:

- `scripts/submission_audit.py` — NEW — Python script (≤400 lines) implementing all §14/§13/§12 + CI + Phoenix + demo gates from `docs/architecture.md` §"Submission checklist gates". Architecture: each gate is a method on a `SubmissionAuditor` class returning a `GateResult` Pydantic model `{ id: str, category: Literal["§14","§13","§12","ci","phoenix","demo"], name: str, status: Literal["pass","fail","warn","skip"], detail: str, command: str | None }`. The `main()` orchestrates: runs each gate, collects results, prints a categorized table grouped by category, exit code = 0 if all `pass`/`warn`/`skip`, exit code = 1 if any `fail`. CLI: `python scripts/submission_audit.py [--strict] [--skip-online] [--category §14|§13|§12|ci|phoenix|demo] [--json]`. `--strict` upgrades `warn` to `fail`. `--skip-online` skips demo-URL curl + Phoenix-Cloud assertions (used in offline CI). `--json` emits machine-readable output for the orchestrator. Uses `typer`, `structlog`, `httpx` (for demo URL check), `subprocess.run` (for shelling out to ruff/ty/pnpm/pytest commands). Gates implemented:
  - **§14.1** `no_mocks_in_hot_path` — `grep -rE "(mock|fake|dummy|hardcoded|simulated)" apps/chaoslab-agent/src/ apps/target-agent/src/` excluding `tests/`, `_vendored/`, and lines containing `# §14 carve-out` comment. Zero hits = pass.
  - **§14.2** `target_uses_real_gemini` — `grep -rE "litellm|LiteLlm" apps/target-agent/src/` returns ≥1 hit AND `grep "gemini" apps/target-agent/src/`/`apps/chaoslab-agent/src/` returns ≥1 hit (real model name configured).
  - **§14.3** `phoenix_integration_real` — `grep -rE "phoenix.client|arize_phoenix" apps/chaoslab-agent/src/` returns ≥3 hits AND no `MOCK_PHOENIX` / `FAKE_PHOENIX` constants present.
  - **§14.4** `gitlab_mcp_real` — `grep -rE "gitlab.com/api/v4/mcp" apps/chaoslab-agent/src/patcher/` returns ≥1 hit.
  - **§13.1** `readme_shape` — README has all 6 sections in order (project name, demo URL, hero image, run-locally, cross-framework matrix, license). Uses regex set from story-8.1's BDD.
  - **§13.2** `license_apache_2_0` — `LICENSE` exists, first line contains "Apache License", ≥200 lines.
  - **§13.3** `notice_vendoring` — `NOTICE` exists, contains "deepankarm/agent-chaos", "Phoenix", "GitLab" attributions.
  - **§13.4** `demo_url_reachable` — `httpx.get(<demo URL extracted from README>, timeout=10)` returns status_code 200. Demo URL extracted via regex from `## Demo` section. Skipped under `--skip-online`.
  - **§13.5** `multiple_commits` — `git log --oneline | wc -l` ≥ 20 (iteration visible per §13).
  - **§12.1** `ui_has_header_footer` — `grep -rE "<Header" apps/chaoslab-web/app/` ≥ 1 AND `grep -rE "<Footer" apps/chaoslab-web/app/` ≥ 1 (story-7.9 wires these).
  - **§12.2** `no_placeholder_copy` — `grep -riE "(lorem ipsum|john doe|placeholder text)" apps/chaoslab-web/app/` returns zero hits.
  - **§12.3** `og_hero_exists` — `apps/chaoslab-web/public/og-hero.png` exists with exact 1200×630 dimensions (verified via `Pillow` or `file` command parsing).
  - **§12.4** `mermaid_in_readme` — README contains a ` ```mermaid ` block.
  - **ci.1** `no_files_over_400` — `python scripts/check_max_lines.py --strict` exits 0.
  - **ci.2** `ruff_clean` — `uv run ruff check apps/` exits 0.
  - **ci.3** `ty_clean` — `uv run ty check apps/chaoslab-agent apps/target-agent` exits 0 (with fallback to `mypy --strict` per ADR-001 if `ty` blocks).
  - **ci.4** `eslint_clean` — `pnpm --filter chaoslab-web lint` exits 0.
  - **ci.5** `pytest_count` — `uv run pytest apps/chaoslab-agent/tests apps/target-agent/tests --collect-only -q | grep -c "::test_"` returns ≥80.
  - **ci.6** `vitest_count` — `pnpm --filter chaoslab-web exec vitest --run --reporter=verbose 2>&1 | grep -c "✓"` returns ≥30 (or use `vitest list --json` for a cleaner count).
  - **ci.7** `coverage_threshold` — `uv run pytest --cov --cov-fail-under=80 apps/chaoslab-agent/tests` exits 0 (per `docs/coding-standards.md` `fail_under = 80`).
  - **ci.8** `no_banned_runtime_deps` — `grep -rE "(anthropic|openai|claude|cursor|langchain|langgraph|llamaindex)" apps/*/pyproject.toml apps/*/package.json` returns no hits, EXCEPT `langchain` / `crewai` / `openai` are allowed in optional `[project.optional-dependencies.tier2-targets]` (the Tier 2 adapter dependencies per ADR-002 — flagged as `warn`, not `fail`, with a §14-carve-out comment lookup).
  - **phoenix.1** `replay_project_exists` — if `--skip-online` not set, hits `https://app.phoenix.arize.com/v1/projects/chaoslab-replay` with `PHOENIX_API_KEY` and asserts 200. Else skip.
  - **demo.1** `demo_url_loads_replay_in_30s` — if not skipping, hits `<demo URL>/replay` and asserts response time <30s.
  - Each gate logs its `command` field — the exact shell command it ran, so a `fail` output lets Abu rerun the check by hand.
- `scripts/tests/test_submission_audit.py` — NEW — pytest tests (≤300 lines, ≥15 tests, one per gate category at minimum) using a fixture that creates a temporary fake repo with controllable content (README with/without each section, LICENSE present/absent, etc.) and asserts each gate returns the expected pass/fail status. Uses `respx` to mock demo URL + Phoenix endpoints. Includes one end-to-end test that runs `submission_audit.py` against the REAL current repo state and expects exit 0 (this is the canary — if the real repo doesn't pass its own audit, the test fails loudly).
- `Makefile` — UPDATE — adds `submit-audit` target wrapping `uv run python scripts/submission_audit.py --strict`. Also adds `submit-audit-offline` target that passes `--skip-online`. Two-line addition.
- `.github/workflows/pr-checks.yaml` — UPDATE — adds a `submission-audit-offline` job that runs `make submit-audit-offline` on PRs into `main`. Non-blocking (continue-on-error: true) until close to Day 8, then flipped to blocking. ~10 line addition.
- `docs/architecture.md` — UPDATE — adds a one-line cross-reference at the end of §"Submission checklist gates" pointing to `scripts/submission_audit.py` as the canonical mechanical implementation of this section. ≤3 line diff.

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given the audit script + tests exist
When `test -f scripts/submission_audit.py && test -f scripts/tests/test_submission_audit.py` runs
Then exit 0

Given the script exists
When `uv run python scripts/submission_audit.py --help` runs
Then exit 0
And output contains "--strict"
And output contains "--skip-online"
And output contains "--category"

Given a clean repo with all epics complete (E1–E7 PRs merged, E8.1+8.2+8.3 done)
When `uv run python scripts/submission_audit.py --strict --skip-online` runs (the gate from the story brief, with offline flag for CI)
Then exit code is 0
And stdout contains "[PASS] §14: no mocks in hot path"
And stdout contains "[PASS] §13: README shape"
And stdout contains "[PASS] §12: UI structure"
And stdout contains "[PASS] ci: ≥80 pytest tests"
And stdout contains "[PASS] ci: ≥30 vitest tests"
And stdout contains "[PASS] ci: no files >400 lines"

Given the repo is in a deliberately broken state (test fixture: a stub README missing the demo section)
When `uv run python scripts/submission_audit.py --strict --skip-online` runs against the fixture
Then exit code is 1
And stdout contains "[FAIL] §13: README shape"

Given a fixture repo missing LICENSE
When the audit runs
Then exit 1
And stdout contains "[FAIL] §13: LICENSE"

Given a fixture repo with a 401-line source file
When the audit runs
Then exit 1
And stdout contains "[FAIL] ci: no files >400 lines"

Given a fixture repo with "mock_phoenix_client" in apps/chaoslab-agent/src/main.py
When the audit runs (without --strict, defaults to warn for some, fail for §14)
Then exit 1
And stdout contains "[FAIL] §14: no mocks in hot path"
And stdout contains the matching file path

Given the pytest test file
When `uv run pytest scripts/tests/test_submission_audit.py -v` runs
Then exit code is 0
And output reports ≥ 15 passing tests
And one test named `test_audit_passes_on_real_repo` is among them

Given the Makefile was updated
When `grep -E "^submit-audit:" Makefile && grep -E "^submit-audit-offline:" Makefile` runs
Then exit 0

Given the audit script
When `python scripts/submission_audit.py --json --skip-online` runs
Then exit code is 0
And stdout is valid JSON (parseable by `jq .`)
And the JSON contains a top-level "gates" array with ≥20 entries

Given the script file
When `wc -l scripts/submission_audit.py` runs
Then output ≤ 400 (ADR-010 compliance)

Given the audit script's no_mocks gate
When called with the §14 carve-out path containing "# §14 carve-out" comment
Then the line is excluded from the mock detection (legitimate test scaffolding allowed)
```

---

## Shell verification

The coding agent runs this to confirm the story is done before opening a PR:

```bash
set -e
cd /Users/abu/dev/hackathon/rapid-agents

# Files exist
test -f scripts/submission_audit.py
test -f scripts/tests/test_submission_audit.py

# CLI surface
uv run python scripts/submission_audit.py --help | grep -q "strict"
uv run python scripts/submission_audit.py --help | grep -q "skip-online"
uv run python scripts/submission_audit.py --help | grep -q "category"

# Unit tests pass (≥15 tests)
uv run pytest scripts/tests/test_submission_audit.py -v
[ "$(uv run pytest scripts/tests/test_submission_audit.py --collect-only -q | grep -c '::test_')" -ge 15 ]

# Real-repo end-to-end audit (the gate from the story brief)
uv run python scripts/submission_audit.py --strict --skip-online | tee /tmp/audit.txt
grep -q "\[PASS\] §14" /tmp/audit.txt
grep -q "\[PASS\] §13" /tmp/audit.txt
grep -q "\[PASS\] §12" /tmp/audit.txt
grep -q "\[PASS\] ci" /tmp/audit.txt

# JSON output is parseable
uv run python scripts/submission_audit.py --json --skip-online | jq '.gates | length' | awk '$1 < 20 { exit 1 }'

# Makefile targets
grep -E "^submit-audit:" Makefile
grep -E "^submit-audit-offline:" Makefile
make -n submit-audit | grep -q "submission_audit.py"

# CI workflow update
grep -E "submission-audit-offline" .github/workflows/pr-checks.yaml

# Architecture cross-reference
grep -E "scripts/submission_audit\.py" docs/architecture.md

# Line count
[ "$(wc -l < scripts/submission_audit.py)" -le 400 ]
[ "$(wc -l < scripts/tests/test_submission_audit.py)" -le 400 ]
python3 scripts/check_max_lines.py --strict

# Final canary: audit passes on itself
make submit-audit-offline

echo "story-8.4 verification: PASS"
```

---

## Notes for coding agent

- This script is the §14/§13/§12 gate from `docs/architecture.md` made executable. Read that section verbatim before writing — every gate in this story maps 1:1 onto a checklist item there.
- The §14 mock-scan is the highest-risk Stage-1 disqualification per `research/01-prizes-tracks.md` §"Stage 1": "Anything that smells like a banned AI dependency in `package.json`, `requirements.txt`, etc., is the highest-confidence Stage-1 fail risk." Make the `no_banned_runtime_deps` gate exhaustive — check `pyproject.toml`, `package.json`, `pnpm-lock.yaml`, `uv.lock` for `anthropic`, `claude-`, `cursor`, `openai` (Tier 2 carve-out only), `langchain` (Tier 2 carve-out only).
- The Tier 2 adapter carve-out for `langchain` / `crewai` / `openai` is real per ADR-002 — these are legitimate target-instrumentation deps, not runtime LLM deps. Implement the carve-out via a comment marker (`# §14 carve-out: tier-2 target adapter`) on the import line in the adapter file, AND/OR check that the dep lives in `[project.optional-dependencies.tier2-targets]` rather than `[project.dependencies]`. The audit script must distinguish these correctly OR the script fails on legitimate code.
- The `no_mocks_in_hot_path` gate uses `git ls-files apps/chaoslab-agent/src` to enumerate tracked files (avoids scanning `_vendored/` or `.venv/`). The grep pattern `mock|fake|dummy|hardcoded|simulated` is case-insensitive AND excludes lines matching `# §14 carve-out` comment AND excludes `*/tests/*` and `*/_vendored/*` paths.
- `ty` is alpha per ADR-001; if it crashes or false-positives, the audit script catches the exit-2 case and falls back to running `mypy --strict` with a `[WARN]` (not `[FAIL]`) — documented behavior. CI logs which type-checker actually ran.
- The pytest count gate (`≥80`) is across BOTH `chaoslab-agent/tests/` AND `target-agent/tests/` — that's what the original architecture spec said. The vitest count gate (`≥30`) is `chaoslab-web/tests/` only.
- The demo URL gate uses `httpx.get` with timeout=10, follow_redirects=True. If the Cloud Run service is cold, it can take 15-20 seconds on first hit — set `min-instances=1` for the judging window per ADR-003 to mitigate. The audit retries once on first timeout before failing.
- `--skip-online` is mandatory for CI runs (`pr-checks.yaml`) because GitHub Actions doesn't have `PHOENIX_API_KEY` or the live demo URL in early dev. The `make submit-audit` (no flag) is what Abu runs locally on Day 8 against the real deployed demo.
- The Phoenix project check is via the Phoenix REST API: `GET https://app.phoenix.arize.com/v1/projects?name=chaoslab-replay` with the Bearer token. Returns 200 + a non-empty project list if seeded. Confirmed in `architecture/02-phoenix-deep-dive.md`.
- The JSON output mode (`--json`) is consumed by `sahil-hackathon-orchestrator`'s final gate. Schema is a Pydantic model — export the JSON Schema to `packages/shared-types/audit-report.json` if it helps future-Abu, but not required for this story.
- Banned-dep grep is the most likely false-positive. Use `awk` to parse `pyproject.toml` `[project.dependencies]` block specifically rather than naive grep across the whole file (which catches comments + URLs + dev deps).
- This story DEPENDS ON 8.1 + 8.2 + 8.3 — the audit checks artifacts those stories produce (`README.md` shape, `og-hero.png` dimensions, `chaoslab-replay` Phoenix project, Mermaid block). If any of those stories haven't landed, the audit fails — which is the correct behavior. The orchestrator dispatches 8.1/8.2/8.3 in parallel (they don't depend on each other), then 8.4 last.
- Edge case: if `git log --oneline | wc -l` returns <20 (e.g., a fresh squash-merge wiped history), flag as `[WARN]`, not `[FAIL]` — Devpost's "multiple commits" check is informal per §13 wording. The orchestrator's normal per-story PR pattern lands ~38 commits naturally, so this gate is informational.
- DO NOT use `subprocess.run(shell=True)` — use list-form `subprocess.run(["uv", "run", "ruff", "check", "apps/"])` with `check=False` to capture exit codes. Shell=True is a `ruff S603` hit.
