# Story — /replay canonical 22-second autoplay route

**ID:** story-7.10-replay-route
**Epic:** Epic 7 — chaoslab-web frontend
**Depends on:** story-7.5-attack-matrix, story-7.6-resilience-curve, story-7.7-agent-pipeline, story-7.8-receipt-card
**Estimate:** ~2h
**Status:** PENDING
**tags:** [frontend, p0, ui]

---

## User story

**As a** judge wanting fast gratification before committing 3 minutes to the live demo
**I want to** click /replay and watch a canonical 22-second autoplay run that transitions through all 7 phases ending in the receipt card
**So that** ChaosLab has a deterministic, no-backend-dependency fallback that always works — the safety net if the live agent backend is slow, mid-deploy, or rate-limited during the judging window

---

## File modification map

Exact files the coding agent creates or modifies for this story:

- `apps/chaoslab-web/app/(demo)/replay/page.tsx` — NEW — Server component. Fetches canonical demo data from `${env.AGENT_BACKEND_URL}/replay-data` via `lib/api-client.ts`. On fetch failure, falls back to inline-imported `lib/replay-fixture.ts`. Passes the data to a client wrapper `<ReplayOrchestrator />` for autoplay. ≤80 LOC.
- `apps/chaoslab-web/app/(demo)/replay/replay-orchestrator.tsx` — NEW — Client component. Receives canonical `ReplayPayload`. Uses `useEffect` + `setTimeout` to step through scripted phases (timeline below). Pushes updates into `useRunStore`. Renders `<AttackMatrix>` + `<ResilienceCurve>` + `<AgentPipeline>` + conditionally `<ReceiptCard>` based on store state. data-testid="replay-orchestrator". ≤250 LOC.
- `apps/chaoslab-web/lib/replay-fixture.ts` — NEW — Static fallback fixture (the same canonical run hardcoded, in case backend is unreachable). Exports `REPLAY_FIXTURE: ReplayPayload` with 25 attack cells, 25 reattack cells, resilience curve points, patchX, recipe summary. ≤180 LOC.
- `apps/chaoslab-web/lib/replay-timeline.ts` — NEW — Pure scripted timeline: array of `{ at: number (ms), phase: PhaseLabel, action: (store, payload) => void }`. Total runtime ≤22s. Exports `REPLAY_STEPS`. ≤150 LOC.
- `apps/chaoslab-web/app/(demo)/layout.tsx` — NEW — minimal layout for demo route group: bare header (logo + state pill), no footer (per ux-spec §"Inner-route chrome"). ≤60 LOC.
- `apps/chaoslab-web/app/_components/state-pill.tsx` — NEW — Client component. Subscribes to `useRunStore((s) => s.state)`. Renders a small pill with current-agent-color background and the phase label. Smooth color transitions. ≤80 LOC.
- `apps/chaoslab-web/tests/e2e/replay.spec.ts` — NEW — Playwright test. Loads `/replay`, waits up to 25s, asserts phase transitions through `idle → attacking → patching → reattacking → complete`, asserts `[data-testid="receipt-card"]` is visible in final state. Screenshot to `screenshots/baseline/replay-complete.png`. ≥3 test cases.

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given the /replay route file exists and exports a default component
When `pnpm build` runs
Then exit code is 0
And the build manifest references the /replay route

Given a dev server is running and chaoslab-agent is unreachable (or AGENT_BACKEND_URL points to an unreachable host)
When the client navigates to /replay
Then the page still renders without throwing
And it uses REPLAY_FIXTURE for data
And the autoplay starts

Given a Playwright test navigates to /replay
When the test waits 25 seconds
Then within that window the run-store state transitions through "idle", "attacking", "patching", "reattacking", "complete"
And at the final state, `[data-testid="receipt-card"]` is visible in the DOM
And `[data-testid="attack-matrix"]` is visible with 25 cells
And `[data-testid="resilience-curve"]` is visible with the patch marker

Given the full autoplay completes
When `useRunStore.getState().state` is read at the end
Then it equals "complete"

Given the replay completes
When the document is screenshotted
Then a screenshot is saved at screenshots/baseline/replay-complete.png

Given the timeline ms values are summed
When the total is computed
Then the total runtime is ≤ 22000ms (22 seconds for fast gratification per the user story)

Given Playwright runs the e2e suite for /replay
When the test executes
Then exit code is 0
And ≥3 test cases pass
```

---

## Shell verification

The coding agent runs this to confirm the story is done before opening a PR:

```bash
set -e
cd /Users/abu/dev/hackathon/rapid-agents

# Files exist
test -f apps/chaoslab-web/app/\(demo\)/replay/page.tsx
test -f apps/chaoslab-web/app/\(demo\)/replay/replay-orchestrator.tsx
test -f apps/chaoslab-web/app/\(demo\)/layout.tsx
test -f apps/chaoslab-web/lib/replay-fixture.ts
test -f apps/chaoslab-web/lib/replay-timeline.ts
test -f apps/chaoslab-web/app/_components/state-pill.tsx
test -f apps/chaoslab-web/tests/e2e/replay.spec.ts

# Server vs client split correct
head -5 apps/chaoslab-web/app/\(demo\)/replay/replay-orchestrator.tsx | grep -E "'use client'"
! head -5 apps/chaoslab-web/app/\(demo\)/replay/page.tsx | grep -q "'use client'"

