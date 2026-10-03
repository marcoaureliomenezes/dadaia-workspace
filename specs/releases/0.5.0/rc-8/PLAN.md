# PLAN — Release: 0.5.0

**Status:** Draft
**Release ID:** 0.5.0
**Owner:** dd-software-engineer

Candidate 8 — W8: the test law and the library pipeline leave; W9: bug lineage derived; W10: the open bugs (ADR 0140). SPEC AC8.1–AC8.10, AC9.1–AC9.5, AC10.1–AC10.13, Approved at 3f48e11dd. Paths are relative to `dadaia_workspace/` (`f/` = `features/`, `pub/` = `public/`, `S/` = `pub/skills/`) unless they start with `tests/`, `scripts/`, `specs/`, `docs/`, `.github/`, `README.md`, `AGENTS.md`, `CONTEXT.md`, `pyproject.toml`, `poetry.lock` or `setup.cfg`.
As-is read at `wt/0.5.0b-release` 3f48e11dd; the G1 `<start>` readout equals the birth readout (8f4ed785f): 25,307 production lines / 1,233 test functions / 45,464 test lines / 0 guard lines / 0 guard checks.

## 1. As-is review

Bug history read (permanent architecture review), copied from the product engineer's handoff `2026-10-03T135506Z-dd-product-engineer-rc8-spec-rereview-2-applied`:
- Preflight fix chain: `ci-preflight-unusable-outside-the-source-repo` got a refusal (symptom patch), then `preflight-doctor-judges-instance-state-ci-never-sees`; `ci-preflight-writes-coverage-into-the-repo` is open. Cause: a verb serving only this repo; AC8.9 deletes it.
- `surface: tests`: 67 records, 14 naming a prior bug; F018: 22% fix-induced, many from meta-tests.
- 128 of 237 `fix(bugs):` commits, 2026-08-23..2026-10-02, remove an assert (`git log -E --grep='^fix\(bugs\): ' fb8a29a75`, each through `git show -U0 -- tests | grep -E '^-\s*assert'`). Cause: `dd-bug-resolution` Phases 5-6, which W9 deletes.
- 160 of 211 resolves closed 2026-09-15..2026-10-03T01:46:48Z (the last `closed_at` at fb8a29a75; same at 196f611aa) judge `caused_by: none`; `bc135641c` repaired 6. Command: `git show fb8a29a75:specs/bugs/BUGS.jsonl | jq -s '[.[]|select(.status=="resolved" and .closed_at>="2026-09-15")] | length, ([.[]|select(.caused_by=="none")]|length)'` prints 211 then 160.
- Size ceilings outlived 0143 twice (a89a557ce; `skill_md_line_ceiling`): its `measured_by` greps symbols.
- 7 resolved records on test-child env; `harness_env.py` is not the only builder (AC10.1).
- `session-start-bound-session-omits-onboarding-next-step` preceded `onboarding-next-step-names-another-context`; the as-is review undoes the cross-context walk if it introduced it.
- T-050-133 verifies `evidence_seam`/`evidence_diff`, 40% stale; 0164 (4) retires both.

Ledger slice read here (735 records at 3f48e11dd; title/id/component match; `bugs.py status` lists 11 open):
- preflight 28 records, 1 open; meta-test/ratchet 16, 0 open, 5 naming a prior bug (`frozen-clock-ratchet-scans-tests-tmp-scratch-dir` after its own ratchet; `mutation-baseline-wiring-test-flakes…`, `…-cannot-collect` after the mutation tooling); child env 10, 1 open, 4 linked; coverage 8, 2 open, 3 linked; next-step 14, 1 open, 3 linked; registry schema 5, 1 open; reconcile/pre-push 16, 1 open; backlog anchor 10, 0 open; release memory 3, 1 open.
- The cross-context walk was not introduced by a fix: `next_step`'s `for name in [*names, *trees]` is T-050-17's (97784f9ef); T-048-07's fix (27eadade4) put the focus first and kept the walk, a symptom patch. AC10.4 deletes the walk.
- `onboarding`, `ci_preflight`, `python_env` and the meta-tests each carry ≥ 2 prior fixes: every one leaves (DELETE) or is rebuilt below.

