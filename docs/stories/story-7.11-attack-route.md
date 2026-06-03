# Story — /attack live attack route + SSE + cascade-flip orchestration

**ID:** story-7.11-attack-route
**Epic:** Epic 7 — chaoslab-web frontend
**Depends on:** story-7.5-attack-matrix, story-7.6-resilience-curve, story-7.7-agent-pipeline, story-7.8-receipt-card, story-7.4-run-store-and-sse
**Estimate:** ~2h
**Status:** PENDING
**tags:** [frontend, p0, ui]

---

## User story

**As a** judge watching the wow demo
**I want to** open /attack, see the live 90-180s run play out streaming real Phoenix traces, and at 1:50 watch the Attack Matrix cells cascade-flip red → green while the Resilience Curve jumps from 40% to 92%
**So that** the entire ChaosLab story — "same agent, same attacks, completely different outcome after one hardening loop" — lands in one held frame at 2:15 (the Devpost cover screenshot)

---

## File modification map

Exact files the coding agent creates or modifies for this story:

- `apps/chaoslab-web/app/(demo)/attack/page.tsx` — NEW — Client component (uses `useRunStore` + `useTraceStream`). On mount: calls `useRunStore.reset()`, POSTs to `/api/run`, gets `runId`, opens SSE via `useTraceStream(runId)`. Renders the 4 hero components (`<AttackMatrix>` + `<ResilienceCurve>` + `<AgentPipeline>` + conditionally `<ReceiptCard>`). Orchestrates the timeline per ux-spec §"Behavior (timed for the 3-min demo)" — cascade-flip is driven by the `phase` prop on `<AttackMatrix>` transitioning to `reattacking`. data-testid="attack-route". ≤350 LOC (max — close to limit; helpers extracted below).
- `apps/chaoslab-web/lib/use-attack-run.ts` — NEW — Client hook extracting the run-kickoff side effects (POST /api/run, retry on 503, cleanup on unmount). Exports `useAttackRun()` returning `{ runId, status, error }`. Helps keep `attack/page.tsx` under 350 LOC. ≤120 LOC.
- `apps/chaoslab-web/lib/use-phase-derived-agent.ts` — NEW — Client hook mapping `phase` → `activeAgent` for the AgentPipeline. Pure mapping helper. ≤40 LOC.
- `apps/chaoslab-web/app/(demo)/attack/attack-error-state.tsx` — NEW — Client component shown when SSE fails or backend is unreachable. Friendly retry UI. ≤80 LOC.
- `apps/chaoslab-web/tests/e2e/attack.spec.ts` — NEW — Playwright e2e against a running backend (or a Playwright route handler mocking `/api/run` + `/api/stream`). ≥4 test cases: (1) /attack loads and POSTs to /api/run; (2) within 3 min the page transitions through ≥7 phases; (3) at the reattacking phase, the matrix cells are mostly green; (4) ReceiptCard renders at the end; (5) cascade-flip visual: screenshot regression vs `screenshots/baseline/attack-cascade-flip.png`.

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given the /attack route file exists
When `pnpm build` runs
Then exit code is 0
And the build manifest references the /attack route

Given a dev server is running with a live chaoslab-agent backend
When Playwright navigates to /attack
Then within 5 seconds POST /api/run is invoked (visible in network log)
And the EventSource connects to /api/stream?runId=...
And useRunStore.state transitions from "idle" to "baseline"

Given the test continues
When 3 minutes elapse
Then the run-store state has visited at least 7 phase labels in order: idle, baseline, attacking, judging, patching, reattacking, complete

Given the reattacking phase is active
When the AttackMatrix is queried
Then at least 18 of the 25 cells have computed background-color matching --color-pass-green (cascade-flip has occurred)

Given the run completes
When the DOM is queried
Then `[data-testid="receipt-card"]` is visible
And `useRunStore.getState().recipe` is non-null

Given the backend returns 503 on /api/run
When the user navigates to /attack
Then the AttackErrorState component is rendered with a retry button
And no useTraceStream connection is opened

Given prefers-reduced-motion: reduce is active
When the cascade-flip phase fires
Then cells change color instantly (no Framer Motion stagger)
And the resilience curve patch marker appears instantly

Given a Playwright visual regression test with maxDiffPixelRatio=0.02
When the cascade-flip screenshot is captured
Then it matches screenshots/baseline/attack-cascade-flip.png within tolerance

Given Playwright runs the /attack e2e
When the test suite executes
Then exit code is 0
And ≥4 test cases pass
```

---

## Shell verification

The coding agent runs this to confirm the story is done before opening a PR:

```bash
set -e
cd /Users/abu/dev/hackathon/rapid-agents

# Files exist
test -f apps/chaoslab-web/app/\(demo\)/attack/page.tsx
test -f apps/chaoslab-web/lib/use-attack-run.ts
test -f apps/chaoslab-web/lib/use-phase-derived-agent.ts
test -f apps/chaoslab-web/app/\(demo\)/attack/attack-error-state.tsx
test -f apps/chaoslab-web/tests/e2e/attack.spec.ts

# 'use client' on the route
head -5 apps/chaoslab-web/app/\(demo\)/attack/page.tsx | grep -E "'use client'"

# Uses both store + SSE hook
grep -E "useRunStore" apps/chaoslab-web/app/\(demo\)/attack/page.tsx
grep -E "useTraceStream" apps/chaoslab-web/app/\(demo\)/attack/page.tsx

