import { AgentsClient } from '@/components/agents/agents-client'
import { PageShell } from '@/components/ui/page-shell'
import { agentToSpec, fetchAgents } from '@/lib/api'

export const dynamic = 'force-dynamic'

export default async function AgentsPage() {
  const agents = await fetchAgents()
  return (
    <PageShell label="agents">
      <AgentsClient agents={agents.data.map(agentToSpec)} liveError={agents.liveError} />
    </PageShell>
  )
}
