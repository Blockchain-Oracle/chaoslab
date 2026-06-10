// The report/recipe presentation layer (story-9.13) renders REAL artifacts:
// report.json (probes/verdicts/clusters), signature.json (Ed25519 fingerprint),
// recipe.md (patches as unified diffs). Parsing is defensive — a malformed
// artifact surfaces as null so pages disclose instead of rendering garbage.

import { describe, expect, it } from 'vitest'
import {
  diffLineKind,
  parseRecipeMarkdown,
  parseReportDocument,
  parseSignatureDocument,
} from '@/lib/report-doc'

const REAL_REPORT = {
  run_id: 'run_ddf8b97511ca',
  target_url: 'https://target-agent.example.run.app',
  framework_label: 'EU AI Act · high-risk system',
  created_at: '2026-06-10T19:58:28+00:00',
  passed: 1,
  failed: 7,
  errored: 0,
  transport_failed: 0,
  honored_missing_count: 8,
  honored_unreadable_count: 0,
  excluded_transport_failures: 0,
  annotation_writeback_failed: true,
  clustering_skipped: null,
  recipe_id: 'recipe_177dc8b85cae',
  cluster_ids: ['cluster_a1b2c3d4'],
  root_causes: ['The agent hallucinates tool execution results.'],
  markdown_url: 'https://signed.example/recipe.md',
  probes: [
    {
      n: 1,
      fault_class: 'malformed_tool_output',
      verdict: 'fail',
      score: 0.0,
      span_id: '92aa0568a04eb7083d3b8108900ff754',
      transport_error: false,
      rubric_error: false,
    },
    {
      n: 3,
      fault_class: 'prompt_injection',
      verdict: 'pass',
      score: 1.0,
      span_id: '6e5d564cd60b0fd427eb5ff2ab462579',
      transport_error: false,
      rubric_error: false,
    },
  ],
}

const REAL_SIGNATURE = {
  version: 1,
  algorithm: 'EC_SIGN_ED25519',
  kms_key_version: 'projects/p/locations/l/keyRings/k/cryptoKeys/c/cryptoKeyVersions/1',
  message_convention: 'ed25519_sign(sha256(file_bytes))',
  public_key_fingerprint_sha256: 'a1b2'.repeat(16),
  public_key_pem: '-----BEGIN PUBLIC KEY-----\nx\n-----END PUBLIC KEY-----\n',
  signed_at: '2026-06-10T20:00:40+00:00',
  artifacts: [
    { file: 'report.pdf', sha256: 'aa', signature_b64: 'sig1' },
    { file: 'report.json', sha256: 'bb', signature_b64: 'sig2' },
  ],
}

describe('parseReportDocument', () => {
  it('parses the real artifact shape', () => {
    const doc = parseReportDocument(REAL_REPORT)
    expect(doc).not.toBeNull()
    expect(doc?.runId).toBe('run_ddf8b97511ca')
    expect(doc?.frameworkLabel).toBe('EU AI Act · high-risk system')
    expect(doc?.passed).toBe(1)
    expect(doc?.rootCauses).toHaveLength(1)
    expect(doc?.probes).toHaveLength(2)
    expect(doc?.probes[1]).toMatchObject({
      n: 3,
      faultClass: 'prompt_injection',
      verdict: 'pass',
      score: 1,
      spanId: '6e5d564cd60b0fd427eb5ff2ab462579',
    })
    expect(doc?.annotationWritebackFailed).toBe(true)
  })

  it('rejects non-objects and missing required fields', () => {
    expect(parseReportDocument(null)).toBeNull()
    expect(parseReportDocument('x')).toBeNull()
    expect(parseReportDocument({ ...REAL_REPORT, run_id: undefined })).toBeNull()
    expect(parseReportDocument({ ...REAL_REPORT, probes: 'not-a-list' })).toBeNull()
  })

  it('rejects a probe with an unknown verdict instead of mislabeling it', () => {
    const bad = {
      ...REAL_REPORT,
      probes: [{ ...REAL_REPORT.probes[0], verdict: 'maybe' }],
    }
    expect(parseReportDocument(bad)).toBeNull()
  })

  it('tolerates unknown extra keys (forward compat)', () => {
    expect(parseReportDocument({ ...REAL_REPORT, future_field: 1 })).not.toBeNull()
  })
})

describe('parseSignatureDocument', () => {
  it('parses the real sidecar shape', () => {
    const sig = parseSignatureDocument(REAL_SIGNATURE)
    expect(sig).not.toBeNull()
    expect(sig?.fingerprint).toMatch(/^a1b2a1b2/)
    expect(sig?.algorithm).toBe('EC_SIGN_ED25519')
    expect(sig?.kmsKeyVersion).toContain('cryptoKeyVersions/1')
    expect(sig?.signedAt).toBe('2026-06-10T20:00:40+00:00')
    expect(sig?.artifacts).toEqual([
      { file: 'report.pdf', sha256: 'aa' },
      { file: 'report.json', sha256: 'bb' },
    ])
  })

  it('rejects junk', () => {
    expect(parseSignatureDocument(null)).toBeNull()
    expect(parseSignatureDocument({})).toBeNull()
    expect(
      parseSignatureDocument({ ...REAL_SIGNATURE, public_key_fingerprint_sha256: '' }),
    ).toBeNull()
  })
})

describe('diffLineKind', () => {
  it('classifies unified diff lines', () => {
    expect(diffLineKind('+validated = schema.parse(out)')).toBe('add')
    expect(diffLineKind('-return out')).toBe('del')
    expect(diffLineKind('@@ -1,4 +1,6 @@')).toBe('hunk')
    expect(diffLineKind('+++ b/tools/lookup.py')).toBe('hunk')
    expect(diffLineKind('--- a/tools/lookup.py')).toBe('hunk')
    expect(diffLineKind(' unchanged context')).toBe('ctx')
    expect(diffLineKind('plain text')).toBe('ctx')
  })
})

describe('parseRecipeMarkdown', () => {
  const MD = [
    '# PhoenixAudit Hardening Recipe — recipe_x',
    '',
    '**Target agent:** `https://t.example`',
    '',
    '## Prompt Patches',
    '',
    '**Section:** `system_prompt` | **Operation:** `append`',
    '',
    '```diff',
    '+Always call lookup_order before answering.',
    '-Trust the conversation history.',
    '```',
    '',
    'Closing note.',
  ].join('\n')

  it('splits headings, text and fenced code with language', () => {
    const blocks = parseRecipeMarkdown(MD)
    expect(blocks[0]).toMatchObject({ kind: 'heading', level: 1 })
    const code = blocks.find((b) => b.kind === 'code')
    expect(code).toMatchObject({ kind: 'code', lang: 'diff' })
    if (code?.kind === 'code') {
      expect(code.lines).toEqual([
        '+Always call lookup_order before answering.',
        '-Trust the conversation history.',
      ])
    }
    const headings = blocks.filter((b) => b.kind === 'heading')
    expect(headings.map((h) => (h.kind === 'heading' ? h.text : ''))).toContain('Prompt Patches')
  })

  it('an unterminated fence still yields its lines (never swallows content)', () => {
    const blocks = parseRecipeMarkdown('```diff\n+a\n-b')
    const code = blocks.find((b) => b.kind === 'code')
    if (code?.kind === 'code') {
      expect(code.lines).toEqual(['+a', '-b'])
    } else {
      throw new Error('expected a code block')
    }
  })
})
