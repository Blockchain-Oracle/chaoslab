# Infra — one-time setup

This directory carries the bash scripts that bootstrap GCP for ChaosLab's CI/CD pipeline. Run them once per GCP project; the CI workflows in `.github/workflows/` assume these scripts have already run.

The scripts are **idempotent** — re-running them is safe (existing resources surface as "already exists" warnings).

## Required env vars

Set all of these before running the scripts:

| Var                     | Example                      | Purpose                                                                                 |
| ----------------------- | ---------------------------- | --------------------------------------------------------------------------------------- |
| `PROJECT`               | `chaoslab-cicd`              | GCP project ID                                                                          |
| `PROJECT_NUMBER`        | `123456789012`               | Numeric ID. Get via `gcloud projects describe $PROJECT --format='value(projectNumber)'` |
| `GITHUB_OWNER`          | `Blockchain-Oracle`          | GitHub org / user that owns the repo (case-sensitive — see GOTCHA-1)                    |
| `GITHUB_REPO`           | `chaoslab`                   | GitHub repo name                                                                        |
| `PHOENIX_API_KEY_VALUE` | `(from Arize Phoenix Cloud)` | Phoenix runtime auth (Secret Manager)                                                   |
| `GITLAB_TOKEN_VALUE`    | `(GitLab PAT, scope: api)`   | GitLab MR emission (Secret Manager)                                                     |
| `GEMINI_API_KEY_VALUE`  | `(from Google AI Studio)`    | Gemini judge LLM credential (Secret Manager)                                            |

## Step-by-step

```bash
# 0. Authenticate to GCP and set the active project
gcloud auth login
gcloud config set project "$PROJECT"

# 1. Enable APIs and bootstrap WIF + service accounts
export PROJECT="chaoslab-cicd"  # or whichever
export PROJECT_NUMBER="$(gcloud projects describe "$PROJECT" --format='value(projectNumber)')"
export GITHUB_OWNER="Blockchain-Oracle"
export GITHUB_REPO="chaoslab"
bash infra/workload-identity-federation.sh
# → records WIF provider name + SA emails on stdout. Save them.

# 2. Seed runtime secrets
export PHOENIX_API_KEY_VALUE="<paste from Arize Phoenix dashboard>"
export GITLAB_TOKEN_VALUE="<paste from GitLab PAT>"
export GEMINI_API_KEY_VALUE="<paste from Google AI Studio>"
bash infra/secret-manager-setup.sh

# 3. Paste the recorded values into GitHub repo Variables
# (Settings → Secrets and variables → Actions → Variables — NOT secrets)
```

### GitHub repo Variables (not secrets)

Per `best-practices/02 §5`, these are project IDs + SA emails — not sensitive. Use **Variables**, not Secrets:

- `GCP_PROJECT_NUMBER`
- `WIF_POOL_ID`
- `WIF_PROVIDER_ID`
- `GCP_SERVICE_ACCOUNT` (deploy SA email)
- `STAGING_PROJECT_ID`
- `PROD_PROJECT_ID`
- `CICD_PROJECT_ID`
- `RUNTIME_SA_STAGING`
- `RUNTIME_SA_PROD`

The WIF script prints the exact values to paste at the end of its run.

## Top-5 WIF gotchas

These are the bugs that took hours to debug across multiple WIF setups. Inline as `# GOTCHA-N:` comments in `workload-identity-federation.sh` at the relevant step.

1. **`attribute-condition` is case-sensitive literal match.** `Blockchain-Oracle/chaoslab` ≠ `blockchain-oracle/chaoslab`. Typoed case → OIDC succeeds, principalSet matches no token, "permission denied" with no hint at the cause.

2. **`principalSet` binding must use the FULL `attribute.repository == OWNER/REPO` path**, not just `REPO`. The OIDC token's `repository` claim is the full path; matching on just the repo name silently matches no token.

3. **`roles/iam.serviceAccountUser` on RUNTIME_SA granted TO the DEPLOY_SA** is the load-bearing binding for Cloud Run deploys. Skip it and the deploy SA can authenticate but Cloud Run rejects the impersonation 30 seconds in.

4. **`permissions: id-token: write` must be declared at JOB level** in every GitHub Actions job that needs GCP auth. Workflow-level permissions don't reliably inherit across runner versions. Missing → "no credentials" instead of a clear permission error.

5. **OIDC issuer URI must be exactly `https://token.actions.githubusercontent.com`** — trailing slashes, missing `actions.` subdomain, or `http://` all fail silently with "permission denied" instead of "bad issuer".

## Verification

After running both scripts:

```bash
# WIF pool + provider exist
gcloud iam workload-identity-pools providers describe "$WIF_PROVIDER_ID" \
  --project="$PROJECT" --location=global --workload-identity-pool="$WIF_POOL_ID"

# Deploy SA has the workloadIdentityUser principalSet binding
gcloud iam service-accounts get-iam-policy chaoslab-deploy@$PROJECT.iam.gserviceaccount.com \
  --project="$PROJECT"

# Runtime SA can read the secrets
gcloud secrets get-iam-policy phoenix-api-key --project="$PROJECT"
gcloud secrets get-iam-policy gitlab-token --project="$PROJECT"
```

## Rollback

If setup needs to start over (e.g., wrong `GITHUB_OWNER` case):

```bash
# Delete the SAs first (they reference the WIF pool)
gcloud iam service-accounts delete chaoslab-deploy@$PROJECT.iam.gserviceaccount.com --project="$PROJECT"
gcloud iam service-accounts delete chaoslab-runtime@$PROJECT.iam.gserviceaccount.com --project="$PROJECT"

# Then delete the pool (cascades to provider)
gcloud iam workload-identity-pools delete github-actions-pool \
  --project="$PROJECT" --location=global

# Secrets can be deleted via:
gcloud secrets delete phoenix-api-key --project="$PROJECT"
gcloud secrets delete gitlab-token --project="$PROJECT"

# Re-run the bootstrap scripts.
```

WIF pools enter a 30-day "DELETED" state after deletion — they can be UNDELETED via `gcloud iam workload-identity-pools undelete`. The pool name remains reserved during this window; creating a new one with the same ID will fail until the old one is fully purged or you pick a new ID.

## References

- `docs/cicd.md` §"Workload Identity Federation (one-time setup)"
- `docs/cicd.md` §"Secret management"
- `best-practices/02 §3` (WIF setup)
- `best-practices/02 §13` (failure modes / gotchas)
- ADR-009 (deployment posture)
