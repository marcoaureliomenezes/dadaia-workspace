# specs/AGENTS.md — Spec Context Rules

Scope: this file governs only the `specs/` tree of one Spec Context Project.
Root workspace behavior is in the workspace `AGENTS.md`; production-source behavior is in the repo-local `AGENTS.md`.

## 1. Load order

Before writing or reviewing SDD artifacts, read:

```text
constitution.md
memory/ARCHITECTURE.md
memory/TECHSTACK.md
memory/product/index.md
releases/<release-id>/_RELEASE.json    (phase field read directly, no fold)
releases/<release-id>/SPEC.md
releases/<release-id>/PLAN.md
releases/<release-id>/TASKS.md
```

- Use `_archive/` only for history.
- Use `backlog/` and `bugs/` for intake and triage; they are not approval gates.
- Run ordered work by dispatching the owning agent for each stage — no workflow engine executes stages.
- Concurrent sessions are allowed and surfaced through advisory presence; never wait for a concurrency lock.

## 2. Release gate

Implementation is allowed only when:

- The live release's `_RELEASE.json` `phase` field reads `IMPLEMENTATION`.
- `SPEC.md`, `PLAN.md`, and `TASKS.md` contain `**Status:** Aprovado`.
- The active task is changed from `[ ]` to `[-]` before production edits.
- The task's declared write set contains every production file to be edited.
- If any item is missing: stop, draft or repair the SDD artifact instead of editing production.

## 3. Artifact authority

| Path | Writer |
|---|---|
| `constitution.md` | operator or `product-engineer` during approved governance work |
| `releases/<id>/_RELEASE.json` | agents with file tools, per field (`dd-release-implement`'s `RELEASE-EVENTS.md`) |
| `releases/<id>/SPEC.md` | `product-engineer` |
| `releases/<id>/PLAN.md` | `product-engineer` |
| `releases/<id>/TASKS.md` | `product-engineer`; implementers may change only their task marker |
| `memory/**` | `product-engineer` in `DEFINITION` and `CLOSURE` phase |
| `backlog/**` | `project-manager` only (sole backlog author) |
| `bugs/**` | any agent may file; `product-engineer` resolves into release work |

## 4. Task markers

```text
[ ] OPEN
[-] IN PROGRESS
[x] DONE
```

- Do not take a task already marked `[-]`.
- Do not mark `[x]` without validation evidence in the implementing report.

## 5. Memory

- Memory describes the product as it is now.
- No changelog/history/version sections in `memory/**`.
- The v6 canon root carries no `assets/` member — a diagram is an in-doc fenced Mermaid block.
- Stale memory found during implementation becomes a bug or closure note — never patch memory mid-implementation.

## 6. Doctor

```bash
dadaia specs doctor
```

- `dadaia specs doctor --fix` may repair scaffoldable tree issues.
- Never use it to bypass missing approval, unclear scope, or task ownership.

## 7. Escalation

```text
[SDD BLOCKED]
Context: <context>
Release: <release-id>
Artifact: <path>
Reason: <one sentence>
Needed decision: <one concrete question or action>
```

Generated from `dadaia_workspace/public/templates/specs-AGENTS.md`.
Project teams may customize this file; `dadaia specs doctor` reports drift instead of overwriting it.
