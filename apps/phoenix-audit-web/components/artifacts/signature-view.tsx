'use client'

// In-app viewer for the run's signature.json sidecar (story-9.13 round 2,
// restyled to prototype vocabulary). Header summary card with key identity →
// §1 Artifacts signed table → §2 Public key (collapsible) → §3 Verify offline
// recipe. Download / Copy actions on the page itself.

import { useState } from 'react'
import { A } from '@/components/ui/link'
import { PageFoot } from '@/components/ui/page-foot'
import { SectionHead } from '@/components/ui/section-head'
import { TopBar } from '@/components/ui/topbar'
import { fmtDate } from '@/lib/format'
import type { SignatureDoc } from '@/lib/report-doc'

interface SignatureViewProps {
  runId: string
  signature: SignatureDoc | null
  rawJson: string | null
  signatureError: string | null
  downloadUrl: string | null
  publicKeyPem: string | null
  sample: boolean
}

function MetaRow({ k, v, long }: { k: string; v: React.ReactNode; long?: boolean }) {
  // Long values (full KMS resource paths, fingerprints, etc.) stack under
  // the label so they wrap LEFT-aligned instead of straggling off the right.
  if (long) {
    return (
      <div style={{ padding: '8px 0', borderBottom: '1px dotted var(--hairline-soft)' }}>
        <div style={{ fontSize: 12, color: 'var(--ink-2)', marginBottom: 4 }}>{k}</div>
        <div
          className="mono"
          style={{ fontSize: 11, color: 'var(--ink)', wordBreak: 'break-all', lineHeight: 1.6 }}
        >
          {v}
        </div>
      </div>
    )
  }
  return (
    <div className="leader-row" style={{ padding: '5px 0' }}>
      <span style={{ fontSize: 12, color: 'var(--ink-2)' }}>{k}</span>
      <span className="leader-fill"></span>
      <span className="mono" style={{ fontSize: 11, textAlign: 'right', wordBreak: 'break-all' }}>
        {v}
      </span>
    </div>
  )
}

