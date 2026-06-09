export function BuiltOn() {
  return (
    <section style={{ borderTop: '1px solid var(--hairline)' }}>
      <div
        className="shell"
        style={{
          padding: '34px 40px',
          display: 'flex',
          alignItems: 'center',
          gap: 30,
          flexWrap: 'wrap',
        }}
      >
        <span className="mono muted" style={{ fontSize: 10.5, letterSpacing: '0.18em' }}>
          BUILT ON
        </span>
        <span className="tag" style={{ fontSize: 12, padding: '7px 14px' }}>
          ◳&nbsp; Arize Phoenix
        </span>
        <span className="tag" style={{ fontSize: 12, padding: '7px 14px' }}>
          ▲&nbsp; Google Cloud Agent Builder
        </span>
        <span style={{ flex: 1 }}></span>
        <span className="mono muted" style={{ fontSize: 10.5, letterSpacing: '0.1em' }}>
          SIGNING VIA CLOUD KMS · GDPR ART. 28 DATA PROCESSOR
        </span>
      </div>
    </section>
  )
}
