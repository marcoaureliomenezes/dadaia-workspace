# TASKS: v0.1.15 - Codex Lifecycle Foundation + Slop Control

**Status:** Aprovado
**Release ID:** v0.1.15
**Owner:** product-engineer
**Created:** 2026-06-18

Markers: `[ ]` OPEN, `[-]` IN PROGRESS, `[x]` DONE.

---

## Pre-work

### [ ] T-015-00 - Release approval and implementation branch
- **Owner:** product-engineer
- **Maps:** SPEC scope boundary; PLAN PRE
- **Write set:** `specs/releases/ACTIVE.md`, release handoff/report only
- **Acceptance:** SPEC/PLAN/TASKS are `Aprovado`; ACTIVE changes to
  `release: v0.1.15` / `phase: IMPLEMENTATION`; implementation branch is
  `feature/v0.1.15` or an explicit product-engineer exception is recorded.
- **Parallelism:** first.

## W1 - Models and contracts

### [x] T-015-01 - lifecycle core models
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/core/models/lifecycle.py`,
  `tests/unit/core/test_lifecycle*.py`
- **Acceptance:** pure dataclasses/enums for phases, run state, blocked state,
  gate requirements, evidence, agent requests/results; tests cover creation and
  serialization; no I/O imports in core.

### [x] T-015-02 - hygiene models and SlopPolicy
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/core/models/hygiene.py`,
  `tests/unit/core/test_hygiene*.py`
- **Acceptance:** default TTLs reports=48h, handoffs=24h, tmp=24h; counters
  include zone totals, expired totals, orphan/malformed handoffs, unknown
  `.dadaia/` dirs, cleanup candidates, protected residuals, and scan metrics.

### [x] T-015-03 - runtime file and agent runtime protocols
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/core/protocols/runtime_files.py`,
  `dadaia_workspace/core/protocols/agent_runtime.py`,
  `tests/unit/core/protocols/`
- **Acceptance:** ports cover report, handoff, tmp, run artifact, hygiene
  snapshot, and agent runtime; no concrete filesystem/subprocess/SDK code in
  core.

## W2 - Runtime files and hygiene

### [x] T-015-04 - filesystem runtime-file adapters
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/infrastructure/runtime_files.py`,
  `tests/unit/infrastructure/test_runtime_files*.py`,
  `tests/integration/test_runtime_files*.py`
- **Acceptance:** concrete writers create canonical report, handoff, tmp, run
  artifact, and hygiene snapshot paths; reject unknown `.dadaia/` top-level
  folders and repo-tree destinations; validate handoff/report artifacts where
  applicable.

### [x] T-015-05 - shared hygiene service and TTL reconciliation
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/features/lifecycle/hygiene.py`,
  `dadaia_workspace/features/workspace_clean/service.py`,
  `dadaia_workspace/features/reports_retention/service.py`,
  `tests/unit/features/lifecycle/test_hygiene*.py`
- **Acceptance:** one `SlopPolicy` drives reports, handoffs, and tmp TTLs;
  existing cleanup defaults no longer conflict; status returns exact counters
  without deleting; implementation avoids file-content reads for metadata-only
  decisions.

### [x] T-015-06 - boundary-safe cleanup and preservation rules
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/features/lifecycle/hygiene.py`,
  `tests/integration/test_lifecycle_hygiene_cleanup.py`
- **Acceptance:** dry-run is default; apply requires explicit flag; deletes only
  expired candidates under `.dadaia/reports`, `.dadaia/handoff`, `.dadaia/tmp`;
  preserves important retention records, valid referenced artifacts,
  current-release/review/audit evidence, active runs, durable states, locks,
  sessions, operator-protected paths, and anything outside safe zones; prunes
  safe empty dirs.

### [x] T-015-07 - hygiene snapshot and high-volume scan test
- **Owner:** qa-engineer
- **Write set:** `tests/integration/test_lifecycle_hygiene_snapshot.py`,
  `tests/performance/test_lifecycle_hygiene_scan.py`
- **Acceptance:** baseline/final snapshot JSON schema includes schema version,
  timestamp, context, release, run id, TTL policy, counters, candidates,
  protected residuals, and elapsed scan metrics; synthetic tree at or above the
  measured baseline class verifies documented time, memory, and content-read
  constraints.

## W3 - State machine and gates

### [x] T-015-08 - lifecycle state machine
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/features/lifecycle/state_machine.py`,
  `tests/unit/features/lifecycle/test_state_machine*.py`
- **Acceptance:** legal, illegal, blocked, and resume transitions are
  data-driven and tested; transition inputs are structured evidence; no LLM or
  filesystem dependency.

### [x] T-015-09 - semantic handoff gate validators
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/features/lifecycle/gates.py`,
  `tests/unit/features/lifecycle/test_gates*.py`
- **Acceptance:** validators consume handoff JSON; check agent, context,
  release_id, verdict, severity threshold, artifact hash, commit SHA/task group;
  reject malformed, stale, wrong-agent, wrong-release, wrong-context,
  wrong-commit, and substring-only evidence.

### [x] T-015-10 - preflight service and blocked/resume state
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/features/lifecycle/service.py`,
  `tests/unit/features/lifecycle/test_preflight*.py`
- **Acceptance:** preflight checks context binding, active release, phase, dirty
  worktree, upstream/push readiness, specs doctor result, lease/mode, hygiene
  status, and required handoffs; failures return typed blocked state with next
  operator command when available.

### [x] T-015-11 - lifecycle run-state store
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/features/lifecycle/run_store.py`,
  `dadaia_workspace/infrastructure/json_lifecycle_run_store.py`,
  `tests/unit/features/lifecycle/test_run_store*.py`
