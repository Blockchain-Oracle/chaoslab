# Story — GitHub Actions staging-deploy.yaml workflow

**ID:** story-1.6-staging-deploy-workflow
**Epic:** Epic 1 — Repo + CI/CD foundation
**Depends on:** story-1.4-gcp-iam-bootstrap, story-1.5-pr-checks-workflow
**Estimate:** ~2h
**Status:** PENDING

---

## User story

**As a** ChaosLab maintainer
**I want to** have a GitHub Actions workflow that on every push to `main` (a) auths to GCP via Workload Identity Federation, (b) builds Docker images for chaoslab-web / chaoslab-agent / target-agent only for services whose paths changed, (c) tags each image with `:${{ github.sha }}` and pushes to Artifact Registry, (d) deploys each to Cloud Run staging with `--no-traffic --tag=candidate`, (e) smoke-tests the candidate URL, (f) promotes traffic to 100% on success — and at the end triggers the visual-tests workflow
**So that** the "build once, promote everywhere" pattern (ADR-008) is enforced from day one and every merge to main produces a deployable image hash that can be promoted to prod by story-1.7's workflow without rebuilding

---

## File modification map

Exact files the coding agent creates or modifies for this story:

- `.github/workflows/staging-deploy.yaml` — NEW — full workflow per `docs/cicd.md` §`staging-deploy.yaml`. Jobs:
  1. `detect-changes` — same paths-filter pattern; outputs `agent`, `web`, `target_agent`
  2. `auth-gcp` — runs `google-github-actions/auth@v3` via WIF + `google-github-actions/setup-gcloud@v3`; declares `permissions: id-token: write` at job level
  3. `build-and-deploy` — matrix over `{service: agent, path: apps/chaoslab-agent, changed: agent}`, `{service: web, path: apps/chaoslab-web, changed: web}`, `{service: target-agent, path: apps/target-agent, changed: target_agent}`; per-step `if:` skip when service unchanged; auth → docker-build-push with `cache-from: type=gha,scope=${{ matrix.service }}` → `gcloud run deploy ... --no-traffic --tag=candidate --set-env-vars=ENVIRONMENT=staging --set-secrets=PHOENIX_API_KEY=phoenix-api-key:latest,GITLAB_TOKEN=gitlab-token:latest --service-account=chaoslab-runtime@... --cpu-boost --min-instances=0 --max-instances=10 --memory=1Gi`
  4. `smoke-tests` — `needs: build-and-deploy`; curls `https://<service>-staging---candidate-xxx.run.app/health` for each deployed service; retries 5×; uses `gcloud run services describe ... --format='value(status.traffic.url)' --filter='tag=candidate'` to fetch the candidate URL
  5. `promote-traffic` — `needs: smoke-tests`; runs `gcloud run services update-traffic <service>-staging --to-latest=100 --region=us-central1` for each
  6. `trigger-visual-tests` — implicit via `workflow_run` listener in the visual-tests workflow (story-1.7); this workflow does not need to call it explicitly, but the success of `promote-traffic` is what fires `visual-tests.yaml`
- `apps/chaoslab-agent/Dockerfile` — NEW — minimal placeholder Dockerfile: `FROM python:3.12-slim`, copies `pyproject.toml`, runs `pip install uv && uv sync --frozen`, copies `src/`, exposes 8080, `CMD ["uv", "run", "python", "-m", "chaoslab_agent.main"]`. Real implementation lands in story-4.6 — this is a stub that lets the docker build succeed and the workflow pass actionlint + a dry-run.
- `apps/target-agent/Dockerfile` — NEW — same shape, points at `target_agent.main`
- `apps/chaoslab-web/Dockerfile` — NEW — `FROM node:20-alpine` multi-stage stub: install pnpm, `pnpm install --frozen-lockfile`, `pnpm build` (or `echo skip` for now), final stage runs `pnpm start` on port 8080. Real implementation lands in story-7.3.
- `.dockerignore` — NEW — repo-root file: ignore `node_modules/`, `.venv/`, `.next/`, `.git/`, `docs/`, `research/`, `tests/`, `*.md`
- `CLAUDE.md` — UPDATE — bullet: "Staging deploys fire on every push to `main` via `.github/workflows/staging-deploy.yaml`. The 'build once, promote everywhere' invariant (ADR-008) means the `:${{ github.sha }}` image tag is the unit of promotion. Prod uses the SAME image hash via `prod-promote.yaml` (story-1.7)."

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given .github/workflows/staging-deploy.yaml is created
When `test -f .github/workflows/staging-deploy.yaml` runs
Then exit code is 0

