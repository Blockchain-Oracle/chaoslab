'use client'

// Story-9.15 Surface S — UploadCard (S-3) + ValidationErrorPanel (S-7).
// Ported from designer prototype (Phoenix Audit(4)/js/datasets.jsx).
//
// Designer's mock used a simulated scan animation; we drive the same
// animation from REAL backend round-trip latency so the operator sees
// the same affordance. The validation panel is PERSISTENT (not a toast)
// per the brief — the operator needs to read the rejected rows, fix
// their file, and re-upload.
//
// Two distinct error shapes from the wire 422:
//   - parse_error → whole file rejected (malformed JSON / missing column)
//   - row_errors  → file parsed but per-row validation failed
//
// Both block the upload; nothing is persisted unless every row passes.

import { useRef, useState, type ChangeEvent, type DragEvent } from 'react'
import { uploadDataset } from '@/lib/datasets-client'
import type { DatasetListRowDto, UploadValidationErrorDto } from '@/lib/datasets-types'
import { approxRowCount, detectFormat } from '@/lib/dataset-upload'

type UploadState =
  | { kind: 'idle' }
  | { kind: 'parsing'; filename: string; total: number; scanned: number }
  | { kind: 'validation_error'; error: UploadValidationErrorDto; filename: string }
  | { kind: 'error'; message: string }

async function fileToBase64(file: File): Promise<string> {
  const buf = await file.arrayBuffer()
  let binary = ''
  const bytes = new Uint8Array(buf)
  for (let i = 0; i < bytes.byteLength; i += 1) binary += String.fromCharCode(bytes[i]!)
  return btoa(binary)
}

interface Props {
  onUploaded(row: DatasetListRowDto): void
}

export function DatasetUploadCard({ onUploaded }: Props) {
  const [state, setState] = useState<UploadState>({ kind: 'idle' })
  const [armed, setArmed] = useState(false)
  const [flash, setFlash] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const scanTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const stopScan = () => {
    if (scanTimerRef.current !== null) {
      clearInterval(scanTimerRef.current)
      scanTimerRef.current = null
    }
  }

  const startScanAnimation = (filename: string, total: number) => {
    stopScan()
    setState({ kind: 'parsing', filename, total, scanned: 0 })
    const step = Math.max(1, Math.round(total / 46))
    scanTimerRef.current = setInterval(() => {
      setState((prev) => {
        if (prev.kind !== 'parsing') return prev
        const next = Math.min(total, prev.scanned + step)
        if (next >= total) stopScan()
        return { ...prev, scanned: next }
      })
    }, 55)
  }

  const handleFile = async (file: File) => {
    // Guard against a second drop/pick landing while the first POST is
    // still in flight — otherwise the in-flight upload's `stopScan()`
    // would kill the new file's scan animation when the earlier promise
    // resolves. The file-picker and drop both reach here.
    if (state.kind === 'parsing') return
    const format = detectFormat(file.name)
    if (!format) {
      setState({
        kind: 'error',
        message: `${file.name} must be .json, .jsonl, or .csv`,
      })
      return
    }
    const text = await file.text()
    const total = approxRowCount(text)
    startScanAnimation(file.name, total)
    const datasetName = file.name.replace(/\.(json|jsonl|csv)$/i, '')

    try {
      const body = await fileToBase64(file)
      const result = await uploadDataset({ name: datasetName, format, bodyBase64: body })
      stopScan()
      if (result.kind === 'ok') {
        onUploaded(result.row)
        setState({ kind: 'idle' })
        setFlash(true)
        setTimeout(() => setFlash(false), 2400)
      } else if (result.kind === 'validation_error') {
        setState({ kind: 'validation_error', error: result.error, filename: file.name })
      } else {
        setState({ kind: 'error', message: result.message })
      }
    } catch (err) {
      stopScan()
      setState({
        kind: 'error',
        message: err instanceof Error ? err.message : 'Upload failed',
      })
    }
  }

  const onPick = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (file) void handleFile(file)
  }

  const onDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setArmed(false)
    if (state.kind === 'parsing') return
    const file = e.dataTransfer.files[0]
    if (file) void handleFile(file)
  }

  const cancel = () => {
    stopScan()
    setState({ kind: 'idle' })
  }

  const dismissError = () => setState({ kind: 'idle' })

  return (
    <div>
      <div
        className={'ds-drop' + (armed ? ' armed' : '') + (state.kind === 'parsing' ? ' busy' : '')}
        onDragOver={(e) => {
          e.preventDefault()
          setArmed(true)
        }}
        onDragLeave={() => setArmed(false)}
        onDrop={onDrop}
      >
        <input ref={inputRef} type="file" accept=".json,.jsonl,.csv" onChange={onPick} />
        {state.kind === 'parsing' ? (
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 12 }}>
              <span className="mono" style={{ fontSize: 12, flex: 1 }}>
                {state.filename}{' '}
                <span className="muted">
                  · validating row {state.scanned} / {state.total}…
                </span>
              </span>
              <button className="btn small ghost" onClick={cancel}>
                Stop upload
              </button>
            </div>
            <div className="ds-scan">
              <span className="fill" style={{ width: `${(state.scanned / state.total) * 100}%` }} />
            </div>
            <div
              className="mono muted"
              style={{ fontSize: 10, letterSpacing: '0.08em', marginTop: 9 }}
            >
              SERVER-SIDE VALIDATION · NOTHING IS SAVED UNTIL EVERY ROW PASSES
            </div>
          </div>
        ) : (
          <div style={{ display: 'flex', alignItems: 'center', gap: 18, flexWrap: 'wrap' }}>
            <span
              style={{ fontSize: 17, color: 'var(--ember-deep)', lineHeight: 1 }}
              aria-hidden="true"
            >
              ▲
            </span>
            <div style={{ flex: 1, minWidth: 240 }}>
              <div style={{ fontSize: 13.5, marginBottom: 3 }}>
                Drop a{' '}
                <span className="mono" style={{ fontSize: 12 }}>
                  .jsonl
                </span>{' '}
                /{' '}
                <span className="mono" style={{ fontSize: 12 }}>
                  .csv
                </span>{' '}
                corpus here — or{' '}
                <button
                  onClick={() => inputRef.current?.click()}
                  style={{
                    background: 'none',
                    border: 'none',
                    padding: 0,
                    font: 'inherit',
                    color: 'var(--ember-deep)',
                    borderBottom: '1px dotted var(--ember-deep)',
                    cursor: 'pointer',
                  }}
                >
                  browse
                </button>
                .
                {flash ? (
                  <span
                    className="stamp pass ds-filed-flash"
                    style={{ marginLeft: 10, fontSize: 8.5 }}
                  >
                    Filed ✓
                  </span>
                ) : null}
              </div>
              <div className="mono muted" style={{ fontSize: 10.5, letterSpacing: '0.04em' }}>
                each row: case_id · fault_class · prompt · expected · source — severity, notes
                optional
              </div>
            </div>
          </div>
        )}
      </div>
      {state.kind === 'validation_error' ? (
        <ValidationErrorPanel
          filename={state.filename}
          error={state.error}
          onDismiss={dismissError}
        />
      ) : null}
      {state.kind === 'error' ? (
        <div role="alert" className="auth-notice error" style={{ marginTop: 16, fontSize: 12.5 }}>
          {state.message}
        </div>
      ) : null}
    </div>
  )
}

