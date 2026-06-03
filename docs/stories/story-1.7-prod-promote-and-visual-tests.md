# Story — GitHub Actions prod-promote.yaml + visual-tests.yaml workflows

**ID:** story-1.7-prod-promote-and-visual-tests
**Epic:** Epic 1 — Repo + CI/CD foundation
**Depends on:** story-1.6-staging-deploy-workflow
**Estimate:** ~2h
**Status:** PENDING

---

## User story

**As a** ChaosLab maintainer
**I want to** have two workflows:

1. `prod-promote.yaml` — manually triggered (`workflow_dispatch`) with `commit_sha` + `confirmation=PROMOTE` inputs, that promotes the SAME image hash from staging → prod (never rebuilds) using the blue/green `--no-traffic --tag=candidate-prod` pattern
2. `visual-tests.yaml` — fires automatically after `staging-deploy.yaml` succeeds (via `workflow_run`) and runs Playwright against the live staging URL with anchor-screenshot diffs

**So that** (a) prod releases are explicit human-gated promotions of a staging-validated SHA, and (b) every staging deploy auto-validates the hero visual (Attack Matrix + Resilience Curve cascade-flip) against committed anchor screenshots, catching slop regressions before judges see them

---

## File modification map

Exact files the coding agent creates or modifies for this story:

- `.github/workflows/prod-promote.yaml` — NEW — full workflow per `docs/cicd.md` §`prod-promote.yaml`. Jobs:
  1. `validate-input` — assert `inputs.confirmation == 'PROMOTE'` else fail loudly
  2. `auth-gcp` — WIF with PROD-scoped SA (`chaoslab-deploy-prod@$PROJECT.iam.gserviceaccount.com`); permissions `id-token: write`
  3. `verify-staging-health` — for each service, `gcloud run services describe <service>-staging --format='value(status.url)'` then `curl --fail $URL/health` (assert staging is healthy before promoting from it)
  4. `promote` — matrix over 3 services; `gcloud run services update <service>-prod --image=us-central1-docker.pkg.dev/${CICD_PROJECT}/chaoslab/<service>:${{ inputs.commit_sha }} --region=us-central1 --no-traffic --tag=candidate-prod`; smoke test the candidate URL; `gcloud run services update-traffic <service>-prod --to-latest=100`
  5. `post-promote-smoke` — final curl `--fail` against the prod URLs
  6. `notify` — `actions/github-script@v7` posts a GitHub commit comment with the prod URLs (or a Slack notification if configured)
- `.github/workflows/visual-tests.yaml` — NEW — full workflow per `docs/cicd.md` §`visual-tests.yaml`. Stages:
  1. Trigger: `workflow_run: workflows: ["Deploy Staging"]; types: [completed]; branches: [main]` PLUS `workflow_dispatch` with optional `staging_url` input override
  2. Gate: `if: github.event.workflow_run.conclusion == 'success' || github.event_name == 'workflow_dispatch'`
  3. `auth-gcp` (read-only WIF)
  4. `fetch-staging-url` — `gcloud run services describe chaoslab-web-staging --format='value(status.url)' --region=us-central1`
  5. `playwright-setup` — `pnpm/action-setup@v4`, `actions/setup-node@v4` with pnpm cache, `pnpm install --frozen-lockfile --filter=chaoslab-web`, `pnpm exec playwright install --with-deps chromium`
  6. `run-visual-tests` — `PLAYWRIGHT_BASE_URL=$STAGING_URL pnpm --filter chaoslab-web exec playwright test`
  7. `upload-artifacts` — `if: failure()` — upload `playwright-report/` + `test-results/` as workflow artifacts (7-day retention)
- `apps/chaoslab-web/playwright.config.ts` — NEW — minimal stub config: `defineConfig({ testDir: './tests/e2e', use: { baseURL: process.env.PLAYWRIGHT_BASE_URL ?? 'http://localhost:3000' } })`. Real config + visual specs land in story-7.12 — this stub lets the visual-tests workflow pass actionlint with a meaningful Playwright command.
- `apps/chaoslab-web/tests/e2e/.gitkeep` — NEW — placeholder for visual specs (story-7.12 fills this)
- `apps/chaoslab-web/tests/e2e/smoke.spec.ts` — NEW — single placeholder Playwright test: `test('staging is reachable', async ({ page }) => { await page.goto('/'); await expect(page).toBeDefined(); })` so the test runner has ≥1 test
- `apps/chaoslab-web/package.json` — UPDATE — add `"test:e2e": "playwright test"` script and `@playwright/test` to `devDependencies` (with placeholder version `"^1.49.0"` — pnpm install will resolve)
- `CLAUDE.md` — UPDATE — two bullets:
  - "Prod releases are MANUAL: trigger `prod-promote.yaml` via `gh workflow run prod-promote.yaml -f commit_sha=<sha> -f confirmation=PROMOTE`. Promotes the SAME image hash that already ran in staging — never rebuilds."
  - "Visual tests run automatically after staging-deploy succeeds. Failure artifacts (Playwright traces + screenshots) live on the workflow run for 7 days. See `apps/chaoslab-web/tests/e2e/` for anchor specs (story-7.12 fills these in)."

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given .github/workflows/ contains the prior workflows
When this story completes
Then `test -f .github/workflows/prod-promote.yaml && test -f .github/workflows/visual-tests.yaml` exits 0

