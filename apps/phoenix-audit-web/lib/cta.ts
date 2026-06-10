// Run-audit CTA targets. The wizard (/new) is the SINGLE confirm surface —
// no control in the app starts a live run directly (story-9.10). Sample
// agents open a blank wizard: their fixture URLs must never be runnable.

export function runAuditHref(agent: { id: string; url: string; sample: boolean }): string {
  if (agent.sample) return '/new'
  return `/new?agent=${encodeURIComponent(agent.id)}&url=${encodeURIComponent(agent.url)}`
}

// "Links must be earned": sample rows always have their labeled sample
// report; real rows have a report only when one was actually signed.
export function runHasReport(run: { sample: boolean; reportAvailable?: boolean }): boolean {
  return run.sample ? true : !!run.reportAvailable
}

// Where a history row leads: the sample hero demos the replay; real runs
// open their report when it exists, else the honest run summary.
export function historyRowDest(
  run: { id: string; sample: boolean; reportAvailable?: boolean },
  heroId: string,
): string {
  if (run.sample && run.id === heroId) return '/replay'
  return runHasReport(run) ? `/report/${run.id}` : `/run/${run.id}`
}
