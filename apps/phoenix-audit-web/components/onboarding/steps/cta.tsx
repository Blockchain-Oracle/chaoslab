// Step 5 — Final CTA. Two destinations: "Run your first audit" → /new (the
// real flow against a real target), or "Browse sample audits" → /audits
// (the seeded ownerless runs from story-9.11). Either click PATCHes the
// profile with `onboarded: true` first; the submit-error state surfaces here.

interface StepCtaProps {
  submitting: boolean
  submitError: string | null
  onFinish: (destination: '/new' | '/audits') => void
}

export function StepCta({ submitting, submitError, onFinish }: StepCtaProps) {
  return (
    <div>
      <div className="kicker" style={{ marginBottom: 14 }}>
        You&apos;re set
      </div>
      <h2 className="display" style={{ fontSize: 32, marginBottom: 14 }}>
        Where do you want to land?
      </h2>
      <p style={{ fontSize: 13.5, color: 'var(--ink-2)', lineHeight: 1.7, marginBottom: 26 }}>
        Run a real audit against your own agent, or open one of the seeded sample audits to see what
        a signed report looks like end-to-end.
      </p>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 24 }}>
        <button
          className="opt-card"
          onClick={() => onFinish('/new')}
          disabled={submitting}
          style={{ textAlign: 'left', cursor: submitting ? 'wait' : 'pointer' }}
          type="button"
        >
          <div
            className="mono"
            style={{
              fontSize: 10.5,
              letterSpacing: '0.14em',
              color: 'var(--ember-deep)',
              marginBottom: 8,
            }}
          >
            RUN YOUR FIRST AUDIT
          </div>
          <div className="serif" style={{ fontSize: 17.5, marginBottom: 7 }}>
            Point Phoenix Audit at your agent
          </div>
          <p
            style={{
              fontSize: 13,
              color: 'var(--ink-2)',
              lineHeight: 1.6,
              textWrap: 'pretty',
            }}
          >
            90 seconds against an HTTPS or A2A endpoint. Ends with a signed PDF and the four
            artifact viewers in this product.
          </p>
        </button>
        <button
          className="opt-card"
          onClick={() => onFinish('/audits')}
          disabled={submitting}
          style={{ textAlign: 'left', cursor: submitting ? 'wait' : 'pointer' }}
          type="button"
        >
          <div
            className="mono"
            style={{
              fontSize: 10.5,
              letterSpacing: '0.14em',
              color: 'var(--ember-deep)',
              marginBottom: 8,
            }}
          >
            BROWSE SAMPLE AUDITS
          </div>
          <div className="serif" style={{ fontSize: 17.5, marginBottom: 7 }}>
            See a finished signed report first
          </div>
          <p
            style={{
              fontSize: 13,
              color: 'var(--ink-2)',
              lineHeight: 1.6,
              textWrap: 'pretty',
            }}
          >
            Seeded sample runs against the demo target — full preview, replay, hardening recipe,
            verifiable signature.
          </p>
        </button>
      </div>
      {submitError ? (
        <div
          className="mono"
          style={{
            fontSize: 12,
            color: 'var(--fail)',
            border: '1px dashed currentColor',
            borderRadius: 4,
            padding: '10px 14px',
          }}
        >
          ✕ Could not finish onboarding — {submitError}. Try again; nothing was saved.
        </div>
      ) : null}
    </div>
  )
}
