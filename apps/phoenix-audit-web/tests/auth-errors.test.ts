// Firebase error codes become plain sentences — never codes, never a silent
// no-op (designer's Surface L copy is the contract).

import { describe, expect, it } from 'vitest'
import { describeAuthError } from '@/components/auth/auth-errors'

describe('describeAuthError', () => {
  it.each([
    ['auth/invalid-credential', 'signin'],
    ['auth/wrong-password', 'signin'],
    ['auth/user-not-found', 'signin'],
  ])('%s -> wrong-credentials sentence', (code, mode) => {
    const out = describeAuthError(code, mode as 'signin' | 'signup')
    expect(out).toEqual({
      kind: 'error',
      scope: 'card',
      text: "That email and password don't match. Try again, or continue with Google.",
    })
  })

  it('email already in use points at the Sign in tab', () => {
    expect(describeAuthError('auth/email-already-in-use', 'signup')).toEqual({
      kind: 'error',
      scope: 'card',
      text: 'An account with that email already exists — switch to Sign in.',
    })
  })

  it('weak password is a field-level error', () => {
    expect(describeAuthError('auth/weak-password', 'signup')).toEqual({
      kind: 'error',
      scope: 'password',
      text: 'Passwords need at least 12 characters.',
    })
  })

  it('network failure keeps the form and says so', () => {
    expect(describeAuthError('auth/network-request-failed', 'signin')).toEqual({
      kind: 'error',
      scope: 'card',
      text: "We couldn't reach Phoenix Audit. Check your connection and try again.",
    })
  })

  it('google provider disabled is the warn sentence', () => {
    expect(describeAuthError('auth/operation-not-allowed', 'signin')).toEqual({
      kind: 'warn',
      scope: 'card',
      text: "Google sign-in isn't available yet — use email for now.",
    })
  })

  it('a closed Google popup is not an error — no notice', () => {
    expect(describeAuthError('auth/popup-closed-by-user', 'signin')).toBeNull()
    expect(describeAuthError('auth/cancelled-popup-request', 'signin')).toBeNull()
  })

  it('unknown codes still produce a sentence, not a code', () => {
    const out = describeAuthError('auth/some-future-code', 'signin')
    expect(out?.kind).toBe('error')
    expect(out?.text).not.toMatch(/auth\//)
  })
})

describe('describeAuthError — review additions', () => {
  it('invalid-email joins the wrong-credentials group', () => {
    expect(describeAuthError('auth/invalid-email', 'signin')?.text).toMatch(/don't match/)
  })

  it('too-many-requests asks the user to wait', () => {
    expect(describeAuthError('auth/too-many-requests', 'signin')?.text).toMatch(/Too many/)
  })

  it('configuration-not-found degrades like a disabled Google provider', () => {
    expect(describeAuthError('auth/configuration-not-found', 'signin')).toEqual({
      kind: 'warn',
      scope: 'card',
      text: "Google sign-in isn't available yet — use email for now.",
    })
  })

  it('session-mint failure says auth succeeded but the session did not', () => {
    const out = describeAuthError('phx/session-mint-failed', 'signin')
    expect(out?.kind).toBe('error')
    expect(out?.text).toMatch(/verified.*session/i)
  })
})
