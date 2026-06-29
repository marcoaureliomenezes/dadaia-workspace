---
name: fake-release-definition-spec_create-does-not-create-canonical-spec.md-artifact
status: Closed
severity: "HIGH"
surface: lifecycle bug report workflow
session_id: null
---

# Fake release-definition spec_create does not create canonical SPEC.md artifact

**Symptom:** Fake release-definition spec_create does not create canonical SPEC.md artifact

## Details

After PI release-definition blocked at spec_create, the documented deterministic fallback was tried with --harness fake. The workflow still blocked at spec_create because specs/releases/v0.1.40/SPEC.md was missing. This prevents even fake release-definition from producing canonical release artifacts.

## Repro

.dadaia/.venv/bin/dadaia lifecycle release define --context dadaia-workspace --release-id v0.1.40 --run-id v0140-define-sdd-governance-v2-fake --backlog sdd-governance-v2-agents-lifecycle --bug backlog-doctor-bl-schema-vs-spec-doc-031-terminal-status-format-conflict --bug backlog-doctor-blocks-consumed-item-refactor-commit --bug lifecycle-prompts-still-depend-on-agents-remembering-to-use-dadaia-workflows-by-convention --bug pi-release-definition-spec_create-still-blocks-with-missing-artifact-evidence --harness fake --json

## Expected

Fake release-definition remains a deterministic workflow driver and creates the canonical SPEC/PLAN/TASKS artifacts required by gates.

## Actual

Workflow returned BLOCKED at spec_create: spec_create missing canonical release artifact SPEC.md.

## Resolution

Fixed in v0.1.40 alpha-1 T1. Production `FakeAgentRuntime` now materializes a
deterministic Markdown artifact when a workflow create step explicitly allows a canonical
`SPEC.md`, `PLAN.md`, or `TASKS.md` path, and returns the artifact ref plus SHA-256 hash.
The canonical artifact gate remains strict: handoff-only create success still blocks.

Validation:

- `pytest -p no:cacheprovider tests/integration/cli/test_release_definition_workflow.py::test_cli_fake_runtime_writes_canonical_create_artifacts tests/integration/cli/test_release_definition_workflow.py::test_handoff_only_spec_create_blocks_at_spec_create tests/integration/cli/test_release_definition_workflow.py::test_full_sequence_reaches_commit_gate_and_advances -q` -> `3 passed`.
- `ruff check --no-cache dadaia_workspace/infrastructure/fake_runtime.py tests/integration/cli/test_release_definition_workflow.py` -> `All checks passed!`.
- `mypy --strict dadaia_workspace/infrastructure/fake_runtime.py` -> `Success`.
