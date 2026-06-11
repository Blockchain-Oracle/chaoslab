// Server-side auth config. Fails CLOSED naming the missing env var — a
// deploy with auth half-configured must break loudly, never serve open.
//
// On Cloud Run: omit serviceAccount; next-firebase-auth-edge falls back to
// ComputeEngineCredential, which uses the metadata server + keyless signBlob
// (runtime SA needs roles/iam.serviceAccountTokenCreator + the IAM Service
// Account Credentials API — see infra/README.md).
//
// Off Cloud Run: the library has no metadata server and its public API
// won't accept a custom credential whose getAccessToken() returns a
// gcloud-impersonated token (only ServiceAccountCredential or the metadata
// ADC path). So local sign-in is verify-only: ID-token verification with
// Google's public certs works (apiKey is enough), but /api/login fails
// because there's no signer to mint the session cookie. Preview on staging.

export interface ServerAuthConfig {
  apiKey: string
  cookieName: string
  cookieSignatureKeys: string[]
  serviceAccount?: { projectId: string; clientEmail: string; privateKey: string }
}

const MIN_SIGNATURE_KEY_BYTES = 32

function localVerifyOnlyCredential():
  | { projectId: string; clientEmail: string; privateKey: string }
  | undefined {
  if (process.env.K_SERVICE) return undefined
  const projectId = process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID
  if (!projectId) {
    throw new Error('auth is not configured: set NEXT_PUBLIC_FIREBASE_PROJECT_ID (fail-closed)')
  }
  return { projectId, clientEmail: 'verify-only@local.invalid', privateKey: '' }
}

export function serverAuthConfig(): ServerAuthConfig {
  const apiKey = process.env.NEXT_PUBLIC_FIREBASE_API_KEY
  if (!apiKey) {
    throw new Error('auth is not configured: set NEXT_PUBLIC_FIREBASE_API_KEY (fail-closed)')
  }
  const rawKeys = process.env.AUTH_COOKIE_SIGNATURE_KEYS
  if (!rawKeys) {
    throw new Error('auth is not configured: set AUTH_COOKIE_SIGNATURE_KEYS (fail-closed)')
  }
  const cookieSignatureKeys = rawKeys
    .split(',')
    .map((k) => k.trim())
    .filter(Boolean)
  if (
    cookieSignatureKeys.length === 0 ||
    cookieSignatureKeys.some((k) => k.length < MIN_SIGNATURE_KEY_BYTES)
  ) {
    throw new Error(
      `AUTH_COOKIE_SIGNATURE_KEYS entries must be at least ${MIN_SIGNATURE_KEY_BYTES} bytes`,
    )
  }
  return {
    apiKey,
    cookieName: 'AuthToken',
    cookieSignatureKeys,
    serviceAccount: localVerifyOnlyCredential(),
  }
}
