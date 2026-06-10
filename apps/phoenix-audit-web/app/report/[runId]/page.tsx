import { notFound } from 'next/navigation'
import { ReportPreview } from '@/components/artifacts/report-preview'
import type { ReportPageId, ReportView } from '@/components/artifacts/report-pages'
import { PageShell } from '@/components/ui/page-shell'
import { fetchArtifactJson, fetchArtifactText, fetchRunDetail } from '@/lib/api'
import { parseRecipeMarkdown, parseReportDocument, parseSignatureDocument } from '@/lib/report-doc'

export const dynamic = 'force-dynamic'

interface PageProps {
  params: Promise<{ runId: string }>
  searchParams: Promise<{ page?: string }>
}

const PAGE_IDS = new Set(['cover', 'exec', 'tests', 'clusters', 'recipe', 'appendix'])

export default async function ReportPage({ params, searchParams }: PageProps) {
  const { runId } = await params
  const { page } = await searchParams
  const initialPage = page && PAGE_IDS.has(page) ? (page as ReportPageId) : undefined
  const detail = await fetchRunDetail(runId)
  // Authoritative "run does not exist" → 404; a registry outage (status null
  // / 5xx) falls through and is DISCLOSED via liveError instead.
  if (detail.status === 404) notFound()
  const live = detail.data
    ? {
        urls: detail.data.artifact_urls,
        errors: detail.data.artifact_url_errors,
        reportAvailable: detail.data.run.report_available,
        eventsAvailable: detail.data.run.events_available,
        sample: detail.data.run.owner_uid === null,
        passed: detail.data.run.passed,
        failed: detail.data.run.failed,
        errored: detail.data.run.errored,
        transportFailed: detail.data.run.transport_failed,
        createdAt: detail.data.run.created_at,
        targetUrl: detail.data.run.target_url,
      }
    : null

  // The preview renders REAL artifacts, fetched server-side from their
  // fresh-signed URLs. Each failure is carried independently so the page
  // can disclose exactly what is missing.
  let view: ReportView | null = null
  let reportDocError: string | null = null
  const reportUrl = live?.urls['report.json']
  if (live?.reportAvailable && reportUrl) {
    // Tell "URL signing failed for THIS artifact" apart from "the artifact
    // set never included it" — the agent surfaces the distinction in
    // artifact_url_errors. Without this thread, "Recipe markdown
    // unavailable" reads the same as "no recipe was generated" — Abu would
    // never know which (silent-failure pattern #4).
    const sigSignErr = live.errors['signature.json']
    const recipeSignErr = live.errors['recipe.md']
    const [reportRes, signatureRes, recipeRes] = await Promise.all([
      fetchArtifactJson(reportUrl),
      live.urls['signature.json']
        ? fetchArtifactJson(live.urls['signature.json'])
        : Promise.resolve({
            json: null,
            error: sigSignErr
              ? `signature.json URL signing failed (${sigSignErr}) — reload to retry`
              : 'signature.json not in artifact set',
          }),
      live.urls['recipe.md']
        ? fetchArtifactText(live.urls['recipe.md'])
        : Promise.resolve({
            text: null,
            error: recipeSignErr
              ? `recipe.md URL signing failed (${recipeSignErr}) — reload to retry`
              : null,
          }),
    ])
    const report = reportRes.json === null ? null : parseReportDocument(reportRes.json)
    if (report === null) {
      reportDocError = reportRes.error ?? 'report.json failed validation'
    } else {
      const signature =
        signatureRes.json === null ? null : parseSignatureDocument(signatureRes.json)
      view = {
        report,
        signature,
        signatureError:
          signature === null ? (signatureRes.error ?? 'signature.json failed validation') : null,
        recipeBlocks: recipeRes.text === null ? null : parseRecipeMarkdown(recipeRes.text),
        recipeError: recipeRes.error,
      }
    }
  }

  return (
    <PageShell label="report">
      <ReportPreview
        runId={runId}
        live={live}
        liveError={detail.liveError}
        view={view}
        reportDocError={reportDocError}
        initialPage={initialPage}
      />
    </PageShell>
  )
}
