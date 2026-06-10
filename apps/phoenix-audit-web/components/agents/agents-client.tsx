'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { A } from '@/components/ui/link'
import { PageFoot } from '@/components/ui/page-foot'
import { TopBar } from '@/components/ui/topbar'
import { fmtDate } from '@/lib/format'
import { visibleRows } from '@/lib/sample-merge'
import type { MergedAgent } from '@/lib/sample-merge'

function AgentCard({ a }: { a: MergedAgent }) {
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
          <span className="tag" style={{ fontSize: 9.5, opacity: 0.7 }} title="Seeded sample data">
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
          {a.sample ? 'last audit ' : 'registered '}
          {fmtDate(a.lastAudit)}
        </span>
      </div>
    </div>
  )
}

export interface AgentsClientProps {
  agents: MergedAgent[]
  liveError: string | null
}

export function AgentsClient({ agents, liveError }: AgentsClientProps) {
  // Own-data-first (story-9.10): sample agents render only on request. The
  // demo-target seed is REAL (registered + deployed), so a fresh account
  // still has one agent it can audit immediately.
  const [showSamples, setShowSamples] = useState(false)
  const sampleCount = agents.filter((a) => a.sample).length
  const visible = visibleRows(agents, showSamples)
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
            ⚠ LIVE REGISTRY UNAVAILABLE — showing sample data only. ({liveError})
          </div>
        ) : null}
        {sampleCount > 0 ? (
          <div style={{ marginBottom: 18 }}>
            <button
              className="btn small ghost"
              aria-pressed={showSamples}
              onClick={() => setShowSamples((s) => !s)}
            >
              {showSamples ? 'Hide sample agents' : `Explore sample agents (${sampleCount} seeded)`}
            </button>
          </div>
        ) : null}
        <div style={{ display: 'grid', gap: 14, maxWidth: 760 }}>
          {visible.map((a) => (
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
