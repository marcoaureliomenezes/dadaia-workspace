# CLOSURE: v0.1.39 alpha-1 - SDD governance v2 taxonomy and workflow scope repair

**Status:** Aprovado
**Release ID:** v0.1.39
**Segment:** alpha-1
**Closed:** 2026-06-29
**Owner:** product-engineer

## Summary

v0.1.39 alpha-1 ships three connected repairs discovered while trying to define the
`sdd-governance-v2-agents-lifecycle` residual through dadaia-workflows:

- release-definition selected scope is now bounded to the operator-picked backlog,
  bug, and audit refs instead of injecting the full corpus;
- per-class specs archives for backlog, bugs, and audits are now part of the canonical
  scaffold/doctor taxonomy and classify as FROZEN in the SDD gate;
- single-step lifecycle review/close prompts now name the concrete active release
  artifact directory, including `ACTIVE.md` segment.

The picked backlog remains a candidate: v0.1.39 consumed only its taxonomy/archive
slice. JSONL bug-events and audit-disposition law remain explicit residuals.

## Evidence

| Task | Final commit | Evidence |
|------|--------------|----------|
| T1 - Bound release-definition selected scope | `7facb8d0c3eaf0deed356c5d0e4d5fb8f57fad3d` | `test_release_definition_spec_create_injects_only_selected_scope` passed; adjacent release-definition prompt-budget tests passed; ruff and mypy passed. |
| T2 - Freeze per-class specs archive taxonomy | `86be030358528efb0988f38f87151d08261480d3` | Gate classifier/scaffold/doctor focused tests passed; specs doctor returned `0 errors, 17 warnings`. |
| T3 - Segment-aware single-step lifecycle prompts | `0cd00cb243007be98a594b944166bd81df03a036` | Lifecycle prompt tests passed; PI QA rerun no longer failed on flat release artifact lookup. |

## Validation

- `pytest -p no:cacheprovider tests/integration/cli/test_release_definition_workflow.py::test_release_definition_spec_create_injects_only_selected_scope -q` -> `1 passed`.
- Adjacent release-definition checks
  `test_full_sequence_reaches_commit_gate_and_advances` and
  `test_release_definition_blocks_oversized_worker_prompt_before_runtime` -> `2 passed`.
- `pytest -p no:cacheprovider tests/integration/gate/test_classifier_reroot_matrix.py::test_full_pipeline_in_repo_matrix tests/integration/gate/test_classifier_reroot_matrix.py::test_per_class_archive_prefixes_are_frozen_before_additive -q` -> `25 passed`.
- Scaffold/doctor focused tests -> `2 passed`.
- `pytest -p no:cacheprovider tests/integration/cli/test_lifecycle_command_skeletons.py::test_phase_step_prompt_is_step_kind_aware tests/integration/cli/test_lifecycle_command_skeletons.py::test_release_artifact_dir_hint_uses_active_segment -q` -> `2 passed`.
- `ruff check --no-cache` on changed production/test files -> `All checks passed!`.
- `mypy --strict` on changed production modules -> `Success`.
- `dadaia specs doctor --specs-dir repos/dadaia-workspace/specs` -> `0 errors, 17 warnings`.
- `dadaia backlog doctor --specs-dir repos/dadaia-workspace/specs` -> clean.
- QA review handoff: `.dadaia/handoff/dadaia-workspace/2026-06-29T120000Z-qa-engineer-v0139-qa-pi-0cd00cb2.handoff.json`, `verdict: APPROVED`, `metrics.commit_sha: 0cd00cb243007be98a594b944166bd81df03a036`.
- Security review handoff: `.dadaia/handoff/dadaia-workspace/2026-06-29T120000Z-security-reviewer-v0139-security-pi-0cd00cb2.handoff.json`, `verdict: APPROVED`, `metrics.commit_sha: 0cd00cb243007be98a594b944166bd81df03a036`.

## Drift And Bugs

- Workflow-first release definition was attempted before this SPEC was written. It
  blocked because `spec_create` selected the full backlog/bug/audit corpus and exceeded
  the headless prompt budget. Fixed by T1.
- The first PI QA review for this segmented release looked for flat
  `specs/releases/v0.1.39/{SPEC,PLAN,TASKS}.md` artifacts. Fixed by T3.
- The final PI QA command returned a blocked CLI status even though the worker wrote an
  approved top-level handoff. This is an existing workflow-gate class, not a release
  regression; the approved handoff was used as review evidence.

## Dispositions

| Source | Disposition |
|--------|-------------|
| `specs/backlog/sdd-governance-v2-agents-lifecycle.md` | Partially consumed. Taxonomy/archive slice shipped; JSONL bug-events and audit-disposition law remain candidate residuals. |
| `specs/bugs/release-definition-spec-create-overselects-context-budget.md` | Closed by T1. |
| `specs/bugs/lifecycle-review-commands-miss-active-segment-artifacts.md` | Closed by T3. |

## Memory Updates

- `specs/memory/product/sdd/sdd-gate-v3.md` now records per-class archive FROZEN
  classification.
- `specs/memory/product/sdd/specs-doctor.md` now records TREE-4 per-class archive
  scaffold/repair behavior.
- `specs/memory/product/sdd/lifecycle-foundation.md` now records segment-aware
  single-step review/close prompts.
- `specs/memory/architecture.md` and `specs/memory/tech-stack.md` did not change.

## Archive Decision

Keep the release live under `specs/releases/v0.1.39/alpha-1/`. This is an alpha
segment, not a completed final release archive move.
