// Defensive parsers for the run's REAL artifacts (story-9.13): report.json,
// signature.json and recipe.md feed the restored report/recipe presentation.
// A malformed artifact parses to null so pages DISCLOSE instead of rendering
// garbage — same discipline as parseProfile / parseEventsDocument.

export type ProbeVerdict = 'pass' | 'fail'

export interface ReportProbe {
  n: number
  faultClass: string
  verdict: ProbeVerdict
  score: number
  spanId: string
  transportError: boolean
  rubricError: boolean
}

export interface ReportDoc {
  runId: string
  targetUrl: string
  frameworkLabel: string
  createdAt: string
  passed: number
  failed: number
  errored: number
  transportFailed: number
  rootCauses: string[]
  clusterIds: string[]
  recipeId: string | null
  probes: ReportProbe[]
  honoredMissingCount: number
  annotationWritebackFailed: boolean
}

function str(v: unknown): v is string {
  return typeof v === 'string' && v.length > 0
}

function num(v: unknown): v is number {
  return typeof v === 'number' && Number.isFinite(v)
}

function parseProbe(json: unknown): ReportProbe | null {
  if (typeof json !== 'object' || json === null) return null
  const o = json as Record<string, unknown>
  if (!num(o.n) || !str(o.fault_class) || !str(o.span_id) || !num(o.score)) return null
  if (o.verdict !== 'pass' && o.verdict !== 'fail') return null
  return {
    n: o.n,
    faultClass: o.fault_class,
    verdict: o.verdict,
    score: o.score,
    spanId: o.span_id,
    transportError: o.transport_error === true,
    rubricError: o.rubric_error === true,
  }
}

export function parseReportDocument(json: unknown): ReportDoc | null {
  if (typeof json !== 'object' || json === null) return null
  const o = json as Record<string, unknown>
  if (!str(o.run_id) || !str(o.target_url) || !str(o.framework_label) || !str(o.created_at))
    return null
  if (!num(o.passed) || !num(o.failed) || !num(o.errored)) return null
  if (!Array.isArray(o.probes)) return null
  const probes: ReportProbe[] = []
  for (const p of o.probes) {
    const parsed = parseProbe(p)
    if (!parsed) return null
    probes.push(parsed)
  }
  const rootCauses = Array.isArray(o.root_causes) ? o.root_causes.filter(str) : []
  const clusterIds = Array.isArray(o.cluster_ids) ? o.cluster_ids.filter(str) : []
  return {
    runId: o.run_id,
    targetUrl: o.target_url,
    frameworkLabel: o.framework_label,
    createdAt: o.created_at,
    passed: o.passed,
    failed: o.failed,
    errored: o.errored,
    transportFailed: num(o.transport_failed) ? o.transport_failed : 0,
    rootCauses,
    clusterIds,
    recipeId: str(o.recipe_id) ? o.recipe_id : null,
    probes,
    honoredMissingCount: num(o.honored_missing_count) ? o.honored_missing_count : 0,
    annotationWritebackFailed: o.annotation_writeback_failed === true,
  }
}

export interface SignatureArtifact {
  file: string
  sha256: string
}

export interface SignatureDoc {
  algorithm: string
  fingerprint: string
  kmsKeyVersion: string
  signedAt: string
  artifacts: SignatureArtifact[]
}

export function parseSignatureDocument(json: unknown): SignatureDoc | null {
  if (typeof json !== 'object' || json === null) return null
  const o = json as Record<string, unknown>
  if (!str(o.algorithm) || !str(o.public_key_fingerprint_sha256)) return null
  if (!str(o.kms_key_version) || !str(o.signed_at)) return null
  const artifacts: SignatureArtifact[] = []
  if (Array.isArray(o.artifacts)) {
    for (const a of o.artifacts) {
      if (typeof a !== 'object' || a === null) continue
      const ao = a as Record<string, unknown>
      if (str(ao.file) && str(ao.sha256)) artifacts.push({ file: ao.file, sha256: ao.sha256 })
    }
  }
  return {
    algorithm: o.algorithm,
    fingerprint: o.public_key_fingerprint_sha256,
    kmsKeyVersion: o.kms_key_version,
    signedAt: o.signed_at,
    artifacts,
  }
}

export type DiffKind = 'add' | 'del' | 'hunk' | 'ctx'

export function diffLineKind(line: string): DiffKind {
  if (line.startsWith('+++') || line.startsWith('---') || line.startsWith('@@')) return 'hunk'
  if (line.startsWith('+')) return 'add'
  if (line.startsWith('-')) return 'del'
  return 'ctx'
}

export type RecipeBlock =
  | { kind: 'heading'; level: number; text: string }
  | { kind: 'text'; text: string }
  | { kind: 'code'; lang: string; lines: string[] }

/** Structural split of the recipe markdown — headings, paragraphs, fenced
 *  code (diff blocks render with diffLineKind styling). Deliberately not a
 *  full markdown engine: the recipe is OUR generated artifact with a known
 *  shape; unknown constructs degrade to plain text, never disappear. */
export function parseRecipeMarkdown(md: string): RecipeBlock[] {
  const blocks: RecipeBlock[] = []
  let paragraph: string[] = []
  let fence: { lang: string; lines: string[] } | null = null

  const flushParagraph = () => {
    const text = paragraph.join('\n').trim()
    if (text) blocks.push({ kind: 'text', text })
    paragraph = []
  }

  for (const line of md.split('\n')) {
    if (fence) {
      if (line.startsWith('```')) {
        blocks.push({ kind: 'code', lang: fence.lang, lines: fence.lines })
        fence = null
      } else {
        fence.lines.push(line)
      }
      continue
    }
    if (line.startsWith('```')) {
      flushParagraph()
      fence = { lang: line.slice(3).trim(), lines: [] }
      continue
    }
    const heading = /^(#{1,6})\s+(.*)$/.exec(line)
    if (heading?.[1] && heading[2] !== undefined) {
      flushParagraph()
      blocks.push({ kind: 'heading', level: heading[1].length, text: heading[2].trim() })
      continue
    }
    paragraph.push(line)
  }
  // Unterminated fence: keep its lines — content must never be swallowed.
  if (fence) blocks.push({ kind: 'code', lang: fence.lang, lines: fence.lines })
  flushParagraph()
  return blocks
}
