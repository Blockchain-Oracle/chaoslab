import { describe, expect, it } from 'vitest'
import { agentToSpec, runToHistoryRow, type AgentRecordDto, type RunRecordDto } from '@/lib/api'

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
  events_available: true,
  mr_url: 'https://gitlab.com/Blockchain-Oracle/prior-auth-agent/-/merge_requests/1',
  owner_uid: 'user-a',
}

describe('runToHistoryRow', () => {
  it('maps the registry DTO to the UI row', () => {
    const row = runToHistoryRow(runDto)
    expect(row.id).toBe('run_abc123def456')
    expect(row.framework).toBe('EU AI Act') // chip text, not the full label
    expect(row.pass).toBe(5)
    expect(row.fail).toBe(1)
    expect(row.errored).toBe(0)
    expect(row.transportFailed).toBe(0)
    expect(row.recipe).toBe(true)
    expect(row.mr).toBe(true)
    expect(row.mrUrl).toContain('gitlab.com')
    expect(row.targetUrl).toBe('https://target-agent.example.app')
    expect(row.source).toBe('manual')
    expect(row.eventsAvailable).toBe(true)
  })

  it('surfaces errored/transport_failed — an all-errored run must not look clean', () => {
    const row = runToHistoryRow({
      ...runDto,
      passed: 0,
      failed: 0,
      errored: 6,
      transport_failed: 2,
    })
    expect(row.errored).toBe(6)
    expect(row.transportFailed).toBe(2)
  })

  it('null agent_id stays unattributed (story-9.10) and absent mr stays absent', () => {
    const row = runToHistoryRow({ ...runDto, agent_id: null, mr_url: null, recipe_id: null })
    expect(row.agentId).toBe('')
    expect(row.mr).toBe(false)
    expect(row.mrUrl).toBeUndefined()
    expect(row.recipe).toBe(false)
  })

  it('ownerless runs are the labeled seeded samples; owned runs are not', () => {
    expect(runToHistoryRow({ ...runDto, owner_uid: null }).sample).toBe(true)
    expect(runToHistoryRow(runDto).sample).toBe(false)
  })
})

describe('agentToSpec', () => {
  const dto: AgentRecordDto = {
    agent_id: 'agt_x',
    name: 'X',
    url: 'https://x.example',
    framework: 'adk-a2a',
    tier: 1,
    registered_at: '2026-06-10T00:00:00Z',
    status: 'ok',
    owner_uid: 'user-a',
  }

  it('maps the agent DTO', () => {
    const spec = agentToSpec(dto)
    expect(spec.id).toBe('agt_x')
    expect(spec.transport).toBe('A2A protocol')
    expect(spec.depth).toBe(2)
    expect(spec.sample).toBe(false)
  })

  it('ownerless agents are the labeled seeded demo targets', () => {
    expect(agentToSpec({ ...dto, owner_uid: null }).sample).toBe(true)
  })
})
