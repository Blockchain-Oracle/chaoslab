'use client'

import { useEffect, useRef, useState } from 'react'
import { TIMELINE } from './fixtures'
import type { Phase } from './types'

// Hybrid SSE bridge — real /stream events drive the chamber. Phases gate the
// local clock so the timeline ticker can't run past the real backend phase;
// when the backend emits per-probe events (test_started / test_completed /
// test_verdict / cluster_set / recipe) the chamber renders THOSE and the
// DEMO PACING disclosure disappears. See SPEC.md for the contract.

/** One adversarial probe as reported by the REAL backend event stream. */
export interface LiveProbe {
  n: number
  faultClass: string
  state: 'running' | 'done'
  status?: string
  spanId?: string
  /** `error` = the judge rubric itself failed (rate limit / safety block) —
   *  a MARKED non-verdict, never coerced into pass or fail. */
  verdict?: 'pass' | 'fail' | 'error'
  transportError?: boolean
  rubricError?: boolean
  score?: number
}

export interface LiveCluster {
  clusters: number
  totalFailures: number
  clusterIds: string[]
  rootCauses: string[]
  /** Failures excluded from clustering because they carried no span evidence. */
  excludedTransportFailures: number
  /** Probes whose rubric call itself errored — also unclusterable. */
  rubricErrors: number
  /** Clustering succeeded but Phoenix rejected the annotation write-back. */
  annotationWritebackFailed: boolean
  /** Set when failures existed but none were clusterable. */
  skipped?: string
}

export interface LiveRecipe {
  recipeId: string
  markdownUrl: string | null
}

export interface LiveReport {
  pdfUrl: string | null
  jsonUrl: string | null
  signatureUrl: string | null
  /** Set when the backend skipped report generation (e.g. signing key
   *  not configured) — surfaced, never silent. */
  skippedReason: string | null
}

export interface AuditStreamState {
  connected: boolean
  phase: Phase
  /** Maximum t (seconds) the chamber's local clock may advance to. Keyed to
   *  real phase transitions so the visual stays honest about what the
   *  backend is actually doing. */
  clockCeiling: number
  /** Raw wire lines (event + JSON payload) — what the event feed shows. */
  wireLines: string[]
  /** Real per-probe events from the backend. Non-empty means the backend is
   *  emitting per-probe SSE — the chamber renders THESE instead of the
   *  timeline fixtures and the DEMO PACING disclosure disappears. */
  probes: LiveProbe[]
  cluster: LiveCluster | null
  recipe: LiveRecipe | null
  report: LiveReport | null
  /** Final tally from the complete frame, when provided — the backend's
   *  authoritative counts, preferred over frontend-derived tallies. */
  summary: { passed: number; failed: number; errored: number } | null
  error: string | null
}

const VALID_VERDICTS: ReadonlySet<string> = new Set(['pass', 'fail', 'error'])

const VALID_PHASES: ReadonlySet<string> = new Set<Phase>([
  'queued',
  'injector',
  'judge',
  'patcher',
  'succeeded',
  'failed',
])

// Bound the wire-line buffer so a long-lived or misbehaving stream can't
// grow memory without limit.
const MAX_WIRE_LINES = 500

function ceilingForPhase(phase: Phase): number {
  // Each phase's ceiling is the START of the NEXT phase, so the chamber's
  // per-probe ticker fills the current phase's window completely before
  // the next real event arrives.
  switch (phase) {
    case 'queued':
      return 0
    case 'injector':
      return TIMELINE.phases.find((p) => p.phase === 'judge')?.at ?? TIMELINE.duration
    case 'judge':
      return TIMELINE.phases.find((p) => p.phase === 'patcher')?.at ?? TIMELINE.duration
    case 'patcher':
      return TIMELINE.phases.find((p) => p.phase === 'succeeded')?.at ?? TIMELINE.duration
    case 'succeeded':
    case 'failed':
      return TIMELINE.duration
  }
}

function getAgentUrl(): string {
  // Default: the same-origin proxy (works locally AND against the IAM-gated
  // deployed agent — EventSource cannot attach Authorization headers itself).
  // NEXT_PUBLIC_AGENT_URL overrides for direct-to-agent local debugging.
  const fromEnv = process.env.NEXT_PUBLIC_AGENT_URL
  if (fromEnv && fromEnv.length > 0) return fromEnv
  return '/api/agent'
}

interface PhaseChangeData {
  phase?: string
}

function parseJson<T>(raw: string): T | null {
  try {
    return JSON.parse(raw) as T
  } catch {
    return null
  }
}

