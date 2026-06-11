// Onboarding wizard (story-9.14) — small focused tests on the gate predicate
// + the wizard's reducer. Source-level pins on the server gates mirror the
// audits-recipe-link.test.ts pattern: cheap to write, catches reverts.

import { describe, expect, it, vi } from 'vitest'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import {
  initialWizardState,
  needsOnboarding,
  onboardingReducer,
  runFinish,
  type SaveResult,
  type WizardAction,
} from '@/lib/onboarding'
import type { ProfileDto } from '@/lib/profile'

const baseProfile: ProfileDto = {
  uid: 'user-1',
  email: 'officer@example.com',
  org_name: null,
  framework_default: 'EU AI Act',
  hosting_pref: 'default',
  onboarded: false,
  created_at: null,
  updated_at: null,
}

describe('needsOnboarding predicate', () => {
  it('routes a fresh user (onboarded=false) into the wizard', () => {
    expect(needsOnboarding(baseProfile)).toBe(true)
  })

  it('leaves an onboarded user alone', () => {
    expect(needsOnboarding({ ...baseProfile, onboarded: true })).toBe(false)
  })

  it('does NOT trap users when the profile fetch failed — outage must not force-redirect', () => {
    // Critical contract: a transient registry outage cannot send every signed-in
    // user into the wizard. /audits would then disclose its OWN liveError, and
    // the wizard would render against a null profile (a worse failure mode).
    expect(needsOnboarding(null)).toBe(false)
  })
})

describe('onboarding wizard reducer', () => {
  it('starts on the welcome step with empty field state', () => {
    const s = initialWizardState(baseProfile)
    expect(s.step).toBe('welcome')
    expect(s.orgName).toBe('')
    expect(s.framework).toBe('EU AI Act')
    expect(s.submitting).toBe(false)
    expect(s.submitError).toBeNull()
  })

  it('seeds form fields from the existing profile (a mid-wizard re-entry keeps them)', () => {
    // The wizard only ever fires for onboarded=false, but a user who closes the
    // tab on step 3 and re-opens should not lose anything they entered earlier
    // and persisted. Profile fields seed the form.
    const s = initialWizardState({
      ...baseProfile,
      org_name: 'Meridian Mutual',
      framework_default: 'NIST AI RMF',
    })
    expect(s.orgName).toBe('Meridian Mutual')
    expect(s.framework).toBe('NIST AI RMF')
  })

  it('advances welcome → org → framework → gitlab → cta via NEXT', () => {
    let s = initialWizardState(baseProfile)
    s = onboardingReducer(s, { kind: 'next' })
    expect(s.step).toBe('org')
    s = onboardingReducer(s, { kind: 'next' })
    expect(s.step).toBe('framework')
    s = onboardingReducer(s, { kind: 'next' })
    expect(s.step).toBe('gitlab')
    s = onboardingReducer(s, { kind: 'next' })
    expect(s.step).toBe('cta')
  })

  it('SKIP advances the same way but flags the step as skipped (omitted from final PATCH)', () => {
    let s = initialWizardState(baseProfile)
    s = onboardingReducer(s, { kind: 'next' }) // welcome → org
    s = onboardingReducer(s, { kind: 'skip' }) // org → framework, mark skipped
    expect(s.step).toBe('framework')
    expect(s.skipped.has('org')).toBe(true)
  })

  it('BACK undoes the last step (and clears the skipped flag for the step we re-enter)', () => {
    let s = initialWizardState(baseProfile)
    s = onboardingReducer(s, { kind: 'next' }) // welcome → org
    s = onboardingReducer(s, { kind: 'skip' }) // org → framework
    s = onboardingReducer(s, { kind: 'back' }) // framework → org
    expect(s.step).toBe('org')
    expect(s.skipped.has('org')).toBe(false)
  })

  it('JUMP_TO routes to any step without disturbing existing skips (Docket TOC + "Skip to finish")', () => {
    let s = initialWizardState(baseProfile)
    s = onboardingReducer(s, { kind: 'skip' }) // welcome → org, welcome skipped
    s = onboardingReducer(s, { kind: 'jumpTo', step: 'cta' })
    expect(s.step).toBe('cta')
    // Existing skips persist — jumpTo doesn't enter or leave a step in the
    // "I made a choice" sense; it's pure navigation.
    expect(s.skipped.has('welcome')).toBe(true)

    s = onboardingReducer(s, { kind: 'jumpTo', step: 'org' })
    expect(s.step).toBe('org')
    expect(s.skipped.has('welcome')).toBe(true)
  })

  it('JUMP_TO with markSkipped flags every bypassed step (Welcome → Skip to finish)', () => {
    // Reviewer-flagged silent failure: a "Skip to the finish" click that
    // doesn't mark org/framework/gitlab as skipped lets buildFinalPatch
    // PATCH framework_default = 'EU AI Act' (the seed default) as if the
    // operator chose it. The regulator-facing report then cites a
    // framework the operator never picked. Mark them explicitly.
    let s = initialWizardState(baseProfile)
    s = onboardingReducer(s, {
      kind: 'jumpTo',
      step: 'cta',
      markSkipped: ['org', 'framework', 'gitlab'],
    })
    expect(s.step).toBe('cta')
    expect(s.skipped.has('org')).toBe(true)
    expect(s.skipped.has('framework')).toBe(true)
    expect(s.skipped.has('gitlab')).toBe(true)
    // welcome is not in markSkipped — and it's not the kind of step a
    // user "skips" anyway (no answer to omit) — so it's not flagged.
    expect(s.skipped.has('welcome')).toBe(false)
  })

  it('SET_ORG_NAME updates the org field', () => {
    let s = initialWizardState(baseProfile)
    s = onboardingReducer(s, { kind: 'setOrgName', value: 'Meridian Mutual' })
    expect(s.orgName).toBe('Meridian Mutual')
  })

  it('SET_FRAMEWORK updates the framework field', () => {
    let s = initialWizardState(baseProfile)
    s = onboardingReducer(s, { kind: 'setFramework', value: 'NIST AI RMF' })
    expect(s.framework).toBe('NIST AI RMF')
  })
})

