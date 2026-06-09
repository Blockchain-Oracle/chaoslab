'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { EmptyState } from '@/components/ui/empty-state'
import { Field } from '@/components/ui/field'
import { PageFoot } from '@/components/ui/page-foot'
import { PageShell } from '@/components/ui/page-shell'
import { SectionHead } from '@/components/ui/section-head'
import { Toggle } from '@/components/ui/toggle'
import { TopBar } from '@/components/ui/topbar'
import { AGENTS, HISTORY, agentById, fmtDate } from '@/lib/fixtures'

const CADENCES = ['Hourly', 'Daily', 'Weekly', 'Custom cron']

export default function MonitoringPage() {
  const router = useRouter()
  const [agent, setAgent] = useState('agt_priorauth')
  const [cadence, setCadence] = useState('Daily')
  const [cron, setCron] = useState('0 6 * * *')
  const [windowH, setWindowH] = useState(24)
  const [email, setEmail] = useState(true)
  const [registry, setRegistry] = useState(true)
  const a = agentById(agent)
  const scheduled = HISTORY.filter((r) => r.source === 'scheduled')

  return (
    <PageShell label="monitoring">
      <div className="page-enter">
        <TopBar />
        <div className="shell" style={{ padding: '50px 40px 30px', maxWidth: 940 }}>
          <div className="kicker" style={{ marginBottom: 12 }}>
            Continuous monitoring
          </div>
          <h1 className="display" style={{ fontSize: 38, marginBottom: 10 }}>
            Catch the failures that really happened.
          </h1>
          <p className="muted" style={{ maxWidth: 620, marginBottom: 44, textWrap: 'pretty' }}>
            On a schedule, Phoenix Audit pulls the last N hours of the target agent&apos;s real
            production traces from its Phoenix project, runs the same judge over those real
            conversations — not synthetic tests — and files a signed report in your registry.
          </p>

          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: 44,
              alignItems: 'start',
            }}
          >
            <div>
              <SectionHead no="§1" title="Schedule" />
              <Field label="Target agent">
                <select
                  className="text-input"
                  value={agent}
                  onChange={(e) => setAgent(e.target.value)}
                >
                  {AGENTS.map((x) => (
                    <option key={x.id} value={x.id}>
                      {x.name} — {x.url.replace('https://', '')}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Cadence">
                <div style={{ display: 'flex', gap: 8 }}>
                  {CADENCES.map((c) => (
                    <button
                      key={c}
                      onClick={() => setCadence(c)}
                      className="tag"
                      style={{
                        cursor: 'pointer',
                        padding: '8px 14px',
                        background: cadence === c ? 'var(--ink)' : 'var(--paper-2)',
                        color: cadence === c ? 'var(--paper)' : 'var(--ink-2)',
                        borderColor: cadence === c ? 'var(--ink)' : 'var(--hairline-soft)',
                      }}
                    >
                      {c}
                    </button>
                  ))}
                </div>
              </Field>
              {cadence === 'Custom cron' ? (
                <Field label="Cron expression" hint="Evaluated in UTC by Cloud Scheduler.">
                  <input
                    className="text-input"
                    value={cron}
                    onChange={(e) => setCron(e.target.value)}
                  />
                </Field>
              ) : null}
              <Field label={'Trace window — last ' + windowH + ' hours of traffic'}>
                <input
                  type="range"
                  min={1}
                  max={168}
                  value={windowH}
                  onChange={(e) => setWindowH(Number(e.target.value))}
                  style={{ width: '100%', accentColor: 'var(--ember)' }}
                />
              </Field>
              <Field label="Deliver the signed report to">
                <div style={{ display: 'grid', gap: 10, paddingTop: 4 }}>
                  <label
                    style={{
                      display: 'flex',
                      gap: 12,
                      alignItems: 'center',
                      fontSize: 13.5,
                      cursor: 'pointer',
                    }}
                  >
                    <Toggle on={email} onChange={setEmail} label="email" /> Email summary —
                    maya.okafor@meridianmutual.example
                  </label>
                  <label
                    style={{
                      display: 'flex',
                      gap: 12,
                      alignItems: 'center',
                      fontSize: 13.5,
                      cursor: 'pointer',
                    }}
                  >
                    <Toggle on={registry} onChange={setRegistry} label="registry" /> File to audit
                    registry automatically
                  </label>
                </div>
              </Field>
              <button className="btn ember" style={{ marginTop: 8 }}>
                Enable monitoring — {a?.name ?? ''}
              </button>
            </div>

            <div>
              <SectionHead
                no="§2"
                title="Audits produced by this schedule"
                right={
                  <span className="mono muted" style={{ fontSize: 10.5 }}>
                    {scheduled.length} filed
                  </span>
                }
              />
              {scheduled.length ? (
                <table className="ledger">
                  <thead>
                    <tr>
                      <th>Run</th>
                      <th>Verdicts</th>
                      <th>Filed</th>
                    </tr>
                  </thead>
                  <tbody>
                    {scheduled.map((r) => (
                      <tr
                        key={r.id}
                        className="clickable"
                        onClick={() => router.push(`/report/${r.id}`)}
                      >
                        <td className="mono" style={{ fontSize: 11.5 }}>
                          {r.id}
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
                    ))}
                  </tbody>
                </table>
              ) : (
                <EmptyState
                  kicker="NOTHING SCHEDULED YET"
                  title="No scheduled audits filed."
                  body="Enable monitoring and a fresh signed audit will appear here on every tick — without you touching the product."
                />
              )}
              <p className="mono muted" style={{ fontSize: 10.5, marginTop: 16, lineHeight: 1.8 }}>
                EU AI ACT ARTICLE 72 — POST-MARKET MONITORING: scheduled signed audits satisfy the
                continuous-evidence expectation for high-risk systems.
              </p>
            </div>
          </div>
        </div>
        <PageFoot />
      </div>
    </PageShell>
  )
}
