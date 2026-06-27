---
id: shared.output_handoff
role: shared
workflow: shared
step: output_handoff
static_inputs: []
dynamic_inputs: [output_schema]
output_schema: handoff-v1.1
max_context_policy: exact-files-only
---

# Output contract — emit a structured handoff

Your step does not end with prose. It ends with a single structured result object
that the workflow's Python gate validates before any state advances. Produce that
object; do not produce free-form commentary in its place.

## What the result must carry

Emit one transport-envelope object. Every result carries these fields:

| Field | Meaning |
|---|---|
| `schema` | The transport envelope id — always the literal string `agent-run-result-v1`. |
| `agent` | The role you are running as for this step. |
| `context` | The active Spec Context name. |
| `produced_at` | UTC timestamp ending in `Z`. |
| `scope` | What this step covered — a task id, artifact path, or step name. |
| `metrics` | Quantitative summary of the work (counts, sizes — schema-specific keys). |
| `artifact.type` | One of: report, spec, plan, tasks, closure, memory, other. |

Review and gate steps additionally carry:

| Field | Meaning |
|---|---|
| `verdict` | `APPROVED` or `REJECTED` — the gate keys on this. |
| `verdict_reason` | One concise sentence justifying the verdict. |
| `findings` | Array of `{severity, message, detail_md, fix_recommendation}`; severity is one of CRITICAL, HIGH, MEDIUM, LOW, INFO. |

When the step produced a written artifact (SPEC, PLAN, report) the result names its
path and a content hash so the gate can confirm the file exists and matches.

## Rules

- The verdict is a judgment from evidence, never a courtesy. If acceptance is not
  met, return `REJECTED` with the specific failing criterion in `verdict_reason` and
  a `findings` entry — do not approve to be agreeable.
- Reference inputs by their declared names; never paste their full content into the
  result.
- One result object per step. No second verdict, no trailing narrative after it.
- A result that omits a required field is a gate failure — the step has not produced
  its output and the workflow will not advance.