# 4 hero components imported by orchestrator
grep -E "AttackMatrix" apps/chaoslab-web/app/\(demo\)/replay/replay-orchestrator.tsx
grep -E "ResilienceCurve" apps/chaoslab-web/app/\(demo\)/replay/replay-orchestrator.tsx
grep -E "AgentPipeline" apps/chaoslab-web/app/\(demo\)/replay/replay-orchestrator.tsx
grep -E "ReceiptCard" apps/chaoslab-web/app/\(demo\)/replay/replay-orchestrator.tsx

# Fixture has 25 cells + a recipe + curve points
grep -cE "idx:\s*[0-9]+" apps/chaoslab-web/lib/replay-fixture.ts | awk '{exit ($1>=25?0:1)}'

# Timeline runtime ≤ 22 seconds (heuristic: max `at` value)
python3 -c "import re,sys; src=open('apps/chaoslab-web/lib/replay-timeline.ts').read(); ats=[int(m) for m in re.findall(r'at:\s*(\d+)', src)]; print('max at:', max(ats) if ats else 0); sys.exit(0 if max(ats)<=22000 else 1)"

# Build clean
AGENT_BACKEND_URL=http://localhost:8001 pnpm --filter chaoslab-web build

# Playwright /replay test (boots dev server via playwright.config webServer)
pnpm --filter chaoslab-web exec playwright test apps/chaoslab-web/tests/e2e/replay.spec.ts
test "$(pnpm --filter chaoslab-web exec playwright test apps/chaoslab-web/tests/e2e/replay.spec.ts --reporter=list 2>&1 | grep -cE 'passed')" -ge 1

# 400-line guard
test "$(grep -cvE '^\s*(//|$)' apps/chaoslab-web/app/\(demo\)/replay/replay-orchestrator.tsx)" -le 250
test "$(grep -cvE '^\s*(//|$)' apps/chaoslab-web/lib/replay-fixture.ts)" -le 180
test "$(grep -cvE '^\s*(//|$)' apps/chaoslab-web/lib/replay-timeline.ts)" -le 150

echo "story-7.10 verification: PASS"
```

---

## Notes for coding agent

- `/replay` is the FALLBACK demo path. It MUST work without backend. The static fixture lives in `lib/replay-fixture.ts` and is always available.
- Timeline budget (≤22s total) — scripted phases:
  - 0ms: phase=idle (initial state)
  - 500ms: phase=baseline, activeAgent=injector, 1 baseline point
  - 1500ms: phase=attacking, activeAgent=injector, push cells one at a time
  - Per cell: ~280ms delay (25 cells * 280ms ≈ 7s), each `updateCells` push extends the matrix + appends an attack point
  - 8500ms: phase=judging, activeAgent=judge, slight purple outline on cells
  - 9500ms: phase=patching, activeAgent=patcher, patch badge appears
  - 10000ms: phase=reattacking, activeAgent=injector, `setPatchX(...)` fires
  - Per re-attack cell: ~280ms delay (cells flip via the phase change re-mounting them with new pass/fail data; 25 * 280ms ≈ 7s)
  - 18000ms: phase=complete, `setRecipe(recipe)`, store transitions to complete
  - 19000ms: ReceiptCard visible
  - Final state held until user navigates away
- Implementation pattern in `replay-orchestrator.tsx`:
  ```tsx
  useEffect(() => {
    runStore.reset()
    const timeouts: number[] = []
    for (const step of REPLAY_STEPS) {
      timeouts.push(window.setTimeout(() => step.action(runStore, payload), step.at))
    }
    return () => timeouts.forEach(window.clearTimeout)
  }, [])
  ```
- The static fixture is 25 cells (15 fail / 10 pass for attack; 22 pass / 3 fail for reattack). Pre-computed resilience curve points. Recipe with realistic `recipe_id`, `cost_usd: 0.34`, `duration_seconds: 167`, `baselinePassRate: 0.96`, `postPatchPassRate: 0.92`.
- The `(demo)` route group shares `layout.tsx` with `/attack` — both get the bare header + state pill, no footer (maximum vertical real estate for the hero visual per ux-spec).
- State pill subscribes to `useRunStore((s) => s.state)` and shows the current phase. Color changes via static `PHASE_BG: { idle: 'bg-text-muted', attacking: 'bg-agent-injector', judging: 'bg-agent-judge', patching: 'bg-agent-patcher', reattacking: 'bg-agent-injector', complete: 'bg-pass-green' }` lookup map.
- The optional backend fetch (`/replay-data` endpoint on chaoslab-agent) is for fresh data when available. It's a nice-to-have. The fixture is canonical. If the agent endpoint doesn't exist yet (i.e., backend Epic 6 hasn't shipped that endpoint), the static fixture is the source of truth — that's fine.
- Wrap the page in a try/catch around the api-client call: `try { data = await getReplayData() } catch { data = REPLAY_FIXTURE }`. Server component, so this runs on the server during SSR.
- This route has NO live SSE. All data is pre-known. The `useTraceStream` hook is NOT used here.
- Reduced motion: the entire timeline still plays at the same duration, but individual component animations gracefully degrade per their `useReducedMotion()` checks. Acceptable.
- Total LOC budget: orchestrator ≤250, fixture ≤180, timeline ≤150. If orchestrator crosses 250, extract the `useEffect` setup into a custom hook `useReplayPlayback` in `lib/use-replay-playback.ts`.
- The Playwright test uses `await page.waitForFunction(() => window.__chaoslab_state === 'complete', { timeout: 25000 })`. To make this work, expose `window.__chaoslab_state` from the orchestrator OR use `await expect(page.locator('[data-testid="receipt-card"]')).toBeVisible({ timeout: 25000 })`.
- Route group folder name is `(demo)` (parentheses, then "demo") — Next.js convention for organizing routes without affecting URL.
