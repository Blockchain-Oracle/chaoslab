'use client'

// The wizard state machine + dispatch (story-9.14). Visual scaffolding is
// PLACEHOLDER pending docs/assets.md Surface-O deliveries from the designer
// — the structure (5 steps, skip/back/next semantics, single Finish PATCH,
// submit-error disclosure) is locked; the visual answer is the designer's.

import { useReducer } from 'react'
import { useRouter } from 'next/navigation'
import { PageFoot } from '@/components/ui/page-foot'
import { TopBar } from '@/components/ui/topbar'
import {
  WIZARD_STEPS,
  buildFinalPatch,
  initialWizardState,
  onboardingReducer,
} from '@/lib/onboarding'
import { saveProfile, type ProfileDto } from '@/lib/profile'
import { StepCta } from './steps/cta'
import { StepFramework } from './steps/framework'
import { StepGitlab } from './steps/gitlab'
import { StepOrg } from './steps/org'
import { StepWelcome } from './steps/welcome'

interface OnboardingClientProps {
  /** The user's existing profile — seeds form fields so an interrupted
   *  wizard re-entry preserves prior values. */
  profile: ProfileDto | null
}

export function OnboardingClient({ profile }: OnboardingClientProps) {
  const router = useRouter()
  const [state, dispatch] = useReducer(onboardingReducer, initialWizardState(profile))

  const stepIdx = WIZARD_STEPS.indexOf(state.step)
  const isFirst = stepIdx === 0
  const isLast = state.step === 'cta'

  const finish = async (destination: '/new' | '/audits') => {
    dispatch({ kind: 'submitStart' })
    const { profile: saved, error } = await saveProfile(buildFinalPatch(state))
    if (!saved) {
      dispatch({ kind: 'submitError', error: error ?? 'unknown error' })
      return
    }
    router.push(destination)
  }

  return (
    <div className="page-enter">
      <TopBar />
      <div className="shell" style={{ padding: '54px 40px 30px', maxWidth: 760 }}>
        {/* Progress affordance — PLACEHOLDER per assets.md O-1; the
            designer will replace this step strip. */}
        <div
          className="mono muted"
          style={{
            fontSize: 10.5,
            letterSpacing: '0.12em',
            marginBottom: 28,
            display: 'flex',
            gap: 10,
            flexWrap: 'wrap',
          }}
        >
          {WIZARD_STEPS.map((s, i) => (
            <span
              key={s}
              style={{
                color: i === stepIdx ? 'var(--ember-deep)' : 'var(--ink-3)',
                textTransform: 'uppercase',
              }}
            >
              {String(i + 1).padStart(2, '0')} · {s.toUpperCase()}
              {i < WIZARD_STEPS.length - 1 ? ' →' : ''}
            </span>
          ))}
        </div>

        <div style={{ minHeight: 360, marginBottom: 32 }}>
          {state.step === 'welcome' ? <StepWelcome email={profile?.email ?? null} /> : null}
          {state.step === 'org' ? (
            <StepOrg
              value={state.orgName}
              onChange={(v) => dispatch({ kind: 'setOrgName', value: v })}
            />
          ) : null}
          {state.step === 'framework' ? (
            <StepFramework
              value={state.framework}
              onChange={(v) => dispatch({ kind: 'setFramework', value: v })}
            />
          ) : null}
          {state.step === 'gitlab' ? <StepGitlab /> : null}
          {state.step === 'cta' ? (
            <StepCta
              submitting={state.submitting}
              submitError={state.submitError}
              onFinish={finish}
            />
          ) : null}
        </div>

        {/* Footer actions. CTA step has its own destination buttons —
            footer collapses there to just Back so the user can correct
            an earlier step if they made a mistake. */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 14,
            borderTop: '1px solid var(--hairline)',
            paddingTop: 22,
            flexWrap: 'wrap',
          }}
        >
          <button
            type="button"
            className="btn small ghost"
            onClick={() => dispatch({ kind: 'back' })}
            disabled={isFirst || state.submitting}
          >
            ← Back
          </button>
          <span style={{ flex: 1 }}></span>
          {!isLast ? (
            <>
              {state.step === 'welcome' ? null : (
                <button
                  type="button"
                  className="btn small ghost"
                  onClick={() => dispatch({ kind: 'skip' })}
                >
                  Skip this step
                </button>
              )}
              <button
                type="button"
                className="btn ember"
                onClick={() => dispatch({ kind: 'next' })}
              >
                {state.step === 'welcome' ? 'Get started →' : 'Next →'}
              </button>
            </>
          ) : null}
        </div>
      </div>
      <PageFoot />
    </div>
  )
}
