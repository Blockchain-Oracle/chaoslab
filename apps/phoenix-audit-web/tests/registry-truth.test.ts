// Registry truth rules (story-9.10): stats count REAL work only; samples
// hide behind an explicit affordance; artifact links must be earned.

import { describe, expect, it } from 'vitest'
import { realStats, visibleRows } from '@/lib/sample-merge'
import { runToHistoryRow, type RunRecordDto } from '@/lib/api'
import type { MergedRun } from '@/lib/sample-merge'

function row(over: Partial<MergedRun>): MergedRun {
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
  } as MergedRun
}

describe('realStats', () => {
  it('counts only real rows — a fresh account reads 0, not 47', () => {
    const rows = [
      row({ id: 'r1', pass: 6, fail: 0 }),
      row({ id: 'r2', pass: 3, fail: 3 }),
      row({ id: 's1', sample: true, pass: 6, fail: 0 }),
    ]
    expect(realStats(rows)).toEqual({ audits: 2, withFindings: 1, passedClean: 1 })
  })

  it('errored-only runs are neither findings nor clean passes', () => {
    const rows = [row({ id: 'r1', pass: 0, fail: 0, errored: 6 })]
    expect(realStats(rows)).toEqual({ audits: 1, withFindings: 0, passedClean: 0 })
  })
})

describe('visibleRows', () => {
  const rows = [row({ id: 'r1' }), row({ id: 's1', sample: true })]

  it('hides samples by default', () => {
    expect(visibleRows(rows, false).map((r) => r.id)).toEqual(['r1'])
  })

  it('shows samples only on explicit request', () => {
    expect(visibleRows(rows, true).map((r) => r.id)).toEqual(['r1', 's1'])
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
      mr_url: null,
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
