import { AgentDetailView } from '@/components/agents/agent-detail-view'
import { PageShell } from '@/components/ui/page-shell'
import { agentToSpec, fetchAgents, fetchRuns, runToHistoryRow } from '@/lib/api'
import { AGENTS, HISTORY } from '@/lib/fixtures'
import { mergeAgents, mergeRuns } from '@/lib/sample-merge'

export const dynamic = 'force-dynamic'

interface PageProps {
  params: Promise<{ id: string }>
}

export default async function AgentDetailPage({ params }: PageProps) {
  const { id } = await params
  const [agents, runs] = await Promise.all([fetchAgents(), fetchRuns(id)])
  const merged = mergeAgents(agents.data.map(agentToSpec), AGENTS)
  const agent = merged.find((a) => a.id === id)
  const history = mergeRuns(
    runs.data.map(runToHistoryRow),
    HISTORY.filter((r) => r.agentId === id),
  )
  return (
    <PageShell label="agent-detail">
      <AgentDetailView id={id} {...(agent ? { agent } : {})} runs={history} />
    </PageShell>
  )
}
