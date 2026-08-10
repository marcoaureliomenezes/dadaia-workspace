---
name: project-orchestration
description: >
  Generic dispatch reference for project-manager and project-auditor agents.
  Defines the default public agent inventory, SDD stage inventory, dispatch
  protocol, mediation rules, escalation triggers, and forbidden actions.
applyTo: ".dadaia/handoff/**"
---

# project-orchestration

> **Not an enforcement mechanism.** There is no workflow engine: the ordered SDD flow
> (`DADAIA.md` §1) is agent-dispatched — carried out by dispatching the owning agent for
> each stage against the SDD documents. This skill is reference / dispatcher guidance,
> not a substitute for the documents themselves.

This is the public default orchestration skill. It must stay generic: no
operator-private project names, hostnames, IPs, customer names, private repo
slugs, or optional domain-pack assumptions.

## Agent Inventory

Default topology: 9 core agents (constitution §14 roster). Roles and phases are
normative in the §7/§14 matrices; this table is the dispatch view. There is no
concurrency lock between agents (NO-LOCKS DOCTRINE, v0.1.76) — dispatch purity below is
an orchestration convention, not a session primitive.

The "Routes next to" column is **handoff routing, not executable dispatch**: it names
the agent the dispatcher (PM, top-level) should send to next after consuming this
agent's handoff. Only the top-level session agent holds dispatch capability — a
dispatched sub-agent cannot spawn another agent in either harness, at any approval
level. `project-manager` is the only roster entry whose cell is real dispatch, and only
when it runs as the top-level session agent.

| Agent | Phase (§7) | Primary mission | Routes next to (via PM) | Do not call when |
|---|---|---|---|---|
| `project-manager` | 1–2; coordinates all MUTATING phases | Backlog/bug intake, cross-agent dispatch, mediation, sole dispatch authority | any core agent (real dispatch — top-level only) | A single specialist can complete the task directly |
| `project-auditor` | 4 (audit) | Memory/implementation drift, dead-code and compliance reports | project-manager | A release is still mid-implementation |
| `product-engineer` | 5 + 8 (definition, closure) | SPEC, PLAN, TASKS, CLOSURE, ACTIVE.md, memory | software-architect, project-manager | Task is code-only and already approved |
| `software-architect` | feeds 4/5 | Architecture decisions, ADRs, dependency contracts | software-engineer | No architectural trade-off exists |
| `software-engineer` | 6 (implementation) | Production code + tests for the bound context | qa-engineer | Task is spec authorship, AI-entity surface, or pure review |
| `ai-engineer` | surface owner (`dadaia_workspace/public/**`) | Agents, skills, rules, commands, hooks | security-reviewer, code-reviewer | Task is product code or spec authorship |
| `qa-engineer` | 7 gate → commit | E2E strategy, acceptance validation, smoke evidence | none | Only unit/integration tests are needed |
| `security-reviewer` | 7 gate → push | Security audit, threat modeling, secret/leak review | implementer | No security-relevant surface is involved |
| `code-reviewer` | 7 gate → PR | Diff/PR review, no authoring | none | There is no diff, PR, or staged set |

Plugins (not in core roster, constitution §14): `frontend-engineer`, `design-specialist`,
`devops-engineer`. They may be dispatched within a release when their surface is in scope,
but they do not appear in the default core topology above.

## SDD Stage Inventory

Arm A (`DADAIA.md` §1) has exactly four stages. Each is agent-dispatched — there is no
engine that runs them; the dispatcher hands the stage to its owning agent against the
SDD documents (`ACTIVE.md`, SPEC, PLAN, TASKS, CLOSURE):

| Stage | Entry agent | Governing document(s) |
|---|---|---|
| Backlog definition | `project-manager` (curates), `product-engineer` (reads to author) | `specs/backlog/**` |
| Release definition | `product-engineer` | SPEC, PLAN, TASKS |
| Implementation + reviews | surface implementer, then the review trio | TASKS, review handoffs |
| Audit | `project-auditor` | `specs/audits/**` |

There is no parallel Markdown workflow catalog and no workflow executor to invoke.

## Dispatch Protocol

