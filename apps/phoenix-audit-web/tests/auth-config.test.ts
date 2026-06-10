// Server auth config fails CLOSED, naming the missing env var — a deploy
// with auth half-configured must break loudly, never serve an open app.

import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { serverAuthConfig } from '@/lib/auth/config'

const ENV_KEYS = [
  'NEXT_PUBLIC_FIREBASE_API_KEY',
  'AUTH_COOKIE_SIGNATURE_KEYS',
  'NEXT_PUBLIC_FIREBASE_PROJECT_ID',
] as const
const saved: Record<string, string | undefined> = {}

beforeEach(() => {
  for (const key of ENV_KEYS) saved[key] = process.env[key]
  process.env.NEXT_PUBLIC_FIREBASE_API_KEY = 'test-api-key'
  process.env.AUTH_COOKIE_SIGNATURE_KEYS = 'a'.repeat(32) + ',' + 'b'.repeat(32)
  process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID = 'proj-test'
})

afterEach(() => {
  for (const key of ENV_KEYS) {
    if (saved[key] === undefined) delete process.env[key]
    else process.env[key] = saved[key]
  }
})

describe('serverAuthConfig', () => {
  it('returns apiKey, cookie name and parsed signature keys', () => {
    const cfg = serverAuthConfig()
    expect(cfg.apiKey).toBe('test-api-key')
    expect(cfg.cookieName).toBe('AuthToken')
    expect(cfg.cookieSignatureKeys).toEqual(['a'.repeat(32), 'b'.repeat(32)])
  })

  it.each(ENV_KEYS)('throws naming %s when missing', (key) => {
    delete process.env[key]
    expect(() => serverAuthConfig()).toThrowError(new RegExp(key))
  })

  it('rejects signature keys shorter than 32 bytes', () => {
    process.env.AUTH_COOKIE_SIGNATURE_KEYS = 'short'
    expect(() => serverAuthConfig()).toThrowError(/32/)
  })

  it('off Cloud Run, supplies a verify-only projectId credential', () => {
    const cfg = serverAuthConfig()
    expect(cfg.serviceAccount?.projectId).toBe('proj-test')
    expect(cfg.serviceAccount?.privateKey).toBe('')
  })
})
