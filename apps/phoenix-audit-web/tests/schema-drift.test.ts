// Guard against drift between the committed pydantic-exported JSON Schema
// (packages/shared-types/hardening-recipe.json — the wire source of truth)
// and the frontend's TS mirror (lib/types.ts HardeningRecipe).
//
// TS interfaces are erased at runtime, so the guard pins BOTH sides to one
// expected contract: if the backend model adds/removes/requires a field,
// this test fails and the TS mirror must be updated deliberately.

import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import type { HardeningRecipe } from '@/lib/types'

const schema = JSON.parse(
  readFileSync(
    join(__dirname, '..', '..', '..', 'packages', 'shared-types', 'hardening-recipe.json'),
    'utf-8',
  ),
) as { required?: string[]; properties?: Record<string, unknown> }

describe('hardening-recipe schema ↔ TS mirror', () => {
  it('schema required set matches the TS-required mirror', () => {
    expect(new Set(schema.required)).toEqual(
      new Set([
        'recipe_id',
        'target_agent_id',
        'generated_at',
        'cluster_set',
        'estimated_resilience_improvement',
      ]),
    )
  })

  it('schema property set matches the TS mirror fields', () => {
    expect(new Set(Object.keys(schema.properties ?? {}))).toEqual(
      new Set([
        'recipe_id',
        'target_agent_id',
        'generated_at',
        'cluster_set',
        'prompt_patches',
        'tool_validation_diffs',
        'regression_test_cases',
        'estimated_resilience_improvement',
        'metadata',
      ]),
    )
  })

  it('cluster_set is required on the TS side too (schema requires it)', () => {
    // Compile-time pin: this assignment fails `pnpm typecheck` if clusterSet
    // goes back to optional-with-undefined semantics being required here.
    const recipe: HardeningRecipe = {
      recipeId: 'recipe_000000000000',
      targetAgentId: 'demo-target',
      generatedAt: '2026-06-10T00:00:00+00:00',
      clusterSet: { clusters: [], totalFailures: 0, clustererModel: 'gemini-3.5-flash' },
      promptPatches: [],
      toolValidationDiffs: [],
      regressionTestCases: [],
      estimatedResilienceImprovement: 0,
      metadata: {},
    }
    // @ts-expect-error clusterSet is required — omitting it must not compile
    const missing: HardeningRecipe = {
      recipeId: 'recipe_000000000000',
      targetAgentId: 'demo-target',
      generatedAt: '2026-06-10T00:00:00+00:00',
      promptPatches: [],
      toolValidationDiffs: [],
      regressionTestCases: [],
      estimatedResilienceImprovement: 0,
      metadata: {},
    }
    expect(recipe.clusterSet.totalFailures).toBe(0)
    expect(missing.recipeId).toBeTruthy()
  })
})