export function SignatureView({
  runId,
  signature,
  rawJson,
  signatureError,
  downloadUrl,
  publicKeyPem,
  sample,
}: SignatureViewProps) {
  const [copied, setCopied] = useState(false)
  const [copyError, setCopyError] = useState<string | null>(null)
  const [showPem, setShowPem] = useState(false)
  const copyRaw = async () => {
    if (!rawJson) return
    setCopyError(null)
    if (!navigator.clipboard?.writeText) {
      setCopyError('clipboard API unavailable in this context')
      return
    }
    try {
      await navigator.clipboard.writeText(rawJson)
      setCopied(true)
      setTimeout(() => setCopied(false), 1400)
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err)
      console.error('clipboard write failed:', err)
      setCopyError(msg)
    }
  }

  return (
    <div className="page-enter">
      <TopBar />
      <div className="shell" style={{ padding: '44px 40px 30px', maxWidth: 940 }}>
        <div className="mono muted" style={{ fontSize: 11, marginBottom: 16 }}>
          <A to="audits" style={{ color: 'var(--ember-deep)', textDecoration: 'none' }}>
            AUDIT REGISTRY
          </A>{' '}
          /{' '}
          <A to={`report/${runId}`} style={{ color: 'var(--ember-deep)', textDecoration: 'none' }}>
            {runId}
          </A>{' '}
          / signature.json
        </div>

        <div
          style={{
            display: 'flex',
            alignItems: 'flex-end',
            gap: 18,
            marginBottom: 26,
            flexWrap: 'wrap',
          }}
        >
          <div style={{ flex: 1, minWidth: 280 }}>
            <h1 className="display" style={{ fontSize: 36 }}>
              Signature sidecar.
              {sample ? (
                <span
                  className="tag"
                  style={{ marginLeft: 12, fontSize: 10.5, verticalAlign: 'middle' }}
                  title="Seeded sample — a real audit of the demo target, visible to every account"
                >
                  SAMPLE
                </span>
              ) : null}
            </h1>
            <div className="mono muted" style={{ fontSize: 11.5, marginTop: 8 }}>
              The cryptographic chain-of-custody — verify it offline, without us
            </div>
          </div>
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            {downloadUrl ? (
              <a className="btn primary" href={downloadUrl} download="signature.json">
                Download signature.json
              </a>
            ) : null}
            <button className="btn small ghost" onClick={copyRaw} disabled={!rawJson} type="button">
              {copied ? 'Copied ✓' : 'Copy raw JSON'}
            </button>
          </div>
        </div>
        {copyError ? (
          <div
            className="mono"
            style={{
              fontSize: 11,
              color: 'var(--warn, #8a6d1a)',
              border: '1px dashed currentColor',
              borderRadius: 4,
              padding: '8px 12px',
              marginBottom: 18,
            }}
          >
            ⚠ copy failed — {copyError}. Use the Download button instead.
          </div>
        ) : null}

        {signature ? (
          <>
            <div
              className="card"
              style={{
                padding: '18px 22px',
                marginBottom: 40,
                borderLeft: '3px solid var(--ember-deep)',
                borderRadius: '0 var(--r-lg) var(--r-lg) 0',
              }}
            >
              <div
                className="mono"
                style={{
                  fontSize: 10.5,
                  letterSpacing: '0.12em',
                  color: 'var(--ember-deep)',
                  marginBottom: 12,
                }}
              >
                KEY IDENTITY
              </div>
              <MetaRow k="Algorithm" v={signature.algorithm} />
              <MetaRow k="Signed at" v={fmtDate(signature.signedAt)} />
              <MetaRow k="KMS key version" v={signature.kmsKeyVersion} long />
              <MetaRow k="Public key fingerprint (SHA-256)" v={signature.fingerprint} long />
            </div>

            <SectionHead
              no="§1"
              title="Artifacts signed"
              right={
                <span className="mono muted" style={{ fontSize: 10.5 }}>
                  {signature.artifacts.length} entr
                  {signature.artifacts.length === 1 ? 'y' : 'ies'}
                </span>
              }
            />
            <div style={{ marginBottom: 44 }}>
              {signature.artifacts.length === 0 ? (
                <p className="muted" style={{ fontSize: 12 }}>
                  The sidecar declared no per-artifact signatures.
                </p>
              ) : (
                <table className="ledger">
                  <thead>
                    <tr>
                      <th>File</th>
                      <th>SHA-256</th>
                    </tr>
                  </thead>
                  <tbody>
                    {signature.artifacts.map((a) => (
                      <tr key={a.file}>
                        <td className="mono" style={{ fontSize: 12 }}>
                          {a.file}
                        </td>
                        <td className="mono" style={{ fontSize: 11, wordBreak: 'break-all' }}>
                          {a.sha256}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>

            <SectionHead
              no="§2"
              title="Public key"
              right={
                publicKeyPem ? (
                  <button
                    type="button"
                    className="btn small ghost"
                    onClick={() => setShowPem((v) => !v)}
                  >
                    {showPem ? 'Hide PEM' : 'Show PEM'}
                  </button>
                ) : null
              }
            />
            <div style={{ marginBottom: 44 }}>
              {showPem && publicKeyPem ? (
                <pre
                  className="codeblock"
                  style={{ margin: 0, whiteSpace: 'pre-wrap', fontSize: 11 }}
                >
                  {publicKeyPem}
                </pre>
              ) : (
                <p className="muted" style={{ fontSize: 12.5, lineHeight: 1.7 }}>
                  The Ed25519 public key the runtime SA holds in Cloud KMS. Show it to verify the
                  fingerprint above (SHA-256 of the PEM), or use the downloaded sidecar.
                </p>
              )}
            </div>

            <SectionHead no="§3" title="Verify offline" />
            <p style={{ fontSize: 13, color: 'var(--ink-2)', margin: '0 0 12px', lineHeight: 1.7 }}>
              The sidecar is verifiable without contacting Phoenix Audit. The signature for each
              artifact is computed as <span className="mono">ed25519(sha256(file_bytes))</span>.
            </p>
            <pre
              className="codeblock"
              style={{ margin: 0, whiteSpace: 'pre-wrap', fontSize: 12 }}
            >{`for each artifact in signature.artifacts:
  expected = artifact.sha256
  actual   = sha256(read(artifact.file))
  assert expected == actual
  ed25519_verify(
    public_key_pem,
    message   = sha256_raw(read(artifact.file)),
    signature = base64_decode(artifact.signature_b64),
  )`}</pre>
          </>
        ) : (
          <div
            className="mono"
            style={{
              fontSize: 12,
              color: 'var(--warn, #8a6d1a)',
              border: '1px dashed currentColor',
              borderRadius: 4,
              padding: '12px 16px',
            }}
          >
            ⚠ signature.json could not be loaded{signatureError ? ` (${signatureError})` : ''}.
            {downloadUrl ? ' Use the Download button to fetch the raw artifact.' : ''}
          </div>
        )}
      </div>
      <PageFoot />
    </div>
  )
}