| unit | today | bugs | verdict | why |
|---|---|---|---|---|
| `f/ci_preflight/` (165 lines); `cli/commands/ci.py` `preflight`; `core/exceptions.CiPreflightScopeError`; `container.is_source_repo_root`; `infrastructure/subprocess_runner.subprocess_runner_for_ci`; `infrastructure/python_env._ensure_ci_toolchain` | runs this repo's CI ladder from the shipped CLI; bootstraps pytest into every workspace venv | 28, 1 open | DELETE | AC8.9; a library verb serving only its own repo; `workspace_guardrail._is_source_repo_root` stays (`public_assets`) |
| `f/backlog/subject_registry.py` code anchors (`_module_top_level_symbols`, `_grep_top_level_symbols`, `rglob("*.py")`); `SubjectKind.CLI`, `cli_anchors` threading (`cli/commands/doctor.py:126`, `f/backlog/doctor.py`) | a `code` anchor is a Python `path#symbol`; `cli` binds `dadaia <command>` | 10, 0 open | REBUILD | ≥ 2 bugs; a `code` anchor becomes any tracked path, `#symbol` optional, judged by a word grep; the `cli` kind leaves (only the library's own CLI) |
| `core/workspace_layout.REPO_TREE_ARTIFACTS` (Python/JS caches); `privacy_check._PUBLIC_ASSET_IGNORED_DIRS` | doctor reaps tool caches in every consumer repo | — | DELETE | `REPO_TREE_EXCLUDED` becomes `(".dadaia",)`; the public walk ignores `__pycache__` only (caches redirect by config, 0080) |
| `S/dd-spec-navigator/scripts/_memory_drift.CODE` (12 suffixes) | a unit is a dir holding a listed-language file | — | DELETE | every tracked file outside `NOT_CODE` and dot-dirs is code |
| `hooks/venv_guard.py:48` | names pytest/ruff/mypy | — | DELETE | sentence leaves; behaviour unchanged |
| `S/dd-test-stewardship/`, `pub/templates/tests-AGENTS.md`, wiring (`workspace_layout.REPO_LAW:71`, `f/specs/canon.py`, onboarding list, `f/specs/doctor_memory.py`, persona `skills:`, `behavior-map.json`, CONTEXT-MAP rows) | test lifecycle law shipped to every consumer | — | DELETE | AC8.1, 0166 |
| `pub/data/AGENTS.md` §1 bullets; `pub/data/fixed/slop-tests.md`; `pub/scaffold/memory/QUALITY.md` | point at the stewardship skill and `Intent:` | — | UPDATE | the five test basics rewrite existing bullets (8,293 B; must not grow) |
| `S/dd-release-implementation/MEMORY-UPDATE.md` | states its own canonical-memory rule | — | UPDATE | AC8.2: points at the memory law |
| `tests/contract/test_stewardship_mechanics.py`, `test_test_suite_ratchets.py` | P-21/22/28 and V26/V28–V31 in pytest | 5 linked | DELETE (V28/29/31) + move | P-21, P-22, P-23, P-28 become guard checks; V28/29/31 leave with `Intent:` |
| `tests/integration/test_repo_self_scan.py`, `tests/contract/test_source_repo_hygiene.py`, `test_adr_canon.py` committed-ledger case | duplicate gitleaks/pre-push, the CI hygiene and doctor jobs | — | DELETE | AC8.3 duplicates |
| `tests/scripts/run_mutation_baseline.sh`, `tests/integration/scripts/test_run_mutation_baseline_wiring.py`, `tests/contract/test_mutation_baseline_scope_stdlib_only.py`, `[tool.mutmut]`, group `mutation` | release mutation baseline | 2 linked | DELETE | operator tooling now (private `mutation-diff`) |
| `test_slop_ratchets.py`, `test_import_linter_ignore_cap.py`, `test_suite_cannot_reach_a_real_workspace.py`, `test_suite_cannot_reach_the_instance.py`, `test_frozen_clock_aging_ratchet.py`, `test_harness_env_contract.py`, `test_ci_workflow_hygiene.py`, `test_memory_canonical_shape.py`, `test_version_lineage_consistency.py`, `test_release_semver_canon.py` release-please cases, `test_adr_canon.py` superseded-successor case | meta-tests in pytest | 5 linked | REBUILD | ≥ 2 bugs (xdist races 465, 467): one guard per check, tracked files only |
| `S/dd-bug-resolution/scripts/_bugs_transition.py` `REQUIRED_BY_VERB`, `_EVIDENCE_DIFF_RE`, `_SEAM_RE`, `_seam_exists`; `bugs.py` stats `direction`; schema `evidence_*`; SKILL Phases 5–6; `LINEAGE.md`; `S/dd-audit-project/PILLAR-BUGS.md` rows 26, 27, 44, 45 | verifies two hand-written evidence fields, 40% stale; direction from prose | `bugs-check-trusts-evidence-fields-unverified` and the 160/211 `none` | REBUILD | 0164: the fix commit and its numstat are derived from git; `caused_by` proposed by blame |
| `tests/fixtures/harness_env.py` + 15 ad-hoc env copies; `tests/conftest.py` bytecode | children inherit HOME and write bytecode | 10, 1 open | REBUILD | one builder |
| `pyproject.toml [tool.coverage.run]`; `ci.yml` `COVERAGE_FILE` (2); hook subprocesses | two deciders; hooks never measured | 8, 2 open | REBUILD | `data_file` and `patch = ["subprocess"]` (coverage 7.14.1, no new dependency) decide alone |
| `f/workspace/onboarding.next_step`; callers `cli/commands/context.py`, `cli/commands/doctor.py`, `hooks/ctx_inject.py` | walks every ALIVE context after the focus | 14, 1 open | REBUILD | one context judged |
| `infrastructure/python_env.version_change` | reuses a venv by build identity alone | 1 open | UPDATE | adds the prefix/shebang location test to the one decider |
| `core/context_registry.entries`, `infrastructure/json_context_store.py` | a row missing a key raises `KeyError` | 5, 1 open | UPDATE | the one parse raises `SchemaVersionError` |
| `core/gitflow.py:133` | warns "no gitflow block" when the tree is absent | 15, 1 open | UPDATE | names the absence and `specs init` |
| `f/reconcile/service._snapshot_state`; `f/spec_context/service.install_git_hooks` | scratch copy under `.dadaia/tmp/reconcile/`; unconditional hook rewrite | 16, 1 open | REBUILD | snapshot held in memory (scratch deleted); rewrite only on differing bytes |
| `f/spec_context/doctor.py` HOOKS-DRIFT-1 | always "differs" | — | UPDATE | names absent or differing |
| `S/dd-release-implementation/scripts/release.py` `_memory` | appends a second `kind: memory` entry | 3, 1 open | UPDATE | rerun is a no-op |
| `pub/schemas/bugs/bug-record-v1.schema.json#surface` | documents a deleted regex | 1 open | UPDATE | AC10.10 |
| `scripts/guards/` | — | — | ADD | no unit can carry a check whose subject is the repository; nets against the 14 meta-test files above |
| `pub/entities/behavior-map.json` `skill_md_line_soft`, doctor `SKILL-MD-LENGTH` | — | — | ADD | 0170; nets against CONTEXT-MAP's Budget and Measured columns |
| `CONTEXT.md` four terms | — | — | ADD | AC8.7; nets against the SCAFFOLD homonym entry |

### 1.1 Authorities

| question | authority | consults | deleted |
|---|---|---|---|
| how this repo's CI runs locally | `.github/workflows/ci.yml` + `AGENTS.md` (repo) dev-group line | the operator, CI | `ci preflight`, `f/ci_preflight/`, `_ensure_ci_toolchain` |
| what a backlog `code` anchor resolves to | `f/backlog/subject_registry.py` (tracked path, optional word) | `backlog.py check`, BL-SCHEMA | the ast symbol walk, `SubjectKind.CLI` |
| what a repo tree must not carry | `core/workspace_layout.REPO_TREE_EXCLUDED` (`.dadaia`) | `f/spec_context/doctor._scan_repo_trees`, §5.3 render | `REPO_TREE_ARTIFACTS` |
| which test basics bind | `pub/data/AGENTS.md` (root map) | slop-tests, QUALITY scaffold, personas | `dd-test-stewardship`, tests-AGENTS template, `Intent:`, V28, V29, V31 |
| what canonical memory may change at closure | `pub/scaffold/memory/AGENTS.md` | `MEMORY-UPDATE.md` | MEMORY-UPDATE's own rule |
| whether a repository-subject invariant holds | `scripts/guards/run.py` `CHECKS` | the `guards` CI job, 0176's `Measured by` lines | the moved pytest files |
| which files a guard check reads | `scripts/guards/run.py` `tracked()` (`git ls-files`) | every guard check | each file's walker |
| how long a SKILL.md may be | `behavior-map.json` two keys | doctor `SKILL-MD-LENGTH`, `test_behavior_map.py` | CONTEXT-MAP Budget column |
| whether a size is pinned | guard check `no-size-pin` | 0143's repaired `measured_by` | 0143's symbol grep |
| which commit fixed a bug, and its direction | `bugs.py fix` (git grep of shapes 3/4, numstat) | `stats`, LINEAGE.md, PILLAR-BUGS rows 27, 45 | `evidence_diff` direction, `git log -S` recipe |
| which bug caused this one | `bugs.py resolve` blame candidates | LINEAGE.md, bugs law, schema | an unreasoned `none`, `evidence_seam` verification |
| a test child's environment | `tests/fixtures/harness_env.py` builder | every subprocess test | `os.environ.copy()` copies |
| where coverage data lands | `pyproject.toml [tool.coverage.run]` | CI, `tests/README.md`, `tests/AGENTS.md` | `ci.yml` `COVERAGE_FILE` lines |
| which context a run judges | the bound context or `--context` (`onboarding.next_step` one tree) | doctor, SessionStart, `context` CLI | the cross-context walk |
| whether a workspace venv is reusable | `python_env.version_change` | `init` | — |
| whether a registry row is readable | `core/context_registry.entries` | the store, doctor | the store's `KeyError` path |
| whether `init` rewrites a pre-push hook | `f/spec_context/service.install_git_hooks` (bytes) | `init`, `ci install-hook` | the unconditional rewrite |

### 1.2 Reviewer INFO notes, resolved

- `ALLOWLISTED_DADAIA_ENV` and `HOOK_MODULES` stay in `tests/fixtures/harness_env.py`, their one owner (the builder raises on them). The guard check reads both literals with `ast.literal_eval` of the fixture's source and imports nothing from `tests/`; `HOOK_MODULES` is checked against `dadaia_workspace/hooks/*.py` so a stale literal is red.
- The frozen-clock and V26 checks keep "tracked files only": `run.tracked()` is the one enumerator (bugs 465 `v26-ratchet-scans-tests-tmp-scratch-dir-xdist-race`, 467 `tests-tree-walkers-outside-the-ratchets-still-race-the-xdist-quarantine-probe`); a planted untracked `tests/tmp/x.py` stays out.
- 0020's repair drops `tests/contract/test_harness_env_contract.py` (its check is a guard, named by no principle).
- `tests/helpers/scan_population.py:17-18,40-42` loses the moved files in T-050-160; `tests/fixtures/harness_env.py:48` names the guard check id; `tests/contract/README.md:39` is rewritten in T-050-153, its inventory table deleted (a roster of the directory).

## 2. Design

### 2.1 AC8.9 first: the CLI ships no pipeline (T-050-153, T-050-154)
- 153 deletes every unit of the first row, its tests (9 files, 837 lines, 16 functions) and every line the AC8.9 grep names, except files a later task deletes whole (`test_stewardship_mechanics.py`: 156; the mutation script and its wiring test: 155). `docs/cli.md` is re-rendered by `dadaia help tree` (P-29). `test_python_env.py:85-93` asserts no pytest install. Repo `AGENTS.md` gains `poetry install --with dev` into the workspace venv (nets against `_ensure_ci_toolchain`).
- 154 rebuilds anchors and the repo-tree list (§1 rows 2–5); the schema's `code` pattern drops the mandatory `#symbol`; scaffold backlog law §4.1 rows rewritten; `test_tool_caches_stay_in_the_tmp_zone.py` gains the `pytest` row.
- Δ prod ≈ −280 (153), −110 (154).

### 2.2 W8 law (T-050-158, T-050-162)
- 158: AC8.1 deletion and wiring (`REPO_LAW`'s tests row, doctor `AGENTS-PLACEHOLDER-1` and its rule row leave with the template); root-map basics in existing bullets; AC8.2; AC8.7. Δ prod ≈ −40. AI-entity change: `dd-ai-eng-knowhow` AUTHORING, AI-surface lens, `public stage && public install && public doctor`. No task after 158 writes `Intent:`.
- 162: AC8.5 rule `SKILL-MD-LENGTH` (WARNING, one `Operator action:` naming the path and the split); CONTEXT-MAP loses Budget and Measured (AC8.4's column) and its re-record lane.

### 2.3 Guard scripts (T-050-155, 156, 159–161)
- Glob for G1: `scripts/guards/*.py`. `run.py` holds `tracked()`, the `CHECKS` registry built from every sibling module's `CHECKS` dict (no edit to `run.py` per module), `python scripts/guards/run.py` (all, exit 1 on any red, the log names each check id) and `--planted` (each check over its planted violation in a temp tree, red required). No path or id contains `test_` + an old name or `model_api`.
- Modules and ids: `suite.py` (156): `private-import-ratchet` (V26, P-23), `tier-timeout` (P-21), `quarantine-needs-bug` (P-22), `marker-set-closed` (P-28). `slop.py` (159): `v32`…`v40` rows as one id each, `ignore-cap` (P-10), `features-modules-equal-packages` (P-07), `no-size-pin` (AC8.6). `isolation.py` (160): `no-real-workspace`, `no-instance-reach`, `frozen-clock`, `harness-env`. `repo.py` (161): `no-model-api-in-ci` (P-33), `release-workflow-canon` (P-30), `memory-canonical-shape` (P-32), `adr-superseded-successor`, and each remaining `ci_workflow_hygiene` row as its own id.
- CI: one job `guards` in `ci.yml` runs `run.py` then `run.py --planted`; lint and mypy jobs add `scripts/` (156). Pytest leaves `--cov` alone.
- Δ: test lines −2,500, guard lines ≈ +1,200; functions −60, checks ≈ +25.

### 2.4 AC8.4 behaviour asserts (T-050-163, T-050-164)
- Candidate files found by `.md` read + long-string `in` assert at 3f48e11dd (list in TASKS); each assert becomes exit code, effect or stable id, or leaves with its reason in the body. The two `len(…) == NN` pins leave with their files (159, 161). Δ tests ≈ −250 lines, −8 functions.

### 2.5 W9 (T-050-165, 167, 168)
- 165 DELETE first: Phase 5 "rewritten", Phase 6 "net ≤ 0"; `REQUIRED_BY_VERB["resolve"]` drops `evidence_seam`, `evidence_diff`; `_EVIDENCE_DIFF_RE`, `_SEAM_RE`, `_seam_exists` and the `check` re-reads leave; schema keeps both properties optional; PILLAR-BUGS row 26 counts `evidence_loop`, row 44 loses its clause; §3a row 4 widens (AC9.5).
- 167 ADD `bugs.py fix <id>`: `git log -E --grep='^fix\(bugs\): .*<id>'` else the `(<sha>)` of shape 4; prints sha, test files, numstat; `stats` `direction:` reads it. Nets against the `direction` row's `evidence_diff` split, `_EVIDENCE_DIFF_RE` (165) and LINEAGE's `git log -S` recipe.
- 168 ADD blame: `resolve` runs `git blame` on lines the staged diff removes, skips the projection's regenerated files, `(#n)` squashes and `refactor(T-…)`; refuses a `--caused-by` outside the candidates and `none` with candidates, unless `--lineage-reason` (stored, optional schema property). Nets against `_seam_exists`/`_SEAM_RE` and the `evidence_seam` requirement (165), LINEAGE step 3. AC9.4 in `dd-code-review`.
- Δ prod ≈ −25, +22, +35.

### 2.6 W10 (T-050-169–179), each a `bug` worktree
- One `fix(bugs): <id> — <cause>` commit per bug, its RED a parametrize row in the owner file, red loop in the body, `--caused-by` from 168's candidates. AC10.11 resolves by citation at 181.
- 173 (AC10.2): `[tool.coverage.run] data_file = "../../.dadaia/tmp/coverage/.coverage"` (the 0080 cache path) decides; `ci.yml`'s two `COVERAGE_FILE` lines and `repo.py`'s coverage-file check leave. 178 (AC10.3): `patch = ["subprocess"]`; the cost case counts fake-boundary calls per hook lane at two workspace sizes. Nets: 178's case against nothing in its unit — no unit measures 0118's cost bound; counted in G1.

### 2.7 Release-worktree steps (serial, `release` kind)
| step | after | commit |
|---|---|---|
| R1 | 154 | `chore(adrs): repair measured_by of 0080 — test_tool_caches_stay_in_the_tmp_zone.py for test_no_pollution.py` |
| R2 | 156 | `chore(adrs): repair measured_by of 0070` (guard `private-import-ratchet`) |
| R3 | 159 | `chore(adrs): repair measured_by of 0016, 0017, 0052, 0071, 0143` (0143: `no-size-pin`, AC8.6) |
| R4 | 160 | `chore(adrs): repair measured_by of 0020, 0088` (0020 drops `test_harness_env_contract.py`) |
| R5 | 161 | `chore(adrs): repair measured_by of 0021, 0023, 0025, 0049, 0078` (0023 drops `RELEASE-TREE-MEMORY`) |
| R6 | 153–161 | `docs(memory): … (ADR 0138)` truth corrections, SPEC AC8.10's lines; the `slop-tests` fixed block re-rendered from 158's source |
| R7 | R6 | operator only: `docs(adr): accept meta-test-principles-guard-checks` with the nine `### P-NN` hunks, `amends: 0167` |

- Each repair commit cites the merged task sha; each repair runs before the next task in that chain opens. R7's `measured_by` grep prints nothing before it is offered. T-050-180 re-derives `docs/bug-ledger-lessons.md` after R7 (precedent T-050-150).

### 2.8 Delta summary (a readout, ADR 0142)
- Prod ≈ −280 −110 −40 +20 −25 +22 +35 −10 +15 (W10 rest) ≈ −373 → ≈ 24,934: about 129 lines above the SPEC's ≤ 24,805. Not hidden: §4 names it; 181 measures.
- Tests: functions + checks ≈ 1,233 − 98 + 25 ≈ 1,160 (≤ 1,167); lines + guard lines ≈ 45,464 − 3,460 + 1,200 ≈ 43,200 (≤ 43,232).

## 3. Test strategy

- RED first, at the lowest level, in the owner file (0146 (5)); a new file only for `scripts/guards/*.py`, whose `--planted` mode is its RED.
- A literal expected value; behaviour asserts only (exit code, effect, stable id); mock only at the boundary; a fix commit never rewrites an old assert — rewriting one is its own commit with a reason (AC9.1).
- Private test stack (`~/.claude/rules/private-test-stack.md`), every task: each new or changed test passes the test-audit authoring gate (`~/.claude/plugins/cache/claude-settings/test-audit/1.0.0/skills/test-audit/SKILL.md`); each change to non-test Python runs `mutation-diff` (`~/.claude/skills/mutation-diff/SKILL.md`) on the worktree before commit. Every commit touching `.py` carries `test-audit:` and `mutation:` lines.
- A DEL's dead tests leave in its commit (G5); a deleted test maps to a guard check or a behaviour assert, or its reason, in the body.

## 4. Bootstrap, risks, G4 baseline

- rc-8 opens on the work branch after this definition merges; rc-7 is merged.
- `bug` worktrees open only in the steps below; none other is open while T-050-166 strips `Intent:` (239 files).
- Production gap: if 181's readout exceeds 24,805, the closure logs the miss; extra DELETE candidates read here: the `api` alias-map kind of `subject_registry` (out of SPEC scope, goes to intake).
- G4 baseline: rc-7's run, one runner class, median; the `guards` job is the only job added.

## 5. Parallel schedule

| step | tasks open together | width | how |
|---|---|---|---|
| 1 | T-050-153 | 1 | one impl worktree; AC8.9 lands first |
| 2 | T-050-154, T-050-155, T-050-156, T-050-157 | 4 | one impl worktree each |
| 3 | T-050-158, T-050-159, T-050-160, T-050-161 | 4 | one impl worktree each; R1–R5 follow their merges |
| 4 | T-050-162, T-050-163, T-050-164, T-050-165 | 4 | one impl worktree each; R6, R7 when 153–161 merged |
| 5 | T-050-166, T-050-167 | 2 | one impl worktree each |
| 6 | T-050-168 | 1 | one impl worktree |
| 7 | T-050-169, T-050-170, T-050-171, T-050-172 | 4 | one `bug` worktree each |
| 8 | T-050-173, T-050-174, T-050-175, T-050-176, T-050-177 | 5 | one `bug` worktree each |
| 9 | T-050-178, T-050-179, T-050-180 | 3 | 178, 179 `bug`; 180 impl after R7 |
| 10 | T-050-181 | 1 | measure; closure in the release worktree |

- True edges:
  - 154, 155, 156, 157 need 153 (`test_venv_guard.py`, `tests/AGENTS.md`, `pyproject.toml`, `conftest.py`, `RC-FLOW.md`);
  - 158 needs 154 (`workspace_layout.py`, scaffold backlog law), 155 (`pyproject.toml`) and 156 (V29 reads `PARAMETERS.md`; `conftest.py`);
  - 159, 160 need 156 (`run.py`); 160 needs 155 (census); 161 needs 155 and 156 (`test_adr_canon.py`, `run.py`);
  - 162 needs 158 (CONTEXT-MAP, behavior-map); 163 needs 154, 158, 161 (`test_zone_registry.py`, `test_adr_canon.py`); 164 needs 154, 158 (`test_memory_drift.py`); 165 needs 153, 158 (gitflow and bug-resolution SKILL.md);
  - 166 needs 155–165 (every W8 test writer); 167 needs 165; 168 needs 167;
  - every W10 task needs 166 and 168; 173 needs 161, 169 (`repo.py`, `tests/README.md`); 174 needs 169 (`test_registry_version_grammar.py`); 177 needs 170 (`f/spec_context/doctor.py`); 172 needs 168 (schema); 178 needs 169, 173; 179 needs 168;
  - 180 needs R7 and 165–168 (no later QUALITY edit); 181 needs all.
- Critical path: T-050-153 → T-050-156 → T-050-158 → T-050-165 → T-050-167 → T-050-168 → T-050-169 → T-050-173 → T-050-178 → T-050-181 = 10 steps.
- Overlap check: disjoint in every step except `TASKS.md`, the `*.jsonl` ledgers, the derived `pub/entities/behavior-map.json` and the derived `pub/templates/shipped-hashes.json`.
- Merge order inside a step: ready order; after each merge every open sibling rebases onto the work branch.
