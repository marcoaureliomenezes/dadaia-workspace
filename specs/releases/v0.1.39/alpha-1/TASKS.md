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

- **Status:** [-] IN PROGRESS
- **Owner:** product-engineer
- **Write set:** `dadaia_workspace/features/spec_context/gate_policy.py`, scaffold/doctor source for canonical specs tree, related tests, `specs/backlog/sdd-governance-v2-agents-lifecycle.md`, `specs/releases/v0.1.39/alpha-1/**`
- **Acceptance:** `specs/backlog/_archive/**`, `specs/audits/_archive/**`, and `specs/bugs/_archive/**` classify as FROZEN and are known by scaffold/doctor.
- **Validation:** pending.
