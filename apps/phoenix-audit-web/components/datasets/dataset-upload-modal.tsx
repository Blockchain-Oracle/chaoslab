'use client'

// Story-9.15 follow-up — UploadDatasetModal. The original UX shipped the
// upload card inline at the bottom of /datasets with a "scroll to upload"
// CTA that smooth-scrolled the page. Operators read that as broken
// ("clicking upload drags me to the bottom"), so the user explicitly
// picked the modal pattern over the inline-at-top alternative.
//
// This wrapper is intentionally thin: it reuses the existing
// DatasetUploadCard body unchanged (scan animation, validation panel,
// state machine), and only owns the modal shell + open/close lifecycle.
// The shared `ds-modal-veil` / `ds-modal` classes keep the visual idiom
// consistent with DeleteDatasetModal — operators don't see two different
// modal styles on the same page.
//
// Close behavior — three rules (PR #122 review fleet):
//   1. Backdrop click / Escape / ✕ button are all REFUSED while a parse
//      is in flight. The fetch keeps running server-side and an
//      accidental click would silently kill the UI the operator is
//      watching (silent-failure HIGH).
//   2. Successful upload closes via the parent's onUploaded callback so
//      the new row immediately appears in §S.3 with the existing
//      "Filed ✓" stamp.
//   3. role="dialog" + aria-modal="true" + autofocus on the close
//      button so screen readers + keyboard nav announce the modal and
//      Tab cycles inside.

import { useEffect, useRef, useState } from 'react'
import { DatasetUploadCard } from './dataset-upload-card'
import type { DatasetListRowDto } from '@/lib/datasets-types'

interface Props {
  onCancel: () => void
  onUploaded: (row: DatasetListRowDto) => void
}

export function DatasetUploadModal({ onCancel, onUploaded }: Props) {
  const [busy, setBusy] = useState(false)
  const closeBtnRef = useRef<HTMLButtonElement>(null)

  // Autofocus the close button on mount so the dialog is keyboard-
  // navigable from the moment it appears (accessibility findings I3/F3).
  useEffect(() => {
    closeBtnRef.current?.focus()
  }, [])

  // A close attempt that respects the busy invariant. Used by every
  // close path (backdrop, ✕ button, Escape).
  const tryClose = () => {
    if (busy) return
    onCancel()
  }

  // Owning Escape inside the modal keeps the busy guard in one place
  // (silent-failure HIGH: a parent-level Escape would close mid-parse
  // without consulting `busy` and silently kill an in-flight POST).
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') tryClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
    // tryClose is stable enough: depends only on busy, which is the
    // listener's intended re-bind trigger.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [busy])

  return (
    <div className="ds-modal-veil" onClick={tryClose}>
      <div
        className="ds-modal ds-modal-upload"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label="Upload a dataset"
      >
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 12, marginBottom: 14 }}>
          <span
            className="mono"
            style={{
              fontSize: 10,
              letterSpacing: '0.18em',
              color: 'var(--ember-deep)',
              flex: 1,
            }}
          >
            UPLOAD A DATASET
          </span>
          <button
            ref={closeBtnRef}
            onClick={tryClose}
            aria-label="Close upload dialog"
            title={busy ? 'Upload in progress — wait for it to finish before closing' : 'Close'}
            disabled={busy}
            className="ds-modal-close"
            style={{
              background: 'none',
              border: 'none',
              color: busy ? 'var(--ink-3)' : 'var(--ink-3)',
              opacity: busy ? 0.4 : 1,
              fontSize: 16,
              lineHeight: 1,
              padding: '0 2px',
              cursor: busy ? 'not-allowed' : 'pointer',
            }}
          >
            ✕
          </button>
        </div>
        <p
          className="muted"
          style={{ fontSize: 13, lineHeight: 1.55, marginBottom: 14, maxWidth: 520 }}
        >
          Drop a JSONL or CSV corpus to run as adversarial test cases. Each row needs{' '}
          <span className="mono" style={{ fontSize: 11.5 }}>
            case_id
          </span>
          ,{' '}
          <span className="mono" style={{ fontSize: 11.5 }}>
            fault_class
          </span>
          ,{' '}
          <span className="mono" style={{ fontSize: 11.5 }}>
            prompt
          </span>
          ,{' '}
          <span className="mono" style={{ fontSize: 11.5 }}>
            expected
          </span>{' '}
          and{' '}
          <span className="mono" style={{ fontSize: 11.5 }}>
            source
          </span>{' '}
          — validation runs server-side and nothing is saved until every row passes.
        </p>
        <DatasetUploadCard
          onUploaded={onUploaded}
          onStateChange={(kind) => setBusy(kind === 'parsing')}
        />
      </div>
    </div>
  )
}