Given both workflows must pass actionlint
When `actionlint .github/workflows/prod-promote.yaml .github/workflows/visual-tests.yaml` runs
Then exit code is 0

Given prod-promote.yaml must be manually triggered
When `grep -E "workflow_dispatch:" .github/workflows/prod-promote.yaml` runs
Then exit code is 0
And `grep -E "commit_sha" .github/workflows/prod-promote.yaml` exits 0
And `grep -E "confirmation" .github/workflows/prod-promote.yaml` exits 0

Given prod-promote.yaml must validate the PROMOTE confirmation
When `grep -E "PROMOTE" .github/workflows/prod-promote.yaml` runs
Then exit code is 0

Given prod-promote.yaml must NEVER rebuild — it references the SAME sha image
When `grep -E ":\\\$\{\{\s*(inputs|github\.event\.inputs)\.commit_sha\s*\}\}" .github/workflows/prod-promote.yaml | wc -l` runs
Then output ≥ 3 (each of 3 services references the input sha)

Given prod-promote.yaml uses blue/green
When `grep -cE "(--no-traffic|--tag=candidate-prod|update-traffic.*--to-latest=100)" .github/workflows/prod-promote.yaml` runs
Then output ≥ 3

Given visual-tests.yaml must trigger on workflow_run success
When `grep -A3 "workflow_run:" .github/workflows/visual-tests.yaml | grep -E "(workflows|types|conclusion)"` runs
Then exit code is 0
And `grep -E "Deploy Staging" .github/workflows/visual-tests.yaml` exits 0 (refers to staging-deploy workflow by name)

Given visual-tests.yaml runs Playwright against staging
When `grep -E "PLAYWRIGHT_BASE_URL" .github/workflows/visual-tests.yaml` runs
Then exit code is 0
And `grep -E "playwright install --with-deps chromium" .github/workflows/visual-tests.yaml` exits 0

Given visual-tests.yaml uploads diff artifacts on failure
When `grep -A2 "if:\s*failure" .github/workflows/visual-tests.yaml | grep -E "upload-artifact"` runs
Then exit code is 0

Given the playwright config exists
When `test -f apps/chaoslab-web/playwright.config.ts` runs
Then exit code is 0

Given each workflow file respects 400-line rule
When `wc -l .github/workflows/prod-promote.yaml .github/workflows/visual-tests.yaml | awk '{print $1}' | head -2` runs
Then all values ≤ 400

Given CLAUDE.md was updated
When `grep -cE "(prod-promote|visual-tests)" CLAUDE.md` runs
Then output ≥ 2
```

---

## Shell verification

The coding agent runs this to confirm the story is done before opening a PR:

```bash
set -e
cd /Users/abu/dev/hackathon/rapid-agents

# Both workflow files exist
test -f .github/workflows/prod-promote.yaml
test -f .github/workflows/visual-tests.yaml

# actionlint clean on both
if command -v actionlint > /dev/null 2>&1; then
  actionlint .github/workflows/prod-promote.yaml .github/workflows/visual-tests.yaml
else
  docker run --rm -v "$(pwd):/repo" rhysd/actionlint:latest -color \
    /repo/.github/workflows/prod-promote.yaml \
    /repo/.github/workflows/visual-tests.yaml
fi

# prod-promote: manual trigger, PROMOTE confirmation, sha-referencing promotion
grep -q "workflow_dispatch:" .github/workflows/prod-promote.yaml
grep -q "commit_sha" .github/workflows/prod-promote.yaml
grep -q "confirmation" .github/workflows/prod-promote.yaml
grep -q "PROMOTE" .github/workflows/prod-promote.yaml

SHA_REFS=$(grep -cE ":\\\$\{\{\s*(inputs|github\.event\.inputs)\.commit_sha\s*\}\}" .github/workflows/prod-promote.yaml)
[ "$SHA_REFS" -ge 3 ]

# prod-promote: blue/green pattern present
[ "$(grep -cE '(--no-traffic|--tag=candidate-prod|update-traffic.*--to-latest=100)' .github/workflows/prod-promote.yaml)" -ge 3 ]

