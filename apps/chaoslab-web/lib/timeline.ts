// Pure t -> state derivation for the audit chamber.
// Every UI state in the live + replay chambers comes through deriveAudit(t)
// so play / pause / scrub / restart are all the same code path.

import { TESTS, TIMELINE } from './fixtures'
import type { DerivedAuditState, DerivedTestState, Phase, SseEvent } from './types'

export const clamp = (v: number, a: number, b: number): number => Math.max(a, Math.min(b, v))

export const easeIO = (p: number): number => (p < 0.5 ? 2 * p * p : 1 - Math.pow(-2 * p + 2, 2) / 2)

/** Derives complete chamber UI state from a single t (seconds since start). */
export function deriveAudit(t: number): DerivedAuditState {
  let phase: Phase = 'queued'
  for (const p of TIMELINE.phases) if (t >= p.at) phase = p.phase

  const tests: DerivedTestState[] = TESTS.map((test, i) => {
    const ev = TIMELINE.testEvents[i]
    if (!ev) throw new Error(`Timeline missing event for test ${test.n}`)
    const state: DerivedTestState['state'] =
      t >= ev.end ? 'done' : t >= ev.start ? 'running' : 'pending'
    return { ...test, state, ev }
  })

  const doneCount = tests.filter((x) => x.state === 'done').length
  const failDone = tests.filter((x) => x.state === 'done' && x.verdict === 'fail').length
  const passDone = tests.filter((x) => x.state === 'done' && x.verdict === 'pass').length

  const flipProgress = clamp((t - TIMELINE.clusterAt) / 1.6, 0, 1)
  const lastTestEvent = TIMELINE.testEvents[TIMELINE.testEvents.length - 1]
  const headerWarn = lastTestEvent ? t >= lastTestEvent.end : false
  const patcherStart = TIMELINE.phases[3]?.at ?? TIMELINE.duration
  const recipeProgress = clamp((t - (patcherStart + 0.4)) / 3.4, 0, 1)

  return {
    t,
    phase,
    tests,
    doneCount,
    passDone,
    failDone,
    flipProgress,
    headerWarn,
    recipeProgress,
    receipt: t >= TIMELINE.receiptAt,
  }
}

/** SSE event feed lines, mirroring what /stream would emit if the backend
 *  shipped per-probe events today. Sorted by `at` (seconds). */
export function buildEventLog(): SseEvent[] {
  const ev: SseEvent[] = [
    { at: 0.1, line: 'hello {"run_id":"run_9f3c2ab81d4e","status":"connected"}' },
  ]
  TIMELINE.phases.slice(1).forEach((p) =>
    ev.push({
      at: p.at,
      line:
        p.phase === 'succeeded'
          ? 'complete {"phase":"succeeded"}'
          : `phase_change {"phase":"${p.phase}"}`,
    }),
  )
  TIMELINE.testEvents.forEach((te, i) => {
    const test = TESTS[i]
    if (!test) return
    ev.push({
      at: te.start,
      line: `test_started {"n":${test.n},"citation":"${test.citation}"}`,
    })
    ev.push({
      at: te.end,
      line: `test_completed {"n":${test.n},"verdict":"${test.verdict}","span":"${test.spanId}"}`,
    })
  })
  ev.push({ at: TIMELINE.clusterAt, line: 'cluster_set {"clusters":1,"total_failures":3}' })
  ev.push({ at: TIMELINE.recipeAt, line: 'recipe {"recipe_id":"recipe_7c0d51e2a9b4"}' })
  return ev.sort((a, b) => a.at - b.at)
}

export const EVENT_LOG: SseEvent[] = buildEventLog()