/** Insert-or-update a probe by `n`, keeping the list sorted by `n`. */
function upsertProbe(probes: LiveProbe[], next: Partial<LiveProbe> & { n: number }): LiveProbe[] {
  const existing = probes.find((p) => p.n === next.n)
  const merged: LiveProbe = {
    faultClass: 'unknown',
    state: 'running',
    ...existing,
    ...next,
  }
  return [...probes.filter((p) => p.n !== next.n), merged].sort((a, b) => a.n - b.n)
}

export function useAuditStream(runId: string): AuditStreamState {
  const [state, setState] = useState<AuditStreamState>({
    connected: false,
    phase: 'queued',
    clockCeiling: 0,
    wireLines: [],
    probes: [],
    cluster: null,
    recipe: null,
    report: null,
    summary: null,
    error: null,
  })
  const startedAtRef = useRef<number>(0)

  useEffect(() => {
    if (!runId) return
    const base = getAgentUrl()
    const url = `${base.replace(/\/$/, '')}/stream?runId=${encodeURIComponent(runId)}`
    let source: EventSource | null = null
    try {
      source = new EventSource(url)
    } catch (err) {
      setState((s) => ({ ...s, error: err instanceof Error ? err.message : String(err) }))
      return
    }
    startedAtRef.current = performance.now()

    const stamp = () =>
      ((performance.now() - startedAtRef.current) / 1000).toFixed(1).padStart(5, '0') + 's'

    const append = (line: string) => {
      setState((s) => ({
        ...s,
        wireLines: [...s.wireLines, `${stamp()}  ${line}`].slice(-MAX_WIRE_LINES),
      }))
    }

    const data = (e: Event): string => (e as MessageEvent).data as string

    source.addEventListener('open', () => {
      setState((s) => ({ ...s, connected: true, error: null }))
    })

    source.addEventListener('hello', (e) => {
      append(`hello ${data(e)}`)
    })

    source.addEventListener('phase_change', (e) => {
      const raw = data(e)
      append(`phase_change ${raw}`)
      const parsed = parseJson<PhaseChangeData>(raw)
      const phase = parsed?.phase
      // Validate against the Phase union — an unknown wire value must NOT
      // silently become an unbounded clock ceiling (review finding #4).
      if (!phase || !VALID_PHASES.has(phase)) {
        append(`error {"detail":"unrecognized phase value: ${String(phase)}"}`)
        return
      }
      const valid = phase as Phase
      setState((s) => ({ ...s, phase: valid, clockCeiling: ceilingForPhase(valid) }))
    })

    source.addEventListener('test_started', (e) => {
      const raw = data(e)
      append(`test_started ${raw}`)
      const p = parseJson<{ n?: number; fault_class?: string }>(raw)
      if (typeof p?.n !== 'number') return
      const n = p.n
      const faultClass = p.fault_class ?? 'unknown'
      setState((s) => ({
        ...s,
        probes: upsertProbe(s.probes, { n, faultClass, state: 'running' }),
      }))
    })

    source.addEventListener('test_completed', (e) => {
      const raw = data(e)
      append(`test_completed ${raw}`)
      const p = parseJson<{
        n?: number
        fault_class?: string
        status?: string
        span_id?: string
      }>(raw)
      if (typeof p?.n !== 'number') return
      const n = p.n
      setState((s) => ({
        ...s,
        probes: upsertProbe(s.probes, {
          n,
          ...(p.fault_class ? { faultClass: p.fault_class } : {}),
          state: 'done',
          ...(p.status ? { status: p.status } : {}),
          ...(p.span_id ? { spanId: p.span_id } : {}),
        }),
      }))
    })

    source.addEventListener('test_verdict', (e) => {
      const raw = data(e)
      append(`test_verdict ${raw}`)
      const p = parseJson<{
        n?: number
        verdict?: string
        fault_class?: string
        span_id?: string
        score?: number
        transport_error?: boolean
        rubric_error?: boolean
      }>(raw)
      if (typeof p?.n !== 'number') return
      // Validate the verdict against the union — a malformed wire value must
      // NOT be coerced into a displayed FAIL (that would be invented
      // compliance data). Unknown verdicts are logged and dropped.
      if (!p.verdict || !VALID_VERDICTS.has(p.verdict)) {
        append(`error {"detail":"unrecognized verdict value: ${String(p.verdict)}"}`)
        return
      }
      const n = p.n
      const verdict = p.verdict as 'pass' | 'fail' | 'error'
      setState((s) => ({
        ...s,
        probes: upsertProbe(s.probes, {
          n,
          // test_verdict frames are self-contained (carry fault_class) so a
          // late-joining client never renders an 'unknown' chip.
          ...(p.fault_class ? { faultClass: p.fault_class } : {}),
          state: 'done',
          verdict,
          transportError: p.transport_error === true,
          rubricError: p.rubric_error === true,
          ...(typeof p.score === 'number' ? { score: p.score } : {}),
          ...(p.span_id ? { spanId: p.span_id } : {}),
        }),
      }))
    })

    source.addEventListener('cluster_set', (e) => {
      const raw = data(e)
      append(`cluster_set ${raw}`)
      const p = parseJson<{
        clusters?: number
        total_failures?: number
        cluster_ids?: string[]
        root_causes?: string[]
        excluded_transport_failures?: number
        rubric_errors?: number
        annotation_writeback_failed?: boolean
        skipped?: string
      }>(raw)
      if (!p) return
      setState((s) => ({
        ...s,
        cluster: {
          clusters: p.clusters ?? 0,
          totalFailures: p.total_failures ?? 0,
          clusterIds: p.cluster_ids ?? [],
          rootCauses: p.root_causes ?? [],
          excludedTransportFailures: p.excluded_transport_failures ?? 0,
          rubricErrors: p.rubric_errors ?? 0,
          annotationWritebackFailed: p.annotation_writeback_failed === true,
          ...(p.skipped ? { skipped: p.skipped } : {}),
        },
      }))
    })

    source.addEventListener('recipe', (e) => {
      const raw = data(e)
      append(`recipe ${raw}`)
      const p = parseJson<{ recipe_id?: string; markdown_url?: string }>(raw)
      if (!p?.recipe_id) return
      setState((s) => ({
        ...s,
        recipe: { recipeId: p.recipe_id ?? '', markdownUrl: p.markdown_url ?? null },
      }))
    })

    source.addEventListener('report', (e) => {
      const raw = data(e)
      append(`report ${raw}`)
      const p = parseJson<{
        pdf_url?: string
        json_url?: string
        signature_url?: string
      }>(raw)
      if (!p) return
      setState((s) => ({
        ...s,
        report: {
          pdfUrl: p.pdf_url ?? null,
          jsonUrl: p.json_url ?? null,
          signatureUrl: p.signature_url ?? null,
          skippedReason: null,
        },
      }))
    })

    source.addEventListener('report_skipped', (e) => {
      const raw = data(e)
      append(`report_skipped ${raw}`)
      const p = parseJson<{ reason?: string }>(raw)
      setState((s) => ({
        ...s,
        report: {
          pdfUrl: null,
          jsonUrl: null,
          signatureUrl: null,
          skippedReason: p?.reason ?? 'unknown',
        },
      }))
    })

    source.addEventListener('complete', (e) => {
      const raw = data(e)
      append(`complete ${raw}`)
      const p = parseJson<{ passed?: number; failed?: number; errored?: number }>(raw)
      setState((s) => ({
        ...s,
        phase: 'succeeded',
        clockCeiling: ceilingForPhase('succeeded'),
        summary:
          typeof p?.passed === 'number' && typeof p?.failed === 'number'
            ? { passed: p.passed, failed: p.failed, errored: p.errored ?? 0 }
            : s.summary,
      }))
      source?.close()
    })

    source.addEventListener('cancelled', (e) => {
      append(`cancelled ${data(e)}`)
      source?.close()
    })

    // This handler receives BOTH the backend's custom terminal `error` event
    // (a MessageEvent carrying JSON data) and the browser's connection-level
    // error (no data). The backend error is terminal per the /stream contract
    // (it pushes the sentinel and ends), so we close. A connection-level
    // error with readyState CLOSED is also permanent. Either way the chamber
    // surfaces it — the ticker must never freeze silently (review finding #3).
    source.addEventListener('error', (e) => {
      const raw = (e as MessageEvent).data as string | undefined
      if (typeof raw === 'string' && raw.length > 0) {
        append(`error ${raw}`)
        const parsed = parseJson<{ detail?: string }>(raw)
        setState((s) => ({
          ...s,
          connected: false,
          phase: 'failed',
          error: parsed?.detail ?? 'audit run failed',
        }))
        source?.close()
        return
      }
      if (source?.readyState === EventSource.CLOSED) {
        append('error {"detail":"connection lost"}')
        setState((s) => ({ ...s, connected: false, error: 'connection lost' }))
        return
      }
      // CONNECTING — browser is auto-retrying; reflect the drop without
      // declaring the run dead.
      setState((s) => ({ ...s, connected: false }))
    })

    return () => {
      source?.close()
    }
  }, [runId])

  return state
}
