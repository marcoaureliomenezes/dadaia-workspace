# Closure: Release — v0.1.37 alpha-1 — PI workflow hardening

> **Status:** Aprovado
> **Release ID:** v0.1.37
> **Segment:** alpha-1
> **Owner:** product-engineer
> **Closed:** 2026-06-29

## Summary

v0.1.37 alpha-1 hardens PI as a Layer-2 worker for `dadaia lifecycle` workflows. The
release prevents recursive lifecycle invocation from review workers, narrows PI review
tools, budgets release-definition prompts before headless runtime launch, makes top-level
`lifecycle status` bounded, repairs fake/default bug-report writing, and fixes two
additional live PI review defects found during validation: successful single-step review
runs now persist as completed, and PI recovers valid handoff files when its final message
omits `artifact_refs`.

This segment publishes nothing and creates no tag.

## Tasks completed

All tasks in `TASKS.md` are `[x] DONE`.

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T1 | Guard Layer-2 workers against recursive lifecycle commands | `56b63d31` |
| T2 | Add headless prompt budgeting for release definition | `d111548b` |
| T3 | Fix lifecycle status no-arg behavior | `a6727ade` |
| T4 | Fix bug-report workflow default writer fidelity | `bfd9c622` |
| T5 | Validate PI workflow hardening and update dispositions | this closure span |

## Validations

| Description | Command | Evidence |
|-------------|---------|----------|
| Focused deterministic workflow suite | `.dadaia/.venv/bin/python -m pytest -p no:cacheprovider repos/dadaia-workspace/tests/contract/test_lifecycle_prompt_scope.py repos/dadaia-workspace/tests/contract/test_headless_runtime_security.py repos/dadaia-workspace/tests/integration/cli/test_release_definition_workflow.py repos/dadaia-workspace/tests/integration/cli/test_lifecycle_cli.py repos/dadaia-workspace/tests/integration/cli/test_lifecycle_bug_report_workflow.py -q` | `43 passed in 16.21s` |
| Ruff on touched files | `.dadaia/.venv/bin/python -m ruff check --no-cache <touched files>` | `All checks passed!` |
| Strict typing on touched production files | `.dadaia/.venv/bin/python -m mypy --strict <touched production files>` | `Success: no issues found in 6 source files` |
| Real PI security-review workflow smoke | `timeout 420 .dadaia/.venv/bin/dadaia lifecycle review security --context dadaia-workspace --release-id v0.1.37 --run-id v0137-security-pi-smoke-6bce104a --harness pi --model gpt-5.3-codex-spark:medium --json` | `accepted: true`, runtime `pi_headless`, status `OK`; persisted run `.dadaia/states/lifecycle/v0137-security-pi-smoke-6bce104a.json` has `status: completed` |
| PI security handoff evidence | `.dadaia/handoff/dadaia-workspace/2026-06-28T120000Z-security-reviewer-v0137-security.handoff.json` | `verdict: APPROVED`, `metrics.commit_sha: 6bce104a3018718d44efe838dff6fad2343947b6` |
| Specs structural doctor | `.dadaia/.venv/bin/dadaia specs doctor --specs-dir repos/dadaia-workspace/specs` | `0 error(s), 18 warning(s)`; warnings are legacy/pre-existing archive, memory, and backlog warnings |
| Public projection doctor | `.dadaia/.venv/bin/dadaia public doctor` | `[ok] public-privacy`; `[ok] model-resolution`; `[ok] ai-surface`; `[ok] workflow-policy` |
| Repo hygiene scan | `find repos/dadaia-workspace -type d \( -name .dadaia -o -name .venv -o -name .pytest_cache -o -name .mypy_cache -o -name .hypothesis -o -name .ruff_cache -o -name test-results -o -name playwright-report -o -name coverage \) -print` | no output |

## Dispositions

| File | Kind | Terminal status | Evidence |
|------|------|-----------------|----------|
| `specs/bugs/pi-security-review-worker-recurses-into-lifecycle-command.md` | bug | `Closed` | Prompt boundary guard + PI review tools `read,write`; focused tests and real PI smoke |
| `specs/bugs/release-definition-spec-create-overinjects-context-exceeds-codex-input-limit.md` | bug | `Closed` | Release-definition prompt budget block before runtime launch |
| `specs/bugs/lifecycle-status-no-args-hangs-100pct-cpu.md` | bug | `Closed` | Top-level status now bounded to run-store counters |
| `specs/bugs/bug-report-fake-bug-write-emits-stub-and-discards-fields.md` | bug | `Closed` | Fake writer now materializes `BugReportInput` fields |
| `specs/bugs/lifecycle-review-success-leaves-run-state-running.md` | bug | `Closed` | Single-step phase workflow persists accepted runs as `COMPLETED` |
| `specs/bugs/pi-headless-does-not-recover-written-handoff-without-artifact-refs.md` | bug | `Closed` | PI recovers newly written matching handoff evidence |

## Backlog returns

- `pi-agent-fourth-harness` remains candidate only for WS-PI-5: operator-gated
  DEAD-marking of standalone `dadaia-pi-workspace`. It was not consumed by this release.
- No additional backlog item was consumed.

## Memory updates

- `specs/memory/product/sdd/lifecycle-foundation.md`
- `specs/memory/tech-stack.md`
