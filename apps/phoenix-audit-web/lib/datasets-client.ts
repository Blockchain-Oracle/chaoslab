// Story-9.15 — dataset mutations from CLIENT components, via the
// same-origin /api/agent proxy (session cookie authenticates; the proxy
// mints the agent's identity headers). The server-fetch versions these
// replace lived in lib/datasets.ts and dragged next/headers into the
// client bundle — a production-build breaker.

import type {
  DeleteResult,
  UploadRequest,
  UploadResult,
  DatasetListRowDto,
  UploadValidationErrorDto,
} from './datasets-types'

export async function uploadDataset(req: UploadRequest): Promise<UploadResult> {
  try {
    const res = await fetch('/api/agent/datasets', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
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
    const res = await fetch(`/api/agent/datasets/${encodeURIComponent(slug)}`, {
      method: 'DELETE',
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
