// Every "Run audit" CTA routes through the wizard — the single confirm
// surface (story-9.10). One-click live runs fired real failing audits.

import { describe, expect, it } from 'vitest'
import { runAuditHref } from '@/lib/cta'

describe('runAuditHref', () => {
  it('real agents prefill the wizard with id + url', () => {
    expect(
      runAuditHref({ id: 'demo-target', url: 'https://target-agent-x.a.run.app', sample: false }),
    ).toBe('/new?agent=demo-target&url=https%3A%2F%2Ftarget-agent-x.a.run.app')
  })

  it('sample agents open a blank wizard — fixture URLs must not be runnable', () => {
    expect(
      runAuditHref({
        id: 'agt_priorauth',
        url: 'https://agents.meridianmutual.example',
        sample: true,
      }),
    ).toBe('/new')
  })

  it('encodes ids defensively', () => {
    expect(runAuditHref({ id: 'a b', url: 'https://t.example', sample: false })).toBe(
      '/new?agent=a%20b&url=https%3A%2F%2Ft.example',
    )
  })
})
