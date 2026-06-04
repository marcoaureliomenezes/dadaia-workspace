---
name: project-orchestration
description: >
  Generic dispatch reference for project-manager and project-auditor agents.
  Defines the default public agent inventory, workflow inventory, dispatch
  protocol, mediation rules, escalation triggers, and forbidden actions.
applyTo: ".dadaia/reports/**"
---

# project-orchestration

This is the public default orchestration skill. It must stay generic: no
operator-private project names, hostnames, IPs, customer names, private repo
slugs, or optional domain-pack assumptions.

## Agent Inventory

Default topology: 15 generic agents.

| Agent | Primary mission | Dispatches to | Do not call when |
|---|---|---|---|
| `project-manager` | Cross-agent dispatch, workflow orchestration, mediation | any default agent | A single specialist can complete the task directly |
| `project-auditor` | Memory/implementation drift, dead-code and compliance reports | project-manager | A release is still mid-implementation |
| `product-engineer` | SPEC, PLAN, TASKS, CLOSURE, ACTIVE.md, CLOSURE memory | software-architect, project-manager | Task is code-only and already approved |
| `software-architect` | Architecture decisions, ADRs, dependency contracts | software-engineer-python, software-engineer-node, backend-engineer | No architectural trade-off exists |
| `software-engineer-python` | Python CLI, library, tooling, tests | qa-engineer | Task is Node, browser UI, backend service, AI entity, docs-only, or CI-only |
| `software-engineer-node` | Server-side Node/TypeScript tooling, tests | qa-engineer | Task is Python, browser UI, backend service, AI entity, docs-only, or CI-only |
| `backend-engineer` | Backend services, APIs, persistence | software-architect, qa-engineer | Task is local tooling, browser-only UI, specs, or CI |
| `frontend-engineer` | Browser UI implementation | design-specialist, qa-engineer | Task is backend, CLI, specs, or infra only |
| `ai-engineer` | Agents, skills, rules, workflows, commands, hooks | security-reviewer, code-reviewer | Task is product code or spec authorship |
| `qa-engineer` | E2E strategy, acceptance validation, smoke evidence | none | Only unit/integration tests are needed |
| `devops-engineer` | CI/CD, deployment, projection install | software-engineer-python | No CI/deploy/projection change is in scope |
| `security-reviewer` | Security audit, threat modeling, secret/leak review | devops-engineer, implementer | No security-relevant surface is involved |
| `code-reviewer` | Diff/PR review, no authoring | none | There is no diff, PR, or staged set |
| `researcher` | External-source investigation against trusted sources | none | Local code/spec inspection is enough |
| `design-specialist` | UX/UI review, design spec, visual handoff | frontend-engineer | No user-facing UI is involved |

## Workflow Inventory

Public default workflows:

| Workflow | File | Trigger | Entry |
|---|---|---|---|
| `spec-refinement` | `public/workflows/spec-refinement.workflow.md` | Ambiguous feature scope or backlog item | project-manager |
| `hotfix-release` | `public/workflows/hotfix-release.workflow.md` | Production defect requiring a patch | project-manager |
| `code-review-fan-out` | `public/workflows/code-review-fan-out.workflow.md` | PR or staged diff review | code-reviewer |
| `audit-cycle` | `public/workflows/audit-cycle.workflow.md` | Release CLOSURE or scheduled compliance audit | project-auditor |
| `cross-cutting-feature` | `public/workflows/cross-cutting-feature.workflow.md` | Two or more implementation surfaces | software-architect |
| `onboarding-new-repo` | `public/workflows/onboarding-new-repo.workflow.md` | New repo baseline assessment | project-manager |
| `design-first-implementation` | `public/workflows/design-first-implementation.workflow.md` | UI work requiring design before implementation | design-specialist |

Optional packs may add workflows, agents, and rules, but they must not be part
of the public default install unless explicitly selected by the operator.

## Dispatch Protocol

Only dispatchers call other agents. Leaf specialists do not chain further
dispatch unless the operator explicitly approves it.

Use this shape for sub-agent prompts:

```json
{
  "subagent_type": "<agent-name>",
  "description": "<one-sentence task summary>",
  "prompt": "<full task prompt with input contract>"
}
```

Every dispatch prompt starts with:

```text
## Input Contract
- context: <context-name>
- specs_dir: <absolute-path>
- release_id: <release-id>
- task_id: <task-id or n/a>
- report_dir: .dadaia/reports/<context-name>/<agent-name>/
- allowed_write_paths: <explicit paths or reports-only>
```

Reports land in:

```text
.dadaia/reports/<context-name>/<agent-name>/<UTC>-<task-slug>.html
```

Every HTML report must have a sibling `<stem>.handoff.json` sidecar.

## Strict Implementation-Review-QA Contract

This contract applies to every implementation task in an approved SDD release.
`project-manager` owns orchestration discipline; `product-engineer` owns SDD
artifact approval; implementers and reviewers own their evidence.

### 0. Pre-Implementation Agreement

Before `TASKS.md` is approved, the task definition must be agreed by:

- the owning implementer agent or implementer set
- `qa-engineer`
- `code-reviewer`
- `security-reviewer`
- `design-specialist` when the task touches browser UI, visual UX, flows, or design tokens

The approved task must state implementation scope, declared write set, unit and
integration test plan, E2E/validation plan, code-review criteria, security and
privacy checks, and expected evidence paths. Missing agreement blocks TASKS
approval; it is not deferred to implementation time.

### 1. Implementation Handoff

When an implementer finishes code and local unit/integration checks, the work is
only `implementation-complete`. It is not DONE. The implementer emits a handoff
report with changed files, commits, test commands, known residual risk, and any
security/privacy-sensitive areas. The task marker stays `[-]`.

