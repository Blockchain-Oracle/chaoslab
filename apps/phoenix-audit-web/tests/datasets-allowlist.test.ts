// Story-9.15 — proxy allowlist gains /datasets and /datasets/{slug}.
//
// The detail-slug pattern matches the backend's DatasetIndex slug regex
// (lowercase alphanumerics, hyphens, underscores) — same character class
// the API enforces server-side. Mixed-case or special-char slugs MUST
// 404 at the proxy boundary so a malformed URL never reaches the agent.

import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { NextRequest } from 'next/server'

vi.mock('@/lib/server/agent-fetch', () => ({
  agentAuthHeaders: async () => ({}),
  agentBaseUrl: () => 'http://agent.test',
}))

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

import { GET, POST, DELETE } from '@/app/api/agent/[...path]/route'

function req(method: string, search = ''): NextRequest {
  return {
    method,
    nextUrl: { search } as URL,
    headers: new Headers({ accept: 'application/json' }),
    cookies: { get: vi.fn(() => ({ value: 'AuthToken' })) },
  } as unknown as NextRequest
}

function ctx(path: string[]): { params: Promise<{ path: string[] }> } {
  return { params: Promise.resolve({ path }) }
}

const upstream = vi.fn()
beforeEach(() => {
  upstream.mockReset()
  upstream.mockResolvedValue(new Response('{"datasets":[]}', { status: 200 }))
  vi.stubGlobal('fetch', upstream)
})

describe('proxy allowlist — datasets routes', () => {
  it.each([
    ['datasets'],
    ['datasets/harmbench-v1-sample'],
    ['datasets/regression-agt_x'],
    ['datasets/ds_a1b2c3'],
  ])('forwards %s upstream', async (path) => {
    const res = await GET(req('GET'), ctx(path.split('/')))
    expect(res.status).toBe(200)
    expect(upstream).toHaveBeenCalledOnce()
  })

  it('forwards POST /datasets (upload) upstream', async () => {
    const res = await POST(req('POST'), ctx(['datasets']))
    expect(res.status).toBe(200)
    expect(upstream).toHaveBeenCalledOnce()
  })

  it('forwards DELETE /datasets/{slug} upstream', async () => {
    const res = await DELETE(req('DELETE'), ctx(['datasets', 'ds_a1b2c3']))
    expect(res.status).toBe(200)
    expect(upstream).toHaveBeenCalledOnce()
  })

  it.each([
    ['datasets/Mixed-Case'],
    ['datasets/has spaces'],
    ['datasets/extra/path'],
    ['datasets/has.dots'],
  ])('blocks malformed slug %s with 404', async (path) => {
    const res = await GET(req('GET'), ctx(path.split('/')))
    expect(res.status).toBe(404)
    expect(upstream).not.toHaveBeenCalled()
  })
})
