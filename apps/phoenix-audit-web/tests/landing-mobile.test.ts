// Mobile responsiveness pins for the LANDING surfaces — story-9.19 (M3)
// follow-up. Abu reported the procedure 01-04 cards "everything is very,
// very closed out" at 390×844 — confirmed via DOM measurement: all four
// cards rendered at the same y=4690 in a 4-column grid even on a 390px
// viewport, each ~100px wide. Same shape as the compare grid before
// PR #115 — fixed identically (single column at ≤768px, bottom border
// instead of right). Tests pin both the consumer (the className the
// component renders) and the stylesheet (the @media rule that drives it),
// keeping them from drifting per IF-17.

import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'

const css = readFileSync(join(import.meta.dirname, '../app/globals.css'), 'utf-8')
const procedureSrc = readFileSync(
  join(import.meta.dirname, '../components/landing/procedure.tsx'),
  'utf-8',
)

describe('Procedure component — mobile responsiveness', () => {
  it('renders a `procedure-grid` className so CSS can target it', () => {
    expect(procedureSrc).toContain('className="procedure-grid"')
  })
})

describe('procedure-grid CSS — single column at ≤768px (M-3 follow-up)', () => {
  it('lives INSIDE the existing @media (max-width: 768px) block (not a duplicate — IF-17)', () => {
    // Lightning CSS merges duplicate @media blocks UPWARD into the first
    // occurrence. A second `@media (max-width: 768px)` block would
    // silently move responsive rules out of cascade order. The pin
    // counts the occurrences and rejects any new duplicate.
    const matches = css.match(/@media \(max-width: 768px\)/g) || []
    expect(matches.length).toBe(1)
  })

  it('overrides the desktop 4-column grid to a single column', () => {
    expect(css).toMatch(/\.procedure-grid\s*\{[^}]*grid-template-columns:\s*minmax\(0,\s*1fr\)/)
  })

  it('flips the inter-card right-border to a bottom-border on the first three cards', () => {
    // The desktop layout draws vertical hairlines between the 4 cards
    // (the 4th has none). At single-column, those become horizontal
    // hairlines BETWEEN cards. Mirrors compare-grid's IF-17 fix.
    expect(css).toMatch(/\.procedure-grid\s*>\s*div:not\(:last-child\)/)
  })
})
