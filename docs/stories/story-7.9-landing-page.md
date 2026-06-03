# Story — / landing page + header + footer + OG metadata

**ID:** story-7.9-landing-page
**Epic:** Epic 7 — chaoslab-web frontend
**Depends on:** story-7.2-design-tokens
**Estimate:** ~1.5h
**Status:** PENDING
**tags:** [frontend, p0, ui]

---

## User story

**As a** judge landing on the ChaosLab demo URL with no login
**I want to** see a clean, opinionated hero (title, one-line pitch, single "Run ChaosLab" CTA), a header on every route, and a footer with license + vendoring attribution
**So that** the entry experience reads "v1 of a startup" not "hackathon prototype" (the 25% Design judging lever), the §13 README ordering is mirrored in the UI, and clicking the CTA flows directly into the live attack demo

---

## File modification map

Exact files the coding agent creates or modifies for this story:

- `apps/chaoslab-web/app/page.tsx` — UPDATE — replace the story-7.1 placeholder with the real landing page. Server component. Hero section: project title "ChaosLab" (Geist display, tracking-tight), one-line pitch (verbatim from `docs/PRD.md` §"One-line pitch"), single CTA `<Link href="/attack"><Button size="lg">Run ChaosLab</Button></Link>`. Below-hero: 3-column "How it works" feature grid (Inject → Watch → Harden). Includes header + footer slots. Exports `generateMetadata()` per `best-practices/04 §12` with `title`, `description`, `openGraph.images: ['/og-hero.png']`, twitter card. ≤200 LOC.
- `apps/chaoslab-web/app/_components/header.tsx` — NEW — Server component (no interactivity needed at this story level — state pill lands in story-7.11 wrapper). Renders: ChaosLab wordmark (left), GitHub link + "Run against your agent" CTA (right). Height 64px desktop / 56px mobile via Tailwind `h-16 md:h-14`. ≤100 LOC.
- `apps/chaoslab-web/app/_components/footer.tsx` — NEW — Server component. Renders: "ChaosLab — built at Google Cloud Rapid Agent Hackathon, June 2026" + Apache-2.0 license link + vendoring attribution per ux-spec §"Structural requirements (§12)". ≤80 LOC.
- `apps/chaoslab-web/app/_components/feature-card.tsx` — NEW — Small presentational component for the "How it works" grid. Props `{ title, body, icon }`. Renders a `<Card>` with the agent-color-coded icon, title, body. ≤60 LOC.
- `apps/chaoslab-web/public/og-hero.png` — NEW — 1200×630 PNG placeholder for the OG image. Hand-drawn or AI-generated mockup of the 2:15 frame (matrix mid-cascade + curve mid-jump + PATCH line visible). Real OG image (auto-captured from the demo) lands in Epic 8 story-8.3 — this story drops a working placeholder so `next build` + OG validator pass.
- `apps/chaoslab-web/tests/e2e/landing.spec.ts` — NEW — Playwright test against `/`. ≥4 test cases: (1) `page.title()` matches `/ChaosLab/i`; (2) page contains element with text "Run ChaosLab" linked to `/attack`; (3) header contains "ChaosLab" wordmark; (4) footer contains "Apache" license link.

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given app/page.tsx has been written with generateMetadata
When the page is built and rendered via `pnpm build` + `pnpm start`
Then GET / returns 200
And the HTML title matches /ChaosLab/i

Given the landing page is rendered
When the DOM is queried for the CTA
Then an `<a>` element with text containing "Run ChaosLab" exists
And that anchor's href is "/attack"

Given the header component is rendered
When the DOM is queried
Then the header contains the text "ChaosLab"
And a GitHub link is present

Given the footer is rendered
When the DOM is queried
Then the footer contains a link to "https://www.apache.org/licenses/LICENSE-2.0"
And the footer contains text mentioning "deepankarm/agent-chaos" (vendoring attribution)

Given the metadata is exported
When `pnpm build` produces .next output
Then the rendered HTML <head> contains `<meta property="og:image" content="/og-hero.png">`
And `<meta property="og:title" content` contains "ChaosLab"

Given /public/og-hero.png exists
When `file apps/chaoslab-web/public/og-hero.png` is inspected
Then it identifies as a PNG image
And dimensions are 1200x630 (verified via `identify -format "%wx%h"` or equivalent)

Given Playwright loads /
When the test runs against a local dev server
Then page.title matches /ChaosLab/i
And page contains element with text "Run ChaosLab" linked to /attack
And ≥4 Playwright test cases pass

Given the build succeeds
When `pnpm --filter chaoslab-web build` runs
Then exit code is 0
```

---

## Shell verification

The coding agent runs this to confirm the story is done before opening a PR:

```bash
set -e
cd /Users/abu/dev/hackathon/rapid-agents

# Files exist
test -f apps/chaoslab-web/app/page.tsx
test -f apps/chaoslab-web/app/_components/header.tsx
test -f apps/chaoslab-web/app/_components/footer.tsx
test -f apps/chaoslab-web/app/_components/feature-card.tsx
test -f apps/chaoslab-web/public/og-hero.png
test -f apps/chaoslab-web/tests/e2e/landing.spec.ts

# generateMetadata exported
grep -E "export\s+(const|async\s+function)\s+generateMetadata" apps/chaoslab-web/app/page.tsx

# OG image referenced
grep -E "og-hero\.png" apps/chaoslab-web/app/page.tsx

