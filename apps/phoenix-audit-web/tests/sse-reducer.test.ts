// Wire-protocol state reconstruction for the live audit chamber.
// The reducer is pure — (state, event, raw) → next state — so the
// regulator-demo rendering path is testable without a browser EventSource.

import { describe, expect, it } from 'vitest'
import {
  initialStreamState,
  reduceWireEvent,
  upsertProbe,
  type AuditStreamState,
} from '@/lib/sse-reducer'

function play(events: Array<[string, string]>, from?: AuditStreamState): AuditStreamState {
  let s = from ?? initialStreamState()
  for (const [event, raw] of events) {
    s = reduceWireEvent(s, event, raw).state
  }
  return s
}

describe('phase_change', () => {
  it('advances phase for valid phases', () => {
    const s = play([['phase_change', '{"phase":"judge"}']])
    expect(s.phase).toBe('judge')
  })

  it('rejects malformed JSON without mutating phase, appending an error line', () => {
    const s = play([['phase_change', '{not json']])
    expect(s.phase).toBe('queued')
    expect(s.wireLines.some((l) => l.includes('unrecognized phase value'))).toBe(true)
  })

  it('rejects unknown phase values — never an invented phase', () => {
    const s = play([['phase_change', '{"phase":"exploded"}']])
    expect(s.phase).toBe('queued')
  })

  it("'failed' sticks — no success choreography over a failed run", () => {
    const s = play([
      ['phase_change', '{"phase":"judge"}'],
      ['phase_change', '{"phase":"failed"}'],
    ])
    expect(s.phase).toBe('failed')
  })
})

describe('probe events', () => {
  it('test_started inserts a running probe; test_completed marks it done', () => {
    const s = play([
      ['test_started', '{"n":1,"fault_class":"prompt_injection"}'],
      ['test_completed', '{"n":1,"status":"ok","span_id":"abc"}'],
    ])
    expect(s.probes).toHaveLength(1)
    expect(s.probes[0]).toMatchObject({
      n: 1,
      faultClass: 'prompt_injection',
      state: 'done',
      spanId: 'abc',
    })
  })

  it('out-of-order delivery: test_completed after test_verdict must not regress done state', () => {
    const s = play([
      ['test_started', '{"n":2,"fault_class":"latency_spike"}'],
      ['test_verdict', '{"n":2,"verdict":"pass","fault_class":"latency_spike"}'],
      ['test_completed', '{"n":2,"status":"ok"}'],
    ])
    expect(s.probes).toHaveLength(1)
    expect(s.probes[0]?.state).toBe('done')
    expect(s.probes[0]?.verdict).toBe('pass')
  })

  it('unknown verdict values are logged and DROPPED — never coerced into a fail', () => {
    const s = play([
      ['test_started', '{"n":3,"fault_class":"context_poisoning"}'],
      ['test_verdict', '{"n":3,"verdict":"maybe"}'],
    ])
    expect(s.probes[0]?.verdict).toBeUndefined()
    expect(s.wireLines.some((l) => l.includes('unrecognized verdict value'))).toBe(true)
  })

  it('malformed probe JSON leaves probes untouched', () => {
    const s = play([['test_started', 'garbage']])
    expect(s.probes).toHaveLength(0)
  })

  it('upsertProbe keeps the ledger sorted by n', () => {
    const probes = upsertProbe(upsertProbe([], { n: 3, faultClass: 'x', state: 'running' }), {
      n: 1,
      faultClass: 'y',
      state: 'running',
    })
    expect(probes.map((p) => p.n)).toEqual([1, 3])
  })
})

describe('terminal events', () => {
  it('complete sets succeeded + authoritative summary and is terminal', () => {
    const { state, terminal } = reduceWireEvent(
      initialStreamState(),
      'complete',
      '{"passed":4,"failed":2,"errored":1}',
    )
    expect(terminal).toBe(true)
    expect(state.phase).toBe('succeeded')
    expect(state.summary).toEqual({ passed: 4, failed: 2, errored: 1 })
  })

  it('backend error event with data sets failed + error detail and is terminal', () => {
    const { state, terminal } = reduceWireEvent(
      initialStreamState(),
      'error',
      '{"detail":"target unreachable"}',
    )
    expect(terminal).toBe(true)
    expect(state.phase).toBe('failed')
    expect(state.error).toBe('target unreachable')
    expect(state.connected).toBe(false)
  })

  it('cancelled is terminal without inventing a success phase', () => {
    const { state, terminal } = reduceWireEvent(initialStreamState(), 'cancelled', '{}')
    expect(terminal).toBe(true)
    expect(state.phase).toBe('queued')
  })
})

describe('artifacts + resilience', () => {
  it('report_skipped surfaces the reason — never a silent missing report', () => {
    const s = play([['report_skipped', '{"reason":"signing_key_not_configured"}']])
    expect(s.report?.skippedReason).toBe('signing_key_not_configured')
  })

  it('unknown event types only append to the wire log — stream state unaffected', () => {
    const s = play([
      ['baseline', '{"whatever":1}'],
      ['phase_change', '{"phase":"injector"}'],
    ])
    expect(s.phase).toBe('injector')
    expect(s.wireLines.some((l) => l.includes('baseline'))).toBe(true)
  })

  it('wire log is bounded', () => {
    let s = initialStreamState()
    for (let i = 0; i < 600; i++) {
      s = reduceWireEvent(s, 'hello', `{"i":${i}}`).state
    }
    expect(s.wireLines.length).toBeLessThanOrEqual(500)
  })
})
