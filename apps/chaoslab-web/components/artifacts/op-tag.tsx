import type { ReactNode } from 'react'

interface OpTagProps {
  children: ReactNode
}

// Inline mono pill used as the section/operation marker in the recipe view.
export function OpTag({ children }: OpTagProps) {
  return (
    <span
      className="mono"
      style={{
        fontSize: 10,
        letterSpacing: '0.1em',
        textTransform: 'uppercase',
        color: 'var(--ember-deep)',
        border: '1px solid var(--ember-soft)',
        background: 'var(--ember-faint)',
        padding: '2px 8px',
        borderRadius: 2,
      }}
    >
      {children}
    </span>
  )
}
