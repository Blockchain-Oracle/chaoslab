import { Fragment } from 'react'
import { A } from '@/components/ui/link'
import { Wordmark } from '@/components/ui/wordmark'
import type { Phase } from '@/lib/types'

interface ChamberHeaderProps {
  phase: Phase
  /** Displayed elapsed seconds — live wall-clock or the replay scrub time. */
  elapsedDisplay: number
  mode: 'replay' | 'live'
  /** Live-mode only: actual EventSource open-state from the SSE bridge.
   *  The LIVE indicator must reflect reality, never assert "CONNECTED"
   *  unconditionally (review finding #5). */
  connected?: boolean
  /** The REAL run's header line — there is no fixture default (story-9.11). */
  runLabel: string
}

const PHASE_SEQ: Phase[] = ['queued', 'injector', 'judge', 'patcher', 'succeeded']

export function ChamberHeader({
  phase,
  elapsedDisplay,
  mode,
  connected,
  runLabel,
}: ChamberHeaderProps) {
  const phaseIdx = PHASE_SEQ.indexOf(phase)
  return (
    <header
      style={{
        borderBottom: '1px solid var(--chamber-line)',
        position: 'relative',
        zIndex: 2,
      }}
    >
      <div
        className="chamber-header-row"
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
          {runLabel}
        </span>
        <span style={{ flex: 1 }}></span>
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
        className="phase-rail"
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
                (p === phase && p !== 'succeeded'
                  ? 'active'
                  : i < phaseIdx || phase === 'succeeded'
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
