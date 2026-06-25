# SPEC: v0.1.15 - Codex Lifecycle Foundation + Slop Control

**Status:** Aprovado
**Release ID:** v0.1.15
**Owner:** product-engineer
**Created:** 2026-06-18
**Branch:** `feature/v0.1.15` required for implementation. The current definition
branch `fix/codex-hook-direct-exec-wrapper` is temporary and must not be used for
implementation unless the product-engineer records an explicit exception.

---

## Objective

Build the first deterministic Codex-side lifecycle foundation for dadaia:
CLI commands call Python workflow services; Python owns state transitions,
scope checks, gates, retention, run records, and artifact validation; Codex is
a bounded worker behind an adapter, not the orchestrator of record.

This release is a foundation release. It must prove the lifecycle spine,
semantic gates, canonical runtime-file APIs, hygiene policy, blocked/resume
behavior, and a Codex adapter contract. It must not attempt to automate every
backlog/release/implementation/review workflow end to end in one step.

## Scope boundary

In scope:

- shadow-mode lifecycle state machine and run store;
- `dadaia lifecycle status`, `preflight`, `hygiene`, `report`, and `resume`;
- guarded skeletons for backlog, release, implement, review, and close commands
  that return a deterministic next legal state or typed blocked state;
- canonical report, handoff, tmp, and run-artifact file APIs;
- safe hygiene measurement and opt-in cleanup apply;
- semantic gate validators for QA, security, code review, release definition,
  and closure evidence;
- Codex runtime port, fake adapter tests, and a no-new-dependency
  `CodexExecAdapter` contract.

Out of this release:

- full autonomous release implementation;
- Claude Code/OpenCode parity;
- broad rewrite of AGENTS.md, skills, or rules;
- changing Codex command policy to permit push. This release handles blocked
  push as a resumable lifecycle state.

## Grill / refinement

Mandatory release-definition refinement completed:

- Report: `.dadaia/reports/dadaia-workspace/product-engineer/2026-06-18T033250Z-refine-specs.html`
- Outcome: no open operator questions. The operator chose one Codex-focused
  release now, with deterministic CLI/Python workflows, strict write-scope
  control, anti-slop cleanup, and reduced reliance on advisory agent text.

## Picked inputs

| Input | Status | Disposition |
|---|---|---|
| Architecture report `.dadaia/reports/dadaia-workspace/software-architect/2026-06-18T030021Z-codex-lifecycle-engine-architecture.html` | Picked | Converts recommendation into bounded foundation scope. |
| `specs/backlog/sdd-governance-v2-agents-lifecycle.md` | Picked as design input | Implements deterministic lifecycle foundation for Codex. |
| `specs/backlog/workspace-sanitization.md` | Picked | Establishes workflow-owned hygiene policy and cleanup gates. |
| `specs/bugs/codex-push-policy-blocks-required-release-preflight.md` | Picked | Solves by typed blocked/resume state, not by Codex policy rewrite. |

Historical consumed backlog is context only. No closed release is reopened.

## Current slop baseline

Measured during definition on 2026-06-18:

| Zone | Files | Past desired TTL |
|---|---:|---:|
| `.dadaia/reports/**` | 122 | 121 older than 2 days |
| `.dadaia/handoff/**` | 295 | 294 older than 1 day |
| `.dadaia/tmp/**` | 437,724 | 437,719 older than 1 day |

Implementation must produce canonical hygiene snapshot JSON from the lifecycle
run store before and after cleanup. The definition-time counts above are
planning evidence, not the only acceptance evidence.

## Functional requirements

### W1 - Lifecycle command surface

- FR-W1-01: Add `dadaia lifecycle` with `status`, `preflight`, `hygiene status`,
  `hygiene clean`, `report`, `resume`, and guarded skeletons for
  `backlog define`, `release define`, `implement`, `review qa`,
  `review security`, `review code`, and `close`.
- FR-W1-02: Mutating lifecycle phases require an explicit resolved Spec Context
  Project. Unbound sessions may run read-only status, research, bug definition,
  and hygiene dry-run only.
- FR-W1-03: `status --json` returns context, release, phase, dirty state,
  hygiene counters, latest relevant handoffs, active/blocked run, and next
  legal transition.
- FR-W1-04: `preflight --json` checks context, release files, phase, dirty
  worktree, upstream/push readiness, specs doctor result, lease/mode, and
  hygiene status. Failures return typed blocked states.
