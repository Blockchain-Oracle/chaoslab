'use client'

import { useRouter } from 'next/navigation'
import { A } from '@/components/ui/link'
import { PageFoot } from '@/components/ui/page-foot'
import { PageShell } from '@/components/ui/page-shell'
import { TopBar } from '@/components/ui/topbar'
import { AGENTS, fmtDate } from '@/lib/fixtures'
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
      <div
        style={{
          display: 'flex',
          gap: 10,
          alignItems: 'baseline',
          marginBottom: 6,
        }}
      >
        <span className="serif" style={{ fontSize: 18, flex: 1 }}>
          {a.name}
        </span>
        <span className="tag">
          Tier {a.tier} · {a.framework}
        </span>
      </div>
      <div className="mono muted" style={{ fontSize: 11, marginBottom: 12 }}>
        {a.url.replace('https://', '')}
      </div>
      <div
        style={{
          display: 'flex',
          gap: 8,
          alignItems: 'center',
          flexWrap: 'wrap',
        }}
      >
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
          last audit {fmtDate(a.lastAudit)}
        </span>
      </div>
    </div>
  )
}

export default function AgentsPage() {
  return (
    <PageShell label="agents">
      <div className="page-enter">
        <TopBar />
        <div className="shell" style={{ padding: '50px 40px 30px' }}>
          <div className="kicker" style={{ marginBottom: 12 }}>
            Registered targets
          </div>
          <h1 className="display" style={{ fontSize: 38, marginBottom: 34 }}>
            Target agents.
          </h1>
          <div style={{ display: 'grid', gap: 14, maxWidth: 760 }}>
            {AGENTS.map((a) => (
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
                Register another production agent — support copilots, voice agents, web-automation
                agents…
              </span>
              <A to="new" className="btn small ghost">
                Register target
              </A>
            </div>
          </div>
        </div>
        <PageFoot />
      </div>
    </PageShell>
  )
}
