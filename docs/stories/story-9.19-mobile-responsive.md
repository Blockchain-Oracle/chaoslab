# story-9.19 — mobile-responsive: every surface usable at 390×844

**Epic:** 9 · **Depends on:** story-9.13 (report-presentation), story-9.15 (datasets surface)
**Source:** Wave A4 in the unified-finish plan. Designer brief: `docs/assets.md` Surface M (written first, per the S9.14 lesson).

## Why

Judges open Devpost links on phones. Today the product is desktop-only in practice: the topbar's four nav links + CTA overflow at phone widths, the audit chamber's `'390px 1fr'` grid forces horizontal scroll, and the landing comparison's two columns collapse into unreadable slivers. A product that claims "regulator-ready" but breaks on the device a Director of AI Governance actually opens it on undercuts the day-1-user story. This is responsive EXECUTION on existing designer surfaces — no new visual language (presentation layer is sacred); the only new component is the MobileNav.

## BDD acceptance criteria

- **Given** a ≤768px viewport, **when** any product page renders, **then** the topbar shows wordmark + "Run audit" CTA + a hamburger button (no inline nav links, no UserMenu); tapping the hamburger opens a drawer containing the four nav links (active route marked) and the signed-in identity/sign-out affordance. The drawer closes on backdrop tap, Escape, and route navigation. Nav targets are ≥44px tall. **Given** >768px, **then** the current inline nav renders exactly as today (no visual change).
- **Given** the landing page at ≤768px, **then** `landing-nav` collapses to the same hamburger idiom and `compare.tsx`'s `1fr 1fr` grid stacks to one column with the divider rotating from right-hairline to bottom-hairline.
- **Given** the audit chamber at ≤768px, **then** the `'390px 1fr'` grid becomes a single column with the probe rail ABOVE the live feed; nothing requires horizontal scroll at 390px.
- **Given** any of landing / replay / login / audits / chamber / report / datasets at 390×844, **then** no element overflows the viewport horizontally (`document.documentElement.scrollWidth <= 390`), and display headings step down so no heading line exceeds the viewport.
- Vitest pins the pure logic (breakpoint constant, drawer state reducer/handlers, nav model shared between inline + drawer renderings). Playwright (MCP, local dev server) verifies the seven surfaces at 390×844 — overflow assertion + screenshot per surface attached to the PR for the designer's review pass.

## File map

- NEW `components/ui/mobile-nav.tsx` (hamburger + drawer, Framer Motion; designer idiom per Surface M) + NEW `lib/mobile-nav.ts` (pure: `NAV` model lifted from topbar, drawer-state helpers — node-env-testable per project idiom).
- `components/ui/topbar.tsx` — render inline nav OR MobileNav by breakpoint (CSS-first: media query classes, not JS width sniffing, so SSR markup is stable).
- `components/landing/landing-nav.tsx` — same treatment.
- `components/chamber/audit-chamber.tsx:89` — grid template via CSS class with media query (inline style moves to a class).
- `components/landing/compare.tsx:30` — stack + divider flip.
- `app/globals.css` (or equivalent theme layer) — the ≤768px / ≤390px rules + display-type step-downs.
- Tests: `tests/mobile-nav.test.ts` (NEW); Playwright pass via MCP during the story (not wired into CI — e2e remains unwired per CLAUDE.md).

## Notes

- Breakpoint: 768px single source of truth as a CSS custom property + exported constant; the vitest pin keeps the two from drifting.
- The "Run audit" CTA never enters the drawer — it is THE product action (Surface M).
- Inline styles dominate these components; the responsive overrides go through small CSS classes added to the theme layer rather than converting whole components — minimal diff, presentation intact.
- visx charts (resilience curve, attack matrix) already size to containers; verify at 390px but expect no code change.
