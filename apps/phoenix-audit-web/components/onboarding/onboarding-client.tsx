'use client'

// Story-9.14 redesign — the wizard shell, ported from designer's Surface O
// (Phoenix Audit(2)/js/onboarding.jsx) to TSX with our real reducer +
// runFinish from S9.14. State-machine contract is UNCHANGED: the only
// addition is a `jumpTo` action used by the Docket TOC (jump-back to a
// visited step) and the Welcome step's "skip to the finish" affordance.
// All other behavior — single Finish PATCH, per-step skip semantics,
// server-gate redirect — stays byte-identical to S9.14.

import { useEffect, useReducer, useState } from 'react'
import { useRouter } from 'next/navigation'
import { PageFoot } from '@/components/ui/page-foot'
import { TopBar } from '@/components/ui/topbar'
import { WIZARD_STEPS, initialWizardState, onboardingReducer, runFinish } from '@/lib/onboarding'
import type { WizardStep } from '@/lib/onboarding'
import { saveProfile, type ProfileDto } from '@/lib/profile'
import { CoverPreview } from './cover-preview'
import { Docket } from './docket'
import { CtaStep, Foot, FrameworkStep, GitlabStep, OrgStep, WelcomeStep } from './steps'

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

  // Reviewer-flagged silent-failure: destination was set BEFORE runFinish
  // and stayed set on submitError, so the Docket rendered the failed
  // choice as if it were filed. Clear it the moment the reducer signals
  // an error — retry picks a fresh choice with no stale rail label.
  useEffect(() => {
    if (state.submitError) setDestination(null)
  }, [state.submitError])

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
    // Mark every bypassed step explicitly skipped so buildFinalPatch
    // omits their seed defaults instead of silently writing them as if
    // they were the operator's choice. See reducer comment on jumpTo.
    dispatch({
      kind: 'jumpTo',
      step: 'cta',
      markSkipped: ['org', 'framework', 'gitlab'],
    })
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
              // Docket rows are revisit-only — the row's `disabled` gate
              // is `rowIdx <= visitedIdx`, so the user can never jump
              // FORWARD past unvisited steps from the TOC. No markSkipped
              // needed; if a future affordance lets the operator jump
              // forward, it MUST pass markSkipped for the bypassed
              // steps (see onJumpToFinish + reducer comment).
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
