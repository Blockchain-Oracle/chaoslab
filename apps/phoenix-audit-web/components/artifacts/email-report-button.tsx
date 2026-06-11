'use client'

// Story-9.5 — thin shell over lib/email-report.ts. Failure shows the
// backend detail under the button; sent state names the recipient.

import { useState } from 'react'
import type { EmailReportState } from '@/lib/email-report'
import { emailButtonLabel, requestReportEmail } from '@/lib/email-report'

export function EmailReportButton({ runId }: { runId: string }) {
  const [state, setState] = useState<EmailReportState>({ status: 'idle' })

  async function send() {
    if (state.status === 'sending' || state.status === 'sent') return
    setState({ status: 'sending' })
    setState(await requestReportEmail(runId))
  }

  return (
    <span style={{ display: 'inline-flex', flexDirection: 'column', gap: 4 }}>
      <button
        type="button"
        className="btn ghost"
        onClick={send}
        disabled={state.status === 'sending' || state.status === 'sent'}
        style={state.status === 'sent' ? { color: 'var(--pass)' } : undefined}
      >
        {emailButtonLabel(state)}
      </button>
      {state.status === 'failed' ? (
        <span className="mono" style={{ fontSize: 10, color: 'var(--fail)', maxWidth: 220 }}>
          {state.error}
        </span>
      ) : null}
    </span>
  )
}
