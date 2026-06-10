import type { RefObject } from 'react'
import { FaultClass, SpanLink } from '@/components/ui/stamps'
import { CLUSTER_SET } from '@/lib/fixtures'
import type { DerivedAuditState } from '@/lib/types'

interface ClusterCardProps {
  s: DerivedAuditState
  clusterRef: RefObject<HTMLDivElement | null>
}

export function ClusterCard({ s, clusterRef }: ClusterCardProps) {
  const c = CLUSTER_SET.clusters[0]
  if (!c) return null
  const vis = s.flipProgress
  const settled = vis >= 1
  return (
    <div
      ref={clusterRef}
      style={{
        border: '1px solid ' + (settled ? 'var(--ember-glow)' : 'var(--chamber-line)'),
        borderRadius: 4,
        padding: '16px 18px',
        background: settled ? 'rgba(228,150,70,0.07)' : 'rgba(255,255,255,0.02)',
        boxShadow: settled ? '0 0 40px rgba(228,150,70,0.14)' : 'none',
        opacity: vis > 0 ? 0.35 + vis * 0.65 : 0.35,
        transition: 'border-color 0.6s ease, box-shadow 0.6s ease, background 0.6s ease',
      }}
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          gap: 10,
          marginBottom: 8,
          alignItems: 'baseline',
        }}
      >
        <span
          className="mono"
          style={{
            fontSize: 10,
            letterSpacing: '0.16em',
            color: settled ? 'var(--ember-glow)' : 'var(--chamber-ink-3)',
          }}
        >
          ROOT CAUSE CLUSTER {settled ? '· ' + c.clusterId : ''}
        </span>
        {settled ? (
          <span className="mono" style={{ fontSize: 10.5, color: 'var(--ember-glow)' }}>
            3 failures → 1 cause
          </span>
        ) : null}
      </div>
      {settled ? (
        <div>
          <div className="serif" style={{ fontSize: 16, lineHeight: 1.45, marginBottom: 10 }}>
            {c.rootCause}
          </div>
          <div
            style={{
              display: 'flex',
              gap: 8,
              flexWrap: 'wrap',
              alignItems: 'center',
            }}
          >
            {c.faultClasses.map((f) => (
              <FaultClass key={f} name={f} />
            ))}
            <span style={{ flex: 1 }}></span>
            {c.spanIds.map((sp) => (
              <SpanLink key={sp} id={sp} />
            ))}
          </div>
          <div
            className="mono"
            style={{ fontSize: 10, color: 'var(--chamber-ink-3)', marginTop: 9 }}
          >
            clustered by gemini-3.5-flash · cites EU AI Act {(c.articles ?? []).join(' / ')}
          </div>
        </div>
      ) : (
        <div className="mono" style={{ fontSize: 11.5, color: 'var(--chamber-ink-3)' }}>
          {s.phase === 'judge' ? (
            <span>
              clustering failures<span className="blink-caret">▌</span>
            </span>
          ) : (
            'awaiting judge phase'
          )}
        </div>
      )}
    </div>
  )
}
