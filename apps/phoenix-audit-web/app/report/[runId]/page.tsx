import { ReportPreview } from '@/components/artifacts/report-preview'
import { PageShell } from '@/components/ui/page-shell'
import { fetchRunDetail } from '@/lib/api'
import { HISTORY } from '@/lib/fixtures'

export const dynamic = 'force-dynamic'

interface PageProps {
  params: Promise<{ runId: string }>
}

export default async function ReportPage({ params }: PageProps) {
  const { runId } = await params
  const isSample = HISTORY.some((r) => r.id === runId)
  if (isSample) {
    return (
      <PageShell label="report">
        <ReportPreview runId={runId} />
      </PageShell>
    )
  }
  const detail = await fetchRunDetail(runId)
  const live = detail.data
    ? {
        urls: detail.data.artifact_urls,
        errors: detail.data.artifact_url_errors,
        reportAvailable: detail.data.run.report_available,
        passed: detail.data.run.passed,
        failed: detail.data.run.failed,
        createdAt: detail.data.run.created_at,
        targetUrl: detail.data.run.target_url,
      }
    : null
  return (
    <PageShell label="report">
      <ReportPreview runId={runId} live={live} liveError={detail.liveError} />
    </PageShell>
  )
}
