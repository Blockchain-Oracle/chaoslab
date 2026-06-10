// Replay = the SAME pure reducer as live, fed from the persisted timeline
// (story-9.11). Parity with live reduction is the core invariant: what the
// operator watched live IS what replay shows later.

import { describe, expect, it } from 'vitest'
import { initialStreamState, reduceWireEvent } from '@/lib/sse-reducer'
import { parseEventsDocument, replayStateAt, type RecordedFrame } from '@/lib/replay'

const FRAMES: RecordedFrame[] = [
  { t: 0.0, event: 'phase_change', data: { phase: 'injector', run_id: 'run_x' } },
  {
    t: 1.2,
    event: 'test_started',
    data: { n: 1, fault_class: 'prompt_injection', run_id: 'run_x' },
  },
  {
    t: 2.4,
    event: 'test_completed',
    data: {
      n: 1,
      fault_class: 'prompt_injection',
      status: 'ok',
      span_id: 'a'.repeat(16),
      run_id: 'run_x',
    },
  },
  { t: 3.0, event: 'phase_change', data: { phase: 'judge', run_id: 'run_x' } },
  {
    t: 4.5,
    event: 'test_verdict',
    data: { n: 1, verdict: 'fail', fault_class: 'prompt_injection', run_id: 'run_x' },
  },
  {
    t: 5.0,
    event: 'cluster_set',
    data: {
      clusters: 1,
      total_failures: 1,
      cluster_ids: ['cluster_a'],
      root_causes: ['x'],
      run_id: 'run_x',
    },
  },
  { t: 5.5, event: 'phase_change', data: { phase: 'patcher', run_id: 'run_x' } },
  { t: 7.0, event: 'recipe', data: { recipe_id: 'recipe_abcabcabcabc', run_id: 'run_x' } },
  {
    t: 8.0,
    event: 'report',
    data: {
      pdf_url: 'https://signed/report.pdf',
      json_url: 'https://signed/report.json',
      run_id: 'run_x',
    },
  },
  {
    t: 9.0,
    event: 'complete',
    data: { phase: 'succeeded', passed: 0, failed: 1, run_id: 'run_x' },
  },
]

describe('replayStateAt', () => {
  it('full-timeline fold equals sequential live reduction (parity invariant)', () => {
    let live = initialStreamState()
    for (const f of FRAMES) {
      live = reduceWireEvent(live, f.event, JSON.stringify(f.data)).state
    }
    const replay = replayStateAt(FRAMES, Infinity)
    // wireLines carry stamps that differ (live stamps are wall-clock) — the
    // SEMANTIC state must match exactly.
    expect(replay.phase).toBe(live.phase)
    expect(replay.probes).toEqual(live.probes)
    expect(replay.cluster).toEqual(live.cluster)
    expect(replay.recipe).toEqual(live.recipe)
    expect(replay.report).toEqual(live.report)
    expect(replay.summary).toEqual(live.summary)
    expect(replay.phase).toBe('succeeded')
    expect(replay.summary).toEqual({ passed: 0, failed: 1, errored: 0 })
  })

  it('scrubbing to mid-timeline applies only frames with t <= clock', () => {
    const s = replayStateAt(FRAMES, 4.6)
    expect(s.phase).toBe('judge')
    expect(s.probes).toHaveLength(1)
    expect(s.probes[0]?.verdict).toBe('fail')
    expect(s.cluster).toBeNull()
    expect(s.recipe).toBeNull()
  })

  it('t=0 applies only the first frame', () => {
    const s = replayStateAt(FRAMES, 0)
    expect(s.phase).toBe('injector')
    expect(s.probes).toHaveLength(0)
  })

  it('stamps wire lines with the recorded relative time', () => {
    const s = replayStateAt(FRAMES, 1.3)
    expect(s.wireLines[1]).toMatch(/^001\.2s {2}test_started /)
  })
})

describe('parseEventsDocument', () => {
  const doc = {
    run_id: 'run_x',
    created_at: '2026-06-10T00:00:00Z',
    duration_sec: 9.0,
    frames: FRAMES,
  }

  it('round-trips a valid document', () => {
    const parsed = parseEventsDocument(doc)
    expect(parsed?.run_id).toBe('run_x')
    expect(parsed?.frames).toHaveLength(FRAMES.length)
    expect(parsed?.duration_sec).toBe(9.0)
  })

  it('rejects malformed shapes instead of fabricating a replay', () => {
    expect(parseEventsDocument(null)).toBeNull()
    expect(parseEventsDocument({})).toBeNull()
    expect(parseEventsDocument({ ...doc, frames: 'nope' })).toBeNull()
    expect(parseEventsDocument({ ...doc, frames: [{ t: 'x', event: 1 }] })).toBeNull()
    expect(parseEventsDocument({ ...doc, frames: [] })).toBeNull()
  })
})

describe('parseEventsDocument hardening (PR #100 review)', () => {
  const doc = {
    run_id: 'run_x',
    created_at: '2026-06-10T00:00:00Z',
    duration_sec: 9.0,
    frames: FRAMES,
  }

  it('rejects non-finite t and duration', () => {
    expect(parseEventsDocument({ ...doc, duration_sec: NaN })).toBeNull()
    expect(parseEventsDocument({ ...doc, frames: [{ t: NaN, event: 'x', data: {} }] })).toBeNull()
  })

  it('sorts out-of-order frames so the fold cannot silently truncate', () => {
    const shuffled = [...FRAMES].reverse()
    const parsed = parseEventsDocument({ ...doc, frames: shuffled })
    expect(parsed?.frames.map((f) => f.t)).toEqual(FRAMES.map((f) => f.t))
  })
})
