// Registry truth rules (story-9.10/9.11): stats count YOUR work only;
// seeded samples are visible and labeled but never inflate account numbers;
// artifact links must be earned.

import { describe, expect, it } from 'vitest'
import { runToHistoryRow, type RunRecordDto } from '@/lib/api'
import { registryStats } from '@/lib/registry-stats'
import type { HistoryRow } from '@/lib/types'

function row(over: Partial<HistoryRow>): HistoryRow {
  return {
    id: 'run_x',
    date: '2026-06-10T00:00:00Z',
    agentId: 'a',
    framework: 'EU AI Act',
    pass: 0,
    fail: 0,
    recipe: false,
    mr: false,
    source: 'manual',
    sample: false,
    ...over,
  }
}

describe('registryStats', () => {
  it('counts only your rows — seeded samples never inflate account stats', () => {
    const rows = [
      row({ id: 'r1', pass: 6, fail: 0 }),
      row({ id: 'r2', pass: 3, fail: 3 }),
      row({ id: 's1', sample: true, pass: 6, fail: 0 }),
    ]
    expect(registryStats(rows)).toEqual({ audits: 2, withFindings: 1, passedClean: 1 })
  })

  it('errored-only runs are neither findings nor clean passes', () => {
    const rows = [row({ id: 'r1', pass: 0, fail: 0, errored: 6 })]
    expect(registryStats(rows)).toEqual({ audits: 1, withFindings: 0, passedClean: 0 })
  })
})

describe('runToHistoryRow report availability', () => {
  it('carries report_available — "signed PDF" links must be earned', () => {
    const dto = {
      run_id: 'run_a',
      agent_id: null,
      target_url: 'https://t.example',
      framework_label: 'EU AI Act',
      source: 'manual',
      phase: 'failed',
      created_at: '2026-06-10T00:00:00Z',
      finished_at: null,
      duration_sec: null,
      passed: 0,
      failed: 0,
      errored: 6,
      transport_failed: 6,
      recipe_id: null,
      report_available: false,
      events_available: false,
      mr_url: null,
      owner_uid: 'user-a',
    } as RunRecordDto
    expect(runToHistoryRow(dto).reportAvailable).toBe(false)
  })
})

describe('fmtDate', () => {
  it('formats in UTC regardless of host timezone — the label says UTC', async () => {
    const { fmtDate } = await import('@/lib/format')
    // 23:30 UTC would read as next-day 00:30 in GMT+1 if the tz leaked.
    expect(fmtDate('2026-06-09T23:30:00Z')).toBe('09 Jun 2026 · 23:30 UTC')
  })
})
