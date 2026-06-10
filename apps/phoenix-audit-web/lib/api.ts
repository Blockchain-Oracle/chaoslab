// Typed server-side fetchers for the agent's registry API (story-9.2).
// Server components call these; failures surface as `liveError` so pages can
// render the sample world WITH a visible notice — never silently.

import { agentFetch } from './server/agent-fetch'
import type { AgentSpec, HistoryRow } from './types'

export interface RunRecordDto {
  run_id: string
  agent_id: string | null
  target_url: string
  framework_label: string
  source: 'manual' | 'scheduled'
  phase: string
  created_at: string
  finished_at: string | null
  duration_sec: number | null
  passed: number
  failed: number
  errored: number
  transport_failed: number
  recipe_id: string | null
  report_available: boolean
  mr_url: string | null
}

export interface AgentRecordDto {
  agent_id: string
  name: string
  url: string
  framework: string
  tier: 1 | 2 | 3
  registered_at: string
  status: 'ok' | 'unreachable'
}

export interface RunDetailDto {
  run: RunRecordDto
  artifact_urls: Record<string, string>
  artifact_url_errors: Record<string, string>
}

export interface Live<T> {
  data: T
  /** Set when the live registry could not be reached — pages must DISCLOSE
   *  this (sample-only view), never render silently. */
  liveError: string | null
}

/** "EU AI Act · high-risk system" → "EU AI Act" (the chip text). */
function frameworkChip(label: string): string {
  return label.split('·')[0]?.trim() || label
}

export function runToHistoryRow(dto: RunRecordDto): HistoryRow {
  return {
    id: dto.run_id,
    date: dto.created_at,
    agentId: dto.agent_id ?? 'demo-target',
    framework: frameworkChip(dto.framework_label),
    pass: dto.passed,
    fail: dto.failed,
    recipe: Boolean(dto.recipe_id),
    mr: Boolean(dto.mr_url),
    source: dto.source,
    targetUrl: dto.target_url,
    ...(dto.mr_url ? { mrUrl: dto.mr_url } : {}),
  }
}

export function agentToSpec(dto: AgentRecordDto): AgentSpec {
  return {
    id: dto.agent_id,
    name: dto.name,
    url: dto.url,
    framework: dto.framework,
    tier: dto.tier,
    transport: dto.framework === 'adk-a2a' ? 'A2A protocol' : 'HTTP endpoint',
    depth: dto.tier === 3 ? 1 : 2,
    monitoring: { enabled: false },
    lastAudit: dto.registered_at,
    status: dto.status,
  }
}

async function getJson<T>(path: string): Promise<{ body: T | null; error: string | null }> {
  try {
    const res = await agentFetch(path)
    if (!res.ok) return { body: null, error: `agent API ${res.status} on ${path}` }
    return { body: (await res.json()) as T, error: null }
  } catch (err) {
    return { body: null, error: err instanceof Error ? err.message : String(err) }
  }
}

export async function fetchRuns(agentId?: string): Promise<Live<RunRecordDto[]>> {
  const qs = agentId ? `?agent_id=${encodeURIComponent(agentId)}` : ''
  const { body, error } = await getJson<{ runs: RunRecordDto[] }>(`/runs${qs}`)
  return { data: body?.runs ?? [], liveError: error }
}

export async function fetchAgents(): Promise<Live<AgentRecordDto[]>> {
  const { body, error } = await getJson<{ agents: AgentRecordDto[] }>('/agents')
  return { data: body?.agents ?? [], liveError: error }
}

export async function fetchRunDetail(runId: string): Promise<Live<RunDetailDto | null>> {
  const { body, error } = await getJson<RunDetailDto>(`/runs/${encodeURIComponent(runId)}`)
  return { data: body, liveError: error }
}
