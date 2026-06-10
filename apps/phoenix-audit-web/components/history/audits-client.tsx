'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { StatBlock } from '@/components/history/stat-block'
import { EmptyState } from '@/components/ui/empty-state'
import { A } from '@/components/ui/link'
import { PageFoot } from '@/components/ui/page-foot'
import { TopBar } from '@/components/ui/topbar'
import { historyRowDest } from '@/lib/cta'
import { fmtDate } from '@/lib/format'
import { registryStats } from '@/lib/registry-stats'
import type { AgentSpec, HistoryRow as HistoryRowData } from '@/lib/types'

const FRAMEWORKS = ['All frameworks', 'EU AI Act', 'NIST AI RMF', 'HIPAA', 'SOC 2 + AI']

function SampleChip() {
  return (
    <span
      className="tag"
      style={{ marginLeft: 8, fontSize: 9.5, opacity: 0.7 }}
      title="Seeded sample — a real audit of the demo target, visible to every account"
    >
      SAMPLE
    </span>
  )
}

interface RowProps {
  run: HistoryRowData
  agents: AgentSpec[]
}

function HistoryRow({ run, agents }: RowProps) {
  const router = useRouter()
  const agent = run.agentId ? agents.find((a) => a.id === run.agentId) : undefined
  const name = agent?.name ?? run.targetUrl ?? run.agentId
  const url = agent?.url ?? run.targetUrl ?? ''
  const open = () => router.push(historyRowDest(run))
  const stop = (e: React.MouseEvent) => e.stopPropagation()
  return (
    <tr className="clickable" onClick={open}>
      <td className="mono" style={{ fontSize: 11.5, whiteSpace: 'nowrap' }}>
        {run.id}
      </td>
      <td>
        <div style={{ fontSize: 13.5 }}>{name}</div>
        <div className="mono muted" style={{ fontSize: 10.5 }}>
          {url.replace('https://', '').replace('http://', '')}
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
        {(run.errored ?? 0) + (run.transportFailed ?? 0) > 0 ? (
          <span
            className="mono"
            style={{ color: 'var(--warn, #8a6d1a)', marginLeft: 6 }}
            title={`${run.errored ?? 0} rubric-errored · ${run.transportFailed ?? 0} transport-failed`}
          >
            {(run.errored ?? 0) + (run.transportFailed ?? 0)}⚠
          </span>
        ) : null}
      </td>
      <td className="mono muted" style={{ fontSize: 11, whiteSpace: 'nowrap' }}>
        {fmtDate(run.date)}
        {run.source === 'scheduled' ? (
          <span className="tag" style={{ marginLeft: 8, fontSize: 9.5 }}>
            scheduled
          </span>
        ) : null}
        {run.sample ? <SampleChip /> : null}
      </td>
      <td onClick={stop} style={{ whiteSpace: 'nowrap' }}>
        {run.reportAvailable ? (
          <A to={'report/' + run.id} className="span-link" style={{ marginRight: 12 }}>
            signed PDF
          </A>
        ) : (
          <span className="mono muted" style={{ fontSize: 10.5, marginRight: 12 }}>
            no report
          </span>
        )}
        {run.eventsAvailable ? (
          <A to={'run/' + run.id} className="span-link" style={{ marginRight: 12 }}>
            replay
          </A>
        ) : null}
        {run.recipe && run.reportAvailable ? (
          // The report page exposes the recipe.md download with a freshly
          // signed URL.
          <A to={'report/' + run.id} className="span-link" style={{ marginRight: 12 }}>
            recipe
          </A>
        ) : null}
        {run.mrUrl ? (
          // Only REAL MR urls render — a dead '#mr' anchor is a fake artifact.
          <a className="span-link" href={run.mrUrl} target="_blank" rel="noreferrer">
            MR ↗
          </a>
        ) : null}
      </td>
    </tr>
  )
}

export interface AuditsClientProps {
  rows: HistoryRowData[]
  agents: AgentSpec[]
  liveError: string | null
}

export function AuditsClient({ rows: allRows, agents, liveError }: AuditsClientProps) {
  const [q, setQ] = useState('')
  const [fw, setFw] = useState('All frameworks')
  // Seeded samples are REAL audits, visible to every account and labeled
  // (story-9.11) — a fresh register is never empty, and stats stay yours.
  const rows = allRows.filter((r) => {
    const agent = agents.find((a) => a.id === r.agentId)
    const haystack = (
      r.id +
      (agent?.name ?? '') +
      (agent?.url ?? r.targetUrl ?? '') +
      r.framework
    ).toLowerCase()
    return haystack.includes(q.toLowerCase()) && (fw === 'All frameworks' || r.framework === fw)
  })
  const stats = registryStats(allRows)
  return (
    <div className="page-enter">
      <TopBar />
      <div className="shell" style={{ padding: '50px 40px 30px' }}>
        <div style={{ display: 'flex', alignItems: 'flex-end', gap: 20, marginBottom: 38 }}>
          <div style={{ flex: 1 }}>
            <div className="kicker" style={{ marginBottom: 12 }}>
              Audit registry
            </div>
            <h1 className="display" style={{ fontSize: 38 }}>
              Audit history.
            </h1>
          </div>
          <A to="new" className="btn ember">
            Run audit
          </A>
        </div>

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
            }}
          >
            ⚠ LIVE REGISTRY UNAVAILABLE — nothing can be listed right now. ({liveError})
          </div>
        ) : null}

        <div
          style={{
            display: 'flex',
            marginBottom: 38,
            borderTop: '1px solid var(--ink)',
            paddingTop: 4,
          }}
        >
          <StatBlock value={stats.audits} label="audits — your account" />
          <StatBlock value={stats.withFindings} label="with findings" />
          <StatBlock value={stats.passedClean} label="passed clean" />
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
                  <HistoryRow key={r.id} run={r} agents={agents} />
                ))}
              </tbody>
            </table>
          </div>
        ) : q || fw !== 'All frameworks' ? (
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
        ) : (
          <EmptyState
            kicker="NO AUDITS YET"
            title="Your register is empty."
            body="Run your first audit to establish a signed baseline."
            action={
              <A to="new" className="btn small ember">
                Run your first audit
              </A>
            }
          />
        )}
      </div>
      <PageFoot />
    </div>
  )
}
