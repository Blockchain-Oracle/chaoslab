'use client'

// Settings tells the TRUTH (story-9.10 → 9.12): the real signed-in account,
// preferences persisted server-side on the users/{uid} profile (not
// localStorage), and honest states for everything not yet user-configurable.
// Every save shows its real outcome — saving / saved / failed.

import { useEffect, useRef, useState } from 'react'
import Link from 'next/link'
import { onAuthStateChanged, type User } from 'firebase/auth'
import { getFirebaseAuth } from '@/lib/auth/client'
import { fetchProfile, saveProfile, type HostingPref, type ProfileUpdate } from '@/lib/profile'
import { Field } from '@/components/ui/field'
import { GitLabConnectCard } from '@/components/integrations/gitlab-connect-card'
import { PageFoot } from '@/components/ui/page-foot'
import { PageShell } from '@/components/ui/page-shell'
import { SectionHead } from '@/components/ui/section-head'
import { TopBar } from '@/components/ui/topbar'

const FRAMEWORKS = ['EU AI Act', 'NIST AI RMF', 'HIPAA', 'SOC 2 + AI']

type SaveState =
  | { kind: 'loading' }
  | { kind: 'idle' }
  | { kind: 'saving' }
  | { kind: 'saved' }
  | { kind: 'error'; message: string }

