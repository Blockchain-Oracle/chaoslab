// Client-side helpers for the server-side settings truth (story-9.12).
// Settings and /new read/write through these; a failed load or save comes
// back as an error tuple the UI must disclose — never a silently-kept
// default dressed up as the user's saved preference.

// Single TS source for the backend's HostingPref Literal — the type and the
// runtime membership check below both derive from this list.
export const HOSTING_PREFS = ['default', 'byo'] as const
export type HostingPref = (typeof HOSTING_PREFS)[number]

export interface ProfileDto {
  uid: string
  email: string | null
  org_name: string | null
  framework_default: string
  hosting_pref: HostingPref
  onboarded: boolean
  created_at: string | null
  updated_at: string | null
}

export type ProfileUpdate = Partial<
  Pick<ProfileDto, 'org_name' | 'framework_default' | 'hosting_pref' | 'onboarded'>
>

export interface ProfileResult {
  profile: ProfileDto | null
  error: string | null
}

/** null/undefined → null; string → string; anything else is schema drift the
 *  caller must reject (silently coercing it to null would mask the drift). */
function nullableString(v: unknown): string | null | false {
  if (v == null) return null
  return typeof v === 'string' ? v : false
}

export function parseProfile(json: unknown): ProfileDto | null {
  if (typeof json !== 'object' || json === null) return null
  const o = json as Record<string, unknown>
  if (typeof o.uid !== 'string' || !o.uid) return null
  if (typeof o.framework_default !== 'string' || !o.framework_default) return null
  if (!HOSTING_PREFS.includes(o.hosting_pref as HostingPref)) return null
  if (typeof o.onboarded !== 'boolean') return null
  const email = nullableString(o.email)
  const orgName = nullableString(o.org_name)
  const createdAt = nullableString(o.created_at)
  const updatedAt = nullableString(o.updated_at)
  if (email === false || orgName === false || createdAt === false || updatedAt === false)
    return null
  return {
    uid: o.uid,
    email,
    org_name: orgName,
    framework_default: o.framework_default,
    hosting_pref: o.hosting_pref as HostingPref,
    onboarded: o.onboarded,
    created_at: createdAt,
    updated_at: updatedAt,
  }
}

async function profileRequest(init?: RequestInit): Promise<ProfileResult> {
  try {
    const res = await fetch('/api/agent/profile', { cache: 'no-store', ...init })
    if (!res.ok) return { profile: null, error: `profile API answered ${res.status}` }
    const profile = parseProfile(await res.json())
    if (!profile) return { profile: null, error: 'profile document failed validation' }
    return { profile, error: null }
  } catch (err) {
    return { profile: null, error: err instanceof Error ? err.message : String(err) }
  }
}

export async function fetchProfile(): Promise<ProfileResult> {
  return profileRequest()
}

export async function saveProfile(updates: ProfileUpdate): Promise<ProfileResult> {
  return profileRequest({
    method: 'PATCH',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(updates),
  })
}
