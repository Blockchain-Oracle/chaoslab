import { FinishedRunSummary } from '@/components/chamber/finished-run-summary'
import { LiveAuditShell } from '@/components/chamber/live-audit-shell'
import { ReplayShell } from '@/components/chamber/replay-shell'
import { PageShell } from '@/components/ui/page-shell'
import { fetchEventsDocument, fetchRunDetail } from '@/lib/api'
import { runReplayLabel } from '@/lib/replay'

interface PageProps {
  params: Promise<{ runId: string }>
}

const TERMINAL_PHASES = new Set(['succeeded', 'failed'])

export default async function RunPage({ params }: PageProps) {
  const { runId } = await params
  // FINISHED runs have no stream left (the in-process queue is swept). Their
  // truth is the registry record — and, when a timeline was persisted, the
  // full wire-true replay (story-9.11).
  const detail = await fetchRunDetail(runId)
  if (detail.data && TERMINAL_PHASES.has(detail.data.run.phase)) {
    const eventsUrl = detail.data.run.events_available
      ? detail.data.artifact_urls['events.json']
      : undefined
    const doc = eventsUrl ? await fetchEventsDocument(eventsUrl) : null
    if (doc) {
      return (
        <PageShell label="replay">
          <ReplayShell doc={doc} runLabel={runReplayLabel(detail.data.run)} />
        </PageShell>
      )
    }
    return (
      <PageShell label="run">
        <FinishedRunSummary detail={detail.data} />
      </PageShell>
    )
  }
  return (
    <PageShell label="run">
      <LiveAuditShell runId={runId} />
    </PageShell>
  )
}
