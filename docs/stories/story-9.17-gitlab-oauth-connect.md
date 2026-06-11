# story-9.17 — gitlab-oauth-connect: per-user OAuth + review-first MR filing

**Epic:** 9 · **Depends on:** story-9.12 (user-profile — `users/{uid}` blob), story-9.5 (email-summaries — `RunRecord` identity threading precedent)
**Source:** Wave C2 in the unified-finish plan (`~/.claude/plans/there-i-want-you-toasty-ember.md`). Numbered 9.17 — 9.16 is reserved by in-code references to the dataset overwrite-strategy follow-up.
**ADR impact:** amends ADR-011 (auto-emit → opt-in review-first; service token → per-user OAuth). Escalation rule satisfied: this IS Abu's explicit 2026-06-10 instruction ("MR filed after review via a button — never automatic").

## Why

Filing a merge request into a customer's repo is the single most invasive thing Phoenix Audit does — and the current design does it with a SHARED SERVICE TOKEN, configured per-deployment, with no review step. A Director of AI Governance will not point a product at their repo if the product can write to it autonomously with someone else's identity. The architecture fix Abu locked: **per-user OAuth connect** ("Connect GitLab" in settings), and the MR is filed only when a human clicks **"File as GitLab MR"** on a recipe they have reviewed — using THEIR GitLab identity, into THEIR chosen project, and only ADDING files under `phoenix-audit/` (we never read or modify their code).

Discovery (explorer, 2026-06-11): the auto-emit was never wired into the pipeline — `GitLabMREmitter.emit()` (branch+files via python-gitlab, MR via the official MCP per ADR-011) exists complete but disconnected, and `mr_url` already lives on `RunRecord`/`RunCompletion`. So this story is ADDITIVE: build the OAuth connect + the button endpoint that finally invokes the existing emitter with the user's token. The MCP path is untouched — judging credit preserved.

## BDD acceptance criteria

### Connect flow (backend)

- **Given** an authenticated user calls `GET /integrations/gitlab/connect`, **then** the response is a 307 redirect to `https://gitlab.com/oauth/authorize` with `client_id`, `redirect_uri`, `response_type=code`, `scope=api`, a `state` token, and PKCE `code_challenge` + `code_challenge_method=S256`. The `{state → (uid, code_verifier, created_at)}` document is persisted server-side (Firestore `gitlab_oauth_states/{state}`) — the verifier NEVER goes to the browser.
- **Given** the exchange endpoint `GET /integrations/gitlab/exchange?code=…&state=…` is called with a known, unexpired state (TTL 10 min), **then** the code is exchanged (Authlib `AsyncOAuth2Client.fetch_token`, `code_verifier` from the state doc), the GitLab user is fetched (`GET /api/v4/user`), and `users/{uid}.gitlab = {access_token, refresh_token, expires_at, username, gitlab_user_id, connected_at}` is merged. The state doc is DELETED on use (single-use). Response redirects to `{PUBLIC_WEB_URL or web origin}/settings?gitlab=connected`.
- **Given** an unknown / expired / reused `state`, **then** 422 with reason — never a token exchange. **Given** GitLab's token endpoint errors, **then** redirect to `/settings?gitlab=error` (no token persisted, structured log).
- **Given** a connected user calls `GET /integrations/gitlab/status`, **then** `{connected: true, username}` (no tokens in any response, ever). Disconnected ⇒ `{connected: false}`. **Given** `DELETE /integrations/gitlab/connection`, **then** the gitlab blob is removed and status reads disconnected.
- **Given** a stored token with `expires_at` in the past, **when** any GitLab call is needed, **then** the token is refreshed FIRST (Authlib refresh, `update_token` hook) and **the ROTATED pair is persisted before use** — GitLab rotates refresh tokens; losing the new pair kills the connection silently. A refresh failure (revoked upstream) clears `connected` state and surfaces 409 "GitLab connection expired — reconnect".

### Projects + MR filing

- **Given** a connected user calls `GET /integrations/gitlab/projects`, **then** python-gitlab `projects.list(membership=True, min_access_level=30)` runs with THEIR token (`Gitlab(oauth_token=…)`) and returns `[{id, path_with_namespace}]` (30 = Developer, the minimum that can push a branch + open an MR).
- **Given** `POST /runs/{run_id}/gitlab-mr` with body `{project_id}` from the run's owner (sample runs are NOT filable — 422; a judge must not file MRs from shared specimens), a finished run with `recipe_id`, and a connected GitLab account, **then** the EXISTING `GitLabMREmitter` files branch `phoenix-audit/recipe-{recipe_id}` + files via python-gitlab and the MR via the official MCP endpoint (ADR-011 unchanged) — all with the USER's token — and `mr_url` persists onto the run via the existing completion-merge path. Response `{mr_url}`.
- Guards: not connected ⇒ 409; no recipe on the run ⇒ 409; foreign run ⇒ 404 (existence not disclosed); `mr_url` already set ⇒ 409 with the existing URL (idempotency — no duplicate MRs); emitter failure ⇒ 502 with the error class, nothing persisted.

### Web

