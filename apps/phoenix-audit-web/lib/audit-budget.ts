// Story-9.15 slice 8 — wizard probe budget math.
//
// The operator types "Cap number of tests" (mental model: total probes
// across the run). The backend consumes attacks-per-fault-class across
// the 4 fault classes (prompt_injection / context_poisoning /
// malformed_tool_output / latency_spike). This helper translates the
// operator's number into the backend's number, clamping to a safe
// range and treating NaN as the minimum.
//
// The 20-per-class ceiling matches the backend's per-class fan-out cap;
// raising it requires a backend change first.

const FAULT_CLASS_COUNT = 4
const MIN_PER_CLASS = 1
const MAX_PER_CLASS = 20

export function runsPerFaultFromCap(cap: number): number {
  if (!Number.isFinite(cap)) return MIN_PER_CLASS
  const raw = Math.round(cap / FAULT_CLASS_COUNT)
  return Math.max(MIN_PER_CLASS, Math.min(MAX_PER_CLASS, raw))
}
