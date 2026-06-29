---
name: pi-release-definition-spec_create-still-blocks-with-missing-artifact-evidence
status: Closed
severity: "HIGH"
surface: lifecycle bug report workflow
session_id: null
---

# PI release-definition spec_create still blocks with missing artifact evidence

**Symptom:** PI release-definition spec_create still blocks with missing artifact evidence

## Details

While defining v0.1.40 through dadaia lifecycle release define with --harness pi and model gpt-5.3-codex-spark:medium, the workflow accepted release_scope but blocked at spec_create with reason 'agent result missing artifact evidence'. This repeats the previously claimed-fixed class and prevents PI from being the default release-definition worker for this SDD governance release.

## Repro

timeout 900 .dadaia/.venv/bin/dadaia lifecycle release define --context dadaia-workspace --release-id v0.1.40 --run-id v0140-define-sdd-governance-v2 --backlog sdd-governance-v2-agents-lifecycle --bug backlog-doctor-bl-schema-vs-spec-doc-031-terminal-status-format-conflict --bug backlog-doctor-blocks-consumed-item-refactor-commit --bug lifecycle-prompts-still-depend-on-agents-remembering-to-use-dadaia-workflows-by-convention --harness pi --model gpt-5.3-codex-spark:medium --json

## Expected

PI spec_create emits canonical SPEC artifact evidence or a recoverable matching handoff so the release-definition workflow advances.

## Actual

Workflow returned BLOCKED at spec_create: agent result missing artifact evidence.

## Resolution

Fixed in v0.1.40 alpha-1 T1. Release-definition artifact refs are now computed relative
to the worker cwd instead of `specs_dir.parent`. In the self-hosting workspace, Layer-2
workers run from the workspace root, so the canonical allowed path is
`repos/dadaia-workspace/specs/releases/...`, not `specs/releases/...`. The prior prompt
path pointed PI at a non-existent root-level specs tree, so `spec_create` returned no
usable artifact evidence.

Validation:

- Added repo-context regression coverage proving production fake writes canonical create
  artifacts under `repos/dadaia-workspace/specs/...` and not root `specs/...`.
- `pytest -p no:cacheprovider tests/integration/cli/test_release_definition_workflow.py::test_cli_fake_runtime_writes_canonical_create_artifacts tests/integration/cli/test_release_definition_workflow.py::test_cli_fake_runtime_writes_canonical_create_artifacts_in_repo_context tests/integration/cli/test_release_definition_workflow.py::test_handoff_only_spec_create_blocks_at_spec_create tests/integration/cli/test_release_definition_workflow.py::test_full_sequence_reaches_commit_gate_and_advances -q` -> `4 passed`.
