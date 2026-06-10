#!/usr/bin/env bash
# One-time Cloud Scheduler bootstrap for continuous monitoring (story-9.3).
# A single job ticks POST /internal/scheduler-tick every 15 minutes with an
# OIDC token signed by the deploy SA; the endpoint verifies audience + caller
# and fails CLOSED when unconfigured.
set -euo pipefail

: "${PROJECT:?must set PROJECT (GCP project id)}"
REGION="${REGION:-us-central1}"
# Legacy identity name — see CLAUDE.md (kept through the phoenix-audit rename).
DEPLOY_SA="${DEPLOY_SA:-chaoslab-deploy}"
DEPLOY_SA_EMAIL="${DEPLOY_SA}@${PROJECT}.iam.gserviceaccount.com"

echo "==> Enabling Cloud Scheduler API"
gcloud services enable cloudscheduler.googleapis.com --project="${PROJECT}"

AGENT_URL=$(gcloud run services describe phoenix-audit-agent \
  --region="${REGION}" --project="${PROJECT}" --format='value(status.url)')
[ -n "${AGENT_URL}" ] || { echo "phoenix-audit-agent service not found — deploy it first"; exit 1; }

echo "==> Creating scheduler job phoenix-audit-tick -> ${AGENT_URL}/internal/scheduler-tick"
# Existence-check instead of error suppression — a swallowed stderr once
# masked a real create failure as "already exists".
if gcloud scheduler jobs describe phoenix-audit-tick \
    --project="${PROJECT}" --location="${REGION}" >/dev/null 2>&1; then
  echo "  -> job already exists, continuing"
else
  gcloud scheduler jobs create http phoenix-audit-tick \
    --project="${PROJECT}" \
    --location="${REGION}" \
    --schedule="*/15 * * * *" \
    --uri="${AGENT_URL}/internal/scheduler-tick" \
    --http-method=POST \
    --oidc-service-account-email="${DEPLOY_SA_EMAIL}" \
    --oidc-token-audience="${AGENT_URL}" \
    --attempt-deadline=120s
fi

echo "==> Done. The agent service must run with:"
echo "    SERVICE_BASE_URL=${AGENT_URL}"
echo "    SCHEDULER_INVOKER_EMAIL=${DEPLOY_SA_EMAIL}"
echo "    (staging-deploy.yaml resolves both at deploy time)"
