# Story 9.2 — Web wiring: audits / agents / report go real

**Epic:** Epic 9 — product surfaces real
**Status:** IN PROGRESS
**Depends on:** story-9.1-firestore-persistence

## Why

Every product page except the live chamber renders static fixtures. S9.1 gave
the backend a real registry (GET /runs, GET /runs/{id} with fresh signed
artifact URLs, agents CRUD); this story makes the web app read it — sample
data stays, visibly labeled, merged with real runs (locked with Abu
2026-06-10). The deployed agent service is IAM-gated, so the browser cannot
call it directly: a same-origin Next.js proxy mints Cloud Run ID tokens
server-side (also the enforcement point for Firebase auth in story-9.4).

## BDD acceptance criteria

1. **Same-origin proxy.** `/api/agent/<path>` forwards GET/POST to the agent
   service with a metadata-minted ID token on Cloud Run (no token locally),
   allowlisting only known API paths; SSE responses stream unbuffered.
2. **Chamber connects via the proxy** by default (`NEXT_PUBLIC_AGENT_URL`
   still overrides for direct local use).
3. **Audits page** lists REAL runs from `GET /runs` merged with the sample
   world; sample rows carry a visible `SAMPLE` chip; real rows sort by date
   with everything else. Live-API failure renders sample data WITH a visible
   "live registry unavailable" notice — never silently.
4. **Agents page + detail** list real registered agents (incl. the
   `demo-target` seed) merged with labeled sample agents; detail shows the
   agent's real run history (`GET /runs?agent_id=`).
5. **Report page** for a REAL run shows working Download PDF / signed JSON /
   sidecar links from the re-signed URLs (sign failures from
   `artifact_url_errors` render as a retry notice, distinct from absent).
   Sample run ids keep rendering the fixture report.
6. **Deploy:** `AGENT_URL` env on phoenix-audit-web in staging-deploy.yaml.
7. Vitest covers the run/agent mappers + sample-merge ordering + the
   failure-notice path.

## File map

- `lib/server/agent-fetch.ts` (new) — server-side fetch + ID token via
  google-auth-library (Cloud Run detection: `K_SERVICE`)
- `app/api/agent/[...path]/route.ts` (new) — streaming proxy
- `lib/api.ts` (new) — typed fetchers + DTO→UI mappers
- `lib/sample-merge.ts` (new) — sample tagging + merge
- `lib/sse-bridge.ts` — default base `/api/agent`
- `app/audits/page.tsx` → server component + `components/history/audits-client.tsx`
- `app/agents/page.tsx`, `app/agents/[id]/page.tsx` — same split
- `components/artifacts/report-preview.tsx` — real artifact URLs prop
- `.github/workflows/staging-deploy.yaml` — AGENT_URL env
