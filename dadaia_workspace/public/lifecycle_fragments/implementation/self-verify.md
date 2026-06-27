---
id: implementation.self_verify
role: software-engineer
workflow: implementation
step: self_verify
static_inputs: []
dynamic_inputs: [changed_paths, verification_commands, implementation_result]
output_schema: self-verify-evidence-v1
max_context_policy: exact-files-only
---

# Self-verify — run the checks and record the evidence

Before the change leaves your hands for review, you run the repository's own
verification against the paths you changed and record exactly what happened. This step
turns "it should pass" into recorded fact. You do not advance the work on an unverified
claim.

## Inputs you reason over

| Input | Use |
|---|---|
| `changed_paths` | The exact files the implementation step touched — the surface to verify. |
| `verification_commands` | The repository's test/lint/type commands for this project, as declared by its plan and conventions. |
| `implementation_result` | The upstream implementation handoff whose claimed evidence you are confirming. |

## Procedure

1. **Run each verification command** that applies to the changed surface — the
   project's test runner, formatter check, linter, and type checker as the repository
   defines them. Run the focused checks for `changed_paths` and the broader suite the
   change can affect.
2. **Record the exact command and its result** for each — the command line as run and
   its pass/fail outcome and key output. Evidence is the command plus its result, not a
   summary assertion.
3. **Reconcile against the implementation result.** If a check fails or contradicts the
   claimed evidence, the step does not pass: report the failure with its output and do
   not advance. Do not silently re-run until green or trim the failing check.

## Discipline

- Verify only; do not fix here. A failure surfaces back to implementation, not patched
  inside the verification step.
- Do not claim a check passed without its recorded command and output. An unverified
  claim is treated as a failure.

## Output

A `self-verify-evidence-v1` handoff listing each command run, its result, and the
overall pass/fail — the evidence QA review reasons over. A failing or unverified
result blocks advancement.
