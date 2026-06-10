import type { ReactNode } from 'react'

interface SectionHeadProps {
  no?: string
  /** Plain string or an inline-formatted node (e.g. **bold** rendered via
   *  the markdown inline parser when SectionHead drives a markdown heading). */
  title: ReactNode
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
