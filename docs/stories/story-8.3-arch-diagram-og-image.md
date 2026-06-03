# Story — Mermaid architecture diagram + Devpost OG image

**ID:** story-8.3-arch-diagram-og-image
**Epic:** Epic 8 — README + Submission polish
**Depends on:** Should run AFTER all other epics (E1–E7) complete; the OG screenshot specifically requires Epic 7 (`/replay` route + cascade-flip animation at the 2:15 frame) to be visually finished
**Estimate:** ~1.5h
**Status:** PENDING

**Tags:** `[docs, p0, submission]`

---

## User story

**As a** Stage-2 judge skimming the README on GitHub mobile AND a viewer encountering the Devpost project card / X share / LinkedIn share with the OG image preview,
**I want to** see a Mermaid architecture diagram rendered inline on GitHub showing the 3 Cloud Run services + ADK sub-agent composition + Phoenix loop + GitLab MR emission, AND a 1200×630 hero PNG of the cascade-flip moment as the Devpost cover + Open Graph image,
**So that** (a) the README's visual "I can see this is real" hit lands before any text is read (Pattern D production polish per `brainstorm/05-prior-winners.md` §"Pattern D"), and (b) every Devpost / social share of the project URL displays the wow-moment frame instead of a blank gray rectangle

---

## File modification map

Exact files the coding agent creates or modifies for this story:

- `README.md` — UPDATE — inserts a new `## Architecture` section between the demo section and the run-locally section. Contains a Mermaid code block (` ```mermaid ... ``` `) that GitHub renders natively. The diagram shows:
  - 3 Cloud Run services as boxes: `chaoslab-web` (Next.js), `chaoslab-agent` (ADK orchestrator), `target-agent` (naive victim)
  - Inside `chaoslab-agent`: a SequentialAgent containing 3 sub-agents (`Injector`, `Judge`, `Patcher`) per ADR-002
  - `chaoslab-agent` → `target-agent` arrow labeled "A2A (RemoteA2aAgent)"
  - `Injector` and `Judge` both arrow into a `Phoenix Cloud` node labeled "OpenInference spans + experiments + annotations" per ADR-004/ADR-005
  - `Patcher` arrows out to two terminals: `GitLab MR via gitlab.com/api/v4/mcp` (per ADR-011) and `GCS Markdown artifact`
  - `chaoslab-web` connects to `chaoslab-agent` via SSE (`/api/stream`)
  - Diagram is `flowchart LR` (left-to-right) for landscape README rendering. Total Mermaid block ≤60 lines.
