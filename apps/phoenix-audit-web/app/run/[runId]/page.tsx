import { redirect } from 'next/navigation'
import { LiveAuditShell } from '@/components/chamber/live-audit-shell'
import { PageShell } from '@/components/ui/page-shell'
import { HERO_RUN } from '@/lib/fixtures'

interface PageProps {
  params: Promise<{ runId: string }>
}

export default async function LiveAuditPage({ params }: PageProps) {
  const { runId } = await params
  // The seeded hero run has no backend stream — deep links go to the replay
  // chamber instead of an EventSource that can only error-loop.
  if (runId === HERO_RUN.id) redirect('/replay')
  return (
    <PageShell label="run">
      <LiveAuditShell runId={runId} />
    </PageShell>
  )
}
