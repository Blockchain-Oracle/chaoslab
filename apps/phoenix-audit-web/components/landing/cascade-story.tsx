// The killer story — three failures converge into one.
const FAILURES: ReadonlyArray<[string, string]> = [
  ['MITRE ATLAS AML.T0051', 'Indirect injection via tool output'],
  ['OWASP LLM01', 'Poisoned patient-record context'],
  ['HarmBench A-031', 'Malformed eligibility tool response'],
]

function CascadeArrows({ single }: { single?: boolean }) {
  return (
    <svg
      width="74"
      height="160"
      viewBox="0 0 74 160"
      fill="none"
      style={{ margin: '0 6px' }}
      aria-hidden="true"
    >
      {single ? (
        <path d="M4 80 H66" stroke="var(--ember-glow)" strokeWidth="1.2" strokeDasharray="3 4" />
      ) : (
        <g>
          <path
            d="M4 26 C 40 26, 40 80, 68 80"
            stroke="var(--ember-glow)"
            strokeWidth="1.2"
            strokeDasharray="3 4"
            fill="none"
          />
          <path d="M4 80 H68" stroke="var(--ember-glow)" strokeWidth="1.2" strokeDasharray="3 4" />
          <path
            d="M4 134 C 40 134, 40 80, 68 80"
            stroke="var(--ember-glow)"
            strokeWidth="1.2"
            strokeDasharray="3 4"
            fill="none"
          />
        </g>
      )}
      <path d="M62 75 L70 80 L62 85" stroke="var(--ember-glow)" strokeWidth="1.2" fill="none" />
    </svg>
  )
}

export function CascadeStory() {
  return (
    <section
      id="how"
      style={{
        borderTop: '1px solid var(--hairline)',
        background: 'var(--chamber)',
        color: 'var(--chamber-ink)',
      }}
      className="chamber-scope"
    >
      <div className="shell" style={{ padding: '90px 40px 96px' }}>
        <div className="kicker bare" style={{ color: 'var(--chamber-ink-3)', marginBottom: 18 }}>
          <span
            style={{
              width: 22,
              height: 1,
              background: 'var(--ember-glow)',
              display: 'inline-block',
            }}
          ></span>
          The cascade-flip
        </div>
        <h2
          className="display"
          style={{ fontSize: 'clamp(34px, 4vw, 52px)', maxWidth: 760, marginBottom: 64 }}
        >
          Three failures. <em style={{ color: 'var(--ember-glow)' }}>One root cause.</em>
          <br />
          Patch in four seconds.
        </h2>

        <div
          className="cascade-grid"
          style={{
            display: 'grid',
            gridTemplateColumns: '1fr auto 1fr auto 1fr',
            gap: 0,
            alignItems: 'center',
          }}
        >
          <div style={{ display: 'grid', gap: 12 }}>
            {FAILURES.map(([cit, name]) => (
              <div
                key={cit}
                style={{
                  border: '1px solid var(--chamber-line)',
                  borderRadius: 4,
                  padding: '13px 16px',
                  background: 'rgba(220,90,60,0.06)',
                }}
              >
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    gap: 10,
                    marginBottom: 5,
                  }}
                >
                  <span className="citation">{cit}</span>
                  <span className="stamp fail">Fail</span>
                </div>
                <div style={{ fontSize: 13, color: 'var(--chamber-ink-2)' }}>{name}</div>
              </div>
            ))}
          </div>
          <CascadeArrows />
          <div
            style={{
              border: '1px solid var(--ember-glow)',
              borderRadius: 4,
              padding: '18px 19px',
              background: 'rgba(228,150,70,0.07)',
              boxShadow: '0 0 44px rgba(228,150,70,0.12)',
            }}
          >
            <div
              className="mono"
              style={{
                fontSize: 10,
                letterSpacing: '0.16em',
                color: 'var(--ember-glow)',
                marginBottom: 9,
              }}
            >
              ROOT CAUSE CLUSTER · cluster_a3f81c2e
            </div>
            <div className="serif" style={{ fontSize: 16.5, lineHeight: 1.45 }}>
              submit_prior_auth is invoked on{' '}
              <em style={{ color: 'var(--ember-glow)' }}>unvalidated input</em> — validate_request
              is never called first.
            </div>
            <div
              className="mono"
              style={{ fontSize: 10.5, color: 'var(--chamber-ink-3)', marginTop: 10 }}
            >
              explains 3 of 3 failures
            </div>
          </div>
          <CascadeArrows single />
          <div
            style={{
              border: '1px solid var(--chamber-line)',
              borderRadius: 4,
              overflow: 'hidden',
            }}
          >
            <div
              className="mono"
              style={{
                fontSize: 10,
                letterSpacing: '0.16em',
                color: 'var(--chamber-ink-3)',
                padding: '10px 14px',
                borderBottom: '1px solid var(--chamber-line-soft)',
                display: 'flex',
                justifyContent: 'space-between',
              }}
            >
              <span>HARDENING RECIPE</span>
              <span style={{ color: 'var(--pass-glow)' }}>4.1 s</span>
            </div>
            <div className="mono" style={{ fontSize: 11.5, lineHeight: 1.8, padding: '12px 14px' }}>
              <div className="dim" style={{ color: 'var(--chamber-ink-3)' }}>
                @@ system_prompt @@
              </div>
              <div style={{ color: 'var(--pass-glow)' }}>+ MUST call validate_request</div>
              <div style={{ color: 'var(--pass-glow)' }}>+ before any tool output acts</div>
              <div className="dim" style={{ color: 'var(--chamber-ink-3)' }}>
                @@ tools/submit_prior_auth @@
              </div>
              <div style={{ color: 'var(--pass-glow)' }}>+ add_input_validator</div>
            </div>
          </div>
        </div>

        <p
          style={{
            maxWidth: 660,
            marginTop: 56,
            fontSize: 15.5,
            lineHeight: 1.7,
            color: 'var(--chamber-ink-2)',
            textWrap: 'pretty',
          }}
        >
          Surface-level failures rarely have surface-level causes. Phoenix Audit watches your
          agent&apos;s internal execution while each adversarial test lands, then collapses
          independent failures into the single underlying defect — and ships the fix as a real merge
          request, regression tests included.
        </p>
      </div>
    </section>
  )
}