- FR-W1-05: When Codex cannot perform an external action such as push, preflight
  emits a valid blocked handoff with exact operator command and resume token.

### W2 - Lifecycle state machine

- FR-W2-01: Add a pure Python state-machine service, explicitly including a
  concrete implementation module under `features/lifecycle/state_machine.py`.
- FR-W2-02: Legal transitions cover backlog definition, release definition,
  implementation, QA checkpoint, security checkpoint, code-review checkpoint,
  closure, blocked, and resume.
- FR-W2-03: Transitions consume structured evidence: active release files,
  handoff JSON, git status, commit SHA, dirty diff summary, test results,
  specs doctor result, and hygiene counters.
- FR-W2-04: String-substring gates are invalid. Gates validate structured
  artifacts semantically.
- FR-W2-05: Existing Markdown workflow files may remain documentation and panel
  references. Python is the lifecycle enforcement source.

### W3 - Runtime file APIs

- FR-W3-01: Add concrete filesystem adapters/services for canonical reports,
  handoffs, tmp files, hygiene snapshots, and run artifacts.
- FR-W3-02: Reports go under `.dadaia/reports/<context>/<agent>/`, use the
  report validation path, and link to a matching handoff when human-facing.
- FR-W3-03: Handoffs go under `.dadaia/handoff/<context>/` and must validate
  schema, artifact hash, context, release id, agent, verdict, and metrics shape.
- FR-W3-04: Tmp files go under `.dadaia/tmp/<workflow-or-agent>/<YYYYMMDD>/`.
- FR-W3-05: Run records and hygiene snapshots go under canonical lifecycle run
  storage, not inside any repo tree.
- FR-W3-06: File APIs reject unknown `.dadaia/` top-level folders unless the
  folder is in the durable canonical map.

### W4 - Slop measurement and cleanup gates

- FR-W4-01: Define one `SlopPolicy`: reports TTL 48h, handoffs TTL 24h, tmp TTL
  24h, with protected/durable path classes.
- FR-W4-02: Hygiene status computes zone totals, expired totals, unknown
  `.dadaia/` top-level folders, orphan/malformed handoffs, empty stale
  directories, and cleanup candidates.
- FR-W4-03: Hygiene snapshot JSON includes schema version, timestamp, context,
  release, run id, TTL policy, counters, candidate counts, protected residuals,
  and elapsed scan metrics.
- FR-W4-04: Standalone cleanup defaults to dry-run. Cleanup apply requires an
  explicit flag.
- FR-W4-05: Lifecycle report workflow runs hygiene status automatically and may
  apply cleanup only when explicitly requested by command option or policy
  input; it must never silently delete valuable evidence.
- FR-W4-06: Cleanup preserves important report-retention records, current-release
  and active-run evidence, valid handoff-referenced artifacts, audits/reviews
  referenced by live release state, durable `.dadaia/states`, locks, sessions,
  operator-protected paths, and anything outside the declared safe zones.
- FR-W4-07: Existing `dadaia clean` and `dadaia reports cleanup` defaults are
  reconciled so conflicting TTL defaults do not persist.

### W5 - Semantic gates and review evidence

- FR-W5-01: QA checkpoint accepts only valid `qa-engineer` handoff evidence for
  the same context/release/task group or commit range, verdict `APPROVED`, and
  test evidence.
- FR-W5-02: Security checkpoint accepts only valid `security-reviewer` handoff
  whose `metrics.commit_sha` matches the pushed SHA.
- FR-W5-03: Code-review checkpoint accepts only valid `code-reviewer` handoff
  for the same context/release/commit range with no unresolved HIGH/CRITICAL
  findings.
- FR-W5-04: Release definition completion requires SPEC/PLAN/TASKS with
  `**Status:** Aprovado`, mandatory grill report path, picked backlog/bugs list,
  and explicit disposition plan for consumed backlog/bugs.
- FR-W5-05: Closure completion requires CLOSURE evidence triples, memory update
  compliance, bug/backlog disposition, ACTIVE reset/archive, specs doctor clean,
  and hygiene postflight evidence.

### W6 - Codex runtime adapter

- FR-W6-01: Define `AgentRuntimePort` and structured `AgentRunRequest` /
  `AgentRunResult`. Lifecycle code depends on the port, not on a concrete SDK.
- FR-W6-02: Implement fake adapter tests and `CodexExecAdapter` behind the same
  port as the v0.1.15 default. No Codex SDK/package dependency may be added in
  this release. A future `CodexSdkAdapter` requires a separate picked task that
  names the exact package/version and approval criteria before implementation.
