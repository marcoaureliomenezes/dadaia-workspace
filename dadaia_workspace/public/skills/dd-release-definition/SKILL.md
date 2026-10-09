---
name: dd-release-definition
description: >
  Define the live release's next closed-scope candidate from bugs, backlog items and audit findings:
  pick the set, the As-is review (PLAN §1), the SPEC, the PLAN's job DAG and the rc-<N>/tasks/<job>.md
  job files. Use when drafting a candidate in its define tree or writing its SPEC, PLAN or a job file.
  The grill is the main thread's dd-grill-me; implementing tasks is dd-release-implementation's.
---

# dd-release-definition

> `dd-product-engineer` authors the SPEC, `dd-software-engineer` the as-is review, PLAN and the job files. A release has open scope; each candidate does not.

## 1. Pick the set

1. Open `specs/releases/AGENTS.md` (the area's scoped law) and follow it.
2. Inspect `specs/bugs/BUGS.jsonl` via `python3 .agents/skills/dd-bug-resolution/scripts/bugs.py status`/`stats`, each with `--specs <specs-dir>`; read the prior candidate's `## Bug window review` and the ledger slice of `.agents/skills/dd-bug-resolution/LINEAGE.md` §The window and §The filter.
3. Read `specs/backlog/BACKLOG.json`'s `active[]`, consumed untriaged.
4. Each undispositioned `specs/audits/**` finding enters the SPEC's Origin as `findings:<id>`.
5. Name the SPEC's `**Origin:**` per `specs/releases/AGENTS.md` §2.
6. Write the SPEC's `## Bug window review`: list the fixes with `grep -o '"fix_sha": "[0-9a-f]*"' <specs-dir>/bugs/BUGS.jsonl`, then `git show <fix_sha>` each and compare that fix against the overfitting patterns — an assert or test the fix changed; a special case on a test value; a new branch, flag or second path; a reach into another feature; deleted functionality; ≥ 2 fixes on the unit.
7. Give each fix KEEP or REBUILD; a REBUILD reworks the fix's code and what surrounds it, and keeps the fix's tests.

## 2. As-is review

- `dd-software-engineer` runs it read-only, dispatched after the pick and before the grill.
- Read every unit the picked set touches and its ledger slice (its `surface` records in `BUGS.jsonl` and `_archive/bugs_histo.jsonl`, `git log` on the unit); the table rides the handoff into the grill and lands as PLAN §1.
- One row per touched unit, columns `unit | today | bugs | verdict | why`; DELETE vs KEEP is the deletion test (delete the unit: does complexity vanish or reappear across callers?); verdicts follow the root map §1 work order, ADD only for what no unit can carry (`today` `—`, `why` says why).
- REBUILD is mandatory when the unit carries ≥ 2 bugs, the demand changes its fundamental behaviour, the change would need a flag, branch, special case or second path, or its contract contradicts the demand; the engineer and the reviewer judge these triggers.
- §1.1 Authorities: one row per touched question, one authority each; `consults` call it, `deleted` leave with the row's bug.
- The PLAN §1 skeleton:

```markdown
## 1. As-is review

| unit | today | bugs | verdict | why |
|---|---|---|---|---|
| `features/x/service.py` `run` | what it does today | 2 (`bug-a`, `bug-b`) | REBUILD | two prior fixes on this unit |

### 1.1 Authorities

| question | authority | consults | deleted |
|---|---|---|---|
| who runs x | `features/x/service.py` `run` | `cli/x.py` | `legacy_run` |

## DAG

| job | waits on | wave | W: |
|---|---|---|---|
| Job 1 | — | 1 | `src/x.py`, `tests/unit/test_x.py` |
```

## 3. The mandatory grill

The main thread runs `dd-grill-me` on the picked set before the SPEC — never skipped.

## 4. Author the SPEC, PLAN and job files

1. Author the SPEC (Draft) after the grill: the picked set, its acceptance, every `superseded_by` link.
2. Definition runs in the rc's `define` worktree (`worktrees/AGENTS.md` §1); the files' place is the releases law's.
3. Commit shape 5 (`dd-gitflow-default` §3a); after the operator approves SPEC and PLAN, `release.py phase IMPLEMENTATION --sha <sha>` sets `defined` (`dd-release-implementation`'s `RELEASE-EVENTS.md`).
4. SPEC says what; PLAN opens with §1 As-is review (§2) and draws the rc's DAG of jobs — Job 1 first, the Reconciliation job last, an edge where one job needs another's merge; SPEC carries `Replaces` — one bullet per current behaviour a DELETE/REBUILD row removes, or `none` with its reason.
5. SPEC in the repo's existing domain names; only FR, AC and T- numbered; each AC names its test level (unit, integration, E2E, or no test with its reason); sizes per the releases law.

## 5. The job file — tasks

- One file per job, `rc-<N>/tasks/job<n>.md`, its PLAN DAG row `Job <n>`.
- Every job file carries a task table. Each task has id `J<n>.T<k>`, its AC, exact `W:`, owner test file and RED tests; one owner, one session (~1 h), ~100 new code lines.
- The PLAN DAG names each job's wave and complete `W:` set.
- Each behavior task runs as two dispatches (`worktrees/AGENTS.md` §2).
- A task is `running` while its task worktree exists. A cancelled task keeps its row and reason.
- DELETE/REBUILD tasks precede ADD tasks; a task with no statable AC is folded, or goes back to the SPEC.

```markdown
# Job 2 — feature x

| task | AC | `W:` | outcome |
|---|---|---|---|
| J2.T1 | AC2.1 | `tests/unit/test_x.py` | RED acceptance test |
| J2.T2 | AC2.1 | `src/x.py` | implementation; owner `tests/unit/test_x.py` |
```

## 6. Declaring consumption

- The pick is the SPEC's `**Origin:** backlog:<ids>` line (`release.py new --origin`); its exit is closure work (`dd-release-implementation`'s `RC-FLOW.md` Step 4).

## 7. Done when

- Picked set recorded; the `dd-grill-me` session completed and emitted.
- PLAN §1 gives every touched unit one verdict and every touched question one §1.1 authority; SPEC authored from the refined set, `Replaces` present, `**Origin:**` declared.
- Every approved requirement maps into the PLAN's DAG and >=1 job-file task.
- `python3 .agents/skills/dd-release-implementation/scripts/release.py check --specs <specs-dir>` exits 0 (Origin line, DAG, `W:` overlaps).
- Every unresolved gap rides the handoff to the main thread's operator-gated intake, the backlog's one entry path.

## 8. References

- `specs/releases/AGENTS.md` — release-id format, `_RELEASE.json`, the promote act; every other skill is cited where it is used.
