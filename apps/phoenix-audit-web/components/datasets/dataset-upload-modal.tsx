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
// Auto-close: when the upload succeeds, the listing client closes the
// modal in the onUploaded callback so the operator immediately sees the
// new row land in the §S.3 uploaded section (with the existing
// "Filed ✓" stamp).

import { DatasetUploadCard } from './dataset-upload-card'
import type { DatasetListRowDto } from '@/lib/datasets-types'

interface Props {
  onCancel: () => void
  onUploaded: (row: DatasetListRowDto) => void
}

export function DatasetUploadModal({ onCancel, onUploaded }: Props) {
  return (
    <div className="ds-modal-veil" onClick={onCancel}>
      <div
        className="ds-modal ds-modal-upload"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
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
            onClick={onCancel}
            aria-label="Close upload dialog"
            title="Close"
            className="ds-modal-close"
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--ink-3)',
              fontSize: 16,
              lineHeight: 1,
              padding: '0 2px',
              cursor: 'pointer',
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
        <DatasetUploadCard onUploaded={onUploaded} />
      </div>
    </div>
  )
}
