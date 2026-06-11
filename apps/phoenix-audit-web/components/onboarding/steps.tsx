// Story-9.14 redesign — step bodies + foot bar for the wizard, broken
// out of `onboarding-client.tsx` so the shell stays under the 400-line
// guard with room to grow. Each step is a thin presentational
// component over the reducer state; the shell owns the dispatch.

import { Field } from '@/components/ui/field'
import type { WizardStep } from '@/lib/onboarding'
import { AuditLoop } from './audit-loop'
import { DestCards } from './dest-cards'
import { FrameworkRows } from './framework-rows'
import { GitlabPromise } from './gitlab-promise'

export function WelcomeStep({ email }: { email: string | null }) {
  return (
    <div className="onb-welcome">
      <div>
        <div className="kicker" style={{ marginBottom: 14 }}>
          Welcome
        </div>
        <h1 className="display" style={{ fontSize: 33, marginBottom: 16 }}>
          Phoenix Audit, the AI agent that <em>audits other AI agents.</em>
        </h1>
        <p
          style={{
            fontSize: 14,
            color: 'var(--ink-2)',
            lineHeight: 1.65,
            marginBottom: 18,
          }}
        >
          A 90-second adversarial battery probes your agent. An LLM judge reads the Phoenix traces.
          Failures collapse into root-cause clusters — and the whole file ends as a signed audit
          report.
        </p>
        {email ? (
          <div style={{ display: 'flex', gap: 9, alignItems: 'center', marginBottom: 18 }}>
            <span className="avatar-dot" aria-hidden="true">
              {email.charAt(0).toUpperCase()}
            </span>
            <span
              className="mono"
              style={{ fontSize: 10, letterSpacing: '0.05em', color: 'var(--ink-2)' }}
            >
              SIGNED IN AS {email.toUpperCase()}
            </span>
          </div>
        ) : null}
        <p
          className="serif"
          style={{
            fontSize: 16.5,
            fontStyle: 'italic',
            color: 'var(--ember-deep)',
            lineHeight: 1.5,
          }}
        >
          Four short questions, then you&rsquo;re looking at your first signed report. Each step is
          skippable.
        </p>
      </div>
      <AuditLoop />
    </div>
  )
}

export function OrgStep({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  return (
    <div>
      <div className="kicker" style={{ marginBottom: 14 }}>
        Your organization · question 1 of 4
      </div>
      <h1 className="display" style={{ fontSize: 33, marginBottom: 14 }}>
        Who&rsquo;s filing this?
      </h1>
      <p className="muted" style={{ marginBottom: 32, maxWidth: 480 }}>
        The name goes on the signed report cover and the Annex IV documentation — watch it land on
        your cover sheet as you type. Skipping is fine; set it any time in Settings.
      </p>
      <div style={{ maxWidth: 440 }}>
        <Field
          label="Organization name"
          hint="No verification needed — this is the name regulators will read."
        >
          <input
            className="text-input"
            placeholder="e.g. Meridian Mutual Health"
            value={value}
            onChange={(e) => onChange(e.target.value)}
            autoFocus
            spellCheck="false"
          />
        </Field>
      </div>
    </div>
  )
}

export function FrameworkStep({
  value,
  onChange,
}: {
  value: string
  onChange: (v: string) => void
}) {
  return (
    <div>
      <div className="kicker" style={{ marginBottom: 14 }}>
        Default framework · question 2 of 4
      </div>
      <h1 className="display" style={{ fontSize: 33, marginBottom: 14 }}>
        Which control set anchors your reports?
      </h1>
      <p className="muted" style={{ marginBottom: 28, maxWidth: 520 }}>
        This framework&rsquo;s articles are cited on every report cover and in the
        regulatory-mapping appendix. You can override it per audit when starting a run.
      </p>
      <FrameworkRows value={value} onChange={onChange} />
    </div>
  )
}

export function GitlabStep() {
  return (
    <div>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 14,
          marginBottom: 14,
          flexWrap: 'wrap',
        }}
      >
        <div className="kicker">GitLab connection · question 3 of 4</div>
        <span className="stamp neutral" style={{ fontSize: 9, whiteSpace: 'nowrap' }}>
          Coming next · Wave C
        </span>
      </div>
      <h1 className="display" style={{ fontSize: 33, marginBottom: 14 }}>
        File hardening recipes straight into your repo.
      </h1>
      <p className="muted" style={{ marginBottom: 26, maxWidth: 540 }}>
        This one isn&rsquo;t live yet — there&rsquo;s nothing to connect today. But the discipline
        is already fixed, so we&rsquo;re putting it on the record now rather than surprising you
        later:
      </p>
      <GitlabPromise />
    </div>
  )
}

