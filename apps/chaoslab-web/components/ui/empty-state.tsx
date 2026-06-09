import type { ReactNode } from 'react'
import { Glyph } from './glyph'

interface EmptyStateProps {
  kicker?: string
  title: string
  body?: string
  action?: ReactNode
  icon?: ReactNode
}

export function EmptyState({ kicker, title, body, action, icon }: EmptyStateProps) {
  return (
    <div
      style={{
        textAlign: 'center',
        padding: '72px 32px',
        border: '1px dashed var(--hairline)',
        borderRadius: 'var(--r-lg)',
      }}
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'center',
          marginBottom: 18,
          opacity: 0.5,
        }}
      >
        {icon ?? <Glyph size={28} color="var(--ink-3)" />}
      </div>
      {kicker ? (
        <div className="kicker bare" style={{ justifyContent: 'center', marginBottom: 10 }}>
          {kicker}
        </div>
      ) : null}
      <div className="serif" style={{ fontSize: 22, marginBottom: 8, lineHeight: 1.3 }}>
        {title}
      </div>
      {body ? (
        <p className="muted" style={{ maxWidth: 420, margin: '0 auto 22px', fontSize: 14 }}>
          {body}
        </p>
      ) : null}
      {action}
    </div>
  )
}
