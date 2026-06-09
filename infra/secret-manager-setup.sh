#!/usr/bin/env bash
# Seed Secret Manager with runtime secrets the Cloud Run services mount.
# Run AFTER workload-identity-federation.sh (this script binds the runtime
# SA created there to read these secrets).
set -euo pipefail

: "${PROJECT:?must set PROJECT (GCP project id)}"
: "${PHOENIX_API_KEY_VALUE:?must set PHOENIX_API_KEY_VALUE (Arize Phoenix Cloud key)}"
: "${GITLAB_TOKEN_VALUE:?must set GITLAB_TOKEN_VALUE (GitLab personal access token for MR emission)}"

RUNTIME_SA="${RUNTIME_SA:-chaoslab-runtime}"
RUNTIME_SA_EMAIL="${RUNTIME_SA}@${PROJECT}.iam.gserviceaccount.com"

echo "==> Setting active project: ${PROJECT}"
gcloud config set project "${PROJECT}"

echo "==> Enabling Secret Manager API (idempotent)"
gcloud services enable secretmanager.googleapis.com --project="${PROJECT}"

echo "==> Creating secret: phoenix-api-key"
printf '%s' "${PHOENIX_API_KEY_VALUE}" | gcloud secrets create phoenix-api-key \
  --project="${PROJECT}" \
  --replication-policy="automatic" \
  --data-file=- || \
printf '%s' "${PHOENIX_API_KEY_VALUE}" | gcloud secrets versions add phoenix-api-key \
  --project="${PROJECT}" \
  --data-file=-

echo "==> Creating secret: gitlab-token"
printf '%s' "${GITLAB_TOKEN_VALUE}" | gcloud secrets create gitlab-token \
  --project="${PROJECT}" \
  --replication-policy="automatic" \
  --data-file=- || \
printf '%s' "${GITLAB_TOKEN_VALUE}" | gcloud secrets versions add gitlab-token \
  --project="${PROJECT}" \
  --data-file=-

echo "==> Binding runtime SA ${RUNTIME_SA_EMAIL} as secretAccessor on phoenix-api-key"
gcloud secrets add-iam-policy-binding phoenix-api-key \
  --project="${PROJECT}" \
  --member="serviceAccount:${RUNTIME_SA_EMAIL}" \
  --role="roles/secretmanager.secretAccessor"

echo "==> Binding runtime SA ${RUNTIME_SA_EMAIL} as secretAccessor on gitlab-token"
gcloud secrets add-iam-policy-binding gitlab-token \
  --project="${PROJECT}" \
  --member="serviceAccount:${RUNTIME_SA_EMAIL}" \
  --role="roles/secretmanager.secretAccessor"

cat <<EOF

==============================================================================
Secret Manager bootstrap complete.

Secrets created (or new version added):
  phoenix-api-key  →  bound: ${RUNTIME_SA_EMAIL}
  gitlab-token     →  bound: ${RUNTIME_SA_EMAIL}

Verify with:
  gcloud secrets list --project=${PROJECT}
  gcloud secrets get-iam-policy phoenix-api-key --project=${PROJECT}
==============================================================================
EOF
