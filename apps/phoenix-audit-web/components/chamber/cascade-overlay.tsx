'use client'

import { useLayoutEffect, useReducer, type RefObject } from 'react'
import { easeIO } from '@/lib/timeline'
import type { DerivedAuditState } from '@/lib/types'

interface CascadeOverlayProps {
  s: DerivedAuditState
  arenaRef: RefObject<HTMLDivElement | null>
  failRefs: Array<RefObject<HTMLSpanElement | null>>
  clusterRef: RefObject<HTMLDivElement | null>
}

// The 3-dot converge animation. Pure t-driven: drops three glowing dots
// at each failure row's position and linearly interpolates them toward
// the cluster card center as flipProgress advances 0 → 1.
export function CascadeOverlay({ s, arenaRef, failRefs, clusterRef }: CascadeOverlayProps) {
  const [, force] = useReducer((x: number) => x + 1, 0)
  useLayoutEffect(() => {
    if (s.flipProgress > 0 && s.flipProgress < 1) force()
  }, [s.t, s.flipProgress])

  if (s.flipProgress <= 0 || s.flipProgress >= 1) return null
  const arena = arenaRef.current
  const cluster = clusterRef.current
  if (!arena || !cluster) return null

  const ar = arena.getBoundingClientRect()
  const cr = cluster.getBoundingClientRect()
  const ex = cr.left - ar.left + cr.width / 2
  const ey = cr.top - ar.top + 26
  const p = easeIO(s.flipProgress)

  return (
    <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none', zIndex: 5 }}>
      {[0, 1, 2].map((i) => {
        const el = failRefs[i]?.current
        if (!el) return null
        const r = el.getBoundingClientRect()
        const sx = r.left - ar.left + r.width / 2
        const sy = r.top - ar.top + r.height / 2
        const x = sx + (ex - sx) * p
        const y = sy + (ey - sy) * p
        return (
          <span
            key={i}
            style={{
              position: 'absolute',
              left: x - 5,
              top: y - 5,
              width: 10,
              height: 10,
              borderRadius: '50%',
              background: 'var(--fail-glow)',
              boxShadow: '0 0 14px rgba(228,120,80,0.8)',
              opacity: 1 - p * 0.25,
            }}
          ></span>
        )
      })}
    </div>
  )
}
