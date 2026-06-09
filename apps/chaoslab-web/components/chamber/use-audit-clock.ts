'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { TIMELINE } from '@/lib/fixtures'
import { clamp } from '@/lib/timeline'

interface AuditClock {
  t: number
  playing: boolean
  setPlaying: (next: boolean) => void
  seek: (next: number) => void
  restart: () => void
}

interface ClockOptions {
  /** Optional upper bound on `t`. In live mode this comes from the SSE bridge
   *  so the per-probe ticker can't drift ahead of the real backend phase. */
  ceiling?: number
}

/** Playback clock for the audit chamber. Persists t to localStorage per mode
 *  so a refresh resumes where the user left off. */
export function useAuditClock(mode: 'replay' | 'live', options: ClockOptions = {}): AuditClock {
  const storageKey = 'pa_audit_t_' + mode
  const [t, setT] = useState<number>(0)
  const [playing, setPlaying] = useState(true)
  const lastWriteRef = useRef(0)
  const ceiling = options.ceiling ?? TIMELINE.duration

  useEffect(() => {
    if (typeof window === 'undefined') return
    const raw = window.localStorage.getItem(storageKey)
    const v = raw ? parseFloat(raw) : NaN
    const start = Number.isFinite(v) ? clamp(v, 0, TIMELINE.duration) : 0
    setT(start)
    setPlaying(start < TIMELINE.duration)
  }, [storageKey])

  useEffect(() => {
    if (!playing) return
    let last = performance.now()
    const id = setInterval(() => {
      const now = performance.now()
      const dt = (now - last) / 1000
      last = now
      setT((prev) => {
        const next = Math.min(prev + dt, ceiling, TIMELINE.duration)
        if (next >= TIMELINE.duration) setPlaying(false)
        return next
      })
    }, 50)
    return () => clearInterval(id)
  }, [playing, ceiling])

  useEffect(() => {
    if (typeof window === 'undefined') return
    const quarterSec = Math.round(t * 4)
    if (quarterSec === lastWriteRef.current) return
    lastWriteRef.current = quarterSec
    window.localStorage.setItem(storageKey, String(t))
  }, [t, storageKey])

  const seek = useCallback((next: number) => {
    setT(next)
  }, [])

  const restart = useCallback(() => {
    setT(0)
    setPlaying(true)
  }, [])

  return { t, playing, setPlaying, seek, restart }
}
