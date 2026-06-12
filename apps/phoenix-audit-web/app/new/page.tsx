'use client'

import { Suspense, useEffect, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { DatasetPicker } from '@/components/new-audit/dataset-picker'
import { DepthOption } from '@/components/new-audit/depth-option'
import { FrameworkPicker } from '@/components/new-audit/framework-picker'
import { OverridesBlock } from '@/components/new-audit/overrides-block'
import { runsPerFaultFromCap } from '@/lib/audit-budget'
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

// Wire shape from POST /api/agent/validate — flat union so the React state
// machine doesn't have to branch on nested optionals. Optional fields are
// present iff `valid === true`; `reason` iff `valid === false`.
type ValidateApiResponse = {
  valid: boolean
  mode?: 'v1' | 'permissive'
  name?: string
  protocol_version?: string
  version?: string
  skills_count?: number
  auth?: string
  transport?: string
  card_url?: string
  discovery_path?: string
  warnings?: string[]
  reason?: string
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
  // PR #131 — real preflight result. The wizard pings /api/agent/validate
  // on URL paste so users see "✓ AIScan — A2A v0.3.0 · 6 skills · no auth"
  // or "⚠ pre-v1 schema · basic audit only" or "✗ {reason}" before
  // committing to a 90s full audit. Replaces the prior fake setTimeout.
  const [validateResult, setValidateResult] = useState<ValidateApiResponse | null>(null)
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
    setValidateResult(null)
    if (!check.ok) {
      setPinging(false)
      return
    }
    setPinging(true)
    // Debounce so the validate fetch doesn't fire on every keystroke; the
    // 500ms window matches the placeholder cadence the prior fake check
    // used (one feedback per "typed and paused", not one per character).
    const controller = new AbortController()
    const id = window.setTimeout(async () => {
      try {
        const res = await fetch('/api/agent/validate', {
          method: 'POST',
          headers: { 'content-type': 'application/json' },
          body: JSON.stringify({ target_url: url.trim() }),
          signal: controller.signal,
        })
        if (controller.signal.aborted) return
        if (!res.ok) {
          // Treat upstream HTTP errors as "could not validate" — show the
          // status to the user instead of pretending the URL is fine. A
          // 401/403 here means the session expired (rare); 422 means URL
          // failed the SSRF guard.
          setValidateResult({
            valid: false,
            reason: `validate service returned ${res.status}`,
          })
          return
        }
        const body = (await res.json()) as ValidateApiResponse
        setValidateResult(body)
      } catch (err) {
        if (controller.signal.aborted) return
        setValidateResult({
          valid: false,
          reason: err instanceof Error ? err.message : 'network error',
        })
      } finally {
        if (!controller.signal.aborted) setPinging(false)
      }
    }, 500)
    return () => {
      controller.abort()
      window.clearTimeout(id)
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
      const runsPerFault = runsPerFaultFromCap(cap)
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

  // Hint reflects the validate-endpoint verdict — one of four states:
  // (1) still typing / format invalid → static helper copy
  // (2) checking → "Checking address…"
  // (3) valid v1 → ✓ name + protocol_version + skills_count + auth scheme
  //     valid permissive → ⚠ name + first warning ("pre-v1 schema; basic audit only")
  // (4) invalid → ✗ reason from the backend
  const hint = (() => {
    if (pinging) return 'Checking address…'
    if (!validateResult) {
      return 'HTTPS URL, or an A2A address for ADK-native agents.'
    }
    if (!validateResult.valid) {
      return `✗ ${validateResult.reason ?? 'could not validate this address'}`
    }
    const skills =
      validateResult.skills_count != null
        ? `${validateResult.skills_count} skill${validateResult.skills_count === 1 ? '' : 's'}`
        : null
    const auth =
      validateResult.auth && validateResult.auth !== 'none' ? validateResult.auth : 'no auth'
    const pv = validateResult.protocol_version ? `A2A v${validateResult.protocol_version}` : 'A2A'
    if (validateResult.mode === 'permissive') {
      const warning = validateResult.warnings?.[0] ?? 'pre-v1 schema; basic audit only'
      return `⚠ ${validateResult.name ?? 'agent'} — ${warning}`
    }
    // Auth-gated targets (x402 / bearer / oauth) — card probe reads the
    // well-known fine but the audit calls themselves get 401'd 30s in. Flag
    // amber + name the scheme so the user knows what's missing rather than
    // discovering it from a failed run. BYO-token flow is a future PR.
    if (validateResult.auth && validateResult.auth !== 'none') {
      return `⚠ ${validateResult.name ?? 'A2A agent'} — ${pv} · requires ${validateResult.auth} credentials (audit will fail without them)`
    }
    const parts = [pv, skills, auth].filter(Boolean).join(' · ')
    return `✓ ${validateResult.name ?? 'A2A agent'} — ${parts}`
  })()

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
          <p
            className="mono"
            style={{
              fontSize: 11,
              color: 'var(--ink-3)',
              marginTop: -28,
              marginBottom: 32,
              maxWidth: 560,
            }}
          >
            Works with public A2A v1.0 agents (and pre-v1 cards in basic mode). Gated targets —
            bearer / OAuth / API-key / x402 stablecoin paywalls — are detected and named, but the
            audit itself needs credentials we don&rsquo;t yet collect; BYO-token + funded-wallet
            flow is on the roadmap.
          </p>

          <SectionHead
            no="§2"
            title="Audit depth"
            right={
              <span className="tag">depth 2 applied to every run — selection coming soon</span>
            }
          />
          <div
            className="grid-2up"
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
              <div
                className="grid-2up"
                style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}
              >
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
