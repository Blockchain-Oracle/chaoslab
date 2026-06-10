'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { StatBlock } from '@/components/history/stat-block'
import { EmptyState } from '@/components/ui/empty-state'
import { A } from '@/components/ui/link'
import { PageFoot } from '@/components/ui/page-foot'
import { PageShell } from '@/components/ui/page-shell'
import { TopBar } from '@/components/ui/topbar'
import { AGENTS, AGGREGATE, HERO_RUN, HISTORY, agentById, fmtDate } from '@/lib/fixtures'
import type { HistoryRow as HistoryRowT } from '@/lib/types'

const FRAMEWORKS = ['All frameworks', 'EU AI Act', 'NIST AI RMF', 'HIPAA', 'SOC 2 + AI']

interface HistoryRowProps {
  run: HistoryRowT
}

function HistoryRow({ run }: HistoryRowProps) {
  const router = useRouter()
  const agent = agentById(run.agentId) ?? AGENTS[0]
  if (!agent) return null
  const open = () => {
    const path = run.id === HERO_RUN.id ? `/run/${run.id}` : `/report/${run.id}`
    router.push(path)
  }
  const stop = (e: React.MouseEvent) => e.stopPropagation()
  return (
    <tr className="clickable" onClick={open}>
      <td className="mono" style={{ fontSize: 11.5, whiteSpace: 'nowrap' }}>
        {run.id}
      </td>
      <td>
        <div style={{ fontSize: 13.5 }}>{agent.name}</div>
        <div className="mono muted" style={{ fontSize: 10.5 }}>
          {agent.url.replace('https://', '')}
        </div>
      </td>
      <td>
        <span className="tag">{run.framework}</span>
        {run.tier3 ? (
          <span className="mono muted" style={{ fontSize: 10, marginLeft: 6 }}>
            TIER 3 · NO CLUSTERING
          </span>
        ) : null}
      </td>
      <td className="mono num" style={{ whiteSpace: 'nowrap' }}>
        <span style={{ color: 'var(--pass)' }}>{run.pass}✓</span>
        <span className="muted"> / </span>
        <span style={{ color: run.fail ? 'var(--fail)' : 'var(--ink-3)' }}>{run.fail}✕</span>
      </td>
      <td className="mono muted" style={{ fontSize: 11, whiteSpace: 'nowrap' }}>
        {fmtDate(run.date)}
        {run.source === 'scheduled' ? (
          <span className="tag" style={{ marginLeft: 8, fontSize: 9.5 }}>
            scheduled
          </span>
        ) : null}
      </td>
      <td onClick={stop} style={{ whiteSpace: 'nowrap' }}>
        <A to={'report/' + run.id} className="span-link" style={{ marginRight: 12 }}>
          signed PDF
        </A>
        {run.recipe ? (
          <A to={'recipe/' + HERO_RUN.recipeId} className="span-link" style={{ marginRight: 12 }}>
            recipe
          </A>
        ) : null}
        {run.mr ? (
          <a className="span-link" href="#mr" onClick={(e) => e.preventDefault()}>
            MR ↗
          </a>
        ) : null}
      </td>
    </tr>
  )
}

export default function AuditsPage() {
  const [q, setQ] = useState('')
  const [fw, setFw] = useState('All frameworks')
  const rows = HISTORY.filter((r) => {
    const a = agentById(r.agentId)
    if (!a) return false
    const hit = (r.id + a.name + a.url + r.framework).toLowerCase().includes(q.toLowerCase())
    return hit && (fw === 'All frameworks' || r.framework === fw)
  })
  return (
    <PageShell label="audits">
      <div className="page-enter">
        <TopBar />
        <div className="shell" style={{ padding: '50px 40px 30px' }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'flex-end',
              gap: 20,
              marginBottom: 38,
            }}
          >
            <div style={{ flex: 1 }}>
              <div className="kicker" style={{ marginBottom: 12 }}>
                Audit registry · {AGGREGATE.quarter}
              </div>
              <h1 className="display" style={{ fontSize: 38 }}>
                Audit history.
              </h1>
            </div>
            <A to="new" className="btn ember">
              Run audit
            </A>
          </div>

          <div
            style={{
              display: 'flex',
              marginBottom: 38,
              borderTop: '1px solid var(--ink)',
              paddingTop: 4,
            }}
          >
            <StatBlock value={AGGREGATE.audits} label={'audits · ' + AGGREGATE.quarter} />
            <StatBlock value={AGGREGATE.findings} label="with findings" />
            <StatBlock value={AGGREGATE.hardened} label="hardened & re-passed" />
            <div style={{ flex: 1 }}></div>
            <div style={{ alignSelf: 'center', display: 'flex', gap: 10 }}>
              <input
                className="text-input"
                style={{ width: 240, padding: '10px 12px' }}
                placeholder="Search target, run, framework…"
                value={q}
                onChange={(e) => setQ(e.target.value)}
              />
              <select
                className="text-input"
                style={{ width: 170, padding: '10px 12px' }}
                value={fw}
                onChange={(e) => setFw(e.target.value)}
              >
                {FRAMEWORKS.map((f) => (
                  <option key={f}>{f}</option>
                ))}
              </select>
            </div>
          </div>

          {rows.length ? (
            <div className="ledger-wrap">
              <table className="ledger">
                <thead>
                  <tr>
                    <th>Audit run</th>
                    <th>Target agent</th>
                    <th>Framework</th>
                    <th>Verdicts</th>
                    <th>Filed</th>
                    <th>Artifacts</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r) => (
                    <HistoryRow key={r.id} run={r} />
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState
              kicker="NO MATCHES"
              title="No audits match that filter."
              body="Try a different search term or framework — or run a fresh audit against this target."
              action={
                <button
                  className="btn small ghost"
                  onClick={() => {
                    setQ('')
                    setFw('All frameworks')
                  }}
                >
                  Clear filters
                </button>
              }
            />
          )}
        </div>
        <PageFoot />
      </div>
    </PageShell>
  )
}
