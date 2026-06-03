# Story — <ResilienceCurve> visx LinePath with PATCH marker

**ID:** story-7.6-resilience-curve
**Epic:** Epic 7 — chaoslab-web frontend
**Depends on:** story-7.2-design-tokens, story-7.4-run-store-and-sse
**Estimate:** ~2h
**Status:** PENDING
**tags:** [frontend, p0, ui]

---

## User story

**As a** judge watching the ChaosLab demo
**I want to** see a smooth line chart tracking pass rate over time, with a vivid violet vertical PATCH line dropping in at t=1:50 to mark the moment the hardening recipe fires
**So that** the "PATCH line is the literal wedge in the chart" visual pun lands — same story the Attack Matrix tells, told once aggregate-style, for the Devpost cover screenshot at 2:15

---

## File modification map

Exact files the coding agent creates or modifies for this story:

- `apps/chaoslab-web/app/_components/resilience-curve.tsx` — NEW — Client component per `docs/ux-spec.md` `<ResilienceCurve>` contract. Props `{ attackPoints: ResiliencePoint[]; reattackPoints: ResiliencePoint[]; patchX: number | null; width?: number; height?: number }`. Renders an SVG via visx: `<Group>`, `<Grid>`, `<AxisBottom>`, `<AxisLeft>`, `<LinePath>` for attack series (stroke `--color-attack-red`), `<LinePath>` for reattack series (stroke `--color-pass-green`), `<motion.line data-testid="patch-marker">` for the PATCH marker when patchX is non-null. Uses `<ParentSize>` from `@visx/responsive` so it sizes to its container. data-testid="resilience-curve" on the root SVG. ≤300 LOC.
- `apps/chaoslab-web/app/_components/resilience-curve-marker.tsx` — NEW — sub-component for the animated PATCH line (kept separate so the main file stays ≤300 LOC). Uses Framer Motion to animate `pathLength` 0→1 on a vertical dashed `<line>`. Animation gated by `useReducedMotion()` — instant if reduced. data-testid="patch-marker". ≤80 LOC.
- `apps/chaoslab-web/lib/curve-scales.ts` — NEW — Pure helpers: `buildScales({ width, height, allPoints }) → { xScale, yScale }` using `scaleLinear` from `@visx/scale`. Domain x: [0, max(point.x)], y: [0, 1]. Margin object exported. ≤80 LOC.
- `apps/chaoslab-web/tests/unit/resilience-curve.test.tsx` — NEW — Vitest + RTL. ≥7 test cases: (1) renders an `<svg>` with `data-testid="resilience-curve"`; (2) renders two `<path>` elements (attack series + reattack series) when both arrays non-empty; (3) renders only attack series when reattackPoints is empty; (4) renders `[data-testid="patch-marker"]` when patchX is non-null; (5) hides patch marker when patchX is null; (6) reduced-motion → marker animation duration is 0; (7) y-axis range is 0–100%; (8) AxisBottom shows the t=patchX tick when patchX is in domain.
- `apps/chaoslab-web/tests/e2e/resilience-curve.spec.ts` — NEW — Playwright test rendering a test page with sample data; asserts the svg contains two `<path>` elements + the patch marker; visual screenshot to `screenshots/baseline/resilience-curve-canonical.png`. ≥2 test cases.
- `apps/chaoslab-web/package.json` — UPDATE — add `@visx/group`, `@visx/scale`, `@visx/shape`, `@visx/grid`, `@visx/axis`, `@visx/responsive`, `@visx/text` to `dependencies`

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given ResilienceCurve has been written and is rendered with attackPoints + reattackPoints + patchX=12
When the component renders
Then the DOM contains an `<svg>` element with data-testid="resilience-curve"
And the SVG contains exactly 2 `<path>` elements for the data series
And the SVG contains a `<line>` element with data-testid="patch-marker"

Given ResilienceCurve is rendered with patchX=null
When the DOM is queried
Then no element matches [data-testid="patch-marker"]

Given ResilienceCurve is rendered with only attackPoints (reattackPoints empty)
When the DOM is queried
Then exactly 1 `<path>` element is rendered for the data series

Given the attack series LinePath
When the stroke attribute is inspected
Then it equals the --color-attack-red token value (e.g., `oklch(0.65 0.24 25)` or `var(--color-attack-red)`)

Given the reattack series LinePath
When the stroke attribute is inspected
Then it equals the --color-pass-green token value

Given the PATCH marker is rendered
When the stroke attribute is inspected
Then it equals the --color-patch-line token value
And the stroke-dasharray attribute is non-empty (dashed line)

Given prefers-reduced-motion: reduce is active
When the PATCH marker renders
Then no Framer Motion pathLength animation runs (transition duration=0)

Given vitest is run
When `pnpm --filter chaoslab-web exec vitest run apps/chaoslab-web/tests/unit/resilience-curve.test.tsx` executes
Then exit code is 0
And ≥7 test cases pass

Given Playwright is run
When `pnpm --filter chaoslab-web exec playwright test apps/chaoslab-web/tests/e2e/resilience-curve.spec.ts` runs
Then exit code is 0
```

---

## Shell verification

The coding agent runs this to confirm the story is done before opening a PR:

```bash
set -e
cd /Users/abu/dev/hackathon/rapid-agents

# Files exist
test -f apps/chaoslab-web/app/_components/resilience-curve.tsx
test -f apps/chaoslab-web/app/_components/resilience-curve-marker.tsx
test -f apps/chaoslab-web/lib/curve-scales.ts
test -f apps/chaoslab-web/tests/unit/resilience-curve.test.tsx

