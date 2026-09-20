---
name: dd-manager-orchestration
description: >
  Dispatch reference for project-manager: the dispatch protocol, decision authority, escalation triggers, forbidden actions, and the
  which-skill-when router. Use when dispatching work, resolving a conflict, or
  routing a demand to the right skill.
---

# dd-manager-orchestration

> No engine runs the SDD flow — each stage is agent-dispatched (`DADAIA.md` §1).
> This skill is reference for the dispatcher, never a substitute for the SDD
> documents. It stays generic: no operator-private names, hosts, or repo slugs.

## 1. Dispatch protocol

1. Resolve the target agent from the ownership table (`DADAIA.md` §2.1); the stage
   it enters is `DADAIA.md` §1.1.
2. Only the top-level dispatcher calls other agents — a leaf specialist cannot chain
   further dispatch; route a leaf's returned handoff to its `next_handoff.agent`.
3. Open every dispatch prompt with the Input Contract block: context, specs_dir,
   release_id, task_id, report_dir, handoff_dir, allowed_write_paths.
4. Reports land in the repo's reports home (`DADAIA.md` §5.2); every report
   feeding another agent gets a handoff under `.dadaia/handoff/<context>/`.
5. The review/QA sequence holds by discipline (dispatcher, implementer, reviewer
   each uphold their half); git chokepoints are the only mechanical backstop.

## 2. Conflict resolution

1. Resolve a decision by domain with the Decision Authority table (§3); evidence
   means `file:line`, spec citation, command output, or handoff field.
2. On a two-agent deadlock: each agent writes a `Conflict Position` section in its
   report; the dispatcher writes a synthesis naming the exact decision point.
3. Still unresolved: call `dd-grill-me`, ask the operator one concrete question,
   and reflect the answer in SPEC, PLAN, TASKS, ADR, or memory per the phase.
4. Stop and surface to the operator on any Escalation trigger (§3); never perform a
   Forbidden action (§3).

## 3. Reference tables

### Decision authority

| Domain | Primary authority | May object with evidence | Tie-breaker |
|---|---|---|---|
| Scope, SPEC, memory, backlog | project-manager | any agent | operator |
| PLAN, TASKS, implementation, tests | software-engineer | code-reviewer | project-manager |
| Every review lens (architecture, security, QA, product, audit, AI surface) | code-reviewer | software-engineer | project-manager |

### Escalation triggers — stop and surface to the operator

1. Required SPEC/PLAN/TASKS or a resolvable `_RELEASE.json` `phase` missing or not
   approved.
2. A CRITICAL security issue.
3. A dispatched agent returns `[SCOPE ERROR]`.
4. Three or more unresolved conflicts open.
5. The work needs an optional domain pack that is not installed.
6. The demand cannot decompose into tasks without changing an approved SPEC.

### Forbidden actions

| Action | Why |
|---|---|
| Recursive agent chains without operator approval | Breaks traceability |
| Marking tasks DONE without validation evidence | Skips acceptance |
| Push, PR, merge, deploy, closure, or `[x]` before the reviewer's `APPROVED` | Bypasses the quality gate |
| Editing production files without a `[-]` reservation | Breaks task traceability |
| Private/project-specific details in public assets | Security and portability |

## 4. The router — which skill, when

The flow every demand travels, and the skill that owns each moment:

**Arm A (feature):**
`dd-grill-me` (ambiguous intake) → `dd-backlog-definition` (curation; the
operator-gated intake) → `dd-release-definition` (candidate trio, mandatory grill)
→ `dd-release-implementation` (task arc through the promote-or-continue gate).

**Arm B (bug):** `dd-bug-registration` (classify, redact, append — any agent, the
moment a contract breaks) → `dd-bug-resolution` (seven-phase method + resolve).

**Running underneath, on every lane:**
- `dd-spec-navigator` — session grounding (context → memory → trio).
- `dd-gitflow-default` — branches, commit shapes, PRs, the push gate.
- `dd-test-stewardship` — every test's lifecycle.
- `dd-code-review` — the three-axis review before the candidate's PR.
- `dd-handoff-emitter` — emission at every task end.

**Vocabulary layers (reach for them when the words are the problem):**
- `dd-codebase-design` — module/seam/depth; the deletion test on any growing diff.
- `dd-domain-modeling` — the domain glossary; sharpening terms and offering ADRs.

**Health and upkeep:**
- `dd-architecture-survey` — deepening candidates at each candidate close (architecture lens).
- `dd-audit-project` — the three-pillar drift audit (`DADAIA.md` §6.8, audit lens).

**Harness:** `dd-ai-eng-knowhow` (primitives literacy and the AUTHORING contract),
`dd-cli-library` (CLI idioms for every Bash-capable agent).

## 5. Done when

- Every dispatch prompt carries the Input Contract block and a handoff on
  completion.
- Every conflict either resolved via evidence-based authority or escalated.
- No forbidden action occurred.
