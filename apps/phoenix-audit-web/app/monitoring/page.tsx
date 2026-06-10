import { MonitoringClient } from '@/components/monitoring/monitoring-client'
import { PageShell } from '@/components/ui/page-shell'
import { agentToSpec, fetchAgents, fetchRuns, fetchSchedules, runToHistoryRow } from '@/lib/api'

export const dynamic = 'force-dynamic'

export default async function MonitoringPage() {
  const [agents, schedules, runs] = await Promise.all([
    fetchAgents(),
    fetchSchedules(),
    fetchRuns(),
  ])
  return (
    <PageShell label="monitoring">
      <MonitoringClient
        agents={agents.data.map(agentToSpec)}
        schedules={schedules.data}
        scheduledRuns={runs.data.filter((r) => r.source === 'scheduled').map(runToHistoryRow)}
        liveError={schedules.liveError}
      />
    </PageShell>
  )
}
