'use client'

// Story-9.17 — review-first MR filing. The flow is deliberately two-step:
// load the user's projects, make them PICK one, then file. Failure states
// show the backend detail (not-connected 409 → points at settings).

import { useState } from 'react'
import { fetchGitLabProjects, fileGitLabMr, type GitLabProject } from '@/lib/gitlab-connect'

type State =
  | { kind: 'idle' }
  | { kind: 'loading-projects' }
  | { kind: 'picking'; projects: GitLabProject[]; chosen: number | null; filing: boolean }
  | { kind: 'filed'; mrUrl: string }
  | { kind: 'failed'; error: string }

export function GitLabFileMr({ runId, sample }: { runId: string; sample: boolean }) {
  const [state, setState] = useState<State>({ kind: 'idle' })

  // Shared specimens are viewable by everyone — filable by no one.
  if (sample) return null

  async function start() {
    setState({ kind: 'loading-projects' })
    const result = await fetchGitLabProjects()
    if (!result.ok) {
      setState({ kind: 'failed', error: result.error })
      return
    }
    if (result.projects.length === 0) {
      setState({ kind: 'failed', error: 'no GitLab projects with Developer access found' })
      return
    }
    setState({ kind: 'picking', projects: result.projects, chosen: null, filing: false })
  }

  async function file() {
    if (state.kind !== 'picking' || state.chosen === null || state.filing) return
    setState({ ...state, filing: true })
    const result = await fileGitLabMr(runId, state.chosen)
    setState(
      result.ok ? { kind: 'filed', mrUrl: result.mrUrl } : { kind: 'failed', error: result.error },
    )
  }

  if (state.kind === 'filed') {
    return (
      <a className="btn small ghost" href={state.mrUrl} target="_blank" rel="noreferrer">
        GitLab MR ↗
      </a>
    )
  }

  return (
    <span style={{ display: 'inline-flex', flexDirection: 'column', gap: 4 }}>
      {state.kind === 'picking' ? (
        <span style={{ display: 'inline-flex', gap: 6, alignItems: 'center' }}>
          <select
            className="mono"
            style={{ fontSize: 11, maxWidth: 220 }}
            value={state.chosen ?? ''}
            onChange={(e) =>
              setState({ ...state, chosen: e.target.value ? Number(e.target.value) : null })
            }
          >
            <option value="">choose a project…</option>
            {state.projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.path_with_namespace}
              </option>
            ))}
          </select>
          <button
            type="button"
            className="btn small"
            onClick={file}
            disabled={state.chosen === null || state.filing}
          >
            {state.filing ? 'Filing…' : 'File MR'}
          </button>
        </span>
      ) : (
        <button
          type="button"
          className="btn small ghost"
          onClick={start}
          disabled={state.kind === 'loading-projects'}
        >
          {state.kind === 'loading-projects'
            ? 'Loading projects…'
            : state.kind === 'failed'
              ? 'File as GitLab MR — retry'
              : 'File as GitLab MR'}
        </button>
      )}
      {state.kind === 'failed' ? (
        <span className="mono" style={{ fontSize: 10, color: 'var(--fail)', maxWidth: 240 }}>
          {state.error}
        </span>
      ) : null}
    </span>
  )
}