- **Given** the GitLab redirect lands on `/integrations/gitlab/callback?code=…&state=…` (a Next.js SERVER route, registered in BOTH OAuth-app redirect URIs), **then** it forwards code+state to the backend exchange endpoint server-side (same-origin proxy idiom, session cookie verified) and redirects the browser to the backend's redirect target. The path is added to the auth public-paths list (the OAuth round-trip must survive a cold session) — but the FORWARD only happens with a valid session cookie; otherwise redirect to `/login?redirect=…`.
- Settings §2: the "Configured via the service environment" copy is REPLACED by real connect state — `Connected as @{username}` + Disconnect, or a "Connect GitLab" button → `/api/agent/integrations/gitlab/connect`. Honest error state from `?gitlab=error`.
- Recipe page action row: "File as GitLab MR" button (when signed-in owner + no `mr_url` yet) → project picker (from `/projects`) → POST → success swaps to the existing "GitLab MR ↗" link. Failure shows the backend detail.
- Proxy allowlist adds `integrations/gitlab/connect|status|projects|connection` + `runs/{id}/gitlab-mr`. The EXCHANGE endpoint is NOT proxied (the callback server route calls the agent directly with its identity headers).

### Always

- No tokens in logs, responses, or SSE frames. `extra="ignore"` on `UserProfile` admits the new `gitlab` blob without migration. Existing `gitlab_token` (service env token) stays ONLY as the seed-script fallback, marked internal (per plan).
- Offline tests: respx for GitLab token/user endpoints; python-gitlab + MCP client behind the existing seams; no `@pytest.mark.online`.

## File map

- Settings (`config.py`): `GITLAB_OAUTH_CLIENT_ID: str = ""`, `GITLAB_OAUTH_CLIENT_SECRET: SecretStr | None = None`, `GITLAB_OAUTH_REDIRECT_URI: str = ""` (the web callback URL; empty ⇒ connect endpoints fail closed 503).
- NEW `apps/phoenix-audit-agent/src/phoenix_audit_agent/integrations/__init__.py`, `integrations/gitlab_oauth.py` (Authlib client factory, state-doc store seam, exchange + refresh-with-rotation), `integrations/gitlab_api.py` (python-gitlab with user token: projects list, token-expiry gate).
- NEW `apps/phoenix-audit-agent/src/phoenix_audit_agent/api/integrations.py` — the `/integrations/gitlab/*` router (connect, exchange, status, connection-delete, projects).
- `api/runs.py` (or NEW `api/runs_mr.py` if the 400-line cap threatens): `POST /runs/{run_id}/gitlab-mr`.
- `storage/models.py`: `GitLabConnection` model + `UserProfile.gitlab: GitLabConnection | None`; `storage/gitlab_states.py` (NEW — Firestore state docs + in-memory fake seam mirroring profiles.py).
- `patcher/gitlab_emitter.py` + `patcher/_gitlab_rest_client.py` + `patcher/_gitlab_mcp_client.py`: accept a per-call token override (constructor param threading; service-env token stays the default for the seed script).
- `main.py`: include the integrations router.
- Web: `app/api/integrations/gitlab/callback/route.ts` (NEW server route), `lib/auth/routes.ts` (public path), `app/api/agent/[...path]/route.ts` (allowlist), `app/settings/page.tsx:128-136` (connect state), `components/artifacts/recipe-view.tsx:106-129` (File-MR button + picker), NEW `lib/gitlab-connect.ts` (pure request/state logic per the node-env vitest idiom) + `components/integrations/gitlab-file-mr.tsx`.
- `docs/architecture.md` ADR-011: amend wording (opt-in review-first; user OAuth token; MCP MR call unchanged).
- Tests: `tests/unit/integrations/test_gitlab_oauth.py`, `test_gitlab_api.py`, `tests/unit/api/test_integrations_api.py`, `test_runs_gitlab_mr_api.py`; web `tests/gitlab-connect.test.ts`, allowlist + auth-routes extensions.

## Notes

- GitLab OAuth specifics: authorize `https://gitlab.com/oauth/authorize`, token `https://gitlab.com/oauth/token`. Scope `api` (Developer-level repo writes need it; `write_repository` covers git pushes but NOT the MR REST/MCP call). **Refresh tokens rotate on every refresh** (GitLab 15+ behavior) — the `update_token` hook persists the new pair atomically with `expires_at = token["expires_at"]`.
- python-gitlab does NOT auto-refresh OAuth tokens — `integrations/gitlab_api.py` gates every client construction on `expires_at` (refresh if within 60 s of expiry).
- The OAuth app's registered redirect URIs (created by Abu 2026-06-10): `https://phoenix-audit-web-kkkl7l77da-uc.a.run.app/integrations/gitlab/callback` AND `https://api.phxaudit.xyz/integrations/gitlab/callback`. The web server-route is canonical; the api.phxaudit.xyz one becomes usable post-C3.
- Secrets already in Secret Manager: `gitlab-oauth-client-id`, `gitlab-oauth-client-secret` (runtime-SA bound per plan). Staging deploy workflow needs the two new env bindings + `GITLAB_OAUTH_REDIRECT_URI`.
- State docs carry `created_at` for the 10-min TTL check at read time (no Firestore TTL dependency); expired docs are best-effort deleted on touch.
- `min_access_level=30` (Developer) not 40 (Maintainer): filing an MR needs push + MR rights only — asking for Maintainer-only project lists would hide legitimate targets.
- Per-call token override on the emitter keeps the seed-script/service path compiling — but the BUTTON path always passes the user token; there is no fallback from user OAuth to service token (a fallback would file MRs as the wrong identity — worse than failing).
- Slice-1 review fixes (2026-06-11): refresh failures are CLASSIFIED — transport errors raise `GitLabUnavailableError` (retryable, never clears the pair); only OAuth/parse failures clear-and-disclose. Per-uid asyncio lock serializes concurrent refreshes (process-local) with a re-read-before-clear guard for cross-instance rotation. Firestore state consume is transactional (true single-use). Deploy step for C3/ops: add a Firestore TTL policy on `gitlab_oauth_states.created_at` so abandoned verifiers don't accumulate.
