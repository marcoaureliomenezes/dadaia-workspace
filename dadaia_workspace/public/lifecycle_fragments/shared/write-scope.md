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
Every change you make must fall inside that set. The boundary is enforced by the
workflow after the fact (changed paths are compared against the declared set), so a
change outside the set is not a near-miss — it blocks the step.

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

Reserve the task (`[ ]` → `[-]`) before editing, and leave it `[-]` until the
review evidence the workflow requires has cleared. Never flip a task to `[x]`
yourself on the strength of your own work; completion is a gate decision made from
review evidence, not a self-grant.

## In one line

Touch only what `declared_write_set` allows, change only what the task asks for, and
let the gate — not your own judgment — decide when the task is done.