Given the workflow YAML was written
When `actionlint .github/workflows/staging-deploy.yaml` runs
Then exit code is 0

Given the workflow must trigger only on push to main
When `grep -A2 "^on:" .github/workflows/staging-deploy.yaml | grep -E "(push|branches.*main)"` runs
Then exit code is 0

Given the workflow uses Workload Identity Federation
When `grep -E "google-github-actions/auth@v3" .github/workflows/staging-deploy.yaml` runs
Then exit code is 0
And `grep -E "id-token: write" .github/workflows/staging-deploy.yaml` exits 0

Given the workflow tags images with the commit SHA (build-once-promote-everywhere)
When `grep -E ":\\\$\{\{\s*github\.sha\s*\}\}" .github/workflows/staging-deploy.yaml | wc -l` runs
Then output ≥ 3 (each of the 3 services tagged with sha)

Given the workflow uses Docker layer caching with per-service scope
When `grep -E "scope=\\\$\{\{\s*matrix\.service\s*\}\}" .github/workflows/staging-deploy.yaml | wc -l` runs
Then output ≥ 2 (cache-from + cache-to)

Given the workflow uses --no-traffic + --tag=candidate (blue/green pattern)
When `grep -cE "(--no-traffic|--tag=candidate)" .github/workflows/staging-deploy.yaml` runs
Then output ≥ 2

Given the workflow uses paths-filter to skip unchanged services
When `grep -E "dorny/paths-filter@v3" .github/workflows/staging-deploy.yaml` runs
Then exit code is 0

Given the workflow promotes traffic only after smoke succeeds
When `grep -E "update-traffic.*--to-latest=100" .github/workflows/staging-deploy.yaml` runs
Then exit code is 0

Given the Dockerfile stubs exist
When `test -f apps/chaoslab-agent/Dockerfile && test -f apps/target-agent/Dockerfile && test -f apps/chaoslab-web/Dockerfile` runs
Then exit code is 0

Given .dockerignore exists at repo root
When `grep -cE "(node_modules|\.venv|\.next|docs|research)" .dockerignore` runs
Then output ≥ 5

Given the workflow file itself
When `wc -l .github/workflows/staging-deploy.yaml` runs
Then output ≤ 400

Given CLAUDE.md was updated
When `grep -E "staging-deploy\.yaml" CLAUDE.md` runs
Then exit code is 0
```

---

## Shell verification

The coding agent runs this to confirm the story is done before opening a PR:

```bash
set -e
cd /Users/abu/dev/hackathon/rapid-agents

# Workflow file exists
test -f .github/workflows/staging-deploy.yaml

# actionlint passes
if command -v actionlint > /dev/null 2>&1; then
  actionlint .github/workflows/staging-deploy.yaml
else
  docker run --rm -v "$(pwd):/repo" rhysd/actionlint:latest -color /repo/.github/workflows/staging-deploy.yaml
fi

# Triggers on main only
grep -A4 "^on:" .github/workflows/staging-deploy.yaml | grep -E "main"

# WIF auth wired
grep -q "google-github-actions/auth@v3" .github/workflows/staging-deploy.yaml
grep -q "id-token: write" .github/workflows/staging-deploy.yaml

# Each of 3 services tagged with commit sha
SHA_TAGS=$(grep -cE ":\\\$\{\{\s*github\.sha\s*\}\}" .github/workflows/staging-deploy.yaml)
[ "$SHA_TAGS" -ge 3 ]

# Per-service docker cache scope
[ "$(grep -cE 'scope=\\\$\{\{\s*matrix\.service\s*\}\}' .github/workflows/staging-deploy.yaml)" -ge 2 ]

# Blue/green pattern (--no-traffic + --tag=candidate, then update-traffic)
grep -q -- "--no-traffic" .github/workflows/staging-deploy.yaml
grep -q -- "--tag=candidate" .github/workflows/staging-deploy.yaml
grep -q -- "update-traffic.*--to-latest=100" .github/workflows/staging-deploy.yaml

# Paths filter
grep -q "dorny/paths-filter@v3" .github/workflows/staging-deploy.yaml

# Secrets-by-reference for Phoenix + GitLab
grep -q "phoenix-api-key:latest" .github/workflows/staging-deploy.yaml
grep -q "gitlab-token:latest" .github/workflows/staging-deploy.yaml

# Dockerfile stubs present
test -f apps/chaoslab-agent/Dockerfile
test -f apps/target-agent/Dockerfile
test -f apps/chaoslab-web/Dockerfile

# .dockerignore present and excludes the right things
[ "$(grep -cE '(node_modules|\.venv|\.next|docs|research)' .dockerignore)" -ge 5 ]

