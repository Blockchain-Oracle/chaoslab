# story-9.20 — docs-v2: navigable manual + new-feature sections + favicon

**Epic:** 9 · **Depends on:** story-9.19 (mobile-responsive — the docs page renders within its rules), story-9.5 / story-9.15 / story-9.17 (the features the new sections document)
**Source:** Wave A5 in the unified-finish plan. Designer brief: `docs/assets.md` Surface D.

## Why

/docs is the page a judge opens to understand the product without running it, and the page a real compliance officer sends to their engineer. Today it documents seven surfaces and stops — datasets, GitLab connect, and email delivery (all shipped this week) are invisible, and the page is one long scroll with no way to jump. A manual that omits a third of the product reads as abandoned. Plus the cosmetic debt: the favicon 404s on every tab.

## BDD acceptance criteria

- **Given** /docs at ≥1040px, **then** a sticky left rail lists every section (anchor-linked, mono register); clicking an entry scrolls to the section and the active entry tracks the scroll position (IntersectionObserver). **Given** <1040px, **then** the rail is absent and the page reads linearly (post-9.19 responsive rules apply).
- **Given** the section list, **then** it includes four NEW sections with accurate, feature-true copy: **Datasets** (upload JSONL/CSV, run audits with them, per-agent regression sets — story-9.15), **GitLab** (per-user OAuth connect, review-first MR filing, the only-ADDS-files-under-`phoenix-audit/` promise — story-9.17), **Email** (scheduled summaries to the schedule's recipient + "Email me this report" with the signed PDF attached — story-9.5), **Auth & privacy** (what's public vs private, the data-residency paragraph). Existing §6 monitoring copy is updated to mention the email recipient field. No claims about unshipped behavior — every sentence must be true on staging today.
- **Given** each section's `shot` slot, **then** `scripts/capture-docs-shots.ts` covers the new sections (datasets page, settings GitLab card, report-page email button) and captured shots are committed; sections without a committed shot render text-only (existing `shotPath` contract — unchanged).
- **Given** any page in the app, **then** the browser tab shows the brand glyph favicon (`app/icon.svg`) — no more 404.
- Vitest pins the pure logic: the section model (ids unique, anchors derivable), the active-section reducer for the scroll spy, and a source pin that every SECTIONS entry with `shot` names a file the capture script knows.

## File map

- `app/docs/page.tsx` — section model gains `id` (anchor slugs) + 4 new sections; layout gains the rail (grid: rail + content at ≥1040px).
- NEW `components/docs/docs-rail.tsx` (client — scroll spy + anchor list) + NEW `lib/docs-sections.ts` (the SECTIONS model moves here so the rail, the page, and tests share one copy — same single-source pattern as NAV_ITEMS in 9.19).
- `app/icon.svg` — brand glyph favicon (created; ships with this story).
- `scripts/capture-docs-shots.ts` — add the three new captures.
- Tests: `tests/docs-sections.test.ts` (NEW).
- `docs/assets.md` Surface D — brief (written first).

## Notes

- The rail is a CLIENT component; the page stays a server component (the existing `existsSync` build-time screenshot gate must keep working — the model split makes that clean).
- Scroll spy via IntersectionObserver with `rootMargin` tuned so the active state flips when a section's heading crosses the upper third — no scroll-event listeners.
- Screenshot capture happens against staging (signed in as the test user for product surfaces) — same flow the Devpost gallery reuses.
- Keep page under the 400-line cap by the SECTIONS extraction (it's the bulk of the file today).
