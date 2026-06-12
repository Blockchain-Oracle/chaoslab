# Environment variables — master reference

Every env var read anywhere in the repo, grouped by app. The `.env.example` file in each app is the canonical place to copy from; this doc is the lookup table.

## Required at quickstart

The six vars below are the minimum to get past `pnpm dev` + a local audit run. Everything else is for deeper local-stack work or Cloud Run deploy.

| Variable                           | Where to set                                                 | Notes                                                                                  |
| ---------------------------------- | ------------------------------------------------------------ | -------------------------------------------------------------------------------------- |
| `PHOENIX_API_KEY`                  | `apps/target-agent/.env` and `apps/phoenix-audit-agent/.env` | Get from [app.phoenix.arize.com](https://app.phoenix.arize.com) → Settings → API keys. |
| `GEMINI_API_KEY`                   | `apps/phoenix-audit-agent/.env`                              | Get from [aistudio.google.com](https://aistudio.google.com) → Get API key.             |
| `NEXT_PUBLIC_FIREBASE_API_KEY`     | `apps/phoenix-audit-web/.env.local`                          | Firebase console → Project settings → web app SDK config.                              |
| `NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN` | `apps/phoenix-audit-web/.env.local`                          | Usually `<your-firebase-project>.firebaseapp.com`.                                     |
| `NEXT_PUBLIC_FIREBASE_PROJECT_ID`  | `apps/phoenix-audit-web/.env.local`                          | The Firebase / GCP project ID.                                                         |
| `AUTH_COOKIE_SIGNATURE_KEYS`       | `apps/phoenix-audit-web/.env.local`                          | Generate with `echo "$(openssl rand -hex 32),$(openssl rand -hex 32)"`.                |

The full table per app is below.

---

## `apps/phoenix-audit-web/`

The Next.js operator surface. See [`apps/phoenix-audit-web/README.md`](../apps/phoenix-audit-web/README.md) for the Firebase setup walkthrough.

| Variable                           | Required at  | Source                                | Default                 | What it does                                                                                                       |
| ---------------------------------- | ------------ | ------------------------------------- | ----------------------- | ------------------------------------------------------------------------------------------------------------------ |
| `AGENT_URL`                        | dev + deploy | env                                   | `http://localhost:8080` | Base URL of `phoenix-audit-agent`. The `/api/agent/[...path]` proxy uses it to forward IAM-tokened requests.       |
| `NEXT_PUBLIC_FIREBASE_API_KEY`     | dev + deploy | env                                   | none                    | Firebase web-app API key. Public; safe in client bundle.                                                           |
| `NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN` | dev + deploy | env                                   | none                    | Firebase auth domain.                                                                                              |
| `NEXT_PUBLIC_FIREBASE_PROJECT_ID`  | dev + deploy | env                                   | none                    | Firebase / GCP project ID. Read by both the client SDK and `next-firebase-auth-edge` server.                       |
| `AUTH_COOKIE_SIGNATURE_KEYS`       | dev + deploy | env (local) / Secret Manager (deploy) | none                    | Comma-separated cookie signing keys, each ≥32 bytes. Rotated by appending a new key to the front.                  |
| `GOOGLE_CLOUD_PROJECT`             | dev only     | env                                   | none                    | `next-firebase-auth-edge` reads this to resolve the project when there's no metadata server. Cloud Run injects it. |

---

## `apps/phoenix-audit-agent/`

The ADK orchestrator (Injector → Judge → Patcher). The full Pydantic Settings model lives in `apps/phoenix-audit-agent/src/phoenix_audit_agent/config.py`.

| Variable                         | Required at  | Source         | Default                           | What it does                                                                                                                                                                                 |
| -------------------------------- | ------------ | -------------- | --------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `PHOENIX_PROVIDER`               | dev + deploy | env            | `phoenix-audit`                   | Phoenix Cloud workspace identifier. Used by the OTLP exporter URL.                                                                                                                           |
| `PHOENIX_COLLECTOR_ENDPOINT`     | dev + deploy | env            | `http://localhost:6006/v1/traces` | OTLP HTTP endpoint. Switch to `https://app.phoenix.arize.com/s/<space>/v1/traces` for Phoenix Cloud, or leave at localhost for the self-hosted Docker Phoenix in `infra/phoenix-self-host/`. |
| `PHOENIX_API_KEY`                | deploy       | Secret Manager | none                              | Required for Phoenix Cloud; absent for self-hosted.                                                                                                                                          |
| `GEMINI_API_KEY`                 | dev          | env            | none                              | The judge LLM API key. On Cloud Run, replaced by Vertex AI IAM — see ADR-007.                                                                                                                |
| `JUDGE_LLM`                      | dev + deploy | env            | `gemini-3.5-flash`                | The judge model. Locked to Flash for cost discipline. Pro is ~1.33× cost; Flash-Lite is 8-11× cheaper but uncalibrated for our rubrics.                                                      |
| `TARGET_DEFAULT_URL`             | dev          | env            | `http://localhost:8001`           | Demo target URL. The web wizard always lets the operator override.                                                                                                                           |
| `ENVIRONMENT`                    | dev + deploy | env            | `dev`                             | `dev` / `staging` / `prod`. Gates which degradation paths are allowed (e.g. fail-loud on Cloud Run when secrets are missing).                                                                |
| `SERVICE_VERSION`                | dev + deploy | env            | `local`                           | Github SHA at build time. Surfaced in the signed report so a regulator can ask "which version produced this attestation?".                                                                   |
| `RUN_ONLINE_TESTS`               | dev only     | env            | `0`                               | `1` enables `@pytest.mark.online` tests that hit real Gemini / Phoenix Cloud. Default off — they cost money.                                                                                 |
| `GOOGLE_APPLICATION_CREDENTIALS` | dev only     | env            | none                              | Path to a service-account JSON for local GCP access. For most workflows `gcloud auth application-default login` is enough; this is the escape hatch.                                         |
| `GITLAB_TOKEN`                   | optional     | env            | none                              | If set, the Patcher files a hardening-recipe MR on the target repo. See ADR-011 for the hybrid MR-emission contract.                                                                         |

---

## `apps/target-agent/`

The sacrificial customer-support demo bot. The Phoenix bootstrap lives in `apps/target-agent/src/target_agent/observability.py`.

| Variable                         | Required at  | Source                                                     | Default                             | What it does                                                                                                                                                                                                                                               |
| -------------------------------- | ------------ | ---------------------------------------------------------- | ----------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `PHOENIX_API_KEY`                | dev + deploy | env (local) / Secret Manager `phoenix-api-key` (Cloud Run) | none                                | Phoenix Cloud workspace API key. On Cloud Run, leave the env unset and let the Secret Manager fallback resolve under `GCP_PROJECT_ID`.                                                                                                                     |
| `PHOENIX_COLLECTOR_ENDPOINT`     | dev + deploy | env                                                        | `https://app.phoenix.arize.com`     | OTLP HTTP endpoint. Match the Phoenix the orchestrator is talking to.                                                                                                                                                                                      |
| `PHOENIX_PROJECT_NAME`           | dev + deploy | env                                                        | `target-agent`                      | Must match the orchestrator's `--project` flag for the joined-trace evidence chain to work.                                                                                                                                                                |
| `GCP_PROJECT_ID`                 | deploy       | env                                                        | none                                | Used for the Secret Manager fallback. Cloud Run injects it; local dev only needs it if you're testing the Secret Manager path.                                                                                                                             |
| `PUBLIC_URL`                     | deploy       | env                                                        | none                                | The Cloud Run public URL for this service. Without it, the A2A agent card advertises `http://localhost:8001/` regardless of where the container actually binds — the orchestrator dispatches messages to localhost and the audit fails 0/5. See issue #22. |
| `PORT`                           | dev + deploy | env                                                        | `8001` (local) / `8080` (Cloud Run) | A2A server bind port. Cloud Run injects `8080`.                                                                                                                                                                                                            |
| `HOST`                           | dev + deploy | env                                                        | `0.0.0.0`                           | Server bind host.                                                                                                                                                                                                                                          |
| `GOOGLE_APPLICATION_CREDENTIALS` | dev only     | env                                                        | none                                | Local SA JSON for Secret Manager fallback testing.                                                                                                                                                                                                         |

---

## `infra/`

Bootstrap-only env. These are consumed by the shell scripts in `infra/`, not by the running services.

See [`infra/README.md`](../infra/README.md) for the full bootstrap walkthrough.

| Variable                                                | Required at | Source | Default                           | What it does                                                                                            |
| ------------------------------------------------------- | ----------- | ------ | --------------------------------- | ------------------------------------------------------------------------------------------------------- |
| `GCP_PROJECT_ID`                                        | bootstrap   | shell  | none                              | Target GCP project for IAM + Secret Manager + KMS setup.                                                |
| `GITHUB_REPO`                                           | bootstrap   | shell  | none                              | `<owner>/<repo>`. Used by `workload-identity-federation.sh` to bind the WIF provider to your repo only. |
| `KMS_KEYRING` / `KMS_KEY`                               | bootstrap   | shell  | `phoenix-audit` / `report-signer` | The Cloud KMS key version that signs every report. Pre-created so the SA bindings can reference it.     |
| `RESEND_API_KEY`                                        | bootstrap   | shell  | none                              | Provisioned into Secret Manager as `resend-api-key:latest`.                                             |
| `GITLAB_OAUTH_CLIENT_ID` / `GITLAB_OAUTH_CLIENT_SECRET` | bootstrap   | shell  | none                              | Provisioned into Secret Manager as `gitlab-oauth-client-{id,secret}:latest`.                            |

## Self-hosted Phoenix (`infra/phoenix-self-host/`)

If you're running Phoenix locally via Docker (e.g. to keep traces off Phoenix Cloud during development), see [`infra/phoenix-self-host/README.md`](../infra/phoenix-self-host/README.md) for the env it expects (basic auth, persistence path, OTLP port).
