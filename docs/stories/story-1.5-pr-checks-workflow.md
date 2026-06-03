# Story — GitHub Actions pr-checks.yaml workflow

**ID:** story-1.5-pr-checks-workflow
**Epic:** Epic 1 — Repo + CI/CD foundation
**Depends on:** story-1.2-precommit-hooks, story-1.3-max-lines-script
**Estimate:** ~1.5h
**Status:** PENDING

---

## User story

**As a** coding agent opening a PR for any later story
**I want to** have a GitHub Actions workflow that runs paths-filter → python-quality (ruff + ty) → ts-quality (eslint + tsc) → max-lines-check → python-tests (pytest+cov) → ts-tests (vitest+cov) → gitleaks → conventional-commits on every PR
**So that** no PR merges with broken lint, type errors, oversized files, or leaked secrets — and every gate is identical between my laptop (pre-commit from story-1.2) and the cloud

---

## File modification map

Exact files the coding agent creates or modifies for this story:

- `.github/workflows/pr-checks.yaml` — NEW — full workflow per `docs/cicd.md` §`pr-checks.yaml`. Jobs (in this order, with `needs:` dependencies):
  1. `detect-changes` — `dorny/paths-filter@v3`; outputs `python`, `ts`, `infra`, `shared`
  2. `python-quality` — `needs: detect-changes`; `if: needs.detect-changes.outputs.python == 'true' || ...shared`; uv setup, `uv sync --frozen --all-extras`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run ty check apps/chaoslab-agent apps/target-agent`; conditional mypy fallback gated on `env.TY_FALLBACK == '1'`
  3. `ts-quality` — `needs: detect-changes`; fires on ts/shared changes; `pnpm/action-setup@v4`, `actions/setup-node@v4` with pnpm cache, `pnpm install --frozen-lockfile`, `pnpm lint`, `pnpm format --check`, `pnpm typecheck`
  4. `max-lines-check` — always runs; checks out, sets up Python 3.12, `python3 scripts/check_max_lines.py --strict`
  5. `python-tests` — `needs: python-quality`; runs `uv run pytest apps/chaoslab-agent/tests/unit apps/target-agent/tests/unit -v --cov --cov-fail-under=80 -m "not online"`; allowed to no-op if dirs don't exist yet (early stories)
  6. `ts-tests` — `needs: ts-quality`; runs `pnpm test:unit --coverage`; allowed to no-op until story-7.1 lands real Vitest config
  7. `gitleaks` — always runs; `gitleaks/gitleaks-action@v2`
  8. `conventional-commits` — `if: github.event_name == 'pull_request'`; uses `webiny/action-conventional-commits@v1.3.0` (or `amannn/action-semantic-pull-request@v5` — see Notes)
- `.github/workflows/.gitkeep` — DELETE if it exists; otherwise no-op
- `apps/chaoslab-agent/tests/.gitkeep` — NEW — placeholder so pytest doesn't error on missing dir
- `apps/chaoslab-agent/tests/unit/.gitkeep` — NEW — placeholder
- `apps/target-agent/tests/.gitkeep` — NEW — placeholder
- `apps/target-agent/tests/unit/.gitkeep` — NEW — placeholder
- `apps/chaoslab-agent/tests/unit/test_smoke.py` — NEW — single placeholder test: `def test_smoke(): assert True` (so pytest has ≥1 test to run and coverage threshold doesn't immediately fail; real tests land in epics 2-6)
- `apps/target-agent/tests/unit/test_smoke.py` — NEW — same single placeholder test
- `apps/chaoslab-web/vitest.config.ts` — NEW — minimal vitest config: `{ test: { environment: 'jsdom' } }` (so `pnpm test:unit` doesn't error; real tests land in epic 7)
- `apps/chaoslab-web/src/__tests__/smoke.test.ts` — NEW — single placeholder test: `import { test, expect } from 'vitest'; test('smoke', () => expect(true).toBe(true))`
- `apps/chaoslab-web/package.json` — UPDATE — add scripts: `"lint": "echo ok"`, `"format": "echo ok"`, `"typecheck": "echo ok"`, `"test:unit": "echo no tests yet"` placeholders that ALL exit 0 (real configs land in story-7.1; these scripts let CI go green without short-circuiting the wiring)
- `package.json` — UPDATE — root-level workspace `scripts.lint`, `scripts.format`, `scripts.typecheck`, `scripts.test:unit` — delegate via `pnpm -r` so CI can call from repo root
- `.gitleaks.toml` — UPDATE if needed — confirm allowlist works for the existing docs corpus (no false positives on `research/**`)
- `CLAUDE.md` — UPDATE — bullet: "PR checks run via `.github/workflows/pr-checks.yaml`. All 8 jobs must be green before merge. Identical gates to pre-commit (`docs/coding-standards.md` §Pre-commit hooks)."

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given .github/workflows/ exists after this story
When `test -f .github/workflows/pr-checks.yaml` runs
Then exit code is 0

Given the workflow YAML was written
When `actionlint .github/workflows/pr-checks.yaml` runs
Then exit code is 0 (no syntax / schema errors)

Given the workflow declares all 8 expected jobs
When `grep -cE "^\s{2}(detect-changes|python-quality|ts-quality|max-lines-check|python-tests|ts-tests|gitleaks|conventional-commits):" .github/workflows/pr-checks.yaml` runs
Then output ≥ 8

Given the workflow must trigger on PR events
When `grep -E "(pull_request|push)" .github/workflows/pr-checks.yaml | head -3` runs
Then exit code is 0
And output contains both "pull_request" and "push"

Given the workflow needs paths-filter
When `grep -E "dorny/paths-filter@v3" .github/workflows/pr-checks.yaml` runs
Then exit code is 0

Given the workflow needs uv setup
When `grep -E "astral-sh/setup-uv@v" .github/workflows/pr-checks.yaml` runs
Then exit code is 0

Given the workflow needs gitleaks
When `grep -E "gitleaks/gitleaks-action@v2" .github/workflows/pr-checks.yaml` runs
Then exit code is 0

Given the smoke tests exist
When `uv run pytest apps/chaoslab-agent/tests/unit apps/target-agent/tests/unit -m "not online" 2>&1 | tail -5` runs
Then exit code is 0
And output contains "2 passed" or "passed" (smoke tests run green)

Given the ts-quality placeholder scripts exist
When `pnpm --filter chaoslab-web lint` runs
Then exit code is 0

Given the max-lines-check job calls the script from story-1.3
When `grep -E "check_max_lines\.py" .github/workflows/pr-checks.yaml` runs
Then exit code is 0

Given CLAUDE.md was updated
When `grep -E "pr-checks\.yaml" CLAUDE.md` runs
Then exit code is 0
```

---

## Shell verification

The coding agent runs this to confirm the story is done before opening a PR:

```bash
set -e
cd /Users/abu/dev/hackathon/rapid-agents

# Workflow file exists
test -f .github/workflows/pr-checks.yaml

# actionlint passes (install via brew if needed, or use docker)
if command -v actionlint > /dev/null 2>&1; then
  actionlint .github/workflows/pr-checks.yaml
else
  docker run --rm -v "$(pwd):/repo" rhysd/actionlint:latest -color /repo/.github/workflows/pr-checks.yaml
fi

# All 8 jobs declared
JOB_COUNT=$(grep -cE "^\s{2}(detect-changes|python-quality|ts-quality|max-lines-check|python-tests|ts-tests|gitleaks|conventional-commits):" .github/workflows/pr-checks.yaml)
[ "$JOB_COUNT" -ge 8 ]

# Triggers correct
grep -q "pull_request:" .github/workflows/pr-checks.yaml
grep -q "push:" .github/workflows/pr-checks.yaml

# Key actions referenced
grep -q "dorny/paths-filter@v3" .github/workflows/pr-checks.yaml
grep -q "astral-sh/setup-uv@v" .github/workflows/pr-checks.yaml
grep -q "pnpm/action-setup@v4" .github/workflows/pr-checks.yaml
grep -q "gitleaks/gitleaks-action@v2" .github/workflows/pr-checks.yaml
grep -q "check_max_lines.py" .github/workflows/pr-checks.yaml

# Smoke tests pass locally (proves the python-tests job has something to run)
uv sync
uv run pytest apps/chaoslab-agent/tests/unit apps/target-agent/tests/unit -m "not online" 2>&1 | tail -3 | grep -q "passed"

# Placeholder TS scripts return 0
pnpm install
pnpm --filter chaoslab-web lint

# 400-line check still green
python3 scripts/check_max_lines.py --strict

# Workflow file itself respects 400-line rule
[ "$(wc -l < .github/workflows/pr-checks.yaml)" -le 400 ]

# CLAUDE.md mentions the workflow
grep -q "pr-checks.yaml" CLAUDE.md

echo "story-1.5 verification: PASS"
```

---

## Notes for coding agent

- The workflow body is specified in `docs/cicd.md` §`pr-checks.yaml` (the stage list 1–8). Translate that into actual YAML — there is no copy-paste source in this case; you compose it.
- Reference reference workflow shapes: `best-practices/02 §2.a` (`ci.yml`) shows the path-filter + parallel-jobs pattern. Adapt naming to ChaosLab conventions (`python-quality` not `python-checks`, etc., per the cicd.md spec).
- `concurrency` block at workflow level: `group: pr-checks-${{ github.ref }}` + `cancel-in-progress: true` — saves cost on force-pushed PRs.
- `permissions:` block: workflow-level `contents: read` + `pull-requests: read` (for paths-filter + PR title check). NO `id-token: write` needed — this workflow does NOT touch GCP.
- For `python-quality` job: pin `astral-sh/setup-uv@v6` (or latest verified). Use `enable-cache: true` + `cache-dependency-glob: '**/uv.lock'`.
- For `ts-quality` job: use `pnpm/action-setup@v4` with `version: 9`, then `actions/setup-node@v4` with `node-version: '20'` + `cache: 'pnpm'` + `cache-dependency-path: pnpm-lock.yaml`.
- Coverage threshold `--cov-fail-under=80` is in pyproject.toml already (`[tool.coverage.report]`). The CLI flag is belt-and-suspenders.
- The `pytest -m "not online"` selector excludes the `@pytest.mark.online` tests (cost-impacting Phoenix/Gemini calls) per `best-practices/06 §3`.
- For `conventional-commits` job: `webiny/action-conventional-commits@v1.3.0` validates PR title format. (The spec mentions both `webiny/...` and `amannn/action-semantic-pull-request` — pick `webiny`, the cicd.md spec calls it out by name.)
- The smoke tests (`test_smoke.py`) MUST be marked NEITHER `@pytest.mark.online` NOR `@pytest.mark.integration` — they're plain unit tests so they run by default.
- The `apps/chaoslab-web/package.json` script placeholders (`"lint": "echo ok"` etc.) are TEMPORARY — they get replaced by real `next lint`, `tsc --noEmit`, `vitest run` invocations in story-7.1. The wiring needs them to exist so CI doesn't fail with "Missing script".
- DO NOT add `--cov-fail-under=80` to the smoke-test run if coverage on placeholder tests will be 0 — either lower threshold for this story (`--cov-fail-under=0`) or omit `--cov` for smoke tests. The 80% threshold applies once real source code lands (epic 2+). Recommended: write the YAML with `--cov-fail-under=80` but accept that python-tests job will fail UNTIL story-2.1 lands real source — document this in `infra/README.md`. OR: gate it with `--cov-fail-under=0` for this story and bump the threshold in a story-2.1 follow-up. **Pick option A** to keep the canonical threshold visible. (Open item: confirm with Abu — see end of story.)
- The workflow does NOT auth to GCP. Auth-requiring workflows are stories 1.6 + 1.7.
- Reference: `cicd.md` §`pr-checks.yaml`, `best-practices/02 §2.a`, `best-practices/02 §6` (caching), `best-practices/02 §10` (pre-commit parity).
