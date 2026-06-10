// Pins the navigation contract Abu's UX feedback established (story-9.13):
// the "recipe" link in the audits table goes to Surface G at /recipe/[runId],
// NOT back to /report/[runId] where the user would have to scroll to find
// the recipe page. A regression to the old href silently drops Surface G
// discoverability — the only way users reach the standalone recipe view.

import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'

describe('audits-client recipe link contract', () => {
  it('routes "recipe" cells to /recipe/[runId] (Surface G), not the report preview', () => {
    const src = readFileSync(
      join(import.meta.dirname, '../components/history/audits-client.tsx'),
      'utf-8',
    )
    // Pinned shape: `to={'recipe/' + run.id}`. The source-level assertion is
    // narrow so it catches BOTH a revert to the old `report/...?page=recipe`
    // shape AND a typo'd path (`recipes/`, `/recipe`).
    expect(src).toMatch(/to=\{'recipe\/' \+ run\.id\}/)
    expect(src).not.toMatch(/to=\{'report\/' \+ run\.id \+ '\?page=recipe'\}/)
  })
})
