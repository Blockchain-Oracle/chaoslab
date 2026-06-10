// The designed multi-page report preview (restored in story-9.13), fed by the
// run's REAL artifacts: report.json drives every number, signature.json the
// attestation block, recipe.md the recipe page. No fixture values anywhere.

import { Seal } from '@/components/ui/seal'
import { Verdict } from '@/components/ui/stamps'
import { Wordmark } from '@/components/ui/wordmark'
import { fmtDate } from '@/lib/format'
import type { RecipeBlock, ReportDoc, SignatureDoc } from '@/lib/report-doc'
import { LockedParagraph } from './locked-paragraph'
import { RecipeMdView } from './recipe-md-view'

export type ReportPageId = 'cover' | 'exec' | 'tests' | 'clusters' | 'recipe' | 'appendix'

export interface ReportPageDef {
  id: ReportPageId
  label: string
}

export const REPORT_PAGES: ReportPageDef[] = [
  { id: 'cover', label: 'Cover & attestation' },
  { id: 'exec', label: 'Executive summary' },
  { id: 'tests', label: 'Adversarial probes' },
  { id: 'clusters', label: 'Failure clusters' },
  { id: 'recipe', label: 'Hardening recipe' },
  { id: 'appendix', label: 'Framework mapping' },
]

export interface ReportView {
  report: ReportDoc
  /** null = sidecar unavailable; the cover DISCLOSES instead of faking. */
  signature: SignatureDoc | null
  signatureError: string | null
  /** null = recipe.md unavailable; the recipe page discloses. */
  recipeBlocks: RecipeBlock[] | null
  recipeError: string | null
}

interface ReportPageProps {
  page: ReportPageId
  view: ReportView
  signed: boolean
}

function probeVerdict(p: ReportDoc['probes'][number]): 'pass' | 'fail' | 'error' {
  if (p.rubricError || p.transportError) return 'error'
  return p.verdict
}

