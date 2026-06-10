import { describe, expect, it } from 'vitest'
import { agentToSpec, runToHistoryRow, type AgentRecordDto, type RunRecordDto } from '@/lib/api'
import { mergeAgents, mergeRuns } from '@/lib/sample-merge'
import type { AgentSpec, HistoryRow } from '@/lib/types'

const runDto: RunRecordDto = {
  run_id: 'run_abc123def456',
  agent_id: 'demo-target',
  target_url: 'https://target-agent.example.app',
  framework_label: 'EU AI Act · high-risk system',
  source: 'manual',
  phase: 'succeeded',
  created_at: '2026-06-10T07:00:00Z',
  finished_at: '2026-06-10T07:01:30Z',
  duration_sec: 90.1,
  passed: 5,
  failed: 1,
  errored: 0,
  transport_failed: 0,
  recipe_id: 'recipe_deadbeefcafe',
  report_available: true,
  mr_url: 'https://gitlab.com/Blockchain-Oracle/prior-auth-agent/-/merge_requests/1',
}

describe('runToHistoryRow', () => {
  it('maps the registry DTO to the UI row', () => {
    const row = runToHistoryRow(runDto)
    expect(row.id).toBe('run_abc123def456')
    expect(row.framework).toBe('EU AI Act') // chip text, not the full label
    expect(row.pass).toBe(5)
    expect(row.fail).toBe(1)
    expect(row.recipe).toBe(true)
    expect(row.mr).toBe(true)
    expect(row.mrUrl).toContain('gitlab.com')
    expect(row.targetUrl).toBe('https://target-agent.example.app')
    expect(row.source).toBe('manual')
  })

  it('null agent_id falls back to demo-target and absent mr stays absent', () => {
    const row = runToHistoryRow({ ...runDto, agent_id: null, mr_url: null, recipe_id: null })
    expect(row.agentId).toBe('demo-target')
    expect(row.mr).toBe(false)
    expect(row.mrUrl).toBeUndefined()
    expect(row.recipe).toBe(false)
  })
})

describe('agentToSpec', () => {
  it('maps the agent DTO', () => {
    const dto: AgentRecordDto = {
      agent_id: 'agt_x',
      name: 'X',
      url: 'https://x.example',
      framework: 'adk-a2a',
      tier: 1,
      registered_at: '2026-06-10T00:00:00Z',
      status: 'ok',
    }
    const spec = agentToSpec(dto)
    expect(spec.id).toBe('agt_x')
    expect(spec.transport).toBe('A2A protocol')
    expect(spec.depth).toBe(2)
  })
})

function row(id: string, date: string, sampleAgnostic?: Partial<HistoryRow>): HistoryRow {
  return {
    id,
    date,
    agentId: 'agt_priorauth',
    framework: 'EU AI Act',
    pass: 6,
    fail: 0,
    recipe: false,
    mr: false,
    source: 'manual',
    ...sampleAgnostic,
  }
}

describe('mergeRuns', () => {
  it('tags samples, keeps real untagged, sorts newest first across both', () => {
    const real = [row('run_real1', '2026-06-10T07:00:00Z')]
    const samples = [
      row('run_old1', '2026-06-01T00:00:00Z'),
      row('run_old2', '2026-06-09T00:00:00Z'),
    ]
    const merged = mergeRuns(real, samples)
    expect(merged.map((r) => r.id)).toEqual(['run_real1', 'run_old2', 'run_old1'])
    expect(merged[0]?.sample).toBe(false)
    expect(merged[1]?.sample).toBe(true)
  })
})

describe('mergeAgents', () => {
  it('real agent with same id replaces the sample', () => {
    const spec = (id: string): AgentSpec => ({
      id,
      name: id,
      url: 'https://x',
      framework: 'adk-a2a',
      tier: 1,
      transport: 'A2A protocol',
      depth: 2,
      monitoring: { enabled: false },
      lastAudit: '2026-06-01T00:00:00Z',
      status: 'ok',
    })
    const merged = mergeAgents([spec('demo-target')], [spec('demo-target'), spec('agt_sample')])
    expect(merged.filter((a) => a.id === 'demo-target')).toHaveLength(1)
    expect(merged.find((a) => a.id === 'demo-target')?.sample).toBe(false)
    expect(merged.find((a) => a.id === 'agt_sample')?.sample).toBe(true)
  })
})
