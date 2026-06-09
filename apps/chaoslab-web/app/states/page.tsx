import { StateCard } from '@/components/states/state-card'
import { EmptyState } from '@/components/ui/empty-state'
import { Field } from '@/components/ui/field'
import { A } from '@/components/ui/link'
import { PageFoot } from '@/components/ui/page-foot'
import { PageShell } from '@/components/ui/page-shell'
import { Citation } from '@/components/ui/stamps'
import { TopBar } from '@/components/ui/topbar'

export default function StatesPage() {
  return (
    <PageShell label="states">
      <div className="page-enter">
        <TopBar />
        <div className="shell" style={{ padding: '50px 40px 30px' }}>
          <div className="kicker" style={{ marginBottom: 12 }}>
            Surface K — for the build
          </div>
          <h1 className="display" style={{ fontSize: 38, marginBottom: 8 }}>
            Error, empty &amp; blocked states.
          </h1>
          <p className="muted" style={{ marginBottom: 40, maxWidth: 560 }}>
            Every surface ships with these. The live audit must never feel frozen; errors always
            name the next action.
          </p>

          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(2, 1fr)',
              gap: '28px 32px',
            }}
          >
            <StateCard label="Empty — first-run audit history">
              <EmptyState
                kicker="NO AUDITS YET"
                title="You haven't run any audits yet."
                body="Your first signed audit report is 90 seconds away."
                action={
                  <A to="new" className="btn small ember">
                    Start your first audit
                  </A>
                }
              />
            </StateCard>

            <StateCard label="Error — target agent unreachable (wizard)">
              <Field
                label="Target agent address"
                error="Probe ping failed — the target agent did not respond."
              >
                <input
                  className="text-input invalid"
                  defaultValue="https://agents.meridianmutual.example/voice-intake"
                  readOnly
                />
              </Field>
              <button className="btn small ghost">Retry probe</button>
            </StateCard>

            <StateCard label="Error — audit crashed mid-run (SSE error event)">
              <div
                className="mono"
                style={{ fontSize: 11, color: 'var(--fail)', marginBottom: 10 }}
              >
                {'error {"run_id":"run_4b22…","detail":"target returned HTTP 503 during probe 04"}'}
              </div>
              <p style={{ fontSize: 13, color: 'var(--ink-2)', marginBottom: 14 }}>
                The audit stopped at probe 04 of 06. Nothing was signed or filed. Completed probes
                are preserved in the Phoenix trace.
              </p>
              <div style={{ display: 'flex', gap: 10 }}>
                <button className="btn small primary">Re-run audit</button>
                <button className="btn small ghost">View partial trace ↗</button>
              </div>
            </StateCard>

            <StateCard label="Blocked — signing key not configured">
              <div
                style={{
                  display: 'flex',
                  gap: 12,
                  alignItems: 'center',
                  marginBottom: 12,
                }}
              >
                <span className="stamp warn">Blocked</span>
                <span style={{ fontSize: 13.5 }}>
                  The audit ran, but the report can&apos;t be signed.
                </span>
              </div>
              <p style={{ fontSize: 13, color: 'var(--ink-2)', marginBottom: 14 }}>
                No Cloud KMS signing key is configured for Meridian Mutual Health. The unsigned
                draft is held for 24 hours.
              </p>
              <A to="settings" className="btn small primary">
                Configure signing key
              </A>
            </StateCard>

            <StateCard label="Blocked — audit cap reached">
              <div
                style={{
                  display: 'flex',
                  gap: 12,
                  alignItems: 'center',
                  marginBottom: 12,
                }}
              >
                <span className="stamp warn">Cap reached</span>
                <span style={{ fontSize: 13.5 }}>50 of 50 audits used this cycle.</span>
              </div>
              <p style={{ fontSize: 13, color: 'var(--ink-2)' }}>
                Scheduled monitoring continues; manual runs resume on 1 July. Contact your account
                owner to raise the cap.
              </p>
            </StateCard>

            <StateCard label="Error — GitLab connection broken (recipe view)">
              <p style={{ fontSize: 13, color: 'var(--ink-2)', marginBottom: 12 }}>
                The hardening recipe was generated, but the merge request could not be opened — the
                GitLab OAuth grant has expired.
              </p>
              <div style={{ display: 'flex', gap: 10 }}>
                <A to="settings" className="btn small primary">
                  Reconnect GitLab
                </A>
                <button className="btn small ghost">Download markdown instead</button>
              </div>
            </StateCard>

            <StateCard label="Marker — fallback-emitted finding">
              <div
                style={{
                  display: 'flex',
                  gap: 10,
                  alignItems: 'center',
                  marginBottom: 10,
                  flexWrap: 'wrap',
                }}
              >
                <span style={{ fontSize: 13.5 }}>Poisoned patient-record context</span>
                <Citation>OWASP LLM01</Citation>
                <span className="stamp fail">Fail</span>
              </div>
              <span className="fallback-flag">
                ◌ FALLBACK PATH — judge call rate-limited; synthetic verdict, flagged in signed
                report metadata
              </span>
              <p style={{ fontSize: 12.5, color: 'var(--ink-3)', marginTop: 10 }}>
                Fallback findings stay visibly distinct everywhere they appear — the regulator must
                be able to tell them apart.
              </p>
            </StateCard>

            <StateCard label="Loading — the 90-second window (Surface C)">
              <p style={{ fontSize: 13, color: 'var(--ink-2)', lineHeight: 1.65 }}>
                The chamber never shows a spinner. The pipeline visualization pulses the active
                agent, the SSE feed ticks, and probe rows land one by one — the screen is alive
                between every phase change.
              </p>
              <A
                to="replay"
                className="span-link"
                style={{ fontSize: 12, marginTop: 10, display: 'inline-block' }}
              >
                See it in the replay →
              </A>
            </StateCard>
          </div>
        </div>
        <PageFoot />
      </div>
    </PageShell>
  )
}
