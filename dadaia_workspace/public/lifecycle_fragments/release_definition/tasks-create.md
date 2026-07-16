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

Every task MUST carry a checklist marker line in exactly this shape (the
implementation pipeline parses it to reserve/complete tasks — a TASKS.md with no
recognizable markers cannot be implemented):

```markdown
- [ ] **T1 - <short imperative title>**
```


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

When a task creates or changes a caller-facing surface, its description must carry
the exact public type/function/method name, signature, fields, and module/export path
already approved in the PLAN. Copy those bindings faithfully. Never replace them with
generic phrases such as "one value" or "one API", and never invent a binding missing
from the approved PLAN.

## Rules

- **When revising an existing TASKS.md, REWRITE THE WHOLE FILE.** Never append or
  patch sections: a leftover tail from a prior draft creates duplicate task ids,
  which is an automatic implementability rejection. One file, one consistent task
  list, every id unique.

- Group tasks so that two tasks with disjoint write sets can proceed independently,
  and never let two tasks claim the same path family without an explicit dependency
  between them.
- Cover the whole PLAN: every workstream maps to one or more tasks, and every SPEC
  requirement is reachable through them. Nothing the PLAN promised is left untasked.
- Keep each write set as tight as the work allows; a write set wider than the task
  needs invites scope drift at implementation.
- Tasks declare validation; an implementer must never have to invent how their work
  is verified.
- Tasks carry approved public contract bindings; an implementer must never have to
  choose caller-facing names, signatures, fields, or import paths.
- Repository-local pytest commands must disable cache creation with the exact option
  `-p no:cacheprovider`. `--cache-clear` is not a substitute: it clears an existing
  cache and then permits pytest to recreate `.pytest_cache/`. Do not author any
  validation command that can leave a cache, coverage, report, or tool-state artifact
  inside the repository.
- A task's validation is part of its dependency graph. Every API, command, fixture,
  snapshot, integration path, or evidence source named by that validation must exist by
  the end of the task or one of its preconditions. Put cross-component/end-to-end
  assertions in the later integration task; validate earlier adapters or units directly.
  Never make task `Tn` depend on evidence first created by a later task.

## Output

A TASKS draft with task groups, owners, write sets, validations, and dependency
order, emitted per the output contract. The TASKS enter implementability review.
