# Closure: Release — v0.1.36 alpha-1 — PI Layer-2 validation hardening

> **Status:** Aprovado
> **Release ID:** v0.1.36
> **Segment:** alpha-1
> **Owner:** product-engineer
> **Closed:** 2026-06-28

## Summary

v0.1.36 alpha-1 makes PI a more reliable Layer-2 workflow worker for
`dadaia lifecycle release define`. The release fixes stale PI model identity, qualifies PI
model execution to the `openai-codex` provider, forwards PI thinking effort, and makes
release-definition `--step-model` selection truly step-specific instead of collapsing by
runtime kind.

The segment also aligns the release-definition create-step prompts with the Python artifact
gate: SPEC/PLAN/TASKS create workers are now explicitly instructed to write canonical
release artifacts and return path/hash evidence. A real PI smoke verified
`openai-codex/gpt-5.3-codex-spark`, and a bounded workflow smoke verified that live PI
workers are visible through the persisted `active_worker` run-state marker while running.

## Tasks completed

All tasks in `TASKS.md` are `[x] DONE`.

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T1 | Refresh PI model catalog and adapter command | this commit |
| T2 | Fix release-definition per-step model routing | this commit |
| T3 | Require canonical artifacts from release-definition create fragments | this commit |
| T4 | Update PI bug records and live validation evidence | this commit |
| T5 | Persist active-worker state for live release-definition steps | this commit |

## Validations

| Description | Command | Evidence |
|-------------|---------|----------|
| Focused PI adapter/catalog/release-definition/panel/public tests | `.dadaia/.venv/bin/python -m pytest -p no:cacheprovider repos/dadaia-workspace/tests/contract/test_headless_runtime_security.py repos/dadaia-workspace/tests/unit/core/test_harness_models.py repos/dadaia-workspace/tests/unit/core/test_lifecycle_models.py repos/dadaia-workspace/tests/integration/cli/test_release_definition_workflow.py repos/dadaia-workspace/tests/integration/panel/test_workflows_api.py repos/dadaia-workspace/tests/integration/test_public_assets.py -q` | `103 passed` |
| Ruff on touched Python files | `.dadaia/.venv/bin/python -m ruff check --no-cache <touched files> --config repos/dadaia-workspace/pyproject.toml` | `All checks passed!` |
| Specs structural doctor | `.dadaia/.venv/bin/dadaia specs doctor --specs-dir repos/dadaia-workspace/specs` | `0 error(s), 18 warning(s)`; warnings are legacy/pre-existing memory/archive/backlog warnings |
| Direct real PI provider-qualified command smoke | `pi --mode json --model openai-codex/gpt-5.3-codex-spark --thinking low --no-tools --no-session --no-context-files -p "Reply with exactly: OK"` | PI returned provider `openai-codex`, model `gpt-5.3-codex-spark`, final text `OK` |
| Bounded real PI workflow active-worker smoke | `timeout 60s .dadaia/.venv/bin/dadaia lifecycle release define --context dadaia-workspace --release-id v0.1.36-pi-active-worker-smoke --run-id v0136-pi-active-worker-smoke --harness fake --step-harness release_scope=pi --step-model release_scope=gpt-5.3-codex-spark:medium --json` | During the run, `.dadaia/states/lifecycle/v0136-pi-active-worker-smoke.json` showed `active_worker.step=release_scope`, `active_worker.runtime_kind=pi_headless`, populated timestamps, and non-empty `injected_context` |
| PI backlog-definition structured-data gate regression | `.dadaia/.venv/bin/python -m pytest -p no:cacheprovider repos/dadaia-workspace/tests/integration/test_backlog_definition_workflow.py::test_intake_grill_accepts_structured_data_without_artifact_refs repos/dadaia-workspace/tests/integration/test_cli_backlog_define.py -q` | `6 passed` |
| Public asset projection doctor | `.dadaia/.venv/bin/dadaia public stage`; `.dadaia/.venv/bin/dadaia public doctor` | staged lifecycle fragments are coherent; doctor reports `[ok] public-privacy`, `[ok] model-resolution`, `[ok] workflow-policy`; only expected dirty-source warnings |
| Repo hygiene scan | `find repos/dadaia-workspace -type d \( -name .pytest_cache -o -name .ruff_cache -o -name .mypy_cache -o -name test-results -o -name playwright-report -o -name .dadaia \) -print` | no output |

