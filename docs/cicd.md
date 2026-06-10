# CI/CD Spec — Phoenix Audit

> **Rename note (PR #83, 2026-06-10):** any `chaoslab-agent` / `chaoslab-web` / `chaoslab_agent` reference in this document refers to the renamed `apps/phoenix-audit-agent` / `apps/phoenix-audit-web` / `phoenix_audit_agent`. GCP identities (SAs `chaoslab-deploy` / `chaoslab-runtime`, bucket `chaoslab-recipes`) intentionally keep their legacy names — see CLAUDE.md.

**Status:** DRAFT — pending Abu approval (LOCKS upon approval)
**Last updated:** 2026-06-02

Per Abu's explicit directive: **CI/CD is the FIRST piece built.** Every later story ships into this pipeline. Without CI/CD locked first, every other story retrofits discipline. Story-1.1 of Epic 1 is "set up CI/CD with 400-line enforcement working end-to-end."

---

## Pipeline overview

```
                    ┌─────────────────────────────────────────┐
                    │  Pull Request opened / pushed           │
                    └─────────────────┬───────────────────────┘
                                      │
                              ┌───────▼────────┐
                              │ pr-checks.yaml │
                              ├────────────────┤
                              │ • paths-filter │
                              │ • ruff + ty    │
                              │ • eslint + tsc │
                              │ • 400-line     │
                              │ • pytest unit  │
                              │ • vitest unit  │
                              │ • coverage ≥80%│
                              │ • gitleaks     │
                              └───────┬────────┘
                                      │ (all green)
                              ┌───────▼────────┐
                              │ Branch merged  │
                              │   to main      │
                              └───────┬────────┘
                                      │
                            ┌─────────▼──────────┐
                            │ staging-deploy.yaml│
                            ├────────────────────┤
                            │ • build image      │
                            │ • tag :${sha}      │
                            │ • push Artifact Reg│
                            │ • deploy → staging │
                            │ • smoke test       │
                            └─────────┬──────────┘
                                      │ (all green)
                            ┌─────────▼──────────┐
                            │ visual-tests.yaml  │
                            ├────────────────────┤
                            │ • Playwright vs    │
                            │   staging URL      │
                            │ • screenshot diff  │
                            └─────────┬──────────┘
                                      │
                            (manual approval)
                                      │
                            ┌─────────▼──────────┐
                            │ prod-promote.yaml  │
                            ├────────────────────┤
                            │ • promote SAME hash│
                            │   to prod (never   │
                            │   rebuild)         │
                            │ • blue/green via   │
                            │   --no-traffic +   │
                            │   smoke + traffic  │
                            └────────────────────┘
```

---

## Workflow files

All workflows under `.github/workflows/`. Path-based filters in each so unrelated changes don't trigger heavy jobs.

### `pr-checks.yaml`

Runs on every push to a non-main branch and on every PR.

**Stages (parallel where possible):**

1. **detect-changes** (`dorny/paths-filter@v3`) — outputs `python-changed`, `ts-changed`, `infra-changed`
2. **python-quality** (depends on detect, fires if python-changed)
   - Setup `uv` (`astral-sh/setup-uv@v3` with cache)
   - `uv sync --frozen --all-extras`
   - `uv run ruff check .` (lint)
   - `uv run ruff format --check .` (format)
   - `uv run ty check apps/chaoslab-agent apps/target-agent`
   - Fallback `uv run mypy --strict apps/chaoslab-agent apps/target-agent` only if `TY_FALLBACK=1` env set (ADR-001)
3. **ts-quality** (depends on detect, fires if ts-changed)
   - Setup `pnpm` (`pnpm/action-setup@v4` with cache)
   - `pnpm install --frozen-lockfile`
   - `pnpm lint` (ESLint 9)
   - `pnpm format --check` (Prettier)
   - `pnpm typecheck` (tsc --noEmit)
4. **max-lines-check** (always runs)
   - `python3 scripts/check_max_lines.py --strict` (exit 1 if any tracked file >400 lines)
5. **python-tests** (depends on python-quality)
   - `uv run pytest apps/chaoslab-agent/tests/unit apps/target-agent/tests/unit -v --cov --cov-fail-under=80`
   - `pytest.mark.online` excluded (cost control per `best-practices/06 §3`)
6. **ts-tests** (depends on ts-quality)
   - `pnpm test:unit --coverage` (Vitest)
   - Coverage threshold ≥80% on changed files
7. **gitleaks** (always runs) — `gitleaks/gitleaks-action@v2` scans for committed secrets
8. **conventional-commits** — `webiny/action-conventional-commits@v1.3.0` validates PR title

**All steps must be green for merge.** Branch protection rule on `main` enforces.

### `staging-deploy.yaml`

Runs on every push to `main`.

**Critical pattern (ADR-008 — build once, promote everywhere):** the image built and tested in staging is the SAME image that gets promoted to prod. Never rebuild.

**Stages:**

1. **detect-changes** — same paths-filter
2. **auth-gcp** — `google-github-actions/auth@v3` via Workload Identity Federation. Service account: `chaoslab-deploy@PROJECT.iam.gserviceaccount.com`
3. **build-chaoslab-agent** (if python or shared changed)
   - `docker buildx build` with `--cache-from type=gha,scope=chaoslab-agent --cache-to type=gha,scope=chaoslab-agent,mode=max`
   - Tag: `us-central1-docker.pkg.dev/PROJECT/chaoslab/chaoslab-agent:${{ github.sha }}`
   - Push to Artifact Registry
4. **build-chaoslab-web** (if ts or shared changed)
   - Same pattern, tag `chaoslab-web:${{ github.sha }}`
5. **build-target-agent** (if target-agent changed)
   - Same pattern, tag `target-agent:${{ github.sha }}`
6. **deploy-staging-chaoslab-agent**
   - `gcloud run deploy chaoslab-agent --image=us-central1-docker.pkg.dev/PROJECT/chaoslab/chaoslab-agent:${{ github.sha }} --region=us-central1 --no-traffic --tag=candidate --set-env-vars=ENVIRONMENT=staging --set-secrets=PHOENIX_API_KEY=phoenix-api-key:latest,GITLAB_TOKEN=gitlab-token:latest --service-account=chaoslab-runtime@PROJECT.iam.gserviceaccount.com --cpu-boost`
7. **deploy-staging-chaoslab-web**
   - Same pattern with `chaoslab-web` and its env vars (`AGENT_BACKEND_URL=https://chaoslab-agent-staging-xxx.run.app`)
8. **deploy-staging-target-agent**
   - Same pattern with `target-agent`
9. **smoke-tests** — `curl --fail https://chaoslab-web-staging---candidate-xxx.run.app/health` for each service
10. **promote-staging-traffic** — `gcloud run services update-traffic chaoslab-web --to-latest=100 --region=us-central1` for each service after smoke green
11. **trigger-visual-tests** — `workflow_run` event triggers `visual-tests.yaml` against the freshly-deployed staging URL

### `prod-promote.yaml`

Manually triggered (`workflow_dispatch`) — never automatic. Promotes a specific staging-validated commit to prod.

**Inputs:** `commit_sha` (string), `confirmation` (must equal "PROMOTE")

**Stages:**

1. **validate-input** — assert `confirmation == "PROMOTE"`, else fail
2. **auth-gcp** — WIF, prod-specific service account `chaoslab-deploy-prod@PROJECT.iam.gserviceaccount.com`
3. **verify-staging-health** — check staging revision serving 100% traffic and `/health` returning 200
4. **promote-chaoslab-agent**
   - `gcloud run services update chaoslab-agent --image=us-central1-docker.pkg.dev/PROJECT/chaoslab/chaoslab-agent:${{ github.event.inputs.commit_sha }} --region=us-central1 --no-traffic --tag=candidate-prod`
   - Smoke test on candidate URL
   - `gcloud run services update-traffic ... --to-latest=100`
5. **promote-chaoslab-web + promote-target-agent** — same pattern
6. **post-promote-smoke** — `curl --fail` on prod URLs
7. **notify** — GitHub comment with prod URLs

### `visual-tests.yaml`

Runs after `staging-deploy.yaml` succeeds AND on manual dispatch.

**Stages:**

1. **auth-gcp** — read-only WIF
2. **fetch-staging-url** — `gcloud run services describe chaoslab-web --format='value(status.url)' --region=us-central1`
3. **playwright-setup**
   - `pnpm install --frozen-lockfile --filter=chaoslab-web`
   - `pnpm exec playwright install --with-deps chromium`
4. **run-visual-tests**
   - `PLAYWRIGHT_BASE_URL=$STAGING_URL pnpm test:e2e`
   - Includes screenshot regression for the Attack Matrix canonical state, the Resilience Curve mid-attack, and the post-patch state
5. **upload-artifacts** — Playwright traces + screenshots as workflow artifact on failure

---

## Workload Identity Federation (one-time setup)

Per `best-practices/02 §3`. Script: `infra/workload-identity-federation.sh`.

### Pool + provider creation

```bash
gcloud iam workload-identity-pools create chaoslab-github-pool \
  --location=global \
  --display-name="ChaosLab GitHub Pool"

gcloud iam workload-identity-pools providers create-oidc chaoslab-github-provider \
  --location=global \
  --workload-identity-pool=chaoslab-github-pool \
  --display-name="ChaosLab GitHub Provider" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.repository_owner=assertion.repository_owner" \
  --attribute-condition='assertion.repository == "<OWNER>/rapid-agents"' \
  --issuer-uri=https://token.actions.githubusercontent.com
```

⚠ **WIF gotcha #1 (per `best-practices/02 §13`):** the `attribute-condition` is a CASE-SENSITIVE LITERAL match. `<OWNER>/RAPID-AGENTS` (capital) fails silently. Use exact GitHub repo casing.

⚠ **WIF gotcha #2:** `principalSet` binding must use `attribute.repository == OWNER/REPO`, NOT just `REPO`. Common one-line bug.

### Service account creation + binding

```bash
gcloud iam service-accounts create chaoslab-deploy \
  --display-name="ChaosLab CI/CD Deploy SA"

gcloud iam service-accounts create chaoslab-runtime \
  --display-name="ChaosLab Cloud Run Runtime SA"

# Deploy SA can deploy to Cloud Run, push to Artifact Registry, read secrets
gcloud projects add-iam-policy-binding $PROJECT \
  --member="serviceAccount:chaoslab-deploy@$PROJECT.iam.gserviceaccount.com" \
  --role="roles/run.developer"

gcloud projects add-iam-policy-binding $PROJECT \
  --member="serviceAccount:chaoslab-deploy@$PROJECT.iam.gserviceaccount.com" \
  --role="roles/artifactregistry.writer"

gcloud projects add-iam-policy-binding $PROJECT \
  --member="serviceAccount:chaoslab-deploy@$PROJECT.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# Critical: Deploy SA needs to "act as" the Runtime SA
gcloud iam service-accounts add-iam-policy-binding chaoslab-runtime@$PROJECT.iam.gserviceaccount.com \
  --member="serviceAccount:chaoslab-deploy@$PROJECT.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"

# Runtime SA gets actual runtime permissions (Vertex AI, Cloud Logging, etc.)
gcloud projects add-iam-policy-binding $PROJECT \
  --member="serviceAccount:chaoslab-runtime@$PROJECT.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"

gcloud projects add-iam-policy-binding $PROJECT \
  --member="serviceAccount:chaoslab-runtime@$PROJECT.iam.gserviceaccount.com" \
  --role="roles/logging.logWriter"

# Bind WIF subject to Deploy SA
gcloud iam service-accounts add-iam-policy-binding chaoslab-deploy@$PROJECT.iam.gserviceaccount.com \
  --role=roles/iam.workloadIdentityUser \
  --member="principalSet://iam.googleapis.com/projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/chaoslab-github-pool/attribute.repository/<OWNER>/rapid-agents"
```

⚠ **WIF gotcha #3 (the silent killer):** forgetting `roles/iam.serviceAccountUser` on the runtime SA granted to the deploy SA → auth succeeds, deploy fails 30 seconds in with a misleading "permission denied" error.

### GitHub Actions auth step

In every workflow:

```yaml
- name: Authenticate to Google Cloud
  uses: google-github-actions/auth@v3
  with:
    workload_identity_provider: projects/${{ env.PROJECT_NUMBER }}/locations/global/workloadIdentityPools/chaoslab-github-pool/providers/chaoslab-github-provider
    service_account: chaoslab-deploy@${{ env.PROJECT }}.iam.gserviceaccount.com

- name: Set up gcloud
  uses: google-github-actions/setup-gcloud@v3
```

⚠ **WIF gotcha #4:** every job that needs auth must have `permissions: id-token: write` at the job level. Common to set at workflow level and miss a job override.

---

## Secret management

All secrets in Google Secret Manager. Bootstrap via `infra/secret-manager-setup.sh`:

```bash
echo -n "$PHOENIX_API_KEY_VALUE" | gcloud secrets create phoenix-api-key --data-file=-
echo -n "$GITLAB_TOKEN_VALUE" | gcloud secrets create gitlab-token --data-file=-

gcloud secrets add-iam-policy-binding phoenix-api-key \
  --member="serviceAccount:chaoslab-runtime@$PROJECT.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding gitlab-token \
  --member="serviceAccount:chaoslab-runtime@$PROJECT.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

Cloud Run reads at deploy time via `--set-secrets=PHOENIX_API_KEY=phoenix-api-key:latest,GITLAB_TOKEN=gitlab-token:latest`.

**Never** commit secrets to repo. `.gitleaks.toml` config + pre-commit + CI `gitleaks` step are the three layers.

---

## 400-line enforcement script

`scripts/check_max_lines.py` — invoked from both pre-commit (local) and `pr-checks.yaml` (CI). Per ADR-010 and `best-practices/03 §1.1`.

```python
#!/usr/bin/env python3
"""Enforce 400-line maximum per source file. Skip blank lines and comments."""
from __future__ import annotations
import sys
from pathlib import Path
from typing import Iterable

MAX_LINES = 400
ROOTS = ["apps/", "packages/", "scripts/"]
EXTENSIONS = {".py", ".ts", ".tsx", ".js", ".jsx", ".md"}
EXCLUDE_PATTERNS = {"__init__.py", ".d.ts", "_vendored/", "node_modules/", ".next/", "dist/", "build/"}

def is_excluded(path: Path) -> bool:
    return any(pat in str(path) for pat in EXCLUDE_PATTERNS)

def count_significant_lines(path: Path) -> int:
    text = path.read_text(encoding="utf-8", errors="ignore")
    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.strip().startswith(("#", "//", "/*", "*", "<!--"))
    ]
    return len(lines)

