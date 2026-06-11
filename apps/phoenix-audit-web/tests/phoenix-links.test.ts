// Story-9.21 — Phoenix UI deep-link helper. Never returns a dead link:
// any of `base`, `project`, `spanId` being absent means no link, anywhere.

import { describe, expect, it } from 'vitest'
import { phoenixSpanUrl } from '@/lib/phoenix-links'

describe('phoenixSpanUrl', () => {
  it('builds {base}/projects/{project}/spans/{spanId} when fully configured', () => {
    expect(
      phoenixSpanUrl('https://app.phoenix.arize.com/s/space', 'phoenix-audit', 'a1b2c3d4e5f60708'),
    ).toBe('https://app.phoenix.arize.com/s/space/projects/phoenix-audit/spans/a1b2c3d4e5f60708')
  })

  it('strips a trailing slash on the base so we never emit //projects', () => {
    expect(phoenixSpanUrl('https://x.example/s/space/', 'proj', 'sp')).toBe(
      'https://x.example/s/space/projects/proj/spans/sp',
    )
  })

  it('returns null when ANY of base/project/spanId is missing — never a dead link', () => {
    expect(phoenixSpanUrl(null, 'proj', 'sp')).toBeNull()
    expect(phoenixSpanUrl('https://x', null, 'sp')).toBeNull()
    expect(phoenixSpanUrl('https://x', 'proj', null)).toBeNull()
    expect(phoenixSpanUrl('https://x', 'proj', '')).toBeNull()
    expect(phoenixSpanUrl('', 'proj', 'sp')).toBeNull()
  })

  it('URL-encodes the span and project so an oddly-shaped id never breaks the path', () => {
    expect(phoenixSpanUrl('https://x', 'pro j', 'span/x')).toBe(
      'https://x/projects/pro%20j/spans/span%2Fx',
    )
  })
})
