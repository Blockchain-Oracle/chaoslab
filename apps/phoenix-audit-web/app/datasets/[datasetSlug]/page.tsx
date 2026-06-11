import { notFound, redirect } from 'next/navigation'
import { DatasetDetailClient } from '@/components/datasets/dataset-detail-client'
import { PageShell } from '@/components/ui/page-shell'
import { fetchDatasetDetail } from '@/lib/datasets'
import { fetchProfileServer } from '@/lib/api'
import { needsOnboarding } from '@/lib/onboarding'

export const dynamic = 'force-dynamic'

interface PageProps {
  params: Promise<{ datasetSlug: string }>
}

export default async function DatasetDetailPage({ params }: PageProps) {
  const profile = await fetchProfileServer()
  if (needsOnboarding(profile.data)) redirect('/onboarding')

  const { datasetSlug } = await params
  const result = await fetchDatasetDetail(datasetSlug)

  if (result.kind === 'not_found') {
    notFound()
  }

  return (
    <PageShell label="datasets">
      <DatasetDetailClient slug={datasetSlug} result={result} />
    </PageShell>
  )
}
