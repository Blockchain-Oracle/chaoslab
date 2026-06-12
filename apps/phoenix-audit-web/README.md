# phoenix-audit-web

The operator's view of the audit. Next.js 16 + Tailwind 4 + Firebase Authentication. Talks to `phoenix-audit-agent` over `/api/agent/*` — a server-only proxy that mints a GCP ID token per request.

This README covers the local-dev path. For the live deploy + Cloud Run wiring see [`docs/cicd.md`](../../docs/cicd.md).

## Quickstart

```bash
pnpm install
cp .env.example .env.local
# fill in the env vars (table below)
pnpm dev          # http://localhost:3000
```

## Env you need to set

The full env reference for every app lives in [`docs/env-vars.md`](../../docs/env-vars.md). For local dev this is the short list.

| Variable                           | Required at  | What it does                                                                                                                 |
| ---------------------------------- | ------------ | ---------------------------------------------------------------------------------------------------------------------------- |
| `AGENT_URL`                        | dev + deploy | Base URL of `phoenix-audit-agent`. Local default: `http://localhost:8080`.                                                   |
| `NEXT_PUBLIC_FIREBASE_API_KEY`     | dev + deploy | Firebase web-app API key (public, not secret).                                                                               |
| `NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN` | dev + deploy | Firebase auth domain (`<project>.firebaseapp.com`).                                                                          |
| `NEXT_PUBLIC_FIREBASE_PROJECT_ID`  | dev + deploy | The Firebase / GCP project ID.                                                                                               |
| `AUTH_COOKIE_SIGNATURE_KEYS`       | dev + deploy | Comma-separated cookie signing keys, each ≥32 bytes. Generate with `echo "$(openssl rand -hex 32),$(openssl rand -hex 32)"`. |
| `GOOGLE_CLOUD_PROJECT`             | dev only     | next-firebase-auth-edge reads this to resolve the project. Cloud Run injects it; locally you must set it.                    |

## Firebase setup

A four-step walkthrough if you don't already have a project:

1. **Create a Firebase project.** [console.firebase.google.com](https://console.firebase.google.com) → **Add project**. Use an existing GCP project if you have one (recommended — keeps everything in one tenant), or create fresh.
2. **Enable Email/Password sign-in.** In the project: **Authentication → Sign-in method → Email/Password → Enable**.
3. **Register a web app.** Project settings → **Your apps → Web (`</>`)**. Copy the three `NEXT_PUBLIC_FIREBASE_*` values from the SDK config snippet into `.env.local`.
4. **Add `localhost` as an authorized domain.** Authentication → **Settings → Authorized domains → Add `localhost`** (only for local dev; Cloud Run adds the production domain at deploy time).

## Known local-dev limitation: `/api/login` cannot mint sessions

Completing `/api/login` locally needs a custom-token signer. On Cloud Run the runtime service account signs keylessly via `signBlob`; locally there is no metadata server and the org policy `iam.disableServiceAccountKeyCreation` forbids SA keys. The full sign-in round-trip therefore lives on staging (or run the Firebase Auth emulator via `FIREBASE_AUTH_EMULATOR_HOST` for offline UI work).

Everything else works locally — route gating, redirects, error states, backend token verification.

## Tests

```bash
pnpm test           # vitest unit + integration (~286 tests)
pnpm typecheck      # tsc --noEmit
pnpm lint           # eslint
```

Playwright is wired but not yet on CI. Tests live under `tests/`.

## File layout

- `app/` — Next.js App Router pages (`/audits`, `/agents`, `/datasets`, `/monitoring`, `/settings`, `/new`, `/run/[id]`, `/report/[id]`, `/replay`, `/onboarding`, `/docs`).
- `app/api/agent/[...path]/` — the IAM-gated proxy to `phoenix-audit-agent`. EventSource-friendly so SSE streams pass through unbuffered.
- `components/` — UI components organized by surface (`chamber/`, `datasets/`, `report/`, `monitoring/`, `landing/`, etc.).
- `lib/` — pure logic + types, including `sse-bridge.ts` (live audit stream reducer), `phoenix-links.ts`, `cluster-review.ts`.
- `public/brand/` — banner SVGs (light + dark).

## Deploy

See [`docs/cicd.md`](../../docs/cicd.md). The staging deploy fires automatically on push to `main` via `.github/workflows/staging-deploy.yaml`; prod promotes the same image hash via `prod-promote.yaml`.
