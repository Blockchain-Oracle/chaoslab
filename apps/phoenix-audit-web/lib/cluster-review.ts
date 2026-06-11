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
}

export type ReviewState =
  | { status: 'idle' }
  | { status: 'submitting' }
  | { status: 'saved'; review: ClusterReview; phoenixAnnotated: boolean }
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
): Promise<ReviewState> {
  try {
    const res = await fetchImpl(`/api/agent/runs/${runId}/clusters/${clusterId}/review`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(input),
    })
    if (!res.ok) return { status: 'failed', error: await detailOf(res) }
    const body = (await res.json()) as {
      review?: ClusterReview
      phoenix_annotated?: boolean
    }
    if (!body.review) return { status: 'failed', error: 'malformed response' }
    return {
      status: 'saved',
      review: body.review,
      phoenixAnnotated: body.phoenix_annotated === true,
    }
  } catch (err) {
    return { status: 'failed', error: err instanceof Error ? err.message : String(err) }
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
