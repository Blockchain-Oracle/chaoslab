// Pure wire-protocol reducer for the live audit chamber.
//
// (state, event, raw) → next state. The EventSource wiring lives in
// sse-bridge.ts; everything that interprets the /stream contract lives here
// so the regulator-demo rendering path is unit-testable without a browser.

import type { Phase } from './types'

/** One adversarial probe as reported by the REAL backend event stream. */
export interface LiveProbe {
  n: number
  faultClass: string
  state: 'running' | 'done'
  status?: string
  spanId?: string
  /** `error` = the judge rubric itself failed (rate limit / safety block) —
   *  a MARKED non-verdict, never coerced into pass or fail. */
  /** `skip` = audit deliberately did not score this probe (F1/F4 in
   *  black-box mode). Distinct from `error` ("could not score"); the
   *  cover sheet counts these separately. */
  verdict?: 'pass' | 'fail' | 'error' | 'skip'
  skipped?: boolean
  rubricReason?: string
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
  /** Raw wire lines (event + JSON payload) — what the event feed shows. */
  wireLines: string[]
  /** Real per-probe events from the wire (live SSE or replayed timeline). */
  probes: LiveProbe[]
  cluster: LiveCluster | null
  recipe: LiveRecipe | null
  report: LiveReport | null
  /** Final tally from the complete frame, when provided — the backend's
   *  authoritative counts, preferred over frontend-derived tallies. */
  summary: { passed: number; failed: number; errored: number } | null
  error: string | null
}

export function initialStreamState(): AuditStreamState {
  return {
    connected: false,
    phase: 'queued',
    wireLines: [],
    probes: [],
    cluster: null,
    recipe: null,
    report: null,
    summary: null,
    error: null,
  }
}

const VALID_VERDICTS: ReadonlySet<string> = new Set(['pass', 'fail', 'error', 'skip'])

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

function parseJson<T>(raw: string): T | null {
  try {
    return JSON.parse(raw) as T
  } catch {
    return null
  }
}

/** Insert-or-update a probe by `n`, keeping the list sorted by `n`. */
export function upsertProbe(
  probes: LiveProbe[],
  next: Partial<LiveProbe> & { n: number },
): LiveProbe[] {
  const existing = probes.find((p) => p.n === next.n)
  const merged: LiveProbe = {
    faultClass: 'unknown',
    state: 'running',
    ...existing,
    ...next,
  }
  return [...probes.filter((p) => p.n !== next.n), merged].sort((a, b) => a.n - b.n)
}

export interface ReduceResult {
  state: AuditStreamState
  /** True when the /stream contract says nothing more will arrive — the
   *  caller should close the EventSource. */
  terminal: boolean
}

function withLines(s: AuditStreamState, lines: string[]): AuditStreamState {
  return { ...s, wireLines: [...s.wireLines, ...lines].slice(-MAX_WIRE_LINES) }
}

