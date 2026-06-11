import { redirect } from 'next/navigation'
import { OnboardingClient } from '@/components/onboarding/onboarding-client'
import { PageShell } from '@/components/ui/page-shell'
import { fetchProfileServer } from '@/lib/api'
import { needsOnboarding } from '@/lib/onboarding'

export const dynamic = 'force-dynamic'

export default async function OnboardingPage() {
  const profile = await fetchProfileServer()
  // Already-onboarded users never see the wizard again — the gate is
  // bidirectional. A profile-fetch failure (data === null) is treated as
  // "let them see the wizard" because the server can't prove they've
  // finished; the wizard's own PATCH will then either succeed or surface
  // the same outage from its error state.
  if (profile.data !== null && !needsOnboarding(profile.data)) {
    redirect('/audits')
  }
  return (
    <PageShell label="onboarding">
      <OnboardingClient profile={profile.data} />
    </PageShell>
  )
}