- FR-W6-03: The adapter task must document the exec surface, why lifecycle
  authority stays outside SDK/Agents, and how sandbox, cwd, env, credentials,
  and model/profile selection are controlled.
- FR-W6-04: Headless Codex hooks are not assumed. CLI preflight/postflight and
  file APIs enforce lifecycle invariants.
- FR-W6-05: Prompt builder inputs are scoped by role, context, release, task,
  allowed paths, forbidden paths, expected schema, and required evidence. It
  must not send whole-workspace context by default.
- FR-W6-06: Adapter execution must not read project-local provider/auth,
  telemetry, or profile configuration; must not pass through whole
  `os.environ`; must allow only an explicit environment allowlist; and must
  redact credentials from run records, handoffs, reports, logs, and errors.
- FR-W6-07: Model/profile selection must come from registry-derived Codex tier
  views or explicit operator input. Sandbox/profile widening requires explicit
  operator-controlled input and must be visible in the run record.

### W7 - Bug resolution: blocked push preflight

- FR-W7-01: The picked bug is resolved when preflight returns BLOCKED with a
  resumable handoff and exact operator command in no-approval push scenarios.
- FR-W7-02: This release does not change Codex command policy. Any future policy
  change must use current Codex `.rules` surfaces and a separate task.

## Non-functional requirements

- NF-1: CLI stays thin; features own behavior; core owns pure models/protocols;
  infrastructure owns filesystem, subprocess, SDK, and git I/O.
- NF-2: No new dependency for Codex runtime work in this release. The default is
  exec-backed. SDK integration is future work unless a later release explicitly
  picks and approves a package/version.
- NF-3: No credentials, private host paths, private repo names, or operator-local
  data in public assets, reports, or handoffs.
- NF-4: Hygiene scan must stream or batch and must not read file contents when
  metadata is enough.
- NF-5: Add a slow/integration performance test with a synthetic tree at or
  above the measured baseline class. It must document time, memory, and
  content-read constraints.
- NF-6: Do not add new lifecycle-enforcement prose to AGENTS.md, skills, or
  rules unless it replaces longer advisory text or points operators to the new
  deterministic command.

## Architecture deltas

- `cli/commands/lifecycle.py` - new command group.
- `features/lifecycle/state_machine.py` - legal transitions and blocked/resume.
- `features/lifecycle/service.py` - lifecycle orchestration over deterministic
  ports.
- `features/lifecycle/hygiene.py` - single hygiene policy/status/cleanup service.
- `features/lifecycle/gates.py` - semantic review/release/closure gates.
- `features/lifecycle/report_workflow.py` - report workflow proof.
- `features/lifecycle/prompt_builder.py` - scoped worker prompts.
- `features/lifecycle/run_store.py` - lifecycle run records.
- `core/models/lifecycle.py`, `core/models/hygiene.py` - pure models.
- `core/protocols/agent_runtime.py`, `core/protocols/runtime_files.py` - ports.
- `infrastructure/codex_runtime.py` and filesystem runtime-file adapters.
- Existing cleanup/report retention services updated or wrapped to one policy.

## Acceptance criteria

1. `dadaia lifecycle --help` exposes the foundation commands and guarded
   skeletons.
2. `status --json` and `preflight --json` work without real Codex.
3. Preflight produces typed blocked/resume handoff for blocked push.
4. State-machine tests cover legal, illegal, blocked, and resume transitions.
5. Runtime file API tests accept canonical paths and reject non-canonical paths.
6. Hygiene dry-run/apply tests preserve protected evidence and delete only safe
   expired candidates.
7. Hygiene snapshot JSON exists for baseline and final comparison.
8. Large synthetic-tree hygiene test verifies performance constraints.
9. Report workflow writes report+handoff and runs hygiene status; cleanup apply
   happens only under explicit option/policy.
10. Semantic gates reject stale, wrong-context, wrong-agent, wrong-release,
    wrong-commit, malformed, and substring-only evidence.
11. Fake Codex adapter proves Python advances state only after validation.
12. Codex adapter decision is documented and credentials/sandbox/cwd/env behavior
    is test-covered or explicitly opt-in for live execution.
13. `dadaia specs doctor --specs-dir repos/dadaia-workspace/specs` has no new
    errors attributable to this release.
14. Closure records backlog/bug disposition and updates memory only in CLOSURE.
