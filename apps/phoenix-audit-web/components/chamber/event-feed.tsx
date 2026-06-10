'use client'

import { useEffect, useMemo, useRef } from 'react'
import { EVENT_LOG } from '@/lib/timeline'

interface EventFeedProps {
  t: number
  /** Live mode override — pre-formatted "TIMESTAMP  event payload" lines
   *  arriving over the real SSE wire. When present, replaces the synthesized
   *  EVENT_LOG slice. */
  liveLines?: string[]
}

export function EventFeed({ t, liveLines }: EventFeedProps) {
  const ref = useRef<HTMLDivElement | null>(null)
  const visible = useMemo(() => {
    if (liveLines) {
      return liveLines.map((line) => ({ at: 0, line, prefix: '' }))
    }
    return EVENT_LOG.filter((e) => e.at <= t).map((e) => ({
      at: e.at,
      line: e.line,
      prefix: e.at.toFixed(1).padStart(5, '0') + 's',
    }))
  }, [t, liveLines])
  useEffect(() => {
    if (ref.current) ref.current.scrollTop = ref.current.scrollHeight
  }, [visible.length])
  return (
    <div>
      <div
        className="mono"
        style={{
          fontSize: 10,
          letterSpacing: '0.2em',
          color: 'var(--chamber-ink-3)',
          marginBottom: 10,
        }}
      >
        SERVER-SENT EVENTS — /stream
      </div>
      <div
        ref={ref}
        style={{
          height: 132,
          overflowY: 'auto',
          border: '1px solid var(--chamber-line-soft)',
          borderRadius: 4,
          padding: '8px 12px',
          background: 'rgba(0,0,0,0.25)',
        }}
      >
        {visible.length === 0 ? (
          <div
            className="mono"
            style={{
              fontSize: 10.5,
              color: 'var(--chamber-ink-3)',
              opacity: 0.5,
            }}
          >
            waiting for connection…
          </div>
        ) : null}
        {visible.map((e, i) => (
          <div
            key={i}
            className="mono"
            style={{
              fontSize: 10.5,
              lineHeight: 1.9,
              color: i === visible.length - 1 ? 'var(--ember-glow)' : 'var(--chamber-ink-3)',
              whiteSpace: 'nowrap',
            }}
          >
            {e.prefix ? <span style={{ opacity: 0.5 }}>{e.prefix}</span> : null}
            {e.prefix ? '  ' : ''}
            {e.line}
          </div>
        ))}
      </div>
    </div>
  )
}
