import type { Phase } from '@/lib/types'

interface StationProps {
  label: string
  sub: string
  active: boolean
  done: boolean
}

function Station({ label, sub, active, done }: StationProps) {
  const border = active
    ? 'var(--ember-glow)'
    : done
      ? 'var(--chamber-ink-3)'
      : 'var(--chamber-line)'
  return (
    <div
      style={{
        border: '1px solid ' + border,
        borderRadius: 4,
        padding: '11px 14px',
        flex: 1,
        background: active ? 'rgba(228,150,70,0.08)' : 'rgba(255,255,255,0.02)',
        boxShadow: active ? '0 0 26px rgba(228,150,70,0.16)' : 'none',
        transition: 'border-color 0.5s ease, box-shadow 0.5s ease, background 0.5s ease',
      }}
    >
      <div
        className="mono"
        style={{
          fontSize: 10.5,
          letterSpacing: '0.16em',
          color: active
            ? 'var(--ember-glow)'
            : done
              ? 'var(--chamber-ink-2)'
              : 'var(--chamber-ink-3)',
          display: 'flex',
          alignItems: 'center',
          gap: 8,
        }}
      >
        <span
          className={'phase-node ' + (active ? 'active' : done ? 'done' : '')}
          style={{ gap: 0 }}
        >
          <span className="phase-dot"></span>
        </span>
        {label}
      </div>
      <div style={{ fontSize: 11.5, color: 'var(--chamber-ink-3)', marginTop: 4 }}>{sub}</div>
    </div>
  )
}

function Connector({ active }: { active: boolean }) {
  return (
    <svg
      width="22"
      height="56"
      viewBox="0 0 22 56"
      style={{ alignSelf: 'center', flexShrink: 0 }}
      aria-hidden="true"
    >
      <path
        d="M0 28 H22"
        stroke={active ? 'var(--ember-glow)' : 'var(--chamber-line)'}
        strokeWidth="1.2"
        strokeDasharray="3 3"
        style={{ transition: 'stroke 0.5s ease' }}
      />
    </svg>
  )
}

interface PipelineProps {
  phase: Phase
}

export function Pipeline({ phase }: PipelineProps) {
  const seq: Phase[] = ['injector', 'judge', 'patcher']
  const idx = seq.indexOf(phase)
  const doneIdx = phase === 'succeeded' ? 3 : idx
  const probing = phase === 'injector'
  return (
    <div>
      <div
        className="mono"
        style={{
          fontSize: 10,
          letterSpacing: '0.2em',
          color: 'var(--chamber-ink-3)',
          marginBottom: 12,
        }}
      >
        AUDIT PIPELINE — A MULTI-AGENT SYSTEM
      </div>
      <div className="pipeline-row" style={{ display: 'flex', gap: 10, alignItems: 'stretch' }}>
        <Station
          label="INJECTOR"
          sub="sends the test battery"
          active={phase === 'injector'}
          done={doneIdx > 0}
        />
        <Connector active={doneIdx >= 1} />
        <Station
          label="JUDGE"
          sub="verdicts + clustering"
          active={phase === 'judge'}
          done={doneIdx > 1}
        />
        <Connector active={doneIdx >= 2} />
        <Station
          label="PATCHER"
          sub="hardening recipe"
          active={phase === 'patcher'}
          done={doneIdx > 2}
        />
      </div>
      {/* target agent lane */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 0, margin: '4px 0 0 36px' }}>
        <svg width="40" height="58" viewBox="0 0 40 58" fill="none" aria-hidden="true">
          <path
            d="M20 0 V44 M20 44 H40"
            stroke="var(--chamber-line)"
            strokeWidth="1"
            strokeDasharray="2 4"
          />
          {probing ? (
            <circle r="2.6" fill="var(--ember-glow)">
              <animateMotion dur="1.1s" repeatCount="indefinite" path="M20 2 V44 H40" />
            </circle>
          ) : null}
        </svg>
        <div
          style={{
            border: '1px dashed ' + (probing ? 'var(--ember-glow)' : 'var(--chamber-line)'),
            borderRadius: 4,
            padding: '9px 14px',
            marginTop: 26,
            transition: 'border-color 0.5s ease',
          }}
        >
          <div
            className="mono"
            style={{
              fontSize: 10.5,
              letterSpacing: '0.14em',
              color: probing ? 'var(--ember-glow)' : 'var(--chamber-ink-2)',
            }}
          >
            TARGET AGENT
          </div>
          <div
            className="mono"
            style={{ fontSize: 10.5, color: 'var(--chamber-ink-3)', marginTop: 3 }}
          >
            instrumented over A2A · traces land in Phoenix
          </div>
        </div>
      </div>
    </div>
  )
}
