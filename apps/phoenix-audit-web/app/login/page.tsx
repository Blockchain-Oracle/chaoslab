// /login — the branded moment (designer's Surface L): spinning seal
// watermark behind the login-card; landing + demo replay stay public.

import type { Metadata } from 'next'
import { LoginCard } from '@/components/auth/login-card'
import { A } from '@/components/ui/link'
import { Seal } from '@/components/ui/seal'
import { Wordmark } from '@/components/ui/wordmark'

export const metadata: Metadata = {
  title: 'Sign in — Phoenix Audit',
}

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>
}) {
  const params = await searchParams
  const redirect = typeof params.redirect === 'string' ? params.redirect : null
  const signedOut = params.signedout === '1'
  return (
    <div className="page-enter login-stage">
      <div className="login-watermark" aria-hidden="true">
        <Seal size={780} spin={true} />
      </div>
      <header className="login-strip">
        <A to="" style={{ textDecoration: 'none', color: 'inherit', display: 'flex' }}>
          <Wordmark size={16} glyph={18} />
        </A>
        <A
          to="replay"
          className="mono"
          style={{
            fontSize: 10.5,
            letterSpacing: '0.14em',
            color: 'var(--ink-3)',
            textDecoration: 'none',
          }}
        >
          WATCH THE DEMO REPLAY →
        </A>
      </header>
      <main
        className="rise rise-1"
        style={{
          flex: 1,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '30px 20px 70px',
          position: 'relative',
        }}
      >
        <LoginCard
          redirect={redirect}
          initialNotice={
            signedOut ? { kind: 'info', text: 'Signed out — sign in to continue.' } : null
          }
        />
      </main>
      <footer className="login-strip" style={{ justifyContent: 'center' }}>
        <span
          className="mono"
          style={{
            fontSize: 10,
            letterSpacing: '0.16em',
            color: 'var(--ink-3)',
            textAlign: 'center',
          }}
        >
          THE LANDING PAGE &amp; DEMO REPLAY STAY PUBLIC · EVERYTHING ELSE IS BEHIND SIGN-IN
        </span>
      </footer>
    </div>
  )
}
