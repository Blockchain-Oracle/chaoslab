import { notFound } from 'next/navigation'
import { JsonView } from '@/components/artifacts/json-view'
import { PageShell } from '@/components/ui/page-shell'
import { fetchArtifactJson, fetchRunDetail } from '@/lib/api'
import { parseReportDocument } from '@/lib/report-doc'

export const dynamic = 'force-dynamic'

interface PageProps {
  params: Promise<{ runId: string }>
}

export default async function ReportJsonPage({ params }: PageProps) {
  const { runId } = await params
  const detail = await fetchRunDetail(runId)
  if (detail.status === 404) notFound()
  const run = detail.data?.run

  const downloadUrl = detail.data?.artifact_urls['report.json'] ?? null
  const res = downloadUrl
    ? await fetchArtifactJson(downloadUrl)
    : { json: null, error: 'report.json not in the artifact set' }

  const jsonText = res.json === null ? null : JSON.stringify(res.json, null, 2)
  const report = res.json === null ? null : parseReportDocument(res.json)

  return (
    <PageShell label="report-json">
      <JsonView
        runId={runId}
        jsonText={jsonText}
        report={report}
        jsonError={res.error}
        downloadUrl={downloadUrl}
        sample={run?.owner_uid === null}
      />
    </PageShell>
  )
}
