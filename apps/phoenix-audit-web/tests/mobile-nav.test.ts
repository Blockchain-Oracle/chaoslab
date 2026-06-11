// Story-9.19 — MobileNav pure logic. The drawer component is a thin shell
// (node-env vitest idiom); what's pinned here: the shared nav model, the
// breakpoint single-source-of-truth, and the drawer-state transitions that
// guard against a stuck-open drawer after navigation.

import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import { MOBILE_BREAKPOINT_PX, NAV_ITEMS, drawerReducer, isNavActive } from '@/lib/mobile-nav'

describe('NAV_ITEMS — single nav model for inline topbar AND drawer', () => {
  it('carries the four product destinations in order', () => {
    expect(NAV_ITEMS.map(([slug]) => slug)).toEqual(['audits', 'agents', 'monitoring', 'settings'])
  })

  it('topbar.tsx renders from THIS model (no second copy to drift)', () => {
    const src = readFileSync('components/ui/topbar.tsx', 'utf8')
    expect(src).toContain('NAV_ITEMS')
    expect(src).not.toMatch(/const NAV[:\s]/)
  })
})

describe('MOBILE_BREAKPOINT_PX — single source of truth', () => {
  it('is 768', () => {
    expect(MOBILE_BREAKPOINT_PX).toBe(768)
  })

  it('matches the CSS media-query breakpoint (constant ↔ stylesheet pin)', () => {
    const css = readFileSync('app/globals.css', 'utf8')
    expect(css).toContain(`@media (max-width: ${MOBILE_BREAKPOINT_PX}px)`)
  })

  it('keeps the !important on the desktop-nav hide — landing-nav inline display:flex loses ONLY because of it', () => {
    const css = readFileSync('app/globals.css', 'utf8')
    const mobileBlock = css.slice(css.indexOf(`@media (max-width: ${MOBILE_BREAKPOINT_PX}px)`))
    expect(mobileBlock).toContain('display: none !important')
  })

  it('has the ≤390px display step-down block', () => {
    const css = readFileSync('app/globals.css', 'utf8')
    expect(css).toContain('@media (max-width: 390px)')
  })
})

describe('landing-nav — same hamburger idiom as the topbar (BDD criterion 2)', () => {
  it('mounts MobileNav and tags its desktop-only elements', () => {
    const src = readFileSync('components/landing/landing-nav.tsx', 'utf8')
    expect(src).toContain('<MobileNav />')
    expect(src).toContain('className="nav-desktop"')
    // The secondary CTA hides on mobile; the primary "Run audit" stays.
    expect(src).toContain('btn small ghost nav-desktop')
  })
})

describe('mobile-nav component invariants (Surface M)', () => {
  it('renders from the shared NAV_ITEMS — no second nav copy to drift', () => {
    const src = readFileSync('components/ui/mobile-nav.tsx', 'utf8')
    expect(src).toContain('NAV_ITEMS')
    expect(src).not.toMatch(/const NAV[:\s]/)
  })

  it('the "Run audit" CTA never enters the drawer — it is THE product action', () => {
    const src = readFileSync('components/ui/mobile-nav.tsx', 'utf8')
    expect(src).not.toContain('Run audit')
  })
})

describe('isNavActive', () => {
  it('matches exact and nested routes', () => {
    expect(isNavActive('/audits', 'audits')).toBe(true)
    expect(isNavActive('/audits/run_abc', 'audits')).toBe(true)
    expect(isNavActive('/agents/x', 'agents')).toBe(true)
  })

  it('does not match unrelated routes or the landing page', () => {
    expect(isNavActive('/', 'audits')).toBe(false)
    expect(isNavActive('/auditschamber', 'audits')).toBe(false)
    // The pre-9.19 topbar used route.startsWith(slug), which would have
    // matched these — the segment-aware behavior is deliberate (PR #115 M1).
    expect(isNavActive('/audits-x', 'audits')).toBe(false)
    expect(isNavActive('/agentsmonitoring', 'agents')).toBe(false)
  })
})

describe('drawerReducer', () => {
  it('toggles open/closed', () => {
    expect(drawerReducer(false, { type: 'toggle' })).toBe(true)
    expect(drawerReducer(true, { type: 'toggle' })).toBe(false)
  })

  it('closes on backdrop, escape, and navigation — never opens from them', () => {
    for (const type of ['backdrop', 'escape', 'navigate'] as const) {
      expect(drawerReducer(true, { type })).toBe(false)
      expect(drawerReducer(false, { type })).toBe(false)
    }
  })
})
