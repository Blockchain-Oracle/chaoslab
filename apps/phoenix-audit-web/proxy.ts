// Next.js 16 proxy (the middleware.ts successor) — the page-level auth gate
// (story-9.4). Product pages redirect signed-out visitors to /login; the
// landing page and demo replay stay public. /api/agent enforces its own 401
// in the route handler (EventSource clients need JSON errors, not redirects).

import type { NextRequest } from 'next/server'
import { NextResponse } from 'next/server'
import { authMiddleware } from 'next-firebase-auth-edge'
import { serverAuthConfig } from '@/lib/auth/config'
import { isPublicPath } from '@/lib/auth/routes'

function loginRedirect(request: NextRequest, reason?: 'session'): NextResponse {
  const url = request.nextUrl.clone()
  url.pathname = '/login'
  url.search =
    `redirect=${encodeURIComponent(request.nextUrl.pathname + request.nextUrl.search)}` +
    (reason ? `&error=${reason}` : '')
  return NextResponse.redirect(url)
}

export async function proxy(request: NextRequest): Promise<NextResponse> {
  const cfg = serverAuthConfig()
  return authMiddleware(request, {
    loginPath: '/api/login',
    logoutPath: '/api/logout',
    ...cfg,
    cookieSerializeOptions: {
      path: '/',
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'lax' as const,
      // SECURITY trade-off, deliberate: 12 DAYS (not hours). A judge who
      // signs in on day 1 of the judging window stays signed in through it —
      // continuity beats short-session purism for this product's moment.
      // The cookie is httpOnly+secure+signed; sign-out clears it. Revisit to
      // hours post-judging.
      maxAge: 12 * 60 * 60 * 24,
    },
    handleValidToken: async (_tokens, headers) => {
      return NextResponse.next({ request: { headers } })
    },
    handleInvalidToken: async () => {
      if (isPublicPath(request.nextUrl.pathname)) return NextResponse.next()
      return loginRedirect(request)
    },
    handleError: async (error) => {
      // Verification ERRORS (not just absent sessions) also land on /login —
      // fail closed, logged server-side, and the login page shows a notice
      // (?error=session) so the user isn't dumped there with no explanation.
      console.error('auth middleware error:', error)
      if (isPublicPath(request.nextUrl.pathname)) return NextResponse.next()
      return loginRedirect(request, 'session')
    },
  })
}

export const config = {
  // Everything except Next internals and static assets. /api/agent is matched
  // on purpose: the middleware refreshes expiring session cookies on those
  // calls too; its 401 handling stays in the route handler.
  matcher: ['/api/login', '/api/logout', '/((?!_next|favicon.ico|og/|.*\\.).*)'],
}
