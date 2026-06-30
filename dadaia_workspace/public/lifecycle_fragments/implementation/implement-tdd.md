---
id: implementation.implement_tdd
role: software-engineer
workflow: implementation
step: implement_tdd
static_inputs: []
dynamic_inputs: [task_group, spec_criteria, plan_slice, relevant_source_files]
output_schema: implementation-result-v1
max_context_policy: exact-files-only
---

# Implement (TDD) — minimal code that makes a test pass

You implement exactly the `task_group` reserved for this step, against the
`spec_criteria` it must satisfy and the `plan_slice` that governs how. You write the
behavior and the test that proves it — nothing wider. The cited write-scope, anti-slop,
and output-handoff fragments carry the disciplines this step builds the test-first
procedure on top of.

## Inputs you reason over

| Input | Use |
|---|---|
| `task_group` | The reserved unit of work and its declared write set — the only paths you may touch. |
| `spec_criteria` | The acceptance criteria this code must satisfy; each one needs a test that asserts it. |
| `plan_slice` | The portion of the plan that dictates approach, ordering, and test strategy for this group. |
| `relevant_source_files` | The exact existing source you extend or call into — do not assume code outside this set. |

## The test-first loop

1. **Write the test first, where feasible.** Add a targeted, initially-failing test
   that pins the behavior from `spec_criteria`, and confirm it fails for the right
   reason — a test that passes before the code exists proves nothing. Where a true
   failing-first test is impractical (e.g. a pure config or wiring change), state why in
   the result and substitute the tightest verification available.
2. **Write the minimal code to pass.** Add only enough production code to turn the
   failing test green — no speculative abstraction, no feature the criteria did not ask
   for.
3. **Run the tests and record the commands.** Execute the relevant test plus the
   surrounding suite the change can affect, and capture the exact commands and results
   as evidence — claims without recorded commands do not count.
4. **Repeat per criterion** until every acceptance criterion in `spec_criteria` for
   this `task_group` has a passing test.

## Discipline

- Keep the diff minimal and single-purpose — no unrelated refactor, rename, or reformat.
  The write-set boundary and the task-marker discipline are the cited `shared.write_scope`
  fragment's canonical contract; follow it, do not restate it.

## Output

An `implementation-result-v1` handoff: the `changed_paths` (production and test),
the test evidence (commands run plus pass/fail results), and the standard handoff
fields. The result feeds self-verify and QA review; it does not mark the task done.
