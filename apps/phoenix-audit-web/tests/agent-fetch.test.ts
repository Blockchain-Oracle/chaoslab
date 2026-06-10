// The memoized ID-token client must never cache a FAILED mint — a rejected
// promise cached forever would 401 every proxied request until redeploy.

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const getIdTokenClient = vi.fn()

vi.mock('google-auth-library', () => ({
  GoogleAuth: class {
    getIdTokenClient(audience: string) {
      return getIdTokenClient(audience)
    }
  },
}))

import { agentAuthHeaders } from '@/lib/server/agent-fetch'

function clientReturning(token: string) {
  return {
    getRequestHeaders: async () => new Headers({ Authorization: token }),
  }
}

beforeEach(() => {
  getIdTokenClient.mockReset()
  vi.stubEnv('K_SERVICE', 'phoenix-audit-web')
})

afterEach(() => {
  vi.unstubAllEnvs()
})

describe('agentAuthHeaders memoization', () => {
  // The memo Map is module-level state — give each test its own audience so
  // one test's cache entry can't leak into the next.
  it('reuses one client across calls (no per-request mint)', async () => {
    vi.stubEnv('AGENT_URL', 'http://agent-one.test')
    getIdTokenClient.mockResolvedValue(clientReturning('Bearer tok-1'))
    const first = await agentAuthHeaders()
    const second = await agentAuthHeaders()
    expect(first).toEqual({ Authorization: 'Bearer tok-1' })
    expect(second).toEqual({ Authorization: 'Bearer tok-1' })
    expect(getIdTokenClient).toHaveBeenCalledTimes(1)
  })

  it('evicts a failed mint so the next request retries instead of failing forever', async () => {
    vi.stubEnv('AGENT_URL', 'http://agent-two.test')
    getIdTokenClient.mockRejectedValueOnce(new Error('metadata server hiccup'))
    getIdTokenClient.mockResolvedValue(clientReturning('Bearer tok-2'))

    await expect(agentAuthHeaders()).rejects.toThrow('metadata server hiccup')
    // allow the eviction microtask to run
    await Promise.resolve()

    const headers = await agentAuthHeaders()
    expect(headers).toEqual({ Authorization: 'Bearer tok-2' })
    expect(getIdTokenClient).toHaveBeenCalledTimes(2)
  })
})
