// Story-9.17 — GitLab connect/status/projects/file-MR request logic. Pure
// module (node-env vitest idiom); the settings card + recipe button are
// thin shells over these helpers.

import { describe, expect, it, vi } from 'vitest'
import {
  disconnectGitLab,
  fetchGitLabProjects,
  fetchGitLabStatus,
  fileGitLabMr,
  startGitLabConnect,
} from '@/lib/gitlab-connect'

function fetchReturning(status: number, body: unknown) {
  return vi.fn(async () => new Response(JSON.stringify(body), { status }))
}

describe('fetchGitLabStatus', () => {
  it('returns the connection state', async () => {
    const f = fetchReturning(200, { connected: true, username: 'abu' })
    expect(await fetchGitLabStatus(f)).toEqual({ connected: true, username: 'abu' })
    expect(f).toHaveBeenCalledWith('/api/agent/integrations/gitlab/status')
  })

  it('returns null on failure — the card shows "status unavailable", never a fake disconnected', async () => {
    const f = fetchReturning(502, { detail: 'x' })
    expect(await fetchGitLabStatus(f)).toBeNull()
    const g = vi.fn(async () => {
      throw new TypeError('network down')
    })
    expect(await fetchGitLabStatus(g)).toBeNull()
  })
})

describe('startGitLabConnect', () => {
  it('returns the authorize URL to navigate to', async () => {
    const f = fetchReturning(200, { authorize_url: 'https://gitlab.com/oauth/authorize?x=1' })
    expect(await startGitLabConnect(f)).toBe('https://gitlab.com/oauth/authorize?x=1')
  })

  it('returns null when unconfigured (503) or errored', async () => {
    expect(await startGitLabConnect(fetchReturning(503, { detail: 'not configured' }))).toBeNull()
  })
})

describe('disconnectGitLab', () => {
  it('DELETEs and reports success', async () => {
    const f = vi.fn(async () => new Response(null, { status: 204 }))
    expect(await disconnectGitLab(f)).toBe(true)
    expect(f).toHaveBeenCalledWith('/api/agent/integrations/gitlab/connection', {
      method: 'DELETE',
    })
  })

  it('reports failure without throwing', async () => {
    const f = vi.fn(async () => {
      throw new TypeError('down')
    })
    expect(await disconnectGitLab(f)).toBe(false)
  })
})

describe('fetchGitLabProjects', () => {
  it('returns projects on success', async () => {
    const f = fetchReturning(200, { projects: [{ id: 7, path_with_namespace: 'abu/agents' }] })
    expect(await fetchGitLabProjects(f)).toEqual({
      ok: true,
      projects: [{ id: 7, path_with_namespace: 'abu/agents' }],
    })
  })

  it('surfaces the backend detail (409 reconnect, 502 gitlab down)', async () => {
    const f = fetchReturning(409, { detail: 'GitLab connection expired — reconnect' })
    expect(await fetchGitLabProjects(f)).toEqual({
      ok: false,
      error: 'GitLab connection expired — reconnect',
    })
  })
})

describe('fileGitLabMr', () => {
  it('POSTs the chosen project and returns the MR URL + persistence disclosure', async () => {
    const f = fetchReturning(200, {
      mr_url: 'https://gitlab.com/abu/agents/-/merge_requests/7',
      persisted: true,
    })
    const result = await fileGitLabMr('run_abc123def456', 7, f)
    expect(f).toHaveBeenCalledWith('/api/agent/runs/run_abc123def456/gitlab-mr', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ project_id: 7 }),
    })
    expect(result).toEqual({
      ok: true,
      mrUrl: 'https://gitlab.com/abu/agents/-/merge_requests/7',
      persisted: true,
    })
  })

  it('surfaces idempotency and failure details', async () => {
    const f = fetchReturning(409, { detail: 'an MR was already filed for this run: https://x' })
    expect(await fileGitLabMr('run_abc123def456', 7, f)).toEqual({
      ok: false,
      error: 'an MR was already filed for this run: https://x',
    })
  })

  it('contains network errors', async () => {
    const f = vi.fn(async () => {
      throw new TypeError('network down')
    })
    const result = await fileGitLabMr('run_abc123def456', 7, f)
    expect(result.ok).toBe(false)
  })
})
