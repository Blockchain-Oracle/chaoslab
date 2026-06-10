import { AuditChamber } from '@/components/chamber/audit-chamber'
import { PageShell } from '@/components/ui/page-shell'

export default function ReplayPage() {
  return (
    <PageShell label="replay">
      <AuditChamber mode="replay" />
    </PageShell>
  )
}
