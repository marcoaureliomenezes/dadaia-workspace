"""The scan-test vacuity-guard CONVENTION (v0.4.5 FR5, ``scan-test-vacuity-guard``).

Deliberately NOT a shared harness or base class — the v0.4.4 S5-FR23 ruling evaluated
"one scan harness, N rules" and REJECTED it as premature abstraction on evidence (zero
registered bugs trace to walker duplication across the census below; the detectors are
rule-specific by nature and a harness would couple N independent ratchets to one
framework — see ``specs/_archive/releases/v0.4.4/reviews/S5-FR23-first-firing-ruling.md``,
"One scan harness, N rules"). This module is a two-line CONVENTION every tree-walking
source-scan test applies **at its own call site**: assert the enumerated population is
non-empty, and assert one known sentinel member is present in it. A future mis-rooted
walker (a file moved one directory deeper, a ``.parents[N]`` off by one) then fails
LOUDLY, at the point of collection, instead of scanning zero files and passing
vacuously green forever — the exact false-confidence class the v0.4.4 ruling verified
live in three files (``test_frozen_clock_aging_ratchet.py``,
``test_harness_env_contract.py``, ``test_core_file_io_purity.py``).

Census (T-045-17, produced by scan over ``tests/**`` at v0.4.5 S2 HEAD; the raw scan
transcript is captured at
``.dadaia/tmp/software-engineer/20260825/T-045-17-census.txt``). The v0.4.4 ruling
counted 15 tree-/package-walking + single-module source-scan tests at ITS HEAD
(``specs/_archive/releases/v0.4.4/reviews/S5-FR23-first-firing-ruling.md`` check (b)).
Landing FR5 last inside S2 — after FR2 (T-045-14), FR3 (T-045-15) and FR4 (T-045-16),
per the TASKS.md sequencing — means the population this task guards is that same 15
PLUS the new scan-shaped tests those three FRs themselves introduced (the atomic-write
census, the two byte-golden-roster consumers, the three skill-inventory-oracle
consumers) and two pre-existing scans the original ruling's grep pass did not enumerate
(the self-scan, which discovers its tracked-file population via ``git ls-files`` rather
than ``rglob``/``glob``; the public-source hygiene directory listing). The honest
current count is 20 files / 21 call sites — a measured, not estimated, deviation from
the SPEC text's "~15", which quotes the pre-S2 backlog finding verbatim (SPEC v0.4.5
§3, FR5 body).

Tree-/package-walking population scans (the convention applies at the call site named):

* ``tests/contract/test_frozen_clock_aging_ratchet.py`` ::
  test_no_file_combines_a_frozen_datetime_constant_with_a_real_clock_call
* ``tests/contract/test_harness_env_contract.py`` :: ``_iter_test_files()``
* ``tests/unit/helpers/test_no_local_helper_copies.py`` :: ``_test_files()``
* ``tests/contract/test_core_file_io_purity.py`` ::
  test_core_file_io_purity_ratchet_and_authorized_set_grounded
* ``tests/contract/test_release_semver_canon.py`` :: ``_find_semver_compile_sites()``
* ``tests/contract/test_telemetry_connection_factory_allowlist.py`` :: ``_connect_sites()``
* ``tests/contract/test_session_store_ownership.py`` ::
  test_pointer_and_record_namespace_residue_is_owner_or_allowlisted_only
* ``tests/unit/public/test_no_gpt_only_claim.py`` :: test_no_surviving_gpt_only_claim
* ``tests/unit/features/panel/test_no_bearer_in_url.py`` ::
  test_no_credential_query_param_in_panel_or_cli_sources
* ``tests/contract/test_rules_skills_map.py`` :: ``_skills_on_disk()``
* ``tests/contract/test_public_scripts_thin_wrapper.py`` ::
  test_thin_wrapper_registry_stays_data_driven_and_correctly_scoped
* ``tests/contract/test_bind_resolution_seam_dynamic_walk.py`` ::
  test_no_resolver_driven_verb_hardcodes_the_dadaia_workspace_default
* ``tests/unit/core/test_atomic_write_census.py`` ::
  test_no_named_shim_or_inline_tmp_writer_survives_by_name (+ the sole-definition
  census, belt-and-suspenders)
* ``tests/integration/test_repo_self_scan.py`` ::
  test_no_hit_outside_the_shrink_only_baseline (already asserted non-empty; this task
  adds the sentinel half)
* ``tests/contract/test_public_source_hygiene.py`` ::
  test_pre_push_ci_gate_ships_pyproject_excludes_bytecode_and_scripts_leave_no_pycache
* ``tests/unit/infrastructure/test_install_target_goldens.py`` ::
  test_doctor_stage_lines_match_the_public_asset_roster
* ``tests/unit/infrastructure/test_public_assets_profile.py`` ::
  test_absent_profile_doctor_stage_lines_match_the_public_asset_roster
* ``tests/e2e/features/test_public_pipeline.py`` :: ``TestStage`` +
  ``TestInstallAll`` (two call sites, one per staged/installed skill-set comparison)
* ``tests/integration/test_public_assets.py`` ::
  test_stage_manifest_codex_adapters_and_install_all

Deliberately EXCLUDED:

* ``tests/unit/features/chokepoints/test_denylist_scan.py`` ::
  test_no_allowlist_or_sanctioned_terms_constant_in_matcher_source — reads
  ``Path(module.__file__)`` after a successful ``import``; a broken path fails the
  import, not the scan.
* ``tests/contract/test_telemetry_chmod_source_guard.py`` ::
  test_every_os_chmod_is_posix_guarded_and_at_least_one_exists — reads one hardcoded
  ``_SERVICE`` path directly (``.read_text()`` raises ``FileNotFoundError`` if
  mis-rooted) and already asserts ``visitor.total >= 1`` (a non-empty check on the
  found call sites, pre-existing).
* ``tests/unit/core/test_kernel_tunables.py`` :: every case —
  ``importlib.import_module(dotted)`` on a fixed, parametrized dotted path; a
  mis-rooted/renamed module fails the import, never scans zero files silently.
* ``tests/scripts/check_skill_orphans.py`` :: ``_all_skills()`` — its ``skills_dir``
  parameter is CALLER-CONTROLLED (``DADAIA_WORKSPACE_ROOT``), and its own dedicated
  suite (``tests/integration/scripts/test_check_skill_orphans.py``) legitimately drives
  it against tiny SYNTHETIC scratch trees (``__wired_skill``/``__orphan_skill``) to
  test the checker's reachability logic in isolation. A fixed real-skill sentinel
  would break that by-design scratch usage — caught live: applying it here turned
  ``test_orphan_detected_then_wired_exits_clean`` and
  ``test_disable_model_invocation_skill_is_never_flagged_an_orphan`` RED for the wrong
  reason (a missing sentinel in a deliberately-synthetic fixture tree, not a real
  mis-rooted walker). The real-tree invocation is instead guarded by this module's own
  ``tests/integration/test_public_assets.py`` call site above (always the real,
  unparameterized ``skill_names()``) and by
  ``test_real_repo_orphans_match_known_exemption_or_none``'s exemption-set equality
  failing loudly on an empty/broken real tree.
"""

from __future__ import annotations

from collections.abc import Collection


def assert_populated[T](population: Collection[T], sentinel: T) -> None:
    assert population, "scan found nothing — mis-rooted walker?"
    assert sentinel in population, f"sentinel {sentinel!r} missing from the scanned population"