function ValidationErrorPanel({
  filename,
  error,
  onDismiss,
}: {
  filename: string
  error: UploadValidationErrorDto
  onDismiss: () => void
}) {
  const isParse = Boolean(error.parse_error)
  return (
    <div className="ds-errpanel" role="alert">
      <div style={{ display: 'flex', gap: 12, alignItems: 'baseline' }}>
        <span
          className="mono"
          style={{
            fontSize: 10,
            letterSpacing: '0.16em',
            color: 'var(--fail)',
            whiteSpace: 'nowrap',
          }}
        >
          {isParse ? '✕ FILE REJECTED' : '✕ ROWS REJECTED'}
        </span>
        <span
          style={{
            fontSize: 13,
            lineHeight: 1.6,
            flex: 1,
            color: 'var(--ink)',
          }}
        >
          {isParse ? (
            <>
              <strong>{filename}</strong> isn&rsquo;t valid — nothing could be parsed. This is a
              whole-file problem, not a row problem: fix the file format, then drop it again.
            </>
          ) : (
            <>
              <strong>{filename}</strong> is well-formed, but {error.row_errors.length} row
              {error.row_errors.length === 1 ? '' : 's'} failed validation. Nothing was saved — fix
              these rows in your source file and drop it again.
            </>
          )}
        </span>
        <button
          onClick={onDismiss}
          aria-label="Dismiss validation errors"
          title="Dismiss"
          style={{
            background: 'none',
            border: 'none',
            color: 'var(--fail)',
            fontSize: 14,
            lineHeight: 1,
            padding: '0 2px',
            cursor: 'pointer',
          }}
        >
          ✕
        </button>
      </div>

      {isParse ? (
        <div style={{ marginTop: 12 }}>
          <div className="err-row" style={{ borderTop: 'none', padding: '0 0 4px' }}>
            <span className="mono" style={{ fontSize: 10.5, color: 'var(--fail)' }}>
              file
            </span>
            <span style={{ fontSize: 12.5, color: 'var(--ink-2)' }}>{error.parse_error}</span>
          </div>
          <div
            className="mono muted"
            style={{ fontSize: 10, letterSpacing: '0.08em', marginTop: 12 }}
          >
            EXPECTED — ONE JSON OBJECT PER LINE:
          </div>
          <pre className="raw" style={{ marginTop: 6 }}>
            {
              '{"case_id":"mm-001","fault_class":"prompt_injection","prompt":"…","expected":"…","source":"internal-redteam-2026Q1"}'
            }
          </pre>
        </div>
      ) : (
        <div style={{ marginTop: 10 }}>
          {error.row_errors.map((r) => (
            <div key={`${r.row}-${r.reason}`} className="err-row">
              <span
                className="mono"
                style={{ fontSize: 10.5, color: 'var(--fail)', whiteSpace: 'nowrap' }}
              >
                row {r.row}
              </span>
              <span style={{ fontSize: 12.5, color: 'var(--ink)' }}>{r.reason}</span>
            </div>
          ))}
          <div
            className="mono muted"
            style={{ fontSize: 10, letterSpacing: '0.06em', marginTop: 10 }}
          >
            VALID fault_class VALUES: prompt_injection · context_poisoning · malformed_tool_output ·
            latency_spike
          </div>
        </div>
      )}
    </div>
  )
}