def main() -> int:
    failures: list[tuple[Path, int]] = []
    for root in ROOTS:
        for path in Path(root).rglob("*"):
            if not path.is_file() or path.suffix not in EXTENSIONS or is_excluded(path):
                continue
            count = count_significant_lines(path)
            if count > MAX_LINES:
                failures.append((path, count))
    if failures:
        print(f"❌ {len(failures)} files exceed {MAX_LINES} lines:")
        for p, c in sorted(failures, key=lambda x: -x[1]):
            print(f"  {p}: {c} lines (over by {c - MAX_LINES})")
        return 1
    print(f"✅ All files ≤ {MAX_LINES} lines")
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

**Wired into pre-commit** (`.pre-commit-config.yaml`):

```yaml
- repo: local
  hooks:
    - id: check-max-lines
      name: Enforce 400-line limit
      entry: python3 scripts/check_max_lines.py --strict
      language: system
      pass_filenames: false
      always_run: true
```

**Wired into CI** (`pr-checks.yaml`):

```yaml
max-lines-check:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with: { python-version: "3.12" }
    - run: python3 scripts/check_max_lines.py --strict
```

---

## Branch protection

On `main`:

- Require pull request before merging
- Require 1 approving review (Abu OR `sahil-pr-audit` bot — automated approval counts)
- Require status checks to pass: `pr-checks/python-quality`, `pr-checks/ts-quality`, `pr-checks/max-lines-check`, `pr-checks/python-tests`, `pr-checks/ts-tests`, `pr-checks/gitleaks`, `pr-checks/conventional-commits`
- Require branches up to date before merging
- Require linear history (no merge commits — squash only)
- Lock branch (only via PR, no direct pushes)
- Required signed commits (optional — turn off if it slows orchestrator)

