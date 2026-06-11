// Story-9.15 — SERVER-side fetchers for the /datasets pages. Imports
// next/headers + google-auth-library via the server fetch helpers, so this
// module must only ever be imported from server components / route handlers.
// Client components: types from lib/datasets-types, mutations from
// lib/datasets-client (via the /api/agent proxy).

import { agentFetch } from './server/agent-fetch'
import { userIdentityHeaders } from './server/user-fetch'
import type { Live } from './api'
import type {
  DatasetDetailDto,
  DatasetDetailResult,
  DatasetListRowDto,
  DatasetUnavailableDto,
} from './datasets-types'

// Server pages import their wire types from here (pre-split callers);
// the types live in datasets-types so client components never touch this
// server-only module.
export type {
  DatasetDetailDto,
  DatasetDetailResult,
  DatasetItemDto,
  DatasetKind,
  DatasetListRowDto,
  DatasetUnavailableDto,
  UploadValidationErrorDto,
} from './datasets-types'

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
