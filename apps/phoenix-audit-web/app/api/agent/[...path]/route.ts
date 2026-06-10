// Same-origin proxy to the IAM-gated agent service.
//
// The browser (EventSource can't attach Authorization headers) talks to
// /api/agent/<path>; this handler forwards with a metadata-minted ID token.
// Becomes the Firebase-auth enforcement point in story-9.4.

import type { NextRequest } from 'next/server'
import { agentAuthHeaders, agentBaseUrl } from '@/lib/server/agent-fetch'

// Allowlist — this is a proxy to ONE service's known API, not an open relay.
const ALLOWED = [
  /^run$/,
  /^runs$/,
  /^runs\/[a-zA-Z0-9_-]+$/,
  /^stream$/,
  /^agents$/,
  /^agents\/[a-zA-Z0-9_-]+$/,
  /^health$/,
]

function allowed(path: string): boolean {
  return ALLOWED.some((re) => re.test(path))
}

async function proxy(req: NextRequest, pathParts: string[]): Promise<Response> {
  const path = pathParts.join('/')
  if (!allowed(path)) {
    return Response.json({ detail: `path not allowed: ${path}` }, { status: 404 })
  }
  const search = req.nextUrl.search
  const headers: Record<string, string> = await agentAuthHeaders()
  const contentType = req.headers.get('content-type')
  if (contentType) headers['content-type'] = contentType
  // Accept is forced per-path: only /stream is SSE; everything else is JSON.
  // Browser cookies are DELIBERATELY not forwarded — the agent is a separate
  // trust domain; do not "helpfully" add them.
  headers['accept'] = path === 'stream' ? 'text/event-stream' : 'application/json'

  const upstream = await fetch(`${agentBaseUrl()}/${path}${search}`, {
    method: req.method,
    headers,
    body: req.method === 'POST' ? req.body : undefined,
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

// SSE must not be statically optimized or buffered, must run on Node (the
// metadata-server ID-token mint + duplex streaming need it), and must outlive
// the ~90s audit: the App Router default duration (10s) would tear the stream
// down mid-demo.
export const dynamic = 'force-dynamic'
export const runtime = 'nodejs'
export const maxDuration = 300