interface CtaStepProps {
  submitting: boolean
  submitError: string | null
  choice: 'new' | 'audits' | null
  onPick: (d: 'new' | 'audits') => void
}

export function CtaStep({ submitting, submitError, choice, onPick }: CtaStepProps) {
  return (
    <div>
      <div className="kicker" style={{ marginBottom: 14 }}>
        You&rsquo;re set · question 4 of 4
      </div>
      <h1 className="display" style={{ fontSize: 33, marginBottom: 14 }}>
        Where do you want to land?
      </h1>
      <p className="muted" style={{ marginBottom: 24, maxWidth: 520 }}>
        Choosing a destination finishes setup — your answers are filed once, and skipped questions
        keep their defaults.
      </p>
      {submitError ? (
        <div className="auth-notice error" role="alert" style={{ marginBottom: 18 }}>
          That didn&rsquo;t save — <strong>you&rsquo;re not onboarded yet.</strong> Nothing you
          answered was lost: pick a destination again and we&rsquo;ll send the same request.
        </div>
      ) : null}
      <DestCards
        submitting={submitting}
        submitError={submitError}
        choice={choice}
        onPick={onPick}
      />
      <div
        className="mono"
        style={{
          fontSize: 9.5,
          letterSpacing: '0.12em',
          color: 'var(--ink-3)',
          marginTop: 16,
        }}
      >
        FILED ONCE, ON FINISH · PATCH /profile · onboarded: true
      </div>
    </div>
  )
}

interface FootProps {
  step: WizardStep
  submitting: boolean
  onBack: () => void
  onNext: () => void
  onSkip: () => void
  onJumpToFinish: () => void
}

export function Foot({ step, submitting, onBack, onNext, onSkip, onJumpToFinish }: FootProps) {
  const skipCopy: Partial<Record<WizardStep, string>> = {
    org: 'Skip — set it in Settings later',
    framework: 'Skip — keep EU AI Act',
  }
  return (
    <div className="onb-foot">
      {step !== 'welcome' ? (
        <button className="btn small ghost" onClick={onBack} disabled={submitting}>
          ← Back
        </button>
      ) : null}
      {step === 'welcome' ? (
        <button className="btn ember" onClick={onNext}>
          Begin — question 1 →
        </button>
      ) : null}
      <span style={{ flex: 1 }} />
      {step === 'welcome' ? (
        <button className="onb-skip" onClick={onJumpToFinish}>
          In a hurry? Skip to the finish
        </button>
      ) : null}
      {skipCopy[step] ? (
        <button className="onb-skip" onClick={onSkip}>
          {skipCopy[step]}
        </button>
      ) : null}
      {step === 'gitlab' ? (
        <span className="mono muted" style={{ fontSize: 10, letterSpacing: '0.1em' }}>
          NOTHING TO ANSWER HERE
        </span>
      ) : null}
      {step === 'org' || step === 'framework' ? (
        <button className="btn ember small" style={{ padding: '10px 20px' }} onClick={onNext}>
          Next →
        </button>
      ) : null}
      {step === 'gitlab' ? (
        <button className="btn ember small" style={{ padding: '10px 20px' }} onClick={onNext}>
          Got it — last question →
        </button>
      ) : null}
      {step === 'cta' ? (
        <span className="mono muted" style={{ fontSize: 10, letterSpacing: '0.1em' }}>
          PICKING A CARD IS THE FINISH
        </span>
      ) : null}
    </div>
  )
}
