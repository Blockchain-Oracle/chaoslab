'use client'

// Story-9.17 — real GitLab connect state on settings §2. Three honest
// states: connected-as / not-connected / status-unavailable (a transport
// failure must never render as a confident "not connected").

import { useEffect, useState } from 'react'
import {
  disconnectGitLab,
  fetchGitLabStatus,
  startGitLabConnect,
  type GitLabStatus,
} from '@/lib/gitlab-connect'

type CardState =
  | { kind: 'loading' }
  | { kind: 'unavailable' }
  | { kind: 'status'; status: GitLabStatus }

export function GitLabConnectCard() {
  const [state, setState] = useState<CardState>({ kind: 'loading' })
  const [busy, setBusy] = useState(false)
  // The exchange redirect lands on /settings?gitlab=connected|error.
  const [flag] = useState<string | null>(() =>
    typeof window === 'undefined'
      ? null
      : new URLSearchParams(window.location.search).get('gitlab'),
  )

  async function refresh() {
    const status = await fetchGitLabStatus()
    setState(status === null ? { kind: 'unavailable' } : { kind: 'status', status })
  }

  useEffect(() => {
    void refresh()
  }, [])

  async function connect() {
    setBusy(true)
    const url = await startGitLabConnect()
    if (url) {
      window.location.href = url
      return
    }
    setBusy(false)
    setState({ kind: 'unavailable' })
  }

  async function disconnect() {
    setBusy(true)
    await disconnectGitLab()
    await refresh()
    setBusy(false)
  }

  return (
    <div className="card" style={{ padding: '16px 20px', marginBottom: 26 }}>
      <div className="field-label" style={{ marginBottom: 4 }}>
        GitLab merge requests
      </div>
      {flag === 'error' ? (
        <div className="mono" style={{ fontSize: 11, color: 'var(--fail)', marginBottom: 6 }}>
          ✕ GitLab connection failed — try again.
        </div>
      ) : null}
      {state.kind === 'loading' ? (
        <div className="mono muted" style={{ fontSize: 12 }}>
          Checking connection…
        </div>
      ) : state.kind === 'unavailable' ? (
        <div className="mono" style={{ fontSize: 12, color: 'var(--warn, #8a6d1a)' }}>
          ⚠ Connection status unavailable right now — reload to retry.
        </div>
      ) : state.status.connected ? (
        <div className="mono" style={{ fontSize: 12 }}>
          <span style={{ color: 'var(--pass)' }}>● Connected as @{state.status.username}</span> —
          hardening recipes can be filed as merge requests with your GitLab identity, after you
          review them.{' '}
          <button
            type="button"
            className="btn small ghost"
            style={{ marginLeft: 10 }}
            onClick={disconnect}
            disabled={busy}
          >
            Disconnect
          </button>
        </div>
      ) : (
        <div className="mono" style={{ fontSize: 12 }}>
          Connect your GitLab account to file reviewed hardening recipes as merge requests — the MR
          only ADDS files under <code>phoenix-audit/</code> in a project you choose.{' '}
          <button
            type="button"
            className="btn small"
            style={{ marginLeft: 10 }}
            onClick={connect}
            disabled={busy}
          >
            {busy ? 'Opening GitLab…' : 'Connect GitLab'}
          </button>
        </div>
      )}
    </div>
  )
}
