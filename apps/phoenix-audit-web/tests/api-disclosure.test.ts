// Registry fetch failures must surface as liveError DISCLOSURE — pages render
// the sample world WITH a visible notice, never a thrown render error and
// never a silent demo fallback.

import { beforeEach, describe, expect, it, vi } from 'vitest'

const agentFetch = vi.fn()

vi.mock('@/lib/server/agent-fetch', () => ({
  agentFetch: (...args: unknown[]) => agentFetch(...args),
}))

import { fetchRunDetail, fetchRuns } from '@/lib/api'

beforeEach(() => {
  agentFetch.mockReset()
})

describe('liveError disclosure', () => {
  it('backend 503 → empty data + liveError, no throw', async () => {
    agentFetch.mockResolvedValue(new Response('oops', { status: 503 }))
    const { data, liveError } = await fetchRuns()
    expect(data).toEqual([])
    expect(liveError).toContain('503')
  })

  it('non-JSON body on a 200 → liveError, no throw', async () => {
    agentFetch.mockResolvedValue(
      new Response('<html>gateway error</html>', {
        status: 200,
        headers: { 'content-type': 'text/html' },
      }),
    )
    const { data, liveError } = await fetchRuns()
    expect(data).toEqual([])
    expect(liveError).not.toBeNull()
  })

  it('network failure → liveError + status null (outage, not authoritative 404)', async () => {
    agentFetch.mockRejectedValue(new Error('ECONNREFUSED'))
    const detail = await fetchRunDetail('run_abcabcabcab')
    expect(detail.data).toBeNull()
    expect(detail.liveError).toContain('ECONNREFUSED')
    expect(detail.status).toBeNull()
  })

  it('authoritative 404 → status 404 so the page can notFound()', async () => {
    agentFetch.mockResolvedValue(new Response('{"detail":"nope"}', { status: 404 }))
    const detail = await fetchRunDetail('run_abcabcabcab')
    expect(detail.data).toBeNull()
    expect(detail.status).toBe(404)
  })
})
