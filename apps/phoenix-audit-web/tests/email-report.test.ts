// Story-9.5 — "Email me this report" request + state logic. The component
// is a thin shell over these helpers (node-env vitest idiom); the states
// here ARE the button's honest sent/failed disclosure.

import { describe, expect, it, vi } from 'vitest'
import { emailButtonLabel, requestReportEmail } from '@/lib/email-report'

function fetchReturning(status: number, body: unknown) {
  return vi.fn(async () => new Response(JSON.stringify(body), { status }))
}

describe('requestReportEmail', () => {
  it('POSTs to the proxy path and returns sent state', async () => {
    const f = fetchReturning(200, { sent: true, to: 'a@example.com', attachment_included: true })
    const state = await requestReportEmail('run_abc123def456', f)
    expect(f).toHaveBeenCalledWith('/api/agent/runs/run_abc123def456/email', { method: 'POST' })
    expect(state).toEqual({ status: 'sent', to: 'a@example.com', attachmentIncluded: true })
  })

  it('discloses the link-only fallback (attachment omitted)', async () => {
    const f = fetchReturning(200, { sent: true, to: 'a@example.com', attachment_included: false })
    const state = await requestReportEmail('run_abc123def456', f)
    expect(state).toEqual({ status: 'sent', to: 'a@example.com', attachmentIncluded: false })
  })

  it('surfaces the backend detail on failure statuses', async () => {
    const f = fetchReturning(502, { detail: 'report email failed: RateLimitError' })
    const state = await requestReportEmail('run_abc123def456', f)
    expect(state).toEqual({ status: 'failed', error: expect.stringContaining('RateLimitError') })
  })

  it('maps 503 to a not-configured failure, not a crash', async () => {
    const f = fetchReturning(503, { detail: 'email delivery not configured' })
    const state = await requestReportEmail('run_abc123def456', f)
    expect(state).toEqual({ status: 'failed', error: expect.stringContaining('not configured') })
  })

  it('contains network errors as failed state', async () => {
    const f = vi.fn(async () => {
      throw new TypeError('network down')
    })
    const state = await requestReportEmail('run_abc123def456', f)
    expect(state).toEqual({ status: 'failed', error: expect.stringContaining('network down') })
  })

  it('treats an unparseable error body as failed with the HTTP status', async () => {
    const f = vi.fn(async () => new Response('<html>gateway</html>', { status: 504 }))
    const state = await requestReportEmail('run_abc123def456', f)
    expect(state).toEqual({ status: 'failed', error: expect.stringContaining('504') })
  })
})

describe('emailButtonLabel', () => {
  it('walks idle → sending → sent with the recipient named', () => {
    expect(emailButtonLabel({ status: 'idle' })).toBe('Email me this report')
    expect(emailButtonLabel({ status: 'sending' })).toBe('Sending…')
    expect(
      emailButtonLabel({ status: 'sent', to: 'a@example.com', attachmentIncluded: true }),
    ).toBe('✓ Sent to a@example.com')
  })

  it('discloses link-only sends — a judge must see the PDF was NOT attached', () => {
    expect(
      emailButtonLabel({ status: 'sent', to: 'a@example.com', attachmentIncluded: false }),
    ).toBe('✓ Sent to a@example.com (link only)')
  })

  it('failed state invites retry', () => {
    expect(emailButtonLabel({ status: 'failed', error: 'x' })).toBe('✕ Send failed — retry')
  })
})
