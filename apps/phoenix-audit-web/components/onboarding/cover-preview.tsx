// Story-9.14 redesign — CoverPreview (O-3). A live miniature of the
// regulator-facing audit-report cover sheet that fills in as the
// operator answers the wizard. Persistent context: visible across all
// steps in the left rail so each answer has a visible consequence.

import { Seal } from '@/components/ui/seal'

interface Props {
  org: string
  framework: string
  email: string | null
  caption?: boolean
}

// One framework string maps to one regulator-facing citation line. Held
// here (not in a shared module) because the cover-sheet rendering is
// the only place that needs the cited form — the rest of the app shows
// the framework name itself.
const FRAMEWORK_CITATIONS: Record<string, string> = {
  'EU AI Act': 'ART. 9, 11–15, 72 · ANNEX IV',
  'NIST AI RMF': 'GOVERN · MAP · MEASURE · MANAGE',
  HIPAA: '§164.312 TECHNICAL SAFEGUARDS',
  'SOC 2 + AI': 'TRUST SERVICES CRITERIA + AI',
  Custom: 'YOUR CONTROL IDs, CITED VERBATIM',
}

export function CoverPreview({ org, framework, email, caption = true }: Props) {
  const cited = FRAMEWORK_CITATIONS[framework] ?? FRAMEWORK_CITATIONS['EU AI Act']!
  const filer = email ? email.toUpperCase() : 'YOUR ACCOUNT'
  return (
    <div>
      <div className="onb-cover">
        <span className="cover-seal">
          <Seal size={42} spin={true} />
        </span>
        <div
          className="mono"
          style={{
            fontSize: 8.5,
            letterSpacing: '0.2em',
            color: 'var(--ink-3)',
            marginBottom: 16,
            paddingRight: 48,
          }}
        >
          SIGNED AUDIT REPORT
        </div>
        <div
          className="mono"
          style={{ fontSize: 8.5, letterSpacing: '0.16em', color: 'var(--ink-3)', marginBottom: 4 }}
        >
          PREPARED BY
        </div>
        <div
          className="serif"
          style={{ fontSize: 16.5, lineHeight: 1.25, marginBottom: 11, minHeight: 21 }}
        >
          {org ? (
            org
          ) : (
            <span className="blank mono" style={{ fontSize: 10.5 }}>
              org name · set later
            </span>
          )}
        </div>
        <div
          className="mono"
          style={{
            fontSize: 9,
            letterSpacing: '0.08em',
            color: 'var(--ember-deep)',
            marginBottom: 11,
          }}
        >
          {framework.toUpperCase()} · {cited}
        </div>
        <div
          style={{
            borderTop: '1px solid var(--hairline-soft)',
            paddingTop: 8,
            display: 'grid',
            gap: 3,
          }}
        >
          <div
            className="mono"
            style={{ fontSize: 8, letterSpacing: '0.05em', color: 'var(--ink-3)' }}
          >
            FILED BY {filer}
          </div>
          <div
            className="mono"
            style={{ fontSize: 8, letterSpacing: '0.05em', color: 'var(--ink-3)' }}
          >
            SIGNATURE · CLOUD KMS · PENDING FIRST RUN
          </div>
        </div>
      </div>
      {caption ? (
        <p className="muted" style={{ fontSize: 11.5, marginTop: 9, lineHeight: 1.55 }}>
          Your cover sheet — it fills in as you answer.
        </p>
      ) : null}
    </div>
  )
}
