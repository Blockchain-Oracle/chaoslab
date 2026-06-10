import { A } from '../ui/link'
import { Seal } from '../ui/seal'

export function ClosingCta() {
  return (
    <section style={{ borderTop: '1px solid var(--hairline)', background: 'var(--paper-2)' }}>
      <div
        className="shell"
        style={{
          padding: '84px 40px',
          display: 'grid',
          gridTemplateColumns: 'auto 1fr auto',
          gap: 44,
          alignItems: 'center',
        }}
      >
        <Seal size={120} />
        <div>
          <h2 className="display" style={{ fontSize: 34, marginBottom: 10 }}>
            File something a regulator will respect.
          </h2>
          <p className="muted" style={{ maxWidth: 520, textWrap: 'pretty' }}>
            Your first signed audit report is 90 seconds away. No payment during the judging window.
          </p>
        </div>
        <div style={{ display: 'grid', gap: 12 }}>
          <A to="new" className="btn ember">
            Run audit
          </A>
          <A to="replay" className="btn ghost">
            Watch a sample audit
          </A>
        </div>
      </div>
    </section>
  )
}
