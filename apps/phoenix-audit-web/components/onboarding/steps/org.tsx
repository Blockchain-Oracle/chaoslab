// Step 2 — Org name. Skippable. The org name appears on the audit report
// cover (Wave-B work) so it identifies the filing entity in the regulator
// document, not just a display field.

import { Field } from '@/components/ui/field'

export function StepOrg({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  return (
    <div>
      <div className="kicker" style={{ marginBottom: 14 }}>
        Your organization
      </div>
      <h2 className="display" style={{ fontSize: 32, marginBottom: 14 }}>
        Who&apos;s filing this?
      </h2>
      <p style={{ fontSize: 13.5, color: 'var(--ink-2)', lineHeight: 1.7, marginBottom: 22 }}>
        Used to identify the filing entity on signed audit reports — Annex IV documentation names a
        real organization. Skip for now if you&apos;re evaluating; you can set it from Settings any
        time.
      </p>
      <Field label="Organization name" hint="Free text — your legal entity or team.">
        <input
          className="text-input"
          placeholder="Meridian Mutual Health"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          spellCheck="false"
          autoFocus
        />
      </Field>
    </div>
  )
}
