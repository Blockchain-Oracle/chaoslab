// Story-9.15 — typed wire shapes + fetchers for the /datasets surface.
//
// The wire contract mirrors the backend BDD: list returns scoped rows
// (no `phoenix_dataset_id` ever surfaces here), detail returns a 503
// with the index header on Phoenix outage so the UI can render a
// banner instead of erroring, upload 422 carries `parse_error` XOR
// `row_errors`, delete 204/409/404.
//
// Each fetcher returns a discriminated-union result so the caller has
// to handle every wire branch — there is no swallowed-error path.

import { agentFetch } from './server/agent-fetch'
import { userIdentityHeaders } from './server/user-fetch'
import type { Live } from './api'

export type DatasetKind = 'battery' | 'regression' | 'uploaded'

export interface DatasetListRowDto {
  dataset_id: string
  name: string
  kind: DatasetKind
  row_count: number
  source_url: string | null
  agent_id: string | null
  created_at: string
  updated_at: string
}

export interface DatasetItemDto {
  case_id: string
  fault_class: string
  prompt: string
  expected: string
  source: string
  severity: string | null
  notes: string | null
}

export interface DatasetDetailDto extends DatasetListRowDto {
  items: DatasetItemDto[]
}

/** 503 body when Phoenix is down: index header rides through so the
 *  detail page can render a banner instead of failing. */
export interface DatasetUnavailableDto extends DatasetListRowDto {
  reason: string
}

export interface UploadValidationErrorDto {
  /** Whole-file failure (malformed JSON, missing CSV column, ...). */
  parse_error: string | null
  /** Per-row failures (unknown fault_class, duplicate case_id, ...). */
  row_errors: { row: number; reason: string }[]
}

export type DatasetDetailResult =
  | { kind: 'ok'; data: DatasetDetailDto }
  | { kind: 'phoenix_outage'; header: DatasetUnavailableDto }
  | { kind: 'not_found' }
  | { kind: 'error'; message: string }

export type UploadResult =
  | { kind: 'ok'; row: DatasetListRowDto }
  | { kind: 'validation_error'; error: UploadValidationErrorDto }
  | { kind: 'error'; message: string }

export type DeleteResult =
  | { kind: 'ok' }
  | { kind: 'conflict'; detail: string }
  | { kind: 'not_found' }
  | { kind: 'error'; message: string }

async function _identityHeaders(): Promise<Record<string, string>> {
  return userIdentityHeaders() as Promise<Record<string, string>>
}

/** Scoped listing — battery + caller's uploaded + caller's regression. */
export async function fetchDatasets(): Promise<Live<DatasetListRowDto[]>> {
  try {
    const res = await agentFetch('/datasets', { headers: await _identityHeaders() })
    if (!res.ok) {
      return { data: [], liveError: `agent API ${res.status} on /datasets` }
    }
    const body = (await res.json()) as { datasets: unknown }
    if (!Array.isArray(body.datasets)) {
      return { data: [], liveError: 'agent API returned non-array datasets — contract drift' }
    }
    return { data: body.datasets as DatasetListRowDto[], liveError: null }
  } catch (err) {
    return { data: [], liveError: err instanceof Error ? err.message : String(err) }
  }
}

/** Detail with Phoenix-outage-aware result branch. */
export async function fetchDatasetDetail(slug: string): Promise<DatasetDetailResult> {
  try {
    const res = await agentFetch(`/datasets/${encodeURIComponent(slug)}`, {
      headers: await _identityHeaders(),
    })
    if (res.status === 200) {
      const data = (await res.json()) as DatasetDetailDto
      return { kind: 'ok', data }
    }
    if (res.status === 404) {
      return { kind: 'not_found' }
    }
    if (res.status === 503) {
      const header = (await res.json()) as DatasetUnavailableDto
      return { kind: 'phoenix_outage', header }
    }
    return { kind: 'error', message: `agent API ${res.status} on /datasets/${slug}` }
  } catch (err) {
    return { kind: 'error', message: err instanceof Error ? err.message : String(err) }
  }
}

export interface UploadRequest {
  name: string
  format: 'jsonl' | 'csv'
  /** base64-encoded raw bytes of the JSONL or CSV file. */
  bodyBase64: string
}

export async function uploadDataset(req: UploadRequest): Promise<UploadResult> {
  try {
    const res = await agentFetch('/datasets', {
      method: 'POST',
      headers: {
        ...(await _identityHeaders()),
        'content-type': 'application/json',
      },
      body: JSON.stringify({ name: req.name, format: req.format, body: req.bodyBase64 }),
    })
    if (res.status === 201) {
      const row = (await res.json()) as DatasetListRowDto
      return { kind: 'ok', row }
    }
    if (res.status === 422) {
      const error = (await res.json()) as UploadValidationErrorDto
      return { kind: 'validation_error', error }
    }
    return { kind: 'error', message: `agent API ${res.status} on POST /datasets` }
  } catch (err) {
    return { kind: 'error', message: err instanceof Error ? err.message : String(err) }
  }
}

export async function deleteDataset(slug: string): Promise<DeleteResult> {
  try {
    const res = await agentFetch(`/datasets/${encodeURIComponent(slug)}`, {
      method: 'DELETE',
      headers: await _identityHeaders(),
    })
    if (res.status === 204) {
      return { kind: 'ok' }
    }
    if (res.status === 409) {
      const body = (await res.json()) as { detail?: string }
      return { kind: 'conflict', detail: body.detail ?? 'dataset is read-only' }
    }
    if (res.status === 404) {
      return { kind: 'not_found' }
    }
    return { kind: 'error', message: `agent API ${res.status} on DELETE /datasets/${slug}` }
  } catch (err) {
    return { kind: 'error', message: err instanceof Error ? err.message : String(err) }
  }
}
