# TASKS — Release: 0.4.7

**Status:** Aprovado
**Release ID:** 0.4.7
**Owner:** product-engineer

---

## Candidate 2 — the gate blocks three things

- [x] T-047-14 — FR2: `tests/contract/test_every_block_carries_a_fix.py` — enumerate
  every BLOCK path by public seam (root whitelist, venv guard, PROTECTED sessions/law,
  scope, `push_gate_decision` refusals, `ci verdict-check`, `release new`/`archive`/
  `rc-archive`, Doctor error-class rules), assert one `fix:` line, feed it through
  `pre_gate.evaluate_payload` as Bash and assert ALLOW. RED on today's tree. Write
  set: `tests/**`. Blocked by: none. Delivers: the operator reads the list of BLOCKs
  that stall today.
- [x] T-047-15 — FR1: `PathClass` = ADDITIVE/MUTATING/PROTECTED; delete MEMORY,
  LAW, UNGATED, `_MEMORY_WRITE_PHASES`, `release_state.MEMORY_WRITE_PHASES`, the
  READ block; `evaluate(rel_path, bind, target_slug, …)`; `core.invocation` resolves
  `Bind` (name + `all_repos()` slugs) and drops `release`/`phase`/`resolve_mode`
  (`resolve_active_release` moves to `SpecsTree` or dies); `fix:` on the root,
  PROTECTED and scope messages; gate tests rewritten without `_RELEASE.json`
  fixtures. Write set: `dadaia_workspace/hooks/**`, `dadaia_workspace/features/
  spec_context/gate_policy.py`, `dadaia_workspace/core/{invocation,release_state,
  session_store}.py`, `dadaia_workspace/features/specs/specs_tree.py`, `tests/**`.
  Blocked by: T-047-14. Delivers: bound to A, a write into `repos/B/` is refused with a
  runnable fix; a memory atom is writable in every phase.
- [x] T-047-16 — FR3 + FR4 (bug `context-bind-implementation-requires-release-id-
  stall-when-none-live`): delete `_cache_guard_reason` + helpers and their tests;
  `[tool.ruff] cache-dir`, `[tool.mypy] cache_dir` in `pyproject.toml`; preflight
  drops the per-command flags and `resolve_mypy_cache_dir`; `context bind <ctx>
  [--print-env]` only (`--mode/--release/--force/--reason` deleted, record loses
  `mode`/`release`); `test_no_pollution` proves bare commands. Write set:
  `dadaia_workspace/hooks/venv_guard.py`, `pyproject.toml`, `dadaia_workspace/features/
  ci_preflight/**`, `dadaia_workspace/cli/commands/context.py`, `dadaia_workspace/core/
  session_store.py`, `tests/**`. Blocked by: T-047-15. Delivers: the bug's repro exits
  0 with no live release; a bare `pytest` leaves no `.pytest_cache/`.
