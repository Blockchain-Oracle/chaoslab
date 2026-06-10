'use client'

// Surface G — the hardening recipe rendered as its OWN page (prototype
// fidelity, restored after PR #100 deleted it). Breadcrumb · title · action
// row (download / GitLab MR / copy) · sectioned body. The recipe markdown
// (the actual signed artifact) IS the data source — rendered with the same
// diff styling as the report-preview recipe excerpt.

import { useState } from 'react'
import { A } from '@/components/ui/link'
import { PageFoot } from '@/components/ui/page-foot'
import { TopBar } from '@/components/ui/topbar'
import { fmtDate } from '@/lib/format'
import type { RecipeBlock } from '@/lib/report-doc'
import { RecipeMdView } from './recipe-md-view'

export interface RecipeViewProps {
  runId: string
  recipeId: string | null
  /** Raw recipe.md bytes (markdown) — for the "Copy as JSON" action. */
  recipeMd: string | null
  /** Parsed structural blocks (heading/text/code) — for in-app render. */
  recipeBlocks: RecipeBlock[] | null
  recipeError: string | null
  /** Fresh-signed URL on the recipe.md artifact — for "Download markdown". */
  downloadUrl: string | null
  /** Real GitLab MR URL when the recipe was filed; null otherwise. */
  mrUrl: string | null
  createdAt: string | null
  /** Same SAMPLE chip discipline as the rest of the product. */
  sample: boolean
}

export function RecipeView({
  runId,
  recipeId,
  recipeMd,
  recipeBlocks,
  recipeError,
  downloadUrl,
  mrUrl,
  createdAt,
  sample,
}: RecipeViewProps) {
  const [copied, setCopied] = useState(false)

  const copyAsJson = async () => {
    if (!recipeMd) return
    // The signed artifact is markdown; expose it as JSON-quoted text for
    // pasting into a regulator ticket or audit log without escaping by hand.
    await navigator.clipboard.writeText(JSON.stringify({ recipe_id: recipeId, markdown: recipeMd }))
    setCopied(true)
    setTimeout(() => setCopied(false), 1400)
  }

  return (
    <div className="page-enter">
      <TopBar />
      <div className="shell" style={{ padding: '50px 40px 30px', maxWidth: 940 }}>
        <div className="mono muted" style={{ fontSize: 11, marginBottom: 16 }}>
          <A to="audits" style={{ color: 'var(--ember-deep)', textDecoration: 'none' }}>
            AUDIT REGISTRY
          </A>{' '}
          /{' '}
          <A to={`report/${runId}`} style={{ color: 'var(--ember-deep)', textDecoration: 'none' }}>
            {runId}
          </A>
          {recipeId ? ` / ${recipeId}` : ''}
        </div>

        <div
          style={{
            display: 'flex',
            alignItems: 'flex-end',
            gap: 18,
            marginBottom: 8,
            flexWrap: 'wrap',
          }}
        >
          <h1 className="display" style={{ fontSize: 38, flex: 1, minWidth: 280 }}>
            Hardening recipe.
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
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            {downloadUrl ? (
              <a
                className="btn small"
                href={downloadUrl}
                download={recipeId ? `${recipeId}.md` : 'recipe.md'}
              >
                Download markdown
              </a>
            ) : null}
            {mrUrl ? (
              <a className="btn small ghost" href={mrUrl} target="_blank" rel="noreferrer">
                GitLab MR ↗
              </a>
            ) : null}
            <button
              className="btn small ghost"
              onClick={copyAsJson}
              disabled={!recipeMd}
              type="button"
            >
              {copied ? 'Copied ✓' : 'Copy as JSON'}
            </button>
          </div>
        </div>

        <div
          style={{
            display: 'flex',
            gap: 10,
            flexWrap: 'wrap',
            alignItems: 'center',
            marginBottom: 40,
          }}
        >
          {createdAt ? (
            <span className="mono muted" style={{ fontSize: 11.5, whiteSpace: 'nowrap' }}>
              filed {fmtDate(createdAt)}
            </span>
          ) : null}
          <A to={`report/${runId}`} className="span-link" style={{ fontSize: 12 }}>
            ← open the signed report this recipe came from
          </A>
        </div>

        {recipeBlocks ? (
          <RecipeMdView blocks={recipeBlocks} numbered />
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
            ⚠ The recipe markdown could not be loaded
            {recipeError ? ` (${recipeError})` : ''}.
            {downloadUrl
              ? ' Use the Download markdown button above to fetch the raw artifact.'
              : ''}
          </div>
        )}
      </div>
      <PageFoot />
    </div>
  )
}
