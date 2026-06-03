# Story — GCP IAM bootstrap (Workload Identity Federation + Secret Manager)

**ID:** story-1.4-gcp-iam-bootstrap
**Epic:** Epic 1 — Repo + CI/CD foundation
**Depends on:** story-1.1-monorepo-init
**Estimate:** ~1.5h
**Status:** PENDING

---

## User story

**As a** ChaosLab maintainer (Abu, running the one-time setup)
**I want to** have a documented, reviewable, `shellcheck`-clean pair of bash scripts that bootstrap Workload Identity Federation (WIF) for GitHub → GCP auth AND seed Phoenix/GitLab secrets into Secret Manager, plus an `infra/README.md` capturing every env var and the top-5 WIF gotchas
**So that** the staging-deploy and prod-promote workflows from stories 1.6/1.7 can authenticate via OIDC (no JSON keys) and read runtime secrets — and so that future-me (or any other operator) can re-run setup against a fresh GCP project without re-reading 30k lines of corpus

This story produces SCRIPTS ONLY — Abu runs them himself against his real GCP project (`chaoslab-cicd` or equivalent). The story does NOT execute them in CI.

---

## File modification map

Exact files the coding agent creates or modifies for this story:

- `infra/workload-identity-federation.sh` — NEW — bash script implementing the full WIF setup from `docs/cicd.md` §"Workload Identity Federation (one-time setup)". Reads required env vars (`PROJECT`, `PROJECT_NUMBER`, `GITHUB_OWNER`, `GITHUB_REPO`); creates the pool, the OIDC provider with attribute-condition, both service accounts (`chaoslab-deploy`, `chaoslab-runtime`), the principalSet binding, and all 7 IAM policy bindings. Includes the top-5 WIF gotchas from `best-practices/02 §13` as inline `# GOTCHA-N:` comments at the relevant step. Uses `set -euo pipefail` and the strict-bash boilerplate.
- `infra/secret-manager-setup.sh` — NEW — bash script implementing `docs/cicd.md` §"Secret management" — reads env vars (`PHOENIX_API_KEY_VALUE`, `GITLAB_TOKEN_VALUE`, `PROJECT`); creates the two secrets via `gcloud secrets create ... --data-file=-`; binds `roles/secretmanager.secretAccessor` to the runtime SA. Same `set -euo pipefail` discipline.
- `infra/README.md` — NEW — operator-facing one-time-setup doc:
  1. Required env vars table (`PROJECT`, `PROJECT_NUMBER`, `GITHUB_OWNER`, `GITHUB_REPO`, `PHOENIX_API_KEY_VALUE`, `GITLAB_TOKEN_VALUE`)
  2. Step-by-step: enable GCP APIs → run WIF script → record output → run Secret Manager script → record output → paste WIF provider name + SA email into GitHub repo variables (`vars.GCP_PROJECT_NUMBER`, `vars.WIF_POOL_ID`, `vars.WIF_PROVIDER_ID`, `vars.GCP_SERVICE_ACCOUNT`, `vars.STAGING_PROJECT_ID`, `vars.PROD_PROJECT_ID`, `vars.CICD_PROJECT_ID`, `vars.RUNTIME_SA_STAGING`, `vars.RUNTIME_SA_PROD`)
  3. The top-5 WIF gotchas verbatim from `best-practices/02 §13` (also in the scripts as comments — README is the human-readable copy)
  4. Verification commands: `gcloud iam workload-identity-pools providers describe ...`, `gcloud iam service-accounts get-iam-policy ...`
  5. Rollback / teardown: how to delete the pool + SAs if setup needs to start over
- `CLAUDE.md` — UPDATE — add one bullet: "GCP IAM bootstrap is a MANUAL ONE-TIME step run by Abu via `bash infra/workload-identity-federation.sh && bash infra/secret-manager-setup.sh` after setting the env vars listed in `infra/README.md`. CI workflows in `.github/workflows/*.yaml` assume this has happened."

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

This story does NOT modify `.github/workflows/*` — that's stories 1.5–1.7.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given infra/ exists as an empty placeholder dir from story-1.1
When the coding agent creates the three new files
Then `test -f infra/workload-identity-federation.sh && test -f infra/secret-manager-setup.sh && test -f infra/README.md` exits 0

Given both shell scripts exist
When `shellcheck infra/workload-identity-federation.sh infra/secret-manager-setup.sh` runs
Then exit code is 0 (zero shellcheck warnings or errors)

Given the WIF script was written per cicd.md
When `grep -cE "(gcloud iam workload-identity-pools|gcloud iam service-accounts|principalSet)" infra/workload-identity-federation.sh` runs
Then output ≥ 5 (key gcloud commands present)

Given the WIF script must declare strict-bash discipline
When `head -5 infra/workload-identity-federation.sh | grep -E "set -euo pipefail"` runs
Then exit code is 0

Given the top-5 WIF gotchas must be inlined as comments
When `grep -cE "^# GOTCHA-" infra/workload-identity-federation.sh` runs
Then output ≥ 5

Given the Secret Manager script was written
When `grep -cE "(gcloud secrets create|gcloud secrets add-iam-policy-binding)" infra/secret-manager-setup.sh` runs
Then output ≥ 3

Given infra/README.md was written
When `grep -cE "(PROJECT|PROJECT_NUMBER|GITHUB_OWNER|GITHUB_REPO|PHOENIX_API_KEY_VALUE|GITLAB_TOKEN_VALUE)" infra/README.md` runs
Then output ≥ 6 (all required env vars documented)

