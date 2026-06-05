# TASKS: v0.1.4 - test-suite-architecture

**Status:** Aprovado
**Release ID:** v0.1.4
**Owner:** product-engineer
**Created:** 2026-06-03

---

## Execution Order

Maximum one `[-]` at a time unless this file is amended with explicit disjoint
write sets.

```text
T-TEST-01 -> T-TEST-02 -> T-TEST-03 -> T-TEST-04 -> T-TEST-05
          -> T-TEST-06 -> T-TEST-07 -> T-TEST-08 -> T-TEST-09
```

---

## Tasks

### T-TEST-01 - Add executable pytest taxonomy and tmp quarantine

- **Status:** [x]
- **Owner:** software-engineer-python + qa-engineer
- **Target files:** `pyproject.toml`, `tests/tmp/**`, `tests/README.md` or equivalent test docs

Add pytest markers for `unit`, `contract`, `integration`, `e2e`, `slow`, and
`tmp`. Remove coverage flags from default `addopts`. Add `tests/tmp/` and
exclude it from default collection. Document the no-slop test rules.

### T-TEST-02 - Split CI and release test commands by layer

- **Status:** [x]
- **Owner:** devops-engineer + qa-engineer
- **Target files:** `.github/workflows/ci.yml`, `.github/workflows/release.yml`

Replace the single `poetry run pytest -q` command with layer-specific jobs:
unit-fast, contract-coverage, integration, e2e-python, and e2e-panel. Keep the
80% coverage gate in explicit coverage job.

### T-TEST-03 - Create contract suite and promote current public contracts

- **Status:** [x]
- **Owner:** software-engineer-python + qa-engineer
- **Target files:** `tests/contract/**`, selected current tests from `tests/unit/**` and `tests/integration/**`

Create `tests/contract/`. Move or rewrite current public behavior checks for
handoff schema, report validation, public asset manifest/projection, SDD doctor
invariants, gate policy, panel API envelopes, and CLI output/status contracts.

### T-TEST-04 - Delete R2 QA gap and coverage-archive tests

- **Status:** [x]
- **Owner:** software-engineer-python
- **Target files:** `tests/unit/test_r2_qa_gaps.py`, replacement contract/unit files as needed

Delete `tests/unit/test_r2_qa_gaps.py` after preserving only still-current
lock/doctor/service behavior in properly named test files. Remove all `AC-COV`,
line-number coverage, `R-2`, and deleted-method assertions.

### T-TEST-05 - Remove deleted-method and removed-invariant tests

- **Status:** [x]
- **Owner:** software-engineer-python
- **Target files:** `tests/unit/test_spec_context_service.py`, `tests/unit/test_spec_context_doctor.py`, related spec_context tests

Delete assertions whose only purpose is proving `activate`, `deactivate`,
`promote`, or old INV-1/INV-2/INV-3/INV-6 behavior is absent. Keep current
alive/dead/delete and INV-4/INV-5 behavior.

### T-TEST-06 - Rewrite retired panel memory and palette tests

- **Status:** [x]
- **Owner:** software-engineer-python + qa-engineer
- **Target files:** `tests/unit/features/panel/test_memory_byte_identity.py`, `tests/unit/features/panel/test_palette.py`

Remove retired byte-identity canaries and duplicated exact palette constants.
Keep or promote current traversal, content-type, memory view, and token
source-of-truth contracts.

### T-TEST-07 - Collapse panel PR-history asset tests

- **Status:** [x]
- **Owner:** software-engineer-python + frontend-engineer + qa-engineer
- **Target files:** `tests/unit/features/panel/test_assets_pr3_10.py`, `test_assets_pr3_16.py`, `test_assets_pr3_17.py`, `test_pr304_theme_switcher.py`, `test_agents_expand_pr3_11.py`, replacement current-behavior test files

Rename or replace PR/task-numbered files with current behavior contracts.
Delete negative extraction/deleted-code assertions. Collapse string-presence
checks into parameterized contracts and keep only behavior-relevant UI shell,
ARIA, token, and module-loading checks.

### T-TEST-08 - Consolidate panel view/index tests

- **Status:** [x]
- **Owner:** frontend-engineer + qa-engineer
- **Target files:** `tests/unit/features/panel/test_views_index.py`, related panel view tests

Collapse per-element HTML presence tests into parameterized structural contracts.
Keep standalone tests for escaping/XSS, ordering, API auth bootstrapping, and
current user-visible shell behavior.

### T-TEST-09 - Budget integration/E2E journeys and verify suite

- **Status:** [x]
- **Owner:** qa-engineer + software-engineer-python
- **Target files:** `tests/e2e/features/test_handoff_pipeline.py`, `tests/integration/test_cli_import.py`, marker updates across tests

Mark/classify slow process-boundary tests. Keep one full handoff happy path and
one import journey. Move invalid-schema and archive edge cases to unit/contract
where possible. Run all validation commands from SPEC AC-10 and record timings.
