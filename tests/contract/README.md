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
| `test_harness_env_contract.py` | **Hard-fail (no baseline)**: any non-allowlisted `DADAIA_*` setenv outside the fixture; any test that imports a hook behavior module AND simulates `sys.stdin` in-process to drive its `main()` |
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

## Lifecycle-asymmetry coverage map (retroactive)

This map discharges the "Lifecycle-asymmetry coverage" policy above for the main features:
each row records where the three asymmetric paths (**delete/orphan**, **dirty input**,
**missing dependency**) are actually covered, grounded in real test names (grep-verified,
not aspirational). A `GAP` marks an honest, unaddressed asymmetric path; the map — not a
retroactive test — is the deliverable, so a `GAP` is documented rather than papered over.

| Feature | Delete / orphan | Dirty input | Missing dependency |
|---|---|---|---|
| **spec_context lifecycle** (`dead`/clean-tree) | `unit/test_spec_context_service.py::test_dead_removes_repo_and_marks_dead`, `::test_dead_clean_tree_unchanged_no_untracked`; residue `contract/test_session_bound_context_residue.py` | `unit/test_spec_context_service.py::test_dead_with_commit_blocks_on_planted_secret` / `_private_ip` / `_untracked_pem_key_file`, `::test_dead_refuses_on_untracked_files_without_commit` | `unit/test_spec_context_service.py::test_dead_not_found_raises`, `::test_dead_state_error_when_not_alive`, `::test_dead_raises_context_locked_when_impl_lock_held` |
| **lease** | `test_lock_steal.py::test_steal_stale_record_returns_true_with_new_session`, `test_lease_pid_liveness.py::test_acquire_ttl_stale_dead_holder_takes_over`; live holder protected: `::test_acquire_ttl_stale_alive_holder_blocks_no_takeover` | `test_lease_stale.py::test_row2_missing_fields_is_stale`, `::test_row3_corrupt_heartbeat_is_stale`, `::test_row1_none_is_stale` | `test_lease_pid_liveness.py::test_is_stale_ttl_expired_no_probe_is_stale_fallback`, `::test_is_stale_probe_raises_falls_back_to_ttl`; `test_lock_steal.py::test_steal_absent_record_creates_new` |
| **session_identity** | `test_session_identity.py::test_iter_ptr_files_empty_when_dir_absent`, `::test_coherence_absent_sources_are_not_a_violation` | `::test_session_record_fail_soft_on_corrupt_json`, `::test_read_session_invalid_id_returns_none`, `::test_path_validation_rejects_traversal` (CWE-22) | `::test_coherence_absent_sources_are_not_a_violation` (absent ptr/record is fail-soft, not an error) |
| **public install/stage/doctor** | `test_install_prune.py::test_copy_tree_prunes_orphan` (+ nested / opencode variants) | `test_public_assets.py::test_agent_missing_name_skipped`, `::test_invalid_agent_names_raise` | `test_doctor_projected_drift.py::test_cli_exits_nonzero_on_missing`, `::test_cli_exits_nonzero_on_drift` |
| **panel** | `test_service.py::test_empty_registry_returns_no_groups`, `::test_no_active_context_returns_empty_contexts` | `test_api_agent_prompt.py::test_invalid_id_chars_returns_400`, `::test_double_dot_traversal_returns_400`, `::test_symlink_traversal_returns_400` | `test_api_agent_prompt.py::test_missing_agent_returns_404`, `::test_no_agents_dir_raises` |
| **memory catalog** | `test_catalog.py::test_empty_product_dir_produces_empty_features` (no atoms → empty, valid envelope) | `integration/scripts/test_generate_memory_catalog.py::test_missing_required_field_returns_error`, `::test_subprocess_missing_field_exits_one` | `integration/scripts/test_generate_memory_catalog.py::test_empty_product_dir_returns_empty_catalog` (absent product dir → empty, no crash) |
| **ci_preflight** | `test_service.py::test_fail_fast_stops_at_first_failure`, `::test_all_passed_is_false_for_empty` (empty check set) | `test_service.py::test_checks_for_quick_swaps_in_no_e2e_pytest` (guards a forbidden quick-swap) | `test_service.py::test_subprocess_runner_missing_binary_returns_127_not_traceback` (poetry/binary absent → clean 127) |
| **telemetry** | `test_reader_claude.py::test_empty_file_noop`, `::test_missing_file_returns_empty` (no usage log → empty) | `test_reader_claude.py::test_malformed_line_skipped`, `::test_malformed_line_does_not_stop_reader`; `test_allowlist.py::test_missing_required_keys_returns_none` | `test_pricing.py::test_no_applicable_row_before_effective_from`, `::test_missing_usage_keys_default_to_zero` (absent pricing row / usage keys → safe default) |

No `GAP` rows: every named feature has at least one real test on each of the three
asymmetric paths. If a future feature lands without one of these legs, add its row here with
an explicit `GAP` marker in the missing cell rather than omitting the feature.
