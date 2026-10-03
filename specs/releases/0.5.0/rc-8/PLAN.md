# PLAN — Release: 0.5.0

**Status:** Approved
**Release ID:** 0.5.0
**Owner:** dd-software-engineer

Candidate 8 — W8: the test law and the library pipeline leave; W9: bug lineage derived; W10: the open bugs (ADR 0140). SPEC AC8.1–AC8.10, AC9.1–AC9.5, AC10.1–AC10.13, Approved at 3f48e11dd and amended by operator ruling at 6ea03b0ff (AC8.9's second deletion list; AC8.10's P-07 and P-28 by their own tool; ADR 0176 edited at 6ec30315d). Paths are relative to `dadaia_workspace/` (`f/` = `features/`, `pub/` = `public/`, `S/` = `pub/skills/`) unless they start with `tests/`, `scripts/`, `specs/`, `docs/`, `.github/`, `README.md`, `AGENTS.md`, `CONTEXT.md`, `pyproject.toml`, `poetry.lock` or `setup.cfg`.
As-is read at `wt/0.5.0b-release` 6ec30315d; the G1 `<start>` readout equals the birth readout (8f4ed785f): 25,307 production lines / 1,233 test functions / 45,464 test lines / 0 guard lines / 0 guard checks.

## 1. As-is review

Bug history read (permanent architecture review), copied from the product engineer's handoff `2026-10-03T135506Z-dd-product-engineer-rc8-spec-rereview-2-applied`:
- Preflight fix chain: `ci-preflight-unusable-outside-the-source-repo` got a refusal (symptom patch), then `preflight-doctor-judges-instance-state-ci-never-sees`; `ci-preflight-writes-coverage-into-the-repo` is open. Cause: a verb serving only this repo; AC8.9 deletes it.
- `surface: tests`: 67 records, 14 naming a prior bug; F018: 22% fix-induced, many from meta-tests.
- 128 of 237 `fix(bugs):` commits, 2026-08-23..2026-10-02, remove an assert (`git log -E --grep='^fix\(bugs\): ' fb8a29a75`, each through `git show -U0 -- tests | grep -E '^-\s*assert'`). Cause: `dd-bug-resolution` Phases 5-6, which W9 deletes.
- 160 of 211 resolves closed 2026-09-15..2026-10-03T01:46:48Z (the last `closed_at` at fb8a29a75; same at 196f611aa) judge `caused_by: none`; `bc135641c` repaired 6. Command: `git show fb8a29a75:specs/bugs/BUGS.jsonl | jq -s '[.[]|select(.status=="resolved" and .closed_at>="2026-09-15")] | length, ([.[]|select(.caused_by=="none")]|length)'` prints 211 then 160.
- Size ceilings outlived 0143 twice (a89a557ce; `skill_md_line_ceiling`): its `measured_by` greps symbols.
- 7 resolved records on test-child env; `harness_env.py` is not the only builder (AC10.1).
- T-050-133 verifies `evidence_seam`/`evidence_diff`, 40% stale; 0164 (4) retires both.

Ledger slice read here (735 records; title/id/component match; `bugs.py status` lists 11 open):
- preflight 28 records, 1 open; meta-test/ratchet 16, 0 open, 5 naming a prior bug (`frozen-clock-ratchet-scans-tests-tmp-scratch-dir` after its own ratchet; `mutation-baseline-wiring-test-flakes…`, `…-cannot-collect` after the mutation tooling); child env 10, 1 open, 4 linked; next-step 14, 1 open, 3 linked; registry schema 5, 1 open; reconcile/pre-push 16, 1 open; backlog anchor 10, 0 open (4 are the alias map's and `subjects`'); release memory 3, 1 open.
- The cross-context walk was not introduced by a fix: `next_step`'s `for name in [*names, *trees]` is T-050-17's (97784f9ef); T-048-07's fix (27eadade4) put the focus first and kept the walk, a symptom patch. AC10.4 deletes the walk.
- Coverage location, five steps, one cause:
  - 0ce8e20c0 (T-SANI-03, 2026-06-04): `data_file = ".dadaia/.cache/coverage/.coverage"`, resolved against the cwd, created `.dadaia/` inside the repo;
  - 4ce1dac4e (T-SANI-03 regression, same day): `/tmp/dadaia-ws-toolcache/coverage/.coverage`, absolute but POSIX-only;
  - T-018-07 (in db7aecbe0, 2026-06-09): removed as non-portable; each CI job sets its own `COVERAGE_FILE` (today `ci.yml:167,229`);
  - `release-workflow-coverage-file-in-checkout` (d533fbcf5): `release.yml` lacked the per-job line, so another call site got one;
  - `ci-preflight-writes-coverage-into-the-repo` (open): `ci preflight` and the documented `pytest --cov` (`tests/README.md:11`, `tests/AGENTS.md:57`) have no line at all.
  - Structural cause: decided per call site, and in config resolved against the cwd (`../../` from a worktree root is `worktrees/`). Ruff and mypy have no `../../` entry at HEAD (`pyproject.toml` holds none; `QUALITY.md:63` says they do and is false): they are already redirected by `core/workspace_layout.TOOL_CACHE_ENV`, absolute from the workspace root and set once per harness by `infrastructure/runtime_config.py:69,135` (ADR 0080). Coverage joins that decider (§2.6).
