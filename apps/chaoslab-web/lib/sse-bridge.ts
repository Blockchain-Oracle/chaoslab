'use client'

import { useEffect, useRef, useState } from 'react'
import { TIMELINE } from './fixtures'
import type { Phase } from './types'

// Hybrid SSE bridge — real /stream phase events drive `phase`, gate the
// chamber's local clock so the per-probe ticker can't run past the real
// backend phase. The backend currently emits hello, phase_change, complete,
// cancelled, error; the per-probe ticker fills in until those land too.
// See SPEC.md and the plan doc for the contract.

export interface AuditStreamState {
  connected: boolean
  phase: Phase
  /** Maximum t (seconds) the chamber's local clock may advance to. Keyed to
   *  real phase transitions so the visual stays honest about what the
   *  backend is actually doing. */
  clockCeiling: number
  /** Raw wire lines (event + JSON payload) — what the event feed shows. */
  wireLines: string[]
  error: string | null
}

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
  const fromEnv = process.env.NEXT_PUBLIC_AGENT_URL
  if (fromEnv && fromEnv.length > 0) return fromEnv
  return 'http://localhost:8001'
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

export function useAuditStream(runId: string): AuditStreamState {
  const [state, setState] = useState<AuditStreamState>({
    connected: false,
    phase: 'queued',
    clockCeiling: 0,
    wireLines: [],
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

    source.addEventListener('open', () => {
      setState((s) => ({ ...s, connected: true, error: null }))
    })

    source.addEventListener('hello', (e) => {
      append(`hello ${(e as MessageEvent).data}`)
    })

    source.addEventListener('phase_change', (e) => {
      const data = (e as MessageEvent).data as string
      append(`phase_change ${data}`)
      const parsed = parseJson<PhaseChangeData>(data)
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

    source.addEventListener('complete', (e) => {
      append(`complete ${(e as MessageEvent).data}`)
      setState((s) => ({
        ...s,
        phase: 'succeeded',
        clockCeiling: ceilingForPhase('succeeded'),
      }))
      source?.close()
    })

    source.addEventListener('cancelled', (e) => {
      append(`cancelled ${(e as MessageEvent).data}`)
      source?.close()
    })

    // This handler receives BOTH the backend's custom terminal `error` event
    // (a MessageEvent carrying JSON data) and the browser's connection-level
    // error (no data). The backend error is terminal per the /stream contract
    // (it pushes the sentinel and ends), so we close. A connection-level
    // error with readyState CLOSED is also permanent. Either way the chamber
    // surfaces it — the ticker must never freeze silently (review finding #3).
    source.addEventListener('error', (e) => {
      const data = (e as MessageEvent).data as string | undefined
      if (typeof data === 'string' && data.length > 0) {
        append(`error ${data}`)
        const parsed = parseJson<{ detail?: string }>(data)
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