# 4 hero components rendered
grep -E "AttackMatrix" apps/chaoslab-web/app/\(demo\)/attack/page.tsx
grep -E "ResilienceCurve" apps/chaoslab-web/app/\(demo\)/attack/page.tsx
grep -E "AgentPipeline" apps/chaoslab-web/app/\(demo\)/attack/page.tsx
grep -E "ReceiptCard" apps/chaoslab-web/app/\(demo\)/attack/page.tsx

# Calls /api/run on mount
grep -E "/api/run" apps/chaoslab-web/app/\(demo\)/attack/page.tsx apps/chaoslab-web/lib/use-attack-run.ts

# data-testid
grep -E "attack-route" apps/chaoslab-web/app/\(demo\)/attack/page.tsx

# Build clean
AGENT_BACKEND_URL=http://localhost:8001 pnpm --filter chaoslab-web build

# Typecheck
pnpm --filter chaoslab-web exec tsc --noEmit

# Playwright e2e (requires a live or mocked backend)
pnpm --filter chaoslab-web exec playwright test apps/chaoslab-web/tests/e2e/attack.spec.ts
test "$(pnpm --filter chaoslab-web exec playwright test apps/chaoslab-web/tests/e2e/attack.spec.ts --reporter=list 2>&1 | grep -cE 'passed')" -ge 1

# 400-line guard
test "$(grep -cvE '^\s*(//|$)' apps/chaoslab-web/app/\(demo\)/attack/page.tsx)" -le 350
test "$(grep -cvE '^\s*(//|$)' apps/chaoslab-web/lib/use-attack-run.ts)" -le 120

echo "story-7.11 verification: PASS"
```

---

## Notes for coding agent

- This file is at the LOC ceiling. If `page.tsx` approaches 350 LOC, extract helpers aggressively:
  - Run kickoff side effects → `lib/use-attack-run.ts` (already in file map)
  - Phase → activeAgent mapping → `lib/use-phase-derived-agent.ts` (already in file map)
  - Error state UI → `attack-error-state.tsx` (already in file map)
  - If still over: extract the layout (the 4-quadrant arrangement of hero components) into `attack-hero-layout.tsx` (≤120 LOC)
- Page structure:
  1. `useEffect` on mount: reset store, kick off run via `useAttackRun()`
  2. `useTraceStream(runId)` opens SSE — this hook owns the EventSource lifecycle from story-7.4
  3. Read state slice from store: `const { state, cells, resilienceCurve, patchX, recipe, activeAgent } = useRunStore()`
  4. Derive `phase` for the matrix from `state` (1:1 mapping)
  5. Conditional rendering of `<ReceiptCard>` only when `state === 'complete' && recipe`
- The cascade-flip is DRIVEN by the `phase` prop on `<AttackMatrix>` changing from `attacking` to `reattacking`. The matrix component (story-7.5) handles the re-mount via `key={\`${phase}-${idx}\`}`internally. This route just changes the prop value when SSE delivers a`phase`event with`phase: 'reattacking'`.
- POST /api/run payload shape: `{ target: 'naive-customer-support', faults: ['malformed_tool_output', 'prompt_injection', 'context_poisoning', 'latency_spike'], count: 25 }`. Locked with backend story-4.1. Response: `{ runId: string }`.
- SSE connection failure handling: if `useTraceStream` reports an error within 5s of opening, render `<AttackErrorState />` instead of the hero. Show a "Retry" button that re-mounts the page.
- Connection retry pattern: if POST /api/run returns 503, retry with exponential backoff (1s, 2s, 4s), max 3 attempts. After that, show AttackErrorState. Logic lives in `use-attack-run.ts`.
- The state pill in the header (from story-7.10) automatically updates based on `useRunStore`. No extra wiring needed here.
- The `activeAgent` prop for `<AgentPipeline>` is derived from phase via `use-phase-derived-agent.ts`:
  - `baseline | attacking | reattacking` → `injector`
  - `judging` → `judge`
  - `patching` → `patcher`
  - `idle | complete` → `null`
- The PATCH line fires when the SSE delivers a `patch` event with `patchX: number`. The store action `setPatchX(x)` is called by `useTraceStream`. The `<ResilienceCurve>` component (story-7.6) automatically renders the marker when `patchX != null`.
- Performance: the page re-renders on every SSE update. Use `useShallow` from zustand for the store selectors to avoid re-rendering when unrelated slices change. Each hero component reads its own slice.
- Edge case: SSE delivers a `done` event but the recipe is null (backend bug). Don't render an empty ReceiptCard. Gate strictly on `state === 'complete' && recipe != null`. The store reset on mount prevents stale state from a prior run.
- For the visual regression test, run the demo to the cascade-flip moment, wait for stability (use `await page.waitForFunction(() => window.__chaoslab_state === 'reattacking', { timeout: 120000 })`), then `await page.screenshot()`. Compare against `screenshots/baseline/attack-cascade-flip.png` with `maxDiffPixelRatio: 0.02` per `best-practices/04 §14`.
- Reduced-motion: the cells flip instantly, the curve patch marker appears instantly. The route DOES NOT need extra reduced-motion handling — each hero component has its own gating. The route just passes props.
- During the 3-min demo, the page should ideally NEVER show a loading spinner — the SSE stream starts within ~1s of mount and the matrix populates incrementally. If a spinner is needed (per submission checklist §12 "Loading + empty states implemented"), show one ONLY during the 0–1s gap before the first SSE event arrives.
- Total LOC budget for `page.tsx`: ≤350. Hard ceiling. If exceeded, that's a split signal — fail the 400-line check and require splitting before merge.
- Test fixtures for Playwright (when running without a live backend): use Playwright `page.route('/api/run', ...)` to mock the POST response and `page.route('/api/stream', ...)` to mock the SSE stream by returning a pre-recorded `text/event-stream` body with scripted events at scripted intervals.
