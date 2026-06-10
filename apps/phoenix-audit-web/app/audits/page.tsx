import { AuditsClient } from '@/components/history/audits-client'
import { PageShell } from '@/components/ui/page-shell'
import { agentToSpec, fetchAgents, fetchRuns, runToHistoryRow } from '@/lib/api'
import { AGENTS, HISTORY } from '@/lib/fixtures'
import { mergeAgents, mergeRuns } from '@/lib/sample-merge'

export const dynamic = 'force-dynamic'

export default async function AuditsPage() {
  const [runs, agents] = await Promise.all([fetchRuns(), fetchAgents()])
  const rows = mergeRuns(runs.data.map(runToHistoryRow), HISTORY)
  const agentSpecs = mergeAgents(agents.data.map(agentToSpec), AGENTS)
  return (
    <PageShell label="audits">
      <AuditsClient rows={rows} agents={agentSpecs} liveError={runs.liveError} />
    </PageShell>
  )
}
