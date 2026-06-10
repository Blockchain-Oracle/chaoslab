'use client'

import { useState } from 'react'
import { A } from '@/components/ui/link'
import { PageFoot } from '@/components/ui/page-foot'
import { SectionHead } from '@/components/ui/section-head'
import { FaultClass, SpanLink } from '@/components/ui/stamps'
import { TopBar } from '@/components/ui/topbar'
import { CLUSTER_SET, HERO_RUN, RECIPE } from '@/lib/fixtures'
import { fmtDate } from '@/lib/format'
import { useSafeTimeout } from '@/lib/use-safe-timeout'
import { OpTag } from './op-tag'

export function RecipeView() {
  const r = RECIPE
  const c = CLUSTER_SET.clusters[0]
  const [copied, setCopied] = useState(false)
  const schedule = useSafeTimeout()
  const flash = () => {
    setCopied(true)
    schedule(() => setCopied(false), 1400)
  }
  if (!c) return null
  return (
    <div className="page-enter">
      <TopBar />
      <div className="shell" style={{ padding: '50px 40px 30px', maxWidth: 940 }}>
        <div className="mono muted" style={{ fontSize: 11, marginBottom: 16 }}>
          <A to="audits" style={{ color: 'var(--ember-deep)', textDecoration: 'none' }}>
            AUDIT REGISTRY
          </A>{' '}
          / run_9f3c2ab81d4e / {r.recipeId}
        </div>
        <div style={{ display: 'flex', alignItems: 'flex-end', gap: 18, marginBottom: 8 }}>
          <h1 className="display" style={{ fontSize: 38, flex: 1 }}>
            Hardening recipe.
          </h1>
          <div style={{ display: 'flex', gap: 10 }}>
            <button className="btn small" onClick={flash}>
              Download markdown
            </button>
            <a
              className="btn small ghost"
              href={HERO_RUN.mrUrl}
              onClick={(e) => e.preventDefault()}
            >
              GitLab MR !214 ↗
            </a>
            <button className="btn small ghost" onClick={flash}>
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
          <span className="mono muted" style={{ fontSize: 11.5, whiteSpace: 'nowrap' }}>
            generated {fmtDate(r.generatedAt)} · in {r.generationSec} s
          </span>
          <span className="tag" style={{ color: 'var(--pass)' }}>
            estimated resilience improvement +{Math.round(r.estimatedResilienceImprovement * 100)}%
          </span>
        </div>

        <SectionHead no="§1" title="Root cause clusters addressed" />
        <div
          className="card"
          style={{
            padding: '18px 22px',
            marginBottom: 44,
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
              marginBottom: 8,
            }}
          >
            {c.clusterId} · EXPLAINS {c.failureCount} OF {CLUSTER_SET.totalFailures} FAILURES
          </div>
          <p className="serif" style={{ fontSize: 17, lineHeight: 1.5, marginBottom: 12 }}>
            {c.rootCause}
          </p>
          <div
            style={{
              display: 'flex',
              gap: 8,
              flexWrap: 'wrap',
              alignItems: 'center',
            }}
          >
            {c.faultClasses.map((f) => (
              <FaultClass key={f} name={f} />
            ))}
            <span style={{ flex: 1 }}></span>
            {c.spanIds.map((sp) => (
              <SpanLink key={sp} id={sp} />
            ))}
          </div>
        </div>

        <SectionHead
          no="§2"
          title="Prompt patches"
          right={
            <span className="mono muted" style={{ fontSize: 10.5 }}>
              {r.promptPatches.length} patches
            </span>
          }
        />
        <div style={{ display: 'grid', gap: 16, marginBottom: 44 }}>
          {r.promptPatches.map((p, i) => (
            <div key={i} className="card" style={{ padding: '16px 20px' }}>
              <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
                <OpTag>{p.section}</OpTag>
                <OpTag>{p.operation}</OpTag>
              </div>
              {p.before ? (
                <div
                  style={{
                    fontFamily: 'var(--mono)',
                    fontSize: 12,
                    color: 'var(--fail)',
                    textDecoration: 'line-through',
                    marginBottom: 8,
                    lineHeight: 1.6,
                    opacity: 0.75,
                  }}
                >
                  {p.before}
                </div>
              ) : null}
              <div
                style={{
                  fontFamily: 'var(--mono)',
                  fontSize: 12.5,
                  lineHeight: 1.7,
                  background: 'var(--pass-soft)',
                  borderRadius: 3,
                  padding: '10px 14px',
                  color: 'var(--ink)',
                }}
              >
                <span style={{ color: 'var(--pass)', marginRight: 8 }}>+</span>
                {p.after}
              </div>
            </div>
          ))}
        </div>

        <SectionHead
          no="§3"
          title="Tool validation diffs"
          right={
            <span className="mono muted" style={{ fontSize: 10.5 }}>
              unified diff
            </span>
          }
        />
        <div style={{ display: 'grid', gap: 16, marginBottom: 44 }}>
          {r.toolValidationDiffs.map((d, i) => (
            <div key={i}>
              <div
                style={{
                  display: 'flex',
                  gap: 8,
                  alignItems: 'center',
                  marginBottom: 10,
                }}
              >
                <span className="mono" style={{ fontSize: 13 }}>
                  {d.toolName}
                </span>
                <OpTag>{d.operation}</OpTag>
              </div>
              <pre className="codeblock" style={{ margin: 0, whiteSpace: 'pre' }}>
                {d.codePatch.split('\n').map((line, j) => {
                  const cls = line.startsWith('+')
                    ? 'add'
                    : line.startsWith('---') || line.startsWith('+++') || line.startsWith('@@')
                      ? 'dim'
                      : ''
                  return (
                    <div key={j} className={cls}>
                      {line}
                    </div>
                  )
                })}
              </pre>
            </div>
          ))}
        </div>

        <SectionHead
          no="§4"
          title="Regression test cases"
          right={
            <span className="mono muted" style={{ fontSize: 10.5 }}>
              add to your test suite
            </span>
          }
        />
        <table className="ledger" style={{ marginBottom: 14 }}>
          <thead>
            <tr>
              <th style={{ width: 30 }}>#</th>
              <th>Input</th>
              <th>Expected</th>
            </tr>
          </thead>
          <tbody>
            {r.regressionTestCases.map((tc, i) => (
              <tr key={i}>
                <td className="mono muted" style={{ fontSize: 11 }}>
                  {String(i + 1).padStart(2, '0')}
                </td>
                <td className="mono" style={{ fontSize: 12 }}>
                  {tc.input}
                </td>
                <td style={{ fontSize: 13, color: 'var(--ink-2)' }}>{tc.expected}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="muted" style={{ fontSize: 12 }}>
          These three cases ship inside merge request !214 alongside the patches above.
        </p>
      </div>
      <PageFoot />
    </div>
  )
}
