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
2. Inspect `specs/bugs/BUGS.jsonl` via `python3 .agents/skills/dd-bug-resolution/scripts/bugs.py status`/`stats`.
3. Read `specs/backlog/BACKLOG.json`'s `active[]`, consumed untriaged.
4. Each undispositioned `specs/audits/**` finding enters the SPEC with its disposition (`python3 .agents/skills/dd-audit-project/scripts/audit.py disposition`).
5. Name the SPEC's `**Origin:**`: `operator-demand`, `backlog:<ids>` or `bugs:<ids>`.

**Done when** the picked set is recorded; it becomes the SPEC's scope.

## 2. As-is review

- `dd-software-engineer` runs it read-only, dispatched after the pick and before the grill.
- Read every unit the picked set touches and its ledger slice (`python3 .agents/skills/dd-bug-resolution/scripts/bugs.py status`/`stats`, `git log` on the unit); the table rides the handoff into the grill and lands as PLAN §1.
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
5. SPEC in domain names (`dd-domain-modeling`'s `CONTEXT.md`); only FR, AC and T- numbered; sizes per the releases law.

## 5. The job file — stages and tasks

- One file per job, `rc-<N>/tasks/<job>.md`; no `TASKS.md`, no markers, no start commits. `release.py check` and `phase IMPLEMENTATION` refuse a file with no `## Stage` heading, a stage with no `- Contract:` line, or a stage 1 whose tasks write anything but tests.
- A stage's contract is fixed when it opens: its exit tests by level, its envelope (the `W:` union it may touch) and the ACs it serves.
- Stage 1 writes every acceptance test RED, as a strict xfail; later stages turn them green; tasks of one stage write disjoint `W:`.
- A task: id `J<n>.S<m>.T<k>`, its AC, its exact `W:`, its owner test file, its RED tests; one owner, one session (~1 h), ~100 new code lines.
- A task is `running` while its task worktree exists; the job's close task writes `done` once.
- A task born inside an open stage cites its AC; a cancelled one keeps its line and its reason; a file two tasks write is listed as hot with one owner task — the audit measures these (`dd-audit-project` PILLAR-SPECS).
- DELETE/REBUILD tasks precede ADD tasks; a task with no statable AC is folded, or goes back to the SPEC.

```markdown
# Job 2 — the bug window

## Stage J2.S1 — RED

- Contract: exit tests `tests/unit/test_x.py` strict xfail; envelope `tests/**`; ACs AC2.1
- J2.S1.T1 — AC2.1 · `W:` `tests/unit/test_x.py` · owner `tests/unit/test_x.py`

## Stage J2.S2 — fix

- Contract: exit tests unit + integration; envelope `src/**`; ACs AC2.1
- J2.S2.T1 — AC2.1 · `W:` `src/x.py` · owner `tests/unit/test_x.py`
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
