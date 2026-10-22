---
name: dd-manager-orchestration
description: >
  Dispatch reference for the main thread (the operator's session), the only coordinator: the dispatch protocol, decision authority, escalation triggers, and main-thread discipline. Use when dispatching work or resolving a conflict. Not the order of a candidate's jobs and tasks (dd-release-implementation's RC-FLOW.md) nor worktree mechanics (worktrees/AGENTS.md).
---

# dd-manager-orchestration

## 1. Dispatch protocol

1. Resolve the target agent from the root `AGENTS.md`, heading "Who does what". Research and extraction go to `dd-researcher`, never `Explore` or `general-purpose`.
2. Only the main thread calls other agents; route a leaf's returned handoff to its `next_handoff.agent`.
3. Open every dispatch prompt with this block:

   ```
   context: <ctx>
   specs_dir: <path>
   release_id: <id>
   task_id: <J<n>.T<k> or the review target>
   worktree: <path>
   ```
4. Reports land where the root `AGENTS.md`, heading "Where things are written", says; a report feeding another agent gets a handoff under `.dadaia/handoff/<context>/`.
5. Open, merge and clean worktrees with `.dadaia/.venv/bin/dadaia worktree` (verbs: its `--help`; rules: `worktrees/AGENTS.md`).
6. The task is the unit of dispatch, never a job: sub-agents work disjoint tasks in parallel, one `wt-task-<kkk>` tree each (`worktrees/AGENTS.md`, heading "The tree").
7. Dispatch by the job file's `who:` (shape rule: `dd-release-definition`, heading "The job file — tasks"): `sr` → dd-sw-engineer-sr, `jr` → dd-sw-engineer-jr, `pe`/`cr` → the owning persona. Pass no model; the installed template decides.
8. A REJECTED verdict whose finding names a `jr` task re-dispatches that task to dd-sw-engineer-sr.
9. A ruling carries its reproduction and a consumer sweep across every repo of the context.
10. A rework brief names the finding's contract class, requires its RED test first and a sweep of every other site of the class, and carries the bug history to read, the seams with evidence and the merge hazards with sibling jobs.
11. One fresh agent per task, its full scope in its first prompt; a changed scope is a new dispatch, and an agent that stops early leaves the rest to a new dispatch against the same worktree.
12. Check commits, files and test runs yourself; a handoff reported but not written does not count.
13. A status answer counts each open class with its number.
14. When a task's work merges or its hand-back is checked, stop every agent of that task still running; a finished agent is never left running.

## 2. Conflict resolution

1. Resolve a decision by domain with the "Decision authority" table below; evidence
   means `file:line`, spec citation, command output, or handoff field.
2. On a two-agent deadlock: each agent states its position with evidence in the `findings` of its handoff or verdict; the main thread writes a synthesis naming the exact decision point.
3. Still unresolved: before launch, call `dd-grill-me` and reflect the operator's answer in SPEC, PLAN, job files, ADR, or memory per the phase; after launch, decide by law, ADRs and rulings (a failing old test: the root `AGENTS.md`, heading "The flow", test line) and log it with the label `dd-grill-me` gives an unruled default.
4. Between launch and the closure report to the operator the main thread asks nothing: every question belongs to `dd-grill-me` before launch. An act the law reserves to the operator, and a bug proposal, wait for the closure report as one batch while independent tasks continue; the exception is a block-list bug (`specs/bugs/AGENTS.md`, heading "Resolution", a security finding included), put to the operator at once since it stops every merge.

## 3. Reference tables

### Decision authority

| Domain | Primary authority | May object with evidence | Tie-breaker |
|---|---|---|---|
| Scope, SPEC, memory, backlog | dd-product-engineer | any agent | main thread; operator for a product-contract change |
| PLAN, job files, implementation, tests | dd-sw-engineer-sr | dd-code-reviewer | main thread |
| Every review lens (architecture, security, QA, product, audit, AI surface) | dd-code-reviewer | dd-sw-engineer-sr | main thread |

### Escalation triggers — a report line, not a wait

1. Required SPEC/PLAN/job files or a resolvable `_RELEASE.json` `phase` missing or not
   approved (the `specs/AGENTS.md` precondition, heading "Before implementing", fails; a `wt-hotfix` lane, or a block-list fix on a closed `wt-rc`, under `specs/bugs/AGENTS.md`, heading "Resolution", needs only its open bug).
2. A CRITICAL security issue.
3. A dispatched agent returns `[SCOPE ERROR]`.
4. Three or more unresolved conflicts open.
5. The demand cannot decompose into tasks without changing an approved SPEC.

### Main-thread discipline

| Do | Because |
|---|---|
| Chain agents only through the main thread | Every hand-off stays traceable |
| Merge a task only with its validation evidence | Acceptance is checked |
| Merge only as `worktrees/AGENTS.md`, heading "Merges, gates, review", says | One gate, one home |
| Edit production files only inside the tree its task names; a bug fix, where `specs/bugs/AGENTS.md`, heading "Resolution", says | The edit then passes its tree's merge checks and review. |
| Land an edit inside an open job as one of its tasks | Micro-dispatch: the ritual wait it adds outweighs the edit |

## 4. Done when

- Every merge meets its gate (the first row of the table above); every dispatch prompt carries the block of step 3.
- Every conflict either resolved via evidence-based authority or reported.
