'use client'

// Story-9.15 Surface S — upload card on /datasets. Validation errors
// (422 row_errors OR parse_error) render as a PERSISTENT inline panel
// (not a toast) per the brief — the operator needs to fix their file
// and re-upload.

import { useState } from 'react'
import {
  uploadDataset,
  type DatasetListRowDto,
  type UploadValidationErrorDto,
} from '@/lib/datasets'

type UploadState =
  | { kind: 'idle' }
  | { kind: 'uploading'; filename: string }
  | { kind: 'validation_error'; error: UploadValidationErrorDto; filename: string }
  | { kind: 'error'; message: string }

async function fileToBase64(file: File): Promise<string> {
  const buf = await file.arrayBuffer()
  let binary = ''
  const bytes = new Uint8Array(buf)
  for (let i = 0; i < bytes.byteLength; i += 1) binary += String.fromCharCode(bytes[i]!)
  // btoa is sync + browser-native; works in Edge/Node 22+ which the web runs on.
  return btoa(binary)
}

function detectFormat(filename: string): 'jsonl' | 'csv' | null {
  const lower = filename.toLowerCase()
  if (lower.endsWith('.csv')) return 'csv'
  if (lower.endsWith('.json') || lower.endsWith('.jsonl')) return 'jsonl'
  return null
}

interface Props {
  onUploaded(row: DatasetListRowDto): void
}

export function DatasetUploadCard({ onUploaded }: Props) {
  const [state, setState] = useState<UploadState>({ kind: 'idle' })
  const [name, setName] = useState('')

  async function onPick(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    const format = detectFormat(file.name)
    if (!format) {
      setState({ kind: 'error', message: 'File must be .json, .jsonl, or .csv' })
      return
    }
    const datasetName = name.trim() || file.name.replace(/\.(json|jsonl|csv)$/i, '')
    setState({ kind: 'uploading', filename: file.name })
    try {
      const body = await fileToBase64(file)
      const result = await uploadDataset({ name: datasetName, format, bodyBase64: body })
      if (result.kind === 'ok') {
        onUploaded(result.row)
        setName('')
        setState({ kind: 'idle' })
      } else if (result.kind === 'validation_error') {
        setState({ kind: 'validation_error', error: result.error, filename: file.name })
      } else {
        setState({ kind: 'error', message: result.message })
      }
    } catch (err) {
      setState({
        kind: 'error',
        message: err instanceof Error ? err.message : 'Upload failed',
      })
    }
  }

  return (
    <div
      style={{
        border: '1px dashed var(--hairline)',
        borderRadius: 'var(--r-lg)',
        padding: 24,
        marginBottom: 36,
      }}
    >
      <div className="mono" style={{ fontSize: 10, letterSpacing: '0.16em', marginBottom: 12 }}>
        UPLOAD A DATASET
      </div>
      <p className="muted" style={{ fontSize: 12.5, marginBottom: 14 }}>
        Each row: <code>case_id, fault_class, prompt, expected, source</code>. JSONL or CSV.
      </p>
      <input
        className="text-input"
        placeholder="Dataset name (optional — defaults to filename)"
        value={name}
        onChange={(e) => setName(e.target.value)}
        style={{ marginBottom: 12 }}
        disabled={state.kind === 'uploading'}
      />
      <input
        type="file"
        accept=".json,.jsonl,.csv"
        onChange={onPick}
        disabled={state.kind === 'uploading'}
      />
      {state.kind === 'uploading' ? (
        <div className="mono muted" style={{ fontSize: 11, marginTop: 12 }}>
          Validating + uploading {state.filename}…
        </div>
      ) : null}
      {state.kind === 'error' ? (
        <div className="auth-notice error" role="alert" style={{ marginTop: 16, fontSize: 12.5 }}>
          {state.message}
        </div>
      ) : null}
      {state.kind === 'validation_error' ? <ValidationErrorPanel error={state.error} /> : null}
    </div>
  )
}

function ValidationErrorPanel({ error }: { error: UploadValidationErrorDto }) {
  return (
    <div
      role="alert"
      style={{
        marginTop: 16,
        padding: 14,
        background: 'var(--surface-2)',
        borderLeft: '3px solid var(--ember-deep)',
      }}
    >
      <div className="serif" style={{ fontSize: 14, marginBottom: 6 }}>
        Upload didn&rsquo;t pass validation.
      </div>
      {error.parse_error ? (
        <p className="mono" style={{ fontSize: 12 }}>
          File-level: <strong>{error.parse_error}</strong>
        </p>
      ) : null}
      {error.row_errors.length > 0 ? (
        <ul style={{ listStyle: 'none', padding: 0, margin: '8px 0 0' }}>
          {error.row_errors.map((re) => (
            <li
              key={`${re.row}-${re.reason}`}
              className="mono"
              style={{ fontSize: 11.5, marginBottom: 2 }}
            >
              Row {re.row}: {re.reason}
            </li>
          ))}
        </ul>
      ) : null}
      <p className="muted" style={{ fontSize: 11.5, marginTop: 10 }}>
        Fix the rows above and re-upload. Nothing was saved.
      </p>
    </div>
  )
}
