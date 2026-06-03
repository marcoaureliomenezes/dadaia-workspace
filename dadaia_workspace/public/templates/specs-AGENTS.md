# specs/AGENTS.md — Spec Context Rules

Scope: this file governs only the `specs/` tree of one Spec Context Project.
Root workspace behavior is in the workspace `AGENTS.md`; production-source
behavior is in the repo-local `AGENTS.md`.

## Load Order

Before writing or reviewing SDD artifacts, read:

```text
constitution.md
memory/architecture.md
memory/tech-stack.md
memory/product/index.md
releases/ACTIVE.md
releases/<release-id>/SPEC.md
releases/<release-id>/PLAN.md
releases/<release-id>/TASKS.md
```

Use `_archive/` only for history. Use `backlog/` and `bugs/` for intake and
triage; they are not approval gates.

## Release Gate

Implementation is allowed only when:

- `ACTIVE.md` declares the active release and `phase: IMPLEMENTATION`.
- `SPEC.md`, `PLAN.md`, and `TASKS.md` contain `**Status:** Aprovado`.
- The active task is changed from `[ ]` to `[-]` before production edits.
- The task's declared write set contains every production file to be edited.

If any item is missing, stop. Draft or repair the SDD artifact instead of
editing production.

## Artifact Authority

| Path | Writer |
|---|---|
| `constitution.md` | operator or `product-engineer` during approved governance work |
| `releases/ACTIVE.md` | `product-engineer` |
| `releases/<id>/SPEC.md` | `product-engineer` |
| `releases/<id>/PLAN.md` | `product-engineer` |
| `releases/<id>/TASKS.md` | `product-engineer`; implementers may change only their task marker |
| `releases/<id>/CLOSURE.md` | `product-engineer` in `CLOSURE` |
| `memory/**` | `product-engineer` in `CLOSURE` only |
| `backlog/**` | `product-engineer` or operator intake |
| `bugs/**` | any agent may file; `product-engineer` resolves into release work |

## Task Markers

Use only these markers:

```text
[ ] OPEN
[-] IN PROGRESS
[x] DONE
```

Do not take a task already marked `[-]`. Do not mark `[x]` without validation
evidence in the implementing report.

## Memory

Memory describes the product as it is now.

- No changelog/history/version sections in `memory/**`.
- Screenshots referenced by memory live under `assets/`.
- Stale memory found during implementation becomes a bug or closure note; do
  not patch memory mid-implementation.

## Doctor

Run before closing spec work:

```bash
dadaia specs doctor
```

`dadaia specs doctor --fix` may repair scaffoldable tree issues. It must not be
used to bypass missing approval, unclear scope, or task ownership.

## Escalation

Use this exact shape when blocked:

```text
[SDD BLOCKED]
Context: <context>
Release: <release-id>
Artifact: <path>
Reason: <one sentence>
Needed decision: <one concrete question or action>
```

Generated from `dadaia_workspace/public/templates/specs-AGENTS.md`. Project
teams may customize this file; `dadaia specs doctor` reports drift instead of
overwriting it.
