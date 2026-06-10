// Replay from the persisted timeline (story-9.11). The fold reuses the SAME
// pure reducer as the live chamber, so replay can never diverge from what
// the operator watched live.

import { initialStreamState, reduceWireEvent, type AuditStreamState } from './sse-reducer'

export interface RecordedFrame {
  /** Seconds since run start, as recorded by the backend at emit time. */
  t: number
  event: string
  data: Record<string, unknown>
}

export interface RunEventsDocument {
  run_id: string
  created_at: string
  duration_sec: number
  frames: RecordedFrame[]
}

/** Validate the events.json shape — a malformed document yields null, never
 *  a fabricated replay. */
export function parseEventsDocument(raw: unknown): RunEventsDocument | null {
  if (typeof raw !== 'object' || raw === null) return null
  const doc = raw as Record<string, unknown>
  if (typeof doc.run_id !== 'string' || typeof doc.created_at !== 'string') return null
  // Also reject duration <= 0: a zero-length timeline would freeze the
  // playback clock and render an unusable scrubber — the summary path with a
  // disclosed load failure is the honest degradation.
  if (typeof doc.duration_sec !== 'number' || !Number.isFinite(doc.duration_sec)) return null
  if (doc.duration_sec <= 0) return null
  if (!Array.isArray(doc.frames) || doc.frames.length === 0) return null
  for (const f of doc.frames) {
    if (typeof f !== 'object' || f === null) return null
    const frame = f as Record<string, unknown>
    if (typeof frame.t !== 'number' || !Number.isFinite(frame.t)) return null
    if (typeof frame.event !== 'string') return null
    if (typeof frame.data !== 'object' || frame.data === null) return null
  }
  // Defensive sort: replayStateAt's fold breaks at the first frame.t > t, so
  // an out-of-order document would silently truncate the replay.
  const frames = (doc.frames as unknown as RecordedFrame[]).slice().sort((a, b) => a.t - b.t)
  return {
    run_id: doc.run_id,
    created_at: doc.created_at,
    duration_sec: doc.duration_sec,
    frames,
  }
}

const stamp = (t: number): string => t.toFixed(1).padStart(5, '0') + 's'

/** Fold all frames with `frame.t <= t` through the live reducer. */
export function replayStateAt(frames: RecordedFrame[], t: number): AuditStreamState {
  let state = initialStreamState()
  for (const frame of frames) {
    if (frame.t > t) break
    state = reduceWireEvent(state, frame.event, JSON.stringify(frame.data), stamp(frame.t)).state
  }
  return state
}

/** Chamber header line for a replayed run. */
export function runReplayLabel(run: {
  run_id: string
  target_url: string
  framework_label: string
  owner_uid?: string | null
}): string {
  const host = run.target_url.replace(/^https?:\/\//, '')
  const framework = run.framework_label.split('·')[0]?.trim() || run.framework_label
  const kind = run.owner_uid == null ? 'sample replay' : 'replay'
  return `${run.run_id} · ${host} · ${framework} (${kind})`
}