export default function SettingsPage() {
  const [hosting, setHosting] = useState<HostingPref>('default')
  const [framework, setFramework] = useState('EU AI Act')
  const [user, setUser] = useState<User | null>(null)
  const [save, setSave] = useState<SaveState>({ kind: 'loading' })

  useEffect(() => {
    let cancelled = false
    void fetchProfile().then(({ profile, error }) => {
      if (cancelled) return
      if (profile) {
        setHosting(profile.hosting_pref)
        setFramework(profile.framework_default)
        setSave({ kind: 'idle' })
      } else {
        setSave({ kind: 'error', message: `could not load your saved settings — ${error}` })
      }
    })
    const off = onAuthStateChanged(getFirebaseAuth(), setUser)
    return () => {
      cancelled = true
      off()
    }
  }, [])

  const saveSeq = useRef(0)
  const persist = (updates: ProfileUpdate) => {
    const seq = ++saveSeq.current
    setSave({ kind: 'saving' })
    void saveProfile(updates).then(({ profile, error }) => {
      // Two quick clicks can resolve out of order — only the LATEST save may
      // re-render state, or an older response would snap controls backwards.
      if (seq !== saveSeq.current) return
      if (profile) {
        // Server truth wins — render what was actually stored.
        setHosting(profile.hosting_pref)
        setFramework(profile.framework_default)
        setSave({ kind: 'saved' })
      } else {
        setSave({ kind: 'error', message: `save failed — ${error}` })
      }
    })
  }

  const setMode = (m: HostingPref) => {
    setHosting(m)
    persist({ hosting_pref: m })
  }
  const setFw = (f: string) => {
    setFramework(f)
    persist({ framework_default: f })
  }

  return (
    <PageShell label="settings">
      <div className="page-enter">
        <TopBar />
        <div className="shell" style={{ padding: '50px 40px 30px', maxWidth: 820 }}>
          <div className="kicker" style={{ marginBottom: 12 }}>
            Account
          </div>
          <h1 className="display" style={{ fontSize: 38, marginBottom: 44 }}>
            Settings.
          </h1>

          <SectionHead
            no="§1"
            title="Account"
            right={
              <span className="mono muted" style={{ fontSize: 10.5 }}>
                need help?{' '}
                <Link href="/docs" className="span-link">
                  read the docs →
                </Link>
              </span>
            }
          />
          <div
            className="grid-2up"
            style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}
          >
            <Field label="Signed in as">
              <input
                className="text-input"
                value={user?.email ?? '…'}
                readOnly
                aria-readonly="true"
              />
            </Field>
            <Field
              label="Default regulatory framework"
              hint="Preselected when you start a new audit."
            >
              <select
                className="text-input"
                value={framework}
                onChange={(e) => setFw(e.target.value)}
              >
                {FRAMEWORKS.map((f) => (
                  <option key={f}>{f}</option>
                ))}
              </select>
            </Field>
          </div>

          <SectionHead no="§2" title="Signing & connections" />
          <div className="card" style={{ padding: '16px 20px', marginBottom: 16 }}>
            <div className="field-label" style={{ marginBottom: 4 }}>
              Cloud KMS signing
            </div>
            <div className="mono" style={{ fontSize: 12 }}>
              <span style={{ color: 'var(--pass)' }}>● managed by the service</span> — every signed
              report carries its Ed25519 verification fingerprint and signature sidecar.
            </div>
          </div>
          <GitLabConnectCard />

          <SectionHead
            no="§3"
            title="Phoenix hosting mode"
            right={
              <span className="mono muted" style={{ fontSize: 10.5 }}>
                drives the report&apos;s residency paragraph
              </span>
            }
          />
          <div
            className="grid-2up"
            style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: 16,
              marginBottom: 26,
            }}
            role="radiogroup"
          >
            <div
              className={'opt-card ' + (hosting === 'default' ? 'selected' : '')}
              onClick={() => setMode('default')}
              role="radio"
              aria-checked={hosting === 'default'}
              tabIndex={0}
            >
              <div
                className="mono"
                style={{
                  fontSize: 10.5,
                  letterSpacing: '0.14em',
                  color: 'var(--ember-deep)',
                  marginBottom: 8,
                }}
              >
                PHOENIX AUDIT–HOSTED · DEFAULT
              </div>
              <div className="serif" style={{ fontSize: 17, marginBottom: 7 }}>
                Zero friction
              </div>
              <p
                style={{
                  fontSize: 13,
                  color: 'var(--ink-2)',
                  lineHeight: 1.6,
                }}
              >
                Trace data is held briefly on Phoenix Audit infrastructure and cryptographically
                erased 24 hours after the signed report. GDPR Article 28 data processor terms apply.
              </p>
            </div>
            <div
              className={'opt-card ' + (hosting === 'byo' ? 'selected' : '')}
              onClick={() => setMode('byo')}
              role="radio"
              aria-checked={hosting === 'byo'}
              tabIndex={0}
            >
              <div
                className="mono"
                style={{
                  fontSize: 10.5,
                  letterSpacing: '0.14em',
                  color: 'var(--ember-deep)',
                  marginBottom: 8,
                }}
              >
                CUSTOMER-HOSTED · BYO PHOENIX
              </div>
              <div className="serif" style={{ fontSize: 17, marginBottom: 7 }}>
                Your tenancy only
              </div>
              <p
                style={{
                  fontSize: 13,
                  color: 'var(--ink-2)',
                  lineHeight: 1.6,
                }}
              >
                For regulated estates. You provide your own Phoenix endpoint, API key and project —
                audit trace data never leaves your tenancy. Phoenix Audit holds no copy.
              </p>
            </div>
          </div>
          {hosting === 'byo' ? (
            <p className="mono muted" style={{ fontSize: 11.5, lineHeight: 1.7 }}>
              ◌ BYO endpoint configuration is provisioned with your deployment — the service reads
              PHOENIX_COLLECTOR_ENDPOINT and PHOENIX_API_KEY from its environment. In-app
              configuration is not available yet.
            </p>
          ) : null}
          <p
            className="mono"
            style={{
              fontSize: 10.5,
              marginTop: 18,
              color: save.kind === 'error' ? 'var(--fail)' : 'var(--ink-2)',
            }}
            role="status"
          >
            {save.kind === 'loading' && 'Loading your saved settings…'}
            {save.kind === 'idle' &&
              'Preferences save to your account as you change them — there is nothing else to submit.'}
            {save.kind === 'saving' && 'Saving…'}
            {save.kind === 'saved' && '✓ Saved to your account.'}
            {save.kind === 'error' && `✕ ${save.message}`}
          </p>
        </div>
        <PageFoot />
      </div>
    </PageShell>
  )
}
