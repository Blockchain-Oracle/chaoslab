'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { clamp } from '@/lib/replay-clock'

interface AuditClock {
  t: number
  playing: boolean
  setPlaying: (next: boolean) => void
  seek: (next: number) => void
  restart: () => void
}

/** Playback clock for replaying a recorded run. `duration` comes from the
 *  run's persisted timeline. Persists t per run so a refresh resumes. */
export function useAuditClock(duration: number, runId: string): AuditClock {
  const storageKey = 'pa_audit_t_' + runId
  const [t, setT] = useState<number>(0)
  const [playing, setPlaying] = useState(true)
  const lastWriteRef = useRef(0)

  useEffect(() => {
    if (typeof window === 'undefined') return
    const raw = window.localStorage.getItem(storageKey)
    const v = raw ? parseFloat(raw) : NaN
    const start = Number.isFinite(v) ? clamp(v, 0, duration) : 0
    setT(start)
    setPlaying(start < duration)
  }, [storageKey, duration])

  useEffect(() => {
    if (!playing) return
    let last = performance.now()
    const id = setInterval(() => {
      const now = performance.now()
      const dt = (now - last) / 1000
      last = now
      setT((prev) => {
        const next = Math.min(prev + dt, duration)
        if (next >= duration) setPlaying(false)
        return next
      })
    }, 50)
    return () => clearInterval(id)
  }, [playing, duration])

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
