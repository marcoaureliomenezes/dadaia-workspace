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

> **Not the lifecycle enforcement mechanism.** Ordered task reservation and the
> per-phase lifecycle sequence are owned by the dadaia-workflows (`dadaia lifecycle`),
> whose Python gates own task-state transitions. This skill is reference / manual-operator
> guidance for the human-auditable marker discipline only.
>
> **Default action:** when the operator asks for implementation/review/closure work that
> maps to a supported lifecycle phase, run the matching `dadaia lifecycle ...` workflow
> first. Use the marker mechanics below directly only inside that workflow's worker
> context or after a registered workflow bug justifies manual fallback.

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
lease × phase × mode on file-write tool calls (see the `workspace-protocol` rule §1). Marker discipline exists
for traceability and coordination between agents and the operator — uphold it even
though no hook will block you for skipping it.

## Mechanics moved to the engine (D12)

The **ordered task-state mechanics** — reserve `[ ]`→`[-]`, run the work, complete
`[-]`→`[x]`, and the per-step sequencing — are now enforced by the lifecycle engine:
`features/lifecycle/state_machine.py` owns the legal phase transitions
(`is_legal_transition`, `TransitionDecision`) and `features/lifecycle/pipeline.py` owns
per-step sequencing (each `PipelineStep` carries the `task_id` it transitions). This
skill no longer narrates that ordered procedure; it records the **human-auditable marker
discipline** the engine's transitions correspond to, plus the judgment a human applies
when the mechanics meet reality (recovery, gate blocks, where TASKS.md lives).

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
same commit (per the `release-governance` cadence: alpha-N boundaries are qa-only;
reviews mature the release, and the push boundary itself is mechanically gated — the
pre-push security-verdict chokepoint requires an APPROVED `security-reviewer` handoff
whose `metrics.commit_sha` equals each pushed ref sha, per push-cycle). UI tasks also
require `design-specialist` approval. Before those approvals it is forbidden to mark
`[x]`, open a PR, request merge, deploy, close the release, write `CLOSURE.md`, or update
memory. If any reviewer requests changes, return to step 2 and keep `[-]`.

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

The merged `pre_gate` hook blocks for **kernel** reasons, never for marker reasons
(stages: root-whitelist → venv-guard → SDD gate, first-block-wins). The block message
tells you which rule fired. The SDD-gate stage's reasons:

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
must remain grep-parsable. The `chore(tasks): start` reservation commit exists so the
`[-]` state is observable by other agents and recorded in history; the operator may
squash on PR merge per-repo policy.

## In one sentence

> Before touching any production file: declare the task with `[-]` and commit. Before
> closing: only flip to `[x]` after QA/code/security approve the implementation
> handoff. No exception.

## Segments (ADR-1/ADR-5)

For a segmented release, the active TASKS.md lives at
`specs/releases/<release-id>/<segment>/TASKS.md` (segment = `alpha-N`/`rc-N` from
`ACTIVE.md`'s `segment:` line). Reserve/flip `[ ] -> [-] -> [x]` markers there. Flat
(no-segment) releases keep `releases/<release-id>/TASKS.md`.
