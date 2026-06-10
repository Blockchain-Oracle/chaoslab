import { AgentDetailView } from '@/components/agents/agent-detail-view'
import { PageShell } from '@/components/ui/page-shell'

interface PageProps {
  params: Promise<{ id: string }>
}

export default async function AgentDetailPage({ params }: PageProps) {
  const { id } = await params
  return (
    <PageShell label="agent-detail">
      <AgentDetailView id={id} />
    </PageShell>
  )
}
