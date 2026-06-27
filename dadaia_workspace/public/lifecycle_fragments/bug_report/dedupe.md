---
id: bug_report.dedupe
role: product-engineer
workflow: bug_report
step: dedupe
static_inputs: []
dynamic_inputs: [open_bugs, selected_bugs]
output_schema: bug-dedupe-handoff-v1
max_context_policy: summary
---

# Dedupe — is this a new bug or an existing one

You compare the normalized intake against every tracked bug and decide whether it is a
genuinely new bug or a duplicate of an existing record. You return a verdict; you do
not write the record.

## Inputs you reason over

| Input | Use |
|---|---|
| `open_bugs` | The open bugs the intake is matched against. |
| `selected_bugs` | The full bug set, including dispositioned ones, for completeness. |

## Review rubric

| Check | Pass condition |
|---|---|
| Same symptom | A bug describing the same symptom + repro is treated as a duplicate, not re-filed. |
| Same surface | A bug on the same surface with a compatible cause is a duplicate candidate. |
| Genuinely new | No existing record covers this symptom + repro + surface. |

## Output

A verdict — `APPROVED` (genuinely new — proceed to write a record) or `REJECTED`
(duplicate — fold into the existing bug instead of filing a new file) — with a
one-sentence reason. When REJECTED, name the existing bug it duplicates. A bug is
never silently dropped; a duplicate is routed, not deleted.
