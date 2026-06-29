---
name: pi-security-review-handoff-can-emit-short-commit-sha-and-miss-pre-push-exact-sha-gate
status: Closed
severity: "MEDIUM"
surface: lifecycle bug report workflow
resolved: 2026-06-29
release: v0.1.37
session_id: null
---

# PI security review handoff can emit short commit SHA and miss pre-push exact-SHA gate

**Symptom:** PI security review handoff can emit short commit SHA and miss pre-push exact-SHA gate

## Repro

Run dadaia lifecycle review security --context dadaia-workspace --release-id v0.1.37 --run-id v0137-security-pi-final-d9f1d81c --harness pi --model gpt-5.3-codex-spark:medium --json, then inspect the emitted security-reviewer handoff metrics.commit_sha

## Expected

security-reviewer handoff metrics.commit_sha is the exact pushed 40-character commit SHA required by the pre-push security-verdict gate

## Actual

PI emitted an APPROVED handoff with metrics.commit_sha=d9f1d81c, while HEAD was d9f1d81c686f4aea5a60d16722d72b86457b7896

## Root Cause

The single-step review prompt required a security handoff but did not provide the exact
40-character HEAD SHA or explicitly forbid abbreviation. A PI worker could therefore emit an
approved handoff with a short SHA that the exact-match pre-push security-verdict gate would not
accept.

## Fix

`dadaia_workspace/cli/commands/lifecycle.py` now discovers the current context repo HEAD and
includes the exact 40-character SHA in review-step prompts, with an explicit "do not abbreviate"
instruction for `metrics.commit_sha`.

## Validation

- `.dadaia/.venv/bin/python -m pytest -p no:cacheprovider repos/dadaia-workspace/tests/integration/cli/test_lifecycle_cli.py -q` -> `15 passed`
- `.dadaia/.venv/bin/python -m ruff check --no-cache repos/dadaia-workspace/dadaia_workspace/cli/commands/lifecycle.py repos/dadaia-workspace/tests/integration/cli/test_lifecycle_cli.py` -> `All checks passed!`
- `.dadaia/.venv/bin/python -m mypy --strict repos/dadaia-workspace/dadaia_workspace/cli/commands/lifecycle.py` -> `Success`