describe('buildFinalPatch — what gets sent on Finish', () => {
  it('includes onboarded:true and all non-skipped fields', async () => {
    const { buildFinalPatch } = await import('@/lib/onboarding')
    let s = initialWizardState(baseProfile)
    s = onboardingReducer(s, { kind: 'setOrgName', value: 'Meridian Mutual' })
    s = onboardingReducer(s, { kind: 'setFramework', value: 'NIST AI RMF' })
    const patch = buildFinalPatch(s)
    expect(patch).toEqual({
      onboarded: true,
      org_name: 'Meridian Mutual',
      framework_default: 'NIST AI RMF',
    })
  })

  it('OMITS org_name when the user skipped it (instead of sending null/empty)', async () => {
    // The PATCH validator forbids empty framework_default and treats org_name=''
    // as "clear". Skip = "leave it as the profile currently stores it" — sending
    // an empty value would be a write where the user asked for no write.
    const { buildFinalPatch } = await import('@/lib/onboarding')
    let s = initialWizardState(baseProfile)
    s = onboardingReducer(s, { kind: 'next' }) // welcome → org
    s = onboardingReducer(s, { kind: 'skip' }) // org skipped
    s = onboardingReducer(s, { kind: 'setFramework', value: 'HIPAA' })
    const patch = buildFinalPatch(s)
    expect(patch).toEqual({ onboarded: true, framework_default: 'HIPAA' })
    expect(patch).not.toHaveProperty('org_name')
  })

  it('always sets onboarded:true even if every other step was skipped', async () => {
    // A user who clicks Skip on every step is still ONBOARDED — they were
    // shown the wizard, they made a choice (to keep defaults). Re-prompting
    // them on next sign-in would be hostile.
    const { buildFinalPatch } = await import('@/lib/onboarding')
    let s = initialWizardState(baseProfile)
    for (let i = 0; i < 4; i++) s = onboardingReducer(s, { kind: 'skip' })
    expect(buildFinalPatch(s)).toEqual({ onboarded: true })
  })

  it('skipped flag wins over a typed-then-backed-out org_name (rail and patch agree)', async () => {
    // Reviewer-flagged: a user who types an org name, then hits Back,
    // then Skip on the org step ends up with `state.orgName === '<typed>'`
    // AND `state.skipped` containing 'org'. buildFinalPatch must omit
    // org_name (skip = "no write"), and the Docket must render
    // 'skipped · Settings' (not the typed value) so the rail's editorial
    // promise matches what gets PATCHed.
    const { buildFinalPatch } = await import('@/lib/onboarding')
    let s = initialWizardState(baseProfile)
    s = onboardingReducer(s, { kind: 'next' }) // welcome → org
    s = onboardingReducer(s, { kind: 'setOrgName', value: 'Meridian Mutual' })
    s = onboardingReducer(s, { kind: 'skip' }) // org skipped, name still in state
    expect(s.orgName).toBe('Meridian Mutual')
    expect(s.skipped.has('org')).toBe(true)
    const patch = buildFinalPatch(s)
    expect(patch).not.toHaveProperty('org_name')
  })

  it('Welcome → Skip to finish via jumpTo+markSkipped emits ONLY {onboarded:true}', async () => {
    // Reviewer-flagged silent failure: prior to markSkipped, this same
    // sequence would PATCH framework_default = 'EU AI Act' (seed default)
    // as if the operator chose it. The cover sheet would then cite a
    // framework the operator never picked. Pin the fix.
    const { buildFinalPatch } = await import('@/lib/onboarding')
    let s = initialWizardState(baseProfile)
    s = onboardingReducer(s, {
      kind: 'jumpTo',
      step: 'cta',
      markSkipped: ['org', 'framework', 'gitlab'],
    })
    expect(buildFinalPatch(s)).toEqual({ onboarded: true })
  })
})

