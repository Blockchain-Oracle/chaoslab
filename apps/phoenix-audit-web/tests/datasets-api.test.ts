// Story-9.15 lib/api dataset fetchers — listing, detail, upload, delete.
//
// The wire contract mirrors the backend BDD: list returns scoped
// datasets, detail can return 503 with the index header (Phoenix outage
// graceful degrade), upload 422 carries parse_error XOR row_errors,
// delete 204 on success, 409 on battery/regression kinds.

import { beforeEach, describe, expect, it, vi } from 'vitest'

import type * as AgentFetchModule from '@/lib/server/agent-fetch'

vi.mock('@/lib/server/agent-fetch', async () => {
  const real = await vi.importActual<typeof AgentFetchModule>('@/lib/server/agent-fetch')
  return {
    ...real,
    agentAuthHeaders: async () => ({}),
    agentBaseUrl: () => 'http://agent.test',
  }
})

vi.mock('@/lib/server/user-fetch', () => ({
  userIdentityHeaders: async () => ({}),
}))

import {
  fetchDatasets,
  fetchDatasetDetail,
  uploadDataset,
  deleteDataset,
  type DatasetListRowDto,
  type DatasetDetailDto,
  type DatasetUnavailableDto,
  type UploadValidationErrorDto,
} from '@/lib/datasets'

const fetchMock = vi.fn()
beforeEach(() => {
  fetchMock.mockReset()
  vi.stubGlobal('fetch', fetchMock)
})

describe('fetchDatasets — listing', () => {
  it('returns the row array on 200', async () => {
    const rows: DatasetListRowDto[] = [
      {
        dataset_id: 'harmbench-v1-sample',
        name: 'HarmBench v1 (sample)',
        kind: 'battery',
        row_count: 50,
        source_url: 'https://example/source',
        agent_id: null,
        created_at: '2026-06-11T07:00:00+00:00',
        updated_at: '2026-06-11T07:00:00+00:00',
      },
    ]
    fetchMock.mockResolvedValue(new Response(JSON.stringify({ datasets: rows }), { status: 200 }))
    const result = await fetchDatasets()
    expect(result.data).toEqual(rows)
    expect(result.liveError).toBeNull()
  })

  it('returns [] + liveError on agent failure', async () => {
    fetchMock.mockResolvedValue(new Response('boom', { status: 500 }))
    const result = await fetchDatasets()
    expect(result.data).toEqual([])
    expect(result.liveError).toBeTruthy()
  })
})

describe('fetchDatasetDetail — detail page', () => {
  it('returns 200 detail with items', async () => {
    const detail: DatasetDetailDto = {
      dataset_id: 'harmbench-v1-sample',
      name: 'HarmBench v1 (sample)',
      kind: 'battery',
      row_count: 1,
      source_url: 'https://example',
      agent_id: null,
      created_at: '2026-06-11T07:00:00+00:00',
      updated_at: '2026-06-11T07:00:00+00:00',
      items: [
        {
          case_id: 'pi-001',
          fault_class: 'prompt_injection',
          prompt: 'p',
          expected: 'e',
          source: 's',
          severity: 'high',
          notes: null,
        },
      ],
    }
    fetchMock.mockResolvedValue(new Response(JSON.stringify(detail), { status: 200 }))
    const result = await fetchDatasetDetail('harmbench-v1-sample')
    expect(result.kind).toBe('ok')
    if (result.kind === 'ok') expect(result.data.items).toHaveLength(1)
  })

  it('returns kind=phoenix_outage when agent returns 503 with index body', async () => {
    const outage: DatasetUnavailableDto = {
      dataset_id: 'harmbench-v1-sample',
      name: 'HarmBench v1 (sample)',
      kind: 'battery',
      row_count: 50,
      source_url: null,
      agent_id: null,
      created_at: '2026-06-11T07:00:00+00:00',
      updated_at: '2026-06-11T07:00:00+00:00',
      reason: 'dataset rows temporarily unavailable',
    }
    fetchMock.mockResolvedValue(new Response(JSON.stringify(outage), { status: 503 }))
    const result = await fetchDatasetDetail('harmbench-v1-sample')
    expect(result.kind).toBe('phoenix_outage')
    if (result.kind === 'phoenix_outage') {
      expect(result.header.name).toBe('HarmBench v1 (sample)')
      expect(result.header.reason).toBe('dataset rows temporarily unavailable')
    }
  })

  it('returns kind=not_found on 404', async () => {
    fetchMock.mockResolvedValue(new Response('{"detail":"dataset not found"}', { status: 404 }))
    const result = await fetchDatasetDetail('ghost')
    expect(result.kind).toBe('not_found')
  })

  it('returns kind=error on other 5xx', async () => {
    fetchMock.mockResolvedValue(new Response('boom', { status: 500 }))
    const result = await fetchDatasetDetail('any')
    expect(result.kind).toBe('error')
  })
})

