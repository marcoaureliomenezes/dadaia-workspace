# TASKS: v0.1.39 alpha-1 - SDD governance v2 taxonomy and workflow scope repair

**Status:** Aprovado
**Release ID:** v0.1.39
**Segment:** alpha-1
**Owner:** product-engineer
**Created:** 2026-06-29

Marks: `[ ]` OPEN, `[-]` IN PROGRESS, `[x]` DONE.

---

## Tasks

### T1 - Bound release-definition selected scope

- **Status:** [x] DONE
- **Owner:** product-engineer
- **Write set:** `dadaia_workspace/features/lifecycle/context_selector.py`, `dadaia_workspace/features/lifecycle/workflows/release_definition.py`, `tests/integration/cli/test_release_definition_workflow.py`, `specs/bugs/release-definition-spec-create-overselects-context-budget.md`, `specs/releases/v0.1.39/alpha-1/**`
- **Acceptance:** `spec_create` injects only operator-selected backlog/bug/audit items; the scoped v0.1.39 release-definition workflow no longer blocks on prompt size.
- **Validation:** `pytest -p no:cacheprovider tests/integration/cli/test_release_definition_workflow.py::test_release_definition_spec_create_injects_only_selected_scope -q` -> `1 passed`; adjacent release-definition checks -> `2 passed`; `ruff check --no-cache` on changed files -> `All checks passed!`; `mypy --strict` on changed selector/container -> `Success`.

### T2 - Freeze per-class specs archive taxonomy

- **Status:** [x] DONE
- **Owner:** product-engineer
- **Write set:** `dadaia_workspace/features/spec_context/gate_policy.py`, scaffold/doctor source for canonical specs tree, related tests, `specs/backlog/sdd-governance-v2-agents-lifecycle.md`, `specs/releases/v0.1.39/alpha-1/**`
- **Acceptance:** `specs/backlog/_archive/**`, `specs/audits/_archive/**`, and `specs/bugs/_archive/**` classify as FROZEN and are known by scaffold/doctor.
- **Validation:** `pytest -p no:cacheprovider tests/integration/gate/test_classifier_reroot_matrix.py::test_full_pipeline_in_repo_matrix tests/integration/gate/test_classifier_reroot_matrix.py::test_per_class_archive_prefixes_are_frozen_before_additive -q` -> `25 passed`; scaffold/doctor focused tests -> `2 passed`; `ruff check --no-cache` on changed files -> `All checks passed!`; `mypy --strict` on changed taxonomy/scaffold files -> `Success`; `dadaia specs doctor --fix --specs-dir repos/dadaia-workspace/specs` -> `0 errors, 17 warnings`.

### T3 - Segment-aware single-step lifecycle prompts

- **Status:** [x] DONE
- **Owner:** product-engineer
- **Write set:** `dadaia_workspace/cli/commands/lifecycle.py`, `tests/integration/cli/test_lifecycle_command_skeletons.py`, `specs/bugs/lifecycle-review-commands-miss-active-segment-artifacts.md`, `specs/releases/v0.1.39/alpha-1/**`
- **Acceptance:** QA/security/code/close prompts name the concrete active segment artifact dir when `ACTIVE.md` has a matching segment; QA workflow no longer rejects due flat-path lookup.
- **Validation:** `pytest -p no:cacheprovider tests/integration/cli/test_lifecycle_command_skeletons.py::test_phase_step_prompt_is_step_kind_aware tests/integration/cli/test_lifecycle_command_skeletons.py::test_release_artifact_dir_hint_uses_active_segment -q` -> `2 passed`; `ruff check --no-cache` on changed CLI/test files -> `All checks passed!`; `mypy --strict dadaia_workspace/cli/commands/lifecycle.py` -> `Success`; PI QA rerun `v0139-qa-pi-1306ff32` resolved the original flat-path failure and reached this T3 task state.
