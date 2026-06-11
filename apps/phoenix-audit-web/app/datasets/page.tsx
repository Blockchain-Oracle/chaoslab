import { redirect } from 'next/navigation'
import { DatasetsListingClient } from '@/components/datasets/datasets-listing-client'
import { PageShell } from '@/components/ui/page-shell'
import { fetchDatasets } from '@/lib/datasets'
import { fetchProfileServer } from '@/lib/api'
import { needsOnboarding } from '@/lib/onboarding'

export const dynamic = 'force-dynamic'

export default async function DatasetsPage() {
  // Same onboarding gate as /audits — Maya cannot use the datasets surface
  // before completing the wizard.
  const profile = await fetchProfileServer()
  if (needsOnboarding(profile.data)) redirect('/onboarding')

  const { data, liveError } = await fetchDatasets()
  return (
    <PageShell label="datasets">
      <DatasetsListingClient rows={data} liveError={liveError} />
    </PageShell>
  )
}
