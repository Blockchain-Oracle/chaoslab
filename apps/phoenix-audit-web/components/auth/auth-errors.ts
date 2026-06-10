// Firebase error codes become plain sentences (designer's Surface L copy).
// `scope: 'password'` renders as a field-level error; 'card' as auth-notice.

export interface AuthErrorNotice {
  kind: 'error' | 'warn'
  scope: 'card' | 'password'
  text: string
}

const WRONG_CREDENTIALS: AuthErrorNotice = {
  kind: 'error',
  scope: 'card',
  text: "That email and password don't match. Try again, or continue with Google.",
}

export function describeAuthError(
  code: string,
  _mode: 'signin' | 'signup',
): AuthErrorNotice | null {
  switch (code) {
    case 'auth/invalid-credential':
    case 'auth/wrong-password':
    case 'auth/user-not-found':
    case 'auth/invalid-email':
      return WRONG_CREDENTIALS
    case 'auth/email-already-in-use':
      return {
        kind: 'error',
        scope: 'card',
        text: 'An account with that email already exists — switch to Sign in.',
      }
    case 'auth/weak-password':
      return { kind: 'error', scope: 'password', text: 'Passwords need at least 12 characters.' }
    case 'auth/network-request-failed':
      return {
        kind: 'error',
        scope: 'card',
        text: "We couldn't reach Phoenix Audit. Check your connection and try again.",
      }
    case 'auth/operation-not-allowed':
    case 'auth/configuration-not-found':
      return {
        kind: 'warn',
        scope: 'card',
        text: "Google sign-in isn't available yet — use email for now.",
      }
    case 'auth/popup-closed-by-user':
    case 'auth/cancelled-popup-request':
      // The user changed their mind — that is not a failure.
      return null
    case 'auth/too-many-requests':
      return {
        kind: 'error',
        scope: 'card',
        text: 'Too many attempts — wait a moment and try again.',
      }
    default:
      return {
        kind: 'error',
        scope: 'card',
        text: 'Something went wrong signing you in. Try again, or continue with Google.',
      }
  }
}
