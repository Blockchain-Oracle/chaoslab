// Client-side helpers for the server-side settings truth (story-9.12).
// Settings and /new read/write through these; a failed load or save comes
// back as an error tuple the UI must disclose — never a silently-kept
// default dressed up as the user's saved preference.

export type HostingPref = 'default' | 'byo'

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

export function parseProfile(json: unknown): ProfileDto | null {
  if (typeof json !== 'object' || json === null) return null
  const o = json as Record<string, unknown>
  if (typeof o.uid !== 'string' || !o.uid) return null
  if (typeof o.framework_default !== 'string' || !o.framework_default) return null
  if (o.hosting_pref !== 'default' && o.hosting_pref !== 'byo') return null
  if (typeof o.onboarded !== 'boolean') return null
  return {
    uid: o.uid,
    email: typeof o.email === 'string' ? o.email : null,
    org_name: typeof o.org_name === 'string' ? o.org_name : null,
    framework_default: o.framework_default,
    hosting_pref: o.hosting_pref,
    onboarded: o.onboarded,
    created_at: typeof o.created_at === 'string' ? o.created_at : null,
    updated_at: typeof o.updated_at === 'string' ? o.updated_at : null,
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
