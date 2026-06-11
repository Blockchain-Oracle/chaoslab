// Story-9.21 — officer cluster review request + state logic. The Phoenix
// annotation outcome is DISCLOSED end-to-end ("link only" pattern from S9.5):
// review.saved + phoenixAnnotated=false renders distinctly so the officer
// can see a partial-success and retry the annotation half without losing
// the verdict on the run record.

type FetchLike = (url: string, init?: RequestInit) => Promise<Response>

export type ReviewVerdict = 'confirmed' | 'disputed'

export interface ClusterReview {
  verdict: ReviewVerdict
  note: string | null
  reviewer_email: string
  reviewed_at: string
  /** PR #120 review B2: persisted alongside the review on the run record so a
   *  page refresh preserves the "(annotation pending)" disclosure — never
   *  silently renders a partial-success as a clean confirmation. */
  phoenix_annotated?: boolean
}

export type ReviewState =
  | { status: 'idle' }
  | { status: 'submitting' }
  | {
      status: 'saved'
      review: ClusterReview
      phoenixAnnotated: boolean
      /** Set when a SUBSEQUENT submit failed but the prior saved state was
       *  preserved (PR #120 review HIGH-2). */
      retryError?: string
    }
  | { status: 'failed'; error: string }

export interface ReviewInput {
  verdict: ReviewVerdict
  note?: string
}

async function detailOf(res: Response): Promise<string> {
  try {
    const body = (await res.json()) as { detail?: unknown }
    if (typeof body.detail === 'string') return body.detail
  } catch {
    // non-JSON error body — the status is the message
  }
  return `HTTP ${res.status}`
}

export async function submitClusterReview(
  runId: string,
  clusterId: string,
  input: ReviewInput,
  fetchImpl: FetchLike = fetch,
  prior?: ReviewState,
): Promise<ReviewState> {
  try {
    const res = await fetchImpl(`/api/agent/runs/${runId}/clusters/${clusterId}/review`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(input),
    })
    if (!res.ok) {
      const error = await detailOf(res)
      // PR #120 review HIGH-2: a retry blip must NOT wipe a previously-
      // saved review from the UI (the backend still has it). Preserve the
      // prior saved state and surface the retry error as a sub-line.
      if (prior?.status === 'saved') return { ...prior, retryError: error }
      return { status: 'failed', error }
    }
    const body = (await res.json()) as {
      review?: ClusterReview
      phoenix_annotated?: boolean
    }
    if (!body.review) {
      const error = 'malformed response'
      if (prior?.status === 'saved') return { ...prior, retryError: error }
      return { status: 'failed', error }
    }
    return {
      status: 'saved',
      review: body.review,
      phoenixAnnotated: body.phoenix_annotated === true,
    }
  } catch (err) {
    const error = err instanceof Error ? err.message : String(err)
    if (prior?.status === 'saved') return { ...prior, retryError: error }
    return { status: 'failed', error }
  }
}

/** PR #120 review HIGH-2: re-fire JUST the Phoenix annotation half without
 *  re-writing the review record (preserves the reviewed_at audit trail).
 *  Server endpoint reads the stored review + re-runs annotate_officer_verdict. */
export async function retryClusterAnnotation(
  runId: string,
  clusterId: string,
  fetchImpl: FetchLike = fetch,
): Promise<{ ok: boolean; error?: string }> {
  try {
    const res = await fetchImpl(
      `/api/agent/runs/${runId}/clusters/${clusterId}/review/annotate-retry`,
      { method: 'POST' },
    )
    if (!res.ok) return { ok: false, error: await detailOf(res) }
    const body = (await res.json()) as { phoenix_annotated?: boolean }
    return { ok: body.phoenix_annotated === true }
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : String(err) }
  }
}

export function reviewClusterLabel(state: ReviewState): string {
  switch (state.status) {
    case 'idle':
      return 'Mark CONFIRMED · DISPUTED'
    case 'submitting':
      return 'Saving…'
    case 'saved': {
      const verdict = state.review.verdict.toUpperCase()
      const tail = state.phoenixAnnotated ? '' : ' (annotation pending)'
      return `Reviewed by ${state.review.reviewer_email} — ${verdict}${tail}`
    }
    case 'failed':
      return '✕ Save failed — retry'
  }
}