## Drifts

### delivered-epics-sanitized-not-consumed

**Description:** The operator asked to work on three backlog recommendations. Two of the
named epics, `workflow-model-governance-panel-control-plane` and
`workflow-step-handoff-data-plane-cleanup`, were already delivered. Consuming them again
would corrupt backlog truth.

**Resolution:** The release consumed current residual bugs correlated with those epics
instead: PI model governance defects, release-definition create artifact defects, and
workflow run-state observability while PI is active. `pi-agent-fourth-harness` remains
candidate because its remaining WS-PI-5 context DEAD-mark is operator-gated.

**Memory updates:** `lifecycle-foundation.md`, `architecture.md`, and `tech-stack.md`
updated to current model/adapter/run-state truth.

### full-pi-release-definition-run-is-expensive-and-long-running

**Description:** Full live PI release-definition validation is multi-step and can spend
minutes inside a real worker. Early scratch runs were terminated after gathering evidence
because they provided no intermediate lifecycle visibility before v0.1.36's active-worker
marker.

**Resolution:** The release fixed the observability gap with `LifecycleRun.active_worker`
and validated the marker with a bounded real-PI `release_scope` workflow run. Full PI
end-to-end release-definition remains an opt-in live-worker exercise because it spends
operator credits and runtime.

**Memory updates:** `lifecycle-foundation.md` records the active-worker marker.

## Memory updates

Files written during this CLOSURE phase:

- `specs/memory/product/sdd/lifecycle-foundation.md` — PI catalog now uses
  `gpt-5.3-codex-spark`; `PiHeadlessAdapter` now provider-qualifies GPT ids and forwards
  `--thinking`; release-definition persists `active_worker` while a live worker is active.
- `specs/memory/architecture.md` — Layer-2 model catalog and PI command semantics updated
  to `gpt-5.3-codex-spark` and provider-qualified PI execution.
- `specs/memory/tech-stack.md` — PI runtime bullet updated with the live-verified
  `openai-codex/gpt-5.3-codex-spark` smoke and command semantics.
- `specs/memory/product/index.md` and `specs/memory/product/catalog.json` — no change: no
  feature atom was added or removed.

## Dispositions

| File | Kind | Terminal status | Evidence |
|------|------|-----------------|----------|
| `specs/bugs/lifecycle-step-model-overrides-collapse-by-runtime-kind.md` | bug | `Closed` | T2; release-definition step-model regression |
| `specs/bugs/pi-default-review-profiles-gpt-5-5-unreachable-provider.md` | bug | `Closed` | T1; provider-qualified PI command contract + direct PI smoke |
| `specs/bugs/bug-spec-create-pi-no-artifact-bug_write.md` | bug | `Closed` | T3; canonical create-fragment artifact contract |
| `specs/bugs/release-define-pi-worker-long-running-no-progress-heartbeat.md` | bug | `Closed` | T5; active-worker run-state regression + bounded PI smoke |
| `specs/bugs/backlog-definition-pi-intake-grill-artifact-evidence-gate.md` | bug | `Closed` | Structured-data gate regression; `intake_grill` accepts schema-valid data without artifact refs |

## Backlog returns

- `pi-agent-fourth-harness` remains candidate for WS-PI-5 only: DEAD-mark the standalone
  `dadaia-pi-workspace` context after operator-safe handling. It was intentionally not
  consumed here.
- `workflow-model-governance-panel-control-plane` remains delivered in earlier releases;
  this alpha only cleaned up PI model-governance residuals.
- `workflow-step-handoff-data-plane-cleanup` remains delivered in earlier releases; this
  alpha only tightened create-step artifact handoff instructions.
- `bug-report-fake-bug-write-emits-stub-and-discards-fields` remains open and should be
  considered for the next workflow-hardening release.
- `lifecycle-status-no-args-hangs-100pct-cpu` remains open and should be considered for the
  next workflow-hardening release.

## Archive decision

**KEEP** — this is a segmented `alpha-1` closure. The segment is closeable and ready to
commit, but the release directory should remain under `specs/releases/v0.1.36/alpha-1/`
until the coordinator opens the next segment or makes an explicit ship/archive decision.
