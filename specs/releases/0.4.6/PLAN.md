# PLAN — Release: 0.4.6

**Status:** Em revisão
**Release ID:** 0.4.6
**Owner:** product-engineer

---

## Candidate 4 — workspace instance compliance: one zone registry, one doctor

### Method

1. **Record before views.** The registry and its three ratchets land first and alone (FR1+FR2);
   every later task derives a view from it or deletes a hand copy of it.
2. **Expand, switch, contract.** The doctor absorbs the four engines (FR3+FR4) before any engine
   is deleted; consumers switch to the registry before the lists die; each demolition is one
   green commit.
3. **Delete, never quarantine.** The dry `dadaia doctor` listing is the safety step; `--fix` is
   the deletion; no mover, no legacy set, no manifest of moved files.
4. **One writer per record.** `harness_profile.json` gets one store writer; `spec-contexts.json`
   one export writer; the exceptions file one migration inside `fix()`.
5. **Law after mechanism.** `ai-engineer` rewrites `DADAIA.md`, the zone fragments and the skills
   only once the code they describe exists (FR16 blocked by FR9-FR14).
6. **Memory in its phase.** The atom, the decider row, the P-11 wording and the catalog land in
   the CLOSURE pass (FR17).
7. **Validate on this instance.** The candidate is done when `dadaia doctor` on the live
   workspace reads 100% after `--fix`, then projection, `public doctor` and `specs doctor` agree.

### Module map (architect A-B)

| Module | Role after the candidate | Grows / deletes |
|---|---|---|
| `core/workspace_layout.py` | the one home of root law + `.dadaia` layout: `ZoneClass`, `Creator`, `Zone`, `DADAIA_ZONES`, `STATES_CANON`, `DADAIA_ROOT_FILES`, `INSTANCE_EXCEPTIONS`, `parse_exception_globs`, derived views | +60; -39 (two tuples) |
| `features/spec_context/doctor.py` | `_scan_zones()` -> `Finding(code, path, verdict, fixable, detail)`; `fix()` consumes the same list in the fixed order | +140; -240 (ROOT-1..4, RETIRED-LOCK, EFF-1, globs) |
| `cli/commands/doctor.py` | `--fix`, `--expired-only`, `--json`, `--quiet`, the score line, exit code | +30 |
| `infrastructure/public_assets.py` | `stage` renders the zone table and the states canon table into the two fragments | +25; -21 hand rows |
| `infrastructure/projection_rules.py` | harness-dir predicate `foreign_entries(workspace_root, profile)` (moved from `public doctor`); `_scripts_tree_rules` gone | +0 net; -9 |
| `infrastructure/json_harness_profile_store.py` | `write` — the one profile writer (init + fix) | +15; -46 in `workspace/service.py` |
| `features/workspace/service.py` | init creates `creator is INIT` zones + canon seeds through the store | -15 lists, -40 writer, -4 academy |
| `features/export/service.py`, `features/import_/service.py` | JSON out via `atomic_write`; JSON in via the injected `JsonContextStore.save` | 193->60, 295->60; models 32->12, 32->10; cli 60->25, 89->35 |
| `hooks/pre_gate.py`, `hooks/sdd_post_gate.py` | latency and post-gate telemetry writers removed | -80 |
| harness runtime configs (Claude, Codex) | one SessionStart entry: `dadaia doctor --fix --expired-only --quiet` | +24 |
| `public/data/{dadaia,states}-AGENTS.md` | `<!-- zones -->` / canon placeholders, rendered at stage | -21 |

- Seam placement: the registry is data plus pure parse — `core` stays I/O-free (P-11 set
  unchanged at eight); `doctor` consumes `core` + `infrastructure` only (P-07); hooks import
  nothing new and SessionStart is a CLI process (P-12); `infrastructure` imports `core` only for
  the table render (P-05).
- Deletion test on a new `core/zones.py`: a second home for the same fact family, imported next
  to `workspace_layout` by every consumer — pass-through; rejected. Extend the existing leaf.

### Deletion ledger (architect C) — net -8,165 lines (-4,755 Python)

