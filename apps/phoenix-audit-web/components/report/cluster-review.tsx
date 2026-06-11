'use client'

// Story-9.21 — officer review control on a failure cluster. Thin shell over
// lib/cluster-review (request + label logic are unit-tested per the project
// idiom); this component just owns the open/closed/note-input state.

import { useState } from 'react'
import { phoenixSpanUrl } from '@/lib/phoenix-links'
import {
  retryClusterAnnotation,
  reviewClusterLabel,
  submitClusterReview,
  type ClusterReview,
  type ReviewState,
} from '@/lib/cluster-review'

interface ClusterReviewControlProps {
  runId: string
  clusterId: string
  /** When set, the existing review renders as a dated line. */
  existing: ClusterReview | null
  /** The cluster's exemplar span — drives the Phoenix deep-link. */
  spanId: string | null
  /** Phoenix UI deep-link config (from RunDetailResponse). */
  phoenixUiBase: string | null
  phoenixProject: string | null
}

export function ClusterReviewControl({
  runId,
  clusterId,
  existing,
  spanId,
  phoenixUiBase,
  phoenixProject,
}: ClusterReviewControlProps) {
  const [open, setOpen] = useState(false)
  const [note, setNote] = useState('')
  const [state, setState] = useState<ReviewState>(
    existing
      ? {
          status: 'saved',
          review: existing,
          // PR #120 review B2: hydrate from the persisted boolean — never
          // hardcode `true` on refresh, or a partial-success silently
          // upgrades to a clean confirmation on the next page load.
          phoenixAnnotated: existing.phoenix_annotated !== false,
        }
      : { status: 'idle' },
  )
  const [retrying, setRetrying] = useState(false)
  const spanHref = phoenixSpanUrl(phoenixUiBase, phoenixProject, spanId)

  async function send(verdict: 'confirmed' | 'disputed') {
    const prior = state
    setState({ status: 'submitting' })
    setState(
      await submitClusterReview(
        runId,
        clusterId,
        { verdict, note: note || undefined },
        fetch,
        prior,
      ),
    )
    setOpen(false)
  }

  async function retryAnnotation() {
    if (state.status !== 'saved') return
    setRetrying(true)
    const result = await retryClusterAnnotation(runId, clusterId)
    setRetrying(false)
    if (result.ok) {
      setState({ ...state, phoenixAnnotated: true, retryError: undefined })
    } else if (result.error) {
      setState({ ...state, retryError: result.error })
    }
  }

  return (
    <div className="cluster-review" style={{ marginTop: 14 }}>
      {state.status === 'saved' ? (
        <div className="mono" style={{ fontSize: 10.5, color: 'var(--ink-2)' }}>
          {reviewClusterLabel(state)}
          {state.review.note ? (
            <div style={{ marginTop: 4, color: 'var(--ink-3)' }}>“{state.review.note}”</div>
          ) : null}
          {spanHref ? (
            <a
              className="span-link"
              href={spanHref}
              target="_blank"
              rel="noreferrer"
              style={{ marginLeft: 10 }}
            >
              Review in Phoenix ↗
            </a>
          ) : null}
          {!state.phoenixAnnotated ? (
            <button
              type="button"
              className="btn small ghost"
              onClick={retryAnnotation}
              disabled={retrying}
              style={{ marginLeft: 10, fontSize: 10 }}
            >
              {retrying ? 'Retrying annotation…' : 'Retry annotation'}
            </button>
          ) : null}
          {state.retryError ? (
            <div style={{ marginTop: 4, color: 'var(--fail)' }}>✕ {state.retryError}</div>
          ) : null}
        </div>
      ) : open ? (
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <input
            className="text-input"
            placeholder="Optional note (≤500 chars)"
            value={note}
            maxLength={500}
            onChange={(e) => setNote(e.target.value)}
            style={{ flex: 1, minWidth: 220, padding: '6px 10px', fontSize: 12 }}
            disabled={state.status === 'submitting'}
          />
          <button
            type="button"
            className="btn small primary"
            onClick={() => send('confirmed')}
            disabled={state.status === 'submitting'}
          >
            {state.status === 'submitting' ? 'Saving…' : 'Confirm'}
          </button>
          <button
            type="button"
            className="btn small ghost"
            onClick={() => send('disputed')}
            disabled={state.status === 'submitting'}
          >
            Dispute
          </button>
          <button
            type="button"
            className="btn small ghost"
            onClick={() => setOpen(false)}
            disabled={state.status === 'submitting'}
          >
            Cancel
          </button>
        </div>
      ) : (
        <button
          type="button"
          className="btn small ghost"
          onClick={() => setOpen(true)}
          style={state.status === 'failed' ? { color: 'var(--fail)' } : undefined}
        >
          {reviewClusterLabel(state)}
        </button>
      )}
      {state.status === 'failed' ? (
        <div
          className="mono"
          style={{ fontSize: 10, color: 'var(--fail)', marginTop: 4, maxWidth: 360 }}
        >
          {state.error}
        </div>
      ) : null}
    </div>
  )
}
