# Story — <ReceiptCard> final summary card slide-up

**ID:** story-7.8-receipt-card
**Epic:** Epic 7 — chaoslab-web frontend
**Depends on:** story-7.2-design-tokens, story-7.4-run-store-and-sse
**Estimate:** ~1.5h
**Status:** PENDING
**tags:** [frontend, p0, ui]

---

## User story

**As a** judge reaching the end of the ChaosLab demo at 2:45
**I want to** see a clean receipt card slide up showing run stats, fault classes, root causes, recipe links (Markdown + GitLab MR if emitted), cost in USD, duration, and the headline "60% → 92% improvement" number
**So that** the demo closes with a quantifiable proof — every measurable judging criterion (Tech Implementation, Design, Potential Impact) gets a tangible artifact in the final frame

---

## File modification map

Exact files the coding agent creates or modifies for this story:

- `apps/chaoslab-web/app/_components/receipt-card.tsx` — NEW — Client component per `docs/ux-spec.md` `<ReceiptCard>` contract. Props per the locked TS interface (runId, attackCount, faultClasses, rootCausesFound, recipeId, mrUrl, markdownUrl, costUsd, durationSeconds, baselinePassRate, postPatchPassRate, improvement). Renders a shadcn/ui `<Card>` with sections: header (recipe_id badge + run stats), fault classes list, root causes count, recipe links (Markdown link + GitLab MR link if mrUrl is non-null), cost+duration row, baseline → post-patch headline number with improvement %. Slide-up animation via Framer Motion (`initial={{ y: 40, opacity: 0 }} animate={{ y: 0, opacity: 1 }}`). Reduced-motion gated. data-testid="receipt-card". ≤200 LOC.
- `apps/chaoslab-web/lib/format.ts` — NEW — Pure formatters: `formatUsd(n: number)`, `formatDuration(seconds: number)` ("2m 47s"), `formatPercent(n: number)` ("92%"), `formatImprovement(delta: number)` ("+52pp"). ≤60 LOC.
- `apps/chaoslab-web/tests/unit/receipt-card.test.tsx` — NEW — Vitest + RTL. ≥7 test cases: (1) renders `[data-testid="receipt-card"]`; (2) shows the recipe_id text; (3) when mrUrl is non-null, renders an `<a>` with `href={mrUrl}` and target="\_blank"; (4) when mrUrl is null, NO GitLab MR link is rendered; (5) markdownUrl link is always rendered; (6) shows cost formatted as USD ("$0.34"); (7) shows duration formatted ("2m 47s"); (8) shows baseline → post-patch improvement; (9) reduced motion → no slide-up animation.

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given ReceiptCard has been written and rendered with a fully-populated ReceiptCardProps object including recipe_id "recipe_abc123def456" and mrUrl "https://gitlab.com/example/agent/-/merge_requests/42"
When the DOM is queried
Then an element matches [data-testid="receipt-card"]
And the element text contains "recipe_abc123def456"
And the DOM contains an `<a>` with href="https://gitlab.com/example/agent/-/merge_requests/42"
And that anchor element has target="_blank" and rel containing "noopener"

Given ReceiptCard is rendered with mrUrl=null
When the DOM is queried for the GitLab MR link
Then no `<a>` with href matching gitlab.com is rendered
And the markdownUrl link is still rendered

Given ReceiptCard is rendered with costUsd=0.34
When the DOM is queried for the cost element
Then the text matches "$0.34"

Given ReceiptCard is rendered with durationSeconds=167
When the DOM is queried for the duration element
Then the text matches "2m 47s"

Given ReceiptCard is rendered with baselinePassRate=0.40, postPatchPassRate=0.92, improvement=0.52
When the DOM is queried for the improvement headline
Then the text contains "92%" and contains a positive improvement indicator (e.g., "+52pp" or "+52%")

Given prefers-reduced-motion: reduce is active
When ReceiptCard renders
Then no slide-up animation runs (Framer Motion transition duration=0)

Given the card is rendered
When axe-core scans it
Then no accessibility violations are reported
And links open in a new tab (target="_blank") with rel="noopener noreferrer"

Given vitest is run
When `pnpm --filter chaoslab-web exec vitest run apps/chaoslab-web/tests/unit/receipt-card.test.tsx` executes
Then exit code is 0
And ≥7 test cases pass
```

---

## Shell verification

The coding agent runs this to confirm the story is done before opening a PR:

```bash
set -e
cd /Users/abu/dev/hackathon/rapid-agents

