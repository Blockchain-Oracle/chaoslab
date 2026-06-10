import { notFound } from 'next/navigation'
import { SignatureView } from '@/components/artifacts/signature-view'
import { PageShell } from '@/components/ui/page-shell'
import { fetchArtifactJson, fetchRunDetail } from '@/lib/api'
import { parseSignatureDocument } from '@/lib/report-doc'

export const dynamic = 'force-dynamic'

interface PageProps {
  params: Promise<{ runId: string }>
}

export default async function SignaturePage({ params }: PageProps) {
  const { runId } = await params
  const detail = await fetchRunDetail(runId)
  if (detail.status === 404) notFound()
  const run = detail.data?.run

  const downloadUrl = detail.data?.artifact_urls['signature.json'] ?? null
  const signErr = detail.data?.artifact_url_errors['signature.json']
  const res = downloadUrl
    ? await fetchArtifactJson(downloadUrl)
    : {
        json: null,
        error: signErr
          ? `signature.json URL signing failed (${signErr}) — reload to retry`
          : 'signature.json not in the artifact set',
      }
  const signature = res.json === null ? null : parseSignatureDocument(res.json)
  const rawJson = res.json === null ? null : JSON.stringify(res.json, null, 2)
  // Stringifying `undefined` / a non-string yields the literal text
  // "undefined" — a regulator pasting it into a verifier sees a confusing
  // "invalid PEM" failure. Shape-check the value first.
  let publicKeyPem: string | null = null
  if (res.json && typeof res.json === 'object' && 'public_key_pem' in res.json) {
    const candidate = (res.json as { public_key_pem: unknown }).public_key_pem
    if (typeof candidate === 'string' && candidate.includes('BEGIN PUBLIC KEY')) {
      publicKeyPem = candidate
    }
  }

  return (
    <PageShell label="signature">
      <SignatureView
        runId={runId}
        signature={signature}
        rawJson={rawJson}
        signatureError={
          signature === null ? (res.error ?? 'signature.json failed validation') : null
        }
        downloadUrl={downloadUrl}
        publicKeyPem={publicKeyPem}
        // Loose `== null` catches OMITTED owner_uid (deploy skew) — mirrors
        // lib/api.ts `runToHistoryRow`.
        sample={run?.owner_uid == null && Boolean(run)}
      />
    </PageShell>
  )
}