# 'use client'
head -5 apps/chaoslab-web/app/_components/resilience-curve.tsx | grep -E "'use client'"
head -5 apps/chaoslab-web/app/_components/resilience-curve-marker.tsx | grep -E "'use client'"

# visx imports present
grep -E "@visx/(shape|scale|axis|grid|responsive|group)" apps/chaoslab-web/app/_components/resilience-curve.tsx

# data-testids
grep -E "resilience-curve" apps/chaoslab-web/app/_components/resilience-curve.tsx
grep -E "patch-marker" apps/chaoslab-web/app/_components/resilience-curve-marker.tsx

# Framer Motion + reduced-motion
grep -E "framer-motion" apps/chaoslab-web/app/_components/resilience-curve-marker.tsx
grep -E "useReducedMotion" apps/chaoslab-web/app/_components/resilience-curve-marker.tsx

# Color tokens referenced (--color-attack-red, --color-pass-green, --color-patch-line)
grep -cE "color-(attack-red|pass-green|patch-line)" apps/chaoslab-web/app/_components/resilience-curve.tsx apps/chaoslab-web/app/_components/resilience-curve-marker.tsx | awk -F: '{s+=$2} END{exit (s>=3?0:1)}'

# Unit tests pass with ≥7
pnpm --filter chaoslab-web exec vitest run apps/chaoslab-web/tests/unit/resilience-curve.test.tsx
test "$(pnpm --filter chaoslab-web exec vitest run apps/chaoslab-web/tests/unit/resilience-curve.test.tsx --reporter=verbose 2>&1 | grep -cE '✓|PASS')" -ge 7

# Typecheck + build
pnpm --filter chaoslab-web exec tsc --noEmit
AGENT_BACKEND_URL=http://localhost:8001 pnpm --filter chaoslab-web build

# 400-line guard
test "$(grep -cvE '^\s*(//|$)' apps/chaoslab-web/app/_components/resilience-curve.tsx)" -le 300
test "$(grep -cvE '^\s*(//|$)' apps/chaoslab-web/app/_components/resilience-curve-marker.tsx)" -le 80
python3 scripts/check_max_lines.py --strict apps/chaoslab-web/app/_components apps/chaoslab-web/lib

echo "story-7.6 verification: PASS"
```

---

## Notes for coding agent

- visx is a primitive library — you assemble. Don't expect a "Chart" component. The hierarchy:
  ```
  <ParentSize>
    {({width, height}) => (
      <svg width={width} height={height} data-testid="resilience-curve">
        <Group left={margin.left} top={margin.top}>
          <Grid xScale={xScale} yScale={yScale} ... />
          <AxisBottom scale={xScale} ... />
          <AxisLeft scale={yScale} tickFormat={fmtPercent} ... />
          <LinePath data={attackPoints} x={d => xScale(d.x)} y={d => yScale(d.y)} stroke="var(--color-attack-red)" />
          <LinePath data={reattackPoints} ... stroke="var(--color-pass-green)" />
          {patchX != null && <PatchMarker x={xScale(patchX)} height={innerHeight} />}
        </Group>
      </svg>
    )}
  </ParentSize>
  ```
- Wrap the entire thing in `<ParentSize>` so it auto-sizes. Default min height in tests: 320px (Playwright sets parent dimensions).
- The PATCH marker animation: Framer Motion `<motion.line>` with `initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: 0.8, ease: 'easeInOut' }}`. SVG `<line>` doesn't natively support pathLength — use a `<motion.path>` with `d={\`M ${x} 0 L ${x} ${height}\`}` instead. Style with `strokeDasharray="4 4"` for the dashed look.
- Color tokens: `stroke="var(--color-attack-red)"` works in SVG via CSS-var binding. Verify by running `pnpm build` then `curl` the page and inspect the rendered SVG. Tailwind 4 + visx + CSS variables play nicely.
- Domain handling: x-axis is "run index" (0..N total runs). y-axis is "pass rate" (0..1, displayed as 0%..100%). `tickFormat={(v) => \`${Math.round(Number(v) * 100)}%\`}` on AxisLeft.
- The two series share an x-axis but represent DIFFERENT runs (attackPoints = pre-patch runs, reattackPoints = post-patch runs). The PATCH line at `patchX` sits between them visually — it's the boundary.
- Reduced motion: in `resilience-curve-marker.tsx`, `const shouldReduceMotion = useReducedMotion(); transition={{ duration: shouldReduceMotion ? 0 : 0.8 }}`. The marker still appears, just instantly.
- visx is a CLIENT-ONLY library — DOM-dependent. `'use client'` mandatory at the top of both .tsx files.
- Performance: visx renders to native SVG. No canvas. Re-render cost on each new point is acceptable for ~50 points total. Don't memoize prematurely; if FPS drops below 60, profile first.
- Margins: typical visx pattern is `{ top: 20, right: 24, bottom: 32, left: 48 }`. Pull from `lib/curve-scales.ts`.
- Test pattern for unit tests: render the component with React Testing Library + jsdom; assertions use `screen.getByTestId` + querying `svg.querySelectorAll('path')`. For computed style on stroke, use `getComputedStyle(path).stroke` (jsdom resolves CSS variables in this case).
- DO NOT use Recharts, Chart.js, or D3 directly — `architecture.md` locks visx as the chart layer.
- Total LOC budget: resilience-curve.tsx ≤300, resilience-curve-marker.tsx ≤80, curve-scales.ts ≤80. If the main file approaches 300, extract the `<Grid>` + axis setup into another helper.
- The line interpolation is `curveMonotoneX` from `@visx/curve` (`import { curveMonotoneX } from '@visx/curve'; <LinePath curve={curveMonotoneX}>`). Smooth, non-overshooting. Default `curveLinear` looks jagged on small samples.
