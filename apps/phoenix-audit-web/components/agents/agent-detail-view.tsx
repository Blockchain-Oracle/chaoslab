'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { EmptyState } from '@/components/ui/empty-state'
import { A } from '@/components/ui/link'
import { PageFoot } from '@/components/ui/page-foot'
import { SectionHead } from '@/components/ui/section-head'
import { TopBar } from '@/components/ui/topbar'
import { runAuditHref } from '@/lib/cta'
import { AGENTS, HERO_RUN, HISTORY, agentById } from '@/lib/fixtures'
import { fmtDate } from '@/lib/format'
import type { MergedAgent, MergedRun } from '@/lib/sample-merge'
import { useSafeTimeout } from '@/lib/use-safe-timeout'

const snippetFor = (projectId: string) => `from phoenix_audit import instrument

# 3 lines, at your agent's startup:
instrument(project="${projectId}",
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
  const schedule = useSafeTimeout()
  if (!a) return null
  const isSample = agent ? agent.sample : true
  const runs = runsProp ?? HISTORY.filter((r) => r.agentId === a.id)
  const err = a.status === 'unreachable'
  // The wizard is the single confirm surface — no one-click live runs
  // (story-9.10: an un-confirmed click fired a real failing audit).
  const wizardHref = runAuditHref({ id: a.id, url: a.url, sample: isSample })
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
          <button className="btn ember" onClick={() => router.push(wizardHref)} disabled={err}>
            Run audit now
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
          <span className="mono muted" style={{ fontSize: 12 }}>
            {a.url}
          </span>
          {isSample ? (
            <span className="tag" title="Seeded sample data — not your registered agent">
              SAMPLE
            </span>
          ) : null}
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
                  <A to={wizardHref.slice(1)} className="btn small ember">
                    Run audit
                  </A>
                }
              />
            )}
          </div>

          <div style={{ display: 'grid', gap: 26 }}>
            <div className="card" style={{ padding: '18px 20px' }}>
              <span
                className="field-label"
                style={{ margin: 0, display: 'block', marginBottom: 8 }}
              >
                Continuous monitoring
              </span>
              <p className="muted" style={{ fontSize: 12.5, lineHeight: 1.6, marginBottom: 10 }}>
                Re-run the audit battery on a schedule — catch regressions before a regulator does.
              </p>
              {/* The real schedule form lives on /monitoring — no fake toggle
                  pretending state that nothing persists (story-9.10). */}
              <A
                to="monitoring"
                className="span-link"
                style={{ fontSize: 11.5, display: 'inline-block' }}
              >
                Set up a schedule →
              </A>
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
                <pre style={{ fontFamily: 'inherit', margin: 0, whiteSpace: 'pre' }}>
                  {snippetFor(a.id)}
                </pre>
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
