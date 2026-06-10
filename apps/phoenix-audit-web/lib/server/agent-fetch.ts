// Server-side fetch to the phoenix-audit-agent service.
//
// The deployed agent is IAM-gated (no public invoker): on Cloud Run
// (K_SERVICE set) we mint an ID token for the agent's URL via the metadata
// server (google-auth-library). Locally there is no metadata server and the
// agent runs unauthenticated on localhost — no token attached.

import { GoogleAuth, type IdTokenClient } from 'google-auth-library'

const auth = new GoogleAuth()

// Memoized per audience: getIdTokenClient() constructs a NEW client (and its
// own token cache) per call — one metadata-server round trip on EVERY proxied
// request. A single client refreshes its own token near expiry.
const idClientByAudience = new Map<string, Promise<IdTokenClient>>()

export function agentBaseUrl(): string {
  return (process.env.AGENT_URL ?? 'http://localhost:8080').replace(/\/$/, '')
}

function onCloudRun(): boolean {
  return Boolean(process.env.K_SERVICE)
}

function idTokenClient(audience: string): Promise<IdTokenClient> {
  let client = idClientByAudience.get(audience)
  if (!client) {
    client = auth.getIdTokenClient(audience)
    // A failed mint must not be cached forever — retry on the next request.
    client.catch(() => idClientByAudience.delete(audience))
    idClientByAudience.set(audience, client)
  }
  return client
}

export async function agentAuthHeaders(): Promise<Record<string, string>> {
  if (!onCloudRun()) return {}
  const client = await idTokenClient(agentBaseUrl())
  const headers = await client.getRequestHeaders()
  const token = headers.get('Authorization')
  return token ? { Authorization: token } : {}
}

export async function agentFetch(path: string, init?: RequestInit): Promise<Response> {
  const headers = {
    ...(await agentAuthHeaders()),
    ...Object.fromEntries(new Headers(init?.headers).entries()),
  }
  return fetch(`${agentBaseUrl()}${path}`, {
    ...init,
    headers,
    cache: 'no-store',
  })
}
