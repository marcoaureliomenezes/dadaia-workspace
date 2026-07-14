---
id: audit.audit_scope
role: project-auditor
workflow: audit
step: audit_scope
static_inputs: [specs/memory/architecture.md]
dynamic_inputs: [open_audits, open_bugs, architecture_summary, code_map_summary]
output_schema: audit-scope-handoff-v1
max_context_policy: summary
---

# Audit scope — bound what this audit will examine

This step opens an audit pass: it turns a request to "audit" into a bounded,
evidence-led scope — the lenses to apply, the surfaces to examine, and the acceptance
the audit will judge against. You scope and bound; you do not yet run the drift scan or
triage findings.

## Inputs you reason over

| Input | Use |
|---|---|
| `open_audits` | Prior audit findings still open — the baseline you build on, not repeat. |
| `open_bugs` | Known bugs that may indicate where to look. |
| `architecture_summary` | The layer rules and module map so the scope is realistic against what exists. |
| `code_map_summary` | Where the affected behavior lives today. |

## Procedure

1. **State the audit question.** Name the concrete soundness question this pass
   answers (e.g. "does the workflow data plane respect retention safety?"). A scope
   with no question is a fishing trip.
2. **Pick the lenses.** Select the review lenses to apply — security, architecture,
   test fidelity, drift, privacy — bounded to the audit question. Each lens is
   justified by evidence, not added for completeness.
3. **Bound the surfaces.** Name the exact files, modules, or doctors the audit will
   examine. The scope is a finite set; an unbounded scope is rejected.
4. **Declare acceptance.** State how each lens's pass/fail will be judged, so the
   triage step has an objective rubric.

## Output

Write one `agent-run-result-v1` object whose domain fields have this exact shape:

```json
{
  "summary": "one sentence",
  "audit_question": "one concrete soundness question",
  "lenses": [
    {"name": "architecture", "rationale": "why this lens is required"}
  ],
  "surfaces": ["exact/path/or/module"],
  "acceptance_criteria": [
    {"lens": "architecture", "pass_condition": "measurable pass condition"}
  ]
}
```

Every lens must appear exactly once in `acceptance_criteria`. Empty lists, generic
summaries, and artifact-only transport objects fail the Python gate. This handoff is
the drift-scan step's authoritative scope.
