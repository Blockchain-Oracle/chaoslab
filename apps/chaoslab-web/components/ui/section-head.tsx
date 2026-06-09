import type { ReactNode } from 'react'

interface SectionHeadProps {
  no?: string
  title: string
  right?: ReactNode
}

export function SectionHead({ no, title, right }: SectionHeadProps) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'baseline',
        gap: 14,
        borderBottom: '1px solid var(--ink)',
        paddingBottom: 10,
        marginBottom: 18,
      }}
    >
      {no ? <span className="doc-section-no">{no}</span> : null}
      <h2 className="serif" style={{ fontSize: 21, fontWeight: 500, flex: 1 }}>
        {title}
      </h2>
      {right}
    </div>
  )
}
