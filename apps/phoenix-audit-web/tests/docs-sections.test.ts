// Story-9.20 — the docs section model + scroll-spy logic. The rail and the
// page both render from lib/docs-sections (single-source, like NAV_ITEMS);
// these pins keep anchors unique, the new-feature sections present, and the
// spy reducer honest.

import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import { SECTIONS, activeSection } from '@/lib/docs-sections'

describe('SECTIONS model', () => {
  it('has unique, anchor-safe ids', () => {
    const ids = SECTIONS.map((s) => s.id)
    expect(new Set(ids).size).toBe(ids.length)
    for (const id of ids) expect(id).toMatch(/^[a-z0-9-]+$/)
  })

  it('documents the new-feature surfaces (9.5 email, 9.15 datasets, 9.17 gitlab, privacy)', () => {
    const ids = SECTIONS.map((s) => s.id)
    expect(ids).toEqual(expect.arrayContaining(['datasets', 'gitlab', 'email', 'privacy']))
  })

  it('numbers sections sequentially — the rail and headings derive from order', () => {
    SECTIONS.forEach((s, i) => expect(s.no).toBe(`§${i + 1}`))
  })

  it('keeps the GitLab adds-only promise in the copy — the trust sentence', () => {
    const gitlab = SECTIONS.find((s) => s.id === 'gitlab')
    expect(gitlab).toBeDefined()
    expect(gitlab!.body.join(' ')).toContain('phoenix-audit/')
    expect(gitlab!.body.join(' ').toLowerCase()).toContain('only adds')
  })

  it('page and rail render from THIS model (no second copy to drift)', () => {
    const page = readFileSync('app/docs/page.tsx', 'utf8')
    expect(page).toContain("from '@/lib/docs-sections'")
    expect(page).not.toMatch(/const SECTIONS[:\s]/)
    const rail = readFileSync('components/docs/docs-rail.tsx', 'utf8')
    expect(rail).toContain("from '@/lib/docs-sections'")
  })
})

describe('activeSection — scroll-spy reducer', () => {
  it('picks the LAST section whose top has crossed the threshold', () => {
    expect(activeSection(['what', 'signin', 'agents'], new Set(['what']))).toBe('what')
    expect(activeSection(['what', 'signin', 'agents'], new Set(['what', 'signin']))).toBe('signin')
  })

  it('falls back to the first section when nothing has crossed yet', () => {
    expect(activeSection(['what', 'signin'], new Set())).toBe('what')
  })

  it('ignores ids not in the model order', () => {
    expect(activeSection(['what', 'signin'], new Set(['rogue', 'what']))).toBe('what')
  })
})
