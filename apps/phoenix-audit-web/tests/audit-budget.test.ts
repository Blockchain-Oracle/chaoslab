// Story-9.15 slice 8 — pure helper for the wizard's probe-budget math.
//
// The wizard exposes "Cap number of tests" as the operator's mental
// model, but the backend takes attacks-per-fault-class across 4
// classes. The conversion is silent-failure-prone: cap=3 today
// quietly becomes 4 probes (1 × 4 classes), and the operator-facing
// label doesn't disclose the multiplier. The helper IS the contract
// — the test pins the rounding + clamp behavior so a future tweak
// can't drift it.

import { describe, expect, it } from 'vitest'
import { runsPerFaultFromCap } from '@/lib/audit-budget'

describe('runsPerFaultFromCap', () => {
  it('rounds the requested cap into per-fault-class probe budget', () => {
    expect(runsPerFaultFromCap(6)).toBe(2) // 2 × 4 = 8 probes
    expect(runsPerFaultFromCap(12)).toBe(3)
    expect(runsPerFaultFromCap(40)).toBe(10)
  })

  it('clamps the minimum to 1 (never zero probes)', () => {
    expect(runsPerFaultFromCap(0)).toBe(1)
    expect(runsPerFaultFromCap(-1)).toBe(1)
    expect(runsPerFaultFromCap(1)).toBe(1)
  })

  it('clamps the maximum to 20 per fault class', () => {
    expect(runsPerFaultFromCap(80)).toBe(20)
    expect(runsPerFaultFromCap(1000)).toBe(20)
  })

  it('treats NaN as the minimum (1) instead of NaN-propagating', () => {
    expect(runsPerFaultFromCap(Number.NaN)).toBe(1)
  })
})