- `apps/chaoslab-web/public/og-hero.png` — NEW — 1200×630 PNG generated via Playwright screenshot of the `/replay` route paused at the 2:15 frame state (matrix mid-cascade-flip, curve mid-jump, PATCH line visible) per `docs/ux-spec.md` §"Devpost OG image". File is a real PNG committed to the repo (NOT an SVG, NOT a placeholder). File size target ≤500KB (well under the `check-added-large-files` pre-commit hook's 500KB threshold from story-1.2; if larger, optimize via `pngquant --quality=80-95` or `oxipng -o 4`).
- `apps/chaoslab-web/scripts/capture-og-image.ts` — NEW — Playwright capture script (≤120 lines) that: (1) launches a Playwright Chromium with viewport 1200×630, deviceScaleFactor=2 for retina sharpness; (2) navigates to `http://localhost:3000/replay?freeze=2.15s` (the `/replay` route accepts a `freeze` query param landed in story-7.10 that pauses the animation at a specific timestamp); (3) waits for the `data-testid="cascade-flip-frozen-2.15"` selector to appear (set by `/replay` page when freeze frame is rendered); (4) takes a screenshot to `apps/chaoslab-web/public/og-hero.png`; (5) re-saves the screenshot resized to exact 1200×630 via Playwright's `page.screenshot({ clip: { x: 0, y: 0, width: 1200, height: 630 } })`. CLI: `pnpm tsx apps/chaoslab-web/scripts/capture-og-image.ts`. Used by Abu locally OR by CI to regenerate the asset.
- `apps/chaoslab-web/app/(demo)/replay/page.tsx` — UPDATE — adds a `?freeze=2.15s` query param handler that pauses the cascade-flip animation at a specific timestamp and sets `data-testid="cascade-flip-frozen-2.15"` on the matrix container. Story-7.10 owns the route; this story adds the freeze-frame escape hatch needed for the capture script. ≤30 line diff.
- `apps/chaoslab-web/app/layout.tsx` — UPDATE — sets `generateMetadata()` (or static `metadata` export) with `openGraph.images = [{ url: "/og-hero.png", width: 1200, height: 630 }]` AND `twitter.card = "summary_large_image"` + `twitter.images = ["/og-hero.png"]` per `docs/ux-spec.md` §"Devpost OG image". ≤25 line diff.
- `apps/chaoslab-web/tests/unit/og-metadata.test.ts` — NEW — vitest test (≤80 lines, ≥3 tests) asserting the `generateMetadata()` output has the correct `openGraph.images[0].width === 1200`, `height === 630`, and `url` ends with `/og-hero.png`. One test asserts the PNG actually exists at the expected public path.
- `Makefile` — UPDATE — adds `capture-og` target wrapping the capture script. One-line addition.

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

---

## Acceptance criteria (BDD — machine-verifiable)

````
Given README.md exists
When `grep -F '```mermaid' README.md` runs (the gate from story brief, escaped)
Then exit 0 (Mermaid code block present)

Given README.md has the Mermaid block
When `grep -E "chaoslab-(web|agent)|target-agent|Phoenix|GitLab|Injector|Judge|Patcher" README.md | wc -l` runs
Then output ≥ 7 (all key services + sub-agents appear in the diagram)

Given README.md has the Mermaid block
When `awk '/```mermaid/,/```$/' README.md | grep -E "(flowchart|graph) (LR|TB|TD)"` runs
Then exit 0 (valid Mermaid diagram declaration)

Given the OG hero PNG exists
When `test -f apps/chaoslab-web/public/og-hero.png` runs (the gate from story brief)
Then exit 0

Given the OG hero PNG exists
When `file apps/chaoslab-web/public/og-hero.png` runs (verbatim gate from story brief)
Then output contains "PNG image data, 1200 x 630"
And the same `file` output contains "8-bit/color RGB" or "8-bit/color RGBA" (real image, not 1x1 placeholder)

Given the OG PNG exists
When `stat -f%z apps/chaoslab-web/public/og-hero.png` runs (or `stat -c%s` on Linux)
Then output is ≤ 500000 (under pre-commit large-file gate)
And output is ≥ 50000 (real content, not an empty stub)

Given the capture script exists
When `test -f apps/chaoslab-web/scripts/capture-og-image.ts` runs
Then exit 0
And `pnpm --filter chaoslab-web exec tsx --check apps/chaoslab-web/scripts/capture-og-image.ts` exits 0 (valid TS syntax)

Given the layout.tsx has been updated
When `grep -E "(openGraph|og-hero.png)" apps/chaoslab-web/app/layout.tsx | wc -l` runs
Then output ≥ 2

Given the vitest test exists
When `pnpm --filter chaoslab-web test -- og-metadata.test.ts` runs
Then exit code is 0
And output reports ≥ 3 passing tests

Given the Makefile was updated
When `grep -E "^capture-og:" Makefile` runs
Then exit 0

Given all files
When line counts are checked
Then `capture-og-image.ts` is ≤ 400 lines AND `og-metadata.test.ts` is ≤ 400 lines AND README.md is ≤ 400 lines
````

---

## Shell verification

The coding agent runs this to confirm the story is done before opening a PR:

````bash
set -e
cd /Users/abu/dev/hackathon/rapid-agents

# Mermaid block in README
grep -F '```mermaid' README.md
awk '/```mermaid/,/```$/' README.md | grep -qE "(flowchart|graph) (LR|TB|TD)"
[ "$(grep -cE 'chaoslab-(web|agent)|target-agent|Phoenix|GitLab|Injector|Judge|Patcher' README.md)" -ge 7 ]

# OG PNG real
test -f apps/chaoslab-web/public/og-hero.png
file apps/chaoslab-web/public/og-hero.png | grep -E "PNG image data, 1200 x 630"
file apps/chaoslab-web/public/og-hero.png | grep -E "8-bit/color RG?BA?"

# OG PNG size sane (50KB ≤ size ≤ 500KB)
SIZE=$(stat -f%z apps/chaoslab-web/public/og-hero.png 2>/dev/null || stat -c%s apps/chaoslab-web/public/og-hero.png)
[ "$SIZE" -le 500000 ] && [ "$SIZE" -ge 50000 ]

# Capture script valid TS
test -f apps/chaoslab-web/scripts/capture-og-image.ts
pnpm --filter chaoslab-web exec tsc --noEmit apps/chaoslab-web/scripts/capture-og-image.ts

# Layout metadata wired
grep -E "(openGraph|og-hero.png)" apps/chaoslab-web/app/layout.tsx | wc -l | awk '$1 < 2 { exit 1 }'

# Replay freeze-frame handler exists
grep -E "freeze.*2\.15|cascade-flip-frozen-2\.15" apps/chaoslab-web/app/\(demo\)/replay/page.tsx

# Vitest OG test passes
cd apps/chaoslab-web && pnpm test -- og-metadata.test.ts
cd /Users/abu/dev/hackathon/rapid-agents

# Makefile target
grep -E "^capture-og:" Makefile

# Line counts
[ "$(wc -l < apps/chaoslab-web/scripts/capture-og-image.ts)" -le 400 ]
[ "$(wc -l < apps/chaoslab-web/tests/unit/og-metadata.test.ts)" -le 400 ]
python3 scripts/check_max_lines.py --strict

echo "story-8.3 verification: PASS"
````

---

## Notes for coding agent

- The Mermaid diagram is rendered by GitHub natively (no plugin, no Action) since 2022 — just use a ` ```mermaid ... ``` ` fenced code block in markdown. Devpost does NOT render Mermaid in their project description field, so this diagram lives in README.md only; for the Devpost form, the OG image carries the visual weight.
- Suggested Mermaid skeleton (refine for clarity, keep under 60 lines):

  ```mermaid
  flowchart LR
    User[👤 Judge / Developer] --> Web[chaoslab-web<br/>Cloud Run<br/>Next.js 16]
    Web -- SSE /api/stream --> Agent[chaoslab-agent<br/>Cloud Run<br/>ADK SequentialAgent]
    Agent --> Injector[Injector sub-agent<br/>4 fault classes]
    Agent --> Judge[Judge sub-agent<br/>LLM-as-judge + clustering]
    Agent --> Patcher[Patcher sub-agent<br/>HardeningRecipe]
    Injector -- A2A RemoteA2aAgent --> Target[target-agent<br/>Cloud Run<br/>naive ADK victim]
    Injector -- OpenInference spans --> Phoenix[(Phoenix Cloud<br/>chaoslab-demo project)]
    Judge -- experiments + annotations --> Phoenix
    Patcher --> GitLab[GitLab MR<br/>gitlab.com/api/v4/mcp]
    Patcher --> GCS[(GCS<br/>Markdown artifact)]
  ```

- The `/replay?freeze=2.15s` route handler MUST exist BEFORE the capture script runs. If story-7.10 didn't land it, add the freeze-frame escape hatch in this story (it's already in the file map). Keep the freeze logic simple: when `searchParams.freeze === "2.15s"`, set the Zustand run-store to the 2.15-second timestamp snapshot and disable the SSE listener so the animation doesn't move past it.
- Playwright must be installed in `chaoslab-web` already (per `docs/architecture.md` test framework list). If not, `pnpm add -D @playwright/test playwright` first.
- The capture script needs the chaoslab-web dev server running. The Makefile `capture-og` target should be: `pnpm --filter chaoslab-web dev & DEV_PID=$!; sleep 8; pnpm --filter chaoslab-web exec tsx apps/chaoslab-web/scripts/capture-og-image.ts; kill $DEV_PID`. Document this in the script's top comment.
- Image dimensions are exact: 1200×630. NOT 1200×627, NOT 1280×640. Devpost + Open Graph + Twitter all expect this aspect ratio. The `file` command output verifies dimensions to byte-precision.
- The PNG is a committed binary — `git lfs` is NOT required at this size (<500KB). Pre-commit hook's `check-added-large-files` allows up to 500KB per story-1.2's config. If `pngquant` reduces below 200KB without visible loss, do it.
- If Abu's dev environment is headless (VPS), the capture script needs `playwright install chromium` first AND a virtual display (`xvfb-run`). Document in the script header.
- The OG image is regenerated on every visual-anchor change, but committed to the repo so judges see it even before the staging Cloud Run wakes up. Do NOT lazy-generate the OG from the live service.
- `apps/chaoslab-web/public/og-hero.png` is referenced by both `README.md` (story-8.1) AND `layout.tsx` metadata — single source of truth. If the file path changes, update both.
