---
name: dadaia-task-manager
description: >
  Mandatory protocol for every agent that modifies production files inside a
  Spec Context Project. Defines how to reserve, execute, and complete tasks in
  TASKS.md using the 3 canonical markers: [ ] OPEN → [-] IN PROGRESS → [x] DONE.
  Marker discipline is the human-auditable trace of "who took what"; the SDD
  gate hook enforces path-class × presence × phase × mode separately.
tldr: "Reserve a task [ ]->[-] and commit before writing; flip [-]->[x] only after QA/code/security approve."
applyTo: "specs/**/TASKS.md"
---

# dadaia-task-manager — Task State Protocol

> Discipline, not a hook check — no engine reads `TASKS.md` or any marker.

## 1. When

| Marker | State | Meaning |
|---|---|---|
| `[ ]` | OPEN | Default; nobody working on it. |
| `[-]` | IN PROGRESS | Reserved; work is active. |
| `[x]` | DONE | Implemented, reviewed, approved, committed. |

- Before writing any MUTATING-path production file under the active context.
- Recovering a stale `[-]`, two simultaneous `[-]`, or a gate block.
- Relaying work to a shell-less sub-agent (`product-engineer`, D-1).

## 2. Steps

1. Check the active TASKS.md for two simultaneous `[-]` first.
2. Stop and report to the operator if two simultaneous `[-]` are found — never resolve it yourself.
3. Flip `[ ]` → `[-]` for an OPEN task; commit `chore(tasks): start <task-id>` alone.
4. Work with the marker held at `[-]` for the whole duration; intermediate commits are fine.
5. Wait for `qa-engineer`, `code-reviewer`, `security-reviewer` green approval on the same commit.
6. Flip `[-]` → `[x]` only after that approval, in a final conventional-commit.
7. To abandon: flip `[-]` → `[ ]`, commit `chore(tasks): abandon <task-id>` naming the reason.
8. Shell-less sub-agent dispatch: commit its `[ ]`→`[-]` flip before relaying the next work item — never batched.
9. On an old foreign `[-]`: do not flip it; read `git log` first.
10. Report the old foreign `[-]` to the operator before any transition.
11. On a gate block: read which stage fired (`DADAIA.md` §3).
12. Rebind mode only if your own session resolved READ (`dadaia context bind <ctx> --mode implementation`).

## 3. Done when

- Every flip is a standalone commit, observable in git history.
- `[x]` exists only after all three reviewers approved the same commit.
- No two simultaneous `[-]` in the same TASKS.md.
- TASKS.md stays grep-parsable Markdown.

## 4. References

- `DADAIA.md` §3 — gate stages, mode resolution, path classes, block reasons.
- `DADAIA.md` §4 (Gitflow) / `dd-gitflow-default` — which branch a reservation lands on.
- `dd-release-implement` (`RC-FLOW.md`) — the review/QA gate-cadence table.
- TASKS.md primary: `<specs_dir>/releases/<release-id>/TASKS.md` — always flat; `rc-N/` holds archived candidates only.
- TASKS.md legacy: `specs/features/*/TASKS.md` under `SDD_LEGACY_FEATURES=1`; root `<specs_dir>/TASKS.md` is migration-only.