- Venv reuse, three bugs on one identity: `init-venv-installs-index-version-not-running-distribution` (the venv held other bytes than the running build; fix: always repack the running build); `reinit-with-unchanged-version-label-mixes-venv-and-projection` (ca16acd7b rebuilt `version_change` to compare `"<version> <digest>"`; 2d44e93f4 deleted its second pip step); the open `init-on-a-copied-workspace-leaves-a-cli-bound-to-the-original` (the copied entry scripts name the original interpreter, and `pip_executable` runs the original's `pip`). Each was a facet missing from what "this venv" means; §2.6 states the identity.
- Hook equality: `install_git_hooks` (`f/spec_context/service.py:144-150`) compares text, `check_installed_hooks` (`f/spec_context/doctor.py:162-165`) compares bytes and folds absent into "differs": two deciders of one question. At 6ec30315d a second install returns `[]`, mtime kept: AC10.8's hook half is green, its scratch half the RED.
- `onboarding`, `ci_preflight`, `python_env`, the backlog anchors and the meta-tests each carry ≥ 2 prior fixes: every one leaves (DELETE) or is rebuilt below.

| unit | today | bugs | verdict | why |
|---|---|---|---|---|
| `f/ci_preflight/` (165 lines); `cli/commands/ci.py` `preflight`; `core/exceptions.CiPreflightScopeError`; `container.is_source_repo_root`; `infrastructure/subprocess_runner.subprocess_runner_for_ci`; `infrastructure/python_env._ensure_ci_toolchain` | runs this repo's CI ladder from the shipped CLI; bootstraps pytest into every workspace venv | 28, 1 open | DELETE | AC8.9; `workspace_guardrail._is_source_repo_root` stays (`public_assets`) |
| `f/backlog/subject_registry.py:80-108` `load_alias_map`, `:330-348` alias and `api` binding, `Registry._aliases`/`_by_id`; `core/models/backlog.SubjectKind.API`; schema enum and `_backlog_write._KINDS` `api` | `api` binds through an operator alias map only | 4 | DELETE | AC8.9; no backlog or histo record binds `api` |
| `cli/_backlog_roots.py` (41 lines); `cli/commands/doctor.py` `--source-root`, `--alias-map` (`:104-105,120,278-287,320,335,356-357`); `f/backlog/doctor.build_context` `source_root`/`alias_map_path` | threads two roots the doctor never needs from the operator | 1 (`…-default-alias-map-unresolved-from-repo-subdir`) | DELETE | AC8.9; `_apply_fixes` never read either |
| `S/dd-backlog-definition/scripts/backlog.py:93-101` `subjects` and wiring (`:9,39,42,63-65,106,115-116`) | lists the alias map | 2 | DELETE | AC8.9 |
| `core/workspace_layout.STATES_CANON` `backlog_subject_aliases.txt` | canon entry for the alias file | — | DELETE | AC8.9; the instance's 7-line file is reaped by `doctor --fix` |
| `f/specs/doctor_release.py:33,108-128` `PLAN_MAX_LINES`, SPEC-DOC-005; `f/specs/rules.py:69-74` | a PLAN line ceiling | — | DELETE | AC8.9; 0143, 0152 (2): a size is a recommendation |
| `setup.cfg:97-109` hand-kept `features-no-cross-feature` module list | P-07's list, pinned equal to disk by `test_import_linter_ignore_cap.py:57` | — | DELETE | AC8.10: `modules = dadaia_workspace.features.*` (import-linter 2.13) |
| `tests/conftest.py:234-238` `_KNOWN_MARKERS` | P-28's set, pinned by `test_stewardship_mechanics.py:100` | — | DELETE | AC8.10: `--strict-markers` in `addopts` |
| `f/backlog/subject_registry.py:110-163` code anchors (`_module_top_level_symbols`, `_grep_top_level_symbols`, `rglob("*.py")`); `SubjectKind.CLI`, `cli_anchors` threading | a `code` anchor is a Python `path#symbol`; `cli` binds `dadaia <command>` | 10, 0 open | REBUILD | ≥ 2 bugs; a `code` anchor is any tracked path, `#word` optional, judged by a word grep; `cli` leaves |
| `core/workspace_layout.REPO_TREE_ARTIFACTS`; `privacy_check._PUBLIC_ASSET_IGNORED_DIRS` | doctor reaps tool caches in every consumer repo | — | DELETE | `REPO_TREE_EXCLUDED` becomes `(".dadaia",)`; the public walk ignores `__pycache__` only (0080) |
| `S/dd-spec-navigator/scripts/_memory_drift.CODE` (12 suffixes) | a unit is a dir holding a listed-language file | — | DELETE | every tracked file outside `NOT_CODE` and dot-dirs is code |
| `hooks/venv_guard.py:48` | names pytest/ruff/mypy | — | DELETE | sentence leaves; behaviour unchanged |
| `S/dd-test-stewardship/`, `pub/templates/tests-AGENTS.md`, wiring (`workspace_layout.REPO_LAW:71`, `f/specs/canon.py`, onboarding list, `f/specs/doctor_memory.py`, persona `skills:`, `behavior-map.json`, CONTEXT-MAP rows) | test lifecycle law shipped to every consumer | — | DELETE | AC8.1, 0166 |
| `pub/data/AGENTS.md` §1 bullets; `pub/data/fixed/slop-tests.md`; `pub/scaffold/memory/QUALITY.md` | point at the stewardship skill and `Intent:` | — | UPDATE | the five test basics rewrite existing bullets (8,293 B; must not grow) |
| `S/dd-release-implementation/MEMORY-UPDATE.md` | states its own canonical-memory rule | — | UPDATE | AC8.2: points at the memory law |
| `tests/contract/test_stewardship_mechanics.py`, `test_test_suite_ratchets.py` | P-21/22/23 and V26/V28–V31 in pytest | 5 linked | DELETE | V28/29/31 and P-28's pin leave; the rest move to guard checks at 0176's granularity (§2.3) |
| `tests/integration/test_repo_self_scan.py`, `tests/contract/test_source_repo_hygiene.py`, `test_adr_canon.py` committed-ledger case | duplicate gitleaks/pre-push, the CI hygiene and doctor jobs | — | DELETE | AC8.3 duplicates |
| `tests/scripts/run_mutation_baseline.sh`, its wiring test, `test_mutation_baseline_scope_stdlib_only.py`, `[tool.mutmut]`, group `mutation` | release mutation baseline | 2 linked | DELETE | operator tooling, outside the repo |
| `test_context_map.py:105-107,119` budgets and Measured column; `test_docs_derived_from_memory.py:34,247-252` README 10 KB budget | size pins on shipped files | — | DELETE | 0143, AC8.4/AC8.6; before `no-size-pin` lands |
| `test_slop_ratchets.py`, `test_import_linter_ignore_cap.py`, `test_suite_cannot_reach_a_real_workspace.py`, `test_suite_cannot_reach_the_instance.py`, `test_frozen_clock_aging_ratchet.py`, `test_harness_env_contract.py`, `test_ci_workflow_hygiene.py`, `test_memory_canonical_shape.py`, `test_version_lineage_consistency.py`, `test_release_semver_canon.py` release-please cases, `test_adr_canon.py` superseded-successor case | meta-tests in pytest | 5 linked | REBUILD | ≥ 2 bugs (xdist races 465, 467): one guard check per function, tracked files only |
| `S/dd-bug-resolution/scripts/_bugs_transition.py` `REQUIRED_BY_VERB`, `_EVIDENCE_DIFF_RE`, `_SEAM_RE`, `_seam_exists`; `bugs.py` stats `direction`; schema `evidence_*`; SKILL Phases 5–6; `LINEAGE.md`; `S/dd-audit-project/PILLAR-BUGS.md` rows 26, 27, 44, 45 | verifies two hand-written evidence fields, 40% stale; direction from prose | `bugs-check-trusts-evidence-fields-unverified` and the 160/211 `none` | REBUILD | 0164: the fix commit and its numstat come from git; `caused_by` proposed by blame |
| `tests/fixtures/harness_env.py` + 15 ad-hoc env copies; `tests/conftest.py` bytecode | children inherit HOME and write bytecode | 10, 1 open | REBUILD | one builder |
| `ci.yml:167,229` `COVERAGE_FILE`; documented `pytest --cov`; hook subprocesses | per-call-site location; hooks never measured | 8, 2 open | REBUILD | `TOOL_CACHE_ENV` decides for every workspace session, one workflow-level line for CI; `patch = ["subprocess"]` |
| `f/workspace/onboarding.next_step`; callers `cli/commands/context.py`, `cli/commands/doctor.py`, `hooks/ctx_inject.py` | walks every ALIVE context after the focus | 14, 1 open | REBUILD | one context judged |
| `infrastructure/python_env.version_change`, `provider_build`, `installed_build`, `pip_executable` | identity is version and payload digest; pip runs through a script | 3, 1 open | REBUILD | identity gains the entrypoint's interpreter; `python -m pip`; `pip_executable` leaves |
| `core/context_registry.entries`, `infrastructure/json_context_store.py` | a row missing a key raises `KeyError` | 5, 1 open | UPDATE | the one parse raises `SchemaVersionError` |
| `core/gitflow.py:133` | warns "no gitflow block" when the tree is absent | 15, 1 open | UPDATE | names the absence and `specs init` |
| `f/reconcile/service._snapshot_state` | scratch copy under `.dadaia/tmp/reconcile/` | 16, 1 open | REBUILD | snapshot held in memory, scratch deleted |
| `install_git_hooks` and HOOKS-DRIFT-1 equality | two deciders (text, bytes) | — | REBUILD | one `hook_state` → absent / differing / equal, both consume it |
| `S/dd-release-implementation/scripts/release.py` `_memory` | appends a second `kind: memory` entry | 3, 1 open | UPDATE | rerun is a no-op |
| `pub/schemas/bugs/bug-record-v1.schema.json#surface` | documents a deleted regex | 1 open | UPDATE | AC10.10 |
| `infrastructure/git_subprocess` tracked paths + `container` seam | — | — | ADD | `code` anchors need the tracked set and `cli` may not import infrastructure; nets against `rglob("*.py")`, the ast walk and `_backlog_roots` |
| `scripts/guards/` | — | — | ADD | no unit can carry a check whose subject is the repository; nets against the 14 meta-test files above |
| `bugs.py resolve --lineage-reason` (stored, optional schema property) | — | — | ADD | AC9.3; nets against `evidence_seam`, `_SEAM_RE`, `_seam_exists` (T-050-165) |
| `pub/entities/behavior-map.json` `skill_md_line_soft`, doctor `SKILL-MD-LENGTH` | — | — | ADD | 0170; nets against CONTEXT-MAP's Budget and Measured columns and SPEC-DOC-005 |
| `CONTEXT.md` four terms | — | — | ADD | AC8.7; nets against the SCAFFOLD homonym entry |

### 1.1 Authorities

| question | authority | consults | deleted |
|---|---|---|---|
| how this repo's CI runs locally | `.github/workflows/ci.yml` + `AGENTS.md` (repo) dev-group line | the operator, CI | `ci preflight`, `f/ci_preflight/`, `_ensure_ci_toolchain` |
| what a backlog `code` anchor resolves to | `f/backlog/subject_registry.py` over the tracked paths `container` hands it | doctor `ledgers`, BL-SCHEMA | the ast walk, `SubjectKind.CLI`, `SubjectKind.API`, the alias map, `_backlog_roots`, `--source-root`, `--alias-map`, `subjects` |
| how long a PLAN may be | nobody (0152 (2): a recommendation) | the reviewer | SPEC-DOC-005 |
| which feature packages are independent | `lint-imports`, `modules = dadaia_workspace.features.*` | CI lint | the hand-kept list and its disk-equality test |
| which pytest markers exist | `pyproject.toml` `markers` under `--strict-markers` | collection | `_KNOWN_MARKERS` and its equality test |
| what a repo tree must not carry | `core/workspace_layout.REPO_TREE_EXCLUDED` (`.dadaia`) | `f/spec_context/doctor._scan_repo_trees` | `REPO_TREE_ARTIFACTS` |
| which test basics bind | `pub/data/AGENTS.md` (root map) | slop-tests, QUALITY scaffold, personas | `dd-test-stewardship`, tests-AGENTS template, `Intent:`, V28, V29, V31 |
| what canonical memory may change at closure | `pub/scaffold/memory/AGENTS.md` | `MEMORY-UPDATE.md` | MEMORY-UPDATE's own rule |
| whether a repository-subject invariant holds | `scripts/guards/run.py` `CHECKS` | the `guards` CI job, 0176's `Measured by` lines | the moved pytest files |
| which files a guard check reads | `scripts/guards/run.py` `tracked()` (`git ls-files`) | every guard check | each file's walker |
| how long a SKILL.md may be | `behavior-map.json` two keys | doctor `SKILL-MD-LENGTH`, `test_behavior_map.py` | CONTEXT-MAP Budget column |
| whether a size is pinned | guard check `no-size-pin` | 0143's repaired `measured_by` | 0143's symbol grep |
| which commit fixed a bug, and its direction | `bugs.py fix` (git grep of shapes 3/4, numstat) | `stats`, LINEAGE.md, PILLAR-BUGS rows 27, 45 | `evidence_diff` direction, `git log -S` recipe |
| which bug caused this one | `bugs.py resolve` blame candidates | LINEAGE.md, bugs law, schema | an unreasoned `none`, `evidence_seam` verification |
| a test child's environment | `tests/fixtures/harness_env.py` builder | every subprocess test | `os.environ.copy()` copies |
| where a tool cache or coverage data lands | `COVERAGE_FILE`/`RUFF_CACHE_DIR`/`MYPY_CACHE_DIR`, absolute: `workspace_layout.TOOL_CACHE_ENV` in a workspace, one `ci.yml` workflow-level line in CI | `runtime_config`, the harness env, `tests/README.md`, `tests/AGENTS.md` | the two per-job `COVERAGE_FILE` lines |
| which context a run judges | the bound context or `--context` (`onboarding.next_step` one tree) | doctor, SessionStart, `context` CLI | the cross-context walk |
| whether a workspace venv is reusable | `python_env.version_change` over one identity | `init` | `pip_executable` |
| whether a registry row is readable | `core/context_registry.entries` | the store, doctor | the store's `KeyError` path |
| whether an installed hook is absent, differing or equal | `f/spec_context/service.hook_state` | `install_git_hooks`, HOOKS-DRIFT-1 | the text and bytes comparisons |

### 1.2 Reviewer INFO notes, resolved

- `ALLOWLISTED_DADAIA_ENV` and `HOOK_MODULES` stay in `tests/fixtures/harness_env.py`; both are `frozenset({...})` (`:154,216`), so the guard `literal_eval`s the call's set-literal argument, imports nothing from `tests/`, and checks `HOOK_MODULES` against `hooks/*.py`; the plant keeps that shape.
- The frozen-clock and V26 checks keep "tracked files only": `run.tracked()` is the one enumerator (bugs 465, 467); a planted untracked `tests/tmp/x.py` stays out.
- 0020's repair drops `tests/contract/test_harness_env_contract.py`.
- `tests/helpers/scan_population.py:17-18,40-42` loses the moved files in T-050-160; `tests/fixtures/harness_env.py:48` names the guard check id; `tests/contract/README.md:39,91` are rewritten in T-050-153 and T-050-154, its inventory table deleted.

## 2. Design

### 2.1 AC8.9 first: the CLI ships no pipeline (T-050-153, T-050-154)
- 153 deletes every unit of the first row, its tests (9 files, 837 lines, 17 functions, plus `test_cli_ci.py`'s preflight case) and every line the preflight half of the AC8.9 grep names, except files a later task deletes whole (`test_stewardship_mechanics.py`: 156; the mutation script and its wiring test: 155). `docs/cli.md` is re-rendered by `dadaia help tree`. `test_python_env.py:85-93` asserts no pytest install. Repo `AGENTS.md` gains `poetry install --with dev` into the workspace venv (nets against `_ensure_ci_toolchain`). 153 also drops `--source-root .` (`ci.yml:345`, `docs/getting-started.md:113`; behaviour-neutral, `_backlog_roots.py:28` defaults to `specs_dir.parent`) and adds `--strict-markers` to `addopts`, so no step-2 task shares `ci.yml` or `pyproject.toml`.
- 154 deletes AC8.9's second list but SPEC-DOC-005 (§1 rows 2–5) and rebuilds anchors and the repo-tree list:
  - `build_context(specs_dir, tracked)`: `cli/commands/doctor.py` gets `tracked` from a `container` seam over `GitSubprocessClient` (`git ls-files` of `specs_dir`'s repo; `cli` may not import infrastructure); the registry reads a word from `<repo>/<path>` only when the ref carries `#word`;
  - the schema's `code` pattern drops the mandatory `#symbol` and its `api` enum value; scaffold backlog law §4.1's `code`, `cli`, `api` rows and `subjects` bullet are rewritten; `test_backlog_definition_backlog_script.py:493` becomes the kind refusal with an `api` row, whose fix line (`_backlog_write.py:34`, today `{SCRIPT} subjects`) becomes `{SCRIPT} new --help`, whose `--intent` help 154 makes list `_KINDS`;
  - `test_tool_caches_stay_in_the_tmp_zone.py` gains the `pytest` row.
  - The instance's stray `.dadaia/states/backlog_subject_aliases.txt` is then reaped by `doctor --fix`; logged at closure.
- Δ prod: 153 ≈ −280; 154 ≈ −110 (first list) −138 (second list: registry −62, `API` −2, `STATES_CANON` −1, `_backlog_roots` −41, doctor threading −15, `subjects` −17) +12 (tracked-path adapter and seam) = −236.

### 2.2 W8 law and sizes (T-050-158, T-050-162)
- 158: AC8.1 deletion and wiring (`REPO_LAW`'s tests row, doctor `AGENTS-PLACEHOLDER-1` and its rule row leave with the template); root-map basics in existing bullets; AC8.2; AC8.7. Δ prod ≈ −40. AI-entity change: `dd-ai-eng-knowhow` AUTHORING, AI-surface lens, `public stage && public install && public doctor`. No task after 158 writes `Intent:`.
- 162 owns every file-size question: AC8.5 rule `SKILL-MD-LENGTH` (WARNING, one `Operator action:` naming the path and the split); CONTEXT-MAP loses Budget and Measured and its re-record lane, with `test_context_map.py:105-107,119` and the Measured-column test; SPEC-DOC-005 (`doctor_release.py:33,108-128`, `rules.py:69-74`, `test_doctor.py`'s SPEC-DOC-005 case, the fix-lines plant); the README 10 KB budget (`test_docs_derived_from_memory.py:34,247-252`). Δ prod +20 −29.

### 2.3 Guard scripts (T-050-155, 156, 159–161)
- Glob for G1: `scripts/guards/*.py`. `run.py` holds `tracked()`, the `CHECKS` registry built from every sibling module's `CHECKS` dict, `python scripts/guards/run.py` (all, exit 1 on any red, the log names each check id) and `--planted` (each check over its planted violation in a temp tree, red required). No path or id contains `test_` + an old name or `model_api`.
- Checks at ADR 0176's granularity: one id per principle or rule; every moved function survives as a `--planted` row of its id, and the violation message names the sub-rule. Deleted, never moved: V28, V29, V31, `test_marker_set_is_pinned…` (P-28: `--strict-markers`), `test_preflight_pytest_excludes_quarantine…` (AC8.9), `test_cross_feature_contract_modules_equals_disk…` (P-07: `lint-imports`).
  - `suite.py` (156), 6 ids: `private-import-ratchet` (V26, P-23), `tracked-suite-only`, `tier-timeout` (P-21: contract 30 s, explicit marker kept, four tiers, one calibrated ceiling), `quarantine-needs-bug` (P-22: refusal without a bug, collection with one, actionable serial and xdist, and every `pytest` step's `-m` in `.github/workflows` carries `not quarantine`, `ci.yml:140,171,200,231,257,294`, planted with a selector lacking it), `statement-id-cited`, `push-starts-no-gc`.
  - `slop.py` (159), 9 ids: `v32`, `v33`, `v37`, `v38`, `v39`, `v40`, `doctor-section-subset`, `ignore-cap` (P-10), and the ADD `no-size-pin` (AC8.6). Its subject is a file's line or byte count against a constant, 0170's two keys excepted; hit counts (V26, V32, V33) and the Agent Skills field limits (`test_standalone_skills.py:29-30`) are not file sizes. 159 deletes `tests/helpers/suite_files.py`, whose four consumers 156, 159 and 160 delete.
  - `isolation.py` (160), 5 ids: `no-real-workspace` (cwd walk, start outside the checkout, bare doctor), `no-instance-reach` (fenced child, every enclosing instance fenced), `frozen-clock`, `harness-env-allowlist`, `hook-stdin-not-in-process`.
  - `repo.py` (161), 10 ids: `no-model-api-in-ci` (P-33), `workflow-never-rules`, `release-workflow-canon` (P-30: main-only pinned release-please, publish chain, manifest and patch rule, pyproject version = CHANGELOG top), `memory-canonical-shape` (P-32, its nine rules), `adr-superseded-successor`, `ci-triggers-gitflow`, `pr-source-guard-release-pr`, `ci-checkout-history`, `required-checks-listed`, `onboarding-journey-uv`.
- Session checks (`tier-timeout`, `quarantine-needs-bug`'s collection rows, `push-starts-no-gc`, `no-real-workspace`, `no-instance-reach`) judge what `tests/conftest.py` does to a live session, never the guard's own process: `run.py` runs ONE pytest subprocess over a generated probe under the repo conftest (the pattern of `test_stewardship_mechanics.py:130-178`), its report read by every session check; its seconds count in G4.
- CI: one job `guards` in `ci.yml` runs `run.py` then `run.py --planted`; lint and mypy jobs add `scripts/` (156). Pytest leaves `--cov` alone.
- A guard module has no mutation run of its own: `--planted` turns each check red on its violation, which is the kill a mutant would prove. Its commit body predeclares that `mutation: skipped` line.

### 2.4 AC8.4 behaviour asserts (T-050-163, T-050-164)
- Candidate files found by `.md` read + long-string `in` assert at 3f48e11dd (list in TASKS); each assert becomes exit code, effect or stable id, or leaves with its reason in the body. The two `len(…) == NN` pins leave with their files (159, 161).

### 2.5 W9 (T-050-165, 167, 168)
- 165 DELETE first: Phase 5 "rewritten", Phase 6 "net ≤ 0"; `REQUIRED_BY_VERB["resolve"]` drops `evidence_seam`, `evidence_diff`; `_EVIDENCE_DIFF_RE`, `_SEAM_RE` and `_seam_exists` leave; schema keeps both properties optional; PILLAR-BUGS row 26 counts `evidence_loop`, row 44 loses its clause; §3a row 4 widens (AC9.5).
- 167 ADD `bugs.py fix <id>`: `git log -E --grep='^fix\(bugs\): .*<id>'` else the `(<sha>)` of shape 4; prints sha, test files, numstat; `stats` `direction:` reads it. Nets against the `direction` row's `evidence_diff` split, `_EVIDENCE_DIFF_RE` (165) and LINEAGE's `git log -S` recipe.
- 168 ADD blame: `resolve` runs `git blame` on lines the staged diff removes, skips the projection's regenerated files, `(#n)` squashes and `refactor(T-…)`; refuses a `--caused-by` outside the candidates and `none` with candidates, unless `--lineage-reason` (§1 ADD row). AC9.4 in `dd-code-review`.
- Δ prod ≈ −25, +22, +35.

### 2.6 W10 (T-050-169–179)
- A bug task: one `bug` worktree, one `fix(bugs): <id> — <cause>` commit, its RED a parametrize row in the owner file, red loop in the body, `--caused-by` from 168's candidates. T-050-177 has no bug record: `impl` worktree, `fix(T-050-177): …`. AC10.11 resolves by citation at 181.
- 171 (AC10.5), REBUILD of the identity, not a third branch: a venv is reusable when its build (`"<version> <digest>"`) AND its `dadaia` entrypoint's interpreter (the entrypoint's bytes carry `DIR/.dadaia/.venv`'s python path; POSIX shebang and Windows launcher alike) equal the running side's; `version_change` composes the running side as `provider_build()` plus `python_executable(DIR)` and `installed_build` adds the interpreter the entrypoint names, then compares once; `_verify_venv_provider` keeps `provider_build()` (it checks bytes, not binding). A mismatch is `upgrade`; the reinstall runs `<venv python> -m pip install --force-reinstall` (2d44e93f4's one transaction), which rewrites every entry script for `DIR`; `pip_executable` and its fake leave. No fresh venv: that would be a second install path.
- 173 (AC10.2): `TOOL_CACHE_ENV` gains `COVERAGE_FILE` as its last key, so the Codex `[shell_environment_policy.set]` pin (`test_core_file_io_purity.py:369-380`) holds (`.dadaia/tmp/coverage-cache/.coverage`, absolute, created by coverage), so every harness session places it as it places ruff's and mypy's; `ci.yml`'s two step lines become one workflow-level `COVERAGE_FILE: ${{ github.workspace }}/../coverage/.coverage` (`release.yml` reuses `ci.yml`, ADR 0078); no `data_file` in `pyproject.toml`; `repo.py`'s `workflow-never-rules` drops its coverage row. The case runs `pytest --cov` from the repo root, a subdirectory and a worktree root under the builder's env.
- 176 (AC10.8): the snapshot is held in memory and the scratch directory deleted; `hook_state(installed, shipped)` returns absent, differing or equal, and `install_git_hooks` writes on absent, on force, or on differing and shipped. 177 (AC10.12) makes HOOKS-DRIFT-1 consume `hook_state`, its message naming the state.
- 178 (AC10.3): `patch = ["subprocess"]`; the dead `parallel = false` (`pyproject.toml:183`) leaves. The cost case is `test_doctor_scan_cli.py:168` rebuilt: parametrized over the hook lanes (the SessionStart `doctor --fix --expired-only --quiet`, `ctx_inject`, `sdd_post_gate`, `pre_gate`), filesystem calls counted at two workspace sizes (2 and 20 contexts, 10 and 1,000 files), equal. No new test function.

### 2.7 Release-worktree steps (serial, `release` kind)
| step | after | commit |
|---|---|---|
| R1 | 153 | `chore(adrs): repair measured_by of 0080 — test_tool_caches_stay_in_the_tmp_zone.py for test_no_pollution.py` |
| R2 | 156 | `chore(adrs): repair measured_by of 0070` (guard `private-import-ratchet`) |
| R3 | 159 | `chore(adrs): repair measured_by of 0016, 0017, 0052, 0071, 0143` (0143: `no-size-pin`, AC8.6) |
| R4 | 160 | `chore(adrs): repair measured_by of 0020, 0088` (0020 drops `test_harness_env_contract.py`) |
| R5 | 161 | `chore(adrs): repair measured_by of 0021, 0023, 0025, 0049, 0078` (0023 drops `RELEASE-TREE-MEMORY`) |
| R6a | 158 | `docs(memory): re-render the slop-tests fixed block from 158's source` |
| R6b | 166 | `docs(memory): … (ADR 0138)` truth corrections, SPEC AC8.10's lines: `QUALITY.md:46, 47` (after 166's strip), `51-53, 55, 59-60, 63` (names `TOOL_CACHE_ENV`, no `../../`), `64, 69, 71, 72` (drops the 10 KB README budget, 162); `ARCHITECTURE.md:102, 110, 130, 134, 139` |
| R7 | R6b | operator only: `docs(adr): accept meta-test-principles-guard-checks` with the nine `### P-NN` hunks, `amends: 0167` |

- Each repair cites the merged task sha and runs before the chain's next task opens. R7's `measured_by` grep prints nothing before it is offered. T-050-180 re-derives `docs/bug-ledger-lessons.md` after R7 (precedent T-050-150).

### 2.8 G1 readout (ADR 0142), from the TASKS Δ
- Production: 153 −280; 154 −236; 158 −40; 162 −9; 165 −25; 167 +22; 168 +35; 170 −10; 171 −2; 173 +2; 174 +2; 175 +3; 176 −1; 177 −2; 179 +2 → −539; 25,307 − 539 ≈ 24,768 ≤ 24,805, a 37-line margin on estimates; 181 measures, and a miss is logged at closure, not hidden.
- Test functions: 153 −18, 154 −2, 155 −10, 156 −16, 158 −4, 159 −13, 160 −11, 161 −21, 162 −4, 163 −4, 164 −4, 165 −1, 167 +1, 168 +1 → −106; checks 6 + 9 + 5 + 10 = 30; 1,233 − 106 + 30 ≈ 1,157 ≤ 1,167; 181 measures.
- Test lines: Δ sum −4,979 (−5,139 +160); guard lines +260 +300 +250 +400 −10 = +1,200; 45,464 − 4,979 + 1,200 ≈ 41,685 ≤ 43,232.

## 3. Test strategy

- RED first, at the lowest level, in the owner file (0146 (5)); a new file only for `scripts/guards/*.py`, whose `--planted` mode is its RED.
- A literal expected value; behaviour asserts only (exit code, effect, stable id); mock only at the boundary; a fix commit never rewrites an old assert — rewriting one is its own commit with a reason (AC9.1).
- A DEL's dead tests leave in its commit (G5); a deleted test maps to a guard check or a behaviour assert, or its reason, in the body.

## 4. Bootstrap, risks, G4 baseline

- rc-8 opens on the work branch after this definition merges; rc-7 is merged.
- `bug` worktrees open only in the steps below; none other is open while T-050-166 strips `Intent:` (239 files).
- Margins (estimates): production 37, functions plus checks 10.
- One absolute `COVERAGE_FILE` is shared by concurrent `--cov` runs; worktree tests run without `--cov` (repo `AGENTS.md`).
- A bare terminal outside a harness carries no `TOOL_CACHE_ENV`: there, coverage, ruff and mypy write where the tool defaults, as today (ADR 0080's declared gap).
- G4 baseline: rc-7's run, one runner class, median; only `guards` is added.

## 5. Parallel schedule

| step | tasks open together | width | how |
|---|---|---|---|
| 1 | T-050-153 | 1 | one impl worktree; AC8.9 lands first |
| 2 | T-050-154, T-050-155, T-050-156, T-050-157 | 4 | one impl worktree each; R1 after 153, R2 after 156 |
| 3 | T-050-158, T-050-160, T-050-161 | 3 | one impl worktree each; R6a, R4, R5 follow |
| 4 | T-050-162, T-050-163, T-050-164, T-050-165 | 4 | one impl worktree each |
| 5 | T-050-159, T-050-167 | 2 | one impl worktree each; R3 follows 159 |
| 6 | T-050-166, T-050-168 | 2 | one impl worktree each; R6b, then R7, after 166 |
| 7 | T-050-169, T-050-170, T-050-171, T-050-172 | 4 | one `bug` worktree each |
| 8 | T-050-173, T-050-174, T-050-175, T-050-176 | 4 | one `bug` worktree each |
| 9 | T-050-177, T-050-178, T-050-179, T-050-180 | 4 | 177, 180 impl; 178, 179 `bug` |
| 10 | T-050-181 | 1 | measure; closure in the release worktree |

- Edges: each task's `blocked by:` (TASKS).
- Critical path: T-050-153 → T-050-156 → T-050-158 → T-050-162 → T-050-159 → T-050-166 → T-050-169 → T-050-173 → T-050-178 → T-050-181 = 10 steps.
- Overlap check: disjoint in every step except `TASKS.md`, the `*.jsonl` ledgers, the derived `pub/entities/behavior-map.json` and `pub/templates/shipped-hashes.json`; no step shares `ci.yml` or `pyproject.toml` (153 takes both step-2 hunks).
- Merge in ready order; open siblings rebase after each.
