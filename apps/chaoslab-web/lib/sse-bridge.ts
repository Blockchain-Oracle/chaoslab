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
  phase?: Phase
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
      setState((s) => ({ ...s, wireLines: [...s.wireLines, `${stamp()}  ${line}`] }))
    }

    source.addEventListener('open', () => {
      setState((s) => ({ ...s, connected: true }))
    })

    source.addEventListener('hello', (e) => {
      append(`hello ${(e as MessageEvent).data}`)
    })

    source.addEventListener('phase_change', (e) => {
      const data = (e as MessageEvent).data as string
      append(`phase_change ${data}`)
      const parsed = parseJson<PhaseChangeData>(data)
      if (parsed?.phase) {
        setState((s) => ({
          ...s,
          phase: parsed.phase!,
          clockCeiling: ceilingForPhase(parsed.phase!),
        }))
      }
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

    source.addEventListener('error', (e) => {
      const data = (e as MessageEvent).data
      if (typeof data === 'string' && data.length > 0) {
        append(`error ${data}`)
      } else {
        append('error {"detail":"connection lost"}')
      }
      setState((s) => ({ ...s, connected: false, error: 'stream error' }))
    })

    return () => {
      source?.close()
    }
  }, [runId])

  return state
}