| Block | What leaves | Lines |
|---|---|---|
| workspace_clean | `features/workspace_clean/**`, `cli/commands/clean.py`, `main.py` wiring | 241 |
| tmp_gc | `features/tmp_gc/**`, `cli/commands/tmp.py`, `main.py` wiring | 339 |
| reports retention + verbs | `features/reports/{retention,next}.py`, `__init__` exports, eight `cli/commands/reports.py` verbs, container builders | 913 |
| academy | `features/academy/**` (44 course files), CLI, `core/models/course.py`, `json_course_store.py`, container, panel views/api/css/js, routes, static, `core.js`, tab, init dir, export line | 4,397 |
| panel reports | `views/{reports,api_reports}.py`, `css/{reports,reports_doc}.py`, `js/reports.js`, routes, static, `core.js`, tab, `reports-AGENTS.md`, projection row, behavior-map entry | 1,188 |
| logs | `pre_gate._append_latency` + tail, `sdd_post_gate` three writers, `jsonl_log_rotation.py`, `LOG_ROTATION_MAX_BYTES` | 263 |
| legacy quarantine | `migrate/legacy_dadaia_dirs.py`, reconcile call, setup.cfg ignore edge | 89 |
| hygiene | `core/models/hygiene.py` | 148 |
| scripts projection | `_scripts_tree_rules` + call | 9 |
| export/import tar | service, model and CLI shrink; `patch_state`, `extract`, runner use | 496 |
| canon lists | `DADAIA_ALLOWED_SUBDIRS`, `DADAIA_ADDITIVE_PREFIXES`, `_DADAIA_*_DIRS` | 54 |
| doctor ROOT/EFF/RETIRED | `_check_root_1..4`, `_check_retired_lock_state`, `_check_efficiency_audit`, globs | 240 |
| init profile writer | `_write_harness_profile`, `_persisted_profile_harnesses` -> 6 store-call lines | 40 |
| `dadaia-AGENTS.md` table | 18 hand rows + 3 stale prose lines | 21 |
| **removed** | | **8,438** |
| **added** | registry +60, walk +140, cli +30, store write +15, export/import bodies, table render +25, migration +12, SessionStart +24 | **~345** |

- Net-positive sub-parts, justified: table render +25 vs -21 (buys the ratchet that makes
  "documented but not allowed" unrepresentable — two of the six bugs); SessionStart +24 vs 0
  (nothing was wired; without it 98% of tmp keeps violating its TTL); store `write` +15 paired
  with -46 (one writer instead of an inline copy).
- `legacy_dadaia_dirs.py` does not survive: its set is "not in the registry" = `WS-dadaia-slop`;
  its quarantine produced bug dadaia-reconcile-quarantines-sanctioned-references-clone; its edge
  drops the suppressed-edge cap 4 -> 3.
- Survives unchanged: `core/handoff_index.py`, `reports validate|doctor`, presence and session
  reapers, `public/data/{tmp,handoff,states}-AGENTS.md` bodies (states gains the rendered canon).

### Migration on the live instance (architect E) — `dadaia doctor --fix` is the migration

1. `dadaia doctor` (dry): the operator reads the `WS-dadaia-slop` lines for `reports/ academy/
   logs/ runs/ scripts/` and moves any wanted HTML under `repos/<slug>/reports/` by hand.
2. `dadaia doctor --fix`: presence gc -> session reap -> `root_exceptions.txt` ->
   `instance_exceptions.txt` (deduplicated: `.mcp.json` x3 -> 1, `z_img/`+`z_img` -> `z_img`)
   -> `harness_profile.json` regenerated from the projection dirs present -> expired deleted
   (5,599 tmp files, 224 handoffs, old mcps captures) -> slop deleted (retired zones, `states/`
   residue, `sessions/runtime/`, 8 wheels, kaykit packs).
3. `dadaia public stage && dadaia public install --target all && dadaia public doctor`:
   `.dadaia/AGENTS.md` rendered from the registry, no `.dadaia/scripts`, no `[foreign]` line.
4. `dadaia doctor` again: `compliance: N/N entries canonical (100%)`, exit 0.
5. Consumer workspaces: the same four steps on their next `dadaia doctor --fix`; the exceptions
   migration (12 lines) is deleted in the release after every consumer has run it.

### Test plan (architect F)

- **Deleted with their feature (16 files):** `test_clean_service.py`, `test_tmp_gc_service.py`,
  `test_tmp_gc_cmd.py`, `test_retention_service.py`, `test_reports_retention_cleanup.py`,
  `test_hygiene_models.py`, `test_jsonl_log_rotation.py`,
  `test_jsonl_log_rotation_concurrency.py`, `test_legacy_dadaia_dirs.py`,
  `test_academy_service.py`, `test_service_read_lesson.py`, `test_json_course_store.py`,
  `test_cli_academy.py`, `test_academy_route.py`, `test_api_academy.py`, `test_views_reports.py`.
- **Rewritten:** `test_spec_context_doctor_root.py` (WS codes, finding-verdict enum, score line,
  `--json`), `test_workspace_layout_single_authority.py` (registry object identity in doctor,
  gate_policy, public_assets), `test_root_whitelist.py` (exceptions file name),
  `test_pre_gate.py` + `test_post_gate_reconciler.py` (no logs assertions),
  `test_workspace_service.py` (INIT zones + canon seeds, no academy), `test_container.py`,
  `test_cli_export.py` (+ import round trip through the store), `test_reconcile_service.py` (no
  quarantine step), `test_dadaia_references_lifecycle_sanction.py` (OPERATOR never walked),
  `test_doctor_projected_drift.py` (no `[foreign]`).
- **Goldens:** panel `api_golden_v0155.json` + `test_api_golden.py`, `test_control_tokens.py`,
  `test_no_auth_contract.py`, `test_api_contract.py`; e2e `tab-navigation`, `response-guard`,
  `helpers.ts`; `test_install_target_goldens` + `public_asset_roster.py` (no `.dadaia/scripts`);
  `doctor_all_four_v0158.json`, `test_public_install_e2e.py`, `test_public_install_scope_flags.py`
  (no `[foreign]`; rendered `.dadaia/AGENTS.md` bytes).
