---
name: dd-release-definition
description: >
  Turn bugs and backlog items into the live release's next closed-scope candidate:
  pick the set, review the as-is, run the mandatory grill, author the trio. Use at the start of each
  candidate's definition.
---

# dd-release-definition

> `dd-product-engineer` authors the SPEC, the engineer the as-is review, PLAN and TASKS. A release has open scope; each candidate does not.

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
- The PLAN §1 skeleton — `release.py phase IMPLEMENTATION` refuses a PLAN without either table, an empty authority or a question with two, and a Parallel schedule without its table header, with a width unequal to its task ids, without `Critical path` in the section, or with overlapping `W:` in one step (`release.py check` refuses the same on a live trio):

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
2. Definition runs on the work branch (`<work>M.m.p`, the constitution's `gitflow:`); the trio's place is the releases law's.
3. Commit shape 5 (`dd-gitflow-default` §3a); set the `defined` milestone in `_RELEASE.json`
   (`dd-release-implementation`'s `RELEASE-EVENTS.md`).
4. PLAN opens with §1 As-is review (§2); SPEC carries `Replaces` — one bullet per current behaviour a
   DELETE/REBUILD row removes, or `none` with its reason.
5. SPEC in domain names (`dd-domain-modeling`'s `CONTEXT.md`); only FR, AC and T- numbered; sizes per the releases law.

## 5. TASKS as tracer bullets

- Every task carries `blocked by:` (true edges only, or `none`) and `delivers:` ("after this task the operator can …").
- The FIRST tasks cut a thin end-to-end path; a group verifiable only at its last task is misordered.
- DELETE/REBUILD tasks precede ADD tasks, each expand–contract (add, switch consumers, delete the old) and independently green.
- Each task is one `impl` worktree; `W:` is exact.
- PLAN carries a `Parallel schedule` sizing parallel worktrees, bug fixes included (`worktrees/AGENTS.md` §2): a table walking the `blocked by:` graph and `Critical path` somewhere in the section.
- Two tasks share a step only when their `W:` sets are disjoint, except `TASKS.md`, the `*.jsonl` ledgers, and each file the Parallel schedule section declares as the word derived followed by its backticked path (for example: derived `gen/index.json`); a declared path exempts every `W:` path that ends with it at a `/` boundary. A task's `W:` sits on its one task line; a backticked path inside parentheses is named, not written.

```markdown
## 5. Parallel schedule

| step | tasks open together | width | how |
|---|---|---|---|
| 1 | T-1, T-2 | 2 | one impl worktree each |

- Critical path: T-1 → T-3 = 2 steps.
- Overlap check: disjoint except `TASKS.md`, the `*.jsonl` ledgers and the derived `gen/index.json`.
```

- A task's `RED:` names the owning test file (`dd-test-stewardship`, intent and admission).
- A task with no statable `delivers:` is folded, or goes back to the SPEC.

## 6. Declaring consumption

- The pick is the SPEC's `**Origin:** backlog:<ids>` line (`release.py new --origin`); the entry exits once, at closure, by `python3 .agents/skills/dd-backlog-definition/scripts/backlog.py exit` (`dd-release-implementation` RC-FLOW step 7).

## 7. Done when

- Picked set recorded; the `dd-grill-me` session completed and emitted.
- PLAN §1 names every unit the picked set touches; SPEC authored from the refined set, `Replaces` present, `**Origin:**` declared.
- Every approved requirement maps into PLAN strategy and >=1 TASKS entry.
- Every unresolved gap goes to the main thread's operator-gated intake, never a direct backlog append.

## 8. References

- `specs/releases/AGENTS.md` — release-id format, `_RELEASE.json`, the promote act; every other skill is cited where it is used.