# Files exist
test -f apps/chaoslab-web/app/_components/receipt-card.tsx
test -f apps/chaoslab-web/lib/format.ts
test -f apps/chaoslab-web/tests/unit/receipt-card.test.tsx

# 'use client'
head -5 apps/chaoslab-web/app/_components/receipt-card.tsx | grep -E "'use client'"

# data-testid
grep -E "receipt-card" apps/chaoslab-web/app/_components/receipt-card.tsx

# Framer Motion + reduced motion
grep -E "framer-motion" apps/chaoslab-web/app/_components/receipt-card.tsx
grep -E "useReducedMotion" apps/chaoslab-web/app/_components/receipt-card.tsx

# Conditional GitLab link
grep -E "(mrUrl|gitlab)" apps/chaoslab-web/app/_components/receipt-card.tsx

# Format helpers used
grep -E "format(Usd|Duration|Percent|Improvement)" apps/chaoslab-web/app/_components/receipt-card.tsx

# Unit tests
pnpm --filter chaoslab-web exec vitest run apps/chaoslab-web/tests/unit/receipt-card.test.tsx
test "$(pnpm --filter chaoslab-web exec vitest run apps/chaoslab-web/tests/unit/receipt-card.test.tsx --reporter=verbose 2>&1 | grep -cE '✓|PASS')" -ge 7

# Typecheck + build
pnpm --filter chaoslab-web exec tsc --noEmit
AGENT_BACKEND_URL=http://localhost:8001 pnpm --filter chaoslab-web build

# 400-line guard
test "$(grep -cvE '^\s*(//|$)' apps/chaoslab-web/app/_components/receipt-card.tsx)" -le 200
test "$(grep -cvE '^\s*(//|$)' apps/chaoslab-web/lib/format.ts)" -le 60

echo "story-7.8 verification: PASS"
```

---

## Notes for coding agent

- Card structure (top-to-bottom):
  1. Header row: "RUN COMPLETE" label + `<Badge variant="outline">{recipeId}</Badge>` (shadcn badge)
  2. Headline: "{baselinePassRate*100}% → {postPatchPassRate*100}%" with "+{improvement\*100}pp" in pass-green
  3. Stats grid (3 cols): `attackCount` runs / `faultClasses.length` fault classes / `rootCausesFound` root causes
  4. Recipe section: "Hardening recipe" header + (a) Markdown link (always present) + (b) GitLab MR link (if mrUrl non-null)
  5. Footer row: `formatUsd(costUsd)` cost · `formatDuration(durationSeconds)` duration
  6. CTA: "Run against your own agent →" linking to `/agent/new`
- Use the shadcn `Card`, `CardHeader`, `CardContent`, `CardFooter` primitives installed in story-7.1. They're already styled.
- Reduced motion: `const shouldReduceMotion = useReducedMotion(); transition={{ duration: shouldReduceMotion ? 0 : 0.45, ease: 'easeOut' }}`. The card still appears, just without slide.
- mrUrl conditional rendering: `{mrUrl != null && <a href={mrUrl} target="_blank" rel="noopener noreferrer">View MR #{...}</a>}`. Extract the MR number from the URL via a regex helper or just show "View merge request" if parsing is fiddly.
- Always use `target="_blank" rel="noopener noreferrer"` on external links — security + a11y standard.
- The headline number (e.g., "40% → 92%") is the visual hook. Make it big: `text-5xl font-display tracking-tight`. The improvement delta (+52pp) is in `text-pass-green` next to it.
- "pp" stands for "percentage points" (technically more accurate than "%" for a delta of two percentages). Use "pp" for the improvement and "%" for the absolute rates.
- format helpers:
  - `formatUsd(0.34)` → "$0.34" (use `Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' })`)
  - `formatDuration(167)` → "2m 47s" (simple modulo)
  - `formatPercent(0.92)` → "92%"
  - `formatImprovement(0.52)` → "+52pp"
- The card is rendered conditionally by the parent route — only when `state === 'complete'` AND `recipe != null`. The component itself doesn't care, just renders what it's given.
- ARIA: the card is a region: `role="region" aria-label="ChaosLab run summary"`. Links have descriptive text — not "click here."
- Empty states: NOT handled here. The parent decides whether to render the card; if `recipe` is null, parent renders a skeleton or hides the card. No null guards needed inside the component.
- Total LOC budget: receipt-card.tsx ≤200, format.ts ≤60.
