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
  // trap the user", so an outage falls through to the normal /audits view.
  // The profile liveError IS disclosed below so a fresh user can tell apart
  // "outage hid the gate" from "you completed onboarding."
  const profile = await fetchProfileServer()
  if (needsOnboarding(profile.data)) redirect('/onboarding')

  const [runs, agents] = await Promise.all([fetchRuns(), fetchAgents()])
  // Distinct copy for the profile case: without this Maya sees a generic
  // "runs unavailable" banner that masks the bigger problem of "we couldn't
  // verify whether you've finished onboarding."
  const liveError = profile.liveError
    ? `Couldn't verify your onboarding state (${profile.liveError}) — if this is your first sign-in, reload.`
    : (runs.liveError ?? agents.liveError)
  return (
    <PageShell label="audits">
      <AuditsClient
        rows={runs.data.map(runToHistoryRow)}
        agents={agents.data.map(agentToSpec)}
        liveError={liveError}
      />
    </PageShell>
  )
}
