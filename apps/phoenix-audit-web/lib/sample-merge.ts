// Sample-world policy (amended with Abu 2026-06-10, story-9.10): signed-in
// surfaces are OWN-DATA-FIRST. Samples exist behind one explicit, labeled
// "Explore sample data" affordance — never pre-filling tables or stats for
// a fresh account. /replay stays the public sample showcase.

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

export interface RealStats {
  audits: number
  withFindings: number
  passedClean: number
}

// Stat blocks count REAL work only — a fresh account reads 0, not the
// fixture world's 47. Errored-only runs are neither findings nor passes.
export function realStats(rows: MergedRun[]): RealStats {
  const real = rows.filter((r) => !r.sample)
  return {
    audits: real.length,
    withFindings: real.filter((r) => r.fail > 0).length,
    passedClean: real.filter((r) => r.fail === 0 && r.pass > 0).length,
  }
}

export function visibleRows<T extends { sample: boolean }>(rows: T[], showSamples: boolean): T[] {
  return showSamples ? rows : rows.filter((r) => !r.sample)
}

export function mergeAgents(real: AgentSpec[], samples: AgentSpec[]): MergedAgent[] {
  // A real agent with the same id as a sample replaces it (e.g. demo-target).
  const realIds = new Set(real.map((a) => a.id))
  return [
    ...real.map((a) => ({ ...a, sample: false })),
    ...samples.filter((a) => !realIds.has(a.id)).map((a) => ({ ...a, sample: true })),
  ]
}
