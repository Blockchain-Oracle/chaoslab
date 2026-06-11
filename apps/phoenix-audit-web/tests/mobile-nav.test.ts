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
    expect(css).toContain(`max-width: ${MOBILE_BREAKPOINT_PX}px`)
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
