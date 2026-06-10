// Every "Run audit" CTA routes through the wizard — the single confirm
// surface (story-9.10). Seeded sample agents are REAL deployed targets
// (story-9.11), so every agent row prefills its real URL.

import { describe, expect, it } from 'vitest'
import { historyRowDest, runAuditHref } from '@/lib/cta'

describe('runAuditHref', () => {
  it('prefills the wizard with id + url', () => {
    expect(runAuditHref({ id: 'demo-target', url: 'https://target-agent-x.a.run.app' })).toBe(
      '/new?agent=demo-target&url=https%3A%2F%2Ftarget-agent-x.a.run.app',
    )
  })

  it('encodes ids defensively', () => {
    expect(runAuditHref({ id: 'a b', url: 'https://t.example' })).toBe(
      '/new?agent=a%20b&url=https%3A%2F%2Ft.example',
    )
  })
})

describe('historyRowDest', () => {
  it('run with a report opens it', () => {
    expect(historyRowDest({ id: 'run_a', reportAvailable: true })).toBe('/report/run_a')
  })

  it('run WITHOUT a report opens the run page (replay or honest summary)', () => {
    expect(historyRowDest({ id: 'run_b', reportAvailable: false })).toBe('/run/run_b')
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
      events_available: false,
      mr_url: null,
      owner_uid: 'user-a',
    })
    expect(row.agentId).toBe('')
    expect(row.targetUrl).toBe('https://my-co.example/agent')
  })
})
