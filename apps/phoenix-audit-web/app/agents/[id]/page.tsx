import { AgentDetailView } from '@/components/agents/agent-detail-view'
import { PageShell } from '@/components/ui/page-shell'
import { agentToSpec, fetchAgents, fetchRuns, runToHistoryRow } from '@/lib/api'

export const dynamic = 'force-dynamic'

interface PageProps {
  params: Promise<{ id: string }>
}

export default async function AgentDetailPage({ params }: PageProps) {
  const { id } = await params
  const [agents, runs] = await Promise.all([fetchAgents(), fetchRuns(id)])
  const agent = agents.data.map(agentToSpec).find((a) => a.id === id)
  return (
    <PageShell label="agent-detail">
      <AgentDetailView
        id={id}
        {...(agent ? { agent } : {})}
        runs={runs.data.map(runToHistoryRow)}
      />
    </PageShell>
  )
}