# Workflow file <= 400 lines
[ "$(wc -l < .github/workflows/staging-deploy.yaml)" -le 400 ]

# 400-line rule still green overall
python3 scripts/check_max_lines.py --strict

# CLAUDE.md mentions the workflow
grep -q "staging-deploy.yaml" CLAUDE.md

echo "story-1.6 verification: PASS"
echo "NOTE: Live deploy will succeed only after Abu has run infra/workload-identity-federation.sh + infra/secret-manager-setup.sh from story-1.4."
```

---

## Notes for coding agent

- This story produces a workflow that PASSES `actionlint` and has the correct shape. The first LIVE run will only succeed once (a) Abu has executed `infra/workload-identity-federation.sh` and `infra/secret-manager-setup.sh` against his GCP project (story-1.4), AND (b) GitHub repo variables are set (`GCP_PROJECT_NUMBER`, `WIF_POOL_ID`, `WIF_PROVIDER_ID`, `GCP_SERVICE_ACCOUNT`, `STAGING_PROJECT_ID`, `CICD_PROJECT_ID`, `RUNTIME_SA_STAGING` — see `infra/README.md`). Do NOT block the story on those external preconditions; the verification is structural only.
- Workflow shape source: `docs/cicd.md` §`staging-deploy.yaml` stages 1–11 list the canonical sequence. Reference shape: `best-practices/02 §2.b` (`deploy-cloud-run.yml`) shows a matrix-with-skip pattern you can adapt.
- The `--no-traffic --tag=candidate` flow is non-negotiable — it's how we get blue/green for free on Cloud Run (per ADR-008 + `best-practices/02 §8`). Smoke test against the tagged candidate URL, THEN `update-traffic --to-latest=100`. NEVER deploy direct-to-traffic.
- The matrix-with-skip pattern (`if: env.SKIP != 'true'` inside steps) is mandatory — using job-level `if:` causes the matrix leg to skip silently which makes debugging hard. The pattern from `best-practices/02 §2.b` is: set `SKIP=true` at the top of the job if the service didn't change, then gate each downstream step on `if: env.SKIP != 'true'`.
- Use `google-github-actions/deploy-cloudrun@v3` (declarative) rather than raw `gcloud run deploy` where possible — it handles secret-by-reference injection more cleanly. But raw `gcloud` is fine for `update-traffic` (no equivalent action).
- The Cloud Run service name pattern: `<service>-staging` (e.g., `chaoslab-agent-staging`, `chaoslab-web-staging`, `target-agent-staging`). Prod will be `<service>-prod` in story-1.7.
- Image tagging: `${REGION}-docker.pkg.dev/${CICD_PROJECT_ID}/chaoslab/${service}:${{ github.sha }}` — REGION = `us-central1` (per `cicd.md`); Artifact Registry repo name = `chaoslab`.
- Dockerfile stubs MUST `EXPOSE 8080` and listen on `$PORT` (Cloud Run sets it). The chaoslab-agent stub can just be `CMD ["python", "-c", "import http.server; http.server.HTTPServer(('0.0.0.0', 8080), http.server.BaseHTTPRequestHandler).serve_forever()"]` if you want it absolutely minimal — the real app lands in story-4.6. Avoid overengineering the stub.
- `concurrency.group: staging-deploy-main` + `cancel-in-progress: false` — never cancel a live deploy mid-way.
- Workflow-level `env:` block sets `REGION: us-central1`, `ARTIFACT_REPO: chaoslab`, `PROJECT_NUMBER: ${{ vars.GCP_PROJECT_NUMBER }}`, `CICD_PROJECT_ID: ${{ vars.CICD_PROJECT_ID }}`, `STAGING_PROJECT_ID: ${{ vars.STAGING_PROJECT_ID }}`, `RUNTIME_SA: ${{ vars.RUNTIME_SA_STAGING }}`.
- The `--cpu-boost` flag (per `cicd.md` line 123) is the spelling we want — `best-practices/02 §13` notes the flag name may differ across gcloud versions. This flag is stable in current gcloud (verified 2026-06-03). Do NOT use `--startup-cpu-boost` — that flag name does not exist.
- The visual-tests workflow (story-1.7) listens via `workflow_run: workflows: ["Deploy Staging"]` — make sure THIS workflow's top-level `name:` is `Deploy Staging` (not the filename) so the linkage works. Confirm in story-1.7.
- Reference: `cicd.md` §`staging-deploy.yaml`, `best-practices/02 §2.b`, `best-practices/02 §4` (multi-service strategy), `best-practices/02 §6` (caching), `best-practices/02 §8` (deploy-on-main pattern + blue/green), ADR-008, ADR-009.
