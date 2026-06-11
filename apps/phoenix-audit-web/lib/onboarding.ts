// Onboarding wizard primitives (story-9.14): the gate predicate every server
// page consults to decide "send this user to the wizard?", plus the pure
// reducer + final-patch shape the client component drives. Pure functions
// only — no React, no fetch — so the gates and the state machine are
// unit-testable without DOM or mocks.

import type { ProfileDto, ProfileUpdate } from './profile'

/** Returns true when the user should be routed to the wizard.
 *
 *  A NULL profile (registry unreachable, parse failure) returns FALSE — we
 *  never trap users in a forced wizard on a transient outage. The page they
 *  meant to visit discloses the outage via its own liveError surface. */
export function needsOnboarding(profile: ProfileDto | null): boolean {
  return profile !== null && profile.onboarded === false
}

export type WizardStep = 'welcome' | 'org' | 'framework' | 'gitlab' | 'cta'

export const WIZARD_STEPS: ReadonlyArray<WizardStep> = [
  'welcome',
  'org',
  'framework',
  'gitlab',
  'cta',
]

export interface WizardState {
  step: WizardStep
  orgName: string
  framework: string
  /** Steps the user chose to SKIP. Skipped fields are omitted from the
   *  final PATCH (per the profile API's exclude_unset semantics from
   *  story-9.12 — omitted ≠ cleared). */
  skipped: Set<WizardStep>
  submitting: boolean
  submitError: string | null
}

export function initialWizardState(profile: ProfileDto | null): WizardState {
  return {
    step: 'welcome',
    orgName: profile?.org_name ?? '',
    framework: profile?.framework_default ?? 'EU AI Act',
    skipped: new Set(),
    submitting: false,
    submitError: null,
  }
}

export type WizardAction =
  | { kind: 'next' }
  | { kind: 'back' }
  | { kind: 'skip' }
  /** Navigation — used by the Docket TOC (jump-back to a visited
   *  step) and by Welcome's "In a hurry? Skip to the finish" affordance.
   *
   *  By default does NOT touch the skipped set; an existing skip remains
   *  a skip. Welcome's "Skip to the finish" passes `markSkipped` for the
   *  steps it's bypassing so unanswered defaults aren't silently PATCHed
   *  as if the operator chose them (regulator-facing fields must
   *  distinguish "answered with X" from "skipped — kept default X"). */
  | { kind: 'jumpTo'; step: WizardStep; markSkipped?: ReadonlyArray<WizardStep> }
  | { kind: 'setOrgName'; value: string }
  | { kind: 'setFramework'; value: string }
  | { kind: 'submitStart' }
  | { kind: 'submitError'; error: string }
  | { kind: 'submitSuccess' }

function neighborStep(step: WizardStep, delta: 1 | -1): WizardStep {
  const idx = WIZARD_STEPS.indexOf(step)
  const next = idx + delta
  if (next < 0 || next >= WIZARD_STEPS.length) return step
  return WIZARD_STEPS[next]!
}

export function onboardingReducer(state: WizardState, action: WizardAction): WizardState {
  switch (action.kind) {
    case 'next':
      return { ...state, step: neighborStep(state.step, 1) }
    case 'back': {
      const back = neighborStep(state.step, -1)
      // Re-entering a previously skipped step clears the skip — the user is
      // about to make a real choice.
      const skipped = new Set(state.skipped)
      skipped.delete(back)
      return { ...state, step: back, skipped }
    }
    case 'skip': {
      const skipped = new Set(state.skipped)
      skipped.add(state.step)
      return { ...state, step: neighborStep(state.step, 1), skipped }
    }
    case 'jumpTo': {
      // Asymmetric with `back`: jumpTo is revisit/review (TOC) or batch-
      // skip (Welcome → Finish), not a single-step correction. Existing
      // skips persist; new ones are added when `markSkipped` is passed.
      if (!action.markSkipped || action.markSkipped.length === 0) {
        return { ...state, step: action.step }
      }
      const skipped = new Set(state.skipped)
      for (const s of action.markSkipped) skipped.add(s)
      return { ...state, step: action.step, skipped }
    }
    case 'setOrgName':
      return { ...state, orgName: action.value }
    case 'setFramework':
      return { ...state, framework: action.value }
    case 'submitStart':
      // Clears any prior submitError so a retry doesn't render with the
      // previous error still showing alongside the in-flight spinner.
      return { ...state, submitting: true, submitError: null }
    case 'submitError':
      // Must clear submitting:true so the CTA buttons re-enable for retry.
      return { ...state, submitting: false, submitError: action.error }
    case 'submitSuccess':
      // Today this is masked by router.push unmounting the component; the
      // action exists so a future layout change (router.replace in a shared
      // layout) doesn't leave the wizard with `submitting=true` forever.
      return { ...state, submitting: false, submitError: null }
  }
}

/** The PATCH the wizard sends on Finish. Always sets `onboarded: true` — a
 *  user who saw the wizard and skipped every step is still ONBOARDED;
 *  reprompting them on next sign-in would be hostile. Skipped steps OMIT
 *  their field (exclude_unset on the server keeps the prior stored value).
 *
 *  Throws when a non-skipped framework value is empty — conflating "user
 *  explicitly skipped" with "value is bad" would silently fall back to the
 *  EU AI Act default and Maya wouldn't know why /new doesn't match what
 *  she picked. */
export function buildFinalPatch(state: WizardState): ProfileUpdate & { onboarded: true } {
  const patch: ProfileUpdate & { onboarded: true } = { onboarded: true }
  if (!state.skipped.has('org') && state.orgName.trim()) {
    patch.org_name = state.orgName.trim()
  }
  if (!state.skipped.has('framework')) {
    if (!state.framework) {
      const msg = 'framework step was visited but no value selected — pick one or skip the step'
      throw new Error(msg)
    }
    patch.framework_default = state.framework
  }
  return patch
}

/** SaveProfile-shaped result. Local type avoids dragging `lib/profile` into
 *  every test that wants to drive `runFinish` with a fake. */
export interface SaveResult {
  profile: { onboarded?: boolean } | null
  error: string | null
}

/** The wizard's Finish hot path — extracted from `OnboardingClient` so the
 *  decision tree (in-flight guard, build-patch errors, save success vs save
 *  failure, navigation) is testable WITHOUT DOM. Dispatch + save + push are
 *  passed as deps; the function returns the outcome the caller can ignore
 *  (it's invoked for side effects). */
export async function runFinish(args: {
  state: WizardState
  destination: '/new' | '/audits'
  save: (patch: ProfileUpdate & { onboarded: true }) => Promise<SaveResult>
  push: (path: string) => void
  dispatch: (action: WizardAction) => void
}): Promise<'guarded' | 'patch-error' | 'save-error' | 'navigated'> {
  // Imperative re-entry guard — a rapid keyboard race (tab+Enter on two
  // destination cards) can fire two onClicks before React re-renders with
  // submitting=true, sending two PATCHes.
  if (args.state.submitting) return 'guarded'
  let patch: ProfileUpdate & { onboarded: true }
  try {
    patch = buildFinalPatch(args.state)
  } catch (err) {
    args.dispatch({
      kind: 'submitError',
      error: err instanceof Error ? err.message : String(err),
    })
    return 'patch-error'
  }
  args.dispatch({ kind: 'submitStart' })
  const { profile, error } = await args.save(patch)
  if (!profile) {
    args.dispatch({ kind: 'submitError', error: error ?? 'unknown error' })
    return 'save-error'
  }
  args.dispatch({ kind: 'submitSuccess' })
  args.push(args.destination)
  return 'navigated'
}
