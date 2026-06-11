'use client'

import { Suspense, useEffect, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { DatasetPicker } from '@/components/new-audit/dataset-picker'
import { DepthOption } from '@/components/new-audit/depth-option'
import { FrameworkPicker } from '@/components/new-audit/framework-picker'
import { OverridesBlock } from '@/components/new-audit/overrides-block'
import { fetchProfile } from '@/lib/profile'
import { Field } from '@/components/ui/field'
import { A } from '@/components/ui/link'
import { PageFoot } from '@/components/ui/page-foot'
import { PageShell } from '@/components/ui/page-shell'
import { SectionHead } from '@/components/ui/section-head'
import { TopBar } from '@/components/ui/topbar'

function probeCheck(url: string): { ok: true } | { ok: false; error: string } {
  if (!url.trim()) return { ok: false, error: 'Enter a target agent address.' }
  if (!/^https:\/\/|^a2a:\/\/|^http:\/\/(localhost|127\.)/i.test(url.trim()))
    return {
      ok: false,
      error: 'Must be a reachable HTTPS URL, or an A2A address for ADK-native agents.',
    }
  return { ok: true }
}

export default function NewAuditPage() {
  // useSearchParams demands a Suspense boundary in the App Router.
  return (
    <Suspense>
      <NewAuditForm />
    </Suspense>
  )
}

function NewAuditForm() {
  const router = useRouter()
  const params = useSearchParams()
  // Agent CTAs prefill the wizard (/new?agent=<id>&url=<url>) — the wizard
  // stays the single confirm surface; runs stay associated to the agent.
  // /datasets CTAs prefill the dataset picker (/new?dataset=<slug>).
  const agentId = params.get('agent')
  const datasetParam = params.get('dataset')
  const [hosting, setHosting] = useState<'default' | 'byo'>('default')
  const [url, setUrl] = useState(() => params.get('url') ?? '')
  const [datasetId, setDatasetId] = useState<string | null>(datasetParam)
  const [touched, setTouched] = useState(false)
  const [pinging, setPinging] = useState(false)
  const [pinged, setPinged] = useState(false)
  const [depth, setDepth] = useState<1 | 2>(2)
  const [framework, setFramework] = useState('EU AI Act')
  const [showOverrides, setShowOverrides] = useState(false)
  const [skipCats, setSkipCats] = useState<string[]>([])
  const [cap, setCap] = useState(6)
  const [judge, setJudge] = useState('gemini-3.5-flash (default)')
  const [starting, setStarting] = useState(false)
  const [startError, setStartError] = useState<string | null>(null)
  const [prefsNotice, setPrefsNotice] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    // The settings page persists these on the server-side profile — honor
    // them here so the preference is real, not decorative (story-9.10/9.12).
    void fetchProfile().then(({ profile, error }) => {
      if (cancelled) return
      if (profile) {
        setHosting(profile.hosting_pref)
        setFramework(profile.framework_default)
      } else {
        // The framework framing flows into the regulator-facing report — a
        // silently-substituted default must be disclosed, not implied saved.
        setPrefsNotice(`could not load your saved preferences (${error}) — using defaults`)
      }
    })
    return () => {
      cancelled = true
    }
  }, [])

  const check = probeCheck(url)

  useEffect(() => {
    setPinged(false)
    if (!check.ok) return
    setPinging(true)
    const id = setTimeout(() => {
      setPinging(false)
      setPinged(true)
    }, 900)
    return () => {
      clearTimeout(id)
      setPinging(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [url])

  const run = async () => {
    setTouched(true)
    if (!check.ok || starting) return
    if (typeof window !== 'undefined') {
      localStorage.removeItem('pa_audit_t_live')
    }
    setStarting(true)
    setStartError(null)
    try {
      // REAL audit — POST /run through the same-origin proxy, then follow the
      // returned run id into the live chamber. No fixture short-circuit.
      // "Cap number of tests" is the TOTAL probe budget; the backend takes
      // attacks-per-fault-class (4 classes), so total ≈ 4 × runs_per_fault.
      const runsPerFault = Math.min(20, Math.max(1, Math.round(cap / 4)))
      const res = await fetch('/api/agent/run', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({
          target_url: url.trim(),
          agent_id: agentId ?? undefined,
          dataset_id: datasetId ?? undefined,
          source: 'manual',
          runs_per_fault: runsPerFault,
        }),
      })
      if (!res.ok) throw new Error(`the audit service answered ${res.status}`)
      const body = (await res.json()) as { run_id?: string }
      if (!body.run_id) throw new Error('the audit service returned no run id')
      router.push(`/run/${body.run_id}`)
    } catch (err) {
      setStartError(err instanceof Error ? err.message : String(err))
      setStarting(false)
    }
  }

  const hint = pinging
    ? 'Checking address…'
    : pinged
      ? '✓ Address format OK — reachability and framework are verified by the first audit probe.'
      : 'HTTPS URL, or an A2A address for ADK-native agents.'

  return (
    <PageShell label="new-audit">
      <div className="page-enter">
        <TopBar />
        <div className="shell" style={{ padding: '54px 40px 70px', maxWidth: 880 }}>
          <div className="kicker" style={{ marginBottom: 14 }}>
            New audit run
          </div>
          <h1 className="display" style={{ fontSize: 40, marginBottom: 10 }}>
            Start a new audit.
          </h1>
          <p
            className="muted"
            style={{ marginBottom: prefsNotice ? 12 : 44, maxWidth: 560, textWrap: 'pretty' }}
          >
            Four decisions, one button. The audit takes roughly 90 seconds and ends with a signed
            audit report you can file.
          </p>
          {prefsNotice ? (
            <p
              className="mono"
              style={{ fontSize: 11, color: 'var(--fail)', marginBottom: 32 }}
              role="status"
            >
              ◌ {prefsNotice}
            </p>
          ) : null}

          <SectionHead no="§1" title="Target agent" />
          <Field
            label="Target agent address"
            error={touched && !check.ok ? check.error : null}
            hint={hint}
          >
            <input
              className={'text-input ' + (touched && !check.ok ? 'invalid' : '')}
              placeholder="https://agents.yourcompany.com/agent — or a2a://…"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              onBlur={() => setTouched(true)}
              spellCheck="false"
            />
          </Field>

          <SectionHead
            no="§2"
            title="Audit depth"
            right={
              <span className="tag">depth 2 applied to every run — selection coming soon</span>
            }
          />
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: 16,
              marginBottom: 40,
            }}
            role="radiogroup"
          >
            <DepthOption
              selected={depth === 1}
              onSelect={() => setDepth(1)}
              sub="DEPTH 1 · BLACK-BOX"
              title="Zero setup"
              body="The audit sees only what crosses the wire. Verdicts are correct, but root-cause clustering can't see inside the target agent — findings are reported per test."
            />
            <DepthOption
              selected={depth === 2}
              onSelect={() => setDepth(2)}
              sub="DEPTH 2 · INSTRUMENTED"
              title="Full root-cause clustering"
              body="Add a 3-line snippet to your agent's startup and Phoenix Audit can read its internal trace tree — failures collapse into root cause clusters with span-level evidence."
              link="How do I add the snippet? ↗"
            />
          </div>

          <FrameworkPicker framework={framework} setFramework={setFramework} />

          <DatasetPicker
            value={datasetId}
            onChange={setDatasetId}
            initiallyOpen={Boolean(datasetParam)}
          />

          {hosting === 'byo' ? (
            <div>
              <SectionHead
                no="§3b"
                title="Your Phoenix instance"
                right={<span className="tag">BYO hosting mode</span>}
              />
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                <Field label="Phoenix endpoint URL">
                  <input
                    className="text-input"
                    placeholder="https://phoenix.yourcompany.internal"
                  />
                </Field>
                <Field label="Project name">
                  <input className="text-input" placeholder="prior-auth-audits" />
                </Field>
              </div>
              <Field label="API key">
                <input className="text-input" type="password" placeholder="phx_…" />
              </Field>
              <p className="muted" style={{ fontSize: 12.5, marginTop: -10, marginBottom: 36 }}>
                Audit trace data never leaves your tenancy. Phoenix Audit holds no copy after the
                run completes.
              </p>
            </div>
          ) : (
            <div
              className="mono muted"
              style={{
                fontSize: 11,
                letterSpacing: '0.04em',
                margin: '-18px 0 38px',
                display: 'flex',
                gap: 8,
                alignItems: 'baseline',
              }}
            >
              <span style={{ color: 'var(--ember-deep)' }}>◆</span>
              Phoenix Audit–hosted · trace data cryptographically erased 24 h after the signed
              report (GDPR Art. 28) · change in{' '}
              <A to="settings" style={{ color: 'var(--ember-deep)' }}>
                Settings
              </A>
            </div>
          )}

          <OverridesBlock
            showOverrides={showOverrides}
            setShowOverrides={setShowOverrides}
            skipCats={skipCats}
            setSkipCats={setSkipCats}
            cap={cap}
            setCap={setCap}
            judge={judge}
            setJudge={setJudge}
          />

          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 20,
              borderTop: '1px solid var(--ink)',
              paddingTop: 24,
            }}
          >
            <button
              className="btn ember"
              style={{ padding: '16px 34px', fontSize: 13 }}
              onClick={run}
              disabled={starting}
            >
              {starting ? 'Starting audit…' : 'Run audit'}
            </button>
            <span className="muted" style={{ fontSize: 12.5, maxWidth: 380, lineHeight: 1.55 }}>
              ~90 seconds · audit-mode headers sent on every probe · ends with a signed audit
              report.
            </span>
            {startError ? (
              <span className="mono" style={{ fontSize: 11.5, color: 'var(--fail)' }}>
                ✕ Could not start the audit — {startError}
              </span>
            ) : null}
          </div>
        </div>
        <PageFoot />
      </div>
    </PageShell>
  )
}
