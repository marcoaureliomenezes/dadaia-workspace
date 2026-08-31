---
name: dd-manager-orchestration
description: >
  Generic dispatch reference for project-manager and project-auditor agents.
  Defines the default public agent inventory, SDD stage inventory, dispatch
  protocol, mediation rules, escalation triggers, and forbidden actions.
tldr: "Dispatch reference: 9-agent inventory, SDD stage table, dispatch protocol, decision authority, escalation, forbidden actions."
applyTo: ".dadaia/handoff/**"
---

# dd-manager-orchestration

> Not an enforcement mechanism. No engine runs the SDD flow — each stage is agent-dispatched (`DADAIA.md` §1).
> This skill is reference/dispatcher guidance, never a substitute for the SDD documents.

Stays generic: no operator-private project names, hostnames, IPs, customer names, private repo slugs, or optional domain-pack assumptions.

## 1. When

- `project-manager`/`project-auditor` dispatching work to any core agent.
- Resolving a mediation conflict, an escalation trigger, or a decision-authority question.

## 2. Steps

1. Resolve the target agent from the inventory table (§4) by phase, mission, and "do not call when" clause.
2. Confirm only the top-level dispatcher calls other agents — a leaf specialist cannot chain further dispatch in either harness.
3. Route a leaf's returned handoff to its `next_handoff.agent` — this is handoff routing, not executable dispatch.
4. Build the sub-agent prompt with `subagent_type`, `description`, `prompt` fields.
5. Open every dispatch prompt with the Input Contract block (context, specs_dir, release_id, task_id, report_dir, handoff_dir, allowed_write_paths).
6. Write reports to `.dadaia/reports/<context-name>/<agent-name>/<UTC>-<task-slug>.html`.
7. Emit a handoff JSON for every HTML report that feeds another agent, under `.dadaia/handoff/<context-name>/`.
8. Never treat the review/QA sequence as mechanically enforced — it holds only because dispatcher/implementer/reviewer each uphold their half.
9. Rely on git chokepoints (pre-commit warns and allows; pre-push requires an APPROVED security handoff) as the only mechanical backstop.
10. Resolve a decision by domain using the Decision Authority table (§4).
11. Evidence means file:line, spec citation, command output, or handoff field.
11. On a two-agent deadlock: have each agent write a `Conflict Position` section in its report.
12. Write a synthesis report naming the exact decision point.
13. If still unresolved, call `dd-grill-me` and ask the operator one concrete question.
14. Reflect the operator's answer in SPEC, PLAN, TASKS, ADR, or memory as appropriate for the current phase.
15. Stop and escalate to the operator on any trigger in §4's Escalation table.
16. Never perform any action in §4's Forbidden table.

## 3. Done when

- Every dispatch prompt carries the Input Contract block and a handoff on completion.
- Every conflict either resolved via evidence-based decision authority or escalated per §4.
- No forbidden action occurred.

## 4. References

### Agent inventory (9 core agents; roles/phases normative in constitution §7/§14)

| Agent | Phase | Primary mission | Routes next to (via PM) | Do not call when |
|---|---|---|---|---|
| `project-manager` | 1-2, MUTATING | Intake, bug intake, dispatch, mediation | any core agent (top-level only) | A single specialist suffices |
| `project-auditor` | 4 (audit) | Memory/implementation drift, dead-code, compliance | project-manager | A release is still mid-implementation |
| `product-engineer` | 5+8 (defn, closure) | SPEC, PLAN, TASKS, _RELEASE.json, memory | architect, PM | Task is code-only, already approved |
| `software-architect` | feeds 4/5 | Architecture decisions, ADRs, dependency contracts | software-engineer | No architectural trade-off exists |
| `software-engineer` | 6 (implementation) | Production code + tests for the bound context | qa-engineer | Task is spec, AI-entity, or pure review |
| `ai-engineer` | surface owner | Agents, skills, rules, commands, hooks | security-reviewer, code-reviewer | Task is product code or spec |
| `qa-engineer` | 7 gate -> commit | E2E strategy, acceptance validation, smoke evidence | none | Only unit/integration tests are needed |
| `security-reviewer` | 7 gate -> push | Security audit, threat modeling, secret/leak review | implementer | No security-relevant surface |
| `code-reviewer` | 7 gate -> PR | Diff/PR review, no authoring | none | There is no diff, PR, or staged set |

