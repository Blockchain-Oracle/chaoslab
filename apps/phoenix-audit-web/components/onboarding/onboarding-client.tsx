'use client'

// Story-9.14 redesign — the wizard shell, ported from designer's Surface O
// (Phoenix Audit(2)/js/onboarding.jsx) to TSX with our real reducer +
// runFinish from S9.14. State-machine contract is UNCHANGED: the only
// addition is a `jumpTo` action used by the Docket TOC (jump-back to a
// visited step) and the Welcome step's "skip to the finish" affordance.
// All other behavior — single Finish PATCH, per-step skip semantics,
// server-gate redirect — stays byte-identical to S9.14.

import { useReducer, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Field } from '@/components/ui/field'
import { PageFoot } from '@/components/ui/page-foot'
import { TopBar } from '@/components/ui/topbar'
import { WIZARD_STEPS, initialWizardState, onboardingReducer, runFinish } from '@/lib/onboarding'
import type { WizardStep } from '@/lib/onboarding'
import { saveProfile, type ProfileDto } from '@/lib/profile'
import { AuditLoop } from './audit-loop'
import { CoverPreview } from './cover-preview'
import { DestCards } from './dest-cards'
import { Docket } from './docket'
import { FrameworkRows } from './framework-rows'
import { GitlabPromise } from './gitlab-promise'

interface OnboardingClientProps {
  /** The user's existing profile — seeds form fields so an interrupted
   *  wizard re-entry preserves prior values. */
  profile: ProfileDto | null
}

export function OnboardingClient({ profile }: OnboardingClientProps) {
  const router = useRouter()
  const [state, dispatch] = useReducer(onboardingReducer, initialWizardState(profile))
  // maxVisited lives in local state (not the reducer) — it's a UI
  // affordance, not part of the wizard's saved contract. Tracking the
  // farthest step lets the Docket TOC enable jump-back without letting
  // the user leapfrog ahead.
  const [maxVisited, setMaxVisited] = useState<WizardStep>('welcome')
  const [destination, setDestination] = useState<'new' | 'audits' | null>(null)

  const advanceMaxVisited = (next: WizardStep) => {
    const ni = WIZARD_STEPS.indexOf(next)
    const mi = WIZARD_STEPS.indexOf(maxVisited)
    if (ni > mi) setMaxVisited(next)
  }

  const onNext = () => {
    const idx = WIZARD_STEPS.indexOf(state.step)
    const next = WIZARD_STEPS[idx + 1]
    if (next) advanceMaxVisited(next)
    dispatch({ kind: 'next' })
  }
  const onSkip = () => {
    const idx = WIZARD_STEPS.indexOf(state.step)
    const next = WIZARD_STEPS[idx + 1]
    if (next) advanceMaxVisited(next)
    dispatch({ kind: 'skip' })
  }
  const onJumpToFinish = () => {
    advanceMaxVisited('cta')
    dispatch({ kind: 'jumpTo', step: 'cta' })
  }

  const finish = (dest: 'new' | 'audits') => {
    setDestination(dest)
    const path = dest === 'new' ? '/new' : '/audits'
    void runFinish({ state, destination: path, save: saveProfile, push: router.push, dispatch })
  }

  return (
    <div className="page-enter">
      <TopBar />
      <div className="shell" style={{ padding: '44px 40px 30px' }}>
        <div className="onb-grid">
          <aside className="onb-rail">
            <Docket
              step={state.step}
              maxVisited={maxVisited}
              orgName={state.orgName}
              framework={state.framework}
              destination={destination}
              skipped={state.skipped}
              onJump={(target) => dispatch({ kind: 'jumpTo', step: target })}
            />
            <div style={{ marginTop: 26 }}>
              <CoverPreview
                org={state.orgName}
                framework={state.framework}
                email={profile?.email ?? null}
              />
            </div>
          </aside>
          <main className="onb-step">
            <div className="onb-step-body">
              {state.step === 'welcome' ? <WelcomeStep email={profile?.email ?? null} /> : null}
              {state.step === 'org' ? (
                <OrgStep
                  value={state.orgName}
                  onChange={(v) => dispatch({ kind: 'setOrgName', value: v })}
                />
              ) : null}
              {state.step === 'framework' ? (
                <FrameworkStep
                  value={state.framework}
                  onChange={(v) => dispatch({ kind: 'setFramework', value: v })}
                />
              ) : null}
              {state.step === 'gitlab' ? <GitlabStep /> : null}
              {state.step === 'cta' ? (
                <CtaStep
                  submitting={state.submitting}
                  submitError={state.submitError}
                  choice={destination}
                  onPick={finish}
                />
              ) : null}
            </div>
            <Foot
              step={state.step}
              submitting={state.submitting}
              onBack={() => dispatch({ kind: 'back' })}
              onNext={onNext}
              onSkip={onSkip}
              onJumpToFinish={onJumpToFinish}
            />
          </main>
        </div>
      </div>
      <PageFoot />
    </div>
  )
}

function WelcomeStep({ email }: { email: string | null }) {
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

function OrgStep({ value, onChange }: { value: string; onChange: (v: string) => void }) {
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

function FrameworkStep({ value, onChange }: { value: string; onChange: (v: string) => void }) {
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

function GitlabStep() {
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

function CtaStep({
  submitting,
  submitError,
  choice,
  onPick,
}: {
  submitting: boolean
  submitError: string | null
  choice: 'new' | 'audits' | null
  onPick: (d: 'new' | 'audits') => void
}) {
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

function Foot({ step, submitting, onBack, onNext, onSkip, onJumpToFinish }: FootProps) {
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
