// Story-9.5 — "Email me this report" request + state logic. Pure module so
// the honest sent/failed disclosure is unit-testable (node-env vitest);
// the button component is a thin shell over these helpers.

export type EmailReportState =
  | { status: 'idle' }
  | { status: 'sending' }
  | { status: 'sent'; to: string; attachmentIncluded: boolean }
  | { status: 'failed'; error: string }

type FetchLike = (url: string, init?: RequestInit) => Promise<Response>

export async function requestReportEmail(
  runId: string,
  fetchImpl: FetchLike = fetch,
): Promise<EmailReportState> {
  let res: Response
  try {
    res = await fetchImpl(`/api/agent/runs/${runId}/email`, { method: 'POST' })
  } catch (err) {
    return { status: 'failed', error: err instanceof Error ? err.message : String(err) }
  }
  if (!res.ok) {
    let detail = `HTTP ${res.status}`
    try {
      const body = (await res.json()) as { detail?: unknown }
      if (typeof body.detail === 'string') detail = body.detail
    } catch {
      // Non-JSON error body (gateway page) — the HTTP status is the message.
    }
    return { status: 'failed', error: detail }
  }
  const body = (await res.json()) as { to: string; attachment_included: boolean }
  return { status: 'sent', to: body.to, attachmentIncluded: body.attachment_included }
}

export function emailButtonLabel(state: EmailReportState): string {
  switch (state.status) {
    case 'idle':
      return 'Email me this report'
    case 'sending':
      return 'Sending…'
    case 'sent':
      // Link-only sends stay DISCLOSED — "sent" without the PDF attached
      // would misrepresent what landed in the inbox.
      return state.attachmentIncluded
        ? `✓ Sent to ${state.to}`
        : `✓ Sent to ${state.to} (link only)`
    case 'failed':
      return '✕ Send failed — retry'
  }
}
