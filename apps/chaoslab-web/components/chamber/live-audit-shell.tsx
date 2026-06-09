'use client'

import { useAuditStream } from '@/lib/sse-bridge'
import { AuditChamber } from './audit-chamber'

interface LiveAuditShellProps {
  runId: string
}

export function LiveAuditShell({ runId }: LiveAuditShellProps) {
  const stream = useAuditStream(runId)
  return (
    <AuditChamber
      mode="live"
      demoPacing
      livePhase={stream.phase}
      clockCeiling={stream.clockCeiling}
      liveLines={stream.wireLines}
    />
  )
}
