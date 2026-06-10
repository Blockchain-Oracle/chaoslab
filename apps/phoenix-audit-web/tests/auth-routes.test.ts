// Public/private route matrix (story-9.4). The landing page and the demo
// replay stay public; every product surface requires a session.

import { describe, expect, it } from 'vitest'
import { isPublicPath } from '@/lib/auth/routes'

describe('isPublicPath', () => {
  it.each([
    ['/'],
    ['/login'],
    ['/replay'],
    ['/docs'],
    ['/api/health'],
    ['/api/login'],
    ['/api/logout'],
  ])('public: %s', (path) => {
    expect(isPublicPath(path)).toBe(true)
  })

  it.each([
    ['/audits'],
    ['/agents'],
    ['/agents/agt-1'],
    ['/monitoring'],
    ['/settings'],
    ['/new'],
    ['/run/run_abc'],
    ['/report/run_abc'],
    ['/run/run_abc123def456'],
    ['/states'],
    ['/api/agent/runs'],
  ])('gated: %s', (path) => {
    expect(isPublicPath(path)).toBe(false)
  })

  it('does not treat /replay as a prefix wildcard for product routes', () => {
    // /replayXYZ is not the replay page — unknown routes default to gated.
    expect(isPublicPath('/replayxyz')).toBe(false)
  })
})

describe('safeRedirectTarget', () => {
  it('accepts same-origin relative paths', async () => {
    const { safeRedirectTarget } = await import('@/lib/auth/routes')
    expect(safeRedirectTarget('/monitoring?tab=runs')).toBe('/monitoring?tab=runs')
  })

  it.each([[null], [''], ['https://evil.example/phish'], ['//evil.example/phish'], ['/login']])(
    'falls back to /audits for %s',
    async (raw) => {
      const { safeRedirectTarget } = await import('@/lib/auth/routes')
      expect(safeRedirectTarget(raw)).toBe('/audits')
    },
  )
})
