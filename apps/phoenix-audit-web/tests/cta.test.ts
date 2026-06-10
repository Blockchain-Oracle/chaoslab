// Every "Run audit" CTA routes through the wizard — the single confirm
// surface (story-9.10). One-click live runs fired real failing audits.

import { describe, expect, it } from 'vitest'
import { historyRowDest, runAuditHref, runHasReport } from '@/lib/cta'

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

describe('historyRowDest / runHasReport', () => {
  const hero = 'run_hero'

  it('sample hero demos the replay', () => {
    expect(historyRowDest({ id: 'run_hero', sample: true }, hero)).toBe('/replay')
  })

  it('real run with a report opens it', () => {
    expect(historyRowDest({ id: 'run_a', sample: false, reportAvailable: true }, hero)).toBe(
      '/report/run_a',
    )
  })

  it('real run WITHOUT a report opens the honest run summary — never a report page', () => {
    expect(historyRowDest({ id: 'run_b', sample: false, reportAvailable: false }, hero)).toBe(
      '/run/run_b',
    )
    expect(runHasReport({ sample: false })).toBe(false)
  })

  it('non-hero samples open their labeled sample report', () => {
    expect(historyRowDest({ id: 'run_s', sample: true }, hero)).toBe('/report/run_s')
  })
})

describe('run attribution', () => {
  it('never falls back to demo-target for unattributed runs', async () => {
    const { runToHistoryRow } = await import('@/lib/api')
    const row = runToHistoryRow({
      run_id: 'run_x',
      agent_id: null,
      target_url: 'https://my-co.example/agent',
      framework_label: 'EU AI Act',
      source: 'manual',
      phase: 'succeeded',
      created_at: '2026-06-10T00:00:00Z',
      finished_at: null,
      duration_sec: null,
      passed: 6,
      failed: 0,
      errored: 0,
      transport_failed: 0,
      recipe_id: null,
      report_available: true,
      mr_url: null,
    })
    expect(row.agentId).toBe('')
    expect(row.targetUrl).toBe('https://my-co.example/agent')
  })
})
