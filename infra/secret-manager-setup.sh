#!/usr/bin/env bash
# Seed Secret Manager with runtime secrets the Cloud Run services mount.
# Run AFTER workload-identity-federation.sh (this script binds the runtime
# SA created there to read these secrets).
set -euo pipefail

: "${PROJECT:?must set PROJECT (GCP project id)}"
: "${PHOENIX_API_KEY_VALUE:?must set PHOENIX_API_KEY_VALUE (Arize Phoenix Cloud key)}"
: "${GITLAB_TOKEN_VALUE:?must set GITLAB_TOKEN_VALUE (GitLab personal access token for MR emission)}"
# Hosted deploys use Vertex AI (ADC via the runtime SA) — no Gemini key.
# Set GEMINI_API_KEY_VALUE only when shipping an AI Studio BYO build.
GEMINI_API_KEY_VALUE="${GEMINI_API_KEY_VALUE:-}"

# Legacy identity name — kept through the phoenix-audit rename (see CLAUDE.md).
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

echo "==> Creating secret: cookie-signature-keys (web session-cookie signing, story-9.4)"
# Two comma-separated 64-hex keys — rotation = prepend a new key, keep the old.
COOKIE_SIGNATURE_KEYS_VALUE="${COOKIE_SIGNATURE_KEYS_VALUE:-$(openssl rand -hex 32),$(openssl rand -hex 32)}"
printf '%s' "${COOKIE_SIGNATURE_KEYS_VALUE}" | gcloud secrets create cookie-signature-keys \
  --project="${PROJECT}" \
  --replication-policy="automatic" \
  --data-file=- || \
printf '%s' "${COOKIE_SIGNATURE_KEYS_VALUE}" | gcloud secrets versions add cookie-signature-keys \
  --project="${PROJECT}" \
  --data-file=-

SECRETS=(phoenix-api-key gitlab-token cookie-signature-keys)
if [ -n "${GEMINI_API_KEY_VALUE}" ]; then
  echo "==> Creating optional secret: gemini-api-key (BYO AI Studio path)"
  printf '%s' "${GEMINI_API_KEY_VALUE}" | gcloud secrets create gemini-api-key \
    --project="${PROJECT}" \
    --replication-policy="automatic" \
    --data-file=- || \
  printf '%s' "${GEMINI_API_KEY_VALUE}" | gcloud secrets versions add gemini-api-key \
    --project="${PROJECT}" \
    --data-file=-
  SECRETS+=(gemini-api-key)
fi

for secret in "${SECRETS[@]}"; do
  echo "==> Binding runtime SA ${RUNTIME_SA_EMAIL} as secretAccessor on ${secret}"
  gcloud secrets add-iam-policy-binding "${secret}" \
    --project="${PROJECT}" \
    --member="serviceAccount:${RUNTIME_SA_EMAIL}" \
    --role="roles/secretmanager.secretAccessor"
done

cat <<EOF

==============================================================================
Secret Manager bootstrap complete.

Secrets created (or new version added) — bound to ${RUNTIME_SA_EMAIL}:
$(printf '  %s\n' "${SECRETS[@]}")

Verify with:
  gcloud secrets list --project=${PROJECT}
  gcloud secrets get-iam-policy phoenix-api-key --project=${PROJECT}
==============================================================================
EOF
