// The user profile is the server-side settings truth (story-9.12): the
// settings page and /new read it through these helpers, and a failed load or
// save must surface as an error tuple — never a silently-kept default.

import { afterEach, describe, expect, it, vi } from 'vitest'
import { fetchProfile, parseProfile, saveProfile } from '@/lib/profile'

const VALID = {
  uid: 'user-1',
  email: 'officer@example.com',
  org_name: null,
  framework_default: 'EU AI Act',
  hosting_pref: 'default',
  onboarded: false,
  created_at: null,
  updated_at: null,
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('parseProfile', () => {
  it('accepts a valid profile document', () => {
    const p = parseProfile(VALID)
    expect(p).not.toBeNull()
    expect(p?.framework_default).toBe('EU AI Act')
    expect(p?.hosting_pref).toBe('default')
  })

  it('rejects non-objects and missing required fields', () => {
    expect(parseProfile(null)).toBeNull()
    expect(parseProfile('nope')).toBeNull()
    expect(parseProfile({ ...VALID, uid: undefined })).toBeNull()
    expect(parseProfile({ ...VALID, framework_default: '' })).toBeNull()
  })

  it('rejects an unknown hosting_pref instead of forwarding it to the UI', () => {
    expect(parseProfile({ ...VALID, hosting_pref: 'cloud9' })).toBeNull()
  })
})

describe('fetchProfile / saveProfile', () => {
  it('returns the parsed profile on 200', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => new Response(JSON.stringify(VALID), { status: 200 })),
    )
    const { profile, error } = await fetchProfile()
    expect(error).toBeNull()
    expect(profile?.uid).toBe('user-1')
  })

  it('returns an error tuple on a non-OK status — never a fake default', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => new Response('{}', { status: 503 })),
    )
    const { profile, error } = await fetchProfile()
    expect(profile).toBeNull()
    expect(error).toMatch(/503/)
  })

  it('PATCHes only the given fields and returns the merged profile', async () => {
    const fetchMock = vi.fn(
      async () =>
        new Response(JSON.stringify({ ...VALID, framework_default: 'NIST AI RMF' }), {
          status: 200,
        }),
    )
    vi.stubGlobal('fetch', fetchMock)
    const { profile, error } = await saveProfile({ framework_default: 'NIST AI RMF' })
    expect(error).toBeNull()
    expect(profile?.framework_default).toBe('NIST AI RMF')
    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit]
    expect(url).toBe('/api/agent/profile')
    expect(init.method).toBe('PATCH')
    expect(JSON.parse(init.body as string)).toEqual({ framework_default: 'NIST AI RMF' })
  })

  it('save failure surfaces as an error tuple', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => {
        throw new Error('network down')
      }),
    )
    const { profile, error } = await saveProfile({ onboarded: true })
    expect(profile).toBeNull()
    expect(error).toMatch(/network down/)
  })

  it('a 200 with a malformed body is an error, not a profile', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => new Response(JSON.stringify({ uid: 'user-1' }), { status: 200 })),
    )
    const { profile, error } = await fetchProfile()
    expect(profile).toBeNull()
    expect(error).toMatch(/validation/)
  })
})
