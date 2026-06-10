---
name: dadaia-task-manager
description: >
  Mandatory protocol for every agent that modifies production files inside a
  Spec Context Project. Defines how to reserve, execute, and complete tasks in
  TASKS.md using the 3 canonical markers: [ ] OPEN → [-] IN PROGRESS → [x] DONE.
  Marker discipline is the human-auditable trace of "who took what"; the SDD
  gate hook enforces path-class × lease × phase × mode separately.
applyTo: "specs/**/TASKS.md"
---

# dadaia-task-manager — Task State Protocol

## The 3-marker contract

| Marker | State | Meaning |
|---|---|---|
| `[ ]` | OPEN | Task declared, nobody working on it. Default. |
| `[-]` | IN PROGRESS | An agent reserved it. Work is active. |
| `[x]` | DONE | Implemented, reviewed by QA/code/security, approved, committed. |

**Invariant:** never two simultaneous `[-]` in the same `TASKS.md`. If you find two
`[-]` when starting a session, **stop** and report to the operator.

**Honesty note — markers are discipline, not a hook check.** The SDD gate hook
(`dadaia_workspace.hooks.sdd_gate`) never reads `TASKS.md`, `SPEC.md`, or any status
marker. What it enforces deterministically is path-class × lease × phase × mode on
file-write tool calls (see the `workspace-protocol` rule §1). Marker discipline exists
for traceability and coordination between agents and the operator — uphold it even
though no hook will block you for skipping it.

## The 4-step protocol

When you are about to work on production (any MUTATING path under the active context),
follow these 4 steps **in order**:

### Step 1 — Identify the task

Read the relevant `TASKS.md` (primary: `specs/releases/<active>/TASKS.md`, resolved via
`specs/releases/ACTIVE.md`; legacy compat: if `releases/ACTIVE.md` is absent, fall back
to `specs/features/<feat>/TASKS.md` with `SDD_LEGACY_FEATURES=1`).
Identify the task you will execute. It **must** exist and be `[ ]` (OPEN). If it is not
OPEN, raise an interruption with the operator before proceeding.

### Step 2 — Reserve (`[ ]` → `[-]`) and commit

Use Edit/Write to flip the task marker from `[ ]` to `[-]`. Then make an **isolated**
commit containing only that change:

```
chore(tasks): start <task-id>
```

Example:
```
chore(tasks): start T128
```

That commit is the **observable reservation** saying "agent X took this task". Other
agents in parallel sessions see it via `git pull` or by re-reading the file.

### Step 3 — Do the work

Implement. Multiple commits are fine during this phase (intermediates, refactors,
fixes). The marker stays `[-]` for the whole duration.

### Step 4 — Complete (`[-]` → `[x]`) and commit

When the work is done and the task's acceptance criteria are satisfied:

**Implementation complete is not DONE.** After the implementer finishes code, unit
tests, and integration tests, the task remains `[-]` until `qa-engineer`,
`code-reviewer`, and `security-reviewer` return green approval for the same commit
(per the `release-governance` cadence: alpha-N boundaries are qa-only; the full trio
runs at rc-N ship). UI tasks also require `design-specialist` approval.

Before those approvals, it is forbidden to mark `[x]`, open a PR, request merge,
deploy, close the release, write `CLOSURE.md`, or update memory. If any reviewer
requests changes, return to Step 3 and keep `[-]`.

1. Flip the marker `[-]` → `[x]`.
2. Make the **final task commit** with conventional commits, including in the diff both
   the `[x]` marker and any final pending file.

Example final commit:
```
feat(orchestration): implement run.resume idempotency (T128)
```

## Recovery — when something goes wrong

### I found an old `[-]` from another session

**Do not silently flip it to `[x]`.** You do not know whether the task was completed or
abandoned. Stop, read `git log` to understand the history, and report to the operator
before any transition.

### I found two simultaneous `[-]`

Invariant violation. Stop. Report to the operator. Wait for a decision before any
production edit.

### I need to abandon a task without completing it

Flip the marker `[-]` → `[ ]` and commit:
```
chore(tasks): abandon <task-id>
```
Document the reason in the commit message. Another agent can pick up the task later.

### The SDD gate blocked my write

The gate hook blocks for **kernel** reasons, never for marker reasons. The block
message tells you which rule fired:

- **Live foreign lease** — another session genuinely holds this context's lease
  (heartbeat fresh, or its recorded harness pid is still running — a live holder is
  never stolen). Additive paths (`specs/bugs/`, `specs/backlog/`, `specs/audits/`,
  `.dadaia/reports|handoff|tmp/`) remain writable; the lease frees itself when the
  holder finishes or dies. Never ask the operator to rebind or steal.
- **READ-mode session** — this session's mode resolved READ (the context was bound
  `--mode read`; bind refreshes the context's incumbent pointer, which the gate reads).
  Write rights require the operator binding once:
  `dadaia context bind <ctx> --mode implementation`.
- **MEMORY phase** — `specs/memory/` is writable only in DEFINITION/CLOSURE phase.
- **FROZEN / PROTECTED** — `specs/_archive/` is read-only; `.dadaia/sessions/` is
  CLI-owned (never write it via file tools).

A missing `[-]` marker never produces a gate block — it produces a **discipline
violation** that reviewers and the operator will catch. Reserve anyway, always.

## Where TASKS.md lives

- **Primary:** `<specs_dir>/releases/<active-release-id>/TASKS.md` — the active release
  (pointed at by `<specs_dir>/releases/ACTIVE.md`) keeps its tasks here.
- **Legacy compat:** `<specs_dir>/features/*/TASKS.md` — only when
  `SDD_LEGACY_FEATURES=1` during a migration window.
- **Root (legacy):** `<specs_dir>/TASKS.md` — migration-only; `specs doctor` reports it
  as a structural error afterwards.

It is your responsibility to work inside the scope the reserved task declares — no
hook validates that the `[-]` task covers the exact target file.

TASKS.md **stays in Markdown**. The `[ ]/[-]/[x]` markers are a machine contract and
must remain grep-parsable.

## Why the extra `chore(tasks): start` commit?

Without it, the `[-]` state is not observable by other agents nor recorded in history.
The cost of one extra commit is trivial; the traceability gain is high. If history
pollution bothers anyone, the operator squashes on PR merge — per-repo policy.

## In one sentence

> Before touching any production file: declare the task with `[-]` and commit. Before
> closing: only flip to `[x]` after QA/code/security approve the implementation
> handoff. No exception.

## Segments (ADR-1/ADR-5)

For a segmented release, the active TASKS.md lives at
`specs/releases/<release-id>/<segment>/TASKS.md` (segment = `alpha-N`/`rc-N` from
`ACTIVE.md`'s `segment:` line). Reserve/flip `[ ] -> [-] -> [x]` markers there. Flat
(no-segment) releases keep `releases/<release-id>/TASKS.md`.
