# Story — <AttackMatrix> 5×5 grid with Framer Motion stagger

**ID:** story-7.5-attack-matrix
**Epic:** Epic 7 — chaoslab-web frontend
**Depends on:** story-7.2-design-tokens, story-7.4-run-store-and-sse
**Estimate:** ~2h
**Status:** PENDING
**tags:** [frontend, p0, ui]

---

## User story

**As a** judge watching the ChaosLab demo
**I want to** see a 5×5 grid of cells flip red one by one during the attack phase, then cascade-flip red → green during the re-attack phase
**So that** the entire "agent fails 60% → agent passes 92% after patch" story lands in 1.5 seconds of motion without a single line of narration

---

## File modification map

Exact files the coding agent creates or modifies for this story:

- `apps/chaoslab-web/app/_components/attack-matrix.tsx` — NEW — Client component per `docs/ux-spec.md` `<AttackMatrix>` contract. Props `{ cells: AttackCell[]; revealedCount: number; phase: PhaseLabel }`. Renders a `<div role="grid" aria-label="Attack results, 25 fault injection runs">` containing 25 `<motion.div>` cells with `data-testid="attack-cell-{idx}"`. Stagger via `transition={{ delay: i * 0.04 }}`. Color-blind safety: each cell has a `✗` (fail) or `✓` (pass) icon overlay inside (e.g., via `aria-label` + visible svg/character) so red/green is not the only signal. Click handler opens `phoenixSpanUrl(cell.spanId)` in new tab (`window.open(url, '_blank', 'noopener')`). `useReducedMotion()` gates stagger. `key={\`${phase}-${cell.idx}\`}`forces re-mount on phase transitions to drive the cascade-flip per`best-practices/04 §5` Approach A. ≤300 LOC.
- `apps/chaoslab-web/app/_components/attack-cell.tsx` — NEW — sub-component (kept separate so attack-matrix.tsx stays ≤300 LOC). Single `<motion.div>` cell with the spring transition, icon overlay, tooltip showing `faultClass`, click handler. ≤100 LOC.
- `apps/chaoslab-web/lib/phoenix-links.ts` — NEW — helper `phoenixSpanUrl(spanId: string | null): string | null` building `https://app.phoenix.arize.com/projects/chaoslab-demo/spans/{spanId}` (or null if no spanId). ≤30 LOC.
- `apps/chaoslab-web/tests/unit/attack-matrix.test.tsx` — NEW — Vitest + React Testing Library. ≥8 test cases: (1) renders exactly 25 `[data-testid^="attack-cell-"]` elements when given 25 cells; (2) passed cells get the pass-green color class (verify via getComputedStyle); (3) failed cells get the attack-red color class; (4) revealedCount=10 shows 10 visible cells; (5) phase transition with same cell data re-mounts with new key (verify via DOM); (6) reduced motion: stagger disabled when `prefers-reduced-motion: reduce`; (7) click on a cell with spanId opens new tab (mock window.open); (8) aria-label on grid + cells; (9) icon (✗ or ✓) visible per cell.
- `apps/chaoslab-web/tests/e2e/attack-matrix.spec.ts` — NEW — Playwright test rendering a test page with 25 fixture cells; asserts `[data-testid^="attack-cell-"]` count is 25; asserts computed style of a passed cell's background-color matches `oklch(0.72 0.20 145)` (or its computed equivalent). Visual screenshot to `screenshots/baseline/attack-matrix-canonical.png`. ≥3 test cases.
- `apps/chaoslab-web/package.json` — UPDATE — add `framer-motion` to `dependencies`

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given AttackMatrix has been written and accepts 25 AttackCell objects as the `cells` prop
When the component renders
Then the DOM contains exactly 25 elements matching [data-testid^="attack-cell-"]
And the grid container has data-testid="attack-matrix"

Given AttackMatrix is rendered with cells where cell.passed=true uses the pass-green token
When `getComputedStyle(cell).backgroundColor` is read for a passed cell
Then the value parses to OKLCH (0.72, 0.20, 145) — equivalent to the --color-pass-green token

Given AttackMatrix is rendered with cells where cell.passed=false
When `getComputedStyle(cell).backgroundColor` is read for a failed cell
Then the value parses to OKLCH (0.65, 0.24, 25) — equivalent to the --color-attack-red token

