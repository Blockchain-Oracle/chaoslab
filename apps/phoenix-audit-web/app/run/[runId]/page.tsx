import { LiveAuditShell } from '@/components/chamber/live-audit-shell'
import { PageShell } from '@/components/ui/page-shell'

interface PageProps {
  params: Promise<{ runId: string }>
}

export default async function LiveAuditPage({ params }: PageProps) {
  const { runId } = await params
  return (
    <PageShell label="run">
      <LiveAuditShell runId={runId} />
    </PageShell>
  )
}