# visual-tests: workflow_run trigger referencing staging deploy
grep -q "workflow_run:" .github/workflows/visual-tests.yaml
grep -q "Deploy Staging" .github/workflows/visual-tests.yaml
grep -q "PLAYWRIGHT_BASE_URL" .github/workflows/visual-tests.yaml
grep -q "playwright install --with-deps chromium" .github/workflows/visual-tests.yaml

# visual-tests: artifact upload on failure
grep -A3 "if:.*failure" .github/workflows/visual-tests.yaml | grep -q "upload-artifact"

# Playwright config stub present
test -f apps/chaoslab-web/playwright.config.ts
test -f apps/chaoslab-web/tests/e2e/smoke.spec.ts

# package.json has test:e2e script
grep -q "test:e2e" apps/chaoslab-web/package.json

# Each workflow file <= 400 lines
[ "$(wc -l < .github/workflows/prod-promote.yaml)" -le 400 ]
[ "$(wc -l < .github/workflows/visual-tests.yaml)" -le 400 ]

# Repo-wide 400-line rule still green
python3 scripts/check_max_lines.py --strict

# CLAUDE.md mentions both workflows
[ "$(grep -cE '(prod-promote|visual-tests)' CLAUDE.md)" -ge 2 ]

echo "story-1.7 verification: PASS"
echo "NOTE: First live prod-promote run succeeds only after Abu has bootstrapped the prod-side IAM (extension of infra/workload-identity-federation.sh for prod SA) and the staging-deploy workflow from story-1.6 has produced a deployable SHA."
```

---

## Notes for coding agent

- `docs/cicd.md` §`prod-promote.yaml` lists stages 1–7. `docs/cicd.md` §`visual-tests.yaml` lists stages 1–5. Both are detailed but not literal YAML; you translate to actionlint-clean YAML.
- Reference shape for visual-tests: `best-practices/02 §2.c` (`visual-test.yml`) — has the exact `workflow_run` + `workflow_dispatch` + `fetch-staging-url` + `playwright install` + `upload-artifact on failure` pattern. Adapt service names: it uses `web-staging`, we use `chaoslab-web-staging` (matching the names from story-1.6).
- Reference shape for prod-promote: `best-practices/02 §2.b`'s `deploy-prod` job is the closest analog (matrix + same-image-promotion + manual gate). Adapt the manual gate from a GitHub Environment to a `workflow_dispatch` with confirmation input per `cicd.md`.
- The `workflow_run` linkage between `staging-deploy.yaml` and `visual-tests.yaml` requires the staging workflow's top-level `name:` (NOT filename) to match exactly what `workflow_run.workflows: [...]` lists. Story-1.6 should set `name: Deploy Staging`. Verify before declaring done.
- `validate-input` job: simple `if: inputs.confirmation != 'PROMOTE'` step with `run: echo "Refusing to promote: confirmation must equal PROMOTE"; exit 1`. Or use a step-level `if:` to short-circuit the entire matrix.
- For the prod SA: `cicd.md` references `chaoslab-deploy-prod@PROJECT.iam.gserviceaccount.com`. The `infra/workload-identity-federation.sh` from story-1.4 creates `chaoslab-deploy` (staging-shared). The prod-specific SA + WIF binding is a manual extension Abu does — document this in `CLAUDE.md` and `infra/README.md` (you can update the README in this story if needed, or leave it as a known open item). **Open item flagged at the end of this report.**
- `gh workflow run prod-promote.yaml -f commit_sha=<sha> -f confirmation=PROMOTE` is the canonical invocation pattern — include this exact command in the CLAUDE.md bullet.
- The visual-tests workflow's `fetch-staging-url` step writes to `$GITHUB_OUTPUT` — pattern: `URL=$(gcloud run services describe ...); echo "url=$URL" >> $GITHUB_OUTPUT`. Then downstream step uses `${{ steps.url.outputs.url }}`.
- `playwright install --with-deps chromium` — use ONLY chromium for the demo (lighter, faster). Story-7.12 may add webkit/firefox if needed.
- The smoke `e2e/smoke.spec.ts` test should be intentionally trivial — just enough that `playwright test` runs >0 tests so the workflow has a real assertion path. Real anchor visual tests land in story-7.12.
- `@playwright/test` in devDependencies: use a placeholder pin like `"^1.49.0"`. If the pin lookup fails during `pnpm install`, fall back to `"latest"` — story-7.12 will pin properly.
- Concurrency: `prod-promote` should set `concurrency.group: prod-promote` + `cancel-in-progress: false` (never cancel a prod promotion mid-way). `visual-tests` can set `concurrency.group: visual-tests-${{ github.ref }}` + `cancel-in-progress: true`.
- Reference: `cicd.md` §`prod-promote.yaml` + §`visual-tests.yaml`, `best-practices/02 §2.b` (deploy-prod job), `best-practices/02 §2.c` (visual-test.yml), `best-practices/02 §8` (rollback-safe blue/green), ADR-008.
