'use client'

// Firebase web SDK init for the browser. NEXT_PUBLIC_* references must stay
// literal — Next.js inlines them at build time.

import { getApps, initializeApp, type FirebaseApp } from 'firebase/app'
import { getAuth, type Auth } from 'firebase/auth'

function firebaseApp(): FirebaseApp {
  const existing = getApps()[0]
  if (existing) return existing
  const apiKey = process.env.NEXT_PUBLIC_FIREBASE_API_KEY
  const authDomain = process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN
  const projectId = process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID
  if (!apiKey || !authDomain || !projectId) {
    throw new Error(
      'auth is not configured: set NEXT_PUBLIC_FIREBASE_API_KEY / _AUTH_DOMAIN / _PROJECT_ID',
    )
  }
  return initializeApp({ apiKey, authDomain, projectId })
}

export function getFirebaseAuth(): Auth {
  return getAuth(firebaseApp())
}
