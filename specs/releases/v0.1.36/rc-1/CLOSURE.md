# Closure: Release — v0.1.36 rc-1 — PI Layer-2 release candidate

> **Status:** Aprovado
> **Release ID:** v0.1.36
> **Segment:** rc-1
> **Owner:** product-engineer
> **Closed:** 2026-06-28

## Summary

v0.1.36 rc-1 ships the already-closed `alpha-1` PI Layer-2 release-definition hardening
as the release candidate. This rc segment adds no product code and consumes no additional
backlog; it verifies the committed alpha changes, preserves the real PI live evidence, and
records the ship decision.

The alpha remains the implementation segment. This rc is the validation and release-candidate
gate over commits `2ce13f11` and `dd7ca936`.

## Tasks completed

All tasks in `TASKS.md` are `[x] DONE`.

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T1 | Run deterministic rc validation gates | this commit |
| T2 | Verify alpha live PI evidence is sufficient for rc ship | this commit |
| T3 | Close rc-1 | this commit |

## Validations

| Description | Command | Evidence |
|-------------|---------|----------|
| Ruff on rc-covered Python/test files | `.dadaia/.venv/bin/python -m ruff check --no-cache repos/dadaia-workspace/dadaia_workspace/features/lifecycle/workflows/release_definition.py repos/dadaia-workspace/tests/integration/cli/test_release_definition_workflow.py repos/dadaia-workspace/tests/integration/pi_live/test_real_layer2_worker_workflow_e2e.py` | `All checks passed!` |
| Focused deterministic rc pytest gate | `.dadaia/.venv/bin/python -m pytest -p no:cacheprovider repos/dadaia-workspace/tests/integration/cli/test_release_definition_workflow.py repos/dadaia-workspace/tests/contract/test_headless_runtime_security.py repos/dadaia-workspace/tests/unit/core/test_lifecycle_models.py repos/dadaia-workspace/tests/integration/pi_live/test_real_layer2_worker_workflow_e2e.py -q` | `37 passed, 2 skipped in 14.60s` |
| Specs structural doctor | `.dadaia/.venv/bin/dadaia specs doctor --specs-dir repos/dadaia-workspace/specs` | `0 error(s), 18 warning(s)`; warnings are legacy/pre-existing archive, memory, and backlog warnings |
| Public projection doctor | `.dadaia/.venv/bin/dadaia public doctor` | `[ok] public-privacy`; `[ok] model-resolution`; `[ok] ai-surface (no reintroduced lifecycle ritual)`; `[ok] workflow-policy (no Layer-2 claude/opencode worker residue)` |
| Repo hygiene scan | `find repos/dadaia-workspace -type d \( -name .dadaia -o -name .venv -o -name .pytest_cache -o -name .mypy_cache -o -name .hypothesis -o -name .ruff_cache -o -name test-results -o -name playwright-report -o -name coverage \) -print` | no output |
| Alpha live PI command, create, and review evidence retained | `specs/releases/v0.1.36/alpha-1/CLOSURE.md` | Alpha records direct real PI command smoke, active-worker smoke, real PI command/create e2e, and `1 passed in 340.50s` for the real PI `spec_arch_review` gate with verdict `APPROVED` |

## Drifts

### rc-validation-only

**Description:** The operator initially mentioned `v0.1.38`, then corrected the target to
`v0.1.36`. The active release is `v0.1.36`, so rc-1 stayed on the active release and did
not open or rename another SemVer line.

**Resolution:** `rc-1` is validation-only over the closed `alpha-1` work.

**Memory updates:** none.

## Memory updates

No memory files were changed in this rc segment. The product truth changes for PI Layer-2
release-definition behavior were already recorded in `alpha-1` closure:

- `specs/memory/product/sdd/lifecycle-foundation.md`
- `specs/memory/architecture.md`
- `specs/memory/tech-stack.md`

## Dispositions

No additional bugs or backlog items were picked into `rc-1`. The bug dispositions completed
in `alpha-1` remain the release dispositions for v0.1.36:

| File | Kind | Terminal status | Evidence |
|------|------|-----------------|----------|
| `specs/bugs/lifecycle-step-model-overrides-collapse-by-runtime-kind.md` | bug | `Closed` | `alpha-1/CLOSURE.md` |
| `specs/bugs/pi-default-review-profiles-gpt-5-5-unreachable-provider.md` | bug | `Closed` | `alpha-1/CLOSURE.md` |
| `specs/bugs/bug-spec-create-pi-no-artifact-bug_write.md` | bug | `Closed` | `alpha-1/CLOSURE.md` |
| `specs/bugs/release-define-pi-worker-long-running-no-progress-heartbeat.md` | bug | `Closed` | `alpha-1/CLOSURE.md` |
| `specs/bugs/backlog-definition-pi-intake-grill-artifact-evidence-gate.md` | bug | `Closed` | `alpha-1/CLOSURE.md` |
| `specs/bugs/release-definition-pi-create-step-blocks-on-model-reported-hash.md` | bug | `Closed` | `alpha-1/CLOSURE.md` |
| `specs/bugs/live-pi-review-e2e-fixture-stale-cli-architecture.md` | bug | `Closed` | `alpha-1/CLOSURE.md` |

## Backlog returns

- `pi-agent-fourth-harness` remains candidate for WS-PI-5 only: DEAD-mark the standalone
  `dadaia-pi-workspace` context after operator-safe handling.
- `bug-report-fake-bug-write-emits-stub-and-discards-fields` remains open for a later
  workflow-hardening release.
- `lifecycle-status-no-args-hangs-100pct-cpu` remains open for a later workflow-hardening
  release.

## Archive decision

**KEEP** — `v0.1.36/rc-1` is closed as release-candidate evidence and ready to commit.
Archive movement is left to the explicit lifecycle archive/ship step after this rc commit.
