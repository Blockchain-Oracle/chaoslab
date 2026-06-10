import { redirect } from 'next/navigation'
import { FinishedRunSummary } from '@/components/chamber/finished-run-summary'
import { LiveAuditShell } from '@/components/chamber/live-audit-shell'
import { PageShell } from '@/components/ui/page-shell'
import { fetchRunDetail } from '@/lib/api'
import { HERO_RUN } from '@/lib/fixtures'

interface PageProps {
  params: Promise<{ runId: string }>
}

const TERMINAL_PHASES = new Set(['succeeded', 'failed'])

export default async function LiveAuditPage({ params }: PageProps) {
  const { runId } = await params
  // The seeded hero run has no backend stream — deep links go to the replay
  // chamber instead of an EventSource that can only error-loop.
  if (runId === HERO_RUN.id) redirect('/replay')
  // FINISHED runs have no stream left (the in-process queue is swept) — an
  // EventSource there can only say "connection lost", which reads as a
  // network problem. The registry record is the honest answer (story-9.10).
  const detail = await fetchRunDetail(runId)
  if (detail.data && TERMINAL_PHASES.has(detail.data.run.phase)) {
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
