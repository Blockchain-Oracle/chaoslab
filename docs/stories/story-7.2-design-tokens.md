# Story — Design tokens in globals.css (@theme block, OKLCH)

**ID:** story-7.2-design-tokens
**Epic:** Epic 7 — chaoslab-web frontend
**Depends on:** story-7.1-nextjs-scaffold
**Estimate:** ~0.75h
**Status:** PENDING
**tags:** [frontend, p0, ui]

---

## User story

**As a** coding agent rendering the Attack Matrix + Resilience Curve hero visual
**I want to** drop the full Tailwind 4 `@theme` block from `docs/ux-spec.md` into `app/globals.css` — OKLCH colors for the 5-agent palette + attack-red + pass-green + patch-line + text scales + Geist fonts
**So that** every later component references `bg-attack-red`, `bg-pass-green`, `text-text-primary`, `bg-agent-orchestrator` etc. against perceptually-uniform OKLCH values that hit WCAG AA contrast and that drive the cascade-flip's emotional punch

---

## File modification map

Exact files the coding agent creates or modifies for this story:

- `apps/chaoslab-web/app/globals.css` — UPDATE — replace the story-7.1 stub (`@import "tailwindcss";` only) with the full file: tailwindcss import, `@theme` block carrying every token from `docs/ux-spec.md` "Design tokens (LOCKED)" table, `@layer base` body styles, custom subtle shadow utility, reduced-motion utility per `best-practices/04 §13`. ≤200 LOC.
- `apps/chaoslab-web/app/layout.tsx` — UPDATE — confirm Geist + Geist Mono `next/font/google` imports bind to CSS variables `--font-display` and `--font-mono` so the `@theme` block picks them up (already wired in 7.1; verify the variable names match)

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given the story-7.1 scaffold has globals.css containing only the tailwindcss import
When the coding agent writes the full @theme block
Then `grep -E "^@theme\s*\{" apps/chaoslab-web/app/globals.css` exits 0

Given globals.css has been written
When `grep -E "--color-attack-red.*oklch" apps/chaoslab-web/app/globals.css` runs
Then exit code is 0

Given globals.css has been written
When `grep -E "--color-pass-green.*oklch" apps/chaoslab-web/app/globals.css` runs
Then exit code is 0

Given globals.css has been written
When `grep -E "--color-patch-line.*oklch" apps/chaoslab-web/app/globals.css` runs
Then exit code is 0

Given globals.css has been written
When `grep -cE "--color-agent-(orchestrator|injector|judge|patcher|target)" apps/chaoslab-web/app/globals.css` runs
Then output is 5 (all five agent colors defined)

Given globals.css has been written
When `grep -cE "--color-text-(primary|secondary|muted)" apps/chaoslab-web/app/globals.css` runs
Then output is 3

Given globals.css has been written
When `grep -E "--font-display.*Geist" apps/chaoslab-web/app/globals.css` runs
Then exit code is 0

Given globals.css has been written
When `grep -E "--color-background.*oklch" apps/chaoslab-web/app/globals.css` runs
Then exit code is 0

Given globals.css has been updated
When `pnpm --filter chaoslab-web build` runs
Then exit code is 0
And `grep -r "bg-attack-red\|bg-pass-green" apps/chaoslab-web/.next/static/css/ | wc -l` outputs ≥ 0 (Tailwind compiled the tokens successfully — note: zero hits OK here since no component uses them yet)

Given globals.css has been updated and includes prefers-reduced-motion
When `grep -E "prefers-reduced-motion" apps/chaoslab-web/app/globals.css` runs
Then exit code is 0
```

---

## Shell verification

The coding agent runs this to confirm the story is done before opening a PR:

```bash
set -e
cd /Users/abu/dev/hackathon/rapid-agents

# @theme block exists
grep -E "^@theme\s*\{" apps/chaoslab-web/app/globals.css

# All required tokens
grep -E "--color-attack-red.*oklch" apps/chaoslab-web/app/globals.css
grep -E "--color-pass-green.*oklch" apps/chaoslab-web/app/globals.css
grep -E "--color-patch-line.*oklch" apps/chaoslab-web/app/globals.css
grep -E "--color-background.*oklch" apps/chaoslab-web/app/globals.css
grep -E "--color-surface.*oklch" apps/chaoslab-web/app/globals.css
test "$(grep -cE '--color-agent-(orchestrator|injector|judge|patcher|target)' apps/chaoslab-web/app/globals.css)" -eq 5
test "$(grep -cE '--color-text-(primary|secondary|muted)' apps/chaoslab-web/app/globals.css)" -eq 3
grep -E "--font-display.*Geist" apps/chaoslab-web/app/globals.css
grep -E "--font-mono.*Geist Mono" apps/chaoslab-web/app/globals.css

# Reduced-motion respected
grep -E "prefers-reduced-motion" apps/chaoslab-web/app/globals.css

# Build clean
pnpm --filter chaoslab-web build

# 400-line guard
python3 scripts/check_max_lines.py --strict apps/chaoslab-web/app/globals.css

echo "story-7.2 verification: PASS"
```

---

## Notes for coding agent

- The token list is LOCKED in `docs/ux-spec.md` §"Design tokens (LOCKED)". Copy values VERBATIM — don't paraphrase OKLCH numbers, they were tuned for matched perceptual brightness across the red/green/violet trio.
- The full token set:
  - Backgrounds: `--color-background`, `--color-surface`, `--color-surface-raised`
  - Text: `--color-text-primary`, `--color-text-secondary`, `--color-text-muted`
  - Hero: `--color-attack-red`, `--color-pass-green`, `--color-patch-line`
  - Agents: `--color-agent-orchestrator`, `--color-agent-injector`, `--color-agent-judge`, `--color-agent-patcher`, `--color-agent-target`
  - Fonts: `--font-display` (Geist), `--font-mono` (Geist Mono)
- OKLCH is mandatory (per ux-spec). Do NOT translate to RGB or hex; Tailwind 4 supports OKLCH natively.
- `@layer base` block: `body { @apply bg-background text-text-primary antialiased; font-family: var(--font-display); }`
- Custom subtle shadow utility: define `--shadow-card: 0 1px 3px 0 oklch(0 0 0 / 0.3)` and reference via `@layer utilities` for `.shadow-card` (replaces banned `shadow-md/lg/xl` per ux-spec §"Banned Tailwind classes").
- `prefers-reduced-motion` media block: globally disable transitions/animations for users requesting reduced motion per ux-spec §"Accessibility" and `best-practices/04 §13`. Story-7.5 also gates Framer Motion stagger via `useReducedMotion()` — both layers needed.
- The Geist font binding from story-7.1's `layout.tsx`: `import { Geist, Geist_Mono } from 'next/font/google'` and `<html className={\`\${geist.variable} \${geistMono.variable}\`}>`. The CSS variables must be `--font-display`(NOT`--font-geist-sans`— match the ux-spec token name). Override via`next/font`config:`Geist({ subsets: ['latin'], variable: '--font-display' })`.
- DO NOT add component styles here. Components own their own classes. Only design tokens + base + reduced-motion utility live in globals.css.
- File MUST stay ≤200 LOC — comfortably under the 400-line guard.
- After story lands, story-7.5/7.6/7.7/7.8 reference these tokens via Tailwind utility classes. Verify by writing a temp `<div className="bg-attack-red text-text-primary">test</div>` in `page.tsx`, running `pnpm build`, then `rm` the temp markup before commit.
