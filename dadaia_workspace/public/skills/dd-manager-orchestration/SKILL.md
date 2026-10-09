---
name: dd-manager-orchestration
description: >
  Dispatch reference for the main thread (the operator's session), the only coordinator: the dispatch protocol, decision authority, escalation triggers, and main-thread discipline. Use when dispatching work or resolving a conflict. Not the order of a candidate's jobs and tasks (dd-release-implementation's RC-FLOW.md) nor worktree mechanics (worktrees/AGENTS.md).
---

# dd-manager-orchestration

## 1. Dispatch protocol

1. The main thread dispatches the three roles; resolve the target agent and task from the root `AGENTS.md` map §2.
2. Only the main thread calls other agents — a leaf specialist cannot chain
   further dispatch; route a leaf's returned handoff to its `next_handoff.agent`.
3. Open every dispatch prompt with this block:

   ```
   context: <ctx>
   specs_dir: <path>
   release_id: <id>
   task_id: <J<n>.T<k> or the review target>
   worktree: <path>
   ```
4. Reports land where the root `AGENTS.md` map §4 says; every report
   feeding another agent gets a handoff under `.dadaia/handoff/<context>/`.
5. Open, merge and clean worktrees with `python3 .agents/skills/dd-gitflow-default/scripts/worktree.py new|merge|clean` (`worktrees/AGENTS.md`).
6. The task is the unit of dispatch (ADR 0190), never a job: sub-agents work disjoint tasks in parallel, one per task worktree (`worktrees/AGENTS.md` §1).

## 2. Conflict resolution

1. Resolve a decision by domain with the Decision Authority table (§3); evidence
   means `file:line`, spec citation, command output, or handoff field.
2. On a two-agent deadlock: each agent states its position with evidence in the `findings` of its handoff or verdict; the main thread writes a synthesis naming the exact decision point.
3. Still unresolved: call `dd-grill-me`, ask the operator one concrete question,
   and reflect the answer in SPEC, PLAN, job files, ADR, or memory per the phase.
4. Stop and surface to the operator on any Escalation trigger (§3); keep the §3
   discipline table.

## 3. Reference tables

### Decision authority

| Domain | Primary authority | May object with evidence | Tie-breaker |
|---|---|---|---|
| Scope, SPEC, memory, backlog | dd-product-engineer | any agent | operator |
| PLAN, job files, implementation, tests | dd-software-engineer | dd-code-reviewer | operator |
| Every review lens (architecture, security, QA, product, audit, AI surface) | dd-code-reviewer | dd-software-engineer | operator |

### Escalation triggers — stop and surface to the operator

1. Required SPEC/PLAN/job files or a resolvable `_RELEASE.json` `phase` missing or not
   approved (`python3 .agents/skills/dd-release-implementation/scripts/release.py check --specs <specs-dir>` exits non-zero; a hotfix job needs only its open bug).
2. A CRITICAL security issue.
3. A dispatched agent returns `[SCOPE ERROR]`.
4. Three or more unresolved conflicts open.
5. The demand cannot decompose into tasks without changing an approved SPEC.

### Main-thread discipline

| Do | Why |
|---|---|
| Chain agents only through the main thread, with operator approval | Breaks traceability |
| Merge a task only with its validation evidence | Skips acceptance |
| Write a verdict, merge, deploy or close only after the reviewer's `APPROVED` | `worktrees/AGENTS.md` §2 |
| Edit production files only inside a job's or task's worktree | Breaks task traceability |
| Land an edit inside an open job as one of its tasks | Micro-dispatch: the ritual wait it adds outweighs the edit |
| Keep private/project-specific details out of public assets | Security and portability |

## 4. Done when

- Every merge of the session names an APPROVED verdict file; every dispatch prompt carries that block.
- Every conflict either resolved via evidence-based authority or escalated.
- The §3 discipline held.
