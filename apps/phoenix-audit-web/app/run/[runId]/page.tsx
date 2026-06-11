import { notFound } from 'next/navigation'
import { FinishedRunSummary } from '@/components/chamber/finished-run-summary'
import { LiveAuditShell } from '@/components/chamber/live-audit-shell'
import { ReplayShell } from '@/components/chamber/replay-shell'
import { EmptyState } from '@/components/ui/empty-state'
import { A } from '@/components/ui/link'
import { PageShell } from '@/components/ui/page-shell'
import { fetchEventsDocument, fetchRunDetail } from '@/lib/api'
import { runReplayLabel } from '@/lib/replay'

export const dynamic = 'force-dynamic'

interface PageProps {
  params: Promise<{ runId: string }>
}

const TERMINAL_PHASES = new Set(['succeeded', 'failed'])

export default async function RunPage({ params }: PageProps) {
  const { runId } = await params
  const detail = await fetchRunDetail(runId)
  // Authoritative "run does not exist" → 404. A registry outage is DISCLOSED —
  // opening an EventSource that can only error reads as a network problem.
  if (detail.status === 404) notFound()
  if (!detail.data) {
    return (
      <PageShell label="run">
        <div className="shell" style={{ padding: '80px 40px' }}>
          <EmptyState
            kicker="REGISTRY UNAVAILABLE"
            title="This run can't be looked up right now."
            body={`The live registry could not be reached${detail.liveError ? ` (${detail.liveError})` : ''}. Reload to retry.`}
            action={
              <A to="audits" className="btn small ghost">
                Back to the audit registry
              </A>
            }
          />
        </div>
      </PageShell>
    )
  }
  const run = detail.data.run
  // FINISHED runs have no stream left (the in-process queue is swept). Their
  // truth is the registry record — and, when a timeline was persisted, the
  // full wire-true replay (story-9.11).
  if (TERMINAL_PHASES.has(run.phase)) {
    const eventsUrl = run.events_available ? detail.data.artifact_urls['events.json'] : undefined
    const events = eventsUrl ? await fetchEventsDocument(eventsUrl) : null
    if (events?.doc) {
      return (
        <PageShell label="replay">
          <ReplayShell
            doc={events.doc}
            runLabel={runReplayLabel(run)}
            phoenixUiBase={detail.data.phoenix_ui_base ?? null}
            phoenixProject={detail.data.phoenix_project ?? null}
          />
        </PageShell>
      )
    }
    // events_available without a playable timeline = a recorded replay that
    // could not be loaded — disclosed, never "no replay exists".
    const replayError = run.events_available
      ? (events?.error ??
        detail.data.artifact_url_errors['events.json'] ??
        'signed timeline link unavailable')
      : undefined
    return (
      <PageShell label="run">
        <FinishedRunSummary detail={detail.data} {...(replayError ? { replayError } : {})} />
      </PageShell>
    )
  }
  return (
    <PageShell label="run">
      <LiveAuditShell runId={runId} />
    </PageShell>
  )
}
