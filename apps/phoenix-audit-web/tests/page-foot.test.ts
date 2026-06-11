// PageFoot — source-level pin on the documented links. Story-9.20
// shipped /docs as a real page; the user reported finding it required
// already knowing it existed. Adding a Docs link to the footer is the
// least-intrusive surface increase — the topbar stays at 5 items.

import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'

const src = readFileSync(join(import.meta.dirname, '../components/ui/page-foot.tsx'), 'utf-8')

describe('PageFoot links', () => {
  it('links to /docs so a curious operator can find the manual without typing the URL', () => {
    // The text must be visible (not aria-only). The href is the
    // single-source path; isNavActive isn't a footer concern.
    expect(src).toMatch(/href=['"]\/docs['"]/)
    expect(src).toMatch(/\bDocs\b/)
  })

  it('keeps the GitHub link for trust + provenance', () => {
    expect(src).toMatch(/github\.com\/Blockchain-Oracle\/phoenix-audit/)
  })
})