### SDD stage inventory (Arm A, `DADAIA.md` §1 — exactly four stages, no engine)

| Stage | Entry agent | Governing document(s) |
|---|---|---|
| Backlog definition | `project-manager` (intake+curate), `product-engineer` (reads to author) | `specs/backlog/**` |
| Release definition | `product-engineer` | SPEC, PLAN, TASKS |
| Implementation + reviews | surface implementer, then the review trio | TASKS, review handoffs |
| Audit | `project-auditor` | `specs/audits/**` |

### Pre-Implementation Agreement

- Settled at TASKS approval, not at implementation time.
- The owning implementer set, `qa-engineer`, `code-reviewer`, `security-reviewer` must agree the task definition.
- Missing agreement blocks TASKS approval.

### Decision authority

| Domain | Primary authority | May object with evidence | Tie-breaker |
|---|---|---|---|
| Feature scope, SPEC, TASKS | product-engineer | all agents | product-engineer |
| Architecture, ADRs, patterns | software-architect | software-engineer, security-reviewer | software-architect |
| Production implementation | software-engineer | software-architect, security-reviewer | software-architect |
| AI entities | ai-engineer | product-engineer, security-reviewer | product-engineer |
| E2E acceptance | qa-engineer | software-engineer, product-engineer | qa-engineer |
| Security posture | security-reviewer | software-engineer | security-reviewer |
| Drift scoring | project-auditor | product-engineer | product-engineer |
| Orchestration | project-manager | any agent | operator |

### Escalation triggers — stop and surface to the operator when

1. Required `SPEC.md`/`PLAN.md`/`TASKS.md` or a resolvable `_RELEASE.json` `phase` field are missing or not approved.
2. A CRITICAL security issue is reported.
3. A dispatched agent returns `[SCOPE ERROR]`.
4. Three or more unresolved conflicts are open.
5. The requested work requires an optional domain pack that is not installed.
6. The requested workflow is unknown and cannot be decomposed into default workflows without changing the spec.

### Forbidden actions

| Action | Why forbidden |
|---|---|
| Dispatchers editing outside `.dadaia/reports/` and `.dadaia/handoff/` | They are report/handoff-only roles |
| Recursive agent chains without operator approval | Breaks traceability |
| Marking tasks DONE without validation evidence | Skips acceptance |
| Push, PR, merge, deploy, closure, or `[x]` before QA/code/security approval | Bypasses the quality gate |
| Editing `specs/` outside product-engineer authority | Breaks SDD ownership |
| Editing production files without a `[-]` task reservation | Breaks task traceability |
| Shipping private/project-specific details in public assets | Security and portability risk |

### Generic playbooks

| Playbook | Entry | Use for |
|---|---|---|
| architecture-review | software-architect | ADRs, dependency boundaries, cross-cutting migrations, pattern selection |
| tdd-cycle | surface implementer | Non-trivial logic: failing test, smallest passing change, refactor, QA request |
| bug-fix-fastlane | surface implementer | Reproducible defect, narrow blast radius |
| release-definition | product-engineer (dispatched by PM) | Building a release from bugs+backlog — see `dd-release-definition` |
| security-patch | security-reviewer | Reviewer triages, PM dispatches engineer, then security verification |
| deploy-validation-only | qa-engineer | Deployment already happened, only smoke/evidence needed |
| ai-entity-refinement | ai-engineer | Public agents/skills/rules/commands/hooks; must pass `dadaia public doctor` |
| ai-engineer-recursive-bootstrap | ai-engineer | First restricted-scope self-edit of public AI entities only |
