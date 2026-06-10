# Contract Tests

Contracts pin public APIs, schemas, security boundaries, projection output, and
**anti-drift invariants** so that drift fails CI instead of rotting silently. Every test
here carries `pytestmark = pytest.mark.contract`.

These two policies (mirrored in `specs/AGENTS.md`) are binding for contract authors:

## Consistency-contract-at-introduction

When you introduce a **new hand-maintained pairing** — two tables/files/constant sets that
must stay in sync (a mapping and its derived view, a schema and its fixtures, a config list
and its consumer) — write the consistency contract in the **same change**. The contract
pins the shared invariant: identical key-sets, a capped count, or an absence-of-residue
grep. Do not land the pairing and add the guard "later" — the unguarded window is exactly
when drift gets in.

## Lifecycle-asymmetry coverage

Creation-path tests routinely miss the asymmetric paths. For every feature, ensure tests
(or a documented, justified absence) cover:

- **delete / orphan** — entity removed or left dangling;
- **dirty input** — malformed, partial, or hostile input;
- **missing dependency** — a required upstream artifact/file/service absent.

A residue grep is the canonical contract form for the delete/orphan path: it proves the
retired thing did not resurface. An undocumented asymmetric path is a gap, not coverage.

## Active contracts (inventory)

| File | Pins |
|---|---|
| `test_import_linter_ignore_cap.py` | **Cap**: total `setup.cfg` import-linter `ignore_imports` edges ≤ recorded cap (17); fails on growth (arch F10) |
| `test_retired_model_id_residue.py` | **Residue**: retired model ids (`claude-haiku-3-5`) absent from live code, excluding the registry lineage docstring; do not resolve in the registry index |
| `test_bash_hook_residue.py` | **Residue**: retired bash hook quartet absent from `public/scripts/` and not shipped/invoked from code (`pre-push-ci-gate.sh` retained) |
| `test_harness_env_contract.py` | **Ratchets**: `DADAIA_*` setenv outside the fixture, and in-process hook imports under gate tests — growth-only baselines |
| `test_session_store_ownership.py` | Session-store ownership residue (retired multi-store model) |
| `test_session_bound_context_residue.py` | Session-bound context residue |
| `test_source_repo_hygiene.py` | Source-repo files stay visible to review/CI (no stray ignores) |
| `test_handoff_schema_contract.py` | Public handoff sidecar schema (`handoff-v1.1`) |
| `test_platform_classifier.py` | `pyproject.toml` OS classifiers |
| `test_install_skip_idempotent.py` | `write_generated` idempotent across newline conventions |
| `test_reports_retention_cleanup.py` | Reports-retention cleanup behavior |
| `test_codex_reference_only_wording.py` | Codex orchestration wording (agents vs workflow docs) |
| `test_workflow_review_gate_contract.py` | Implementation-review-QA done gate |
| `cli/` | CLI output/status contracts |

When you add a contract, add a row here in the same change.
