---
name: dd-release-definition
description: >
  Turn bugs and backlog items into the live release's next closed-scope candidate:
  pick the set, review the as-is, run the mandatory grill, author the trio. Use at the start of each
  candidate's definition.
---

# dd-release-definition

> `dd-product-engineer` authors the SPEC, the engineer the as-is review, PLAN and the job files. A release has open scope; each candidate does not.

## 1. Pick the set

1. Open `specs/releases/AGENTS.md` (the area's scoped law) and follow it.
2. Inspect `specs/bugs/BUGS.jsonl` via `python3 .agents/skills/dd-bug-resolution/scripts/bugs.py status`/`stats`/`window`, each with `--specs <specs-dir>`, and read each test the window's records cite.
3. Read `specs/backlog/BACKLOG.json`'s `active[]`, consumed untriaged.
4. Each undispositioned `specs/audits/**` finding enters the SPEC with its disposition (`python3 .agents/skills/dd-audit-project/scripts/audit.py disposition`).
5. Name the SPEC's `**Origin:**`: `operator-demand`, `backlog:<ids>` or `bugs:<ids>`.
6. Write the SPEC's `## Bug window review`: compare each fix in the window (`bugs.py window --specs <specs-dir>`, `bugs.py fix --specs <specs-dir>`) against the overfitting patterns — an assert or test the fix changed; a special case on a test value; a new branch, flag or second path; a reach into another feature; deleted functionality; ≥ 2 fixes on the unit.
7. Give each fix KEEP or REBUILD; a REBUILD reworks the fix's code and what surrounds it, and keeps the fix's tests.

**Done when** the picked set is recorded; it becomes the SPEC's scope.

## 2. As-is review

- `dd-software-engineer` runs it read-only, dispatched after the pick and before the grill.
- Read every unit the picked set touches and its ledger slice (`python3 .agents/skills/dd-bug-resolution/scripts/bugs.py status`/`stats` with `--specs <specs-dir>`, `git log` on the unit); the table rides the handoff into the grill and lands as PLAN §1.
- One row per touched unit, columns `unit | today | bugs | verdict | why`; DELETE vs KEEP is `dd-codebase-design`'s deletion test; verdicts follow the root map §1 work order, ADD only for what no unit can carry (`today` `—`, `why` says why).
- REBUILD is mandatory when the unit carries ≥ 2 bugs, the demand changes its fundamental behaviour, the change would need a flag, branch, special case or second path, or its contract contradicts the demand; the engineer and the reviewer judge these triggers, no script.
- §1.1 Authorities: one row per touched question, one authority each; `consults` call it, `deleted` leave with the row's bug.
- The PLAN §1 skeleton (taught, never judged by a script):

```markdown
## 1. As-is review

| unit | today | bugs | verdict | why |
|---|---|---|---|---|
| `features/x/service.py` `run` | what it does today | 2 (`bug-a`, `bug-b`) | REBUILD | two prior fixes on this unit |

### 1.1 Authorities

| question | authority | consults | deleted |
|---|---|---|---|
| who runs x | `features/x/service.py` `run` | `cli/x.py` | `legacy_run` |
```

**Done when** every touched unit has one As-is verdict and every touched question one authority.

## 3. The mandatory grill

Call the Skill tool with `dd-grill-me` on the picked set — never skipped; a fuzzy term becomes a canonical one (`dd-domain-modeling`) before it reaches the SPEC.

## 4. Author the trio

1. Author the SPEC (Draft) after the grill: the picked set, its acceptance, every `superseded_by` link.
2. Definition runs in the rc's `define` worktree (`worktrees/AGENTS.md` §1); the trio's place is the releases law's.
3. Commit shape 5 (`dd-gitflow-default` §3a); set the `defined` milestone in `_RELEASE.json`
   (`dd-release-implementation`'s `RELEASE-EVENTS.md`).
4. SPEC says what; PLAN opens with §1 As-is review (§2) and draws the rc's DAG of jobs — Job 1 first, the Reconciliation job last, an edge where one job needs another's merge; SPEC carries `Replaces` — one bullet per current behaviour a DELETE/REBUILD row removes, or `none` with its reason.
5. SPEC in domain names (`dd-domain-modeling`'s `CONTEXT.md`); only FR, AC and T- numbered; each AC names its test level (unit, integration, E2E, or no test with its reason); sizes per the releases law.

## 5. The job file — tasks

- One file per job, `rc-<N>/tasks/<job>.md`; no `TASKS.md`, markers, stage headings, contracts or start commits.
- Every job file carries a task table. Each task has id `J<n>.T<k>`, its AC, exact `W:`, owner test file and RED tests; one owner, one session (~1 h), ~100 new code lines.
- The PLAN DAG names each job's wave and complete `W:` set. Jobs in one wave and tasks in one job have disjoint `W:` sets; validation refuses an overlap.
- Each behavior task is two dispatches: the first writes and commits the failing acceptance tests; a fresh second dispatch implements without touching a declared or fallback test path.
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

- The pick is the SPEC's `**Origin:** backlog:<ids>` line (`release.py new --origin`); the entry exits once, at closure, by `python3 .agents/skills/dd-backlog-definition/scripts/backlog.py exit` (`dd-release-implementation` RC-FLOW step 4).

## 7. Done when

- Picked set recorded; the `dd-grill-me` session completed and emitted.
- PLAN §1 names every unit the picked set touches; SPEC authored from the refined set, `Replaces` present, `**Origin:**` declared.
- Every approved requirement maps into the PLAN's DAG and >=1 job-file task.
- Every unresolved gap goes to the main thread's operator-gated intake, never a direct backlog append.

## 8. References

- `specs/releases/AGENTS.md` — release-id format, `_RELEASE.json`, the promote act; every other skill is cited where it is used.
