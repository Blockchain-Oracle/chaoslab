import { Fragment } from 'react'
import { A } from '@/components/ui/link'
import { Wordmark } from '@/components/ui/wordmark'
import type { DerivedAuditState } from '@/lib/types'

interface ChamberHeaderProps {
  s: DerivedAuditState
  /** displayed elapsed seconds; replay multiplies t by ~3.36 to match the projected 87s wall-clock */
  elapsedDisplay: number
  mode: 'replay' | 'live'
  /** Live-mode only: surfaced when the chamber is pacing from the timeline backfill */
  demoPacing?: boolean
  /** Live-mode only: actual EventSource open-state from the SSE bridge.
   *  The LIVE indicator must reflect reality, never assert "CONNECTED"
   *  unconditionally (review finding #5). */
  connected?: boolean
}

const PHASE_SEQ: DerivedAuditState['phase'][] = [
  'queued',
  'injector',
  'judge',
  'patcher',
  'succeeded',
]

export function ChamberHeader({
  s,
  elapsedDisplay,
  mode,
  demoPacing,
  connected,
}: ChamberHeaderProps) {
  const phaseIdx = PHASE_SEQ.indexOf(s.phase)
  return (
    <header
      style={{
        borderBottom: '1px solid var(--chamber-line)',
        position: 'relative',
        zIndex: 2,
      }}
    >
      <div
        style={{
          maxWidth: 1180,
          margin: '0 auto',
          padding: '0 40px',
          height: 58,
          display: 'flex',
          alignItems: 'center',
          gap: 20,
        }}
      >
        <A to="" style={{ textDecoration: 'none', color: 'inherit', display: 'flex' }}>
          <Wordmark size={15} glyph={17} />
        </A>
        <span style={{ width: 1, height: 20, background: 'var(--chamber-line)' }}></span>
        <span
          className="mono"
          style={{
            fontSize: 11,
            color: 'var(--chamber-ink-2)',
            letterSpacing: '0.04em',
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
          }}
        >
          run_9f3c2ab81d4e · prior-auth · EU AI Act
        </span>
        <span style={{ flex: 1 }}></span>
        {demoPacing ? (
          <span
            className="mono"
            title="Per-probe pacing comes from the deterministic timeline until the backend ships per-probe SSE events. Phase changes ARE live."
            style={{
              fontSize: 10,
              letterSpacing: '0.14em',
              color: 'var(--warn)',
              border: '1px dashed var(--warn)',
              padding: '4px 10px',
              borderRadius: 2,
              whiteSpace: 'nowrap',
            }}
          >
            DEMO PACING
          </span>
        ) : null}
        {mode === 'replay' ? (
          <span
            className="mono"
            style={{
              fontSize: 10.5,
              letterSpacing: '0.14em',
              color: 'var(--ember-glow)',
              border: '1px dashed var(--ember-glow)',
              padding: '4px 10px',
              borderRadius: 2,
              whiteSpace: 'nowrap',
            }}
          >
            PRE-RECORDED REPLAY
          </span>
        ) : connected ? (
          <span
            className="mono"
            style={{
              fontSize: 10.5,
              letterSpacing: '0.14em',
              color: 'var(--pass-glow)',
              display: 'inline-flex',
              gap: 8,
              alignItems: 'center',
            }}
          >
            <span className="phase-node active" style={{ color: 'var(--pass-glow)', gap: 0 }}>
              <span className="phase-dot"></span>
            </span>{' '}
            LIVE · SSE CONNECTED
          </span>
        ) : (
          <span
            className="mono"
            style={{
              fontSize: 10.5,
              letterSpacing: '0.14em',
              color: 'var(--warn)',
              display: 'inline-flex',
              gap: 8,
              alignItems: 'center',
            }}
          >
            <span
              style={{
                width: 7,
                height: 7,
                borderRadius: '50%',
                border: '1.4px solid var(--warn)',
                display: 'inline-block',
              }}
            ></span>{' '}
            SSE CONNECTING…
          </span>
        )}
        <A
          to="audits"
          className="mono"
          style={{
            fontSize: 10.5,
            letterSpacing: '0.1em',
            color: 'var(--chamber-ink-3)',
          }}
        >
          EXIT
        </A>
      </div>
      {/* phase rail */}
      <div
        style={{
          maxWidth: 1180,
          margin: '0 auto',
          padding: '14px 40px',
          display: 'flex',
          gap: 26,
          alignItems: 'center',
        }}
      >
        {PHASE_SEQ.map((p, i) => (
          <Fragment key={p}>
            {i > 0 ? (
              <span
                style={{
                  flex: 1,
                  height: 1,
                  background: i <= phaseIdx ? 'var(--ember-glow)' : 'var(--chamber-line)',
                  transition: 'background 0.5s ease',
                }}
              ></span>
            ) : null}
            <span
              className={
                'phase-node ' +
                (p === s.phase && p !== 'succeeded'
                  ? 'active'
                  : i < phaseIdx || s.phase === 'succeeded'
                    ? 'done'
                    : '')
              }
              style={{ whiteSpace: 'nowrap' }}
            >
              <span className="phase-dot"></span>
              {p === 'succeeded' ? 'signed & done' : p}
            </span>
          </Fragment>
        ))}
        <span
          className="mono num"
          style={{
            fontSize: 11,
            color: 'var(--chamber-ink-2)',
            marginLeft: 10,
            whiteSpace: 'nowrap',
          }}
        >
          {elapsedDisplay.toFixed(0)}s elapsed
        </span>
      </div>
    </header>
  )
}
