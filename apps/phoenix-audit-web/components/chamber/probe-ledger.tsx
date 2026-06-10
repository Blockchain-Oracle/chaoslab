import type { RefObject } from 'react'
import { Citation, HonoredDot, ModeTag, SpanLink, Verdict } from '@/components/ui/stamps'
import type { DerivedAuditState, DerivedTestState } from '@/lib/types'

interface ProbeRowProps {
  test: DerivedTestState
  t: number
  failRef: RefObject<HTMLSpanElement | null> | null
}

function ProbeRow({ test, t, failRef }: ProbeRowProps) {
  const landed = test.state === 'done'
  const fresh = landed && t - test.ev.end < 0.6 // t-driven; capture/scrub safe
  return (
    <div className={'probe-row ' + (landed ? 'landed' : test.state === 'running' ? 'running' : '')}>
      <span className="mono" style={{ fontSize: 11, color: 'var(--chamber-ink-3)' }}>
        {String(test.n).padStart(2, '0')}
      </span>
      <div style={{ minWidth: 0 }}>
        <div
          style={{
            display: 'flex',
            gap: 9,
            alignItems: 'center',
            flexWrap: 'wrap',
            marginBottom: 3,
          }}
        >
          <span style={{ fontSize: 13.5, color: 'var(--chamber-ink)' }}>{test.name}</span>
          <Citation title={test.citationLong}>{test.citation}</Citation>
          <ModeTag mode={test.mode} />
        </div>
        <div
          style={{
            display: 'flex',
            gap: 14,
            alignItems: 'center',
            flexWrap: 'wrap',
          }}
        >
          {landed ? (
            <HonoredDot honored={test.honored} dark />
          ) : (
            <span className="mono" style={{ fontSize: 10.5, color: 'var(--chamber-ink-3)' }}>
              {test.state === 'running' ? (
                <span>
                  probing<span className="blink-caret">▌</span>
                </span>
              ) : (
                'queued'
              )}
            </span>
          )}
          {landed ? <SpanLink id={test.spanId} /> : null}
          {landed && test.article ? (
            <span
              className="mono"
              style={{
                fontSize: 10.5,
                color: 'var(--fail-glow)',
                letterSpacing: '0.04em',
              }}
            >
              {test.article}
            </span>
          ) : null}
        </div>
      </div>
      <span ref={failRef} style={{ justifySelf: 'end' }}>
        {landed ? (
          <span className={fresh ? 'verdict-in' : ''} style={{ display: 'inline-flex' }}>
            <Verdict v={test.verdict} />
          </span>
        ) : (
          <span className="stamp neutral">·····</span>
        )}
      </span>
    </div>
  )
}

interface ProbeLedgerProps {
  s: DerivedAuditState
  failRefs: Array<RefObject<HTMLSpanElement | null>>
}

export function ProbeLedger({ s, failRefs }: ProbeLedgerProps) {
  let failIdx = -1
  return (
    <div style={{ border: '1px solid var(--chamber-line)', borderRadius: 4 }}>
      <div
        style={{
          padding: '11px 18px',
          borderBottom: '1px solid var(--chamber-line)',
          display: 'flex',
          alignItems: 'baseline',
          gap: 12,
        }}
      >
        <span
          className="mono"
          style={{
            fontSize: 10,
            letterSpacing: '0.2em',
            color: 'var(--chamber-ink-3)',
          }}
        >
          ADVERSARIAL TEST BATTERY
        </span>
        <span style={{ flex: 1 }}></span>
        <span className="mono num" style={{ fontSize: 11, color: 'var(--pass-glow)' }}>
          {s.passDone} pass
        </span>
        <span className="mono num" style={{ fontSize: 11, color: 'var(--fail-glow)' }}>
          {s.failDone} fail
        </span>
        <span className="mono num" style={{ fontSize: 11, color: 'var(--chamber-ink-3)' }}>
          {s.doneCount}/6
        </span>
      </div>
      {s.tests.map((test) => {
        if (test.verdict === 'fail') failIdx += 1
        const ref = test.verdict === 'fail' ? (failRefs[failIdx] ?? null) : null
        return <ProbeRow key={test.n} test={test} t={s.t} failRef={ref} />
      })}
    </div>
  )
}
