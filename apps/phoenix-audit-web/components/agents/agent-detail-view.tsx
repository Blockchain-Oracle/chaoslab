'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { EmptyState } from '@/components/ui/empty-state'
import { A } from '@/components/ui/link'
import { PageFoot } from '@/components/ui/page-foot'
import { SectionHead } from '@/components/ui/section-head'
import { Toggle } from '@/components/ui/toggle'
import { TopBar } from '@/components/ui/topbar'
import { AGENTS, HERO_RUN, HISTORY, agentById } from '@/lib/fixtures'
import { fmtDate } from '@/lib/format'
import type { MergedAgent, MergedRun } from '@/lib/sample-merge'
import { useSafeTimeout } from '@/lib/use-safe-timeout'

const SNIPPET = `from phoenix_audit import instrument

# 3 lines, at your agent's startup:
instrument(project="prior-auth",
           endpoint=PHOENIX_COLLECTOR,
           audit_headers=True)`

interface AgentDetailViewProps {
  id: string
  /** Server-provided real agent (sample=false) or labeled sample. Fixture
   *  lookup remains the fallback for legacy callers. */
  agent?: MergedAgent
  /** Server-provided run history (real + sample, labeled). */
  runs?: MergedRun[]
}

export function AgentDetailView({ id, agent, runs: runsProp }: AgentDetailViewProps) {
  const router = useRouter()
  const a = agent ?? agentById(id) ?? AGENTS[0]
  const [copied, setCopied] = useState(false)
  const [mon, setMon] = useState(!!a?.monitoring.enabled)
  const [starting, setStarting] = useState(false)
  const [startError, setStartError] = useState<string | null>(null)
  const schedule = useSafeTimeout()
  if (!a) return null
  const isSample = agent ? agent.sample : true
  const runs = runsProp ?? HISTORY.filter((r) => r.agentId === a.id)
  const err = a.status === 'unreachable'
  const runHero = async () => {
    if (typeof window !== 'undefined') {
      window.localStorage.removeItem('pa_audit_t_live')
    }
    if (isSample) {
      // Sample agents demo the chamber via the fixture replay.
      router.push('/replay')
      return
    }
    setStarting(true)
    setStartError(null)
    try {
      const res = await fetch('/api/agent/run', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ target_url: a.url, agent_id: a.id, source: 'manual' }),
      })
      if (!res.ok) throw new Error(`the audit service answered ${res.status}`)
      const body = (await res.json()) as { run_id?: string }
      if (!body.run_id) throw new Error('the audit service returned no run id')
      router.push(`/run/${body.run_id}`)
    } catch (e) {
      setStartError(e instanceof Error ? e.message : String(e))
      setStarting(false)
    }
  }
  return (
    <div className="page-enter">
      <TopBar />
      <div className="shell" style={{ padding: '50px 40px 30px' }}>
        <div className="mono muted" style={{ fontSize: 11, marginBottom: 16 }}>
          <A to="agents" style={{ color: 'var(--ember-deep)', textDecoration: 'none' }}>
            TARGET AGENTS
          </A>{' '}
          / {a.id}
        </div>
        <div
          style={{
            display: 'flex',
            alignItems: 'flex-end',
            gap: 18,
            marginBottom: 10,
          }}
        >
          <h1 className="display" style={{ fontSize: 38, flex: 1 }}>
            {a.name}
          </h1>
          <button className="btn ember" onClick={runHero} disabled={err || starting}>
            {starting ? 'Starting…' : 'Run audit now'}
          </button>
        </div>
        <div
          style={{
            display: 'flex',
            gap: 10,
            alignItems: 'center',
            flexWrap: 'wrap',
            marginBottom: 36,
          }}
        >
          {startError ? (
            <span className="mono" style={{ fontSize: 11.5, color: 'var(--fail)', width: '100%' }}>
              ✕ Could not start the audit — {startError}
            </span>
          ) : null}
          <span className="mono muted" style={{ fontSize: 12 }}>
            {a.url}
          </span>
          <span className="tag">
            Tier {a.tier} · {a.framework}
          </span>
          <span className="tag">{a.transport}</span>
          <span className="tag">Depth {a.depth}</span>
        </div>

        {err ? (
          <div
            style={{
              border: '1px solid var(--fail)',
              background: 'var(--fail-soft)',
              borderRadius: 'var(--r-lg)',
              padding: '16px 20px',
              marginBottom: 36,
              display: 'flex',
              gap: 14,
              alignItems: 'center',
            }}
          >
            <span className="stamp fail">Unreachable</span>
            <span style={{ fontSize: 13.5, color: 'var(--ink-2)', flex: 1 }}>
              The probe ping has failed since 28 May. Audits are paused for this target until it
              responds over HTTPS.
            </span>
            <button className="btn small ghost">Retry probe</button>
          </div>
        ) : null}

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: '1fr 380px',
            gap: 44,
            alignItems: 'start',
          }}
        >
          <div>
            <SectionHead no="§1" title="Audit history — this agent" />
            {runs.length ? (
              <table className="ledger">
                <thead>
                  <tr>
                    <th>Run</th>
                    <th>Framework</th>
                    <th>Verdicts</th>
                    <th>Filed</th>
                  </tr>
                </thead>
                <tbody>
                  {runs.map((r) => {
                    const path = r.id === HERO_RUN.id ? '/replay' : `/report/${r.id}`
                    return (
                      <tr key={r.id} className="clickable" onClick={() => router.push(path)}>
                        <td className="mono" style={{ fontSize: 11.5 }}>
                          {r.id}
                        </td>
                        <td>
                          <span className="tag">{r.framework}</span>
                        </td>
                        <td className="mono num">
                          <span style={{ color: 'var(--pass)' }}>{r.pass}✓</span>
                          <span className="muted"> / </span>
                          <span
                            style={{
                              color: r.fail ? 'var(--fail)' : 'var(--ink-3)',
                            }}
                          >
                            {r.fail}✕
                          </span>
                        </td>
                        <td className="mono muted" style={{ fontSize: 11 }}>
                          {fmtDate(r.date)}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            ) : (
              <EmptyState
                kicker="NO AUDITS YET"
                title="This agent hasn't been audited."
                body="Run the first audit to establish a signed baseline for this target."
                action={
                  <A to="new" className="btn small ember">
                    Run audit
                  </A>
                }
              />
            )}
          </div>

          <div style={{ display: 'grid', gap: 26 }}>
            <div className="card" style={{ padding: '18px 20px' }}>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 12,
                  marginBottom: 8,
                }}
              >
                <span className="field-label" style={{ margin: 0, flex: 1 }}>
                  Continuous monitoring
                </span>
                <Toggle on={mon} onChange={setMon} label="continuous monitoring" />
              </div>
              {mon ? (
                <div>
                  <div className="leader-row" style={{ padding: '4px 0' }}>
                    <span style={{ fontSize: 12.5, color: 'var(--ink-2)' }}>Cadence</span>
                    <span className="leader-fill"></span>
                    <span className="mono" style={{ fontSize: 11.5 }}>
                      Daily · 06:00 UTC
                    </span>
                  </div>
                  <div className="leader-row" style={{ padding: '4px 0' }}>
                    <span style={{ fontSize: 12.5, color: 'var(--ink-2)' }}>Window</span>
                    <span className="leader-fill"></span>
                    <span className="mono" style={{ fontSize: 11.5 }}>
                      last 24 h of traffic
                    </span>
                  </div>
                  <A
                    to="monitoring"
                    className="span-link"
                    style={{ fontSize: 11.5, marginTop: 8, display: 'inline-block' }}
                  >
                    Configure schedule →
                  </A>
                </div>
              ) : (
                <p className="muted" style={{ fontSize: 12.5, lineHeight: 1.6 }}>
                  Audit real production traces on a schedule — catch failures that actually
                  happened, not just synthetic ones.
                </p>
              )}
            </div>

            <div>
              <div className="field-label" style={{ marginBottom: 10 }}>
                {a.depth === 2
                  ? 'Instrumentation snippet · Depth 2'
                  : 'Ready to upgrade to Depth 2?'}
              </div>
              {a.depth === 1 ? (
                <p className="muted" style={{ fontSize: 12.5, marginBottom: 10, lineHeight: 1.6 }}>
                  Add these 3 lines to the agent&apos;s startup and the next audit gains full
                  root-cause clustering.
                </p>
              ) : null}
              <div className="codeblock" style={{ position: 'relative', fontSize: 11.5 }}>
                <pre style={{ fontFamily: 'inherit', margin: 0, whiteSpace: 'pre' }}>{SNIPPET}</pre>
                <button
                  className="btn small"
                  style={{
                    position: 'absolute',
                    top: 10,
                    right: 10,
                    borderColor: 'var(--chamber-line)',
                    color: 'var(--chamber-ink)',
                    padding: '5px 10px',
                  }}
                  onClick={() => {
                    setCopied(true)
                    schedule(() => setCopied(false), 1500)
                  }}
                >
                  {copied ? 'Copied ✓' : 'Copy'}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
      <PageFoot />
    </div>
  )
}
