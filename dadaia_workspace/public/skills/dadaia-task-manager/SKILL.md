---
name: dadaia-task-manager
description: >
  Reserve, execute and complete TASKS.md tasks with the three canonical markers
  ([ ] open, [-] in progress, [x] done). Use before writing any production file inside
  a Spec Context Project, and when recovering a stale or conflicting marker.
---

# dadaia-task-manager — Task State Protocol

> Discipline, not a hook check — no engine reads `TASKS.md` or any marker. The marker
> trail is the human-auditable trace of "who took what"; the SDD gate enforces
> path-class × presence × phase × mode separately (`DADAIA.md` §3).

## The markers

| Marker | State | Meaning |
|---|---|---|
| `[ ]` | OPEN | Default; nobody working on it. |
| `[-]` | IN PROGRESS | Reserved; work is active. |
| `[x]` | DONE | Implemented, validated, committed. |

## Reserve → work → complete

1. Check the active `TASKS.md` first; one `[-]` at a time unless TASKS declares
   disjoint write sets.
2. Flip `[ ]` → `[-]`; commit `chore(tasks): start <task-id>` alone — the reservation
   is observable before any production write.
3. Work with the marker held at `[-]`, inside the task's declared write set;
   intermediate commits are fine.
4. Flip `[-]` → `[x]` in the task's completing commit —
   `conventional-commit(task-id): description` — once the task's own bar is met
   (suite green; the candidate-close review trio validates the candidate, cadence in
   `dd-release-implement`'s `RC-FLOW.md`).
5. To abandon: flip `[-]` → `[ ]`, commit `chore(tasks): abandon <task-id>` naming
   the reason.
6. Dispatching a shell-less sub-agent: commit its `[ ]`→`[-]` flip before relaying
   the work item — one flip per dispatch, never batched.

## Recovery

- Two simultaneous `[-]`: stop and report to the operator — never resolve it
  yourself.
- A foreign `[-]` from another session: read `git log` first, then report it to the
  operator before any transition.
- A gate block: read which stage fired (`DADAIA.md` §3); rebind mode only if your own
  session resolved READ (`dadaia context bind <ctx> --mode implementation`).

## Done when

- Every flip is observable in git history as its own commit or as the task's
  completing commit.
- No two simultaneous `[-]` in the same TASKS.md; the file stays grep-parsable
  Markdown.

## References

- `DADAIA.md` §3 — gate stages, mode resolution, path classes; §4 — which branch a
  reservation lands on (`dd-gitflow-default`).
- Live TASKS.md: `<specs_dir>/releases/<release-id>/TASKS.md`, always flat — `rc-N/`
  holds archived candidates only.