---

## Conventional commits

Format: `<type>(<scope>): <subject>` (per `best-practices/03 §13`)

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `perf`, `ci`, `build`, `revert`

Examples (orchestrator generates these):

- `feat(injector): add malformed_tool_output fault decorator`
- `fix(phoenix-tools): handle 429 retries in run_experiment wrapper`
- `chore(deps): bump @visx/scale to 4.x`
- `ci(workflows): wire visual-tests after staging deploy`

PR title MUST match this format — enforced by `webiny/action-conventional-commits` in `pr-checks.yaml`.

---

## Cost projection (per `architecture/06 §5`)

- 9 days dev + 4 weeks judging window
- ~$45 dev + ~$27 judging = **~$72** under the $100 GCP credit
- Two non-negotiable optimizations:
  1. `JUDGE_LLM=gemini-3.5-flash` (ADR-007) — saves $80 vs Gemini Pro
  2. Prompt-caching the target system prompt for repeated runs
- Min-instances=1 on web + agent during judging ($7/svc/mo × 2 = ~$14) — counter-intuitively costs MORE than tokens at this scale, but cold-start mitigation is worth it

---

## Notes for downstream agents

- The orchestrator's first dispatched story (Epic 1, Story 1.1) bootstraps the entire `scripts/` + `infra/` + `.github/workflows/` skeleton in one PR. Subsequent stories ship into this pipeline.
- Every PR runs the full `pr-checks.yaml` — if a coding agent's PR is red, it must fix before merge. No exceptions.
- The deploy workflows are NOT triggered by per-story PRs — only on merge to main. The orchestrator merges in batches.
