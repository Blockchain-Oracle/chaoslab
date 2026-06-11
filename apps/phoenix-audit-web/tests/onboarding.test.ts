// Onboarding wizard (story-9.14) — small focused tests on the gate predicate
// + the wizard's reducer. Source-level pins on the server gates mirror the
// audits-recipe-link.test.ts pattern: cheap to write, catches reverts.

import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { needsOnboarding, onboardingReducer, initialWizardState } from '@/lib/onboarding'
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
