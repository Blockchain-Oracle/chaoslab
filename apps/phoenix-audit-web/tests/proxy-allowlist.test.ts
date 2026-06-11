// The /api/agent proxy is an allowlist to ONE service — the budget-burning
// scheduler tick and any other /internal/* surface must never be reachable
// through it.

import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { NextRequest } from 'next/server'

vi.mock('@/lib/server/agent-fetch', () => ({
  agentAuthHeaders: async () => ({}),
  agentBaseUrl: () => 'http://agent.test',
}))

// This file's subject is the allowlist — requests arrive with a valid
// session (auth enforcement: proxy-identity.test.ts).
vi.mock('next-firebase-auth-edge', () => ({
  getTokens: async () => ({ token: 'verified-id-token' }),
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
    headers: new Headers(),
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
  upstream.mockResolvedValue(
    new Response('{}', { status: 200, headers: { 'content-type': 'application/json' } }),
  )
  vi.stubGlobal('fetch', upstream)
})

describe('proxy allowlist', () => {
  it.each([
    ['internal/scheduler-tick'],
    ['internal'],
    ['runs/../internal/scheduler-tick'],
    ['admin'],
    ['runs/abc/extra'],
  ])('blocks %s with 404 and never calls upstream', async (path) => {
    const res = await POST(req('POST'), ctx(path.split('/')))
    expect(res.status).toBe(404)
    expect(upstream).not.toHaveBeenCalled()
  })

  it.each([['runs'], ['agents'], ['health'], ['schedules'], ['profile']])(
    'forwards %s upstream',
    async (path) => {
      const res = await GET(req('GET'), ctx([path]))
      expect(res.status).toBe(200)
      expect(upstream).toHaveBeenCalledOnce()
      const url = upstream.mock.calls[0]?.[0] as string
      expect(url).toBe(`http://agent.test/${path}`)
    },
  )

  it.each([
    ['integrations/gitlab/connect'],
    ['integrations/gitlab/status'],
    ['integrations/gitlab/projects'],
    ['integrations/gitlab/connection'],
  ])('forwards %s upstream (story-9.17)', async (path) => {
    const res = await GET(req('GET'), ctx(path.split('/')))
    expect(res.status).toBe(200)
    expect(upstream).toHaveBeenCalledOnce()
  })

  it('blocks the exchange endpoint — only the callback server route may reach it', async () => {
    const res = await GET(req('GET'), ctx(['integrations', 'gitlab', 'exchange']))
    expect(res.status).toBe(404)
    expect(upstream).not.toHaveBeenCalled()
  })

  it('forwards runs/{id}/gitlab-mr POST upstream (story-9.17)', async () => {
    const res = await POST(req('POST'), ctx(['runs', 'run_abc123def456', 'gitlab-mr']))
    expect(res.status).toBe(200)
    expect(upstream).toHaveBeenCalledOnce()
  })

  it('forwards runs/{id}/email POST upstream (story-9.5)', async () => {
    const res = await POST(req('POST'), ctx(['runs', 'run_abc123def456', 'email']))
    expect(res.status).toBe(200)
    expect(upstream).toHaveBeenCalledOnce()
    expect(upstream.mock.calls[0]?.[0]).toBe('http://agent.test/runs/run_abc123def456/email')
  })

  it('blocks email sub-sub-paths', async () => {
    const res = await POST(req('POST'), ctx(['runs', 'run_abc', 'email', 'extra']))
    expect(res.status).toBe(404)
    expect(upstream).not.toHaveBeenCalled()
  })

  it('blocks profile sub-paths — /profile is the only settings surface', async () => {
    const res = await GET(req('GET'), ctx(['profile', 'other-uid']))
    expect(res.status).toBe(404)
    expect(upstream).not.toHaveBeenCalled()
  })

  it('forces text/event-stream accept ONLY for /stream', async () => {
    await GET(req('GET', '?runId=run_abc'), ctx(['stream']))
    const init = upstream.mock.calls[0]?.[1] as RequestInit
    expect((init.headers as Record<string, string>)['accept']).toBe('text/event-stream')

    upstream.mockClear()
    await GET(req('GET'), ctx(['runs']))
    const init2 = upstream.mock.calls[0]?.[1] as RequestInit
    expect((init2.headers as Record<string, string>)['accept']).toBe('application/json')
  })
})
