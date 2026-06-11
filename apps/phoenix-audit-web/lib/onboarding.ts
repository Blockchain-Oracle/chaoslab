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
  | { kind: 'setOrgName'; value: string }
  | { kind: 'setFramework'; value: string }
  | { kind: 'submitStart' }
  | { kind: 'submitError'; error: string }

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
    case 'setOrgName':
      return { ...state, orgName: action.value }
    case 'setFramework':
      return { ...state, framework: action.value }
    case 'submitStart':
      return { ...state, submitting: true, submitError: null }
    case 'submitError':
      return { ...state, submitting: false, submitError: action.error }
  }
}

/** The PATCH the wizard sends on Finish. Always sets `onboarded: true` — a
 *  user who saw the wizard and skipped every step is still ONBOARDED;
 *  reprompting them on next sign-in would be hostile. Skipped steps OMIT
 *  their field (exclude_unset on the server keeps the prior stored value). */
export function buildFinalPatch(state: WizardState): ProfileUpdate & { onboarded: true } {
  const patch: ProfileUpdate & { onboarded: true } = { onboarded: true }
  if (!state.skipped.has('org') && state.orgName.trim()) {
    patch.org_name = state.orgName.trim()
  }
  if (!state.skipped.has('framework') && state.framework) {
    patch.framework_default = state.framework
  }
  return patch
}
