// User identity for SERVER-side calls to the agent (story-9.4).
//
// Server components fetch the registry directly (lib/api.ts -> agentFetch),
// bypassing the /api/agent proxy — so the user's Firebase ID token must be
// attached here too. No session => no header: the backend answers 401 and
// the page shows its standard visible notice (never a silent empty list).

import { cookies } from 'next/headers'
import { getTokens } from 'next-firebase-auth-edge'
import { serverAuthConfig } from '@/lib/auth/config'

export async function userIdentityHeaders(): Promise<Record<string, string>> {
  const tokens = await getTokens(await cookies(), serverAuthConfig())
  return tokens ? { 'x-firebase-id-token': tokens.token } : {}
}