describe('uploadDataset — POST /datasets', () => {
  it('returns ok on 201', async () => {
    const row: DatasetListRowDto = {
      dataset_id: 'ds_abc',
      name: 'My corpus',
      kind: 'uploaded',
      row_count: 2,
      source_url: null,
      agent_id: null,
      created_at: '2026-06-11T07:00:00+00:00',
      updated_at: '2026-06-11T07:00:00+00:00',
    }
    fetchMock.mockResolvedValue(new Response(JSON.stringify(row), { status: 201 }))
    const result = await uploadDataset({ name: 'My corpus', format: 'jsonl', bodyBase64: 'eA==' })
    expect(result.kind).toBe('ok')
    if (result.kind === 'ok') expect(result.row.dataset_id).toBe('ds_abc')
  })

  it('returns kind=validation_error on 422 with row_errors', async () => {
    const err: UploadValidationErrorDto = {
      parse_error: null,
      row_errors: [{ row: 17, reason: 'fault_class: unknown' }],
    }
    fetchMock.mockResolvedValue(new Response(JSON.stringify(err), { status: 422 }))
    const result = await uploadDataset({ name: 'x', format: 'jsonl', bodyBase64: 'eA==' })
    expect(result.kind).toBe('validation_error')
    if (result.kind === 'validation_error') {
      expect(result.error.row_errors).toHaveLength(1)
      expect(result.error.parse_error).toBeNull()
    }
  })

  it('returns kind=validation_error on 422 with parse_error', async () => {
    const err: UploadValidationErrorDto = {
      parse_error: 'line 1: not valid JSON',
      row_errors: [],
    }
    fetchMock.mockResolvedValue(new Response(JSON.stringify(err), { status: 422 }))
    const result = await uploadDataset({ name: 'x', format: 'jsonl', bodyBase64: 'eA==' })
    expect(result.kind).toBe('validation_error')
    if (result.kind === 'validation_error') {
      expect(result.error.parse_error).toBe('line 1: not valid JSON')
    }
  })

  it('returns kind=error on agent 500', async () => {
    fetchMock.mockResolvedValue(new Response('boom', { status: 500 }))
    const result = await uploadDataset({ name: 'x', format: 'jsonl', bodyBase64: 'eA==' })
    expect(result.kind).toBe('error')
  })
})

describe('deleteDataset — DELETE /datasets/{slug}', () => {
  it('returns kind=ok on 204', async () => {
    fetchMock.mockResolvedValue(new Response(null, { status: 204 }))
    const result = await deleteDataset('ds_abc')
    expect(result.kind).toBe('ok')
  })

  it('returns kind=conflict on 409 (battery/regression read-only)', async () => {
    fetchMock.mockResolvedValue(
      new Response('{"detail":"battery datasets are read-only"}', { status: 409 }),
    )
    const result = await deleteDataset('harmbench-v1-sample')
    expect(result.kind).toBe('conflict')
    if (result.kind === 'conflict') {
      expect(result.detail).toMatch(/battery/i)
    }
  })

  it('returns kind=not_found on 404', async () => {
    fetchMock.mockResolvedValue(new Response('{"detail":"dataset not found"}', { status: 404 }))
    const result = await deleteDataset('ghost')
    expect(result.kind).toBe('not_found')
  })

  it('returns kind=error on 500', async () => {
    fetchMock.mockResolvedValue(new Response('boom', { status: 500 }))
    const result = await deleteDataset('any')
    expect(result.kind).toBe('error')
  })
})
