// Story-9.14 redesign — FrameworkRows (O-4). The default-framework
// picker rendered as named rows with a sub-description and a
// "cited on your covers" indicator that surfaces only on the selected
// row (so the operator sees the consequence of her choice in the
// affordance itself, not just in the rail's CoverPreview).

interface Props {
  value: string
  onChange: (value: string) => void
}

const FRAMEWORKS: { name: string; sub: string }[] = [
  { name: 'EU AI Act', sub: 'Articles 9, 11–15, 72 · Annex IV documentation' },
  { name: 'NIST AI RMF', sub: 'GOVERN / MAP / MEASURE / MANAGE functions' },
  { name: 'HIPAA', sub: '§164.312 technical safeguards' },
  { name: 'SOC 2 + AI', sub: 'Trust services criteria, AI addendum' },
  { name: 'Custom', sub: 'Bring your own control mapping — we cite your control IDs' },
]

export function FrameworkRows({ value, onChange }: Props) {
  return (
    <div className="fw-group" role="radiogroup" aria-label="Default regulatory framework">
      {FRAMEWORKS.map(({ name, sub }) => {
        const sel = value === name
        const custom = name === 'Custom'
        const cls = ['fw-row', sel ? 'selected' : '', custom ? 'custom' : '']
          .filter(Boolean)
          .join(' ')
        return (
          <button
            type="button"
            key={name}
            role="radio"
            aria-checked={sel}
            className={cls}
            onClick={() => onChange(name)}
          >
            <span className="fw-ring" aria-hidden="true" />
            <span className="fw-name">
              {name}
              {name === 'EU AI Act' ? (
                <span
                  className="mono"
                  style={{
                    fontSize: 8.5,
                    letterSpacing: '0.12em',
                    color: 'var(--ink-3)',
                    marginLeft: 8,
                  }}
                >
                  DEFAULT
                </span>
              ) : null}
            </span>
            <span className="fw-sub">{sub}</span>
            <span className="fw-cited">◆ cited on your covers</span>
          </button>
        )
      })}
    </div>
  )
}