export function ReportPage({ page, view, signed }: ReportPageProps) {
  const { report, signature } = view
  const [frameworkName, ...frameworkRest] = report.frameworkLabel.split('·').map((s) => s.trim())

  if (page === 'cover') {
    const coverRows: ReadonlyArray<[string, string]> = [
      ['Audit run', report.runId],
      ['Target agent', report.targetUrl],
      ['Framework', report.frameworkLabel],
      ['Filed', fmtDate(report.createdAt)],
      [
        'Signing key',
        signature
          ? `Cloud KMS · ${signature.algorithm} · ${signature.fingerprint.slice(0, 16)}…`
          : 'Cloud KMS · Ed25519 · sidecar unavailable',
      ],
    ]
    return (
      <div>
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'flex-start',
            marginBottom: 46,
          }}
        >
          <Wordmark size={15} glyph={17} />
          <span className="mono muted" style={{ fontSize: 10 }}>
            {report.runId}
          </span>
        </div>
        <div className="kicker" style={{ marginBottom: 14 }}>
          Signed audit report
        </div>
        <h2 className="display" style={{ fontSize: 30, marginBottom: 30 }}>
          {frameworkName}
          {frameworkRest.length ? (
            <>
              <br />
              <em>{frameworkRest.join(' · ')}</em>
            </>
          ) : null}
        </h2>
        {coverRows.map(([k, v]) => (
          <div key={k} className="leader-row" style={{ padding: '4.5px 0' }}>
            <span style={{ fontSize: 12, color: 'var(--ink-2)' }}>{k}</span>
            <span className="leader-fill"></span>
            <span className="mono" style={{ fontSize: 10.5 }}>
              {v}
            </span>
          </div>
        ))}
        {/* Verbatim-locked texts — docs/run-config-schema.md §"Default-mode
            variant" and docs/header-convention.md §"Audit-report warning".
            Only the declared {N} placeholder substitutes. */}
        <LockedParagraph title="DATA RESIDENCY — DEFAULT HOSTING VARIANT">
          Audit traces are retained in Phoenix Audit&apos;s hosted Phoenix project for 24 hours
          after this report&apos;s cryptographic signature is emitted, then cryptographically erased
          via Cloud KMS key-shred. Phoenix Audit acts as a GDPR Article 28 data processor for the
          duration of the retention window. This signed PDF is the durable artifact; all underlying
          probe-and-response data is destroyed after the retention window closes.
        </LockedParagraph>
        {report.honoredMissingCount > 0 ? (
          <LockedParagraph title="HEADER CONVENTION WARNING — INCLUDED FOR THIS RUN">
            Target did not signal it honored the X-Phoenix-Audit-* headers (`phoenix_audit.honored =
            true` was absent from {report.honoredMissingCount} probe-response spans). Side-effecting
            tool calls during this audit run MAY have been executed for real against the target. To
            opt into dry-run behavior, the target must read `X-Phoenix-Audit-Dry-Run` and
            short-circuit side-effecting tools when its value is `true`, AND emit
            `phoenix_audit.honored = true` as a span attribute on every response.
          </LockedParagraph>
        ) : null}
        {signed ? (
          <div
            style={{
              position: 'absolute',
              right: 70,
              bottom: 64,
              transform: 'rotate(-8deg)',
              filter: 'drop-shadow(0 6px 16px rgba(28,23,18,0.2))',
            }}
            className="verdict-in"
          >
            <Seal size={120} spin={false} />
          </div>
        ) : null}
      </div>
    )
  }

  if (page === 'exec') {
    const stats: ReadonlyArray<[string, string]> = [
      [String(report.probes.length), 'probes'],
      [`${report.passed} / ${report.failed}`, 'pass / fail'],
      [String(report.rootCauses.length), 'root causes'],
      [String(report.errored), 'unscored'],
    ]
    return (
      <div>
        <div className="kicker" style={{ marginBottom: 14 }}>
          Executive summary — board-ready, unedited
        </div>
        <h2 className="serif" style={{ fontSize: 24, marginBottom: 18 }}>
          {report.failed} failure{report.failed === 1 ? '' : 's'}. {report.rootCauses.length} root
          cause{report.rootCauses.length === 1 ? '' : 's'}.{report.recipeId ? ' Patched.' : ''}
        </h2>
        <p
          style={{
            fontSize: 13.5,
            lineHeight: 1.75,
            color: 'var(--ink-2)',
            marginBottom: 18,
            textWrap: 'pretty',
          }}
        >
          On {fmtDate(report.createdAt)}, Phoenix Audit ran {report.probes.length} adversarial
          probes against {report.targetUrl} under the {report.frameworkLabel} profile.{' '}
          {report.passed} passed, {report.failed} failed
          {report.errored ? `, ${report.errored} could not be scored (marked, never counted)` : ''}.
          The failures collapse into {report.rootCauses.length} root-cause cluster
          {report.rootCauses.length === 1 ? '' : 's'}
          {report.recipeId ? `, patched by hardening recipe ${report.recipeId}` : ''}.
        </p>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(4, 1fr)',
            borderTop: '1px solid var(--ink)',
          }}
        >
          {stats.map(([v, l]) => (
            <div key={l} style={{ padding: '14px 12px 0 0' }}>
              <div className="serif num" style={{ fontSize: 24 }}>
                {v}
              </div>
              <div
                className="mono muted"
                style={{
                  fontSize: 9.5,
                  letterSpacing: '0.12em',
                  textTransform: 'uppercase',
                  marginTop: 4,
                }}
              >
                {l}
              </div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  if (page === 'tests') {
    return (
      <div>
        <div className="kicker" style={{ marginBottom: 18 }}>
          Adversarial probes
        </div>
        {report.probes.map((p) => (
          <div
            key={p.n}
            style={{
              borderBottom: '1px solid var(--hairline-soft)',
              padding: '11px 0',
              display: 'flex',
              gap: 10,
              alignItems: 'center',
            }}
          >
            <span className="mono muted" style={{ fontSize: 10 }}>
              {String(p.n).padStart(2, '0')}
            </span>
            <span style={{ fontSize: 12.5, flex: 1 }}>{p.faultClass}</span>
            <span className="mono muted" style={{ fontSize: 9.5 }} title="Phoenix span id">
              {p.spanId.slice(0, 12)}…
            </span>
            <span className="mono" style={{ fontSize: 10.5, width: 50, textAlign: 'right' }}>
              {p.score.toFixed(2)}
            </span>
            <Verdict v={probeVerdict(p)} />
          </div>
        ))}
        <p className="mono muted" style={{ fontSize: 9.5, marginTop: 14, lineHeight: 1.7 }}>
          Verdicts come from per-fault LLM-as-judge rubrics over the target&apos;s Phoenix trace
          spans; every span id above is the evidence pointer for that probe.
        </p>
      </div>
    )
  }

  if (page === 'clusters') {
    return (
      <div>
        <div className="kicker" style={{ marginBottom: 18 }}>
          Failure clusters — {report.rootCauses.length} root cause
          {report.rootCauses.length === 1 ? '' : 's'}
        </div>
        <div style={{ display: 'grid', gap: 12 }}>
          {report.rootCauses.map((cause, i) => (
            <div
              key={i}
              style={{
                border: '1px solid var(--hairline)',
                borderLeft: '3px solid var(--ember-deep)',
                padding: '14px 18px',
                borderRadius: '0 3px 3px 0',
              }}
            >
              <div
                className="mono"
                style={{
                  fontSize: 10,
                  color: 'var(--ember-deep)',
                  letterSpacing: '0.12em',
                  marginBottom: 8,
                }}
              >
                {report.clusterIds[i] ?? `CLUSTER ${i + 1}`}
              </div>
              <p className="serif" style={{ fontSize: 15, lineHeight: 1.55 }}>
                {cause}
              </p>
            </div>
          ))}
        </div>
        {report.annotationWritebackFailed ? (
          <p
            className="mono"
            style={{ fontSize: 9.5, marginTop: 14, color: 'var(--warn, #8a6d1a)' }}
          >
            ⚠ Phoenix annotation write-back failed — the clustering result is valid; span
            annotations were not persisted.
          </p>
        ) : null}
      </div>
    )
  }

  if (page === 'recipe') {
    return (
      <div>
        <div className="kicker" style={{ marginBottom: 18 }}>
          Hardening recipe{view.report.recipeId ? ` — ${view.report.recipeId}` : ''}
        </div>
        {view.recipeBlocks ? (
          <div style={{ maxHeight: 560, overflowY: 'auto', paddingRight: 6 }}>
            <RecipeMdView blocks={view.recipeBlocks} />
          </div>
        ) : (
          <p className="muted" style={{ fontSize: 13 }}>
            {view.recipeError
              ? `The recipe artifact could not be loaded right now (${view.recipeError}) — use the download button above.`
              : 'No hardening recipe was generated for this run.'}
          </p>
        )}
        <p className="mono muted" style={{ fontSize: 9.5, marginTop: 14, lineHeight: 1.7 }}>
          FILE AS GITLAB MR — available once you connect GitLab in Settings (coming next). The MR
          only ADDS files under phoenix-audit/ in your repository.
        </p>
      </div>
    )
  }

  // appendix — framework mapping. Per-article finding counts are NOT
  // fabricated: rows carry real evidence pointers or their satisfaction state.
  return (
    <div>
      <div className="kicker" style={{ marginBottom: 18 }}>
        Regulatory framework mapping — {frameworkName}
      </div>
      {[
        ['Article 9', 'Risk management system', 'this audit constitutes testing evidence'],
        ['Article 12', 'Record-keeping', 'satisfied via Phoenix trace spans'],
        [
          'Article 15',
          'Accuracy, robustness, cybersecurity',
          `${report.failed} finding${report.failed === 1 ? '' : 's'} (probe table)`,
        ],
        ['Article 72', 'Post-market monitoring', 'see continuous monitoring'],
      ].map(([a, t, n]) => (
        <div key={a} className="leader-row" style={{ padding: '7px 0' }}>
          <span className="mono" style={{ fontSize: 11, color: 'var(--ember-deep)', width: 78 }}>
            {a}
          </span>
          <span style={{ fontSize: 12.5 }}>{t}</span>
          <span className="leader-fill"></span>
          <span className="mono muted" style={{ fontSize: 10.5 }}>
            {n}
          </span>
        </div>
      ))}
      <p className="mono muted" style={{ fontSize: 9.5, marginTop: 16, lineHeight: 1.7 }}>
        Findings map to the regulatory frame selected at run time. Phoenix trace spans referenced
        per probe provide the record-keeping evidence trail; the signed artifact set provides the
        chain-of-custody anchor required for filing.
      </p>
    </div>
  )
}
