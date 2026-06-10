import { MonitoringClient } from '@/components/monitoring/monitoring-client'
import { PageShell } from '@/components/ui/page-shell'
import { agentToSpec, fetchAgents, fetchRuns, fetchSchedules, runToHistoryRow } from '@/lib/api'
import { AGENTS, HISTORY } from '@/lib/fixtures'
import { mergeAgents, mergeRuns } from '@/lib/sample-merge'

export const dynamic = 'force-dynamic'

export default async function MonitoringPage() {
  const [agents, schedules, runs] = await Promise.all([
    fetchAgents(),
    fetchSchedules(),
    fetchRuns(),
  ])
  const merged = mergeAgents(agents.data.map(agentToSpec), AGENTS)
  const scheduledRuns = mergeRuns(
    runs.data.filter((r) => r.source === 'scheduled').map(runToHistoryRow),
    HISTORY.filter((r) => r.source === 'scheduled'),
  )
  return (
    <PageShell label="monitoring">
      <MonitoringClient
        agents={merged}
        schedules={schedules.data}
        scheduledRuns={scheduledRuns}
        liveError={schedules.liveError}
      />
    </PageShell>
  )
}
