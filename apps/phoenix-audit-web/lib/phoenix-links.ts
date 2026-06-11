// Story-9.21 — Phoenix UI deep-link helper. Null in, null out: any of
// base/project/spanId missing returns null so the UI never renders a
// dead-link affordance (the same posture as story-9.5's email link rows).

export function phoenixSpanUrl(
  base: string | null | undefined,
  project: string | null | undefined,
  spanId: string | null | undefined,
): string | null {
  if (!base || !project || !spanId) return null
  const trimmed = base.replace(/\/+$/, '')
  return `${trimmed}/projects/${encodeURIComponent(project)}/spans/${encodeURIComponent(spanId)}`
}
