'use client'

// user-menu — the signed-in state in the app header (designer's Surface L).
// Sign out clears the session cookie AND the Firebase client state, then
// lands on /login with the "Signed out — sign in to continue" notice.

import { useEffect, useRef, useState } from 'react'
import { onAuthStateChanged, signOut, type User } from 'firebase/auth'
import { getFirebaseAuth } from '@/lib/auth/client'

export function UserMenu() {
  const [open, setOpen] = useState(false)
  const [user, setUser] = useState<User | null>(null)
  const [signOutFailed, setSignOutFailed] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    return onAuthStateChanged(getFirebaseAuth(), setUser)
  }, [])

  useEffect(() => {
    function onDoc(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', onDoc)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDoc)
      document.removeEventListener('keydown', onKey)
    }
  }, [])

  async function handleSignOut() {
    // Cookie first (the actual gate), client state second. Navigation only
    // happens when the cookie is actually cleared — showing "Signed out"
    // while a 12-day session cookie survives would be a lie with a long
    // shelf life on a shared machine.
    try {
      const res = await fetch('/api/logout')
      if (!res.ok) throw new Error(`logout endpoint answered ${res.status}`)
      await signOut(getFirebaseAuth())
      window.location.assign('/login?signedout=1')
    } catch (err) {
      console.error('sign-out failed — session cookie may still be active:', err)
      setSignOutFailed(true)
    }
  }

  // The session cookie is the gate, not the client SDK — middleware already
  // let this page render. Until the client SDK hydrates, show nothing.
  if (!user) return null

  const email = user.email ?? 'signed in'
  const name = user.displayName ?? email.split('@')[0]
  const initial = (name?.[0] ?? 'P').toUpperCase()

  return (
    <div className="user-menu" ref={ref}>
      <button
        type="button"
        className="user-menu-btn"
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen(!open)}
      >
        <span className="avatar-dot" aria-hidden="true">
          {initial}
        </span>
        <span className="user-menu-email">{email}</span>
        <span style={{ fontSize: 8, color: 'var(--ink-3)' }}>▾</span>
      </button>
      {open ? (
        <div className="user-menu-pop" role="menu">
          <div className="who">
            <div style={{ fontSize: 13.5, fontWeight: 500 }}>{name}</div>
            <div
              className="mono muted"
              style={{ fontSize: 10.5, letterSpacing: '0.04em', marginTop: 3 }}
            >
              {email}
            </div>
          </div>
          <button
            type="button"
            className="user-menu-signout"
            role="menuitem"
            onClick={handleSignOut}
          >
            Sign out →
          </button>
          {signOutFailed ? (
            <div role="alert" style={{ padding: '8px 12px', fontSize: 12, color: 'var(--fail)' }}>
              Sign-out didn’t complete — try again.
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  )
}
