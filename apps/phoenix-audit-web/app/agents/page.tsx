import { AgentsClient } from '@/components/agents/agents-client'
import { PageShell } from '@/components/ui/page-shell'
import { agentToSpec, fetchAgents } from '@/lib/api'
import { AGENTS } from '@/lib/fixtures'
import { mergeAgents } from '@/lib/sample-merge'

export const dynamic = 'force-dynamic'

export default async function AgentsPage() {
  const agents = await fetchAgents()
  const merged = mergeAgents(agents.data.map(agentToSpec), AGENTS)
  return (
    <PageShell label="agents">
      <AgentsClient agents={merged} liveError={agents.liveError} />
    </PageShell>
  )
}
