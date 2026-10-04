# PLAN — Release: 0.5.0

**Status:** Approved
**Release ID:** 0.5.0
**Owner:** dd-software-engineer

Candidate 8 — W8: the test law and the library pipeline leave; W9: bug lineage derived; W10: the open bugs (ADR 0140). SPEC AC8.1–AC8.10, AC9.1–AC9.5, AC10.1–AC10.14, Approved at 3f48e11dd and amended by operator ruling at 6ea03b0ff (AC8.9's second deletion list; AC8.10's P-07 and P-28 by their own tool; ADR 0176 edited at 6ec30315d); W11, AC11.0–AC11.6, folded by operator ruling at fde8254d3 (agent-behavior evals, a parallel lane in `dadaia-evals`; the evals gate at the promote is SPEC §Carried rc-12's, 0178); amended at e64918789 (AC8.3's visibility rows to `specs-canon-tracked`, AC10.14, AC11.5 onto `dadaia-evals` `main`) and at d5f060c17 (review of 0dfbe16f6); amended by operator ruling at 23c7c7f35 (AC10.1 runs pytest with `-B`) and at 5bc6dc63f, re-cut at 257fb7128 (AC10.1's one authority is the conftest session env, with a tripwire and its plant). Amended for W12 (AC12.1–AC12.14, AC9.3, AC9.4 and AC10.1 rewritten; SPEC Approved at 6b84527bc): §6; from here W12's Order (§6.1) governs every open task. Paths are relative to `dadaia_workspace/` (`f/` = `features/`, `pub/` = `public/`, `S/` = `pub/skills/`) unless they start with `tests/`, `scripts/`, `specs/`, `docs/`, `.github/`, `README.md`, `AGENTS.md`, `CONTEXT.md`, `pyproject.toml`, `poetry.lock` or `setup.cfg`.
As-is read at `wt/0.5.0b-release` 6ec30315d; the G1 `<start>` readout equals the birth readout (8f4ed785f): 25,307 production lines / 1,233 test functions / 45,464 test lines / 0 guard lines / 0 guard checks.

## 1. As-is review

Bug history read (permanent architecture review), from handoff `2026-10-03T135506Z-dd-product-engineer-rc8-spec-rereview-2-applied`:
- Preflight fix chain: `ci-preflight-unusable-outside-the-source-repo` got a refusal (symptom patch), then `preflight-doctor-judges-instance-state-ci-never-sees`; `ci-preflight-writes-coverage-into-the-repo` is open. Cause: a verb serving only this repo; AC8.9 deletes it.
- `surface: tests`: 67 records, 14 naming a prior bug; F018: 22% fix-induced, many from meta-tests.
- 128 of 237 `fix(bugs):` commits, 2026-08-23..2026-10-02, remove an assert (`git log -E --grep='^fix\(bugs\): ' fb8a29a75`, each through `git show -U0 -- tests | grep -E '^-\s*assert'`). Cause: `dd-bug-resolution` Phases 5-6, which W9 deletes.
- 160 of 211 resolves closed 2026-09-15..2026-10-03T01:46:48Z judge `caused_by: none`; `bc135641c` repaired 6. Command: `git show fb8a29a75:specs/bugs/BUGS.jsonl | jq -s '[.[]|select(.status=="resolved" and .closed_at>="2026-09-15")] | length, ([.[]|select(.caused_by=="none")]|length)'` prints 211 then 160.
- Size ceilings outlived 0143 twice (a89a557ce; `skill_md_line_ceiling`): its `measured_by` greps symbols.
- Child env: 10 records, 1 open (row 54; the handoff's 7 are their resolved test-child subset); 15 ad-hoc copies bypassed `harness_env.py`. Inheriting children hold by construction; from-scratch envs start from `child_keys()`, and the sessionfinish tripwire catches a miss (AC10.1).
- T-050-133 verifies `evidence_seam`/`evidence_diff`, 40% stale; 0164 (4) retires both.

Ledger slice read here (735 records; title/id/component match; `bugs.py status` lists 11 open):
- preflight 28 records, 1 open; meta-test/ratchet 16, 0 open, 5 naming a prior bug (`frozen-clock-ratchet-scans-tests-tmp-scratch-dir` after its own ratchet; `mutation-baseline-wiring-test-flakes…`, `…-cannot-collect` after the mutation tooling); child env 10, 1 open, 4 linked; next-step 14, 1 open, 3 linked; registry schema 5, 1 open; reconcile/pre-push 16, 1 open; backlog anchor 10, 0 open (4 are the alias map's and `subjects`'); release memory 3, 1 open.
- The cross-context walk was not introduced by a fix: `next_step`'s `for name in [*names, *trees]` is T-050-17's (97784f9ef); T-048-07's fix (27eadade4) put the focus first and kept the walk, a symptom patch. AC10.4 deletes the walk.
- Coverage location, five steps, one cause (0ce8e20c0 cwd-relative; 4ce1dac4e POSIX-only; db7aecbe0 per-job `ci.yml:167,229`; d533fbcf5 `release.yml`; open `ci-preflight-writes-coverage-into-the-repo`: `ci preflight` and `pytest --cov`, `tests/README.md:11`, `tests/AGENTS.md:57`, none):
  - Structural cause: decided per call site, and in config resolved against the cwd (`../../` from a worktree root is `worktrees/`). Ruff and mypy (no `../../` entry; `QUALITY.md:63` is false) are already redirected by `core/workspace_layout.TOOL_CACHE_ENV`, absolute from the workspace root and set once per harness by `infrastructure/runtime_config.py:69,135` (ADR 0080). Coverage joins that decider (§2.6).
- Venv reuse, three bugs on one identity: `init-venv-installs-index-version-not-running-distribution` (the venv held other bytes than the running build; fix: always repack the running build); `reinit-with-unchanged-version-label-mixes-venv-and-projection` (ca16acd7b rebuilt `version_change` to compare `"<version> <digest>"`; 2d44e93f4 deleted its second pip step); the open `init-on-a-copied-workspace-leaves-a-cli-bound-to-the-original` (the copied entry scripts name the original interpreter, and `pip_executable` runs the original's `pip`). Each was a facet missing from what "this venv" means; §2.6 states the identity.
- Hook equality: `install_git_hooks` (`f/spec_context/service.py:144-150`) compares text, `check_installed_hooks` (`f/spec_context/doctor.py:162-165`) compares bytes and folds absent into "differs": two deciders of one question. At 6ec30315d a second install returns `[]`, mtime kept: AC10.8's hook half is green, its scratch half the RED.
- A memory-drift unit is a directory; a file at the repo root belongs to no unit (T-050-154 ruling).
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
| `tests/contract/test_stewardship_mechanics.py`, `test_test_suite_ratchets.py` | P-21/22/23 and V26/V28–V31 in pytest | 5 linked | REBUILD | V28/29/31 and P-28's pin leave; the rest move to guard checks at 0176's granularity (§2.3) |
| `tests/integration/test_repo_self_scan.py`, `tests/contract/test_source_repo_hygiene.py`, `test_adr_canon.py` committed-ledger case | duplicate gitleaks/pre-push, the CI hygiene and doctor jobs | — | DELETE | AC8.3 duplicates |
| `tests/scripts/run_mutation_baseline.sh`, its wiring test, `test_mutation_baseline_scope_stdlib_only.py`, `[tool.mutmut]`, group `mutation` | release mutation baseline | 2 linked | DELETE | operator tooling, outside the repo |
| `test_context_map.py:105-107,119` budgets and Measured column; `test_docs_derived_from_memory.py:34,247-252` README 10 KB budget | size pins on shipped files | — | DELETE | 0143, AC8.4/AC8.6; before `no-size-pin` lands |
| `test_slop_ratchets.py`, `test_import_linter_ignore_cap.py`, `test_suite_cannot_reach_a_real_workspace.py`, `test_suite_cannot_reach_the_instance.py`, `test_frozen_clock_aging_ratchet.py`, `test_harness_env_contract.py`, `test_ci_workflow_hygiene.py`, `test_memory_canonical_shape.py`, `test_version_lineage_consistency.py`, `test_release_semver_canon.py` release-please cases, `test_adr_canon.py` superseded-successor case | meta-tests in pytest | 5 linked | REBUILD | ≥ 2 bugs (xdist races 465, 467): guard checks at 0176's granularity (§2.3), tracked files only |
| `S/dd-bug-resolution/scripts/_bugs_transition.py` `REQUIRED_BY_VERB`, `_EVIDENCE_DIFF_RE`, `_SEAM_RE`, `_seam_exists`; `bugs.py` stats `direction`; schema `evidence_*`; SKILL Phases 5–6; `LINEAGE.md`; `S/dd-audit-project/PILLAR-BUGS.md` rows 26, 27, 44, 45 | verifies two hand-written evidence fields, 40% stale; direction from prose | `bugs-check-trusts-evidence-fields-unverified` and the 160/211 `none` | REBUILD | 0164: the fix commit and its numstat come from git; `caused_by` proposed by blame |
| (superseded by §6.4, AC10.1 re-cut) `tests/fixtures/harness_env.py` + 15 ad-hoc env copies; `tests/conftest.py` bytecode | children inherit HOME and write bytecode | 10, 1 open | REBUILD | one authority, `tests/conftest.py`'s session env (`PYTHONDONTWRITEBYTECODE=1`, `DADAIA_FENCED_ROOTS` at import; `HOME`/`USERPROFILE`/`XDG_CACHE_HOME`/`LOCALAPPDATA` under `tempfile.mkdtemp(prefix="dadaia-test-home-")` at `pytest_configure`, by `pin_child_env()`, removed at `pytest_unconfigure`). Leave: `session_home()`, `_base_env()`'s `HOME` pin, both e2e `_hook_env` helpers, the ad-hoc copies that rebuilt child keys, and module-level env snapshots taken before the pin; per-call filtered reads of the session env stay. Stay: `base_env()`, public, for hook and non-hook children; `child_keys()`, the base of a from-scratch env; `pin_child_env()`. The bootstrap and onboarding e2e envs are `base_env()` minus `DADAIA_*` but the fence |
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
| `S/dd-gitflow-default/scripts/_worktree_new.new` impl trio read; `_worktree_git.gitflows` | reads the trio from `repo` itself, so an associated repo has none; the Draft fix line names `repo_name` | 0 on the trio read (3 records name `worktree new`, all resolved, none on it) | UPDATE | AC11.0: the one read names the main repo (§2.9); no second read, no branch on role |
| root map `:43`, `S/dd-gitflow-default/SKILL.md` §3b, `CICD-AUTOMATION.md:17`; `CONTEXT.md` **Evals repo** | "no CI job calls a model API", unscoped | — | UPDATE | AC11.1, 0177: three existing lines rescoped; one term beside **Scope** |

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
| a test child's environment (superseded by §6.4: `suite_env`) | `tests/conftest.py` session env (`pin_child_env()`; `base_env()`, `child_keys()` derive from it) | every subprocess test | `session_home()`, `_base_env()`'s `HOME` pin, the e2e `_hook_env` helpers, the ad-hoc copies that rebuilt child keys, module-level env snapshots taken before the pin (per-call filtered reads of the session env stay) |
| where a tool cache or coverage data lands | `COVERAGE_FILE`/`RUFF_CACHE_DIR`/`MYPY_CACHE_DIR`, absolute: `workspace_layout.TOOL_CACHE_ENV` in a workspace, one `ci.yml` workflow-level line in CI | `runtime_config`, the harness env, `tests/README.md`, `tests/AGENTS.md` | the two per-job `COVERAGE_FILE` lines |
| which context a run judges | the bound context or `--context` (`onboarding.next_step` one tree) | doctor, SessionStart, `context` CLI | the cross-context walk |
| whether a workspace venv is reusable | `python_env.version_change` over one identity | `init` | `pip_executable` |
| whether a registry row is readable | `core/context_registry.entries` | the store, doctor | the store's `KeyError` path |
| whether an installed hook is absent, differing or equal | `f/spec_context/service.hook_state` | `install_git_hooks`, HOOKS-DRIFT-1 | the text and bytes comparisons |

### 1.2 Reviewer INFO notes, resolved

- `ALLOWLISTED_DADAIA_ENV` and `HOOK_MODULES` stay in `tests/fixtures/harness_env.py`; both are `frozenset({...})` (`:154,216`), so the guard `literal_eval`s the call's set-literal argument, imports nothing from `tests/`, and checks `HOOK_MODULES` against `hooks/*.py`; the plant keeps that shape.
- The frozen-clock and V26 checks keep "tracked files only": `run.tracked()` is the one enumerator (bugs 465, 467); a planted untracked `tests/tmp/x.py` stays out.
- 0020's repair drops `tests/contract/test_harness_env_contract.py`.
- `tests/helpers/scan_population.py:17-18,40-42` loses the moved files in T-050-160; `tests/fixtures/harness_env.py:48` names the guard check id; `tests/contract/README.md:91`'s inventory table leaves in T-050-154.

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
  - `repo.py` (161), 11 ids: `no-model-api-in-ci` (P-33), `workflow-never-rules`, `release-workflow-canon` (P-30: main-only pinned release-please, publish chain, manifest and patch rule, pyproject version = CHANGELOG top), `memory-canonical-shape` (P-32, its nine rules), `adr-superseded-successor`, `ci-triggers-gitflow`, `pr-source-guard-release-pr`, `ci-checkout-history`, `required-checks-listed`, `onboarding-journey-uv`, `specs-canon-tracked` (AC8.3's visibility rows: one probe per `canon.py` `CANON` row, `git check-ignore --no-index`; expected ignored only where rendering the row's `TEMPLATES` source through `render_registry_tables` changes it, today `specs/AGENTS.md`, and the two `releases/_archive/<v>/{local-notes.md,tmp/}` rows, the ignored half; plants: a `.gitignore` hiding `specs/releases/**/TASKS.md`, a re-include of `_archive/**/local-notes.md`; ≈ +40 guard lines). `.gitignore:119,139` stop citing the deleted `test_source_repo_hygiene.py`.
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
- A bug task: one `bug` worktree, one `fix(bugs): <id> — <cause>` commit, its RED a parametrize row in the owner file (except AC10.1's: a session hook, the `pytest_sessionfinish` tripwire, since no per-test assert sees other tests' children), red loop in the body, `--caused-by` from 168's candidates. T-050-177 has no bug record: `impl` worktree, `fix(T-050-177): …`. AC10.11 resolves by citation at 181.
- 171 (AC10.5), REBUILD of the identity, not a third branch: a venv is reusable when its build (`"<version> <digest>"`) AND its `dadaia` entrypoint's interpreter (the entrypoint's bytes carry `DIR/.dadaia/.venv`'s python path; POSIX shebang and Windows launcher alike) equal the running side's; `version_change` composes the running side as `provider_build()` plus `python_executable(DIR)` and `installed_build` adds the interpreter the entrypoint names, then compares once; `_verify_venv_provider` keeps `provider_build()` (it checks bytes, not binding). A mismatch is `upgrade`; the reinstall runs `<venv python> -m pip install --force-reinstall` (2d44e93f4's one transaction), which rewrites every entry script for `DIR`; `pip_executable` and its fake leave. No fresh venv: that would be a second install path.
- 173 (AC10.2): `TOOL_CACHE_ENV` gains `COVERAGE_FILE` as its last key, so the Codex `[shell_environment_policy.set]` pin (`test_core_file_io_purity.py:369-380`) holds (`.dadaia/tmp/coverage-cache/.coverage`, absolute, created by coverage), so every harness session places it as it places ruff's and mypy's; `ci.yml`'s two step lines become one workflow-level `COVERAGE_FILE: ${{ github.workspace }}/../coverage/.coverage` (`release.yml` reuses `ci.yml`, ADR 0078); no `data_file` in `pyproject.toml`; `repo.py`'s `workflow-never-rules` drops its coverage row. The case runs `pytest --cov` from the repo root, a subdirectory and a worktree root under the session env.
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
| R8 | the fold | `docs(adr): accept evals-reopen-without-plugin` (0179), done at f4c3d5b39 |
| R9 | 161, R5 | operator only: `docs(adr): accept <0177's slug>`, `amends: 0025`, with P-33's re-scope hunk; its check `no-model-api-in-ci` exists from 161; beside it, the operator's `dadaia-evals` act (SPEC W11 prerequisites: environment `evals`, `main` only, its secret; the `ci.yml` job required on `develop` and `main`); 188 needs both |
| R10 | `0.5.0d-bug` merge (the union fix; 0180's `measured_by` passes on the work branch) | operator only: `docs(adr): accept <0180's slug>`; unblocks T-050-189 |

- 0178 is accepted at closure, not here (SPEC §Decisions).
- AC10.14's memory half (`worktrees.md:5,35,36`, `bug-ledger.md:32`; `worktrees.md:35` also for AC11.0; `catalog.json` regenerated) is the closure memory pass (0138 lane), no task row; it waits only on the `0.5.0d-bug` merge. Only 189's law line waits on R10.
- G6, no deadlock: a task pending on an operator ruling at closure (183, 187, 188 on R9; 189 on R10) leaves T-050-181's `blocked by:` once rc-9's §Carried line records it.
- Closure notes: refresh this repo's own `specs/backlog/AGENTS.md` (the template 154 supersedes); `release-lifecycle.md:42`'s "local CI preflight" leaves (153).
- Each repair cites the merged task sha and runs before the chain's next task opens. R7's `measured_by` grep prints nothing before it is offered. T-050-180 re-derives `docs/bug-ledger-lessons.md` after R7 (precedent T-050-150).

### 2.8 G1 readout (ADR 0142)
- This repo's lines only (SPEC W11): 182 counts; 183 and 189 are Markdown, outside the `*.py` readout; 184–188 write `repos/dadaia-evals`.
- Measured: 153, 156 merged; 155, 154 (rework in flight) at review; `0.5.0d-bug` unplanned; test lines 153 −818, 154 −165, 155 −649 (its `.sh` outside), 156 −628, d-bug +15; 169 at 7c6d19fe8: production 0, tests +128/−123 = +5, functions 0 (planned −60; the miss is the operator's "Global test setup" ruling: the RED is a session check, not a builder replacing copies); 170 at dbf3cae97: production +23/−19 = +4 (planned −10), tests +52/−2 = +50 (planned +10), functions +2 (planned 0) (structural: the existing `_alive_repo_tops(context)` seam threads through `scan`/`fix` and a single-context judge replaces the walk; no new branch or flag). Merged follow-ups: 169's CI fix 4ca3d7136 (pin moved to `pytest_configure`): production +1 (`python_env.py` `-B`), `conftest.py` +18/−5, so 169 totals production +1, tests +18, functions 0; 170's a88d849c4: a stub +1/−1, totals unchanged. 171 at adf31f8d2: production +12/−13 = −1 (planned −2), tests +61/−16 = +45 (planned +10; `tests/fakes.py` −8), functions +1 (planned 0). Else the TASKS Δ.
- Production: 153 −283; 154 −261; d-bug −18; 158 −40; 162 −9; 165 −25; 167 +22; 168 +35; 169 +1; 170 +4; 171 −1; 173 +2; 174 +2; 175 +3; 176 −1; 177 −2; 179 +2; 182 +10 → −559; 25,307 − 559 ≈ 24,748 ≤ 24,805, a 57-line margin; 181 measures, and a miss is logged at closure, not hidden.
- Test functions: 153 −19, 154 −1, 155 −9, 156 −15, 158 −4, 159 −13, 160 −11, 161 −21, 162 −4, 163 −4, 164 −4, 165 −1, 167 +1, 168 +1, 169 0, 170 +2, 171 +1, 182 0 (a parametrize row) → −101; checks 6 + 9 + 5 + 11 = 31; 1,233 − 101 + 31 ≈ 1,163 ≤ 1,167, a 4-check margin; 181 measures.
- Test lines: Δ sum −4,762 (182's +15 in; actuals 169 +18, 170 +50, 171 +45 for −60, +10, +10 planned); guard lines +493 +300 +250 +440 −10 = +1,473 (161's +40: `specs-canon-tracked`); 45,464 − 4,762 + 1,473 ≈ 42,175 ≤ 43,232, a 1,057-line margin.
- Overrun risk: 156's guard came in at 1.9× its estimate; 159–161 at 1.9× leave ≈ 320 lines.

### 2.9 W11 (T-050-182–188)
- 182 (AC11.0), deletion first: `gitflows` already reads each row of `context list --json`; each repo's entry gains the row's `main_repo` as `flow["main"]`, and `new` reads the trio at `root/repos/<flow["main"]>` on `flow["work"]`, its Draft fix line naming `flow["main"]`. A main repo resolves to itself: one resolution, no second read, no branch on role. Δ ≈ +10 at most. The case is a parametrize row on `test_impl_needs_an_approved_trio_in_the_live_candidate`, an associated repo under `make_workspace`'s registry.
- 183 (AC11.1): text only; AI-entity change under `dd-ai-eng-knowhow` AUTHORING, `public stage && public install && public doctor`; the root map stays ≤ 8,293 B.
- 184–187 (AC11.2–AC11.5), one `impl` worktree of `dadaia-evals` each, `W:` disjoint by directory: 184 the repo law and ignores, 185 `tasks/t1-cold-onboarding/`, 186 `tasks/t2-seeded-bug/`, 187 `.github/workflows/{eval,ci}.yml` and `scripts/`. No `specs/` in that repo.
- 187 (AC11.5): `eval.yml`'s model job alone declares `environment: evals` and runs `uv tool install harbor==0.23.0`, then `harbor run -p tasks -a claude-code -m anthropic/claude-sonnet-5 --ak version=<pinned> -k 3 -n ≤2`, the model per the economy template (ADR 0022). `ci.yml` (push, pull_request, no secret, no environment) runs the workflow check, the planted-token scan fixture and the `compare.py` cases.
- 187, after review, reaches `dadaia-evals` `main` through that repo's PR edges `feature/0.5.0` → `develop` → `main`, each with CI green and an APPROVED verdict; A PR edge carries every `dadaia-evals` commit on its branch, so 184–186 reach `main` with it. Its `done` marker cites the `main` merge sha.
- 188 (AC11.6): `gh workflow run eval.yml -f lib_ref=<tip of feature/0.5.0>` on `dadaia-evals`, once 187 is on its `main`; one dispatch by the main thread, read back into a handoff; the `_RELEASE.json` log line is written at closure (181's lane).
- Markers (the releases law §3, ADR 0111): an `impl` worktree's allowed set holds its own repo's `TASKS.md` only, and `dadaia-evals` has none. `_worktree_kinds.KINDS["release"]` holds `specs/releases/*`, so this candidate's `release` worktree writes W11's markers: `start` before the main thread opens the `dadaia-evals` worktree, `done` after its `WT merge`, `chore(tasks): <verb> T-050-NNN — dadaia-evals <sha>`; they reach the work branch with the `release` worktree's next merge, like R1–R9.

## 3. Test strategy

- RED first, at the lowest level, in the owner file (0146 (5)); a new file only for `scripts/guards/*.py`, whose `--planted` mode is its RED.
- A literal expected value; behaviour asserts only (exit code, effect, stable id); mock only at the boundary; a fix commit never rewrites an old assert — rewriting one is its own commit with a reason (AC9.1).
- A DEL's dead tests leave in its commit (G5); a deleted test maps to a guard check or a behaviour assert, or its reason, in the body.

## 4. Bootstrap, risks, G4 baseline

- rc-8 opens on the work branch after this definition merges; rc-7 is merged.
- `bug` worktrees open only in the steps below; none other is open while T-050-166 strips `Intent:` (239 files).
- One absolute `COVERAGE_FILE` is shared by concurrent `--cov` runs; worktree tests run without `--cov` (repo `AGENTS.md`).
- A bare terminal outside a harness carries no `TOOL_CACHE_ENV`: there, coverage, ruff and mypy write where the tool defaults, as today (ADR 0080's declared gap).
- G4 baseline: rc-7's run, one runner class, median; only `guards` is added (this repo's CI; `eval.yml` is `dadaia-evals`').
- A refused `dadaia-evals` PR edge (CI red, no APPROVED) holds 188; it is fixed at its cause, never bypassed.

## 5. Parallel schedule

| step | tasks open together | width | how |
|---|---|---|---|
| 1 | T-050-153 | 1 | one impl worktree; AC8.9 lands first |
| 2 | T-050-154, T-050-155, T-050-156, T-050-157 | 4 | one impl worktree each; R1 after 153, R2 after 156 |
| 3 | T-050-158, T-050-160, T-050-161 | 3 | one impl worktree each; R6a, R4, R5 follow |
| 4 | T-050-162, T-050-163, T-050-164, T-050-165 | 4 | one impl worktree each |
| 5 | T-050-159, T-050-167, T-050-182, T-050-183 | 4 | one impl worktree each; R3 follows 159; 182 after 164 and `0.5.0d-bug` merge, 183 after R9 |
| 6 | T-050-166, T-050-168; T-050-184, T-050-185, T-050-186, T-050-187 | 6 | one impl worktree each, 184–187 in `dadaia-evals` (its own cap of 5); R6b, then R7, after 166; 187 then reaches `dadaia-evals` `main` (§2.9) |
| 7 | T-050-169, T-050-170, T-050-171, T-050-172; T-050-188, T-050-189 | 6 | one `bug` worktree each; 188 is a dispatch once 187 is on `dadaia-evals` `main`, no worktree; 189 one impl worktree once R10 lands, else rc-9 |
| 8 | T-050-173, T-050-174, T-050-175, T-050-176 | 4 | one `bug` worktree each |
| 9 | T-050-177, T-050-178, T-050-179, T-050-180 | 4 | 177, 180 impl; 178, 179 `bug` |
| 10 | T-050-181 | 1 | measure; closure in the release worktree |

- Every open task here (T-050-172 … T-050-181, T-050-185, T-050-186, T-050-188) is paused; §6.6 schedules W12 first, then these steps resume.
- Edges: each task's `blocked by:` (TASKS).
- Critical path: T-050-153 → T-050-156 → T-050-158 → T-050-162 → T-050-159 → T-050-166 → T-050-169 → T-050-173 → T-050-178 → T-050-181 = 10 steps.
- W11 is off the critical path: 182 → 184–187 → 187 on `dadaia-evals` `main` → 188 ends at step 7. 189 waits only on R10, off the path.
- Widened `W:` inside their own task commits stay sequential: 154's `test_doctor_fix_lines_clear_their_finding.py` precedes 158, 162, 169 (each blocked by 154 transitively), `test_backlog_models.py` is 154's alone; 156's `test_ci_workflow_hygiene.py` (161 deletes it) and `.github/required-checks.json` (161 reads it) precede 161 (blocked by 156); 161's `.gitignore` is its alone.
- Overlap check: `dadaia-evals` paths are disjoint from every W8–W10 `W:`; 182 and 183 share only the derived files below with their step; disjoint in every step except `TASKS.md`, the `*.jsonl` ledgers, the derived `pub/entities/behavior-map.json` and `pub/templates/shipped-hashes.json`; no step shares `ci.yml` or `pyproject.toml` (153 takes both step-2 hunks).
- Merge in ready order; open siblings rebase after each.

## 6. W12 — the bug loop stops (amendment 2026-10-04)

As-is read at `wt/0.5.0b-release` 6b84527bc (= feature/0.5.0). Bug history: the grill handoff `2026-10-04T190000Z-main-thread-grill-fix-induced-bugs` and the read-only audit at 76d7af604 (18 unregistered fix-induced breaks, 16 `fix(...)` + 2 `test(...)` repairs; 4 `rebuild: none` with ≥ 2 prior fixes: dfa3aceb6, 1cfc3b72d, a8f226c8b, 1ee8aa30f). ADRs 0172, 0185, 0186 are accepted (1eff0d75c, 28e8927e8, d5e5a6edd).

### 6.1 Order (SPEC W12 Order, Q5) and the pause

1. T-050-190 (AC12.6, the script), landed by today's `WT merge`; then T-050-191 (AC12.5, AC12.7, T-050-189 folded), also landed by the old code, because `worktree.py merge` runs from the instance projection. R14 re-projects the library (`public stage`, `public install`, `public doctor`) before T-050-192 opens, so T-050-192's merge is the first gated one.
2. T-050-192 (AC9.3 and AC12.12's code); one task per law file: T-050-193 `AUTHORING.md` (rule 9 first: the bar the others meet), 194 bugs law, 195 `dd-bug-resolution`, 196 `dd-release-implementation`, 197 `dd-gitflow-default`, 198 `dd-code-review` (every edit: AC9.4, AC12.6, AC12.12); then T-050-199 (AC12.4).
3. REBUILDs T-050-200 (AC10.1), 201 (AC12.8), 202 (AC12.13); then 203 (AC12.9), 204 (AC12.10); then AC12.14's own fixes 205–208.
4. Paused, no marker (the releases law §3 has none): T-050-172 … T-050-181, T-050-185, T-050-186, T-050-188. Each stays `[ ]` and opens only after T-050-208 merges; T-050-181 is blocked by every W12 task. Their `W:` are re-read against §6 before they open (T-050-173 now writes `scripts/ci.py`, not the pytest lines of `ci.yml`).

### 6.2 The verification command (AC12.5, AC12.6)

- Declared as one line `verify: <command>` in the repo's root `AGENTS.md`, read by `merge` from `git show HEAD:AGENTS.md`, run by the platform shell with the worktree as cwd.
  - Why there: a file that exists and that any repo of any language may have; this repo has one (`AGENTS.md:16-17` already names the worktree's test command, and `pub/data/worktrees-AGENTS.md:44` says "Tests run by the command the repo's `AGENTS.md` names for a worktree"). Gate 1 makes that existing sentence executable, so nothing new is added: no file, schema, config key or flag.
  - Rejected: `specs/constitution.md` (only the main repo carries `specs/`, and an associated repo like `dadaia-evals` merges too); a new dot-file (an ADD where an existing file serves); git config (not read from the landed HEAD, so a worktree could not declare it, against AC12.5's self-declaring case).
  - Bug history: every worktree-merge bug (`first-approved-overrides-newer-rejected`, `linearizes-a-branch-already-containing-work`, `union-duplicates-ledger-records…`) came from merge growing a step whose state it then had to reconcile. One read of HEAD has nothing to reconcile.
- No declaration: `merge` refuses and changes nothing. Fix line (ADR 0158, no placeholder; `merge` prints the real absolute tree path): `fix: Operator action: declare this repo's check command as a verify: line in /abs/worktrees/<repo>/<name>/AGENTS.md and commit it in this worktree`.
- This repo declares `verify: ../../../.dadaia/.venv/bin/python scripts/ci.py`. The line replaces `AGENTS.md:16-17` ("run tests from its root …"): DELETE before ADD, with 0185 cited (0151 M3). Every `merge` runs at `worktrees/<repo>/<name>/`.
- Security: the command comes from a tracked line of the HEAD being landed, the same trust as the code it verifies; the reviewer sees any change to it in the diff (SPEC Risks). `merge` passes it no input of its own.

### 6.3 The CI script (AC12.6)

- `scripts/ci.py`, stdlib only (the `repo-hygiene` and `doctor` jobs install no dev group). `python scripts/ci.py [<job>…]` takes `ci.yml`'s Linux job ids and runs all of them when none is given. It prints `PASS <step>` or `FAIL <step>` per step, runs every step, and exits 1 if any step failed. Each tool runs as `sys.executable -m <tool>`.
- Steps, keyed by job: `lint` (`ruff format --check`, `ruff check`, `lint-imports --config setup.cfg --no-cache` on `dadaia_workspace/ tests/ scripts/`); `typecheck` (`mypy --strict dadaia_workspace/ scripts/`); `guards` (`scripts/guards/run.py`, then `--planted`); `unit-fast`; `contract-coverage` (`--cov … --cov-fail-under=80`); `integration`; `e2e-python` (`DADAIA_REQUIRE_UVX=1`, `uv` on PATH); `repo-hygiene` (`.github/scripts/check_no_repo_local_claude.sh`); `doctor` (`-m dadaia_workspace doctor --specs-dir specs`, with `PYTHONPATH` set to the checkout so the worktree's package is judged).
- Each step keeps the job's `-m` selector. Every pytest run uses `-n 2`; random order is `pytest-randomly`, already in the dev group (`pyproject.toml:62`) and active, since nothing passes `-p no:randomly`.
- One source: each Linux job of `ci.yml` keeps its setup steps (checkout, python, poetry, uv) and its run lines become one line, `poetry run python scripts/ci.py <job>` (`python scripts/ci.py <job>` in `repo-hygiene` and `doctor`). Job ids and names stay, so `.github/required-checks.json` is unchanged. The PR-event jobs and the Windows/macOS jobs keep their own lines.
- Guards follow the move: `suite.py`'s `quarantine-needs-bug` (`:158-162`), `repo.py`'s `onboarding-journey-uv` (`:418-434`) and `repo.py`'s `workflow-never-rules` coverage row (`:107-121`, `coverage-file-in-the-checkout`, which would otherwise pass vacuously) read the pytest selectors, the e2e step and the `--cov` run from `scripts/ci.py`; each plant moves into a planted `scripts/ci.py`.
- Runtime: CI at 76d7af604 ran these jobs in about 7 min of job time on 4-vCPU runners, setup included. Locally, at `-n 2` with unit run twice as CI does, the estimate is 8–10 min. T-050-190 logs one local full run and one CI run's wall time in its commit body (SPEC Risks; G4: the Linux jobs move from `-n auto` to `-n 2`).
- Case, new owner file `tests/integration/test_ci_script.py`: in a tmp tree, a planted F401 turns `lint` to exit 1 with `FAIL ruff check`, and a planted failing `@pytest.mark.unit` test turns `unit-fast` to exit 1 with `FAIL unit-fast`. A clean tree's `lint` exits 0. The test does not create a venv.

### 6.4 As-is review per surface and verdict

| surface | as-is at 6b84527bc | bugs / culprits | verdict | Δ prod / test lines |
|---|---|---|---|---|
| test env | `tests/conftest.py` writes the env at import (`:56` bytecode, `:67` `PYTHONPATH`, `:84` fence, `:118` git config, `:121` `TESTS_PARENT_HOME`), at `pytest_configure` (`:445-449` `pin_child_env` + `drop_operator_env`, `_CHILD_HOME` `:429`) and in a session fixture (`:395` `KIMI_CODE_HOME`); `tests/fixtures/harness_env.py` holds `SUITE_DADAIA_ENV` `:104`, `drop_operator_env` `:107`, `pin_child_env` `:221`, `child_keys` `:230`, `base_env` `:235`. Callers: `child_keys` in `tests/helpers/worktree_ws.py:29,74`, `test_gate_dialects_through_wrappers.py:73,172`, `test_hook_interpreter.py:66,129`, `test_core_file_io_purity.py:337`; `base_env` in `test_push_gate_check.py:65`, `test_worktree_lifecycle.py:152`, `test_one_line_bootstrap.py:60,217,317`, `test_onboarding_journey.py:84,228`, `test_push_denylist_journey.py:107`, `test_tool_caches_stay_in_the_tmp_zone.py:70`, `test_registry_version_grammar.py:110`, `harness_env.py:251,325`. `tests/unit/test_conftest_pollution_guard.py:17-53` re-executes the conftest with `SimpleNamespace` configs | 9 registered + rows 14, 16, 17; culprits 09d259133, 4ca3d7136 (i, ii), b69ee15b9, 76d7af604 | REBUILD (AC10.1) | 0 / ≈ −110 |
| merge | `S/dd-gitflow-default/scripts/_worktree_end.py` (270 lines): `sys.path` reach-in `:14` into `dd-release-implementation` for `MARK_RE`/`MARKS` `:16`; `_bare`/`_rank`/`_replayed` `:103-128`; `_rebase` `:131-155` with the already-contains return `:135-136`; `merge` runs `_rebase` before `_check_approved` `:240-241`; the moved-branch arm of the failed fast-forward `:249-254`; no test runs | `first-approved-overrides-newer-rejected`, `linearizes-a-branch-already-containing-work`, `union-duplicates-ledger-records…`; culprits 820bee3b0, 36ce79d7d, 1cfc3b72d, b90c64854 (the reach-in's current form) | REBUILD (AC12.7) + gate 1 (AC12.5) | ≈ −37 / ≈ +20 |
| dead | `f/spec_context/service.py`: `dead(…, commit)` `:711`; preflight `:644-709` with the untracked-consent refusal `:662-669`, the secret refusal `:671-678`, the identity refusal `:696-700`; `commit_all` `:737-738`; push `:739` via `infrastructure/git_subprocess.py:285-296` (plain `git push`, no `--no-verify`: the pre-push hook runs, which confirms SPEC AC12.8's third bullet); `commit_all` `git_subprocess.py:192`; `--commit` `cli/commands/context.py:326-336`; `f/certification/service.py:407` passes `--commit` | 4 fixes in 5 days; culprits 49f9940c7/934377e89 (the auto-sync commit), 92a727a20 (the preflight's commit-only refusals), 1ee8aa30f (secret-refusal hunk) | REBUILD (AC12.8, 0172) | ≈ −65 / ≈ −80 |
| sweep | `f/spec_context/sweep.py` (257 lines): `Skipped(str)` `:52`, `succeeded` `:56`, `_owner` `:97-101`, `worktree_git_dir` `:135-139` (one caller, `service.py:683`), `_writable_retry` `:142-152` re-raising through `func(path)`, `remove`'s except arms `:172-185`, `deleter` `:188-190` (callers `cli/commands/specs.py:52,169` and five test files), `move` raising every non-EXDEV `OSError` `:239-241`; `f/workspace/service.py:133` reads a refused hold, a non-empty `str`, as success | 14 fix commits since 09-24; rows 6, 21–23, 27; culprits 8f329db3a, af2154d5a, b9b28202d | REBUILD U1, U2 (AC12.13) | ≈ −20 / ≈ +15 |
| bugs.py lineage | `S/dd-bug-resolution/scripts/bugs.py`: `_NOT_PRODUCTION` `:56` excludes `tests/` from blame and direction alike (`_own` `:121-128`); blame skips `refactor(T-` `:140`; candidates are bug ids only, via `_fixes` `:89-111`, whose grep `:96` and `_SHAPE` `:53` see only `fix(bugs)`/`chore(bugs): resolve`; `_bugs_check.py:83-92` accepts a `caused_by` naming a record only; schema `caused_by` description `bug-record-v1.schema.json:125-131` says "the bug X" | the 160/211 `none` (§1); audit: 6 of 9 test-surface bugs read `none` | UPDATE (AC9.3, AC12.12) | ≈ +18 / ≈ +40 |
| T-050-168 tests | `tests/unit/core/test_specs_version.py:24-25` (a41c69967 re-pinned key 9; aed2ac322 rewrote the rule comment); `tests/unit/skills/test_bug_resolution_bugs_script.py:828-836` (7196e1473's `startswith`/`endswith`/`in`) | rows 10, 12; row 11's d66e50c66 kept | REBUILD (AC12.9) | +1 / ≈ −4 |
| `_StubDoctor` | `tests/unit/cli/test_exitcode_truthfulness.py:26-37`, monkeypatched over `container.build_doctor_service` `:46` | row 13; culprits 86f4cd992 (stub), 686ec7b40; repair a88d849c4 | DELETE (AC12.10) | 0 / ≈ −5 |
| stdin guard | `scripts/guards/isolation.py:301-318` `_patches_stdin` sees only `setattr("sys.stdin", …)` and `setattr(sys, "stdin", …)`, not `sys.stdin = …` | row 20 (ae8d5b056 wrote the check) | own fix (AC12.14) | +3 guard / plant row |
| sweep rows 24–26 | `linked_worktree` `sweep.py:119-132` takes any gitfile `.git`, so a submodule counts, and `:10` says "(or submodule)"; the expire lane decides linked-worktree in `doctor.py:509` and again in `remove` `sweep.py:167`; `hold` stamps only `len(rel.parts) > 1` `:206-207` and `move` skips `utime` on a link `:248` | rows 24, 25, 26 | own fixes (AC12.14) | ≈ +1, −3, +1 |

- AC10.1 (§6.7 O2): AC10.1 deletes "every env-name set but `suite_env`'s". Read here as the scrub sets `SUITE_DADAIA_ENV` and `ENTRY_SIGNAL_ENV_VARS` and `child_keys`'s tuple. `ALLOWLISTED_DADAIA_ENV`, `HARNESS_CONTROL_DADAIA_ENV` and `_FORBIDDEN_HOOK_ENV` stay: they are the hook-env contract, which guard `harness-env-allowlist` (`isolation.py:23,270`) reads (§1.2).

### 6.5 Per AC: DELETE → REBUILD → UPDATE → KEEP → ADD

- **AC12.6** (T-050-190). UPDATE: `ci.yml`'s Linux run lines become one line each; the two guards read the script. KEEP: job ids, setup steps, cross-OS and PR jobs. ADD: `scripts/ci.py`, which nets against the run lines it absorbs, and its owner test. Δ guard/script lines ≈ +75; `ci.yml` ≈ −5; tests ≈ +40.
- **AC12.5 + AC12.7 + AC10.14 law** (T-050-191). Two commits: (1) `refactor(T-050-191): REBUILD worktree merge — land the approved HEAD, never rewrite (0185)`, holding the reverts and the ancestor-check redo; (2) `feat(T-050-191): gate 1 — merge runs the repo's verify: line (0185)`, holding `_verify`, the `verify:` line and `make_workspace`'s `verify: true`.
  - Culprits: 820bee3b0 (in-merge rebase), 36ce79d7d (marker replay and the reach-in), b90c64854 (its current form), 1cfc3b72d (already-contains return).
  - Reverted (DELETE): `_rebase`, `_replayed`, `_bare`, `_rank`, the `sys.path` line and its import, `fnmatch`, the moved-branch arm `:251-253`, `test_parallel_siblings_replay_task_markers` (0111's replay case), and 1cfc3b72d's `test_a_branch_that_merged_the_work_branch_lands_as_is`.
  - Smallest redo: after `_check_allowed`, `git merge-base --is-ancestor <work> HEAD` else refuse with `fix: git -C <tree> rebase <work>` (`git_line`); then `_check_approved` (0168 carry kept); then `--ff-only`. Commit (2) inserts `_verify(tree)` before the fast-forward; it reads the declaration (§6.2) and refuses on absence or a non-zero exit.
  - KEEP: a8f226c8b's dirty-tree fix line; `REPLAY` is renamed `TASKS_GLOB` (impl's TASKS allowed glob; nothing replays).
  - UPDATE: `pub/data/worktrees-AGENTS.md` rewritten once to AC12.11's bar: step 6 (no rebase; the verify run), step 7 (0180's writer re-run, the law half of T-050-189, cited 0180), and `:44`, which becomes the gate 1 line.
  - ADD: repo `AGENTS.md`'s `verify:` line, the self-declaring case; `make_workspace` in `tests/helpers/worktree_ws.py` commits `verify: true`; AC12.5's and AC12.7's cases as rows in `test_worktree_lifecycle.py`.
  - Body cites 0185 and 0180 (0151 M3). Δ ≈ −37 / ≈ +20.
- **AC9.3 + AC12.12 code** (T-050-192). UPDATE only:
  - Blame reads `tests/` too: `_own` keeps `_NOT_PRODUCTION` for the direction alone.
  - The `refactor(T-` skip leaves; only `(#n)` squashes and `dadaia-generated` files are skipped.
  - A blamed commit whose subject is `<type>(T-…)` proposes that task id.
  - `_fixes` greps `^(fix|chore|refactor)\(bugs\): ` with `_SHAPE` matching `refactor\(bugs\): <id> — `.
  - `_bugs_check.py` accepts a task id that some `specs/releases/**/TASKS.md`, `_archive/` included, carries; the schema's `caused_by` description becomes AC9.3's one semantics.
  - Cases (owner file): AC9.3's four, plus a `refactor(bugs): x — REBUILD u: …` commit that `bugs.py fix x` prints. `feat(T-050-192): …`. Δ ≈ +18 / ≈ +40.
- **AC12.11** (T-050-193). UPDATE `AUTHORING.md` rule 9 (`:20`, `:107`): a prohibition carries a short reason or a bug/ADR id. Δ 0.
- **AC12.1, AC9.3 law** (T-050-194). UPDATE `pub/scaffold/bugs/AGENTS.md:14` ("own mistake" covers only unmerged rework inside a worktree) and `:23`'s `caused_by` semantics (bug or task). The scaffold law is in the stamp canon, so the same commit bumps `CANONICAL_SPECS_VERSION` 9 → 10 (`core/specs_version.py:35`, a `v10 =` line) and pins key 10 (§6.7 O1). Δ +1.
- **AC12.2, AC9.3 law** (T-050-195). UPDATE `LINEAGE.md:29` (blame skips only `(#n)` and `dadaia-generated`; `tests/` included) and `:33-34` (one fix-induced bug triggers a REBUILD: revert plus the smallest redo, one commit; work in flight stops; the ≥ 2 trigger stays; the body names each culprit sha). Phase 0 of `S/dd-bug-resolution/SKILL.md` follows it. Δ 0.
- **AC12.3** (T-050-196). UPDATE `S/dd-release-implementation/SKILL.md:38`: a red that a merged fix caused goes to registration, revert and redo; a flaky red is quarantined with a bug. Δ 0.
- **AC12.12 law** (T-050-197). ADD one §3a row to `S/dd-gitflow-default/SKILL.md`: `refactor(<task-id>): REBUILD <unit> — …` in `impl`, `refactor(bugs): <bug-id> — REBUILD <unit>: …` in `bug`. Δ 0.
- **AC9.4, AC12.6 and AC12.12 review lines** (T-050-198). UPDATE `S/dd-code-review/SKILL.md:55`: a `caused_by` other than `none` means the review reads every line the prior fix wrote and checks the revert, and "nothing gates it" leaves. ADD two lines: (1) the verdict carries the `verify:` output for its sha and names Windows-only and macOS-only risk as unverified; no output means no APPROVED. (2) No APPROVED on a `refactor(...)` that deletes tests without an approved REBUILD verdict in the SPEC. Δ 0.
- **AC12.4** (T-050-199). One `bug` worktree, `specs/bugs/BUGS.jsonl` only:
  - one `chore(bugs): report …` commit: 27 `append`s, their `update --set caused_by=…`, and the two repairs;
  - one shape-4 `chore(bugs): resolve <slug> — retro repair (<sha>[, <sha>])` per sha row (1–5, 7–9, 11, 15, 18, 19), with `--lineage-reason "retro: repaired by <sha>"`;
  - the AC rows (6, 10, 12–14, 16, 17, 20–27) stay open. Δ 0.
- **AC10.1** (T-050-200). One REBUILD commit: `refactor(T-050-200): REBUILD test session env — one suite_env, applied once at pytest_configure`.
  - Culprits: 09d259133 (the pin and the `base_env`/`child_keys`/`pin_child_env` trio), 4ca3d7136 (i, ii: the fake-session coupling and the configure-time pin hunks), b69ee15b9 (the in-process heartbeat line), 76d7af604 (its conftest hunk).
  - Reverted, and DELETE: every env write in `tests/conftest.py` outside `pytest_configure`; `pin_child_env`, `child_keys`, `drop_operator_env`, `base_env`, `SUITE_DADAIA_ENV`, `ENTRY_SIGNAL_ENV_VARS`, `_CHILD_HOME`, `TESTS_PARENT_HOME`; `_FORBIDDEN_HOOK_ENV` moves into `suite_env`, the only reader left once `base_env` is deleted; the `SimpleNamespace` re-execution in `test_conftest_pollution_guard.py`.
  - Redo: a pure `suite_env(parent, home) -> dict[str, str]` in `tests/fixtures/harness_env.py` returning the whole suite env (temp `HOME`/`USERPROFILE`/`XDG_CACHE_HOME`/`LOCALAPPDATA`, `PYTHONDONTWRITEBYTECODE=1`, the fence, `PYTHONPATH`, `GIT_CONFIG_GLOBAL`, `KIMI_CODE_HOME`; every `DADAIA_*` and every `_FORBIDDEN_HOOK_ENV` name out except `DADAIA_REQUIRE_UVX` and `DADAIA_FENCED_ROOTS`, today's `SUITE_DADAIA_ENV`; no second entry-signal list). `pytest_configure` applies it once with `os.environ.clear(); os.environ.update(…)` in the controller and in each worker. Every child env is `suite_env(...) | overrides`, or the inherited `os.environ`.
  - The tripwire (`pytest_sessionfinish`) reads the parent `HOME` that `suite_env` received.
  - KEEP: the heartbeat as a hook subprocess (76d7af604), and `python_env.py`'s `-B` (row 15).
  - ADD: `pytester` (built in), enabled by `pytest_plugins` in the conftest.
  - Cases: the `suite_env` parametrize row and AC10.1's two `pytester` runs, in `test_conftest_pollution_guard.py`.
  - Δ 0 / ≈ −110. Rows 14, 16, 17 resolve by shape 4 citing its sha.
- **AC12.8** (T-050-201). One REBUILD commit: `refactor(T-050-201): REBUILD context dead — it never commits (0172)`.
  - Culprits: 49f9940c7/934377e89, 92a727a20, 1ee8aa30f's secret hunk. 49f9940c7 is a 432-file squash and cannot be reverted directly, so the body states that the deletion is its revert: the auto-sync lines it wrote leave by hand, with nothing else of it touched.
  - DELETE: `commit_all` (`git_subprocess.py:192`) and its call; `--commit` and `dead(commit=…)`; `DeadSecretFoundError`; the untracked-consent and identity refusals; the `--commit` that `certification/service.py:407` passes.
  - Redo: a dirty or untracked repo refuses with one fix line per file and touches nothing. The line uses ADR 0158's operator form with the real path: `Operator action: move /abs/repos/<r>/<f> into a worktree and commit it there, or discard it`. It is never a runnable discard: a `checkout --` or `rm` line would destroy hand edits, the class of the resolved CRITICAL `context-dead-secret-fix-line-stashes-what-dead-then-destroys`. The choice stays the operator's (0172). The non-work-branch refusal stays only for unpushed commits on HEAD (0056 g, as 0172 amends it).
  - KEEP: `unrecoverable()`'s stash count, `identity_fix` for baseline, and the push through the pre-push hook.
  - The 0154 writers (§6.7 O3): `context create` clones. `specs init` (`cli/commands/specs.py:175-176`) commits the files it wrote via `commit_paths` in its own act. The audits writer, `S/dd-audit-project/scripts/audit.py` with `_audit_store.py`, commits what its verbs `disposition` and `close` write. Shape: §3a has no row for a direct `specs/audits/` write. These commits use `chore(audits): <verb> <audit> — …`, the conventional form of the §3a ledger rows. A §3a row for it is left for the operator to rule (logged at closure, not invented here). `context baseline`'s `commit_paths` (`service.py:575`) is then left with only what neither of those wrote.
  - `docs/cli.md` is re-rendered by `help tree`. Cases: 0172's `measured_by`; no refusal line contains `checkout --` or `rm`. Δ ≈ −59 / ≈ −70.
- **AC12.13** (T-050-202). One REBUILD commit: `refactor(T-050-202): REBUILD sweep delete path and result protocol — judged by outcome, a refusal is falsy`.
  - Culprits reverted: 8f329db3a's `_owner` leftover; af2154d5a's try/except arm and owner text, keeping its EXDEV `kept` return; b9b28202d's `OSError` arm.
  - Redo U1: one `onexc` that never raises (chmod, one retry, the first failing path recorded in a list local to the `remove` call); file unlinks go through it; `remove` judges by `occupied(target)` and refuses naming the recorded entry and its parent's owner. A permission failure alone prescribes the operator act (row 22).
  - Redo U2: `Skipped` becomes a falsy result whose text is read only through `str()`; a success is truthy; `succeeded` and `deleter` are deleted (callers `specs.py:52,169` pass `lambda p: sweep.remove(root, p, p.name)`); `move` returns its `os.replace` failure as a refusal.
  - `worktree_git_dir` moves to `service.py`. Row 23 (`workspace/service.py:133`) is fixed by U2 with no line changed there. Row 27's hold loop (`service.py:743-746`) refuses with a fix line once `move` stops raising.
  - KEEP: the TTL walk, `-N`, `_inside`, `walk`, `lstat`.
  - Cases: SPEC AC12.13's seven. Δ ≈ −20 / ≈ +15.
- **AC12.9** (T-050-203). One REBUILD commit: `refactor(T-050-203): REBUILD T-050-168's tests — the stamp bumps, the refusal line is compared whole`.
  - Culprits: a41c69967 and aed2ac322 (reverted: key 9 goes back to its original fingerprint `bf25e8106cf60674` beside key 10, and the rule comment "re-pinned only together with a stamp bump" returns), 7196e1473 (reverted: the predicates).
  - Redo: the refusal row builds its expected fix line per platform and compares `stderr` lines for equality. The real bump is T-050-194's commit (§6.7 O1).
  - KEEP: d66e50c66. Δ 0 / ≈ −4. R13, after T-050-194, restamps this repo's tree.
- **AC12.10** (T-050-204). One REBUILD commit: `refactor(T-050-204): REBUILD the doctor exit-code test — the real DoctorService`.
  - Culprits: the stub's author 86f4cd992 and 686ec7b40; a88d849c4 is the repair.
  - DELETE: `_StubDoctor` and the monkeypatch.
  - Redo: the tmp workspace the test already writes gets a real `.dadaia/nonsense` (ROOT-4), so the cases keep their expected exit codes.
  - Δ 0 / ≈ −5.
- **AC12.14** (T-050-205 … 208). Shape 3 each, RED first. Row 20: a planted `sys.stdin = io.StringIO()` row in `isolation.py`'s plants, then `_patches_stdin` matches the `Assign`. Row 24: `linked_worktree` requires the gitdir to resolve under `<common>/worktrees/`, and `:10` drops "(or submodule)". Row 25: the lane passes its one decision to `remove`, and the second walk leaves. Row 26: `hold` stamps a root-level link with `os.utime(…, follow_symlinks=False)`. Δ ≈ +2 prod, +3 guard.
- W12 production Δ ≈ −37 + 18 − 65 − 20 + 1 + 2 ≈ −101 (O3's two commits are counted in T-050-201's Δ), which widens §2.8's 57-line margin to ≈ 158. Test lines ≈ −84. `scripts/ci.py` counts with the guard lines (+75).

### 6.6 Schedule (machine limit: ≤ 2 test-running agents, `-n 2`; ADR 0149)

| step | tasks | width | how |
|---|---|---|---|
| W1 | T-050-190 | 1 | impl; today's merge |
| W2 | T-050-191 | 1 | impl; old merge code; R14 follows |
| W3 | T-050-192, T-050-193 | 2 | impl each |
| W4 | T-050-194, T-050-195 | 2 | impl each; R11 and R13 after both |
| W5 | T-050-196, T-050-197 | 2 | impl each |
| W6 | T-050-198 | 1 | impl |
| W7 | T-050-199 | 1 | bug; ledger only |
| W8 | T-050-200 | 1 | impl; alone (its `W:` spans the suite) |
| W9 | T-050-201 | 1 | impl; then its rows' shape-4 tail |
| W10 | T-050-202 | 1 | impl (`service.py` after 201) |
| W11 | T-050-203, T-050-204 | 2 | impl each |
| W12 | T-050-205, T-050-206 | 2 | bug each |
| W13 | T-050-207 | 1 | bug |
| W14 | T-050-208 | 1 | bug |

- Every `WT merge` now runs the full Linux suite (§6.3), so merges land one at a time. Two worktrees are open together only where their `W:` are disjoint except for the derived `behavior-map.json`/`shipped-hashes.json` and the ledgers.
- Docker work (T-050-185, T-050-186 image builds) runs alone, with no other test-running agent, once the pause lifts. The paused tasks then follow §5 steps 7–10 at width ≤ 2.
- Each REBUILD's AC rows resolve in one `bug` worktree after its merge (shape 4, `by T-050-NNN (<sha>)`): 200 → 14, 16, 17; 202 → 6, 21, 22, 23, 27; 203 → 10, 12; 204 → 13.
- Release-worktree steps added to §2.7:
  - R11: `docs(specs): re-render specs/*/AGENTS.md from the scaffold — T-050-194`; the repo copy already drifts at `specs/bugs/AGENTS.md:23,49`.
  - R12: `chore(adrs): repair measured_by of 0180`, only if T-050-191 renames `test_in_place_ledger_change_refuses_at_rebase`.
  - R13: `chore(specs): restamp the tree to v10 — T-050-194` (precedent c4471aee8).
  - R14, after T-050-191 merges and before T-050-192 opens: `.dadaia/.venv/bin/dadaia public stage`, `public install`, `public doctor` clean, re-projecting gate 1 into the instance. No commit (instance only); its doctor output is logged in the next handoff.
- Critical path: 190 → 191 → 192 → 194 → 198 → 199 → 200 → 201 → 202 → 203 → 206 → 207 → 208 = 13 merges, each ≈ 8–10 min of verification.

### 6.7 Points answered via inspection (main thread, 2026-10-04)

- O1, stamp vs order. Answered via inspection: the stamp rule "re-pinned only together with a stamp bump" predates T-050-168 (aed2ac322 rewrote it), so a canon change bumps. T-050-194 bumps to 10 in the same commit as its canon change; no reorder and no re-pin are needed. T-050-203 only reverts a41c69967's re-pin and aed2ac322's comment, so key 9 returns to its original fingerprint and key 10 pins the new canon. AC12.9's bump is delivered by T-050-194's commit.
- O2, AC10.1's name sets. Answered via inspection: only the scrub sets leave (`SUITE_DADAIA_ENV`, `ENTRY_SIGNAL_ENV_VARS`, `child_keys`'s tuple). `ALLOWLISTED_DADAIA_ENV` stays because guard `harness-env-allowlist` reads it (0176, `isolation.py:23`). `HARNESS_CONTROL_DADAIA_ENV` stays because the hook helpers read it (`harness_env.py:259,332`). `_FORBIDDEN_HOOK_ENV`'s only reader, `base_env`, is deleted, so `suite_env` absorbs it as its scrub list, keeping `DADAIA_REQUIRE_UVX` and `DADAIA_FENCED_ROOTS`.
- O3, the 0154 writers. Answered via inspection from the accepted ADR 0172. Its decision says "Each sanctioned direct writer of ADR 0154 leaves its output committed in the act that writes it", and its consequences say "specs init and the audits writer each gain the commit of their own output". T-050-201 adds both: `specs init` and the audits writer (`S/dd-audit-project/scripts/audit.py`, which exists as code) commit their own output.
- O4, AC12.14 vs AC12.2. Answered via inspection from Q24's explicit own-fix ruling ("H4, H5 e H6 ganham correção própria no rc-8, cada uma com teste vermelho primeiro"). T-050-195 lands AC12.2 before 205–208, so Q24 is the reason, not timing. Rows 24–26 are shape-3 fixes whose body says `rebuild: none — Q24`.
