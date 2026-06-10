// Server-side auth config. Fails CLOSED naming the missing env var — a
// deploy with auth half-configured must break loudly, never serve open.
//
// No serviceAccount: on Cloud Run, next-firebase-auth-edge reads credentials
// from the environment (runtime SA needs roles/iam.serviceAccountTokenCreator
// signBlob + the IAM Service Account Credentials API — see infra/README.md).

export interface ServerAuthConfig {
  apiKey: string
  cookieName: string
  cookieSignatureKeys: string[]
  serviceAccount?: { projectId: string; clientEmail: string; privateKey: string }
}

const MIN_SIGNATURE_KEY_BYTES = 32

// Local dev has no GCP metadata server, and the library's ADC path is
// metadata-only — so off Cloud Run we hand it a projectId-bearing credential.
// VERIFY-ONLY: ID-token verification needs only Google's public certs +
// apiKey. Exception: /api/login signs a custom token and DOES need a real
// signer — which is why the full sign-in round trip only works on Cloud Run
// (keyless signBlob) and is the known local limitation in .env.example.
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
