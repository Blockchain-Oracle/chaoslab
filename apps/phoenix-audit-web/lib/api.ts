// Typed server-side fetchers for the agent's registry API (story-9.2).
// Server components call these; failures surface as `liveError` so pages can
// render the sample world WITH a visible notice — never silently.

import { parseEventsDocument, type RunEventsDocument } from './replay'
import { agentFetch } from './server/agent-fetch'
import { userIdentityHeaders } from './server/user-fetch'
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
  events_available: boolean
  mr_url: string | null
  owner_uid: string | null
}

export interface AgentRecordDto {
  agent_id: string
  name: string
  url: string
  framework: string
  tier: 1 | 2 | 3
  registered_at: string
  status: 'ok' | 'unreachable'
  owner_uid: string | null
}

export interface ScheduleDto {
  schedule_id: string
  agent_id: string | null
  target_url: string
  cadence: 'hourly' | 'daily'
  enabled: boolean
  next_fire_at: string
  last_fired_at: string | null
  last_run_id: string | null
  deliver_email: boolean
  email_recipient: string | null
  created_at: string
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
    // No fallback attribution: a run without an agent_id renders its REAL
    // target URL — defaulting to 'demo-target' dressed every custom-URL
    // audit as the Demo Support Agent (story-9.10 review finding).
    agentId: dto.agent_id ?? '',
    framework: frameworkChip(dto.framework_label),
    pass: dto.passed,
    fail: dto.failed,
    // Without these a 0-pass/0-fail/6-errored run renders as a clean row.
    errored: dto.errored,
    transportFailed: dto.transport_failed,
    recipe: Boolean(dto.recipe_id),
    mr: Boolean(dto.mr_url),
    source: dto.source,
    targetUrl: dto.target_url,
    reportAvailable: dto.report_available,
    eventsAvailable: dto.events_available,
    // Ownerless records are the seeded REAL sample audits — visible to all,
    // labeled (story-9.11). Loose == also catches an OMITTED field (deploy
    // skew/stale cache) — an unlabeled sample inflating stats is the failure.
    sample: dto.owner_uid == null,
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
    // Ownerless agents are the seeded demo targets — real, runnable, labeled.
    sample: dto.owner_uid == null,
  }
}

async function getJson<T>(
  path: string,
): Promise<{ body: T | null; error: string | null; status: number | null }> {
  try {
    const res = await agentFetch(path, { headers: await userIdentityHeaders() })
    if (!res.ok)
      return { body: null, error: `agent API ${res.status} on ${path}`, status: res.status }
    return { body: (await res.json()) as T, error: null, status: res.status }
  } catch (err) {
    // status null = the registry never answered (network/agent down) —
    // callers must distinguish this from an authoritative 404.
    return { body: null, error: err instanceof Error ? err.message : String(err), status: null }
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

export async function fetchRunDetail(
  runId: string,
): Promise<Live<RunDetailDto | null> & { status: number | null }> {
  const { body, error, status } = await getJson<RunDetailDto>(`/runs/${encodeURIComponent(runId)}`)
  return { data: body, liveError: error, status }
}

export async function fetchSchedules(): Promise<Live<ScheduleDto[]>> {
  const { body, error } = await getJson<{ schedules: ScheduleDto[] }>('/schedules')
  return { data: body?.schedules ?? [], liveError: error }
}

/** The public sample-replay source (no user identity — the endpoint serves
 *  only ownerless seeded runs; agentFetch's service OIDC covers IAM). */
export async function fetchFeaturedRun(): Promise<Live<RunDetailDto | null>> {
  try {
    const res = await agentFetch('/featured-run')
    if (!res.ok) return { data: null, liveError: `agent API ${res.status} on /featured-run` }
    return { data: (await res.json()) as RunDetailDto, liveError: null }
  } catch (err) {
    return { data: null, liveError: err instanceof Error ? err.message : String(err) }
  }
}

export interface EventsFetchResult {
  doc: RunEventsDocument | null
  /** Why the timeline could not be loaded — pages must DISCLOSE this
   *  ("replay recorded but unavailable"), never imply no replay exists. */
  error: string | null
}

/** Server-side fetch of a run's persisted timeline from its signed GCS URL
 *  (server-side: no browser CORS in play). Failures are returned AND logged —
 *  a registry that says events_available=true while the load fails is drift
 *  someone must be able to debug. */
export async function fetchEventsDocument(signedUrl: string): Promise<EventsFetchResult> {
  try {
    const res = await fetch(signedUrl, { cache: 'no-store' })
    if (!res.ok) {
      console.error(`events.json fetch failed: HTTP ${res.status}`)
      return { doc: null, error: `timeline fetch failed (HTTP ${res.status})` }
    }
    const doc = parseEventsDocument(await res.json())
    if (!doc) {
      console.error('events.json failed shape validation')
      return { doc: null, error: 'timeline document failed validation' }
    }
    return { doc, error: null }
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err)
    console.error('events.json fetch error:', msg)
    return { doc: null, error: `timeline fetch error (${msg})` }
  }
}
