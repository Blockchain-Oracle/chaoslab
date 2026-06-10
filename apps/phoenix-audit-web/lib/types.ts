// Types aligned with packages/shared-types/hardening-recipe.json (the backend schema).
// Frontend-only types (Test, AgentSpec, RunRecord, Phase, Timeline) added below.

export type FaultClass =
  | 'malformed_tool_output'
  | 'prompt_injection'
  | 'context_poisoning'
  | 'latency_spike'

export type PromptPatchSection = 'system_prompt' | 'tool_description' | 'few_shot_example'
export type PromptPatchOperation = 'insert' | 'replace' | 'append'

export interface PromptPatch {
  section: PromptPatchSection
  operation: PromptPatchOperation
  before?: string | null
  after: string
}

export type ToolValidationOperation =
  | 'add_input_validator'
  | 'add_output_validator'
  | 'add_retry_policy'
  | 'add_timeout'

export interface ToolValidationDiff {
  toolName: string
  operation: ToolValidationOperation
  codePatch: string
}

export interface RegressionTestCase {
  input: string
  expected: string
}

export interface FailureCluster {
  clusterId: string
  rootCause: string
  failureCount: number
  spanIds: string[]
  faultClasses: FaultClass[]
  /** EU AI Act articles (or other framework citations) the cluster touches. */
  articles?: string[]
}

export interface FailureClusterSet {
  clusters: FailureCluster[]
  totalFailures: number
  clustererModel: 'gemini-3.5-flash'
}

export interface HardeningRecipe {
  recipeId: string
  targetAgentId: string
  generatedAt: string
  generationSec?: number
  // Required — mirrors the JSON Schema (cluster_set is in `required`); the
  // drift guard in tests/schema-drift.test.ts pins both sides.
  clusterSet: FailureClusterSet
  promptPatches: PromptPatch[]
  toolValidationDiffs: ToolValidationDiff[]
  regressionTestCases: RegressionTestCase[]
  estimatedResilienceImprovement: number
  metadata: Record<string, unknown>
}

// ---------- frontend-only ----------

export type Phase = 'queued' | 'injector' | 'judge' | 'patcher' | 'succeeded' | 'failed'

export type TestVerdict = 'pass' | 'fail'
export type TestMode = 'single-turn' | 'two-turn'

export interface Test {
  /** 1-indexed probe number within the battery. */
  n: number
  name: string
  /** Short citation chip text, e.g. "OWASP LLM01". */
  citation: string
  /** Long-form citation for tooltips. */
  citationLong: string
  category: FaultClass
  mode: TestMode
  verdict: TestVerdict
  /** Whether the target acknowledged the audit-mode headers convention. */
  honored: boolean
  spanId: string
  /** Regulatory article violated, if any. */
  article: string | null
  prompt: string
  response: string
}

export interface AgentMonitoring {
  enabled: boolean
  cadence?: string
  window?: number
  deliver?: string[]
}

export type AgentTier = 1 | 2 | 3
export type AgentDepth = 1 | 2
export type AgentStatus = 'ok' | 'unreachable'

export interface AgentSpec {
  id: string
  name: string
  url: string
  framework: string
  tier: AgentTier
  transport: string
  depth: AgentDepth
  monitoring: AgentMonitoring
  lastAudit: string
  status: AgentStatus
}

export interface HeroRun {
  id: string
  createdAt: string
  agentId: string
  targetUrl: string
  commitSha: string
  framework: string
  frameworkDetail: string
  phase: Phase
  passCount: number
  failCount: number
  costUsd: number
  durationSec: number
  pdfUrl: string
  recipeId: string
  mrUrl: string
  signingKey: string
}

export type HistorySource = 'manual' | 'scheduled'

export interface HistoryRow {
  id: string
  date: string
  agentId: string
  framework: string
  pass: number
  fail: number
  /** Real runs: probes whose rubric errored (not a clean pass/fail). */
  errored?: number
  /** Real runs: probes that never reached the target. */
  transportFailed?: number
  recipe: boolean
  mr: boolean
  source: HistorySource
  tier3?: boolean
  /** Real runs: the audited URL (shown when the agent id has no registry entry). */
  targetUrl?: string
  /** Real runs: live MR link from the run record. */
  mrUrl?: string
  /** Real runs: a signed report actually exists — links must be earned. */
  reportAvailable?: boolean
}

export interface AggregateStats {
  audits: number
  findings: number
  hardened: number
  quarter: string
}

// ---------- timeline ----------

export interface TimelinePhaseEvent {
  phase: Phase
  at: number
}

export interface TimelineTestEvent {
  n: number
  start: number
  end: number
}

export interface Timeline {
  duration: number
  phases: TimelinePhaseEvent[]
  testEvents: TimelineTestEvent[]
  clusterAt: number
  recipeAt: number
  receiptAt: number
}

export interface DerivedTestState extends Test {
  state: 'pending' | 'running' | 'done'
  ev: TimelineTestEvent
}

export interface DerivedAuditState {
  t: number
  phase: Phase
  tests: DerivedTestState[]
  doneCount: number
  passDone: number
  failDone: number
  /** 0–1, drives the cascade-flip overlay. */
  flipProgress: number
  /** Whether at least one probe has finished without confirming audit-mode headers. */
  headerWarn: boolean
  /** 0–1, drives the recipe-line streaming. */
  recipeProgress: number
  receipt: boolean
}

export interface SseEvent {
  at: number
  line: string
}
