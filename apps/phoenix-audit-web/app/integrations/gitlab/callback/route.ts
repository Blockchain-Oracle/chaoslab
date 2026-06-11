// Story-9.17 — GitLab OAuth callback (registered redirect URI). Forwards
// code+state to the agent's exchange endpoint SERVER-SIDE with the session
// identity, then lands the browser back on /settings. The exchange endpoint
// is not in the proxy allowlist — this route is its only web-side caller.

import type { NextRequest } from 'next/server'
import { NextResponse } from 'next/server'
import { getTokens } from 'next-firebase-auth-edge'
import { agentAuthHeaders, agentBaseUrl } from '@/lib/server/agent-fetch'
import { serverAuthConfig } from '@/lib/auth/config'

function settingsRedirect(req: NextRequest, flag: 'connected' | 'error'): NextResponse {
  return NextResponse.redirect(new URL(`/settings?gitlab=${flag}`, req.url))
}

export async function GET(req: NextRequest): Promise<NextResponse> {
  const code = req.nextUrl.searchParams.get('code')
  const state = req.nextUrl.searchParams.get('state')
  if (!code || !state) return settingsRedirect(req, 'error')

  const tokens = await getTokens(req.cookies, serverAuthConfig())
  if (!tokens) {
    // Cold session mid-dance: log in, then return here with code+state intact.
    const login = new URL('/login', req.url)
    login.searchParams.set('redirect', req.nextUrl.pathname + req.nextUrl.search)
    return NextResponse.redirect(login)
  }

  let upstream: Response
  try {
    const headers: Record<string, string> = await agentAuthHeaders()
    headers['x-firebase-id-token'] = tokens.token
    const url =
      `${agentBaseUrl()}/integrations/gitlab/exchange` +
      `?code=${encodeURIComponent(code)}&state=${encodeURIComponent(state)}`
    upstream = await fetch(url, { headers, redirect: 'manual' })
  } catch {
    return settingsRedirect(req, 'error')
  }

  const location = upstream.headers.get('location')
  if (upstream.status === 307 && location) {
    // The agent's redirect targets PUBLIC_WEB_URL; re-derive the path on
    // THIS origin so staging (Cloud Run URL) and the domain both work.
    try {
      const target = new URL(location)
      return NextResponse.redirect(new URL(target.pathname + target.search, req.url))
    } catch {
      return settingsRedirect(req, 'error')
    }
  }
  return settingsRedirect(req, 'error')
}
