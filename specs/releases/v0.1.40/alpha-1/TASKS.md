# TASKS: v0.1.40 alpha-1 - SDD Governance v2 completion

**Status:** Aprovado
**Release ID:** v0.1.40
**Segment:** alpha-1
**Owner:** product-engineer
**Created:** 2026-06-29

Marks: `[ ]` OPEN, `[-]` IN PROGRESS, `[x]` DONE.

---

## Tasks

### T1 - Repair release-definition create artifacts

- **Status:** [x] DONE
- **Owner:** product-engineer
- **Write set:** `dadaia_workspace/features/lifecycle/workflows/release_definition.py`, `dadaia_workspace/infrastructure/fake_runtime.py`, `dadaia_workspace/public/lifecycle_fragments/release_definition/*.md`, `tests/integration/cli/test_release_definition_workflow.py`, picked release-definition bug files, `specs/releases/v0.1.40/alpha-1/**`
- **Acceptance:** `dadaia lifecycle release define --harness fake` writes canonical `SPEC.md`, `PLAN.md`, and `TASKS.md`; handoff-only create success still blocks; PI/Codex missing-artifact failures remain explicit workflow bugs.
- **Validation:** `pytest -p no:cacheprovider tests/integration/cli/test_release_definition_workflow.py::test_cli_fake_runtime_writes_canonical_create_artifacts tests/integration/cli/test_release_definition_workflow.py::test_cli_fake_runtime_writes_canonical_create_artifacts_in_repo_context tests/integration/cli/test_release_definition_workflow.py::test_handoff_only_spec_create_blocks_at_spec_create tests/integration/cli/test_release_definition_workflow.py::test_full_sequence_reaches_commit_gate_and_advances -q` -> `4 passed`; `ruff check --no-cache` on touched files -> `All checks passed!`; `mypy --strict` on touched production modules -> `Success`.

### T2 - Add JSONL bug-event telemetry and CLI

- **Status:** [x] DONE
- **Owner:** product-engineer
- **Write set:** `dadaia_workspace/features/bugs/**`, `dadaia_workspace/cli/commands/**`, `dadaia_workspace/public/schemas/**`, `dadaia_workspace/public/rules/bug-registration-guardrail.md`, migration/specs upgrade surfaces, bug/backlog memory as needed, tests, `specs/releases/v0.1.40/alpha-1/**`
- **Acceptance:** `dadaia bugs append|status|stats` work against append-only hourly JSONL; schema and event-coherence validation ship; Markdown bug migration path archives converted sources under `specs/bugs/_archive/`; existing bug-report workflow compatibility is preserved.
- **Validation:** `pytest -p no:cacheprovider tests/unit/features/bugs/test_events.py tests/integration/cli/test_cli_bugs.py -q` -> `4 passed`; `ruff check --no-cache` on touched bug telemetry files -> `All checks passed!`; `mypy --strict dadaia_workspace/features/bugs dadaia_workspace/cli/commands/bugs.py` -> `Success`; `dadaia public stage` + module-entry `dadaia public install --target all` + `dadaia public doctor` -> public-privacy/model/workflow checks OK.

### T3 - Add audit-disposition law

- **Status:** [x] DONE
- **Owner:** product-engineer
- **Write set:** `dadaia_workspace/features/lifecycle/workflows/audit.py`, audit fragments/rules, specs doctor/audit validation surfaces, tests, `specs/releases/v0.1.40/alpha-1/**`
- **Acceptance:** Audit findings require explicit disposition before archive; incomplete/invalid disposition is detected; audit archive to `specs/audits/_archive/` is allowed only after disposition-complete approval.
- **Validation:** `pytest -p no:cacheprovider tests/unit/features/specs/test_audit_dispositions.py -q` -> `5 passed`; `ruff check --no-cache` on touched doctor/test files -> `All checks passed!`; `mypy --strict dadaia_workspace/features/specs/doctor.py` -> `Success`; `dadaia specs doctor --specs-dir specs` -> `0 errors, 17 known warnings`; `dadaia public stage` + module-entry `dadaia public install --target all` + `dadaia public doctor` -> public-privacy/model/workflow checks OK.

### T4 - Make workflow-first lifecycle canonical

- **Status:** [x] DONE
- **Owner:** product-engineer
- **Write set:** `dadaia_workspace/public/rules/**`, `dadaia_workspace/public/skills/**`, relevant memory atoms in CLOSURE, tests/public doctor coverage, picked workflow-first bug file, `specs/releases/v0.1.40/alpha-1/**`
- **Acceptance:** Governing public surfaces state that dadaia-workflows are the default for supported lifecycle phases and manual fallback requires a registered workflow bug; public doctor remains green.
- **Validation:** `rg` contract check confirms workflow-first/default-action/fallback language across root AGENTS source, release/workspace rules, and lifecycle skills; `dadaia specs doctor --specs-dir specs` -> `0 errors, 17 known warnings`; `dadaia public stage` + module-entry `dadaia public install --target all` + `dadaia public doctor` -> public-privacy/model/ai-surface/workflow-policy checks OK.

### T5 - Align backlog terminal status and consume-aware doctor behavior

- **Status:** [-] IN PROGRESS
- **Owner:** product-engineer
- **Write set:** `dadaia_workspace/features/backlog/doctor.py`, `dadaia_workspace/features/specs/doctor.py`, backlog consume/ledger helpers, tests, picked backlog-doctor bug files, `specs/releases/v0.1.40/alpha-1/**`
- **Acceptance:** ADR-11 terminal statuses with version suffix pass both doctors; active release consumed backlog anchor movement does not block implementation commits solely due stale pre-refactor anchors; non-consumed stale anchors still fail.
- **Validation:** Focused backlog/specs doctor tests and `dadaia backlog doctor`.
