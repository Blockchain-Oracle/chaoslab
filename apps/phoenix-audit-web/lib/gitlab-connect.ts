// Story-9.17 — GitLab connect/status/projects/file-MR request logic. Pure
// module so the honest state transitions are unit-testable (node-env
// vitest); the settings card + recipe button are thin shells over these.

type FetchLike = (url: string, init?: RequestInit) => Promise<Response>

export type GitLabStatus = { connected: boolean; username: string | null }

async function detailOf(res: Response): Promise<string> {
  try {
    const body = (await res.json()) as { detail?: unknown }
    if (typeof body.detail === 'string') return body.detail
  } catch {
    // Non-JSON error body — the status is the message.
  }
  return `HTTP ${res.status}`
}

export async function fetchGitLabStatus(
  fetchImpl: FetchLike = fetch,
): Promise<GitLabStatus | null> {
  // null = "status unavailable" — distinct from disconnected, so the card
  // never renders a confident "not connected" off a transport failure.
  try {
    const res = await fetchImpl('/api/agent/integrations/gitlab/status')
    if (!res.ok) return null
    const body = (await res.json()) as { connected?: unknown; username?: unknown }
    if (typeof body.connected !== 'boolean') return null
    return {
      connected: body.connected,
      username: typeof body.username === 'string' ? body.username : null,
    }
  } catch {
    return null
  }
}

export async function startGitLabConnect(fetchImpl: FetchLike = fetch): Promise<string | null> {
  try {
    const res = await fetchImpl('/api/agent/integrations/gitlab/connect')
    if (!res.ok) return null
    const body = (await res.json()) as { authorize_url?: unknown }
    return typeof body.authorize_url === 'string' ? body.authorize_url : null
  } catch {
    return null
  }
}

export async function disconnectGitLab(fetchImpl: FetchLike = fetch): Promise<boolean> {
  try {
    const res = await fetchImpl('/api/agent/integrations/gitlab/connection', { method: 'DELETE' })
    return res.ok
  } catch {
    return false
  }
}

export type GitLabProject = { id: number; path_with_namespace: string }
export type ProjectsResult = { ok: true; projects: GitLabProject[] } | { ok: false; error: string }

export async function fetchGitLabProjects(fetchImpl: FetchLike = fetch): Promise<ProjectsResult> {
  try {
    const res = await fetchImpl('/api/agent/integrations/gitlab/projects')
    if (!res.ok) return { ok: false, error: await detailOf(res) }
    const body = (await res.json()) as { projects?: GitLabProject[] }
    return { ok: true, projects: body.projects ?? [] }
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : String(err) }
  }
}

export type FileMrResult =
  | { ok: true; mrUrl: string; persisted: boolean }
  | { ok: false; error: string }

export async function fileGitLabMr(
  runId: string,
  projectId: number,
  fetchImpl: FetchLike = fetch,
): Promise<FileMrResult> {
  try {
    const res = await fetchImpl(`/api/agent/runs/${runId}/gitlab-mr`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ project_id: projectId }),
    })
    if (!res.ok) return { ok: false, error: await detailOf(res) }
    const body = (await res.json()) as { mr_url?: unknown; persisted?: unknown }
    if (typeof body.mr_url !== 'string') return { ok: false, error: 'malformed response' }
    return { ok: true, mrUrl: body.mr_url, persisted: body.persisted === true }
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : String(err) }
  }
}
