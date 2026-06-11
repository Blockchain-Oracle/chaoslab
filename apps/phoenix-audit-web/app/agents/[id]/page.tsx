import { AgentDetailView } from '@/components/agents/agent-detail-view'
import { PageShell } from '@/components/ui/page-shell'
import { agentToSpec, fetchAgents, fetchRuns, runToHistoryRow } from '@/lib/api'
import { fetchDatasets } from '@/lib/datasets'

export const dynamic = 'force-dynamic'

interface PageProps {
  params: Promise<{ id: string }>
}

export default async function AgentDetailPage({ params }: PageProps) {
  const { id } = await params
  // Datasets fetch is best-effort — a transient outage in the dataset
  // service should not break the agent detail page; the regression CTA
  // simply doesn't render until the next request succeeds.
  const [agents, runs, datasets] = await Promise.all([
    fetchAgents(),
    fetchRuns(id),
    fetchDatasets(),
  ])
  const agent = agents.data.map(agentToSpec).find((a) => a.id === id)
  const regression = datasets.data.find((d) => d.kind === 'regression' && d.agent_id === id) ?? null
  return (
    <PageShell label="agent-detail">
      <AgentDetailView
        id={id}
        {...(agent ? { agent } : {})}
        runs={runs.data.map(runToHistoryRow)}
        regression={regression}
      />
    </PageShell>
  )
}