- **Acceptance:** run records persist under canonical `.dadaia/states/lifecycle/`
  or `.dadaia/runs/lifecycle/`; resume is idempotent; no repo-tree writes;
  corrupt run state yields actionable error.

## W4 - CLI and report workflow

### [x] T-015-12 - lifecycle command group
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/cli/commands/lifecycle.py`,
  `dadaia_workspace/cli/main.py`,
  `dadaia_workspace/container.py`,
  `tests/integration/cli/test_lifecycle_cli.py`
- **Acceptance:** `dadaia lifecycle --help` exposes required commands; exit
  codes distinguish OK, BLOCKED, usage error, and internal error; commands use
  services instead of embedding workflow logic.

### [x] T-015-13 - status, preflight, and hygiene CLI behavior
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/cli/commands/lifecycle.py`,
  `tests/integration/cli/test_lifecycle_hygiene_cli.py`
- **Acceptance:** `status --json`, `preflight --json`, `hygiene status --json`,
  `hygiene clean --dry-run`, and `hygiene clean --apply` work in temp
  workspaces; status/preflight never call Codex; cleanup apply requires explicit
  flag.

### [x] T-015-14 - report workflow proof
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/features/lifecycle/report_workflow.py`,
  `tests/integration/test_lifecycle_report_workflow.py`
- **Acceptance:** one command writes an HTML report, emits matching handoff,
  validates schema/hash, writes hygiene snapshots, and runs hygiene status;
  cleanup apply occurs only with explicit option/policy and fresh artifacts
  remain.

### [x] T-015-15 - guarded skeleton commands
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/cli/commands/lifecycle.py`,
  `tests/integration/cli/test_lifecycle_command_skeletons.py`
- **Acceptance:** commands exist for backlog define, release define, implement,
  review qa/security/code, close, and resume; each resolves context and returns
  deterministic next state or typed blocked state; no silent no-op.

## W5 - Codex worker integration

### [x] T-015-16 - fake AgentRuntimePort tests
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/features/lifecycle/agent_runner.py`,
  `tests/unit/features/lifecycle/test_agent_runtime_fake.py`
- **Acceptance:** fake adapter proves Python advances state only after
  structured output and diff/write-scope validation; "agent says approved" alone
  does not pass a gate.

### [x] T-015-17 - Codex exec adapter decision and implementation
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/infrastructure/codex_runtime.py`,
  `tests/unit/infrastructure/test_codex_runtime*.py`,
  `specs/releases/v0.1.15/CODEX_RUNTIME_DECISION.md`
- **Acceptance:** `CodexExecAdapter` implements `AgentRuntimePort`; no Codex SDK
  or package dependency is added; exec surface is documented; rationale explains
  why lifecycle authority stays outside SDK/Agents; no project-local provider,
  auth, telemetry, or profile config is read; no whole-`os.environ` pass-through;
  environment is explicit allowlist only; credentials are redacted from run
  records, handoffs, reports, logs, and errors; model/profile selection comes
  from registry-derived Codex tier views or explicit operator input; sandbox or
  profile widening requires explicit operator-controlled input and is visible in
  the run record; live Codex tests are opt-in only.

### [x] T-015-18 - scoped prompt builder and write allowlist contract
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/features/lifecycle/prompt_builder.py`,
  `tests/unit/features/lifecycle/test_prompt_builder.py`,
  `tests/contract/test_lifecycle_prompt_scope.py`
- **Acceptance:** prompt includes role, context, release, task, allowed paths,
  forbidden paths, expected schema, and evidence; unrelated workspace-wide
  context is excluded; diff inspection rejects out-of-scope edits; ai-engineer
  may provide ADDITIVE review/report evidence only.

## W6 - Bug proof and end-to-end validation

### [x] T-015-19 - blocked push/resume regression
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/features/lifecycle/service.py`,
  `tests/integration/test_lifecycle_push_preflight.py`
- **Acceptance:** no-approval/blocked-push scenario returns BLOCKED with exact
  operator command and resume token; emits valid handoff; no Codex command
  policy change is made in this release.

### [x] T-015-20 - review gate integration
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/features/lifecycle/gates.py`,
  `tests/integration/test_lifecycle_review_gates.py`
- **Acceptance:** valid QA, security, and code-review handoffs pass only when
  agent/context/release/verdict/commit identity match; stale and wrong-context
  approvals fail.

### [x] T-015-21 - temp workspace lifecycle smoke
- **Owner:** qa-engineer
- **Write set:** `tests/e2e/test_lifecycle_engine_smoke.py`
- **Acceptance:** disposable workspace runs status -> preflight blocked ->
  report workflow -> hygiene status/dry-run/apply -> fake Codex worker ->
  semantic review gate; no writes outside canonical paths; specs doctor remains
  clean.

## W7 - Final gates and closure

### [ ] T-015-22 - final validation
- **Owner:** software-engineer
- **Write set:** none expected
- **Acceptance:** ruff format/check, mypy strict, pytest, specs doctor, public
  doctor, lifecycle smoke, and hygiene performance evidence pass; outputs are
  captured for CLOSURE.

### [ ] T-015-23 - CLOSURE, memory, and backlog/bug disposition
- **Owner:** product-engineer
- **Write set:** `specs/releases/v0.1.15/CLOSURE.md`,
  `specs/memory/**`, picked backlog/bug metadata,
  `specs/releases/ACTIVE.md`
- **Acceptance:** CLOSURE evidence triples; memory updated to current lifecycle
  engine/slop-control truth; picked bug closed only with regression evidence;
  consumed backlog disposition recorded; ACTIVE reset/archive performed after
  release completion.
