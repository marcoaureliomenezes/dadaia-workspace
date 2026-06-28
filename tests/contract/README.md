# Contract Tests

Contract tests pin public APIs, schemas, security boundaries, projection privacy, and
governance invariants. Every test here carries `pytestmark = pytest.mark.contract`.

Contracts are not history storage. A test belongs here only when it protects a current
boundary that external callers, projected runtime assets, security review, or release
governance depends on.

## Admission Rules

A contract test must name the current boundary it protects:

- public CLI output, exit behavior, or JSON shape;
- public HTTP/API/schema shape;
- security or workspace-boundary behavior;
- projection privacy or source-repo hygiene;
- deterministic governance invariant with a current owner.

Do not add contract tests that only prove deleted code remains deleted. A residue grep is
allowed only for a named current boundary, such as credential leakage, unsupported public
CLI resurrection, projected privacy, or compatibility with existing workspace state. The
test docstring must state that boundary and the condition under which the grep can retire.

## Consistency Contracts

When a change introduces a hand-maintained pairing that must stay synchronized, add the
consistency contract in the same change. Examples: a schema and fixtures, a public mapping
and rendered view, a config list and its consumer, or a projection manifest and deployed
asset set.

Keep the contract at the shared invariant level: identical key sets, a capped count,
schema validation, or a public shape. Do not expand it into a private implementation
matrix.

## Current Inventory

| Area | Contract files |
|---|---|
| CLI | `cli/` |
| Handoff/report schemas | `test_handoff_schema_contract.py`, `test_reports_retention_cleanup.py` |
| Source/projection hygiene | `test_source_repo_hygiene.py`, `test_install_skip_idempotent.py` |
| Harness/env boundaries | `test_harness_env_contract.py`, `test_lease_probe_residue.py` |
| Workflow/review gates | `test_workflow_review_gate_contract.py` |
| Platform/package metadata | `test_platform_classifier.py`, `test_import_linter_ignore_cap.py` |
| Model registry behavior | `test_retired_model_id_residue.py` |
| Codex wording/current public surface | `test_codex_reference_only_wording.py` |

When adding a contract, add it to this table and explain why unit or integration coverage
is insufficient.

## Critical Behavior Ownership

Spec Context Project contracts protect binding, workspace/repo boundaries, leases, gate
classification, and session identity.

Panel contracts protect route/security boundaries, API shapes, and mutation guards. Browser
journeys live in E2E; contract tests should not fake a full browser journey.

dadaia-workflows/lifecycle contracts protect public workflow CLI shape, handoff/verdict
gates, runtime/model selection boundaries, and run-store safety.
