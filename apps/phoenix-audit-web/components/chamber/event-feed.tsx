'use client'

import { useEffect, useRef } from 'react'

interface EventFeedProps {
  /** Pre-formatted "TIMESTAMP  event payload" wire lines — live SSE or the
   *  replayed recorded timeline. There is no synthesized fallback. */
  lines: string[]
}

export function EventFeed({ lines }: EventFeedProps) {
  const ref = useRef<HTMLDivElement | null>(null)
  useEffect(() => {
    if (ref.current) ref.current.scrollTop = ref.current.scrollHeight
  }, [lines.length])
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
        {lines.length === 0 ? (
          <div
            className="mono"
            style={{
              fontSize: 10.5,
              color: 'var(--chamber-ink-3)',
              opacity: 0.5,
            }}
          >
            waiting for events…
          </div>
        ) : null}
        {lines.map((line, i) => (
          <div
            key={i}
            className="mono"
            style={{
              fontSize: 10.5,
              lineHeight: 1.9,
              color: i === lines.length - 1 ? 'var(--ember-glow)' : 'var(--chamber-ink-3)',
              whiteSpace: 'nowrap',
            }}
          >
            {line}
          </div>
        ))}
      </div>
    </div>
  )
}