### 2. Review/QA Fan-Out

`project-manager` dispatches all required validators after the implementation
handoff:

- `qa-engineer` validates the E2E/acceptance plan and operator-visible behavior
- `code-reviewer` reviews architecture, maintainability, tests, and regressions
- `security-reviewer` reviews security, privacy, secrets, dependency, and deploy leakage risk
- `design-specialist` reviews UI/design compliance when applicable

Each validator returns `APPROVE` or `REQUEST_CHANGES` in its handoff sidecar.
Any `REQUEST_CHANGES`, CRITICAL/HIGH security finding, failed E2E, missing
evidence, or stale report sends the task back to implementation. The rework loop
continues until every required validator approves the same implementation commit
or the operator explicitly stops the release.

### 3. Done Gate

Only after all required validators approve may the orchestrator or task owner:

- mark the task `[x]`
- push implementation commits
- open or update a PR for merge
- merge, deploy, or close the release
- write release `CLOSURE.md` or memory updates

Before this gate, those actions are forbidden. A local commit is acceptable as
workspace evidence, but it is not release completion and must not be represented
as approved work.

## Decision Authority

| Domain | Primary authority | May object with evidence | Tie-breaker |
|---|---|---|---|
| Feature scope, SPEC, TASKS | product-engineer | all agents | product-engineer |
| Architecture, ADRs, patterns | software-architect | implementers, security-reviewer | software-architect |
| Python implementation | software-engineer-python | software-architect, security-reviewer | software-architect |
| Node implementation | software-engineer-node | software-architect, security-reviewer | software-architect |
| Backend services | backend-engineer | software-architect, security-reviewer | software-architect |
| Browser UI | frontend-engineer | design-specialist, qa-engineer | design-specialist for visual disputes; software-architect for technical disputes |
| AI entities | ai-engineer | product-engineer, security-reviewer | product-engineer |
| CI/CD and projection install | devops-engineer | security-reviewer, software-engineer-python | devops-engineer |
| E2E acceptance | qa-engineer | implementers, product-engineer | qa-engineer |
| Security posture | security-reviewer | implementers, devops-engineer | security-reviewer |
| Drift scoring | project-auditor | product-engineer | product-engineer |
| Orchestration | project-manager | any agent | operator |

Evidence means a file:line citation, spec citation, command output, screenshot,
or report sidecar field. Objections without evidence do not block progress.

## Anti-Deadlock

Use this when two agents remain blocked after one exchange:

1. Each agent writes a `Conflict Position` section in its report.
2. `project-manager` writes a synthesis report with the exact decision point.
3. If the decision still cannot be resolved, invoke `dadaia-grill-me` and ask
   the operator one concrete question.

The operator's answer must be reflected in SPEC, PLAN, TASKS, ADR, or memory as
appropriate for the current phase.

## Escalation Triggers

Stop and surface to the operator when:

1. Required `SPEC.md`, `PLAN.md`, `TASKS.md`, or `ACTIVE.md` files are missing
   or not approved.
2. A CRITICAL security issue is reported.
3. A dispatched agent returns `[SCOPE ERROR]`.
4. Three or more unresolved conflicts are open.
5. The requested work requires an optional domain pack that is not installed.
6. The requested workflow is unknown and cannot be decomposed into default
   workflows without changing the spec.

## Forbidden Actions

| Action | Why forbidden |
|---|---|
| Dispatchers editing outside `.dadaia/reports/` | They are reports-only roles. |
| Recursive agent chains without operator approval | Breaks traceability. |
| Marking tasks DONE without validation evidence | Skips acceptance. |
| Push, PR, merge, deploy, release closure, or `[x]` before QA/code/security approval | Bypasses the quality gate. |
| Editing `specs/` outside product-engineer authority | Breaks SDD ownership. |
| Editing production files without a `[-]` task reservation | Breaks task locking. |
| Shipping private/project-specific details in public assets | Security and portability risk. |

## Generic Playbooks

### Playbook — architecture-review

Entry: `software-architect`.

Use for ADRs, dependency boundaries, cross-cutting migrations, or pattern
selection. Architect reports the recommendation; implementation is dispatched
only after the relevant SDD gate exists.

### Playbook — tdd-cycle

Entry: the surface implementer.

Use for non-trivial logic. Engineer writes or updates a failing test, implements
the smallest passing change, refactors if needed, then requests QA when
operator-visible behavior changed.

### Playbook — bug-fix-fastlane

Entry: the surface implementer.

Use for a reproducible defect with narrow blast radius. Include reproduction
steps, expected/actual behavior, suspected files, and validation command.

### Playbook — security-patch

Entry: `security-reviewer`.

Reviewer triages severity and blast radius. `project-manager` then dispatches
the appropriate implementer or `devops-engineer`, followed by security
verification.

### Playbook — deploy-validation-only

Entry: `qa-engineer`.

Use when deployment already happened and only smoke/evidence is needed. QA
captures command output, screenshots, logs, or endpoint probes and writes a
validation report.

### Playbook — design-validation

Entry: `design-specialist`.

Designer emits a handoff report with states, tokens, accessibility findings,
and screenshots or sketches. `frontend-engineer` implements from that report,
then QA validates the UI.

### Playbook — ai-entity-refinement

Entry: `ai-engineer`.

Use for public agents, skills, rules, workflows, commands, hooks, and runtime
projection behavior. Scope must list exact files or globs. Public asset edits
must pass `dadaia public doctor` and the public privacy gate.

### Playbook — ai-engineer-recursive-bootstrap

Entry: `ai-engineer`.

Use only for the first restricted-scope self-edit of public AI entities. The
task must name exact files or globs, keep the edit generic/public-safe, and end
with `dadaia public doctor`, memory lint when memory is touched, and a privacy
gate result.
