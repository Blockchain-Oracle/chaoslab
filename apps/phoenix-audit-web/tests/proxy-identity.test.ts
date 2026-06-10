// The /api/agent proxy is the Firebase enforcement point (story-9.4): no
// session => 401 before any upstream call; with a session, the verified ID
// token rides upstream in X-Firebase-Id-Token while browser cookies are
// deliberately NOT forwarded (the agent is a separate trust domain).

import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { NextRequest } from 'next/server'

vi.mock('@/lib/server/agent-fetch', () => ({
  agentAuthHeaders: async () => ({ Authorization: 'Bearer gcp-service-token' }),
  agentBaseUrl: () => 'http://agent.test',
}))

const getTokens = vi.fn()
vi.mock('next-firebase-auth-edge', () => ({
  getTokens: (...args: unknown[]) => getTokens(...args),
}))

vi.mock('@/lib/auth/config', () => ({
  serverAuthConfig: () => ({
    apiKey: 'test-api-key',
    cookieName: 'AuthToken',
    cookieSignatureKeys: ['k'.repeat(32)],
  }),
}))

import { GET, POST } from '@/app/api/agent/[...path]/route'

function req(method: string, search = ''): NextRequest {
  return {
    method,
    nextUrl: { search },
    headers: new Headers({ cookie: 'AuthToken=signed-session' }),
    cookies: { get: () => undefined },
    body: null,
  } as unknown as NextRequest
}

function ctx(path: string[]) {
  return { params: Promise.resolve({ path }) }
}

const upstream = vi.fn()

beforeEach(() => {
  upstream.mockReset()
  getTokens.mockReset()
  upstream.mockResolvedValue(
    new Response('{}', { status: 200, headers: { 'content-type': 'application/json' } }),
  )
  vi.stubGlobal('fetch', upstream)
})

describe('proxy identity forwarding', () => {
  it('401s without a session and never calls upstream', async () => {
    getTokens.mockResolvedValue(null)
    const res = await GET(req('GET'), ctx(['runs']))
    expect(res.status).toBe(401)
    expect(upstream).not.toHaveBeenCalled()
  })

  it('attaches X-Firebase-Id-Token from the verified session', async () => {
    getTokens.mockResolvedValue({ token: 'verified-id-token' })
    const res = await GET(req('GET'), ctx(['runs']))
    expect(res.status).toBe(200)
    const init = upstream.mock.calls[0]?.[1] as RequestInit
    const headers = init.headers as Record<string, string>
    expect(headers['x-firebase-id-token']).toBe('verified-id-token')
    // GCP service-to-service auth stays untouched on Authorization.
    expect(headers['Authorization']).toBe('Bearer gcp-service-token')
  })

  it('never forwards browser cookies upstream', async () => {
    getTokens.mockResolvedValue({ token: 'verified-id-token' })
    await POST(req('POST'), ctx(['run']))
    const init = upstream.mock.calls[0]?.[1] as RequestInit
    const headers = init.headers as Record<string, string>
    expect(headers['cookie']).toBeUndefined()
    expect(headers['Cookie']).toBeUndefined()
  })

  it('401 wins over the allowlist 404 only AFTER the allowlist check', async () => {
    // Disallowed paths 404 without touching auth — they read as nonexistent
    // even to authenticated callers, and auth machinery never runs for them.
    getTokens.mockResolvedValue(null)
    const res = await POST(req('POST'), ctx(['internal', 'scheduler-tick']))
    expect(res.status).toBe(404)
    expect(upstream).not.toHaveBeenCalled()
  })
})
