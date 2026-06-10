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
  const signErr = detail.data?.artifact_url_errors['report.json']
  // The agent surfaces URL-signing failure as a distinct error class — telling
  // the user "X not in artifact set" when signing failed reads "give up", but
  // the right ask is "reload to retry". Thread the distinction here.
  const res = downloadUrl
    ? await fetchArtifactJson(downloadUrl)
    : {
        json: null,
        error: signErr
          ? `report.json URL signing failed (${signErr}) — reload to retry`
          : 'report.json not in the artifact set',
      }

  const jsonText = res.json === null ? null : JSON.stringify(res.json, null, 2)
  const report = res.json === null ? null : parseReportDocument(res.json)
  // Distinguish "fetch failed" from "fetch OK but schema drift" — without
  // this, the RECORD SUMMARY card silently disappears with no signal that
  // the structured view is degraded vs the raw record.
  const reportParseError =
    res.json !== null && report === null
      ? 'report.json failed schema validation — the raw record below is authoritative'
      : null

  return (
    <PageShell label="report-json">
      <JsonView
        runId={runId}
        jsonText={jsonText}
        report={report}
        jsonError={res.error}
        reportParseError={reportParseError}
        downloadUrl={downloadUrl}
        // Loose `== null` catches an OMITTED owner_uid field too (deploy
        // skew / stale cache) — mirrors the discipline in lib/api.ts
        // `runToHistoryRow`. Strict `=== null` would un-stamp samples
        // during cache-inconsistent deploys.
        sample={run?.owner_uid == null && Boolean(run)}
      />
    </PageShell>
  )
}
