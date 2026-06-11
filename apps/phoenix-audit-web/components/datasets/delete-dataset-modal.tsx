'use client'

// Story-9.15 Surface S — DeleteDatasetModal (S-11). Forensic copy
// borrowed from the designer prototype but rewired to call the real
// DELETE /datasets/{id} endpoint. The tradeoff is named explicitly:
// signed PDFs of past audits stay valid (signatures don't break), but
// the rows themselves can't be recovered from Phoenix Audit — the
// operator's source file is the only backup.

import { useState } from 'react'
import { deleteDataset } from '@/lib/datasets-client'
import type { DatasetListRowDto } from '@/lib/datasets-types'
import { fmtDate } from '@/lib/format'

interface Props {
  row: DatasetListRowDto
  onCancel: () => void
  onDeleted: (deletedId: string) => void
}

type DeleteState = { kind: 'idle' } | { kind: 'deleting' } | { kind: 'error'; message: string }

export function DeleteDatasetModal({ row, onCancel, onDeleted }: Props) {
  const [state, setState] = useState<DeleteState>({ kind: 'idle' })

  const onConfirm = async () => {
    setState({ kind: 'deleting' })
    const result = await deleteDataset(row.dataset_id)
    if (result.kind === 'ok') {
      onDeleted(row.dataset_id)
      return
    }
    if (result.kind === 'conflict') {
      setState({ kind: 'error', message: result.detail })
      return
    }
    if (result.kind === 'not_found') {
      // Already gone — treat as success so the UI clears. Leave a
      // forensic trail in case the slug came from stale optimistic
      // state pointing at a dataset that never existed.
      console.warn(`[delete] dataset ${row.dataset_id} 404 — treated as success`)
      onDeleted(row.dataset_id)
      return
    }
    setState({ kind: 'error', message: result.message })
  }

  return (
    <div className="ds-modal-veil" onClick={onCancel}>
      <div
        className="ds-modal"
        onClick={(e) => e.stopPropagation()}
        role="alertdialog"
        aria-label={`Delete ${row.name}`}
      >
        <div
          className="mono"
          style={{
            fontSize: 10,
            letterSpacing: '0.18em',
            color: 'var(--fail)',
            marginBottom: 12,
          }}
        >
          DELETE UPLOADED DATASET
        </div>
        <div className="serif" style={{ fontSize: 22, marginBottom: 6 }}>
          Delete <em style={{ color: 'var(--ember-deep)' }}>{row.name}</em>?
        </div>
        <div className="mono muted" style={{ fontSize: 10.5, marginBottom: 16 }}>
          {row.dataset_id} · {row.row_count} rows · uploaded {fmtDate(row.created_at)}
        </div>
        <div style={{ borderTop: '1px solid var(--hairline)', paddingTop: 14, marginBottom: 8 }}>
          <p style={{ fontSize: 13.5, lineHeight: 1.65, marginBottom: 12 }}>
            <strong style={{ fontWeight: 600 }}>
              Finished audit reports that referenced this dataset keep their signed PDFs and remain
              valid evidence.
            </strong>{' '}
            Signatures don&rsquo;t break.
          </p>
          <p style={{ fontSize: 13.5, lineHeight: 1.65, color: 'var(--ink-2)' }}>
            What you lose — irreversibly — is the ability to <em>re-run</em> with this set: any
            audit that references it loses the reference, and this corpus can&rsquo;t be recovered
            from Phoenix Audit. Keep your source file if you may need it again.
          </p>
        </div>
        {state.kind === 'error' ? (
          <div
            role="alert"
            className="mono"
            style={{
              marginTop: 12,
              padding: '8px 12px',
              border: '1px solid var(--fail)',
              background: 'var(--fail-soft)',
              color: 'var(--fail)',
              fontSize: 11,
              borderRadius: 'var(--r)',
            }}
          >
            {state.message}
          </div>
        ) : null}
        <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end', marginTop: 18 }}>
          <button
            className="btn small ghost"
            onClick={onCancel}
            disabled={state.kind === 'deleting'}
          >
            Keep dataset
          </button>
          <button
            className="btn small danger"
            onClick={onConfirm}
            disabled={state.kind === 'deleting'}
          >
            {state.kind === 'deleting' ? 'Deleting…' : 'Delete — I kept my source file'}
          </button>
        </div>
      </div>
    </div>
  )
}
