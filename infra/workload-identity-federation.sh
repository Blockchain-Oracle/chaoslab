#!/usr/bin/env bash
# Bootstrap Workload Identity Federation (WIF) for GitHub → GCP auth.
# Run ONCE per GCP project. Idempotent for the create commands (existing
# resources surface as "already exists" warnings which set -e tolerates via
# the trailing `|| true`).
set -euo pipefail

# Required env vars — fail loud if any are missing.
: "${PROJECT:?must set PROJECT (GCP project id, e.g. chaoslab-cicd)}"
: "${PROJECT_NUMBER:?must set PROJECT_NUMBER (numeric, gcloud projects describe \$PROJECT --format='value(projectNumber)')}"
: "${GITHUB_OWNER:?must set GITHUB_OWNER (e.g. Blockchain-Oracle)}"
: "${GITHUB_REPO:?must set GITHUB_REPO (e.g. chaoslab)}"

POOL_ID="${POOL_ID:-github-actions-pool}"
PROVIDER_ID="${PROVIDER_ID:-github-actions-provider}"
DEPLOY_SA="${DEPLOY_SA:-chaoslab-deploy}"
RUNTIME_SA="${RUNTIME_SA:-chaoslab-runtime}"

echo "==> Setting active project: ${PROJECT}"
gcloud config set project "${PROJECT}"

echo "==> Enabling required GCP APIs (idempotent)"
gcloud services enable \
  iamcredentials.googleapis.com \
  iam.googleapis.com \
  cloudresourcemanager.googleapis.com \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  --project="${PROJECT}"

# Artifact Registry repository — Cloud Run pulls images from here. The
# repo is per-region; staging-deploy.yaml's image tag bakes in
# `us-central1-docker.pkg.dev/${PROJECT}/chaoslab/<service>:<sha>`.
REGION="${REGION:-us-central1}"
REPO_NAME="${REPO_NAME:-chaoslab}"
echo "==> Creating Artifact Registry repository: ${REPO_NAME} (${REGION})"
gcloud artifacts repositories create "${REPO_NAME}" \
  --repository-format=docker \
  --location="${REGION}" \
  --description="ChaosLab service images" \
  --project="${PROJECT}" 2>/dev/null || \
  echo "  -> repository already exists, continuing"

# GOTCHA-1: attribute-condition is a CASE-SENSITIVE LITERAL match against
# the GITHUB_OWNER/GITHUB_REPO string. "Blockchain-Oracle/chaoslab" !=
# "blockchain-oracle/chaoslab". If you typo the case, OIDC succeeds but no
# principalSet matches and the deploy SA impersonation fails with a
# misleading "permission denied" error.

echo "==> Creating WIF pool: ${POOL_ID}"
gcloud iam workload-identity-pools create "${POOL_ID}" \
  --project="${PROJECT}" \
  --location="global" \
  --display-name="GitHub Actions pool" \
  --description="Federates GitHub Actions OIDC tokens into GCP" || true

# GOTCHA-2: The OIDC issuer URI must be EXACTLY this URL. A trailing slash,
# missing "actions." subdomain, or http (not https) all fail silently with
# "permission denied" instead of "bad issuer". Copy verbatim.

echo "==> Creating OIDC provider: ${PROVIDER_ID}"
gcloud iam workload-identity-pools providers create-oidc "${PROVIDER_ID}" \
  --project="${PROJECT}" \
  --location="global" \
  --workload-identity-pool="${POOL_ID}" \
  --display-name="GitHub Actions OIDC" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.repository_owner=assertion.repository_owner,attribute.ref=assertion.ref" \
  --attribute-condition="assertion.repository_owner == '${GITHUB_OWNER}'" \
  --issuer-uri="https://token.actions.githubusercontent.com" || true

echo "==> Creating deploy service account: ${DEPLOY_SA}"
gcloud iam service-accounts create "${DEPLOY_SA}" \
  --project="${PROJECT}" \
  --display-name="ChaosLab CI/CD deploy account" \
  --description="Used by GitHub Actions via WIF to deploy Cloud Run services" || true

echo "==> Creating runtime service account: ${RUNTIME_SA}"
gcloud iam service-accounts create "${RUNTIME_SA}" \
  --project="${PROJECT}" \
  --display-name="ChaosLab runtime identity" \
  --description="Identity Cloud Run services assume at request time" || true

DEPLOY_SA_EMAIL="${DEPLOY_SA}@${PROJECT}.iam.gserviceaccount.com"
RUNTIME_SA_EMAIL="${RUNTIME_SA}@${PROJECT}.iam.gserviceaccount.com"

