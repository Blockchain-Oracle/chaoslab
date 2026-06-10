// Run-audit CTA targets. The wizard (/new) is the SINGLE confirm surface —
// no control in the app starts a live run directly (story-9.10). Sample
// agents open a blank wizard: their fixture URLs must never be runnable.

export function runAuditHref(agent: { id: string; url: string; sample: boolean }): string {
  if (agent.sample) return '/new'
  return `/new?agent=${encodeURIComponent(agent.id)}&url=${encodeURIComponent(agent.url)}`
}
