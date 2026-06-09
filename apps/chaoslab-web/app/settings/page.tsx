'use client'

import { useEffect, useState } from 'react'
import { Field } from '@/components/ui/field'
import { PageFoot } from '@/components/ui/page-foot'
import { PageShell } from '@/components/ui/page-shell'
import { SectionHead } from '@/components/ui/section-head'
import { TopBar } from '@/components/ui/topbar'

const FRAMEWORKS = ['EU AI Act', 'NIST AI RMF', 'HIPAA', 'SOC 2 + AI', 'Custom']

type Hosting = 'default' | 'byo'

export default function SettingsPage() {
  const [hosting, setHosting] = useState<Hosting>('default')

  useEffect(() => {
    const v = (localStorage.getItem('pa_hosting') as Hosting | null) ?? 'default'
    setHosting(v)
  }, [])

  const setMode = (m: Hosting) => {
    setHosting(m)
    localStorage.setItem('pa_hosting', m)
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

          <SectionHead no="§1" title="Organization" />
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <Field label="Operator">
              <input
                className="text-input"
                defaultValue="Maya Okafor — Director of AI Governance"
              />
            </Field>
            <Field label="Organization">
              <input className="text-input" defaultValue="Meridian Mutual Health" />
            </Field>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <Field
              label="Erasure request address"
              hint="Printed on every signed report cover in default hosting mode."
            >
              <input className="text-input" defaultValue="erasure@phoenix-audit.example" />
            </Field>
            <Field label="Default regulatory framework">
              <select className="text-input" defaultValue="EU AI Act">
                {FRAMEWORKS.map((f) => (
                  <option key={f}>{f}</option>
                ))}
              </select>
            </Field>
          </div>

          <SectionHead no="§2" title="Signing & connections" />
          <Field
            label="Cloud KMS signing key"
            hint="Signed audit reports are signed against this key. Fingerprint SHA-256 4B:9E:F1:0A."
          >
            <input
              className="text-input"
              defaultValue="kms://meridian-compliance/keys/audit-signer"
            />
          </Field>
          <div
            className="card"
            style={{
              padding: '16px 20px',
              marginBottom: 26,
              display: 'flex',
              gap: 14,
              alignItems: 'center',
            }}
          >
            <div style={{ flex: 1 }}>
              <div className="field-label" style={{ marginBottom: 4 }}>
                GitLab connection
              </div>
              <div className="mono" style={{ fontSize: 12 }}>
                gitlab.example/meridian — <span style={{ color: 'var(--pass)' }}>● connected</span>{' '}
                · OAuth · merge requests enabled
              </div>
            </div>
            <button className="btn small ghost">Reconnect</button>
          </div>

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
            <div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                <Field label="Phoenix endpoint URL">
                  <input
                    className="text-input"
                    placeholder="https://phoenix.meridianmutual.internal"
                  />
                </Field>
                <Field label="Project name">
                  <input className="text-input" placeholder="agent-audits" />
                </Field>
              </div>
              <Field label="API key">
                <input className="text-input" type="password" placeholder="phx_…" />
              </Field>
            </div>
          ) : null}
          <button className="btn primary" style={{ marginTop: 6 }}>
            Save settings
          </button>
        </div>
        <PageFoot />
      </div>
    </PageShell>
  )
}
