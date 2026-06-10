'use client'

import { useRouter } from 'next/navigation'
import { A } from '@/components/ui/link'
import { PageFoot } from '@/components/ui/page-foot'
import { TopBar } from '@/components/ui/topbar'
import { fmtDate } from '@/lib/format'
import type { AgentSpec } from '@/lib/types'

function AgentCard({ a }: { a: AgentSpec }) {
  const router = useRouter()
  const err = a.status === 'unreachable'
  return (
    <div
      className="card"
      style={{
        padding: '20px 22px',
        cursor: 'pointer',
        borderColor: err ? 'var(--fail)' : undefined,
      }}
      onClick={() => router.push(`/agents/${a.id}`)}
    >
      <div style={{ display: 'flex', gap: 10, alignItems: 'baseline', marginBottom: 6 }}>
        <span className="serif" style={{ fontSize: 18, flex: 1 }}>
          {a.name}
        </span>
        {a.sample ? (
          <span
            className="tag"
            style={{ fontSize: 9.5, opacity: 0.7 }}
            title="Seeded demo target — a real deployed agent, visible to every account"
          >
            SAMPLE
          </span>
        ) : null}
        <span className="tag">
          Tier {a.tier} · {a.framework}
        </span>
      </div>
      <div className="mono muted" style={{ fontSize: 11, marginBottom: 12 }}>
        {a.url.replace('https://', '').replace('http://', '')}
      </div>
      <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
        <span className="tag">
          Depth {a.depth} · {a.depth === 2 ? 'instrumented' : 'black-box'}
        </span>
        {a.monitoring.enabled && a.monitoring.cadence ? (
          <span className="tag" style={{ color: 'var(--pass)' }}>
            ● monitored {a.monitoring.cadence.toLowerCase()}
          </span>
        ) : null}
        {err ? (
          <span className="stamp fail" style={{ fontSize: 9.5 }}>
            Unreachable
          </span>
        ) : null}
        <span style={{ flex: 1 }}></span>
        <span className="mono muted" style={{ fontSize: 10.5 }}>
          registered {fmtDate(a.lastAudit)}
        </span>
      </div>
    </div>
  )
}

export interface AgentsClientProps {
  agents: AgentSpec[]
  liveError: string | null
}

export function AgentsClient({ agents, liveError }: AgentsClientProps) {
  // Seeded demo targets are REAL deployed agents — listed for every account,
  // labeled SAMPLE (story-9.11). A fresh account always has one runnable target.
  return (
    <div className="page-enter">
      <TopBar />
      <div className="shell" style={{ padding: '50px 40px 30px' }}>
        <div className="kicker" style={{ marginBottom: 12 }}>
          Registered targets
        </div>
        <h1 className="display" style={{ fontSize: 38, marginBottom: 34 }}>
          Target agents.
        </h1>
        {liveError ? (
          <div
            className="mono"
            style={{
              fontSize: 11,
              color: 'var(--warn, #8a6d1a)',
              border: '1px dashed currentColor',
              borderRadius: 4,
              padding: '10px 14px',
              marginBottom: 24,
              maxWidth: 760,
            }}
          >
            ⚠ LIVE REGISTRY UNAVAILABLE — nothing can be listed right now. ({liveError})
          </div>
        ) : null}
        <div style={{ display: 'grid', gap: 14, maxWidth: 760 }}>
          {agents.map((a) => (
            <AgentCard key={a.id} a={a} />
          ))}
          <div
            style={{
              border: '1px dashed var(--hairline)',
              borderRadius: 'var(--r-lg)',
              padding: '18px 22px',
              display: 'flex',
              alignItems: 'center',
              gap: 14,
            }}
          >
            <span className="muted" style={{ fontSize: 13.5, flex: 1 }}>
              Audit another production agent — support copilots, voice agents, web-automation
              agents…
            </span>
            <A to="new" className="btn small ghost">
              New audit
            </A>
          </div>
        </div>
      </div>
      <PageFoot />
    </div>
  )
}
