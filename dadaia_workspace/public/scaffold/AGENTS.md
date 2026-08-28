# specs/AGENTS.md — Spec Context Rules

Scope: this file governs only the `specs/` tree of one Spec Context Project.
Root workspace behavior is in the workspace `AGENTS.md`; production-source
behavior is in the repo-local `AGENTS.md`.

## Load Order

Before writing or reviewing SDD artifacts, read:

```text
constitution.md
memory/ARCHITECTURE.md
memory/TECHSTACK.md
memory/product/index.md
releases/<release-id>/RELEASE.json    (phase field read directly, no fold)
releases/<release-id>/SPEC.md
releases/<release-id>/PLAN.md
releases/<release-id>/TASKS.md
```

## Canon Members

A specs root carries exactly these members — nothing else:

| Member | Holds |
|---|---|
| `AGENTS.md` | this file |
| `constitution.md` | absolute product laws |
| `memory/` | current product truth (`memory/AGENTS.md`) |
| `releases/` | release SPEC/PLAN/TASKS/RELEASE.json, `_ideas/` pre-approval drafts, `_archive/releases_histo.jsonl` history |
| `backlog/` | the live demand queue, `_archive/` history |
| `bugs/` | the bug ledger, `_archive/` history |
| `audits/` | audit records, `_archive/` history |
| `ADRs/` | decision records (`ADRs/AGENTS.md`) |

No root `_archive/`, no `.gitkeep`, no stray dotfile — `dadaia specs doctor` flags
anything else. Use `backlog/` and `bugs/` for intake and triage; they are not approval
gates.

Run ordered work by dispatching the owning agent for each stage — backlog-definition,
release-definition, implementation with its reviews and gates, and audit — against
these documents; no workflow engine executes the stages for you. Concurrent sessions are
allowed and surfaced through advisory presence; never wait for or create a workspace
concurrency lock.

## Release Gate

Implementation is allowed only when:

- The live release's `RELEASE.json` `phase` field reads `IMPLEMENTATION` — the SDD
  gate's own decision authority (SPEC FR4, v0.5.0 T-050-21A, A4.1).
- `SPEC.md`, `PLAN.md`, and `TASKS.md` contain `**Status:** Aprovado`.
- The active task is changed from `[ ]` to `[-]` before production edits.
- The task's declared write set contains every production file to be edited.

If any item is missing, stop. Draft or repair the SDD artifact instead of
editing production.

## Artifact Authority

| Path | Writer |
|---|---|
| `constitution.md` | operator or `product-engineer` during approved governance work |
| `releases/<id>/RELEASE.json` | agents with file tools, per field — `dd-release-implement`'s `RELEASE-EVENTS.md` |
| `releases/<id>/SPEC.md` | `product-engineer` |
| `releases/<id>/PLAN.md` | `product-engineer` |
| `releases/<id>/TASKS.md` | `product-engineer`; implementers may change only their task marker |
| `memory/**` | `product-engineer` in `CLOSURE` only |
| `backlog/**` | `project-manager` only (sole backlog author; `product-engineer` is a read-only consumer) |
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
- The v6 canon root carries no `assets/` member; a diagram belongs in-doc as a
  fenced Mermaid block (memory carries no external image references).
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
