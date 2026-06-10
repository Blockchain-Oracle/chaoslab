import { AuditsClient } from '@/components/history/audits-client'
import { PageShell } from '@/components/ui/page-shell'
import { agentToSpec, fetchAgents, fetchRuns, runToHistoryRow } from '@/lib/api'

export const dynamic = 'force-dynamic'

export default async function AuditsPage() {
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
