# SPEC — Release: 0.5.0, candidate 8 (W8: the test law and the library pipeline leave; W9: bug lineage derived; W10: the open bugs)

**Status:** Draft
**Release ID:** 0.5.0
**Owner:** dd-product-engineer
**Opened:** 2026-10-03
**Origin:** backlog:cli-ships-no-library-pipeline,lib-test-guidance-dehydrated,tests-agents-scaffold-without-placeholders,test-intent-docstring-backfill,meta-tests-leave-pytest,preflight-ci-parity-derived,delete-text-count-inventory-asserts,adr-0143-measured-by-checks-the-concept,skill-md-soft-hard-line-limit,memory-update-states-the-truth-correction-lane,bug-fix-adds-never-rewrites-asserts,bug-fix-commit-derived-by-grep,caused-by-proposed-by-blame,focused-review-on-caused-by,bug-terminal-transition-commit-shape,architecture-survey-flat-core-infrastructure,doctor-context-ignores-other-contexts,guidance-messages-name-the-right-target; bugs:test-suite-writes-outside-tmp,ci-preflight-writes-coverage-into-the-repo,hook-entrypoints-invisible-to-coverage,onboarding-next-step-names-another-context,init-on-a-copied-workspace-leaves-a-cli-bound-to-the-original,registry-row-missing-a-key-escapes-reg-schema,pre-push-warns-no-gitflow-block-for-an-absent-specs-tree,upgrade-leaves-reconcile-scratch-behind,bug-surface-schema-documents-the-deleted-regex,release-memory-appends-a-second-entry-on-rerun; findings:20260930-structural-convergence-F003,20260930-structural-convergence-F018,20260930-structural-convergence-F028,20260930-structural-convergence-F043,20260930-structural-convergence-F044,20260930-structural-convergence-F045,20260930-structural-convergence-F047,20260930-structural-convergence-F048,20260930-structural-convergence-F049,20260930-structural-convergence-F050,20260930-structural-convergence-F051,20260930-structural-convergence-F096,20260930-structural-convergence-F097,20260930-structural-convergence-F098,20260930-structural-convergence-F100,20260930-structural-convergence-F101,20260930-structural-convergence-F104,20260930-structural-convergence-F112,20260930-structural-convergence-F128,20260930-structural-convergence-F129,20260930-structural-convergence-F131,20260930-structural-convergence-F135,20260930-structural-convergence-F136

- Sources: grills of 2026-10-02 (rc-8, Q1–Q4) and 2026-10-03 (train, Q1–Q6); reviews B1–B11, H1–L6 on fb8a29a75, then re-review 2 on 196f611aa; PR #278 F1. Task ids start at T-050-153.
- Bug history read (permanent architecture review): PLAN §1, the as-is review.
- Left out: `dependabot-pyjwt-open-on-main`, closing at the ship (rc-12); `removals-shipped-without-recorded-authority`, rejected (Q5).

## Objective

- The library ships no pipeline of its own: `ci preflight` and the pytest bootstrap leave first (Q2).
- Test knowledge leaves the library (0166); meta-tests leave pytest for one CI job; tests assert behaviour (0163, 0167).
- Bug lineage is derived from git, and a bug fix adds a case (0163, 0164). SKILL.md gets one size law (0170).
- The open bugs are fixed; production and tests end smaller (§G1).

## Terms

- `CONTEXT.md` holds the terms. **W8**–**W10** are this candidate; **DEL** and **FR** keep rc-5's meaning.
- **Meta-test**: a test whose subject is the suite or the repository (files outside the package, CI, ledgers), not a package module or shipped asset.
- **Guard script**: a meta-test's unique check, moved into a script the one CI job runs.
- **Owner file**: the one test file owning a module's behaviour; a RED enters it as a new case (0146 (5)).
- **Behaviour assert**: an assert on an exit code, an effect, or a stable id (finding code, slug, flag); a sentence, roster, or count with a source of truth is not one.
- SCAFFOLD here is the test tier (V28), never the specs scaffold. Bare `preflight` is a homonym: `ctx_inject`'s generic preflight, `_dead_preflight` and `_ownership_preflight` stay.

## Decisions

