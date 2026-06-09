import type { ReactNode } from 'react'

interface LockedParagraphProps {
  title: string
  children: ReactNode
}

// Legally locked paragraph — renders verbatim on the signed PDF cover.
// Used for the data-residency block and the header-convention warning.
export function LockedParagraph({ title, children }: LockedParagraphProps) {
  return (
    <div
      style={{
        border: '1px dashed var(--hairline)',
        borderRadius: 3,
        padding: '12px 16px',
        margin: '14px 0',
        background: 'var(--paper-2)',
      }}
    >
      <div
        className="mono"
        style={{
          fontSize: 9.5,
          letterSpacing: '0.14em',
          color: 'var(--ink-3)',
          marginBottom: 7,
          display: 'flex',
          gap: 8,
          alignItems: 'center',
        }}
      >
        <span style={{ color: 'var(--ember-deep)' }}>▣</span>
        {title} — LEGALLY LOCKED · RENDERS VERBATIM
      </div>
      <p
        style={{
          fontSize: 11.5,
          lineHeight: 1.65,
          color: 'var(--ink-2)',
          fontStyle: 'italic',
        }}
      >
        {children}
      </p>
    </div>
  )
}