# GOTCHA-3: principalSet binding must use `attribute.repository ==
# OWNER/REPO` (full owner/repo path), NOT just `REPO`. If you bind on
# `REPO` alone it silently matches no token and the deploy SA is
# uninstantiable from any workflow. The `attribute.repository` mapping
# above produces `Blockchain-Oracle/chaoslab` (full path) per OIDC spec.

echo "==> Binding principalSet to ${DEPLOY_SA_EMAIL} (workloadIdentityUser)"
gcloud iam service-accounts add-iam-policy-binding "${DEPLOY_SA_EMAIL}" \
  --project="${PROJECT}" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL_ID}/attribute.repository/${GITHUB_OWNER}/${GITHUB_REPO}"

# GOTCHA-4: Forgetting roles/iam.serviceAccountUser on RUNTIME_SA granted
# TO the DEPLOY_SA breaks Cloud Run deploys ~30 seconds in with a
# "permission denied for serviceAccountUser" error. The deploy SA needs
# this role to specify the runtime SA as the Cloud Run service identity.
echo "==> Granting serviceAccountUser on ${RUNTIME_SA_EMAIL} to ${DEPLOY_SA_EMAIL}"
gcloud iam service-accounts add-iam-policy-binding "${RUNTIME_SA_EMAIL}" \
  --project="${PROJECT}" \
  --role="roles/iam.serviceAccountUser" \
  --member="serviceAccount:${DEPLOY_SA_EMAIL}"

echo "==> Granting project-level roles to deploy SA: ${DEPLOY_SA_EMAIL}"
for role in \
  "roles/run.admin" \
  "roles/artifactregistry.writer" \
  "roles/storage.admin" \
  "roles/cloudbuild.builds.editor" \
  ; do
  echo "  -> ${role}"
  gcloud projects add-iam-policy-binding "${PROJECT}" \
    --member="serviceAccount:${DEPLOY_SA_EMAIL}" \
    --role="${role}" \
    --condition=None \
    --quiet > /dev/null
done

echo "==> Granting project-level roles to runtime SA: ${RUNTIME_SA_EMAIL}"
for role in \
  "roles/secretmanager.secretAccessor" \
  "roles/logging.logWriter" \
  "roles/monitoring.metricWriter" \
  ; do
  echo "  -> ${role}"
  gcloud projects add-iam-policy-binding "${PROJECT}" \
    --member="serviceAccount:${RUNTIME_SA_EMAIL}" \
    --role="${role}" \
    --condition=None \
    --quiet > /dev/null
done

# GOTCHA-5: Every GitHub Actions JOB that needs GCP auth must declare
# `permissions: id-token: write` at the JOB level. Workflow-level
# permissions don't reliably inherit to all jobs across GitHub Actions
# runner versions. If a job's OIDC token is missing/invalid, you'll see
# "no credentials" rather than a clear permission error. Add the
# job-level permissions block to every deploy job in stories 1.6 and 1.7.

WIF_PROVIDER_NAME="projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL_ID}/providers/${PROVIDER_ID}"

cat <<EOF

==============================================================================
WIF bootstrap complete. Record these into GitHub repo Variables
(Settings → Secrets and variables → Actions → Variables — NOT secrets):

  GCP_PROJECT_NUMBER     = ${PROJECT_NUMBER}
  WIF_POOL_ID            = ${POOL_ID}
  WIF_PROVIDER_ID        = ${PROVIDER_ID}
  WIF_PROVIDER_NAME      = ${WIF_PROVIDER_NAME}
  GCP_SERVICE_ACCOUNT    = ${DEPLOY_SA_EMAIL}
  STAGING_PROJECT_ID     = ${PROJECT}
  PROD_PROJECT_ID        = ${PROJECT}   # change if prod is a separate project
  CICD_PROJECT_ID        = ${PROJECT}
  RUNTIME_SA_STAGING     = ${RUNTIME_SA_EMAIL}
  RUNTIME_SA_PROD        = ${RUNTIME_SA_EMAIL}  # change if prod uses separate SA

Verify with:
  gcloud iam workload-identity-pools providers describe ${PROVIDER_ID} \\
    --project=${PROJECT} --location=global --workload-identity-pool=${POOL_ID}
  gcloud iam service-accounts get-iam-policy ${DEPLOY_SA_EMAIL} --project=${PROJECT}

==============================================================================
EOF