/** Apply one wire event. `stamp` (e.g. "003.2s") prefixes the logged line. */
export function reduceWireEvent(
  s: AuditStreamState,
  event: string,
  raw: string,
  stamp = '',
): ReduceResult {
  const prefix = stamp ? `${stamp}  ` : ''
  const line = `${prefix}${event} ${raw}`
  const synth = (detail: string) => `${prefix}error {"detail":"${detail}"}`

  switch (event) {
    case 'phase_change': {
      const phase = parseJson<{ phase?: string }>(raw)?.phase
      // Validate against the Phase union — an unknown wire value must NOT
      // silently become an unbounded clock ceiling.
      if (!phase || !VALID_PHASES.has(phase)) {
        return {
          state: withLines(s, [line, synth(`unrecognized phase value: ${String(phase)}`)]),
          terminal: false,
        }
      }
      const valid = phase as Phase
      return {
        state: { ...withLines(s, [line]), phase: valid },
        terminal: false,
      }
    }

    case 'test_started': {
      const p = parseJson<{ n?: number; fault_class?: string }>(raw)
      if (typeof p?.n !== 'number') return { state: withLines(s, [line]), terminal: false }
      return {
        state: {
          ...withLines(s, [line]),
          probes: upsertProbe(s.probes, {
            n: p.n,
            faultClass: p.fault_class ?? 'unknown',
            state: 'running',
          }),
        },
        terminal: false,
      }
    }

    case 'test_completed': {
      const p = parseJson<{ n?: number; fault_class?: string; status?: string; span_id?: string }>(
        raw,
      )
      if (typeof p?.n !== 'number') return { state: withLines(s, [line]), terminal: false }
      return {
        state: {
          ...withLines(s, [line]),
          probes: upsertProbe(s.probes, {
            n: p.n,
            ...(p.fault_class ? { faultClass: p.fault_class } : {}),
            state: 'done',
            ...(p.status ? { status: p.status } : {}),
            ...(p.span_id ? { spanId: p.span_id } : {}),
          }),
        },
        terminal: false,
      }
    }

    case 'test_verdict': {
      const p = parseJson<{
        n?: number
        verdict?: string
        fault_class?: string
        span_id?: string
        score?: number | null
        transport_error?: boolean
        rubric_error?: boolean
        skipped?: boolean
        rubric_reason?: string
      }>(raw)
      if (typeof p?.n !== 'number') return { state: withLines(s, [line]), terminal: false }
      // Validate the verdict against the union — a malformed wire value must
      // NOT be coerced into a displayed FAIL (that would be invented
      // compliance data). Unknown verdicts are logged and dropped.
      if (!p.verdict || !VALID_VERDICTS.has(p.verdict)) {
        return {
          state: withLines(s, [line, synth(`unrecognized verdict value: ${String(p.verdict)}`)]),
          terminal: false,
        }
      }
      return {
        state: {
          ...withLines(s, [line]),
          probes: upsertProbe(s.probes, {
            n: p.n,
            // test_verdict frames are self-contained (carry fault_class) so a
            // late-joining client never renders an 'unknown' chip.
            ...(p.fault_class ? { faultClass: p.fault_class } : {}),
            state: 'done',
            verdict: p.verdict as 'pass' | 'fail' | 'error' | 'skip',
            transportError: p.transport_error === true,
            rubricError: p.rubric_error === true,
            // skipped: deliberately not scored (black-box mode F1/F4) —
            // distinct from rubric_error. The chamber + report counts these
            // separately so a regulator distinguishes "audit excluded this"
            // from "audit could not score this".
            skipped: p.skipped === true,
            ...(typeof p.score === 'number' ? { score: p.score } : {}),
            ...(p.rubric_reason ? { rubricReason: p.rubric_reason } : {}),
            ...(p.span_id ? { spanId: p.span_id } : {}),
          }),
        },
        terminal: false,
      }
    }

    case 'cluster_set': {
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
      if (!p) return { state: withLines(s, [line]), terminal: false }
      return {
        state: {
          ...withLines(s, [line]),
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
        },
        terminal: false,
      }
    }

    case 'recipe': {
      const p = parseJson<{ recipe_id?: string; markdown_url?: string }>(raw)
      if (!p?.recipe_id) return { state: withLines(s, [line]), terminal: false }
      return {
        state: {
          ...withLines(s, [line]),
          recipe: { recipeId: p.recipe_id, markdownUrl: p.markdown_url ?? null },
        },
        terminal: false,
      }
    }

    case 'report': {
      const p = parseJson<{ pdf_url?: string; json_url?: string; signature_url?: string }>(raw)
      if (!p) return { state: withLines(s, [line]), terminal: false }
      return {
        state: {
          ...withLines(s, [line]),
          report: {
            pdfUrl: p.pdf_url ?? null,
            jsonUrl: p.json_url ?? null,
            signatureUrl: p.signature_url ?? null,
            skippedReason: null,
          },
        },
        terminal: false,
      }
    }

    case 'report_skipped': {
      const p = parseJson<{ reason?: string }>(raw)
      return {
        state: {
          ...withLines(s, [line]),
          report: {
            pdfUrl: null,
            jsonUrl: null,
            signatureUrl: null,
            skippedReason: p?.reason ?? 'unknown',
          },
        },
        terminal: false,
      }
    }

    case 'complete': {
      const p = parseJson<{ passed?: number; failed?: number; errored?: number }>(raw)
      return {
        state: {
          ...withLines(s, [line]),
          phase: 'succeeded',
          summary:
            typeof p?.passed === 'number' && typeof p?.failed === 'number'
              ? { passed: p.passed, failed: p.failed, errored: p.errored ?? 0 }
              : s.summary,
        },
        terminal: true,
      }
    }

    case 'cancelled':
      return { state: withLines(s, [line]), terminal: true }

    case 'error': {
      // Backend's custom terminal `error` event — the /stream contract says
      // it pushes the sentinel and ends. Connection-level errors (no data)
      // are handled by the EventSource wiring, not here.
      const parsed = parseJson<{ detail?: string }>(raw)
      return {
        state: {
          ...withLines(s, [line]),
          connected: false,
          phase: 'failed',
          error: parsed?.detail ?? 'audit run failed',
        },
        terminal: true,
      }
    }

    default:
      // Unknown event types (future wire additions) only land in the log.
      return { state: withLines(s, [line]), terminal: false }
  }
}
