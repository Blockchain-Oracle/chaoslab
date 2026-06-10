'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { EmptyState } from '@/components/ui/empty-state'
import { Field } from '@/components/ui/field'
import { PageFoot } from '@/components/ui/page-foot'
import { SectionHead } from '@/components/ui/section-head'
import { Toggle } from '@/components/ui/toggle'
import { TopBar } from '@/components/ui/topbar'
import type { ScheduleDto } from '@/lib/api'
import { fmtDate } from '@/lib/format'
import type { MergedAgent, MergedRun } from '@/lib/sample-merge'

const CADENCES: { label: string; value: 'hourly' | 'daily' | null }[] = [
  { label: 'Hourly', value: 'hourly' },
  { label: 'Daily', value: 'daily' },
  { label: 'Weekly', value: null },
  { label: 'Custom cron', value: null },
]

export interface MonitoringClientProps {
  agents: MergedAgent[]
  schedules: ScheduleDto[]
  scheduledRuns: MergedRun[]
  liveError: string | null
}

export function MonitoringClient({
  agents,
  schedules,
  scheduledRuns,
  liveError,
}: MonitoringClientProps) {
  const router = useRouter()
  const realAgents = agents.filter((a) => !a.sample)
  const selectable = realAgents.length > 0 ? realAgents : agents
  const [agentId, setAgentId] = useState(selectable[0]?.id ?? '')
  const [cadence, setCadence] = useState<'hourly' | 'daily'>('daily')
  const [email, setEmail] = useState(false)
  const [recipient, setRecipient] = useState('')
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const selected = agents.find((a) => a.id === agentId)

  const enable = async () => {
    if (!selected || saving) return
    setSaving(true)
    setSaveError(null)
    try {
      const res = await fetch('/api/agent/schedules', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({
          agent_id: selected.id,
          target_url: selected.url,
          cadence,
          deliver_email: email && recipient.length > 0,
          email_recipient: email && recipient.length > 0 ? recipient : null,
        }),
      })
      if (!res.ok) throw new Error(`the audit service answered ${res.status}`)
      router.refresh()
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : String(err))
    } finally {
      setSaving(false)
    }
  }

  const toggleSchedule = async (schedule: ScheduleDto) => {
    setSaveError(null)
    try {
      const res = await fetch(`/api/agent/schedules/${schedule.schedule_id}`, {
        method: 'PATCH',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ enabled: !schedule.enabled }),
      })
      if (!res.ok) throw new Error(`the audit service answered ${res.status}`)
      router.refresh()
    } catch (err) {
      // A silently-snapping-back toggle would tell a compliance officer that
      // monitoring is off when it isn't — surface the failure.
      setSaveError(err instanceof Error ? err.message : String(err))
    }
  }

  return (
    <div className="page-enter">
      <TopBar />
      <div className="shell" style={{ padding: '50px 40px 30px', maxWidth: 940 }}>
        <div className="kicker" style={{ marginBottom: 12 }}>
          Continuous monitoring
        </div>
        <h1 className="display" style={{ fontSize: 38, marginBottom: 10 }}>
          Audit on a schedule, file every report.
        </h1>
        <p className="muted" style={{ maxWidth: 620, marginBottom: 24, textWrap: 'pretty' }}>
          On every tick, Phoenix Audit re-runs the full adversarial battery against the target agent
          and files a fresh signed report in your registry — continuous evidence, hands off.
          (Judging real production traces on the same schedule is on the roadmap.)
        </p>
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
            ⚠ LIVE REGISTRY UNAVAILABLE — showing sample data only. ({liveError})
          </div>
        ) : null}

        <div
          style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 44, alignItems: 'start' }}
        >
          <div>
            <SectionHead no="§1" title="Schedule" />
            <Field label="Target agent">
              <select
                className="text-input"
                value={agentId}
                onChange={(e) => setAgentId(e.target.value)}
              >
                {selectable.map((x) => (
                  <option key={x.id} value={x.id}>
                    {x.name} — {x.url.replace('https://', '').replace('http://', '')}
                    {x.sample ? ' (sample)' : ''}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Cadence">
              <div style={{ display: 'flex', gap: 8 }}>
                {CADENCES.map((c) => (
                  <button
                    key={c.label}
                    onClick={() => c.value && setCadence(c.value)}
                    disabled={!c.value}
                    title={c.value ? undefined : 'Coming after the hackathon'}
                    className="tag"
                    style={{
                      cursor: c.value ? 'pointer' : 'not-allowed',
                      opacity: c.value ? 1 : 0.45,
                      padding: '8px 14px',
                      background: cadence === c.value ? 'var(--ink)' : 'var(--paper-2)',
                      color: cadence === c.value ? 'var(--paper)' : 'var(--ink-2)',
                      borderColor: cadence === c.value ? 'var(--ink)' : 'var(--hairline-soft)',
                    }}
                  >
                    {c.label}
                  </button>
                ))}
              </div>
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
                  <Toggle on={email} onChange={setEmail} label="email" /> Email summary
                </label>
                {email ? (
                  <input
                    className="text-input"
                    placeholder="compliance@yourcompany.com"
                    value={recipient}
                    onChange={(e) => setRecipient(e.target.value)}
                  />
                ) : null}
                <span className="mono muted" style={{ fontSize: 10.5 }}>
                  Reports always file to the audit registry.
                </span>
              </div>
            </Field>
            <button
              className="btn ember"
              style={{ marginTop: 8 }}
              onClick={enable}
              disabled={saving || !selected}
            >
              {saving ? 'Enabling…' : `Enable monitoring — ${selected?.name ?? ''}`}
            </button>
            {saveError ? (
              <div className="mono" style={{ fontSize: 11.5, color: 'var(--fail)', marginTop: 10 }}>
                ✕ Could not enable monitoring — {saveError}
              </div>
            ) : null}

            {schedules.length ? (
              <div style={{ marginTop: 34 }}>
                <SectionHead no="§1b" title="Active schedules" />
                {schedules.map((s) => (
                  <div
                    key={s.schedule_id}
                    className="leader-row"
                    style={{ padding: '7px 0', display: 'flex', gap: 10, alignItems: 'center' }}
                  >
                    <span className="mono" style={{ fontSize: 11 }}>
                      {s.schedule_id}
                    </span>
                    <span className="tag">{s.cadence}</span>
                    <span style={{ flex: 1 }} />
                    <span className="mono muted" style={{ fontSize: 10.5 }}>
                      next {fmtDate(s.next_fire_at)}
                    </span>
                    <Toggle
                      on={s.enabled}
                      onChange={() => void toggleSchedule(s)}
                      label={`schedule ${s.schedule_id}`}
                    />
                  </div>
                ))}
              </div>
            ) : null}
          </div>

          <div>
            <SectionHead
              no="§2"
              title="Audits produced by monitoring"
              right={
                <span className="mono muted" style={{ fontSize: 10.5 }}>
                  {scheduledRuns.length} filed
                </span>
              }
            />
            {scheduledRuns.length ? (
              <table className="ledger">
                <thead>
                  <tr>
                    <th>Run</th>
                    <th>Verdicts</th>
                    <th>Filed</th>
                  </tr>
                </thead>
                <tbody>
                  {scheduledRuns.map((r) => (
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
                        <span style={{ color: r.fail ? 'var(--fail)' : 'var(--ink-3)' }}>
                          {r.fail}✕
                        </span>
                      </td>
                      <td className="mono muted" style={{ fontSize: 11 }}>
                        {fmtDate(r.date)}
                        {r.sample ? (
                          <span
                            className="tag"
                            style={{ marginLeft: 8, fontSize: 9.5, opacity: 0.7 }}
                          >
                            SAMPLE
                          </span>
                        ) : null}
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
  )
}
