import type { ReactNode } from 'react'

interface SectionHeadProps {
  no?: string
  /** Plain string or an inline-formatted node (e.g. **bold** rendered via
   *  the markdown inline parser when SectionHead drives a markdown heading). */
  title: ReactNode
  right?: ReactNode
}

export function SectionHead({ no, title, right }: SectionHeadProps) {
  // The right-side note collides with the title at narrow widths — every
  // longer title (e.g. "Phoenix hosting mode", "Regulatory framework",
  // "Test cases") wraps to 2-3 lines while the note narrows. The
  // section-head class is targeted by globals.css at ≤768px to flow the
  // note onto its own row below the title. The kicker stays glued to
  // the title via the inner flex group so they never split.
  return (
    <div
      className="section-head"
      style={{
        display: 'flex',
        alignItems: 'baseline',
        flexWrap: 'wrap',
        rowGap: 6,
        columnGap: 14,
        borderBottom: '1px solid var(--ink)',
        paddingBottom: 10,
        marginBottom: 18,
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'baseline',
          gap: 14,
          flex: '1 1 auto',
          minWidth: 0,
        }}
      >
        {no ? <span className="doc-section-no">{no}</span> : null}
        <h2 className="serif" style={{ fontSize: 21, fontWeight: 500, margin: 0 }}>
          {title}
        </h2>
      </div>
      {right ? <div className="section-head-right">{right}</div> : null}
    </div>
  )
}
