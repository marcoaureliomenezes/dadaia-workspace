---
id: release_definition.tasks_create
role: product-engineer
workflow: release_definition
step: tasks_create
static_inputs: []
dynamic_inputs: [approved_spec, approved_plan, repo_ownership_map, write_set_guidance]
output_schema: release-tasks-draft-v1
max_context_policy: exact-files-only
---

# TASKS create — author the task breakdown

You break the approved PLAN into concrete, implementable tasks. Each task is a unit
of work an implementer can pick up and finish without guessing: it names its owner
role, its write set, and how it is validated.

## Inputs you reason over

| Input | Use |
|---|---|
| `approved_plan` | The ordered workstreams the tasks must realize. |
| `approved_spec` | The acceptance each task ultimately serves. |
| `repo_ownership_map` | Which role owns which paths, so each task's owner is correct. |
| `write_set_guidance` | The convention for declaring a task's permitted paths. |

## What each task must declare

| Field | Requirement |
|---|---|
| Owner role | The single role responsible for the task. |
| Write set | The exact files/directories the task may create or modify — narrow and explicit. |
| Description | What to build, specific enough to act on without re-deriving the PLAN. |
| Validation | How the task is proven done (the tests/checks it must pass). |
| Preconditions | Other tasks that must complete first, matching the PLAN's dependency order. |
| Marker | The open marker `[ ]`, ready to be reserved. |

## Rules

- Group tasks so that two tasks with disjoint write sets can proceed independently,
  and never let two tasks claim the same path family without an explicit dependency
  between them.
- Cover the whole PLAN: every workstream maps to one or more tasks, and every SPEC
  requirement is reachable through them. Nothing the PLAN promised is left untasked.
- Keep each write set as tight as the work allows; a write set wider than the task
  needs invites scope drift at implementation.
- Tasks declare validation; an implementer must never have to invent how their work
  is verified.

## Output

Write the TASKS draft to the canonical release artifact path named in your allowed write
scope: `TASKS.md` under the current release directory. Then emit one
`agent-run-result-v1` object whose `artifact_refs` includes that exact path, and whose
`structured_output` includes `content_hash` equal to the SHA-256 of the written file
bytes. The TASKS enter implementability review.
