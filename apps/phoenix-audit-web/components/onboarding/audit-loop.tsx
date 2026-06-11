// Story-9.14 redesign — AuditLoop (O-2). Welcome-step SVG illustration:
// center diamond is "your agent under audit"; the Phoenix glyph orbits
// the 90-second loop through four stations (battery / judge / cluster
// / sign). Pure decorative SVG — `aria-hidden` on the figure; the
// adjacent caption carries the same meaning for AT users.

import { Glyph } from '@/components/ui/glyph'

interface Props {
  caption?: boolean
}

export function AuditLoop({ caption = true }: Props) {
  return (
    <div>
      <div className="audit-loop" aria-hidden="true">
        <svg
          width="330"
          height="300"
          viewBox="0 0 330 300"
          fill="none"
          style={{ position: 'absolute', inset: 0 }}
        >
          <circle
            cx="165"
            cy="150"
            r="92"
            stroke="var(--hairline)"
            strokeWidth="1.2"
            strokeDasharray="2 6"
          />
          <circle cx="165" cy="58" r="2.5" fill="var(--ink-3)" />
          <circle cx="257" cy="150" r="2.5" fill="var(--ink-3)" />
          <circle cx="165" cy="242" r="2.5" fill="var(--ink-3)" />
          <circle
            cx="73"
            cy="150"
            r="8"
            stroke="var(--ember-deep)"
            strokeWidth="1"
            strokeDasharray="1.5 2.5"
          />
          <circle cx="73" cy="150" r="2.5" fill="var(--ember-deep)" />
        </svg>
        <div className="loop-center">
          <svg width="42" height="42" viewBox="0 0 42 42" fill="none">
            <path
              d="M21 7 L34.5 21 L21 35 L7.5 21 Z"
              stroke="var(--ink)"
              strokeWidth="1.4"
              fill="rgba(255,255,255,0.6)"
            />
          </svg>
          <div
            className="mono"
            style={{ fontSize: 9, letterSpacing: '0.16em', color: 'var(--ink-3)' }}
          >
            YOUR AGENT
          </div>
        </div>
        <div className="loop-orbit">
          <span className="orbiter">
            <Glyph size={17} color="var(--ember-deep)" />
          </span>
        </div>
        <span className="loop-label n">
          <span className="no">01</span> ADVERSARIAL BATTERY
        </span>
        <span className="loop-label e">
          <span className="no">02</span> JUDGE
        </span>
        <span className="loop-label s">
          <span className="no">03</span> ROOT-CAUSE CLUSTER
        </span>
        <span className="loop-label w">
          <span className="no">04</span> SIGN
        </span>
      </div>
      {caption ? (
        <div
          className="mono"
          style={{
            fontSize: 9.5,
            letterSpacing: '0.14em',
            color: 'var(--ink-3)',
            textAlign: 'center',
            marginTop: 8,
          }}
        >
          ONE LOOP ≈ 90 SECONDS · ENDS SIGNED
        </div>
      ) : null}
    </div>
  )
}