Given the `phase` prop transitions from "attacking" to "reattacking" with new cell data
When the component re-renders
Then each cell re-mounts (verified via Framer Motion's onAnimationStart firing) with the new key
And the stagger animation plays with ~0.04s delay between cells

Given `prefers-reduced-motion: reduce` is active (window.matchMedia mock)
When the component renders
Then no stagger transition is applied (delay = 0)
And cells appear instantly in their final state

Given a cell with non-null spanId is clicked
When the click handler fires
Then `window.open` is called with the Phoenix span URL and `_blank` target and `noopener` rel

Given the component is rendered
When axe-core scans it
Then no accessibility violations are reported
And the grid has role="grid" with aria-label
And each cell has aria-label describing its fault class + pass/fail state

Given vitest is run
When `pnpm --filter chaoslab-web exec vitest run apps/chaoslab-web/tests/unit/attack-matrix.test.tsx` executes
Then exit code is 0
And ≥8 test cases pass

Given playwright is configured
When `pnpm --filter chaoslab-web exec playwright test apps/chaoslab-web/tests/e2e/attack-matrix.spec.ts` runs
Then exit code is 0
```

---

## Shell verification

The coding agent runs this to confirm the story is done before opening a PR:

```bash
set -e
cd /Users/abu/dev/hackathon/rapid-agents

# Files exist
test -f apps/chaoslab-web/app/_components/attack-matrix.tsx
test -f apps/chaoslab-web/app/_components/attack-cell.tsx
test -f apps/chaoslab-web/lib/phoenix-links.ts
test -f apps/chaoslab-web/tests/unit/attack-matrix.test.tsx

# 'use client' directive present
head -5 apps/chaoslab-web/app/_components/attack-matrix.tsx | grep -E "'use client'"
head -5 apps/chaoslab-web/app/_components/attack-cell.tsx | grep -E "'use client'"

# Framer Motion + reduced-motion gating
grep -E "useReducedMotion" apps/chaoslab-web/app/_components/attack-matrix.tsx
grep -E "framer-motion" apps/chaoslab-web/app/_components/attack-cell.tsx

# data-testid plumbing
grep -E "attack-matrix" apps/chaoslab-web/app/_components/attack-matrix.tsx
grep -E "attack-cell-" apps/chaoslab-web/app/_components/attack-cell.tsx

# Color-blind safety: icon overlay
grep -E "(✗|✓|aria-label.*passed|aria-label.*failed)" apps/chaoslab-web/app/_components/attack-cell.tsx

# Phoenix link helper
grep -E "phoenix\.arize\.com" apps/chaoslab-web/lib/phoenix-links.ts

# Unit tests
pnpm --filter chaoslab-web exec vitest run apps/chaoslab-web/tests/unit/attack-matrix.test.tsx
test "$(pnpm --filter chaoslab-web exec vitest run apps/chaoslab-web/tests/unit/attack-matrix.test.tsx --reporter=verbose 2>&1 | grep -cE '✓|PASS')" -ge 8

# Typecheck + build
pnpm --filter chaoslab-web exec tsc --noEmit
AGENT_BACKEND_URL=http://localhost:8001 pnpm --filter chaoslab-web build

# 400-line guard (per-file)
test "$(grep -cvE '^\s*(//|$)' apps/chaoslab-web/app/_components/attack-matrix.tsx)" -le 300
test "$(grep -cvE '^\s*(//|$)' apps/chaoslab-web/app/_components/attack-cell.tsx)" -le 100
python3 scripts/check_max_lines.py --strict apps/chaoslab-web/app/_components

echo "story-7.5 verification: PASS"
```

---

## Notes for coding agent

- This is the centerpiece of the demo's wow moment. Every animation decision is locked by `docs/ux-spec.md` §"Behavior (timed for the 3-min demo)".
- Stagger delay = ~0.04s per cell (25 cells × 0.04s = 1.0s total cascade). Don't change this — it's tuned to the demo video pacing.
- Animation pattern: Approach A from `best-practices/04 §5` — re-mount via `key={\`${phase}-${cell.idx}\`}`triggers a fresh`initial={...} animate={...}` sequence on every phase transition. This is what gives the cascade-flip its punch (cells don't morph, they re-enter).
- Reduced motion: `const shouldReduceMotion = useReducedMotion()`. If true: `transition={{ duration: 0 }}` and skip stagger. The visual still works — cells just snap to final state.
- Color-blind safety per ux-spec §"Accessibility": icon redundancy is non-negotiable. Render `✓` or `✗` (Unicode) as a centered child of each cell. Style: `text-text-primary` for ✓ on green; `text-text-primary` for ✗ on red. Visual designers may want SVG icons (`<CheckIcon />`, `<XIcon />` from lucide-react) — fine, but ensure they're visible (12-16px) inside a small cell.
- ARIA: `role="grid"` on the outer container with `aria-label="Attack results, 25 fault injection runs"`. Each cell: `role="gridcell"` + `aria-label="Run {idx}, {faultClass}, {passed ? 'passed' : 'failed'}"`.
- Click handler: cells with non-null spanId open Phoenix UI. Use `window.open(url, '_blank', 'noopener,noreferrer')`. For tests, mock `window.open` via `vi.spyOn(window, 'open')`.
- Tailwind dynamic classes WARNING: do NOT do `className={\`bg-${cell.passed ? 'pass-green' : 'attack-red'}\`}`— Tailwind 4 still requires literal class names for purging. Use a static conditional:`className={cell.passed ? 'bg-pass-green' : 'bg-attack-red'}`.
- The matrix container layout: `<div className="grid grid-cols-5 gap-1.5 aspect-square w-full max-w-md">`. Sharp corners (`rounded-none` or no rounded class) per ux-spec §"Design tokens" border radius row.
- Cells are pure squares with the cell color + icon. NO border. The gap-1.5 between cells creates the grid look.
- Tooltip on each cell shows `faultClass` (e.g., "Prompt injection — failed"). Use shadcn/ui `Tooltip` (installed in story-7.1).
- Test fixture: a `getMockCells(): AttackCell[]` helper inside tests, returning 25 cells with deterministic pass/fail mix (12 fail, 13 pass during attack phase; 22 pass, 3 fail post-patch).
- Performance: Framer Motion is GPU-accelerated via `transform`. Don't add CSS animations on `width`/`height` — they trigger layout. `scale` + `opacity` only.
- Total LOC budget: attack-matrix.tsx ≤300, attack-cell.tsx ≤100. If attack-matrix.tsx crosses 300, the most likely cause is inlining the cell sub-component — split it out (already done in this file map).
- Phoenix span URL: `https://app.phoenix.arize.com/projects/chaoslab-demo/spans/{spanId}`. The project name `chaoslab-demo` matches ADR-004's canonical-replay Phoenix project. If null spanId, cell is non-clickable (cursor: default).
