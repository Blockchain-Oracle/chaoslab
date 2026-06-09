// The enforcement notice — numbers are CONTENT SLOTS, not design.
// EU AI Act enforcement countdown + penalty exposure.
export function EnforcementStrip() {
  return (
    <div
      style={{
        borderBottom: '1px solid var(--hairline)',
        background: 'var(--ink)',
        color: 'var(--paper)',
      }}
    >
      <div
        className="shell"
        style={{
          padding: '10px 40px',
          display: 'flex',
          gap: 14,
          alignItems: 'baseline',
          justifyContent: 'center',
          flexWrap: 'wrap',
        }}
      >
        <span
          className="mono"
          style={{ fontSize: 11, letterSpacing: '0.18em', color: 'var(--ember-glow)' }}
        >
          NOTICE
        </span>
        <span className="mono" style={{ fontSize: 12, letterSpacing: '0.04em' }}>
          The EU AI Act enforces in{' '}
          <strong data-slot="days-to-enforcement" style={{ color: 'var(--ember-glow)' }}>
            59 days
          </strong>
          &nbsp;·&nbsp; penalty exposure up to{' '}
          <strong data-slot="penalty-exposure" style={{ color: 'var(--ember-glow)' }}>
            €15M
          </strong>{' '}
          or 3% of global turnover
        </span>
      </div>
    </div>
  )
}
