// Story-9.21 — officer cluster review request + label logic. The Phoenix
// annotation outcome is DISCLOSED end-to-end ("link only" pattern from S9.5):
// a successful save with a failed annotation must render distinctly so the
// officer can retry the annotation half without losing the verdict.

import { describe, expect, it, vi } from 'vitest'
import { reviewClusterLabel, submitClusterReview } from '@/lib/cluster-review'

function fetchReturning(status: number, body: unknown) {
  return vi.fn(async () => new Response(JSON.stringify(body), { status }))
}

describe('submitClusterReview', () => {
  it('POSTs the verdict + note and parses the saved review', async () => {
    const review = {
      verdict: 'confirmed',
      note: 'verified against trace',
      reviewer_email: 'officer@corp.example',
      reviewed_at: '2026-06-11T18:30:00Z',
    }
    const f = fetchReturning(200, { review, phoenix_annotated: true })
    const state = await submitClusterReview(
      'run_abc',
      'cluster_xy',
      { verdict: 'confirmed', note: 'verified against trace' },
      f,
    )
    expect(f).toHaveBeenCalledWith('/api/agent/runs/run_abc/clusters/cluster_xy/review', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ verdict: 'confirmed', note: 'verified against trace' }),
    })
    expect(state).toEqual({ status: 'saved', review, phoenixAnnotated: true })
  })

  it('discloses partial success — review saved, Phoenix annotation FAILED', async () => {
    const review = {
      verdict: 'disputed',
      note: null,
      reviewer_email: 'officer@corp.example',
      reviewed_at: '2026-06-11T18:30:00Z',
    }
    const f = fetchReturning(200, { review, phoenix_annotated: false })
    const state = await submitClusterReview('run_abc', 'cluster_xy', { verdict: 'disputed' }, f)
    expect(state).toEqual({ status: 'saved', review, phoenixAnnotated: false })
  })

  it('surfaces backend detail on a 422 or 404', async () => {
    const f = fetchReturning(422, { detail: 'cluster_id not on this run: cluster_xy' })
    const state = await submitClusterReview('run_abc', 'cluster_xy', { verdict: 'confirmed' }, f)
    expect(state.status).toBe('failed')
    if (state.status === 'failed') expect(state.error).toContain('cluster_id')
  })

  it('contains a network failure as a failed state, never a crash', async () => {
    const f = vi.fn(async () => {
      throw new TypeError('network down')
    })
    const state = await submitClusterReview('run_abc', 'cluster_xy', { verdict: 'confirmed' }, f)
    expect(state).toEqual({ status: 'failed', error: 'network down' })
  })
})

describe('reviewClusterLabel', () => {
  it('walks idle → submitting → saved with the human verdict named', () => {
    expect(reviewClusterLabel({ status: 'idle' })).toBe('Mark CONFIRMED · DISPUTED')
    expect(reviewClusterLabel({ status: 'submitting' })).toBe('Saving…')
    expect(
      reviewClusterLabel({
        status: 'saved',
        review: {
          verdict: 'confirmed',
          note: null,
          reviewer_email: 'officer@corp.example',
          reviewed_at: '2026-06-11T18:30:00Z',
        },
        phoenixAnnotated: true,
      }),
    ).toBe('Reviewed by officer@corp.example — CONFIRMED')
  })

  it('discloses the Phoenix-annotation half explicitly when it failed', () => {
    expect(
      reviewClusterLabel({
        status: 'saved',
        review: {
          verdict: 'disputed',
          note: 'note',
          reviewer_email: 'officer@corp.example',
          reviewed_at: '2026-06-11T18:30:00Z',
        },
        phoenixAnnotated: false,
      }),
    ).toBe('Reviewed by officer@corp.example — DISPUTED (annotation pending)')
  })

  it('failed state invites retry', () => {
    expect(reviewClusterLabel({ status: 'failed', error: 'x' })).toBe('✕ Save failed — retry')
  })
})

// --- PR #120 review fixes -------------------------------------------------------

describe('submitClusterReview — prior-state preservation', () => {
  it('keeps the prior saved review when a re-submit fails (network)', async () => {
    const { submitClusterReview } = await import('@/lib/cluster-review')
    const prior = {
      status: 'saved' as const,
      review: {
        verdict: 'confirmed' as const,
        note: null,
        reviewer_email: 'officer@corp.example',
        reviewed_at: '2026-06-11T18:30:00Z',
      },
      phoenixAnnotated: true,
    }
    const f = vi.fn(async () => {
      throw new TypeError('network down')
    })
    const state = await submitClusterReview(
      'run_abc',
      'cluster_xy',
      { verdict: 'disputed' },
      f,
      prior,
    )
    expect(state).toEqual({ ...prior, retryError: 'network down' })
  })

  it('keeps the prior saved review when a re-submit gets a backend 502', async () => {
    const { submitClusterReview } = await import('@/lib/cluster-review')
    const prior = {
      status: 'saved' as const,
      review: {
        verdict: 'confirmed' as const,
        note: null,
        reviewer_email: 'officer@corp.example',
        reviewed_at: '2026-06-11T18:30:00Z',
      },
      phoenixAnnotated: false,
    }
    const f = vi.fn(
      async () => new Response(JSON.stringify({ detail: 'gateway' }), { status: 502 }),
    )
    const state = await submitClusterReview(
      'run_abc',
      'cluster_xy',
      { verdict: 'disputed' },
      f,
      prior,
    )
    expect(state).toEqual({ ...prior, retryError: 'gateway' })
  })
})

describe('retryClusterAnnotation', () => {
  it('hits the retry endpoint and reports the new outcome', async () => {
    const { retryClusterAnnotation } = await import('@/lib/cluster-review')
    const f = vi.fn(
      async () => new Response(JSON.stringify({ phoenix_annotated: true }), { status: 200 }),
    )
    const result = await retryClusterAnnotation('run_abc', 'cluster_xy', f)
    expect(result).toEqual({ ok: true })
    expect(f).toHaveBeenCalledWith(
      '/api/agent/runs/run_abc/clusters/cluster_xy/review/annotate-retry',
      { method: 'POST' },
    )
  })

  it('surfaces the backend detail on failure', async () => {
    const { retryClusterAnnotation } = await import('@/lib/cluster-review')
    const f = vi.fn(
      async () => new Response(JSON.stringify({ detail: 'phoenix down' }), { status: 502 }),
    )
    const result = await retryClusterAnnotation('run_abc', 'cluster_xy', f)
    expect(result).toEqual({ ok: false, error: 'phoenix down' })
  })
})

describe('proxy allowlist — annotate-retry path', () => {
  it('matches the retry path with a dotted cluster id', async () => {
    const dotted = /^runs\/[a-zA-Z0-9_-]+\/clusters\/[A-Za-z0-9_.-]{1,64}\/review\/annotate-retry$/
    expect(dotted.test('runs/run_abc123def456/clusters/cluster.xy/review/annotate-retry')).toBe(
      true,
    )
    expect(dotted.test('runs/run_x/clusters/cluster_01/review/annotate-retry')).toBe(true)
    expect(dotted.test('runs/run_x/clusters/cluster_01/review/extra')).toBe(false)
  })
})
