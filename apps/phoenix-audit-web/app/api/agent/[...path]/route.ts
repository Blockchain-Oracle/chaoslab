// Same-origin proxy to the IAM-gated agent service — and the Firebase-auth
// enforcement point (story-9.4).
//
// The browser (EventSource can't attach Authorization headers) talks to
// /api/agent/<path>; this handler verifies the session cookie, then forwards
// with the metadata-minted GCP ID token on Authorization (Cloud Run ingress)
// and the user's Firebase ID token on X-Firebase-Id-Token (backend identity).

import type { NextRequest } from 'next/server'
import { getTokens } from 'next-firebase-auth-edge'
import { agentAuthHeaders, agentBaseUrl } from '@/lib/server/agent-fetch'
import { serverAuthConfig } from '@/lib/auth/config'

// Allowlist — this is a proxy to ONE service's known API, not an open relay.
// NOTE: /internal/* is deliberately absent — the scheduler tick is
// OIDC-gated and must never be reachable through the public proxy.
const ALLOWED = [
  /^run$/,
  /^runs$/,
  /^runs\/[a-zA-Z0-9_-]+$/,
  // Story-9.5: "Email me this report" — recipient is server-derived from
  // the verified token; the POST carries no body.
  /^runs\/[a-zA-Z0-9_-]+\/email$/,
  // Story-9.17: review-first GitLab MR filing + the connect flow.
  // NOTE: integrations/gitlab/exchange is deliberately ABSENT — only the
  // /integrations/gitlab/callback server route may reach it.
  /^runs\/[a-zA-Z0-9_-]+\/gitlab-mr$/,
  /^integrations\/gitlab\/(connect|status|projects|connection)$/,
  /^stream$/,
  /^agents$/,
  /^agents\/[a-zA-Z0-9_-]+$/,
  /^schedules$/,
  /^schedules\/[a-zA-Z0-9_-]+$/,
  /^profile$/,
  /^health$/,
  // Story-9.15: datasets listing + detail. The slug pattern matches the
  // backend DatasetIndex regex (lowercase + alphanumerics + `_` + `-`),
  // so a mixed-case or special-char slug 404s here and never reaches the
  // agent.
  /^datasets$/,
  /^datasets\/[a-z0-9_-]+$/,
]

function allowed(path: string): boolean {
  return ALLOWED.some((re) => re.test(path))
}

async function proxy(req: NextRequest, pathParts: string[]): Promise<Response> {
  const path = pathParts.join('/')
  if (!allowed(path)) {
    return Response.json({ detail: `path not allowed: ${path}` }, { status: 404 })
  }
  // Session check AFTER the allowlist 404 — disallowed paths read as
  // nonexistent even to authenticated callers and never touch auth or the
  // upstream — and BEFORE any upstream call. EventSource cannot set headers,
  // so the cookie is the only credential the browser can present here.
  const tokens = await getTokens(req.cookies, serverAuthConfig())
  if (!tokens) {
    return Response.json({ detail: 'sign in required' }, { status: 401 })
  }
  const search = req.nextUrl.search
  const headers: Record<string, string> = await agentAuthHeaders()
  headers['x-firebase-id-token'] = tokens.token
  const contentType = req.headers.get('content-type')
  if (contentType) headers['content-type'] = contentType
  // Accept is forced per-path: only /stream is SSE; everything else is JSON.
  // Browser cookies are DELIBERATELY not forwarded — the agent is a separate
  // trust domain; do not "helpfully" add them.
  headers['accept'] = path === 'stream' ? 'text/event-stream' : 'application/json'

  const upstream = await fetch(`${agentBaseUrl()}/${path}${search}`, {
    method: req.method,
    headers,
    body: req.method === 'POST' || req.method === 'PATCH' ? req.body : undefined,
    cache: 'no-store',
    // @ts-expect-error -- undici needs duplex for streaming request bodies
    duplex: 'half',
  })

  // Pass the body stream through untouched — REQUIRED for SSE (no buffering).
  const responseHeaders = new Headers()
  const passthrough = ['content-type', 'cache-control']
  for (const name of passthrough) {
    const value = upstream.headers.get(name)
    if (value) responseHeaders.set(name, value)
  }
  responseHeaders.set('x-accel-buffering', 'no')
  return new Response(upstream.body, {
    status: upstream.status,
    headers: responseHeaders,
  })
}

interface Ctx {
  params: Promise<{ path: string[] }>
}

export async function GET(req: NextRequest, ctx: Ctx): Promise<Response> {
  const { path } = await ctx.params
  return proxy(req, path)
}

export async function POST(req: NextRequest, ctx: Ctx): Promise<Response> {
  const { path } = await ctx.params
  return proxy(req, path)
}

export async function PATCH(req: NextRequest, ctx: Ctx): Promise<Response> {
  const { path } = await ctx.params
  return proxy(req, path)
}

export async function DELETE(req: NextRequest, ctx: Ctx): Promise<Response> {
  // Story-9.15: uploaded datasets are user-deletable. The allowlist gates
  // which slugs reach the agent; the agent enforces ownership.
  const { path } = await ctx.params
  return proxy(req, path)
}

// SSE must not be statically optimized or buffered, must run on Node (the
// metadata-server ID-token mint + duplex streaming need it), and must outlive
// the ~90s audit: the App Router default duration (10s) would tear the stream
// down mid-demo.
export const dynamic = 'force-dynamic'
export const runtime = 'nodejs'
export const maxDuration = 300
