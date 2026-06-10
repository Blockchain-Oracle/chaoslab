'use client'

// login-card — both methods, one screen (designer's Surface L, real Firebase).
// Sign in ↔ Create account via tabs; Google leads (single-button prominence);
// the busy state is the quiet pulse, never a spinner. The form keeps
// everything typed on failure — nothing is cleared.

import { useState } from 'react'
import {
  GoogleAuthProvider,
  createUserWithEmailAndPassword,
  signInWithEmailAndPassword,
  signInWithPopup,
  type UserCredential,
} from 'firebase/auth'
import { getFirebaseAuth } from '@/lib/auth/client'
import { safeRedirectTarget } from '@/lib/auth/routes'
import { Glyph } from '@/components/ui/glyph'
import { describeAuthError } from './auth-errors'
import { AuthInput, AuthNotice, AuthSubmit, GoogleButton } from './primitives'

type Mode = 'signin' | 'signup'
type Busy = 'email' | 'google' | null

interface Notice {
  kind: 'info' | 'warn' | 'error'
  text: string
}

const MIN_PASSWORD_CHARS = 12

async function establishSession(
  credential: UserCredential,
  redirect: string | null,
): Promise<void> {
  const idToken = await credential.user.getIdToken()
  const res = await fetch('/api/login', { headers: { Authorization: `Bearer ${idToken}` } })
  if (!res.ok) {
    // Distinct code: Firebase auth SUCCEEDED here — only the session cookie
    // failed to mint. The generic "something went wrong" would mislead.
    throw Object.assign(new Error(`session cookie mint failed: ${res.status}`), {
      code: 'phx/session-mint-failed',
    })
  }
  // Full navigation (not router.push) so the middleware and every server
  // component see the fresh session cookie.
  window.location.assign(safeRedirectTarget(redirect))
}

export function LoginCard({
  redirect,
  initialNotice = null,
}: {
  redirect: string | null
  initialNotice?: Notice | null
}) {
  const [mode, setMode] = useState<Mode>('signin')
  const [email, setEmail] = useState('')
  const [pw, setPw] = useState('')
  const [busy, setBusy] = useState<Busy>(null)
  const [note, setNote] = useState<Notice | null>(initialNotice)
  const [errs, setErrs] = useState<{ email?: string | null; password?: string | null }>({})

  const signin = mode === 'signin'

  function switchMode(m: Mode) {
    if (busy) return
    setMode(m)
    setNote(null)
    setErrs({})
  }

  function fail(err: unknown) {
    // Always leave a console trail — the on-screen sentence is for the user;
    // the raw error is for whoever debugs a report of it.
    console.error('sign-in attempt failed:', err)
    const code =
      typeof err === 'object' && err !== null && 'code' in err ? String(err.code) : 'unknown'
    const described = describeAuthError(code, mode)
    if (!described) return
    if (described.scope === 'password') {
      setErrs({ password: described.text })
    } else {
      setNote({ kind: described.kind, text: described.text })
    }
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    if (busy) return
    const next = {
      email: email.trim() ? null : 'Enter your email.',
      password: pw ? null : 'Enter your password.',
    }
    if (!signin && pw && pw.length < MIN_PASSWORD_CHARS) {
      next.password = `Passwords need at least ${MIN_PASSWORD_CHARS} characters.`
    }
    setErrs(next)
    if (next.email || next.password) return
    setNote(null)
    setBusy('email')
    try {
      const auth = getFirebaseAuth()
      const credential = signin
        ? await signInWithEmailAndPassword(auth, email.trim(), pw)
        : await createUserWithEmailAndPassword(auth, email.trim(), pw)
      await establishSession(credential, redirect)
    } catch (err) {
      fail(err)
      setBusy(null)
    }
  }

  async function google() {
    if (busy) return
    setNote(null)
    setErrs({})
    setBusy('google')
    try {
      const credential = await signInWithPopup(getFirebaseAuth(), new GoogleAuthProvider())
      await establishSession(credential, redirect)
    } catch (err) {
      fail(err)
      setBusy(null)
    }
  }

  return (
    <form className="auth-card" onSubmit={submit} noValidate>
      <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 16 }}>
        <Glyph size={26} color="var(--ember-deep)" />
      </div>
      <h1
        className="serif"
        style={{
          fontSize: 25,
          fontWeight: 500,
          textAlign: 'center',
          lineHeight: 1.15,
          marginBottom: 7,
        }}
      >
        {signin ? 'Sign in to your register.' : 'Open your register.'}
      </h1>
      <p
        className="muted"
        style={{ fontSize: 13, textAlign: 'center', maxWidth: 300, margin: '0 auto' }}
      >
        {signin
          ? 'Audits, target agents and monitoring are private to your account.'
          : 'Your first signed audit report is 90 seconds away.'}
      </p>

      <div className="auth-tabs" role="tablist" aria-label="Sign in or create account">
        <button
          type="button"
          role="tab"
          aria-selected={signin}
          className={'auth-tab' + (signin ? ' active' : '')}
          onClick={() => switchMode('signin')}
        >
          Sign in
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={!signin}
          className={'auth-tab' + (!signin ? ' active' : '')}
          onClick={() => switchMode('signup')}
        >
          Create account
        </button>
      </div>

      {note ? (
        <AuthNotice kind={note.kind} style={{ marginBottom: 20 }}>
          {note.text}
        </AuthNotice>
      ) : null}

      <GoogleButton busy={busy === 'google'} disabled={busy === 'email'} onClick={google} />
      <div className="divider-word" style={{ margin: '20px 0 18px' }}>
        or with email
      </div>

      <AuthInput
        label="Email"
        name={'auth-email-' + mode}
        type="email"
        autoComplete="email"
        placeholder="you@company.com"
        value={email}
        onChange={setEmail}
        error={errs.email}
        disabled={!!busy}
      />
      <AuthInput
        label="Password"
        name={'auth-pw-' + mode}
        type="password"
        autoComplete={signin ? 'current-password' : 'new-password'}
        placeholder={signin ? 'Your password' : `${MIN_PASSWORD_CHARS}+ characters`}
        value={pw}
        onChange={setPw}
        error={errs.password}
        hint={!signin && !errs.password ? `At least ${MIN_PASSWORD_CHARS} characters.` : null}
        disabled={!!busy}
      />

      <div style={{ marginTop: 24 }}>
        <AuthSubmit
          busy={busy === 'email'}
          busyLabel={signin ? 'Verifying credentials' : 'Opening your register'}
          disabled={!!busy}
        >
          {signin ? 'Sign in' : 'Create account'}
        </AuthSubmit>
      </div>
    </form>
  )
}
