# Mobile responsiveness audit — 2026-06-11, 390×844 (iPhone 14 class)

Working note. Surfaces walked top-to-bottom with Playwright + full-page
screenshots; findings + remediation here, fixes land in
`feat/ux-polish-mobile-404-docs`. Done = the page reads and operates
without horizontal overflow, cropped text, or multi-column layouts that
should have stacked.

## Surface checklist

- [x] / (landing) — full-page screenshot inspected
- [ ] /login
- [ ] /onboarding (5 steps)
- [ ] /audits
- [ ] /agents
- [ ] /agents/[id]
- [ ] /datasets (will use the new modal + new nav)
- [ ] /datasets/[slug]
- [ ] /monitoring
- [ ] /settings
- [ ] /docs
- [ ] /new
- [ ] /run/[id] (live audit / replay)
- [ ] /report/[id]
- [ ] /404 (custom not-found)

## Landing — findings + fixes

| #   | Component                                                                               | Bug at 390×844                                                                                                                                                                | Fix                                                                                                                                            |
| --- | --------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| L1  | `Hero`                                                                                  | Above-the-fold reads OK; the watch-sample CTA strip is fine                                                                                                                   | none                                                                                                                                           |
| L2  | `CascadeStory` (the chamber, "Three failures · One root cause · Patch in four seconds") | 5-column grid `1fr auto 1fr auto 1fr` cramped — failure cards + arrows + root cause + arrows + recipe diff all squeezed into 390px. **The killer demo moment is unreadable.** | Stack vertically at ≤768px: failures column → DOWN arrow → root-cause card → DOWN arrow → hardening recipe. Reuse `CascadeArrows` rotated 90°. |
| L3  | `Procedure` (the "01–04 From address to signed instrument")                             | 4-column grid, each card ~95px wide, text cramped to 5–6 words per line                                                                                                       | **Fixed earlier this session** (`procedure-grid` className + ≤768px stacks to one column with horizontal hairlines)                            |
| L4  | `Frameworks` (the agent-support ledger table)                                           | 4-column `<table>`; default browser layout overflows or squeezes                                                                                                              | Wrap table in a `overflow-x: auto` scroller at ≤768px so the user can swipe; keep desktop intact                                               |
| L5  | `Compare` (the cost / turnaround Big-4)                                                 | 2-col grid already collapses to 1-col at ≤768px (IF-17 pattern)                                                                                                               | none                                                                                                                                           |
| L6  | `ClosingCta` ("File something a regulator will respect.")                               | 3-column `auto 1fr auto` (seal · text · buttons); at 390px the text column compresses to ~60px and EVERY WORD wraps to its own vertical line — looks like the page is broken  | Stack vertically at ≤768px: seal centered → headline + paragraph (full width) → CTA buttons stacked                                            |
| L7  | `PageFoot`                                                                              | Flex-wraps OK, but a long signed-in email in the meta strip pushes width                                                                                                      | acceptable for landing (no UserMenu)                                                                                                           |

## Plan

Fix CascadeStory (L2) + ClosingCta (L6) first — both are full-page-breaking. Then Frameworks (L4). Then continue to /login, /onboarding, … per the checklist. Each surface gets a TDD source-pin (CSS class + media-query presence) before the implementation.
