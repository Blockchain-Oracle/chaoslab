// Server-side fetch to the phoenix-audit-agent service.
//
// The deployed agent is IAM-gated (no public invoker): on Cloud Run
// (K_SERVICE set) we mint an ID token for the agent's URL via the metadata
// server (google-auth-library). Locally there is no metadata server and the
// agent runs unauthenticated on localhost — no token attached.

import { GoogleAuth } from 'google-auth-library'

const auth = new GoogleAuth()

export function agentBaseUrl(): string {
  return (process.env.AGENT_URL ?? 'http://localhost:8080').replace(/\/$/, '')
}

function onCloudRun(): boolean {
  return Boolean(process.env.K_SERVICE)
}

export async function agentAuthHeaders(): Promise<Record<string, string>> {
  if (!onCloudRun()) return {}
  const client = await auth.getIdTokenClient(agentBaseUrl())
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
