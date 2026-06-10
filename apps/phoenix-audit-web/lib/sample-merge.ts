// Sample-world merge (locked with Abu 2026-06-10): the seeded Meridian
// fixtures stay visible — clearly labeled — alongside real persisted runs,
// so the registry never looks dead and the hot path stays real.

import type { AgentSpec, HistoryRow } from './types'

export type MergedRun = HistoryRow & { sample: boolean }
export type MergedAgent = AgentSpec & { sample: boolean }

export function mergeRuns(real: HistoryRow[], samples: HistoryRow[]): MergedRun[] {
  const tagged: MergedRun[] = [
    ...real.map((r) => ({ ...r, sample: false })),
    ...samples.map((r) => ({ ...r, sample: true })),
  ]
  // Newest first. Real runs are current-dated; the sample world is older —
  // a plain date sort keeps real work on top without special-casing.
  return tagged.sort((a, b) => (a.date < b.date ? 1 : a.date > b.date ? -1 : 0))
}

export function mergeAgents(real: AgentSpec[], samples: AgentSpec[]): MergedAgent[] {
  // A real agent with the same id as a sample replaces it (e.g. demo-target).
  const realIds = new Set(real.map((a) => a.id))
  return [
    ...real.map((a) => ({ ...a, sample: false })),
    ...samples.filter((a) => !realIds.has(a.id)).map((a) => ({ ...a, sample: true })),
  ]
}
