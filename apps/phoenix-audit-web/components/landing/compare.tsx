// Versus the Big 4.
const BIG4: ReadonlyArray<[string, string]> = [
  ['Cost per audit pack', '€80K – €250K'],
  ['Turnaround', '12–18 months'],
  ['Evidence', 'Interviews & screenshots'],
  ['Freshness', 'Stale on delivery'],
  ['Fix', 'A recommendations deck'],
]
const PHOENIX: ReadonlyArray<[string, string]> = [
  ['Cost per audit run', 'pennies of LLM cost'],
  ['Turnaround', '~90 seconds, signed'],
  ['Evidence', 'Phoenix trace spans, per finding'],
  ['Freshness', 'Continuously updatable'],
  ['Fix', 'A merge request with regression tests'],
]

export function Compare() {
  return (
    <section id="compare" className="shell" style={{ padding: '88px 40px' }}>
      <div className="kicker" style={{ marginBottom: 14 }}>
        The alternative
      </div>
      <h2 className="display" style={{ fontSize: 36, marginBottom: 46, maxWidth: 700 }}>
        The Big-4 audit pack costs <em>€80K–€250K</em> and takes 12–18 months. It is stale on
        arrival.
      </h2>
      <div
        className="compare-grid"
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: 0,
          borderTop: '1px solid var(--ink)',
        }}
      >
        <div style={{ padding: '26px 36px 26px 0', borderRight: '1px solid var(--hairline)' }}>
          <div
            className="mono muted"
            style={{ fontSize: 11, letterSpacing: '0.16em', marginBottom: 18 }}
          >
            CONSULTING ENGAGEMENT
          </div>
          {BIG4.map(([k, v]) => (
            <div key={k} className="leader-row" style={{ padding: '7px 0' }}>
              <span style={{ fontSize: 13.5, color: 'var(--ink-2)' }}>{k}</span>
              <span className="leader-fill"></span>
              <span className="mono" style={{ fontSize: 12.5, color: 'var(--ink-3)' }}>
                {v}
              </span>
            </div>
          ))}
        </div>
        <div style={{ padding: '26px 0 26px 36px' }}>
          <div
            className="mono"
            style={{
              fontSize: 11,
              letterSpacing: '0.16em',
              marginBottom: 18,
              color: 'var(--ember-deep)',
            }}
          >
            PHOENIX AUDIT
          </div>
          {PHOENIX.map(([k, v]) => (
            <div key={k} className="leader-row" style={{ padding: '7px 0' }}>
              <span style={{ fontSize: 13.5 }}>{k}</span>
              <span className="leader-fill"></span>
              <span className="mono" style={{ fontSize: 12.5, color: 'var(--ember-deep)' }}>
                {v}
              </span>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
