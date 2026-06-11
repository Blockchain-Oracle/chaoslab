import { redirect } from 'next/navigation'
import { AuditsClient } from '@/components/history/audits-client'
import { PageShell } from '@/components/ui/page-shell'
import { agentToSpec, fetchAgents, fetchProfileServer, fetchRuns, runToHistoryRow } from '@/lib/api'
import { needsOnboarding } from '@/lib/onboarding'

export const dynamic = 'force-dynamic'

export default async function AuditsPage() {
  // The profile fetch happens FIRST (a fresh sign-in must land in the wizard
  // before seeing the sample-loaded audits page); a failed fetch returns
  // null which `needsOnboarding` treats as "not onboarded? unknown — do not
  // trap the user", so an outage falls through to the normal /audits view
  // where its own liveError surface discloses the problem.
  const profile = await fetchProfileServer()
  if (needsOnboarding(profile.data)) redirect('/onboarding')

  const [runs, agents] = await Promise.all([fetchRuns(), fetchAgents()])
  return (
    <PageShell label="audits">
      <AuditsClient
        rows={runs.data.map(runToHistoryRow)}
        agents={agents.data.map(agentToSpec)}
        liveError={runs.liveError ?? agents.liveError}
      />
    </PageShell>
  )
}
