# TASKS — Release: 0.4.6

**Status:** Aprovado
**Release ID:** 0.4.6
**Owner:** product-engineer

---

## Candidate 4 — workspace instance compliance: one zone registry, one doctor

Write-set paths are relative to `dadaia_workspace/` unless they start with `tests/`,
`specs/` or `CONTEXT.md`; every new test declares `Intent:` and size at birth.

- [x] T-046-24 — FR1+FR2, the registry and its ratchets: `ZoneClass`, `Creator`, `Zone`,
  `DADAIA_ZONES` (11 rows), `STATES_CANON`, `DADAIA_ROOT_FILES`, `INSTANCE_EXCEPTIONS`,
  `parse_exception_globs`, derived views; the two tuples deleted; `gate_policy` derives its
  ADDITIVE prefixes; `CONTEXT.md` gains the four SPEC §3 terms. RED: `tests/contract/
  test_zone_registry.py` (three ratchets), rewritten `test_workspace_layout_single_authority.py`.
  Owner: software-engineer. Commit: `feat(T-046-24): zone registry in core with its ratchets`.
  Write set: core/workspace_layout.py, features/spec_context/gate_policy.py, CONTEXT.md,
  tests/contract/{test_zone_registry,test_workspace_layout_single_authority}.py, tests/unit/core/**.
  Blocked by: none. Delivers: one record answers "what may live in `.dadaia/`" — AC1.
- [x] T-046-25 — FR3+FR4 (scan half), the one doctor: `_scan_zones()`, `Finding`, the
  finding-verdict enum (inline in `doctor.py`), `fix()` order, `--fix --expired-only --json
  --quiet`, score line, exit code; `foreign_entries()` moved into infrastructure, `public
  doctor` keeps hash drift; ROOT-1..4 / RETIRED-LOCK-STATE / EFF-1 / globs deleted. RED:
  rewritten `test_spec_context_doctor_root.py` (WS codes, score, `--json`, expired-only stops
  before slop), `test_doctor_projected_drift.py`, `test_dadaia_references_lifecycle_sanction.py`.
  Owner: software-engineer. Commit: `feat(T-046-25): dadaia doctor is the one scan and reaper`.
  Write set: features/spec_context/doctor.py, cli/commands/doctor.py, infrastructure/
  {projection_rules,public_assets}.py (foreign scan only), tests/unit/test_spec_context_
  doctor_root.py, tests/unit/features/{spec_context,public_assets}/**, doctor goldens.
  Blocked by: T-046-24. Delivers: `dadaia doctor` on this instance lists every finding and a
  score line; `--fix --expired-only` deletes only expired — AC2, AC4, AC6.
- [ ] T-046-26 — FR4 (contract half), delete the engines: `features/{workspace_clean,tmp_gc}/`,
  `features/reports/{retention,next}.py`, `features/migrate/legacy_dadaia_dirs.py` + reconcile
  call + setup.cfg edge, `core/models/hygiene.py`, `cli/commands/{clean,tmp}.py`, eight `reports`
  verbs, container builders, their 7 tests; cap 4 -> 3, `modules =`, `_RATCHET`, frozen-clock
  enumeration re-pinned. RED: `test_import_linter_ignore_cap.py` at 3, `test_cli_help_quality`.
  Owner: software-engineer. Commit: `refactor(T-046-26): delete clean, tmp gc, retention, hygiene`.
  Write set: those packages/files, cli/main.py, cli/commands/reports.py, container.py,
  features/reconcile/service.py, setup.cfg, tests/contract/{test_import_linter_ignore_cap,
  test_cli_help_quality,test_frozen_clock_aging_ratchet}.py, the 7 deleted tests,
  tests/unit/features/reconcile/**, tests/unit/test_container.py.
  Blocked by: T-046-25. Delivers: one engine exists — AC4, AC10 (engines), AC15 (cap).
- [ ] T-046-27 — FR9, retire `reports/`: panel views/api/css/js, routes, static, `core.js`,
  tab; `public/data/reports-AGENTS.md`, its projection row and behavior-map row. RED: panel
  goldens + `test_api_contract.py` (no `/reports`), `test_behavior_map`, e2e `tab-navigation`.
  Owner: software-engineer. Commit: `refactor(T-046-27): retire the reports zone and panel tab`.
  Write set: features/panel/**, public/data/reports-AGENTS.md, infrastructure/
  projection_rules.py (that row), public/entities/behavior-map.json (that row),
  tests/unit/features/panel/**, tests/e2e/panel/**.
  Blocked by: T-046-26. Delivers: no reports route, no reports zone in the manifest — AC10.
- [ ] T-046-28 — FR10, retire academy: feature + courses, CLI, model, store, container, panel
  views/api/css/js, routes, static, `core.js`, tab, init dir, export line; 6 tests deleted.
  RED: panel goldens (no `/academy`), `test_workspace_service.py`, `test_doctor_memory` map.
  Owner: software-engineer. Commit: `refactor(T-046-28): retire academy`.
  Write set: features/academy/**, cli/commands/academy.py, cli/main.py, core/models/course.py,
  infrastructure/json_course_store.py, container.py, features/panel/**, features/workspace/
  service.py (academy lines), features/export/service.py (one line), their tests.
  Blocked by: T-046-27. Delivers: `dadaia --help` and the panel carry no academy — AC4, AC10.
- [-] T-046-29 — FR11, retire logs: `pre_gate._append_latency` + tail, `sdd_post_gate`
  writers, `jsonl_log_rotation.py`, `LOG_ROTATION_MAX_BYTES`; 2 tests deleted. RED:
  `test_pre_gate.py` / `test_post_gate_reconciler.py` assert no `.dadaia/logs` after a gated
  write; `test_hook_import_surface.py`. Owner: software-engineer.
  Commit: `refactor(T-046-29): retire hook telemetry writers and log rotation`.
  Write set: hooks/{pre_gate,sdd_post_gate}.py, infrastructure/jsonl_log_rotation.py,
  core/kernel_tunables.py, tests/unit/hooks/**, tests/unit/infrastructure/
  test_jsonl_log_rotation.py, tests/integration/infrastructure/**.
  Blocked by: T-046-25. Delivers: a gated write leaves no `logs/` — AC10 (logs).
- [ ] T-046-30 — FR12, stop the scripts projection: `_scripts_tree_rules` + call deleted;
  roster and install goldens without `.dadaia/scripts`. RED: `test_install_target_goldens`.
  Owner: software-engineer. Commit: `refactor(T-046-30): stop projecting .dadaia/scripts`.
  Write set: infrastructure/projection_rules.py, tests/helpers/public_asset_roster.py,
  tests/unit/infrastructure/test_install_target_goldens*.
  Blocked by: T-046-27. Delivers: `public install` creates no `.dadaia/scripts` — AC10.
- [ ] T-046-31 — FR13, export/import JSON: `ExportService.run` -> `_refresh_branches` +
  `atomic_write` of `spec-contexts.json`; `ImportService(store)` reads, saves DEAD, skips
  known, prints the alive step; models and CLIs shrunk; tar, `patch_state`, runner use gone.
  RED: `test_cli_export.py` round trip through the store; export-shape test. Owner:
  software-engineer. Commit: `refactor(T-046-31): export and import one spec-contexts.json`.
  Write set: features/{export,import_}/service.py, core/models/{export,import_}.py,
  cli/commands/{export,import_}.py, container.py (import builder), tests/integration/
  test_cli_export.py, tests/unit/features/{export,import_}/**.
  Blocked by: T-046-28. Delivers: export writes one file, import restores DEAD contexts — AC11.
- [ ] T-046-32 — FR6+FR7+FR8: exceptions migration inside `fix()`; hook `_operator_exception`
  reads `INSTANCE_EXCEPTIONS`; `json_harness_profile_store.write` (init + fix), inline init
  writer deleted; `.env` and `.gitignore` in `ROOT_ALLOWED_FILES`, inline case deleted; bug
  doctor-root1-flags-env-that-dadaia-md-9-declares-canonical resolved (`caused_by: none`).
  RED: `test_root_whitelist.py` (`.env` allowed, file name), `WS-states-missing` -> profile
  from present dirs, migration dedupe. Owner: software-engineer. Commit: `fix(bugs):
  doctor-root1-flags-env-that-dadaia-md-9-declares-canonical — root law from one whitelist
  (T-046-32)`. Write set: core/workspace_layout.py (ROOT_ALLOWED_FILES), hooks/pre_gate.py
  (reader), features/spec_context/doctor.py (fix steps), infrastructure/
  json_harness_profile_store.py, features/workspace/service.py (writer), specs/bugs/BUGS.jsonl,
  tests/unit/hooks/test_root_whitelist.py, tests/unit/test_spec_context_doctor_root.py.
  Blocked by: T-046-29, T-046-31. Delivers: `--fix` migrates the exceptions file and seeds the
  profile; `.env` is canon — AC7, AC8, AC9.
- [ ] T-046-33 — FR14 + SessionStart: `<!-- zones -->` and canon placeholders in
  `dadaia-AGENTS.md` / `states-AGENTS.md`, 18 hand rows deleted; `public_assets.stage` renders
  both tables; one SessionStart entry per harness in `runtime_config.py` running `dadaia doctor
  --fix --expired-only --quiet`. RED: `test_zone_registry` ratchet 1 on the rendered bytes;
  `test_public_install_e2e.py`; runtime-config test for the entry. Owner: software-engineer.
  Commit: `feat(T-046-33): render the zone table at stage; SessionStart runs the reaper`.
  Write set: infrastructure/{public_assets,runtime_config}.py, public/data/{dadaia,states}-
  AGENTS.md, public/entities/behavior-map.json (those two rows), tests/integration/
  test_public_install_e2e.py, tests/unit/infrastructure/**, doctor_all_four golden.
  Blocked by: T-046-25. Delivers: `.dadaia/AGENTS.md` carries 11 rendered rows and every new
  session reaps expired files — AC5, AC12.
- [ ] T-046-34 — FR16, law and skills: `DADAIA.md` §3.2/§5.2/§5.4/§8/§10; `dadaia-AGENTS.md`
  prose; every `public/` reports path -> `repos/<slug>/reports/`; `handoff-AGENTS.md` TTL;
  `RC-FLOW.md` step 8; `dd-workspace-doctor` rewritten; personas; `behavior-map.json` hashes;
  reprojection (`public stage && public install --target all && public doctor`). RED:
  `test_behavior_map`, AC13's grep. Owner: ai-engineer.
  Commit: `docs(T-046-34): one reports home, one doctor, one zone table in the law`.
  Write set: public/data/** (not the two rendered tables), public/skills/**, public/agents/**,
  public/templates/repo-AGENTS.md, public/scaffold/memory/AGENTS.md,
  public/entities/behavior-map.json, the reprojected instance law files.
  Blocked by: T-046-27, T-046-33. Delivers: the law names one reports home, one doctor — AC13.
- [ ] T-046-35 — FR17 + CLOSURE: `workspace-doctor` atom (finding codes and verdicts),
  `ARCHITECTURE.md` decider row + diagram, P-11 "six" -> "eight", `workspace-init`,
  `context-management`, `catalog.json` (MEMORY-UPDATE.md protocol); the closure narrative
  (`_RELEASE.json` log: summary, size, drifts, test-dispositions, artifact-gc via `dadaia
  doctor`, dispositions) follows T-046-36 as closure procedure, not a task.
  Owner: product-engineer. Commit: `docs(T-046-35): memory — candidate 4`.
  Write set: specs/memory/**, specs/releases/0.4.6/_RELEASE.json (phase only).
  Blocked by: T-046-32, T-046-34. Delivers: memory is current truth, `dadaia specs doctor` 0
  errors — AC14.
- [ ] T-046-36 — QA on this live instance, then reviews: `dadaia doctor` (dry, counts
  recorded) -> operator moves wanted reports -> `dadaia doctor --fix` -> reprojection ->
  `dadaia public doctor` -> `dadaia doctor` = 100% -> `dadaia specs doctor`; AC2-AC13 executed,
  evidence under `.dadaia/tmp/qa-engineer/<date>/`; then `software-architect` fidelity review,
  `code-reviewer` three-axis review (six bugs cited), `security-reviewer` verdict on the PR head.
  Owner: qa-engineer (run + handoff) with the trio. Commit: `test(T-046-36): live-instance
  compliance run — <N>/<N> canonical`. Write set: none in-repo (runtime `.dadaia/**`; handoffs;
  the verdict under `specs/releases/0.4.6/verdicts/`).
  Blocked by: T-046-35 (reviews run on the head that carries memory). Delivers: the instance
  reads 100%, the trio has verdicts — AC3, AC15.

## Parallelism

- Disjoint write sets (may hold `[-]` simultaneously): T-046-29 ‖ T-046-26/27/28/30/31;
  T-046-33 ‖ T-046-26/28/29/30/31; T-046-34 ‖ T-046-31/32.
- Serial: T-046-24 -> T-046-25 (foundation); lane A T-046-26 -> 27 -> 28 -> 30 -> 31 -> 32
  (shared `container.py`, `cli/main.py`, panel files, `workspace/service.py`); T-046-27 /
  T-046-33 / T-046-34 share `behavior-map.json`; every `Blocked by:` edge above.
- Regenerated outputs (`.dadaia/agentic/manifest.json`, instance projections) are outside the
  disjointness test — reprojection is idempotent and cumulative.
