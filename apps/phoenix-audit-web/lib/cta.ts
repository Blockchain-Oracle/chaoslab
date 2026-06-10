// Run-audit CTA targets. The wizard (/new) is the SINGLE confirm surface —
// no control in the app starts a live run directly (story-9.10). Seeded
// sample agents are REAL deployed targets (story-9.11), so every agent row
// pre-fills the wizard with its real URL.

export function runAuditHref(agent: { id: string; url: string }): string {
  return `/new?agent=${encodeURIComponent(agent.id)}&url=${encodeURIComponent(agent.url)}`
}

// Where a history row leads: the signed report when one exists, else the
// run page (live chamber, replay, or honest summary — it decides).
export function historyRowDest(run: { id: string; reportAvailable?: boolean }): string {
  return run.reportAvailable ? `/report/${run.id}` : `/run/${run.id}`
}
