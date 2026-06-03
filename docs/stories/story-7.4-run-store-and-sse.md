# Story — Zustand run-store + SSE hook + /api/stream proxy + api-client

**ID:** story-7.4-run-store-and-sse
**Epic:** Epic 7 — chaoslab-web frontend
**Depends on:** story-7.1-nextjs-scaffold, story-7.3-env-and-dockerfile
**Estimate:** ~2h
**Status:** PENDING
**tags:** [frontend, p0, ui]

---

## User story

**As a** coding agent wiring the frontend to the chaoslab-agent backend
**I want to** ship the cross-component state layer (Zustand `run-store`), the SSE hook (`useTraceStream`), the `/api/stream` route handler (proxying chaoslab-agent's `/stream`), and a typed `api-client` wrapping fetch calls to chaoslab-agent
**So that** every visual component (AttackMatrix, ResilienceCurve, AgentPipeline, ReceiptCard) reads from a single source of truth, live trace updates from Phoenix arrive in the UI in real time during the demo, and the SSE proxy isolates the frontend from backend URL changes

---

## File modification map

Exact files the coding agent creates or modifies for this story:

- `apps/chaoslab-web/stores/run-store.ts` — NEW — Zustand v5 store per `best-practices/04 §6`. State: `runId: string | null`, `state: 'idle' | 'baseline' | 'attacking' | 'judging' | 'patching' | 'reattacking' | 'complete'`, `cells: AttackCell[]`, `resilienceCurve: ResiliencePoint[]`, `patchX: number | null`, `recipe: HardeningRecipeSummary | null`, `activeAgent: AgentId | null`, `phase: PhaseLabel`, error state. Actions: `setRun(id)`, `setState(s)`, `updateCells(cells)`, `pushPoint(point)`, `setPatchX(x)`, `setRecipe(r)`, `setActiveAgent(a)`, `reset()`. Type-only exports in this file for `AttackCell`, `ResiliencePoint`, `AgentId`, `PhaseLabel`. ≤220 LOC.
- `apps/chaoslab-web/lib/use-trace-stream.ts` — NEW — Client hook per `best-practices/04 §7`. `useTraceStream(runId)`. Opens `new EventSource('/api/stream?runId=' + runId)`. Subscribes to events: `cell-update`, `point`, `phase`, `patch`, `recipe`, `active-agent`, `error`, `done`. Each event handler calls the matching Zustand action. On unmount or `done`, closes EventSource. Returns `{ connected: boolean, error: string | null }`. Marked `'use client'`. ≤150 LOC.
- `apps/chaoslab-web/app/api/stream/route.ts` — NEW — Next.js route handler with `export const dynamic = 'force-dynamic'`. GET handler proxies `${env.AGENT_BACKEND_URL}/stream?runId=...` upstream, pipes the ReadableStream verbatim to the client. Sets headers `Content-Type: text/event-stream`, `Cache-Control: no-cache`, `Connection: keep-alive`. Handles upstream failure → closes stream with `event: error\ndata: ...\n\n`. ≤120 LOC.
- `apps/chaoslab-web/app/api/run/route.ts` — NEW — POST handler. Forwards POST body to `${env.AGENT_BACKEND_URL}/run`, returns the JSON `{ runId }`. Used by `/attack` route to kick off a run before opening SSE. ≤60 LOC.
- `apps/chaoslab-web/lib/api-client.ts` — NEW — Typed fetch wrapper. `startRun(opts: StartRunRequest): Promise<{ runId: string }>`, `getReplayData(): Promise<ReplayPayload>`, `getHealth(): Promise<{ ok: boolean }>`. Uses `env.AGENT_BACKEND_URL` from server, falls back to `/api/run` etc. when called from client. Pure types — no React. ≤150 LOC.
- `apps/chaoslab-web/lib/types.ts` — NEW — Shared TS types: `AttackCell`, `ResiliencePoint`, `AgentId`, `PhaseLabel`, `HardeningRecipeSummary`, `StartRunRequest`, `ReplayPayload`, SSE event-data shapes. Single source-of-truth, all type-only exports. ≤120 LOC.
- `apps/chaoslab-web/tests/unit/run-store.test.ts` — NEW — Vitest unit tests covering store actions: `setRun`, `updateCells`, `pushPoint`, `setPatchX`, `reset`. ≥6 test cases.
- `apps/chaoslab-web/tests/unit/use-trace-stream.test.ts` — NEW — Vitest test of `useTraceStream` using a mocked EventSource. Verifies that emitting `cell-update` triggers `updateCells` in the store. ≥4 test cases.
- `apps/chaoslab-web/package.json` — UPDATE — add `zustand`, devDeps for `vitest`, `@testing-library/react`, `@testing-library/jest-dom`, `jsdom`, `eventsource` (polyfill for tests)
- `apps/chaoslab-web/vitest.config.ts` — NEW — Vitest config: jsdom env, `setupFiles: ['./tests/setup.ts']`, `globals: true`
- `apps/chaoslab-web/tests/setup.ts` — NEW — imports `@testing-library/jest-dom/vitest`, sets up `global.EventSource` polyfill

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given stores/run-store.ts has been written
When `grep -E "import\s*\{\s*create\s*\}\s*from\s*['\"]zustand['\"]" apps/chaoslab-web/stores/run-store.ts` runs
Then exit code is 0

Given the run-store exposes the required actions
When `grep -cE "(setRun|setState|updateCells|pushPoint|setPatchX|setRecipe|reset):" apps/chaoslab-web/stores/run-store.ts` runs
Then output is ≥ 7

Given use-trace-stream.ts has been written
When `grep -E "'use client'" apps/chaoslab-web/lib/use-trace-stream.ts` runs
Then exit code is 0

Given use-trace-stream.ts subscribes to cell-update
When `grep -E "addEventListener\(\s*['\"]cell-update['\"]" apps/chaoslab-web/lib/use-trace-stream.ts` runs
Then exit code is 0

Given the SSE route exists
When `grep -E "Content-Type.*text/event-stream" apps/chaoslab-web/app/api/stream/route.ts` runs
Then exit code is 0

Given the SSE route forwards to AGENT_BACKEND_URL
When `grep -E "AGENT_BACKEND_URL" apps/chaoslab-web/app/api/stream/route.ts` runs
Then exit code is 0

Given Vitest is configured and tests are written
When `pnpm --filter chaoslab-web exec vitest run` runs
Then exit code is 0
And `pnpm --filter chaoslab-web exec vitest run --reporter=verbose 2>&1 | grep -cE "✓|PASS"` is ≥ 10

Given the SSE endpoint stub exists and a chaoslab-agent stub returns text/event-stream
When a test client sends a GET to /api/stream?runId=abc and the upstream emits `event: cell-update\ndata: [{...}]\n\n`
Then the EventSource client receives a `cell-update` event AND the run-store action `updateCells` is invoked AND `useRunStore.getState().cells.length` matches the dispatched payload

Given build succeeds
When `pnpm --filter chaoslab-web build` runs
Then exit code is 0
And `pnpm --filter chaoslab-web exec tsc --noEmit` exits 0
```

---

## Shell verification

The coding agent runs this to confirm the story is done before opening a PR:

```bash
set -e
cd /Users/abu/dev/hackathon/rapid-agents

# Files exist
test -f apps/chaoslab-web/stores/run-store.ts
test -f apps/chaoslab-web/lib/use-trace-stream.ts
test -f apps/chaoslab-web/app/api/stream/route.ts
test -f apps/chaoslab-web/app/api/run/route.ts
test -f apps/chaoslab-web/lib/api-client.ts
test -f apps/chaoslab-web/lib/types.ts
test -f apps/chaoslab-web/vitest.config.ts

# Zustand wired
grep -E "import\s*\{\s*create\s*\}\s*from\s*['\"]zustand['\"]" apps/chaoslab-web/stores/run-store.ts
test "$(grep -cE '(setRun|setState|updateCells|pushPoint|setPatchX|setRecipe|reset):' apps/chaoslab-web/stores/run-store.ts)" -ge 7

# SSE hook is client + subscribes to cell-update
grep -E "'use client'" apps/chaoslab-web/lib/use-trace-stream.ts
grep -E "addEventListener\(\s*['\"]cell-update['\"]" apps/chaoslab-web/lib/use-trace-stream.ts

# SSE route shape
grep -E "Content-Type.*text/event-stream" apps/chaoslab-web/app/api/stream/route.ts
grep -E "AGENT_BACKEND_URL" apps/chaoslab-web/app/api/stream/route.ts
grep -E "force-dynamic" apps/chaoslab-web/app/api/stream/route.ts

# Tests pass with ≥10 assertions
pnpm --filter chaoslab-web exec vitest run
test "$(pnpm --filter chaoslab-web exec vitest run --reporter=verbose 2>&1 | grep -cE '✓|PASS')" -ge 10

# Build + typecheck
pnpm --filter chaoslab-web exec tsc --noEmit
AGENT_BACKEND_URL=http://localhost:8001 pnpm --filter chaoslab-web build

# 400-line guard
python3 scripts/check_max_lines.py --strict apps/chaoslab-web/stores apps/chaoslab-web/lib apps/chaoslab-web/app/api

echo "story-7.4 verification: PASS"
```

---

## Notes for coding agent

- The Zustand store is THE single source of truth for `/attack` and `/replay` routes. Components NEVER hold their own copies of `cells` / `resilienceCurve` — they subscribe via selector hooks.
- Use Zustand v5 selector pattern with `useShallow` where needed to avoid unnecessary re-renders: `const cells = useRunStore(useShallow((s) => s.cells))`.
- Critical: the SSE route MUST set `export const dynamic = 'force-dynamic'` or Next.js will try to cache the response.
- The SSE proxy is a STREAM passthrough — DO NOT buffer the upstream response. Use `ReadableStream` + `reader.read()` loop per `best-practices/04 §7`. Buffering kills the demo's perceived liveness.
- Event types emitted by chaoslab-agent's `/stream` (locked contract with backend, owned by Epic 4):
  - `cell-update`: `AttackCell[]` (incremental matrix updates)
  - `point`: `ResiliencePoint` (single point appended to curve)
  - `phase`: `{ phase: PhaseLabel }` (state transitions)
  - `patch`: `{ patchX: number }` (PATCH line fires)
  - `recipe`: `HardeningRecipeSummary` (post-patch metadata)
  - `active-agent`: `{ agent: AgentId }` (pipeline glow)
  - `error`: `{ message: string }`
  - `done`: `{}` (close stream)
- For tests, use Vitest's `vi.fn()` to mock `EventSource`. There's no jsdom EventSource — install `eventsource` polyfill and assign `global.EventSource = require('eventsource')` in `tests/setup.ts`. Alternatively, hand-roll a class with `addEventListener`, `dispatchEvent`, `close`.
- The `/api/run` POST handler is the kickoff path. It calls `AGENT_BACKEND_URL/run`, returns `{ runId }`. The `/attack` page (story-7.11) POSTs to this then opens the EventSource.
- `lib/api-client.ts` has DUAL CONTEXTS: callable from server components (uses `env.AGENT_BACKEND_URL`) AND from client (proxies through `/api/run` or `/api/stream`). Branch on `typeof window === 'undefined'`. Document the pattern with a comment.
- All event names match what Epic 4's `chaoslab-agent` emits — coordinate with story-4.1 (the `chaoslab-agent` `/stream` endpoint) by including this contract in the story-4.1 spec OR in a shared types package. For now, mirror the event names exactly.
- The run-store reset() action is called on `/attack` route mount + before kickoff to clear any stale state from prior runs. Critical for the demo replay path.
- File sizes: run-store.ts is the largest (≤220 LOC); split into `run-store.ts` + `run-store-actions.ts` if it crosses 250.
- DO NOT add TanStack Query here — for SSE-streamed state, Zustand is the right tool. TanStack Query is for cached fetches (e.g., `getReplayData()` in story-7.10).
