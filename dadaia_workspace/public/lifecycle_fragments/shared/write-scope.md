---
id: shared.write_scope
role: shared
workflow: shared
step: write_scope
static_inputs: []
dynamic_inputs: [task_group, declared_write_set]
output_schema: handoff-v1.1
max_context_policy: exact-files-only
---

# Write scope — stay inside the declared write set

This step has a declared write set: the exact files and directories it is permitted
to create or modify, supplied as `declared_write_set` for the active `task_group`.
Every change you make must fall inside that set; a change outside it is out of
contract, not a near-miss.

## Discipline

- Edit only paths inside `declared_write_set`. If correct completion of the task
  genuinely requires touching a path outside it, stop and report that the write set
  is too narrow — do not widen it yourself by editing out of scope.
- Make the change minimal and single-purpose. Do not reformat, rename, or refactor
  files the task did not ask you to change, even when they are inside the set.
- Do not touch another step's or another task group's files, even when they sit
  beside yours in the tree.
- Memory atoms, archived releases, and session state are never in a normal step's
  write set; do not write them.

## Task-marker trace

When the step operates on a release task, the task carries a state marker:

| Marker | State |
|---|---|
| `[ ]` | open — nobody is working it |
| `[-]` | reserved — this step took it |
| `[x]` | done — implemented AND reviewed/approved |

The workflow's Python body reserves every incomplete task (`[ ]` → `[-]`) before
this worker starts. Confirm the supplied tasks are reserved, but do not edit
`TASKS.md`: it is intentionally outside the implementation write set. Python leaves
the markers `[-]` through correction retries or a blocked result and changes them to
`[x]` only after QA, security, code review, and closure all succeed.