Only the top-level dispatcher calls other agents. Leaf specialists **cannot** chain
further dispatch — the harness does not grant dispatch capability to sub-agents (this
is a runtime fact, not a policy that an operator approval can lift). A leaf that needs
another agent's work returns a handoff naming `next_handoff.agent`; the dispatcher
routes it.

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
- handoff_dir: .dadaia/handoff/<context-name>/
- allowed_write_paths: <explicit paths or reports-only>
```

Reports land in:

```text
.dadaia/reports/<context-name>/<agent-name>/<UTC>-<task-slug>.html
```

Every HTML report that feeds another agent must have a handoff JSON file under:

```text
.dadaia/handoff/<context-name>/<UTC>-<agent-name>-<task-slug>.handoff.json
```

## Orchestration judgment (no engine backstop)

The **ordered review/QA sequence** — the per-task → end-of-alpha → rc-ship transition
ladder — is not mechanically enforced anywhere: there is no engine state machine and no
gate that reads TASKS.md. It holds only because `project-manager` (dispatch discipline),
implementers (marker discipline, `dadaia-task-manager`), and reviewers (evidence-backed
`APPROVE`/`REQUEST_CHANGES`) each uphold their half. The only mechanical backstops are
the git chokepoints (`DADAIA.md` §3): pre-commit warns and always allows; pre-push
requires an APPROVED `security-reviewer` handoff whose `metrics.commit_sha` matches.

This skill carries the **orchestration judgment** a document alone cannot supply: who may
dispatch (dispatcher purity), the persona inventory and routing, decision authority,
mediation, escalation, and the forbidden actions. The gate cadence below is the
human-readable contract every agent upholds by convention.

## Review/QA gate cadence (upheld by convention, backstopped by the push chokepoint)

`project-manager` owns orchestration discipline; `product-engineer` owns SDD artifact
approval; implementers and reviewers own their evidence. Per ADR-3 (segment/ship
boundaries, not per task), and per the `DADAIA.md` §5 (Releases) and the
`dadaia-task-manager` skill (marker discipline):

| Boundary | Who validates | What unlocks |
|---|---|---|
| Per task | implementer discipline only — TDD, unit/integration tests, pre-push CI gate, `implementation-complete` handoff; marker stays `[-]` | nothing; no per-task reviewer gate |
| End of each `alpha-N` | `qa-engineer` only returns `APPROVE`/`REQUEST_CHANGES` (the **Review/QA Fan-Out**, qa-only) | a qa-gated commit on `feature/{version}` — no push/PR/merge/CLOSURE |
| At `rc-N` ship (operator elects) | full **Review/QA Fan-Out** — `qa-engineer` + `code-reviewer` + `security-reviewer` (+ `design-specialist` plugin for UI, if installed) must all `APPROVE` the **same implementation commit** | mark the task `[x]`, push implementation commits, open or update a PR, merge, deploy, or close the release, write `CLOSURE.md`/memory |

Any `REQUEST_CHANGES`, CRITICAL/HIGH security finding, failed E2E, missing evidence, or
stale report sends the work back to implementation; the rework loop continues until every
required validator approves the **same implementation commit** or the operator stops the
release. Before the applicable gate, the unlock actions above — mark the task `[x]`, push
implementation commits, open or update a PR, and merge, deploy, or close the release — are
forbidden; a local commit is workspace evidence, never release completion.

**Pre-Implementation Agreement (settled at TASKS approval, not at implementation time).**
The task definition must be agreed by the owning implementer set, `qa-engineer`,
`code-reviewer`, `security-reviewer`, and the `design-specialist` plugin for browser
UI/UX/design-token tasks (if installed). The approved task states implementation scope,
declared write set, unit and integration test plan, E2E/validation plan, code-review
criteria, security and privacy checks, and expected evidence paths. Missing agreement
blocks TASKS approval.

## Decision Authority

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

Evidence means a file:line citation, spec citation, command output, screenshot,
or handoff JSON field. Objections without evidence do not block progress.

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
| Dispatchers editing outside `.dadaia/reports/` and `.dadaia/handoff/` | They are report/handoff-only roles. |
| Recursive agent chains without operator approval | Breaks traceability. |
| Marking tasks DONE without validation evidence | Skips acceptance. |
| Push, PR, merge, deploy, release closure, or `[x]` before QA/code/security approval | Bypasses the quality gate. |
| Editing `specs/` outside product-engineer authority | Breaks SDD ownership. |
| Editing production files without a `[-]` task reservation | Breaks task traceability. |
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

### Playbook — release-definition

Entry: `product-engineer` (dispatched by `project-manager`).

Use when the operator wants a new release built from reported bugs + backlog.
`project-manager` dispatches `product-engineer` with the
`dadaia-release-definition` skill. Steps: (1) sanitize stale bugs/backlog
(`deferred`/`rejected` + reason, never delete); (2) pick the bug + backlog set;
(3) apply bug-always-solved — every picked bug is fixed in the release unless a
picked backlog item supersedes it (`superseded_by: <slug>` on the bug + SPEC
note); (4) a **MANDATORY** `dadaia-grill-me` session before the SPEC; (5) author
the SPEC. `project-manager` owns the gate: a release-from-backlog must not reach
SPEC without the grill report. See the `DADAIA.md` §5 (Releases).

### Playbook — security-patch

Entry: `security-reviewer`.

Reviewer triages severity and blast radius. `project-manager` then dispatches
`software-engineer` (or the relevant plugin implementer when the surface is
plugin-owned), followed by security verification.

### Playbook — deploy-validation-only

Entry: `qa-engineer`.

Use when deployment already happened and only smoke/evidence is needed. QA
captures command output, screenshots, logs, or endpoint probes and writes a
validation report.

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
