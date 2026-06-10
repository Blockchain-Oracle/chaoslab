import { ReportPreview } from '@/components/artifacts/report-preview'
import { PageShell } from '@/components/ui/page-shell'

interface PageProps {
  params: Promise<{ runId: string }>
}

export default async function ReportPage({ params }: PageProps) {
  const { runId } = await params
  return (
    <PageShell label="report">
      <ReportPreview runId={runId} />
    </PageShell>
  )
}