# Run ChaosLab CTA
grep -E "Run ChaosLab" apps/chaoslab-web/app/page.tsx
grep -E "href=['\"]/attack['\"]" apps/chaoslab-web/app/page.tsx

# Header + footer
grep -E "ChaosLab" apps/chaoslab-web/app/_components/header.tsx
grep -E "Apache-2.0|apache\.org/licenses" apps/chaoslab-web/app/_components/footer.tsx
grep -E "deepankarm/agent-chaos" apps/chaoslab-web/app/_components/footer.tsx

# OG image is a real 1200x630 PNG
file apps/chaoslab-web/public/og-hero.png | grep -E "PNG image"
# Optional sanity check on dimensions (skip if `identify` not installed):
which identify >/dev/null 2>&1 && [ "$(identify -format '%wx%h' apps/chaoslab-web/public/og-hero.png)" = "1200x630" ] || echo "identify not installed; skipping dimensions check"

# Build clean
AGENT_BACKEND_URL=http://localhost:8001 pnpm --filter chaoslab-web build

# Dev server returns 200 + has ChaosLab title
pnpm --filter chaoslab-web start > /tmp/chaoslab-start.log 2>&1 &
START_PID=$!
sleep 5
curl -sf http://localhost:3000 | grep -iE "<title>.*ChaosLab.*</title>"
kill $START_PID || true

# Playwright e2e
pnpm --filter chaoslab-web exec playwright test apps/chaoslab-web/tests/e2e/landing.spec.ts
test "$(pnpm --filter chaoslab-web exec playwright test apps/chaoslab-web/tests/e2e/landing.spec.ts --reporter=list 2>&1 | grep -cE 'passed')" -ge 1

# 400-line guard
test "$(grep -cvE '^\s*(//|$)' apps/chaoslab-web/app/page.tsx)" -le 200
python3 scripts/check_max_lines.py --strict apps/chaoslab-web/app apps/chaoslab-web/app/_components

echo "story-7.9 verification: PASS"
```

---

## Notes for coding agent

- This is the JUDGE'S FIRST IMPRESSION. Polish bar = "v1 of a startup." Every spacing decision matters. Anchor screenshots in story-7.12 will lock the visual identity.
- The one-line pitch is LOCKED in `docs/PRD.md`: "ChaosLab — adversarial resilience testing for AI agents. Inject 4 fault classes, watch them fail, harden automatically." Copy verbatim.
- Page is a SERVER COMPONENT (no `'use client'`). The CTA `<Link>` from next/link is server-friendly. Only the global state pill in the header (added in story-7.11) needs client.
- `generateMetadata()` is async-allowed but for this story a static `export const metadata: Metadata = {...}` is fine and simpler.
- Hero section layout: full-bleed dark background (`bg-background`), centered max-w-3xl content, title `text-6xl md:text-7xl font-display tracking-tight`, pitch `text-xl text-text-secondary max-w-2xl`, CTA button below.
- "How it works" grid: 3 columns desktop / 1 column mobile. Each card is a `<FeatureCard>` with an agent-color icon (Inject → orange, Watch → purple, Harden → emerald). Icons from lucide-react: `Crosshair`, `Activity`, `ShieldCheck`.
- Header layout: `<header className="h-16 flex items-center justify-between px-6 border-b border-surface-raised">` with wordmark on left, links on right.
- Footer is single-row on desktop, stacked on mobile. Include 3 columns: left (build label), center (license + license link), right (vendoring attribution).
- GitHub link href: placeholder `https://github.com/abu/chaoslab` — the real repo URL is set in `docs/cicd.md` once CI lands. Pull from `env.NEXT_PUBLIC_GITHUB_URL` if defined, fallback to a constant. For this story, hardcode the placeholder; story-8.1 replaces with real URL.
- "Run against your agent" link in header points to `/agent/new` (the per-agent setup route, beta, lands later — for now this can be a placeholder href; the route gets a 404 until that story lands, which is acceptable per the ux-spec note).
- OG image: a hand-made 1200×630 PNG placeholder is fine for now. Create with `magick -size 1200x630 xc:'#0F1A2E' -font Geist -pointsize 96 -fill white -gravity center -annotate +0+0 'ChaosLab' apps/chaoslab-web/public/og-hero.png` if ImageMagick is available, otherwise drop in any black/dark 1200x630 PNG with "ChaosLab" text. Story-8.3 replaces with the real cascade-flip frame.
- The placeholder OG image must be a VALID PNG of the right dimensions or `next build` may complain about `next/image` optimization. If the test environment lacks ImageMagick, commit a pre-made placeholder image.
- Banned classes: no `from-purple-500 to-pink-500` (per Tailwind banned list in `architecture.md`), no `text-gray-600` (use `text-text-secondary` token instead), no `font-sans` (use `--font-display` via the body style from story-7.2).
- Test the actual click flow once: load `/`, click "Run ChaosLab", verify URL becomes `/attack`. Playwright test does this.
- Total LOC budget: page.tsx ≤200, header.tsx ≤100, footer.tsx ≤80, feature-card.tsx ≤60. All comfortably under 400.
- DO NOT add any third-party dependencies in this story — everything needed is already in package.json from earlier stories. If you find yourself wanting `lucide-react`: it's a peer dep of shadcn/ui (already installed via story-7.1's shadcn init).
