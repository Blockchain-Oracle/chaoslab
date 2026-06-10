'use client'

import { useEffect, useRef, useState } from 'react'
import { initialStreamState, reduceWireEvent, type AuditStreamState } from './sse-reducer'

// Hybrid SSE bridge — real /stream events drive the chamber. Phases gate the
// local clock so the timeline ticker can't run past the real backend phase;
// when the backend emits per-probe events (test_started / test_completed /
// test_verdict / cluster_set / recipe) the chamber renders THOSE and the
// DEMO PACING disclosure disappears. All wire-protocol interpretation lives
// in the pure reducer (sse-reducer.ts); this hook owns ONLY the EventSource
// lifecycle. See SPEC.md for the contract.

export type {
  AuditStreamState,
  LiveCluster,
  LiveProbe,
  LiveRecipe,
  LiveReport,
} from './sse-reducer'

function getAgentUrl(): string {
  // Default: the same-origin proxy (works locally AND against the IAM-gated
  // deployed agent — EventSource cannot attach Authorization headers itself).
  // NEXT_PUBLIC_AGENT_URL overrides for direct-to-agent local debugging.
  const fromEnv = process.env.NEXT_PUBLIC_AGENT_URL
  if (fromEnv && fromEnv.length > 0) return fromEnv
  return '/api/agent'
}

// Every named event the backend emits on /stream. Each is routed through the
// reducer; `error` is special-cased below because it doubles as the browser's
// connection-level error event.
const WIRE_EVENTS = [
  'hello',
  'phase_change',
  'test_started',
  'test_completed',
  'test_verdict',
  'cluster_set',
  'recipe',
  'report',
  'report_skipped',
  'complete',
  'cancelled',
] as const

export function useAuditStream(runId: string): AuditStreamState {
  const [state, setState] = useState<AuditStreamState>(initialStreamState)
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

    const apply = (event: string, raw: string) => {
      const stamped = stamp()
      setState((s) => {
        const { state: next, terminal } = reduceWireEvent(s, event, raw, stamped)
        // close() is idempotent — safe even if React re-invokes the updater.
        if (terminal) source?.close()
        return next
      })
    }

    source.addEventListener('open', () => {
      setState((s) => ({ ...s, connected: true, error: null }))
    })

    for (const event of WIRE_EVENTS) {
      source.addEventListener(event, (e) => {
        apply(event, (e as MessageEvent).data as string)
      })
    }

    // This handler receives BOTH the backend's custom terminal `error` event
    // (a MessageEvent carrying JSON data — routed to the reducer) and the
    // browser's connection-level error (no data). A connection-level error
    // with readyState CLOSED is permanent. Either way the chamber surfaces
    // it — the ticker must never freeze silently.
    source.addEventListener('error', (e) => {
      const raw = (e as MessageEvent).data as string | undefined
      if (typeof raw === 'string' && raw.length > 0) {
        apply('error', raw)
        return
      }
      if (source?.readyState === EventSource.CLOSED) {
        setState((s) => {
          const { state: next } = reduceWireEvent(
            s,
            'error',
            '{"detail":"connection lost"}',
            stamp(),
          )
          // Connection loss is NOT the backend declaring the run failed —
          // keep the last known phase, surface the disconnect.
          return { ...next, phase: s.phase }
        })
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
