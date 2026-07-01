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

## Lifecycle-asymmetry coverage map

This map discharges the "Lifecycle-asymmetry coverage" policy above for **every**
subpackage of `dadaia_workspace/features/`. Each row records where the three asymmetric
paths (**delete/orphan**, **dirty input**, **missing dependency**) are actually covered,
grounded in real test names (grep-verified, not aspirational). A `GAP` marks an honest,
unaddressed asymmetric path; the map — not a retroactive test — is the deliverable, so a
`GAP` is documented rather than papered over.

The **Subpackage** column names the `features/` package this row covers as an inline
code span. `tests/contract/test_lifecycle_asymmetry_map.py` enumerates the live
subpackages at test time and fails if any subpackage is absent from this column — so the
map can never silently fall behind the code. When you add a `features/` subpackage, add
its row here in the same change (real coverage or an explicit `GAP` cell).

| Subpackage | Delete / orphan | Dirty input | Missing dependency |
|---|---|---|---|
| `spec_context` (lifecycle: `dead`/clean-tree) | `unit/test_spec_context_service.py::test_dead_removes_repo_and_marks_dead`, `::test_dead_clean_tree_unchanged_no_untracked`; residue `contract/test_session_bound_context_residue.py` | `unit/test_spec_context_service.py::test_dead_with_commit_blocks_on_planted_secret` / `_private_ip` / `_untracked_pem_key_file`, `::test_dead_refuses_on_untracked_files_without_commit` | `unit/test_spec_context_service.py::test_dead_not_found_raises`, `::test_dead_state_error_when_not_alive`, `::test_dead_raises_context_locked_when_impl_lock_held` |
| `spec_context` (lease) | `test_lock_steal.py::test_steal_stale_record_returns_true_with_new_session`, `test_lease_pid_liveness.py::test_acquire_ttl_stale_dead_holder_takes_over`; live holder protected: `::test_acquire_ttl_stale_alive_holder_blocks_no_takeover` | `test_lease_stale.py::test_row2_missing_fields_is_stale`, `::test_row3_corrupt_heartbeat_is_stale`, `::test_row1_none_is_stale` | `test_lease_pid_liveness.py::test_is_stale_ttl_expired_no_probe_is_stale_fallback`, `::test_is_stale_probe_raises_falls_back_to_ttl`; `test_lock_steal.py::test_steal_absent_record_creates_new` |
| `spec_context` (session_identity) | `test_session_identity.py::test_iter_ptr_files_empty_when_dir_absent`, `::test_coherence_absent_sources_are_not_a_violation` | `::test_session_record_fail_soft_on_corrupt_json`, `::test_read_session_invalid_id_returns_none`, `::test_path_validation_rejects_traversal` (CWE-22) | `::test_coherence_absent_sources_are_not_a_violation` (absent ptr/record is fail-soft, not an error) |
| `public` (install/stage/doctor) | `test_install_prune.py::test_copy_tree_prunes_orphan` (+ nested variants) | `test_public_assets.py::test_agent_missing_name_skipped`, `::test_invalid_agent_names_raise` | `test_doctor_projected_drift.py::test_cli_exits_nonzero_on_missing`, `::test_cli_exits_nonzero_on_drift` |
| `panel` | `unit/features/panel/test_service.py::test_empty_registry_returns_no_groups`, `::test_no_active_context_returns_empty_contexts` | `test_api_agent_prompt.py::test_invalid_id_chars_returns_400`, `::test_double_dot_traversal_returns_400`, `::test_symlink_traversal_returns_400` | `test_api_agent_prompt.py::test_missing_agent_returns_404`, `::test_no_agents_dir_raises` |
| `specs` (catalog + doctor + scaffolder) | `test_catalog.py::test_empty_product_dir_produces_empty_features` (no atoms → empty, valid envelope) | `test_doctor.py::test_backlog_malformed_bullet_warns`, `::test_active_md_empty_release_value_is_error`; `test_scaffolder.py::test_hotfix_scaffold_rejects_invalid_semver` | `test_doctor.py::test_missing_constitution_reports_doc_001`, `::test_missing_active_md_reports_doc_003`, `::test_missing_plan_in_active_release_reports_doc_004` |
| `ci_preflight` | `test_service.py::test_fail_fast_stops_at_first_failure`, `::test_all_passed_is_false_for_empty` (empty check set) | `test_service.py::test_checks_for_quick_swaps_in_no_e2e_pytest` (guards a forbidden quick-swap) | `test_service.py::test_subprocess_runner_missing_binary_returns_127_not_traceback` (poetry/binary absent → clean 127) |
| `lifecycle` | `test_hygiene_service.py::test_status_counts_orphan_and_malformed_handoffs`, `test_run_store.py::test_resume_is_idempotent_and_does_not_rewrite_state`, `test_state_machine.py::test_rejects_illegal_transition_without_mutating_run` | `test_run_store.py::test_refuses_to_create_dadaia_inside_repo_root`, `test_gates.py::test_rejects_malformed_handoff`, `test_prompt_builder.py::test_rejects_whole_workspace_or_escaping_paths` | `test_preflight_service.py::test_preflight_failures_return_typed_blocked_state`, `test_gates.py::test_rejects_wrong_semantic_fields_without_substring_matching`, `test_agent_runtime_fake.py::test_agent_says_approved_without_artifact_evidence_does_not_pass_gate` |
| `telemetry` | `test_reader_claude.py::test_empty_file_noop`, `::test_missing_file_returns_empty` (no usage log → empty) | `test_reader_claude.py::test_malformed_line_skipped`, `::test_malformed_line_does_not_stop_reader`; `test_allowlist.py::test_missing_required_keys_returns_none` | `test_pricing.py::test_no_applicable_row_before_effective_from`, `::test_missing_usage_keys_default_to_zero` (absent pricing row / usage keys → safe default) |
| `academy` | `unit/test_academy_service.py::test_delete_removes_course` | `::test_create_invalid_module_raises`, `::test_create_duplicate_raises` | `::test_delete_not_found_raises` |
| `agents` | `unit/features/agents/test_reader.py::test_raw_to_dto_missing_name_returns_empty_agent_list`, `::test_returns_empty_list_when_no_dir_found` | `::test_malformed_frontmatter_skipped`, `::test_missing_frontmatter_skipped`, `::test_get_prompt_symlink_escape_raises_invalid` (CWE-22) | `::test_get_prompt_no_agents_dir_raises`, `::test_get_prompt_agent_not_found_raises`, `::test_claude_branch_used_when_agentic_missing` |
| `export` | `unit/test_export_service.py::test_resolve_includes_drops_dotenv_files` (secret files excluded from the archive) | `::test_resolve_includes_skips_missing_paths` (declared include path absent → skipped, no crash) | GAP — no test for `git_ops`/branch-metadata source unavailable during `refresh_branches`/`build_manifest`; the happy paths (`test_build_manifest_records_branch`, `::test_refresh_branches_updates_current_branch`) assume git ops succeed |
| `import_` | `unit/test_import_service.py::test_extract_skips_env_files`, `::test_patch_json_paths_skips_missing_files` (orphan/absent referenced files skipped) | `::test_validate_rejects_archive_without_manifest`, `::test_validate_raises_on_wrong_extension`, `::test_validate_raises_on_missing_required_field` | `::test_validate_raises_when_archive_missing`, `::test_bootstrap_raises_runtime_error_on_nonzero_exit` |
| `migrate` | `unit/features/migrate/test_state_v2.py::test_execute_migration_deletes_primary_context_json` (legacy state file removed) | `::test_plan_migration_unknown_version_raises`; `test_specs_evolution.py::test_plan_rejects_downgrade` | `test_specs_evolution.py::test_absent_constitution_is_version_zero`, `test_tree_v2.py::test_idempotent_when_root_spec_absent`, `test_tree_v2.py::test_no_foundation_skips_step_1` |
| `orchestration` | `unit/test_orchestration_service.py::test_resume_failed_run_resets_failed_stages` (failed stages cleared on resume) | `unit/test_orchestration_runner.py::test_resolve_raises_on_unknown_binding_kind`, `::test_stage_by_id_raises_on_missing` | `test_orchestration_service.py::test_unknown_workflow_raises`, `::test_must_include_validation_fails_stage_when_file_missing`, `test_orchestration_runner.py::test_resolve_raises_on_missing_workflow_input` / `::test_resolve_raises_on_missing_stage_output` |
| `reports_next` | GAP — `reports_next` is a read-only resolver (computes the next report path from ACTIVE/PLAN); it creates/deletes no entity, so the delete/orphan leg is not applicable | `unit/features/reports_next/test_service.py::test_plan_without_owners_raises` (malformed PLAN body) | `::test_missing_active_md_raises`, `::test_release_none_raises`, `::test_missing_plan_raises` |
| `reports_retention` | `unit/features/reports_retention/test_service.py::test_cleanup_deletes_report_and_handoffs`, `::test_old_orphan_handoff_is_cleanup_candidate`; contract `test_reports_retention_cleanup.py::test_cleanup_contract_does_not_delete_external_symlink_target` | `test_service.py::test_malformed_state_is_reported`; contract `::test_cleanup_contract_preserves_important_malformed_handoff` | `test_service.py::test_cleanup_dry_run_does_not_delete` (no-op when nothing to collect); contract `::test_cleanup_contract_preserves_important_orphan_handoff` (orphan handoff with no report retained) |
| `reports_validation` | `unit/test_reports_validation_service.py::test_check_hash_returns_missing_artifact` (handoff references a deleted/orphaned artifact) | `::test_validate_file_malformed_json`, `::test_validate_file_marks_hash_mismatch_invalid`, `::test_check_hash_rejects_artifact_path_outside_workspace` (CWE-22) | `::test_check_hash_returns_missing_artifact` (referenced artifact file absent) |
| `repos` | `unit/test_repos_service.py::test_list_known_returns_empty_when_catalog_absent` (no catalog → empty, no crash) | GAP — no test feeds a malformed `repos.xlsx`/catalog row; reader assumes well-formed catalog cells | `::test_list_known_returns_empty_when_catalog_absent` (catalog file absent → empty) |
| `server_registry` | `unit/test_server_registry_service.py::test_release_removes_entry`, `::test_clean_removes_stale_pid_entries`, `::test_list_entries_marks_dead_pid_as_stale` | `infrastructure/test_json_server_registry_store_resilience.py::test_invalid_json_returns_empty_registry_and_logs_warning`, `::test_missing_required_key_skips_entry_keeps_valid_ones`, `::test_wrong_type_for_port_skips_entry` | `unit/features/server_registry/test_scan.py::test_scan_returns_empty_when_ss_unavailable` (`ss` binary absent → empty scan); `test_server_registry_service.py::test_release_nonexistent_port_raises` |
| `spec_artifacts` | GAP — `spec_artifacts` only creates SDD/memory artifacts; it has no delete/orphan path (deletion of releases/bugs is out of scope, handled by archive/`git mv`) | `unit/features/spec_artifacts/test_new_artifacts.py::test_invalid_slug_uppercase_raises_value_error`, `::test_invalid_slug_spaces_raises_value_error`; `test_memory_product_add.py::test_memory_product_add_rejects_invalid_slug` | `test_new_artifacts.py::test_creates_releases_dir_if_missing`, `::test_existing_dir_raises_file_exists_error`, `::test_creates_bugs_dir_if_missing` (parent dir absent → created; collision → raises) |
| `workflows` | GAP — workflow definitions are read-only assets loaded from disk; the service neither deletes nor orphans them (`test_dag.py::test_cyclic_stages_render_without_exception` proves a degenerate/cyclic DAG still renders safely) | `unit/features/workflows/test_service.py::test_malformed_workflow_yaml_raises`, `::test_empty_workflow_file_raises`; `test_dag.py::test_stage_id_xss_is_escaped`, `::test_agent_name_xss_is_escaped` | `test_service.py::test_list_returns_empty_when_no_dir`, `::test_claude_workflows_dir_used_when_agentic_missing` |
| `workspace` | GAP — `WorkspaceService.init` is create-only/idempotent (`test_workspace_service.py::test_init_is_idempotent`); it has no delete path | GAP — no malformed-input path: `init` consumes no external file content, only creates a fixed directory/state skeleton | `test_workspace_service.py::test_init_creates_dadaia_dirs`, `::test_is_initialized_false_before_init` (absent workspace state → init creates it / reports uninitialized) |
| `workspace_clean` | `unit/features/workspace_clean/test_clean_service.py::test_real_delete_removes_stale_tmp_file`, `::test_real_delete_removes_stale_reports_file` (stale/orphan artifacts collected) | `::test_never_deletes_outside_dadaia`, `::test_operator_file_in_exception_list_not_deleted` (hostile/operator-protected paths refused) | GAP — clean treats an absent target dir as nothing-to-do; not covered by a dedicated named test (subsumed by the no-candidates path) |
| `chokepoints` | `unit/features/chokepoints/test_push_gate_decision.py::test_branch_deletion_passes_without_verdict` (a deleted/zero-sha ref is never review-gated); `test_pre_commit_decision.py::test_no_lease_allows`, `::test_stale_dead_lease_allows` (orphaned/dead lease record → commit flows) | `test_push_gate_decision.py::test_malformed_handoff_skipped`, `::test_scope_field_is_not_a_fallback`, `::test_stale_sha_approve_blocks` (malformed/mis-keyed handoff input rejected) | `test_push_gate_decision.py::test_no_approve_blocks_and_lists_what_was_found`, `::test_empty_stdin_no_refs_passes`; `test_pre_commit_decision.py::test_none_context_allows` (path not a Spec Context repo → allow) |
| `ai_surface` (read-only doctor: scans the dehydrated AI surface for reintroduced lifecycle ritual) | GAP — `ai_surface` is a read-only doctor scanner; it creates/deletes no entity, so the delete/orphan leg is not applicable | `unit/features/ai_surface/test_ai_surface_doctor.py::test_unbannered_agents_md_with_hard_stop_fails`, `::test_unbannered_skill_with_numbered_reserve_fails`, `::test_banner_does_not_exempt_dehydrated_agents_md` (planted ritual / banner-laundering rejected) | `test_ai_surface_doctor.py::test_missing_public_dir_returns_empty`, `::test_marker_legend_is_not_flagged`, `::test_descriptive_pointer_is_not_flagged` (absent public dir → empty; legend/pointer not a false positive) |
| `backlog` (subject_registry + classifier + ledger + doctor; the v0.1.25 R1 backlog-consistency engine) | GAP — the `backlog` modules are read-only over the live tree (registry/classifier/doctor/ledger create and delete no entity; removal-on-consume is R2 and bound by the never-delete law), so the delete/orphan leg is not applicable | `unit/test_backlog_subject_registry.py::test_code_anchor_unresolved_symbol_halts`, `::test_panel_without_alias_halts`; `unit/test_backlog_models.py::test_code_ref_rejects_absolute_path`, `::test_parse_intents_rejects_unknown_kind`; `integration/test_backlog_doctor.py::test_each_violation_is_flagged` (planted BL-SCHEMA/DUP/CONFLICT/STALE rejected) | `unit/test_backlog_subject_registry.py::test_absent_alias_map_tolerated`, `unit/test_backlog_ledger.py::test_absent_archive_root_is_noop`, `integration/test_backlog_doctor.py::test_stale_noop_when_no_ledger` (absent alias map / archive ledger → no-op, never a false ERROR) |
| `bugs` (append-only JSONL event store; v0.1.46) | GAP — the `bugs` store is append-only; it has no delete/orphan path (`archived` is a `git mv` of the source `.md`, not a store mutation), so the delete/orphan leg is not applicable | `unit/features/bugs/test_jsonl_bug_store.py::test_iter_events_skips_malformed_lines` (corrupt JSONL line tolerated), `::test_from_dict_rejects_missing_required_field` (malformed event rejected) | `::test_status_folds_open_and_terminal`, `::test_stats_aggregates_by_status_and_severity` (fold over an empty/partial stream → no crash) |
| `migrate` (bugs `*.md`→JSONL one-time migration; v0.1.46) | `unit/features/migrate/test_bugs_jsonl.py::test_all_sources_moved_to_archive` (each source `.md` moved to `_archive/`, none left loose/orphaned) | `::test_closed_without_release_uses_unknown_sentinel_and_warns` (a `.md` missing its release → `unknown` sentinel + WARN, not a crash) | `::test_rerun_is_noop`, `::test_dry_run_writes_and_moves_nothing_but_plans` (already-migrated / dry-run → no-op) |

`GAP` cells above are honest, justified absences (read-only resolvers with no
entity to delete, create-only services with no malformed-input surface, or a not-yet-
written leg with a one-line reason) — not omissions. If a future change closes a gap,
replace the `GAP` cell with the real test name in the same change.
