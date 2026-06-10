'use client'

import { EmptyState } from '@/components/ui/empty-state'

export default function RootError({ error, reset }: { error: Error; reset: () => void }) {
  return (
    <div className="page-enter">
      <div className="shell" style={{ padding: '80px 40px 40px', maxWidth: 720 }}>
        <EmptyState
          kicker="UNEXPECTED ERROR"
          title="This page failed to render."
          body={error.message || 'An unexpected error occurred while rendering this page.'}
          action={
            <button className="btn ghost" onClick={reset}>
              Try again
            </button>
          }
        />
      </div>
    </div>
  )
}
