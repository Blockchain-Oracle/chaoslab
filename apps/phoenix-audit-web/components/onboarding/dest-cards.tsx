// Story-9.14 redesign — DestCards (O-6). The Finish step: two
// destination cards (run first audit / browse samples) — picking one
// IS the finish. Cards visibly enter a "FILING YOUR PROFILE…" busy
// state when the PATCH is in flight, and an inline error tied to the
// chosen card (not a toast) when the PATCH fails so retry-attempt and
// failure stay anchored to the same affordance.

type Destination = 'new' | 'audits'

interface Props {
  submitting: boolean
  submitError: string | null
  choice: Destination | null
  onPick: (destination: Destination) => void
}

function DestMarkProbe() {
  return (
    <svg width="52" height="34" viewBox="0 0 52 34" fill="none" aria-hidden="true">
      <path d="M2 17 H24" stroke="var(--ember-deep)" strokeWidth="1.2" strokeDasharray="3 3" />
      <path d="M20 13 L26 17 L20 21" stroke="var(--ember-deep)" strokeWidth="1.2" fill="none" />
      <path d="M40 6 L51 17 L40 28 L29 17 Z" stroke="var(--ink)" strokeWidth="1.3" fill="none" />
    </svg>
  )
}

function DestMarkSamples() {
  return (
    <svg width="52" height="34" viewBox="0 0 52 34" fill="none" aria-hidden="true">
      <path d="M2 8 H34" stroke="var(--ink-2)" strokeWidth="1.2" />
      <path d="M2 17 H26" stroke="var(--ink-2)" strokeWidth="1.2" />
      <path d="M2 26 H30" stroke="var(--ink-2)" strokeWidth="1.2" />
      <circle
        cx="44"
        cy="24"
        r="6.5"
        stroke="var(--ember-deep)"
        strokeWidth="1"
        strokeDasharray="1.5 2"
      />
      <circle cx="44" cy="24" r="2" fill="var(--ember-deep)" />
    </svg>
  )
}

interface CardProps {
  id: Destination
  mark: React.ReactNode
  title: string
  route: string
  body: string
  chosen: boolean
  paused: boolean
  error: boolean
  onPick: () => void
}

function Card({ mark, title, route, body, chosen, paused, error, onPick }: CardProps) {
  const cls = ['opt-card', chosen ? 'chosen' : ''].filter(Boolean).join(' ')
  return (
    <div
      className={cls}
      role="button"
      aria-disabled={paused || undefined}
      onClick={paused ? undefined : onPick}
      style={{ cursor: paused ? 'default' : 'pointer' }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 10,
          marginBottom: 14,
        }}
      >
        {mark}
        <span className="mono muted" style={{ fontSize: 10, whiteSpace: 'nowrap' }}>
          → {route}
        </span>
      </div>
      <div className="serif" style={{ fontSize: 17.5, marginBottom: 7 }}>
        {title}
      </div>
      <p style={{ fontSize: 13, color: 'var(--ink-2)', lineHeight: 1.6 }}>{body}</p>
      {chosen && paused ? (
        <div
          style={{
            display: 'flex',
            gap: 10,
            alignItems: 'center',
            marginTop: 12,
            color: 'var(--ember-deep)',
          }}
        >
          <span className="busy-dot" />
          <span className="mono" style={{ fontSize: 10.5, letterSpacing: '0.1em' }}>
            FILING YOUR PROFILE…
          </span>
        </div>
      ) : null}
      {chosen && error ? (
        <div
          className="mono"
          style={{
            fontSize: 10,
            letterSpacing: '0.1em',
            marginTop: 12,
            color: 'var(--fail)',
          }}
        >
          ✕ DIDN&rsquo;T SAVE — CLICK AGAIN TO RETRY
        </div>
      ) : null}
    </div>
  )
}

export function DestCards({ submitting, submitError, choice, onPick }: Props) {
  const paused = submitting
  return (
    <div className={paused ? 'onb-dest-grid paused' : 'onb-dest-grid'}>
      <Card
        id="new"
        mark={<DestMarkProbe />}
        title="Run your first audit"
        route="/new"
        body="The real flow: point us at an HTTPS or A2A endpoint. About 90 seconds, ends with a signed PDF you can file."
        chosen={choice === 'new'}
        paused={paused}
        error={Boolean(submitError) && choice === 'new'}
        onPick={() => onPick('new')}
      />
      <Card
        id="audits"
        mark={<DestMarkSamples />}
        title="Browse sample audits"
        route="/audits"
        body="Two seeded sample runs — full preview, replay, hardening recipe and signature, all genuinely signed."
        chosen={choice === 'audits'}
        paused={paused}
        error={Boolean(submitError) && choice === 'audits'}
        onPick={() => onPick('audits')}
      />
    </div>
  )
}
