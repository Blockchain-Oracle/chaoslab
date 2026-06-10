# Story 9.4 — Firebase Authentication: gated product surfaces + owner-scoped data

**Epic:** Epic 9 — product surfaces real
**Status:** IN PROGRESS
**Depends on:** story-9.2-web-real-wiring

## Why

The web proxy's POST/PATCH routes are open to the internet — the one HIGH
security finding deliberately deferred to this story. Decision locked with
Abu 2026-06-10: auth is IN, plug-and-play. Firebase Auth (Identity Platform)
won the research verdict: zero DB, GCP-native, free to 50k MAU, and the
FastAPI side verifies tokens with `google-auth` already in our tree.

Setup state (verified live 2026-06-10): Identity Platform is initialized on
`project-9105c0b4-dfc1-4ee7-b22`, **email/password sign-in enabled**, web app
"Phoenix Audit Web" exists (API key live), authorized domains include
`localhost` + the Cloud Run web URL. Google provider needs one console
toggle (personal account — no org — so the OAuth client cannot be created
headlessly); the UI ships with the Google button wired but email/password is
the path that must work end-to-end NOW.

## BDD acceptance criteria

1. **Route gating (web).** Next.js 16 `proxy.ts` runs
   `next-firebase-auth-edge` `authMiddleware`: `/`, `/replay`, `/login`,
   `/api/health`, static assets stay public; `/audits`, `/agents`,
   `/monitoring`, `/settings`, `/new`, `/run/*`, `/report/*`, `/recipe/*`
   and `/api/agent/*` redirect (pages) or 401 (API) without a valid session
   cookie.
2. **Login surface.** `/login` offers email/password sign-in + sign-up
   (works today) and a Google sign-in button (activates with the console
   toggle; failure shows the standard visible notice, never a silent no-op).
   Session = signed, httpOnly cookie minted by the middleware login path;
   logout clears it.
3. **Proxy forwards identity.** `app/api/agent/[...path]/route.ts` reads the
   verified token via `getTokens` and adds `X-Firebase-Id-Token: <idToken>`
   to the upstream request. The existing GCP OIDC `Authorization` header
   (Cloud Run ingress auth) is unchanged. No cookie forwarding upstream.
4. **Backend verifies, fail-closed.** FastAPI dependency `require_user`
   verifies `X-Firebase-Id-Token` as a Firebase ID token (audience =
   project id) off the event loop with cached Google certs. Missing/invalid
   token → 401. Misconfigured verification (missing project id env) → 503
   naming the env var — mirrors the scheduler-tick OIDC pattern, never open.
5. **Owner stamping + scoping.** `POST /run`, `POST /agents`,
   `POST/PATCH /schedules` stamp `owner_uid` from the verified token's
   `sub`. `GET /runs`, `GET /agents`, `GET /schedules` return only the
   caller's records (`owner_uid` match; legacy records with
   `owner_uid=None` stay visible — pre-auth data must not vanish from the
   registry). **Writes require exact ownership** (PR-review amendment
   2026-06-10): legacy ownerless records are readable but immutable via the
   API — sign-ups are open to the internet, so `owner_uid=None` must not
   mean world-writable. `/internal/scheduler-tick` keeps its own OIDC gate
   (no user); scheduled runs inherit `owner_uid` from their schedule.
6. **SSE stays alive.** `/api/agent/stream` works with the session cookie —
   EventSource cannot set headers, so gating happens at the proxy.
7. **Config + deploy.** `NEXT_PUBLIC_FIREBASE_*` (api key, auth domain,
   project id) baked as build args; `cookie-signature-keys` secret in
   Secret Manager; `staging-deploy.yaml` web matrix updated. Server-side
   verification uses ADC on Cloud Run (no service-account key files; if the
   library demands explicit credentials locally, dev uses emulator/env —
   never a committed key).
8. Unit tests cover: middleware public/private matrix (config-level), proxy
   identity-header attach + cookie stripping, backend 401/403/503 paths,
   owner stamping on create, owner filter on list, legacy-None visibility,
   tick unaffected.

## File map

- `apps/phoenix-audit-web/proxy.ts` (new) — authMiddleware config
- `apps/phoenix-audit-web/lib/auth/{config.ts,client.ts}` (new) — firebase
  client init + server config (env-driven)
- `apps/phoenix-audit-web/app/login/page.tsx` + client form (new)
- `apps/phoenix-audit-web/app/api/agent/[...path]/route.ts` — attach
  `X-Firebase-Id-Token`
- `apps/phoenix-audit-web/components/` — header user menu (sign out)
- `src/phoenix_audit_agent/api/auth.py` (new) — `require_user` dependency
- `src/phoenix_audit_agent/api/{runs,agents,schedules}.py` + `main.py` —
  wire dependency, stamp + filter by `owner_uid`
- `src/phoenix_audit_agent/storage/*` — owner filter in list queries
- `.github/workflows/staging-deploy.yaml`, `apps/phoenix-audit-web/Dockerfile`
- tests: `apps/phoenix-audit-web/tests/{proxy-identity,auth-gating}.test.ts`,
  `tests/unit/api/test_auth_dependency.py`, extensions to
  `test_main.py` / `test_schedules_api.py` fakes