describe('reducer — submit actions + boundary clamps', () => {
  it('submitStart sets submitting and clears any prior submitError', () => {
    let s = initialWizardState(baseProfile)
    s = onboardingReducer(s, { kind: 'submitError', error: 'old' })
    s = onboardingReducer(s, { kind: 'submitStart' })
    expect(s.submitting).toBe(true)
    expect(s.submitError).toBeNull()
  })

  it('submitError clears submitting so the CTA re-enables for retry', () => {
    let s = initialWizardState(baseProfile)
    s = onboardingReducer(s, { kind: 'submitStart' })
    s = onboardingReducer(s, { kind: 'submitError', error: 'network down' })
    expect(s.submitting).toBe(false)
    expect(s.submitError).toBe('network down')
  })

  it('submitSuccess clears submitting and any prior error (future-proofs against layout changes)', () => {
    let s = initialWizardState(baseProfile)
    s = onboardingReducer(s, { kind: 'submitError', error: 'transient' })
    s = onboardingReducer(s, { kind: 'submitStart' })
    s = onboardingReducer(s, { kind: 'submitSuccess' })
    expect(s.submitting).toBe(false)
    expect(s.submitError).toBeNull()
  })

  it('back from the first step does NOT wrap to the last step', () => {
    const start = initialWizardState(baseProfile)
    const after = onboardingReducer(start, { kind: 'back' })
    expect(after.step).toBe('welcome')
  })

  it('next from the last step does NOT wrap to the first step', () => {
    let s = initialWizardState(baseProfile)
    for (let i = 0; i < 4; i++) s = onboardingReducer(s, { kind: 'next' })
    expect(s.step).toBe('cta')
    s = onboardingReducer(s, { kind: 'next' })
    expect(s.step).toBe('cta')
  })

  it('setOrgName / setFramework do NOT silently coerce step or other state', () => {
    let s = initialWizardState(baseProfile)
    s = onboardingReducer(s, { kind: 'next' })
    s = onboardingReducer(s, { kind: 'next' })
    expect(s.step).toBe('framework')
    s = onboardingReducer(s, { kind: 'setOrgName', value: 'X' })
    expect(s.step).toBe('framework')
    expect(s.framework).toBe('EU AI Act')
    s = onboardingReducer(s, { kind: 'setFramework', value: 'HIPAA' })
    expect(s.step).toBe('framework')
    expect(s.orgName).toBe('X')
  })
})

describe('buildFinalPatch — defends the framework default', () => {
  it('THROWS when framework step is visited but value is empty (no silent fallback)', async () => {
    const { buildFinalPatch } = await import('@/lib/onboarding')
    let s = initialWizardState(baseProfile)
    s = onboardingReducer(s, { kind: 'setFramework', value: '' })
    // The user didn't skip — they're on a state where they cleared framework.
    // Falling back to the stored profile default would silently disagree with
    // what /new shows them later (silent-failure-hunter Finding 5).
    expect(() => buildFinalPatch(s)).toThrow(/no value selected/)
  })

  it('does NOT throw when framework step is explicitly SKIPPED with empty value', async () => {
    const { buildFinalPatch } = await import('@/lib/onboarding')
    let s = initialWizardState(baseProfile)
    s = onboardingReducer(s, { kind: 'setFramework', value: '' })
    s = onboardingReducer(s, { kind: 'next' }) // welcome → org
    s = onboardingReducer(s, { kind: 'next' }) // org → framework
    s = onboardingReducer(s, { kind: 'skip' }) // framework skipped
    expect(() => buildFinalPatch(s)).not.toThrow()
  })
})