- **Ratchets that move:** `test_import_linter_ignore_cap.py` cap 4 -> 3 and `modules =` minus
  three packages; `test_cli_help_quality._RATCHET` re-measured (13 leaves gone); V32 ceiling
  re-measured down; `test_frozen_clock_aging_ratchet` enumeration (tmp/clean tests gone);
  `test_behavior_map` (reports source removed); `test_doctor_memory` MEM-DRIFT-1 package map.
- **New ratchets** (`tests/contract/test_zone_registry.py`, `Intent: CONTRACT`): table equals
  registry; registry is the only `.dadaia` name list (AST walk, no `.dadaia/<retired>` literal);
  every creator exists.
- **RED tests per task** are named in `TASKS.md`; every new test declares `Intent:` and size at
  birth; no LARGE test is added, none demoted; no quarantine.

### Execution order and parallelism

1. T-046-24 registry + ratchets -> 2. T-046-25 doctor one scan (serial: the foundation).
3. Lane A (`software-engineer`, shared `container.py`/`cli/main.py`/panel files, serial):
   T-046-26 engines -> T-046-27 reports -> T-046-28 academy -> T-046-30 scripts ->
   T-046-31 export/import -> T-046-32 exceptions + profile + `.env`.
4. Lane B (parallel to lane A after T-046-25): T-046-29 logs (hooks + infrastructure only);
   T-046-33 table render + SessionStart (`public_assets.stage`, two fragments, runtime configs).
5. T-046-34 law + skills (`ai-engineer`) after T-046-27 and T-046-33.
6. T-046-35 memory + CLOSURE (`product-engineer`); T-046-36 live-instance QA run + reviews.
   Disjointness per pair is declared in `TASKS.md` §Parallelism.

### Bug-surface answer: reduced (architect G)

- Same file, same symptom family, six times in eight weeks; every resolution edited membership,
  none changed shape. A zone now enters only as `Zone(name, cls, creator, ttl, canon, purpose)`;
  init, doctor, gate, export and the table are views of one record; the table is rendered and
  pinned; a second name list fails an AST ratchet; a row without a live creator fails the build.
- Counts: engines 4 -> 1; canon lists 3 -> 1; TTL authorities 3 -> 1; exception readers 3 -> 2;
  suppressed edges 4 -> 3; zones 18 -> 11; CLI leaves -13; production net -8,165.
- Root-cause gate PASS (the bare list is what is replaced; no branch, flag or wrapper added to an
  existing path). Architecture-fidelity gate PASS (P-01/05/07/11/12 hold; one suppressed edge
  removed).

### Review gates

- **`software-architect` fidelity review** on the candidate head: module map above vs the diff;
  the deletion test on every added line; P-07/P-11/P-12 unchanged; verdict names whether any
  block deviated from sections A-E.
- **`code-reviewer` three-axis review** (`dd-code-review`): standards; spec (FR1-FR16 vs diff);
  bug surface citing the six ledger bugs by id and stating "reduced" with the counts above, or
  "increased" with the line that grew a feature.
- **`security-reviewer` push verdict** on the PR head sha (`DADAIA.md` §4.2): deletion lanes
  guarded by `resolve().relative_to(dadaia)`, symlinks never followed, `--quiet` leaks nothing
  into the model context, no secret material in `spec-contexts.json`, denylist scan green.
- **`qa-engineer`** closes the candidate on this instance: AC2-AC13 executed live, evidence
  captured under `.dadaia/tmp/qa-engineer/<date>/`, then the handoff.

### Technical risks and controls

- **Destructive `--fix` on the live instance.** Dry list first (step 1 of the migration); the
  operator ruled the deletion (D8); AG.1 lane guard kept once in the doctor.
- **Transient red between FR1 and the demolitions.** The instance doctor lists retired zones as
  slop while their code still exists; the dry default deletes nothing; CI runs the unit suite,
  not the live instance.
- **Behavior-map red mid-arc.** T-046-27 re-records its own row; T-046-33 and T-046-34 re-record
  the fragments they touch — never deferred.
- **SessionStart cost.** ~100 ms over 5k files, tens of files after the first fix; `--quiet`.
- **Consumer `[foreign]` readers.** None found outside the goldens; the harness-dir scan moves,
  its coverage does not shrink.
- **Exceptions migration lifetime.** 12 lines inside `fix()`, deleted next release; tracked in
  the closure `drifts` entry.

### Validation plan

- Per task: the ACs in its `Delivers:` line plus the local CI preflight (`ruff format --check`,
  `ruff check`, `mypy --strict`, `pytest`).
- Candidate close: AC3 on this instance (100%), `dadaia public doctor` `[ok]`, `dadaia specs
  doctor` 0 errors after the memory pass, `pytest` green with the zone-registry ratchets and
  the moved ratchets re-pinned, trio review answering "reduced" against the six-bug ledger,
  security verdict on the PR head.
