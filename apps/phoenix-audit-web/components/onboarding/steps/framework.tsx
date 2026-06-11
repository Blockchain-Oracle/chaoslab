// Step 3 — Default regulatory framework. Same 5 options the /new page
// surfaces; the choice feeds `framework_default` on the profile, which
// preselects the framework on every subsequent /new visit. Visually
// matches the prototype's framework picker (stacked radio rows with the
// ember-deep selected inset).

const FRAMEWORKS: ReadonlyArray<[string, string]> = [
  ['EU AI Act', 'Articles 9, 11–15, 72 · Annex IV documentation'],
  ['NIST AI RMF', 'GOVERN / MAP / MEASURE / MANAGE functions'],
  ['HIPAA', '§164.312 technical safeguards'],
  ['SOC 2 + AI', 'Trust services criteria, AI addendum'],
  ['Custom', 'Bring your own control mapping'],
]

export function StepFramework({
  value,
  onChange,
}: {
  value: string
  onChange: (v: string) => void
}) {
  return (
    <div>
      <div className="kicker" style={{ marginBottom: 14 }}>
        Default framework
      </div>
      <h2 className="display" style={{ fontSize: 32, marginBottom: 14 }}>
        Which control set anchors your reports?
      </h2>
      <p style={{ fontSize: 13.5, color: 'var(--ink-2)', lineHeight: 1.7, marginBottom: 22 }}>
        Each audit cites articles from this framework on the cover and in the regulatory mapping
        appendix. You can override per-audit on the /new page.
      </p>
      <div
        style={{
          display: 'grid',
          gap: 0,
          border: '1px solid var(--hairline)',
          borderRadius: 'var(--r-lg)',
          overflow: 'hidden',
          marginBottom: 8,
        }}
        role="radiogroup"
      >
        {FRAMEWORKS.map(([f, sub], i) => {
          const selected = value === f
          return (
            <div
              key={f}
              onClick={() => onChange(f)}
              role="radio"
              aria-checked={selected}
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault()
                  onChange(f)
                }
              }}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 16,
                padding: '14px 18px',
                cursor: 'pointer',
                borderTop: i > 0 ? '1px solid var(--hairline-soft)' : 'none',
                background: selected ? '#fff' : 'transparent',
                boxShadow: selected ? 'inset 3px 0 0 var(--ember-deep)' : 'none',
                transition: 'background 0.15s ease',
              }}
            >
              <span
                style={{
                  width: 14,
                  height: 14,
                  borderRadius: '50%',
                  border: '1.5px solid ' + (selected ? 'var(--ember-deep)' : 'var(--hairline)'),
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0,
                }}
              >
                {selected ? (
                  <span
                    style={{
                      width: 6,
                      height: 6,
                      borderRadius: '50%',
                      background: 'var(--ember-deep)',
                    }}
                  ></span>
                ) : null}
              </span>
              <span className="serif" style={{ fontSize: 16, width: 150 }}>
                {f}
              </span>
              <span className="mono muted" style={{ fontSize: 11 }}>
                {sub}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