Given infra/README.md must document the WIF gotchas for humans
When `grep -ciE "(gotcha|attribute.condition|principalSet|serviceAccountUser|id-token: write)" infra/README.md` runs
Then output ≥ 5

Given the scripts are static — this story does NOT execute them
When `git diff main...HEAD | grep -E "^\+.*PROJECT_NUMBER=" | grep -v "^\+#\|placeholder\|YOUR_PROJECT"` runs
Then output is empty (no hardcoded real project numbers committed)
```

---

## Shell verification

The coding agent runs this to confirm the story is done before opening a PR:

```bash
set -e
cd /Users/abu/dev/hackathon/rapid-agents

# Files exist
test -f infra/workload-identity-federation.sh
test -f infra/secret-manager-setup.sh
test -f infra/README.md

# Scripts pass shellcheck cleanly
shellcheck infra/workload-identity-federation.sh
shellcheck infra/secret-manager-setup.sh

# Strict-bash discipline
head -5 infra/workload-identity-federation.sh | grep -q "set -euo pipefail"
head -5 infra/secret-manager-setup.sh | grep -q "set -euo pipefail"

# Key gcloud commands present in WIF script
[ "$(grep -cE '(gcloud iam workload-identity-pools|gcloud iam service-accounts|principalSet)' infra/workload-identity-federation.sh)" -ge 5 ]

# Top-5 gotchas inlined as comments
[ "$(grep -cE '^# GOTCHA-' infra/workload-identity-federation.sh)" -ge 5 ]

# Secret Manager script has required commands
[ "$(grep -cE '(gcloud secrets create|gcloud secrets add-iam-policy-binding)' infra/secret-manager-setup.sh)" -ge 3 ]

# README documents env vars
[ "$(grep -cE '(PROJECT|PROJECT_NUMBER|GITHUB_OWNER|GITHUB_REPO|PHOENIX_API_KEY_VALUE|GITLAB_TOKEN_VALUE)' infra/README.md)" -ge 6 ]

# README documents gotchas
[ "$(grep -ciE '(gotcha|attribute.condition|principalSet|serviceAccountUser|id-token)' infra/README.md)" -ge 5 ]

# No real project numbers leaked
! git diff HEAD~1...HEAD -- infra/ 2>/dev/null | grep -E "^\+.*PROJECT_NUMBER=[0-9]{10,}" || true

# CLAUDE.md updated
grep -q "workload-identity-federation.sh" CLAUDE.md

# Scripts themselves respect 400-line rule (likely well under)
[ "$(wc -l < infra/workload-identity-federation.sh)" -le 400 ]
[ "$(wc -l < infra/secret-manager-setup.sh)" -le 400 ]

echo "story-1.4 verification: PASS"
```

---

## Notes for coding agent

- **Do NOT execute these scripts.** They mutate real GCP resources. The story produces the scripts; Abu runs them manually against his project. The verification proves the scripts are syntactically/structurally correct, not that the IAM state in GCP is correct.
- The full WIF setup recipe is in `docs/cicd.md` §"Workload Identity Federation (one-time setup)" — paste the gcloud command sequences verbatim, then add the env-var reads at the top and the strict-bash boilerplate.
- The top-5 WIF gotchas you MUST inline as `# GOTCHA-N:` comments (per `best-practices/02 §13`):
  1. `attribute-condition` is case-sensitive literal match — `<OWNER>/RAPID-AGENTS` ≠ `<OWNER>/rapid-agents`
  2. `principalSet` binding must use `attribute.repository == OWNER/REPO`, not just `REPO`
  3. Forgetting `roles/iam.serviceAccountUser` on the runtime SA granted to the deploy SA → auth succeeds, deploy fails 30 seconds in
  4. Every job that needs GCP auth must declare `permissions: id-token: write` at the JOB level (workflow-level setting doesn't always inherit)
  5. The OIDC issuer URI must be exactly `https://token.actions.githubusercontent.com` (typos fail silently with a misleading "permission denied")
- The script reads `OWNER` / `REPO` from env or uses positional args; do NOT hardcode `ajweb3dev/rapid-agents`. Validate required env vars early: `: "${PROJECT:?must set PROJECT env var}"`, etc.
- The `principalSet` binding string is fiddly — preserve the exact pattern from the spec: `principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL_ID}/attribute.repository/${OWNER}/${REPO}`.
- `infra/README.md` must list the GitHub repo variables (under `Settings → Secrets and variables → Actions → Variables`) that the workflows in stories 1.5–1.7 reference: `GCP_PROJECT_NUMBER`, `WIF_POOL_ID`, `WIF_PROVIDER_ID`, `GCP_SERVICE_ACCOUNT`, `STAGING_PROJECT_ID`, `PROD_PROJECT_ID`, `CICD_PROJECT_ID`, `RUNTIME_SA_STAGING`, `RUNTIME_SA_PROD`. These are VARIABLES (not secrets) because they're not sensitive — per `best-practices/02 §5`.
- The Secret Manager script creates two secrets: `phoenix-api-key`, `gitlab-token`. Both bound to `chaoslab-runtime@$PROJECT.iam.gserviceaccount.com` (not `chaoslab-deploy` — runtime SA is what Cloud Run mounts at request time).
- `shellcheck` must be clean — don't quote variables that need word-splitting (rare), DO quote everything that doesn't (almost everything). Use `"${VAR}"` not `$VAR`. Use `"$(cmd)"` not `` `cmd` ``.
- Reference: `cicd.md` §WIF + §Secret management, `best-practices/02 §3` (WIF setup), `best-practices/02 §13` (failure modes / gotchas), ADR-009.