- These ADRs decide: 0071 (amended by 0163), 0104, 0118, 0119, 0122, 0123, 0138, 0140, 0142, 0143 (amended by 0166, 0170), 0146 (5), 0149, 0152 (2), 0158, 0160 (amended by 0164), 0162, 0163, 0164, 0166, 0167 (partly; the rest is rc-9's), 0170.
- One new ADR: 0176 (proposed), AC8.10. The operator accepts it in the release worktree, in the commit carrying the nine `### P-NN` hunks (`specs/ADRs/AGENTS.md` §3); `amends: 0167` is written then (0151 M2). 0143's repair and AC8.10's repairs take the 0138 lane.
- Operator, 2026-10-03, verbatim:
  - Train: "you will only create now the RC8 ... we will wait till we finish the RC8"; rc-9..rc-12 are §Carried.
  - Q1 "Keep in 0.5.0 as rc-11 (Recommended)". Q2 "Yes, into rc-8 (Recommended)".
  - Q3 "Register as bugs, fix in rc-8 W10 (Recommended)"; re-ruled for `init-announces-codex-trust`: "Not a bug: reject the entry (Recommended)".
  - Q4 "Derive it from `bugs.py fix` (Recommended)". Q5 "Reject; authority table goes to rc-12 notes (Recommended)". Q6 "rc-10 via dd-ask-me (Recommended)".
- Order (root map §1): AC8.9; the rest of W8; W9; W10, after AC9.3 and AC8.1's `Intent:` strip. Width: the PLAN's Parallel schedule (0149).

## Gate — G1–G6, applied to W8–W10

- G1 Principles, never a line-count limit (0142):
  - DELETE → REBUILD → UPDATE → KEEP → ADD; an ADD names what it could not delete. No question gets a second decider.
  - Readout, `<start>`/`<end>`: production lines `git ls-files -z 'dadaia_workspace/*.py' | xargs -0 cat | wc -l`; test functions `git grep -hE '^\s*(async\s+)?def test_' -- 'tests/*.py' | wc -l`; test lines `git ls-files -z 'tests/*.py' | xargs -0 cat | wc -l`; guard-script lines and checks over the PLAN's glob for them.
  - At birth (8f4ed785f): 25,307 / 1,233 / 45,464 / 0 / 0.
  - Production: rc-7 planned −160, measured +342 (PR #278 F1); rc-8 carries the 502-line miss and ends at or below 24,805, its ADDs counted; the PLAN names the DELETE rows, AC8.9 the largest.
  - Tests, guard scripts counted in (the c4 target): functions plus guard checks ≤ 1,167; test lines plus guard-script lines ≤ 43,232.
- G2 `bugs.py status` lists no open record whose `caused_by` names a W8–W10 record or commit.
- G3 Each open bug is re-run at `<end>`; one not reproducing is resolved, citing the commit that removed its cause.
- G4 CI green on the three OSes; `.dadaia/.venv/bin/dadaia doctor --context dadaia-workspace` exits 0. Wall-clock vs rc-7: one runner class, the median. The guard-script job is the only job added.
- G5 A test a DEL leaves dead leaves in the same commit. A new test follows the root-map test basics (AC8.1).
- G6 At closure, findings and `active[]` are re-audited; rc-9 is defined from §Carried; one `dispositions` entry logs open before, resolved, open after.

## W8 — the test law and the library pipeline leave: acceptance

- AC8.9 (first) The CLI ships no library pipeline (FR `cli-ships-no-library-pipeline`; supersedes FR `preflight-ci-parity-derived`, F104):
  - Deleted: the `preflight` verb and its imports in `cli/commands/ci.py` (group help reworded); `features/ci_preflight/`; `CiPreflightScopeError`; `container.is_source_repo_root`; `subprocess_runner_for_ci`; `_ensure_ci_toolchain`. `workspace_guardrail._is_source_repo_root` stays (`public_assets` guards `public install`).
  - With them: `setup.cfg` `features.ci_preflight`, `docs/cli.md`, `docs/getting-started.md`, `tests/conftest.py:436`, `tests/contract/README.md`, `test_preflight_doctor_scope.py`, `test_cli_ci.py`'s preflight cases, and every other line the grep below names; the preflight lines of `dd-gitflow-default/SKILL.md`, `RC-FLOW.md`, and, beyond the grep, `dadaia-AGENTS.md:14`, `tests/AGENTS.md:39`, `setup.cfg:59`, `pyproject.toml:99`, `core/workspace_resolver.py:26`, `test_cli_help_quality.py`'s case.
  - `ci push-gate-check` and `ci install-hook` (the pre-push chokepoint) stay; their cases (`test_cli_ci.py:62`, `test_push_gate_check.py:86`) stay green, no new test.
  - `code` anchors resolve any tracked path, the symbol optional. The `cli` anchor kind, `REPO_TREE_ARTIFACTS` reaping (and its consumers `privacy_check._PUBLIC_ASSET_IGNORED_DIRS`, `REPO_TREE_EXCLUDED`), `venv_guard`'s tool names and `_memory_drift`'s extension list turn language-neutral or leave (as-is review; deletion preferred). `public/scaffold/backlog/AGENTS.md` §4.1's `code` and `cli` rows and "no Python sources" bullet are rewritten.
  - `TOOL_CACHE_ENV` stays (0080), language-neutral; the no-cache-in-tree case `test_tool_caches_stay_in_the_tmp_zone.py` stays green.
  - This repo's `AGENTS.md` gains a line installing the `dev` group into the workspace venv; its CI equivalent lives there and in `.github/`.
  - Command: `git grep -niE 'ci.?preflight|CiPreflight|_ensure_ci_toolchain|subprocess_runner_for_ci|[^_]is_source_repo_root' -- . ':!specs' ':!CHANGELOG.md'` prints nothing; `.dadaia/.venv/bin/dadaia ci preflight` exits 2.
  - Case: `test_python_env.py:85-93` asserts no `pytest` install; CI's `dev`-group install proves the line; no new venv.
  - Case: a backlog `code` anchor to a `.go` file passes BL-SCHEMA.
  - At closure, `preflight-ci-parity-derived` exits `superseded --release 0.5.0`; the memory pass deletes the `ci-preflight` atom.
- AC8.1 Test knowledge leaves the library (FR `lib-test-guidance-dehydrated`; 0166; F112, F101):
  - Deleted: `public/skills/dd-test-stewardship/`, `public/templates/tests-AGENTS.md` and their wiring (persona `skills:`, `behavior-map.json` rows, `workspace_layout.REPO_LAW`, `canon.py`, the onboarding list, `doctor_memory.py`, CONTEXT-MAP rows, the tests pinning them).
  - The `Intent:` convention leaves with V28, V29 and V31 (this AC owns them) and every docstring `Intent:` line.
  - The root map gains the test basics by rewriting existing bullets: RED before the fix, at the lowest level; behaviour, not text; mock only at the boundary; a literal expected value; a fix commit never rewrites an old assert. `slop-tests.md`, the QUALITY scaffold and the personas point at them.
  - Command (0166's `measured_by`): `grep -rn 'dd-test-stewardship\|tests-AGENTS\|Intent:' dadaia_workspace/public` prints nothing, and `.dadaia/.venv/bin/dadaia public doctor` is clean; `git grep -n 'Intent:' -- tests` prints nothing.
  - At closure, `tests-agents-scaffold-without-placeholders` and `test-intent-docstring-backfill` exit `superseded --release 0.5.0`.
- AC8.2 One answer for canonical memory at closure (FR `memory-update-states-the-truth-correction-lane`; 0138): `MEMORY-UPDATE.md` states no canonical-memory rule of its own and points at the memory law (a `### P-NN` changes only with its ADR, any other section under 0138); its step 7 names no library-internal test. Command: `grep -c 'QUALITY.md' dadaia_workspace/public/skills/dd-release-implementation/MEMORY-UPDATE.md` prints `1`; `grep -rn 'never touched at closure' dadaia_workspace/public` prints nothing.
- AC8.3 Meta-tests leave pytest for one CI job (FR `meta-tests-leave-pytest`; 0163, 0166, 0167):
  - Deleted as duplicates: `stewardship_mechanics` beyond AC8.10's checks (conftest); `repo_self_scan` (gitleaks, pre-push); `source_repo_hygiene` (the CI repo-hygiene job); `test_adr_canon`'s committed-ledger case (the CI doctor job). V28, V29, V31: AC8.1.
  - Deleted: the mutation tooling (`tests/scripts/run_mutation_baseline.sh`, its wiring tests, `test_mutation_baseline_scope_stdlib_only.py`, `[tool.mutmut]`, the `mutation` group); the memory pass states mutation evidence is operator tooling.
  - Moved to guard checks, each red on a planted violation: V26 (`test_test_suite_ratchets.py`); V32, V33, V37–V40 (`test_slop_ratchets.py`; V32's twin in `test_import_linter_ignore_cap.py`); `suite_cannot_reach_a_real_workspace`, `suite_cannot_reach_the_instance`; `test_ci_workflow_hygiene.py`, `test_memory_canonical_shape.py`; `test_release_semver_canon`'s release-please cases and `test_version_lineage_consistency.py` (P-30's check); `test_adr_canon`'s superseded-successor case; AC8.6's check.
  - Not meta-tests (package subject): `test_core_file_io_purity` (package AST), `test_behavior_map` (shipped `behavior-map.json`), `test_public_source_hygiene` (shipped text, wheel), `test_console_scripts` (the shipped entry-point table), `test_release_semver_canon`'s id-grammar case; `test_law_states_what_the_code_does` is AC8.4's. `test_docs_derived_from_memory.py` stays until rc-12 (AC8.10).
  - The as-is review may add files, never remove one; no unique guard is lost; the parity check dies with preflight.
  - Command: `git ls-files tests | grep -E 'suite_cannot_reach|stewardship_mechanics|repo_self_scan|source_repo_hygiene|test_suite_ratchets|mutation_baseline|slop_ratchets|import_linter_ignore_cap|preflight|ci_workflow_hygiene|memory_canonical_shape|version_lineage'` prints nothing; the CI job's log names each moved guard.
  - At closure, `meta-tests-leave-pytest` exits `delivered --release 0.5.0`.
- AC8.10 Every principle whose test leaves pytest keeps a check (0176):
  - QUALITY P-21 `tier-timeout`, P-22 `quarantine-needs-bug`, P-23 `private-import-ratchet`, P-28 `marker-set-closed`, P-33 `no-model-api-in-ci`; ARCHITECTURE P-07 `features-modules-equal-packages`, P-10 `ignore-cap`, P-30 `release-workflow-canon`, P-32 `memory-canonical-shape`.
  - Each is a guard check with a planted violation, named by its `Measured by` in 0176's accept commit, which drops `RELEASE-TREE-MEMORY` (F128) and `-k model_api` (F131) and strikes P-30's archive clause, false under 0152 (1) (`release.py ship`). Command: 0176's `measured_by` grep prints nothing.
  - P-29 stays outside 0176, its test file too: its record 0012 is rejected, publish-gate check #7 (rc-12) rules on it, and a `### P-NN` line never takes the 0138 lane.
  - Repaired in place (0138), each by a `chore(adrs): repair …` commit in the release worktree right after its moving task merges (`impl` cannot stage `decisions.jsonl`; a6bca8d52): 0016, 0017, 0021, 0023, 0025, 0049, 0052, 0070, 0071, 0078, 0080 (to AC8.9's no-cache case), 0088.
  - Truth corrections (0138), at or before the accept commit, after the removing task: `QUALITY.md:47, 51-53, 55, 59-60, 63-64, 69, 71`; `ARCHITECTURE.md:102, 110, 139`.
  - After the last `QUALITY.md` edit, an `impl` task re-derives `docs/bug-ledger-lessons.md`'s markers (lines 45, 57, 66; T-050-150: `b9d7e4682`, `0800ec554`).
- AC8.4 Tests assert behaviour (FR `delete-text-count-inventory-asserts`; 0167):
  - No test pins a value owned elsewhere (a law sentence, a code roster or count); prose asserts on a doc, law or skill are deleted.
  - A CLI assert checks exit code, effect and stable id; an exception assert, type or attribute; a `fix:` line is executed. No new `--json`.
  - Count pins are deleted or derived from their source; CONTEXT-MAP loses its `Measured` column.
  - Command, the floor: `git grep -nE 'len\(.*\) *== *[0-9]{2,}' -- tests` prints nothing. Below it the reviewer judges the concept; the string-assert readout at `<start>`/`<end>` names each survivor's stable id.
- AC8.5 SKILL.md soft and hard limits (FR `skill-md-soft-hard-line-limit`; 0170): `behavior-map.json` carries `skill_md_line_soft` 333 beside `skill_md_line_ceiling` 500, declared in the schema; `doctor` emits `SKILL-MD-LENGTH` as a WARNING over the soft limit, with one `Operator action:` line naming the SKILL.md path and its split into `references/*.md` and/or `scripts/`; CONTEXT-MAP §3 loses the skills `Budget` column. Command: 0170's `measured_by`, verbatim.
- AC8.6 ADR 0143 measures the concept (FR `adr-0143-measured-by-checks-the-concept`; 0138 lane): its `measured_by` is repaired in place to a check that no test or script compares a file's line or byte count against a constant, except 0170's two `behavior-map.json` keys. The check is an AC8.3 guard; a planted size row turns it red.
- AC8.7 `CONTEXT.md` gains **Meta-test**, **Guard script**, **Owner file** and **Behaviour assert**; the SCAFFOLD test tier leaves the Scaffold homonym entry.
- AC8.8 `dd-architecture-survey` runs read-only over `core/` and `infrastructure/` (FR `architecture-survey-flat-core-infrastructure`), the ring rule unchanged; its proposals reach intake before rc-9's PLAN.

## W9 — bug lineage derived: acceptance

- AC9.1 A bug fix adds a case (FR `bug-fix-adds-never-rewrites-asserts`; 0163, 0164 (4)):
  - Phase 5 loses "existing test rewritten"; Phase 6 loses "production AND tests net ≤ 0".
  - The RED is a parametrize row in the owner file, with a literal expected value and a behaviour name; rewriting an old assert is its own commit, with a reason. The review names `git diff -U0 -- tests | grep -E '^-\s*assert'`.
  - `REQUIRED_BY_VERB` drops `evidence_seam` and `evidence_diff`; they turn optional in the schema, their verification code leaves; `evidence_loop` stays. `PILLAR-BUGS` metric 2 (row 26) counts records carrying `evidence_loop`; row 44 loses its `evidence_seam` clause.
  - Command (0163's `measured_by`): `grep -rn 'net test lines\|<bug-id>#<id>\|mutmut' dadaia_workspace/public` prints nothing; `git grep -n 'evidence.triple\|evidence_seam\|evidence_diff' -- dadaia_workspace/public` lists only the schema's two optional properties.
- AC9.2 The fix commit and its direction are derived, one decider (FR `bug-fix-commit-derived-by-grep`; 0164 (1); Q4):
  - `bugs.py fix <id>` prints the fix sha, test files and numstat, found through shape 3's `^fix\(bugs\): .*<id>` or shape 4's `(<sha>)`; no schema field is added; `LINEAGE.md` uses it in place of `git log -S`.
  - `bugs.py stats`' `direction:` rows and `PILLAR-BUGS` rows 27 (metric 3) and 45 read that numstat, never `evidence_diff`; F003 is re-measured by it and logged.
  - Command: for every record resolved since 2026-08-27, `bugs.py fix` prints a sha or lists it unlinked; both counts are logged.
- AC9.3 `caused_by` is proposed by blame (FR `caused-by-proposed-by-blame`; 0164 (2), (3)):
  - `resolve` blames the lines the staged diff removes and prints the candidates, skipping the regenerated files the projection declares, squash `(#n)` and `refactor(T-…)` commits.
  - It refuses a `--caused-by` outside the candidates, and `none` when candidates exist, unless `--lineage-reason` is given and stored.
  - One semantics in the schema, `LINEAGE.md` and the bugs law: "the fix of X wrote the lines this fix corrects".
  - Case: `none` with candidates exits non-zero; with `--lineage-reason` it passes.
- AC9.4 `caused_by` other than `none` makes the review read every line the prior fix wrote and state REBUILD or why not (FR `focused-review-on-caused-by`; 0164 (5)); it lives in `dd-code-review`, measured by `PILLAR-BUGS`, never gated.
- AC9.5 `dd-gitflow-default` §3a row 4 widens to every terminal transition without code: `chore(bugs): <verb> <id> — <reason, or by <task-id> (<sha>)>`, one edit with AC9.1's (FR `bug-terminal-transition-commit-shape`).

## W10 — the open bugs, harm-ordered (Arm B)

After AC9.3 and AC8.1's `Intent:` strip merge. Each RED is a behaviour assert in its owner file; MEDIUMs first.

- AC10.1 One test child-env builder (DEL `test-suite-writes-outside-tmp`; F018, F049, F135, F136), re-cut on AC8.9:
  - Every test child takes its env from `harness_env.py`: a tmp `HOME`, `PYTHONDONTWRITEBYTECODE=1`, `DADAIA_FENCED_ROOTS`; the parent's `COVERAGE_FILE`, `COVERAGE_PROCESS_START` and `COVERAGE_PROCESS_CONFIG` cross it (AC10.2, AC10.3).
  - Command: `git grep -nE 'os\.environ\.copy\(\)|dict\(os\.environ|\*\*os\.environ' -- tests` prints only the builder; after `env -u PYTHONDONTWRITEBYTECODE HOME=<tmp> python -m pytest -q -n 3 -p no:randomly`, `find dadaia_workspace tests -name __pycache__` prints nothing and `<tmp>/.cache/pip` is absent. F136 is scored from a CI E2E run.
- AC10.2 Coverage data lands outside the repo (DEL `ci-preflight-writes-coverage-into-the-repo`; F048), re-cut on AC8.9: on every documented path (CI, the `pytest --cov` lines of `tests/README.md` and `tests/AGENTS.md`) no coverage file appears in the checkout; one decider, placed by the as-is review. Case: after each path, `git status --porcelain --ignored | grep -c coverage` prints `0`.
- AC10.3 Hooks are visible to coverage and bounded in cost (DEL `hook-entrypoints-invisible-to-coverage`; F051; 0118): `hooks/ctx_inject.py` and `sdd_post_gate` are above 0 in CI's coverage JSON. One case, parametrized over the hook lanes, counts operations at the boundary seam (the filesystem or subprocess fake), no counter in production code; it does not grow with workspace size.
- AC10.4 A run judges only its own context (DEL `onboarding-next-step-names-another-context`; FR `doctor-context-ignores-other-contexts`; FR `guidance-messages-name-the-right-target`, SessionStart part; F028, F096, F098): one decider, the bound context or the one `--context` names; the cross-context walk is deleted. Case: bound to X with two contexts, the next step's `step_id` and slug are X's. Case: with slop only in another context's repo, `doctor --context X` exits 0.
- AC10.5 A copied workspace gets its own CLI (DEL `init-on-a-copied-workspace-leaves-a-cli-bound-to-the-original`; F045): `init` reuses a venv only when its prefix and shebangs point at `DIR/.dadaia/.venv`. Case: after `cp -a` and `init <copy>`, `head -1 <copy>/.dadaia/.venv/bin/dadaia` names `<copy>`; the original is untouched.
- AC10.6 A registry row missing a key is unreadable (DEL `registry-row-missing-a-key-escapes-reg-schema`; 0162): the one parse raises `SchemaVersionError`; doctor reports `REG-SCHEMA` with an `Operator action:` line. Case: a row without `created_at` exits 1 with `REG-SCHEMA`, no `KeyError`.
- AC10.7 An absent specs tree is reported as absent (DEL `pre-push-warns-no-gitflow-block-for-an-absent-specs-tree`; F043): with no constitution, `core/gitflow.py` reports the absence with `fix: .dadaia/.venv/bin/dadaia specs init --context <ctx>`. Case: the finding is asserted and the fix line executed.
- AC10.8 An upgrade leaves no scratch and no silent rewrite (DEL `upgrade-leaves-reconcile-scratch-behind`; F044; 0104): `.dadaia/tmp/reconcile/` is absent after `init`; `init` rewrites a repo's `pre-push` only when it differs from the projected bytes, preferred over a new print. Case: a second `init` leaves the hook's bytes untouched; a differing hook is refreshed.
- AC10.9 Withdrawn: the bug was rejected (Q5); F069 moves to rc-12.
- AC10.10 `bug-record-v1.schema.json`'s `surface` description states the tracked-directory rule (DEL `bug-surface-schema-documents-the-deleted-regex`). Command: `grep -c 'a-z0-9_-' dadaia_workspace/public/schemas/bugs/bug-record-v1.schema.json` prints `0`.
- AC10.11 Resolved at closure by citation: F050 by b5013bbfb; F129 by bdb24bc64; F047 by `chore(bugs): reject removals-shipped-without-recorded-authority`; F100 by the commit exiting `init-announces-codex-trust` rejected (T-050-71 removed the trust INFO on purpose).
- AC10.12 HOOKS-DRIFT-1 states what it observed (FR `guidance-messages-name-the-right-target`, HOOKS-DRIFT-1 part; F098): one code, its message naming the observed state (absent or differing); the fix line (`ci install-hook --force`) serves both. Case: delete a projected hook; the message says absent, and its fix line, executed, restores it. T-050-146 delivered the root-whitelist clause.
- AC10.13 `release.py memory` is idempotent (DEL `release-memory-appends-a-second-entry-on-rerun`; F097): a rerun over the same window exits 0 and leaves the log unchanged. Case: the `kind: memory` entries are byte-equal after the rerun.

## Replaces

- `ci preflight`, its scope error, runner and pytest bootstrap; the Python-only anchors, reaping list, tool names, extension list and `TOOL_CACHE_ENV` list (AC8.9).
- `dd-test-stewardship`, the tests-AGENTS template, the `Intent:` convention, V28, V29, V31; MEMORY-UPDATE's own canonical-memory rule.
- Duplicate meta-tests, the mutation tooling, meta-test pytest files; nine principles' pytest `Measured by` and P-30's archive clause (0176).
- Prose, roster and count asserts; CONTEXT-MAP's `Measured` and skills `Budget` columns; 0143's symbol-list `measured_by`.
- Phase 5's "rewritten", Phase 6's "net ≤ 0"; required `evidence_seam`/`evidence_diff`, their verification, metric 2 over them, direction from `evidence_diff`; the `git log -S` recipe; an unreasoned `none`; the "reopen" wording; §3a row 4's resolve-only wording.
- Ad-hoc child envs, `COVERAGE_FILE` redirects; the cross-context walk; build-identity venv reuse; the bare `KeyError`; the no-block warning for an absent constitution; HOOKS-DRIFT-1's fixed "differs"; the reconcile scratch and unconditional hook rewrite; the deleted surface regex; the second `kind: memory` append.

## Risks

| Weakness | Mitigation |
|---|---|
| A deleted text assert was a real guard. | It maps to a behaviour assert or a reason in the commit body; the reviewer checks. |
| The `Intent:` strip (about 239 files) conflicts with `bug` worktrees. | W10 waits on it. |
| The root map passes its soft budget (8,293 of 8,192 B). | Basics rewrite existing bullets. |
| The deletion goal is missed. | Planned row by row; the closure logs it. |

## Carried — the 0.5.0 map (ADR 0140; one candidate at a time)

- rc-9: the tests tree mirrors the package; the unit tier spawns no processes, carrying rc-7's slow-class G4 growth (operator 2026-10-02: "Same-runner-class rule; slow-class growth to rc-8 (Recommended)", tied to `unit-tier-without-processes`); the production-faithful hook harness (0163); `worktree-rows-injected-not-monkeypatched`; `windows-integration-coverage-gap`; `repo-ci-sast`. With rc-8, they complete 0167.
- rc-10: `public-law-language-neutral`; `dd-ask-me-owned-questioning-skill`, delivering 0165 and `dd-ai-eng-knowhow/AUTHORING.md:134` ("asks the whole frontier at once"), caught by 0165's repaired `measured_by`; `adr-born-at-release-with-options`; `adr-ledger-triage-process-rules`; `architecture-adr-section-generated`; F088, F089, F139–F148.
- rc-11: workspace replication (7 entries, ADRs 0171–0175); F084.
- rc-12, the promote: docs site F109, clone detection F110, launch prep F111; the residue (`spec-context-refusals-print-prose`, `privacy-baseline-one-parser`, `ledger-refusals-guess-specs-from-command-shape`, `ledger-reader-one-numbered-tolerant-iterator`, `doctor-in-a-fresh-worktree-lacks-rendered-specs-law`, F060); memory drift F123–F127; bug metrics F001, F004, F005, F009 (re-measured over AC9.3's links); the publish gate F067; the audit checks never run, F137; the removal-authority notes (F069); PyJWT, closing at the ship.

## Open questions for the operator

- None: the 2026-10-03 grill frontier is empty.