- [x] T-047-17 — FR5a: move the `CanonEntry` rows and add `REPO_TREE_EXCLUDED` to
  `core/workspace_layout.py`; `features/specs/canon.py` imports the rows and keeps
  render/check; `privacy_check._PUBLIC_ASSET_IGNORED_DIRS` and `pyproject` `exclude`
  derive; widen `test_zone_registry.py`'s ratchet to root names, specs members and the
  exclusion set (RED on today's hand-typed law). Write set: `dadaia_workspace/core/
  workspace_layout.py`, `dadaia_workspace/features/specs/canon.py`, `dadaia_workspace/
  infrastructure/privacy_check.py`, `tests/**`. Blocked by: none. Delivers: one module
  answers "what may exist" for root, `.dadaia/`, `specs/` and a repo tree.
- [x] T-047-18 — FR5b: `render_registry_tables` fills `<!-- root -->`,
  `<!-- repo-excluded -->`, `<!-- specs-canon -->` in `public/data/DADAIA.md`
  §5.1/§5.3/§6.2 at `public stage`; contract test: staged §6.2 table == registry rows.
  Write set: `dadaia_workspace/infrastructure/public_assets.py`, `dadaia_workspace/
  public/data/DADAIA.md`, `tests/**`. Blocked by: T-047-17. Delivers: the projected
  law's canon tables cannot drift from the registry.
- [x] T-047-19 — FR6a: `features/spec_context/sweep.py` — `walk`, `move`, `remove`
  behind one guard (symlink never followed, vanished = absent, outside workspace =
  skipped, OSError = one `skipped` action; cross-device move = copy+remove inside);
  `DoctorService.scan()`/`fix()` consume it; `_entries`, `_mtime`, `_remove`,
  `_guarded`, `_remove_dead_repo` deleted (RED: the guard matrix over the primitive).
  Write set: `dadaia_workspace/features/spec_context/{doctor,sweep}.py`, `tests/**`.
  Blocked by: T-047-17. Delivers: one walk serves scan and fix; the CRIT repro (bind,
  `doctor --fix`, `context show`) keeps the bind.
- [x] T-047-20 — FR6b: `reaped` zone row (7 d, Q3 path); slop and INV-5 leftovers
  moved to `reaped/<YYYYMMDD>/<rel-path>` with the clock at the move; deletion only by
  TTL; repo-top + `REPO_TREE_EXCLUDED`-at-depth + nested `.dadaia/` walk over every
  ALIVE repo set (pruned at `.git`, `.venv`, `node_modules`); `WS-reaped-reaped`
  lines; `--expired-only` becomes the reaper lane (seed, move, expire); SessionStart
  args unchanged in shape; `sdd_post_gate` calls the reaper on its throttle; `REPO-
  DADAIA-1` deleted. Write set: `dadaia_workspace/core/workspace_layout.py`,
  `dadaia_workspace/features/spec_context/**`, `dadaia_workspace/hooks/sdd_post_gate.py`,
  `dadaia_workspace/infrastructure/runtime_config.py`, `dadaia_workspace/cli/commands/
  doctor.py`, `dadaia_workspace/features/specs/{rules,doctor_structural}.py`,
  `tests/**`. Blocked by: T-047-19. Delivers: a `.pytest_cache/` under a repo is moved
  at the next throttled PostToolUse and expires a week later; nothing else moves.
- [x] T-047-21 — FR6c: `HOOKS-DRIFT-1` — every ALIVE repo's `.git/hooks/{pre-commit,
  pre-push}` compared byte-wise to `public/scripts/`; error class, `fix: … ci
  install-hook --force`; rendered in the workspace section. Write set:
  `dadaia_workspace/features/spec_context/doctor.py`, `tests/**`. Blocked by:
  T-047-20. Delivers: a stale installed hook is a finding with a runnable fix.
- [ ] T-047-22 — FR7: rewrite every fixture literal that `_TESTS_SCOPE_BASELINE` (23
  rows) and the path-scoped `privacy_baseline.json` `exclude_regex` rows tolerate to a
  synthetic value matching no pattern (or build it at runtime from parts); delete
  `_TESTS_SCOPE_BASELINE` and those rows; `test_repo_self_scan.py` asserts zero hits
  over the tracked tree with no tolerated-pairs list; the scan layers stay full on
  every path; gitleaks required on `develop` (recorded). Write set: `tests/**`,
  `dadaia_workspace/infrastructure/data/privacy_baseline.json`, `dadaia_workspace/
  features/chokepoints/**`, `.github/workflows/ci.yml`. Blocked by: T-047-14.
  Delivers: a synthetic fixture needs no row; a private hostname in `specs/**` or
  `tests/**` is refused at push like anywhere else.
- [ ] T-047-23 — FR8: DADAIA §3.1–§3.5/§5.1/§5.3/§6.2/§7.4/§8.2/§8.5/§10.2;
  `.dadaia/AGENTS.md`; `scaffold/memory/AGENTS.md`; `entities/registry.json`; skills
  `dd-ai-eng-knowhow`, `dd-task-manager`, `dd-cli-library`, `dd-spec-navigator`,
  `dd-workspace-doctor`, `dd-bug-registration`; `CONSUMER_VALIDATION_RECIPE.md`;
  `software-engineer.md`; `kimi-code/AGENTS.md`; behavior-map hashes; `CONTEXT.md`
  (Path class, Zone, Finding verdict, Bind; new Scope, Reaped, Publication boundary,
  Sweep); `public stage` → `install --target all` → `public doctor`; grep proves no
  retired term survives. Write set: `dadaia_workspace/public/**`, `CONTEXT.md`, the
  instance projections via the CLI, `tests/**`. Blocked by: T-047-16, T-047-18,
  T-047-21, T-047-22. Delivers: law, skills, entities and instance say one thing about
  the gate, the canon, the reaper and the scan.
- [ ] T-047-24 — FR9 closure: `CHANGELOG.md [0.4.7]` candidate 2, preflight, `dadaia doctor`
  100 %, gitleaks required on `develop` (PM/operator `gh api`, whole list re-supplied,
  recorded), `_RELEASE.json` CLOSURE with `summary`/`size`/`drifts`/`test-dispositions`/
  `dispositions`/`artifact-gc`/`reviews` entries; the memory pass (`sdd-gate-v3`,
  `context-management`, `workspace-doctor`, `workspace-init`, `spec-context-project`,
  `public-asset-distribution`, `ARCHITECTURE` Part 2 rows, `QUALITY`/`TECHSTACK` cache
  lines) is closure procedure (RC-FLOW step 5), never a task write set. Write set:
  `CHANGELOG.md`, `specs/releases/0.4.7/**`, `specs/backlog/**`, `specs/bugs/**`.
  Blocked by: T-047-23. Delivers: candidate 2 closed, ready for the `feature → develop`
  PR and the promote-or-continue gate.