describe('runFinish — the wizard hot path that decides whether onboarding completes', () => {
  function harness(
    opts: {
      save: (p: object) => Promise<SaveResult>
      stateOverrides?: Partial<ReturnType<typeof initialWizardState>>
    } = {} as never,
  ) {
    const dispatched: WizardAction[] = []
    const pushed: string[] = []
    const baseState = { ...initialWizardState(baseProfile), ...(opts.stateOverrides ?? {}) }
    return {
      dispatched,
      pushed,
      run: (destination: '/new' | '/audits') =>
        runFinish({
          state: baseState,
          destination,
          save: opts.save ?? (async () => ({ profile: null, error: 'no save mock' })),
          push: (p: string) => pushed.push(p),
          dispatch: (a: WizardAction) => dispatched.push(a),
        }),
    }
  }

  it('SUCCESS path: save then dispatch submitStart/submitSuccess then push the destination', async () => {
    const save = vi.fn(async () => ({ profile: { onboarded: true }, error: null }))
    const h = harness({ save })
    const result = await h.run('/audits')
    expect(result).toBe('navigated')
    expect(save).toHaveBeenCalledOnce()
    expect(save).toHaveBeenCalledWith(expect.objectContaining({ onboarded: true }))
    expect(h.dispatched.map((a) => a.kind)).toEqual(['submitStart', 'submitSuccess'])
    expect(h.pushed).toEqual(['/audits'])
  })

  it('SUCCESS path: routes to /new when that destination was picked', async () => {
    const h = harness({ save: async () => ({ profile: { onboarded: true }, error: null }) })
    await h.run('/new')
    expect(h.pushed).toEqual(['/new'])
  })

  it('SAVE-FAILURE path: dispatches submitError with the server message and does NOT push', async () => {
    const h = harness({ save: async () => ({ profile: null, error: 'profile API answered 503' }) })
    const result = await h.run('/audits')
    expect(result).toBe('save-error')
    expect(h.pushed).toEqual([])
    const err = h.dispatched.find((a) => a.kind === 'submitError')
    expect(err && 'error' in err ? err.error : null).toBe('profile API answered 503')
  })

  it("SAVE-FAILURE path with null error: falls back to 'unknown error' (defense in depth)", async () => {
    const h = harness({ save: async () => ({ profile: null, error: null }) })
    await h.run('/audits')
    const err = h.dispatched.find((a) => a.kind === 'submitError')
    expect(err && 'error' in err ? err.error : null).toBe('unknown error')
  })

  it('IN-FLIGHT GUARD: a second call while submitting=true returns "guarded" without calling save', async () => {
    const save = vi.fn(async () => ({ profile: { onboarded: true }, error: null }))
    const h = harness({ save, stateOverrides: { submitting: true } })
    const result = await h.run('/audits')
    expect(result).toBe('guarded')
    expect(save).not.toHaveBeenCalled()
    expect(h.pushed).toEqual([])
    expect(h.dispatched).toEqual([])
  })

  it('PATCH-ERROR path: buildFinalPatch throws → dispatch submitError, save is never called', async () => {
    // Reach the throw via "framework step visited but value empty" — exactly
    // the silent-failure shape Finding 5 patched.
    let state = initialWizardState(baseProfile)
    state = onboardingReducer(state, { kind: 'setFramework', value: '' })
    const save = vi.fn(async () => ({ profile: { onboarded: true }, error: null }))
    const h = harness({ save, stateOverrides: state })
    const result = await h.run('/audits')
    expect(result).toBe('patch-error')
    expect(save).not.toHaveBeenCalled()
    expect(h.pushed).toEqual([])
    const err = h.dispatched.find((a) => a.kind === 'submitError')
    expect(err && 'error' in err ? err.error : null).toMatch(/no value selected/)
  })
})

describe('server-side gate plumbing (source-level pins)', () => {
  it('/audits redirects fresh users into the wizard', () => {
    const src = readFileSync(join(import.meta.dirname, '../app/audits/page.tsx'), 'utf-8')
    // Pinned shape: audits server fetches the profile and redirects when
    // needsOnboarding returns true. A revert that removes the gate would
    // silently send fresh users straight to the sample-loaded audits page.
    expect(src).toMatch(/needsOnboarding/)
    expect(src).toMatch(/redirect\(['"]\/onboarding['"]\)/)
  })

  it('/onboarding redirects already-onboarded users back to /audits', () => {
    const src = readFileSync(join(import.meta.dirname, '../app/onboarding/page.tsx'), 'utf-8')
    expect(src).toMatch(/redirect\(['"]\/audits['"]\)/)
  })
})
