// Stat blocks count REAL account work only — seeded samples are visible in
// the table (labeled) but never inflate "your account" numbers (story-9.11).

import type { HistoryRow } from './types'

export interface RegistryStats {
  audits: number
  withFindings: number
  passedClean: number
}

// Errored-only runs are neither findings nor passes.
export function registryStats(rows: HistoryRow[]): RegistryStats {
  const real = rows.filter((r) => !r.sample)
  return {
    audits: real.length,
    withFindings: real.filter((r) => r.fail > 0).length,
    passedClean: real.filter((r) => r.fail === 0 && r.pass > 0).length,
  }
}
