---
name: dadaia-task-manager
description: >
  Mandatory protocol for every agent that modifies production files inside a
  Spec Context Project. Defines how to reserve, execute, and complete tasks in
  TASKS.md using the 3 canonical markers: [ ] OPEN → [-] IN PROGRESS → [x] DONE.
  Marker discipline is the human-auditable trace of "who took what"; the SDD
  gate hook enforces path-class × presence × phase × mode separately.
applyTo: "specs/**/TASKS.md"
---

# dadaia-task-manager — Task State Protocol

> **Not a hook-enforced mechanism.** There is no workflow engine and no gate that reads
> `TASKS.md`. Task-state transitions hold only because every agent upholds this marker
> discipline itself. This skill is the authoritative protocol for that discipline.

## The 3-marker contract

| Marker | State | Meaning |
|---|---|---|
| `[ ]` | OPEN | Task declared, nobody working on it. Default. |
| `[-]` | IN PROGRESS | An agent reserved it. Work is active. |
| `[x]` | DONE | Implemented, reviewed by QA/code/security, approved, committed. |

**Invariant:** never two simultaneous `[-]` in the same `TASKS.md`. If you find two
`[-]` when starting a session, **stop** and report to the operator.

**Honesty note — markers are discipline, not a hook check.** The SDD-gate stage of the
merged `dadaia_workspace.hooks.pre_gate` PreToolUse hook never reads `TASKS.md`,
`SPEC.md`, or any status marker. What it enforces deterministically is path-class ×
presence × phase × mode on file-write tool calls (see the `DADAIA.md` (the workspace law) §1). Marker discipline exists
for traceability and coordination between agents and the operator — uphold it even
though no hook will block you for skipping it.

## Marker discipline (the human-auditable trace)

When you work on production (any MUTATING path under the active context), the marker
trace is:

1. **Reserve.** Flip `[ ]`→`[-]` for an OPEN task that exists in the active `TASKS.md`
   (resolved via `specs/releases/ACTIVE.md`), then make an isolated
   `chore(tasks): start <task-id>` commit. That commit is the **observable
   reservation** — it is how a parallel session learns "agent X took this task".
   If the task is not OPEN, raise an interruption with the operator first.
2. **Work.** The marker stays `[-]` for the whole duration; intermediate commits are
   fine.
3. **Complete.** Flip `[-]`→`[x]` only when the acceptance criteria are met **and** the
   review gate has cleared — see below — in a final conventional-commit.

**Implementation complete is not DONE (judgment, not mechanic).** After the implementer
finishes code, unit tests, and integration tests, the task remains `[-]` until
`qa-engineer`, `code-reviewer`, and `security-reviewer` return green approval for the
same commit — boundary-by-boundary cadence: `dd-release-implement`'s gate-cadence table,
canonical home (branch contract: `DADAIA.md` §4 Gitflow, operations: `dd-gitflow-default`).
Before those approvals it is forbidden to mark
`[x]`, open a PR, request merge, deploy, close the release, write `CLOSURE.md`, or update
memory. If any reviewer requests changes, return to step 2 and keep `[-]`.

## Dispatcher relaying for a shell-less sub-agent (FR5)

`product-engineer` has no shell (D-1). When a dispatcher relays work items to a
shell-less sub-agent, it commits that sub-agent's `[ ]`→`[-]` reservation flip **before**
relaying the next work item — never batched at the end — so the marker trace stays
observable in git history at every step.

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

Under the NO-LOCKS DOCTRINE (v0.1.76) the gate never blocks a write because of another
session — races between sessions are accepted and surfaced, never prevented. The merged
`pre_gate` hook blocks for **kernel** reasons only, never for marker or concurrency
reasons (stages: root-whitelist → venv-guard → SDD gate, first-block-wins). The block
message tells you which rule fired. The SDD-gate stage's block reasons:

- **READ-mode session (self-scoped only)** — this session's **own** mode resolved READ
  (the context was bound `--mode read`); this blocks only your own MUTATING writes as
  opt-in self-protection — a foreign session's bind can never change your mode. Write
  rights require the operator binding once:
  `dadaia context bind <ctx> --mode implementation`.
- **MEMORY phase** — `specs/memory/` is writable only in DEFINITION/CLOSURE phase.
- **FROZEN / PROTECTED** — `specs/_archive/` is read-only; `.dadaia/sessions/` is
  CLI-owned (never write it via file tools).

A live foreign session's presence on the same context never blocks — the write is
**allowed** and a single throttled advisory warning is surfaced naming the other
session. There is nothing to rebind or steal.

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
must remain grep-parsable. The `chore(tasks): start` reservation commit exists so the
`[-]` state is observable by other agents and recorded in history; the operator may
squash on PR merge per-repo policy.

## In one sentence

> Before touching any production file: declare the task with `[-]` and commit. Before
> closing: only flip to `[x]` after QA/code/security approve the implementation
> handoff. No exception.

Which branch a reservation and its commits land on is the `dd-gitflow-default` skill's
contract, not this one — a task is reserved and worked on whichever branch the active
SDD stage runs on.

## Segments (ADR-1/ADR-5)

For a segmented release, the active TASKS.md lives at
`specs/releases/<release-id>/<segment>/TASKS.md` (segment = `alpha-N`/`rc-N` from
`ACTIVE.md`'s `segment:` line). Reserve/flip `[ ] -> [-] -> [x]` markers there. Flat
(no-segment) releases keep `releases/<release-id>/TASKS.md`.
