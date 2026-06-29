---
name: codex-release-definition-spec_create-does-not-create-canonical-spec.md-artifact
status: Closed
severity: "HIGH"
surface: lifecycle bug report workflow
session_id: null
---

# Codex release-definition spec_create does not create canonical SPEC.md artifact

**Symptom:** Codex release-definition spec_create does not create canonical SPEC.md artifact

## Details

After PI and fake release-definition workers blocked at spec_create, the Codex Layer-2 harness was tried for v0.1.40. It also accepted release_scope but blocked at spec_create because specs/releases/v0.1.40/SPEC.md was missing. This leaves release-definition unusable for the current scope across all attempted workflow harnesses.

## Repro

.dadaia/.venv/bin/dadaia lifecycle release define --context dadaia-workspace --release-id v0.1.40 --run-id v0140-define-sdd-governance-v2-codex --backlog sdd-governance-v2-agents-lifecycle --bug backlog-doctor-bl-schema-vs-spec-doc-031-terminal-status-format-conflict --bug backlog-doctor-blocks-consumed-item-refactor-commit --bug lifecycle-prompts-still-depend-on-agents-remembering-to-use-dadaia-workflows-by-convention --bug pi-release-definition-spec_create-still-blocks-with-missing-artifact-evidence --bug fake-release-definition-spec_create-does-not-create-canonical-spec.md-artifact --harness codex --model gpt-5.5:medium --json

## Expected

Codex spec_create writes canonical SPEC.md artifact evidence or the workflow provides a deterministic artifact materialization path.

## Actual

Workflow returned BLOCKED at spec_create: spec_create missing canonical release artifact SPEC.md.

## Resolution

Fixed in v0.1.40 alpha-1 T1. Release-definition artifact refs are now relative to the
worker cwd. Codex workers run from the workspace root, so self-hosting release artifacts
must be addressed as `repos/dadaia-workspace/specs/releases/...`; the old
`specs/releases/...` ref pointed at a non-existent root-level specs tree.

Validation:

- Added repo-context regression coverage proving production fake writes canonical create
  artifacts under `repos/dadaia-workspace/specs/...` and not root `specs/...`.
- `pytest -p no:cacheprovider tests/integration/cli/test_release_definition_workflow.py::test_cli_fake_runtime_writes_canonical_create_artifacts tests/integration/cli/test_release_definition_workflow.py::test_cli_fake_runtime_writes_canonical_create_artifacts_in_repo_context tests/integration/cli/test_release_definition_workflow.py::test_handoff_only_spec_create_blocks_at_spec_create tests/integration/cli/test_release_definition_workflow.py::test_full_sequence_reaches_commit_gate_and_advances -q` -> `4 passed`.
