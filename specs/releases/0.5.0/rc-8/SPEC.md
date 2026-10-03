# SPEC — Release: 0.5.0, candidate 8 (W8: the test law and the library pipeline leave; W9: bug lineage derived; W10: the open bugs; W11: agent-behavior evals, a parallel lane)

**Status:** Approved
**Release ID:** 0.5.0
**Owner:** dd-product-engineer
**Opened:** 2026-10-03
**Origin:** backlog:agent-behavior-evals,cli-ships-no-library-pipeline,lib-test-guidance-dehydrated,tests-agents-scaffold-without-placeholders,test-intent-docstring-backfill,meta-tests-leave-pytest,preflight-ci-parity-derived,delete-text-count-inventory-asserts,adr-0143-measured-by-checks-the-concept,skill-md-soft-hard-line-limit,memory-update-states-the-truth-correction-lane,bug-fix-adds-never-rewrites-asserts,bug-fix-commit-derived-by-grep,caused-by-proposed-by-blame,focused-review-on-caused-by,bug-terminal-transition-commit-shape,architecture-survey-flat-core-infrastructure,doctor-context-ignores-other-contexts,guidance-messages-name-the-right-target,worktree-memory-states-plain-ledger-merge; bugs:test-suite-writes-outside-tmp,ci-preflight-writes-coverage-into-the-repo,hook-entrypoints-invisible-to-coverage,onboarding-next-step-names-another-context,init-on-a-copied-workspace-leaves-a-cli-bound-to-the-original,registry-row-missing-a-key-escapes-reg-schema,pre-push-warns-no-gitflow-block-for-an-absent-specs-tree,upgrade-leaves-reconcile-scratch-behind,bug-surface-schema-documents-the-deleted-regex,release-memory-appends-a-second-entry-on-rerun; findings:20260930-structural-convergence-F003,20260930-structural-convergence-F018,20260930-structural-convergence-F028,20260930-structural-convergence-F043,20260930-structural-convergence-F044,20260930-structural-convergence-F045,20260930-structural-convergence-F047,20260930-structural-convergence-F048,20260930-structural-convergence-F049,20260930-structural-convergence-F050,20260930-structural-convergence-F051,20260930-structural-convergence-F096,20260930-structural-convergence-F097,20260930-structural-convergence-F098,20260930-structural-convergence-F100,20260930-structural-convergence-F101,20260930-structural-convergence-F104,20260930-structural-convergence-F112,20260930-structural-convergence-F128,20260930-structural-convergence-F129,20260930-structural-convergence-F131,20260930-structural-convergence-F135,20260930-structural-convergence-F136

- Sources: grills of 2026-10-02 (rc-8, Q1–Q4) and 2026-10-03 (train, Q1–Q6); reviews B1–B11, H1–L6 on fb8a29a75, then re-review 2 on 196f611aa; PR #278 F1; for W11, the grills and draft its Origin names. Task ids start at T-050-153.
- Bug history read (permanent architecture review): PLAN §1, the as-is review.
- Left out: `dependabot-pyjwt-open-on-main`, closing at the ship (rc-12); `removals-shipped-without-recorded-authority`, rejected (Q5).

## Objective

- The library ships no pipeline of its own: `ci preflight` and the pytest bootstrap leave first (Q2).
- Test knowledge leaves the library (0166); meta-tests leave pytest for one CI job; tests assert behaviour (0163, 0167).
- Bug lineage is derived from git, and a bug fix adds a case (0163, 0164). SKILL.md gets one size law (0170).
- The open bugs are fixed; production and tests end smaller (§G1).
- Agent behaviour is measured on the shipped wheel, from the associated repo `dadaia-evals`, beside W8–W10 (W11; 0177–0179).

## Terms

- `CONTEXT.md` holds the terms. **W8**–**W11** are this candidate; **DEL** and **FR** keep rc-5's meaning.
- **Meta-test**: a test whose subject is the suite or the repository (files outside the package, CI, ledgers), not a package module or shipped asset.
- **Guard script**: a meta-test's unique check, moved into a script the one CI job runs.
- **Owner file**: the one test file owning a module's behaviour; a RED enters it as a new case (0146 (5)).
- **Behaviour assert**: an assert on an exit code, an effect, or a stable id (finding code, slug, flag); a sentence, roster, or count with a source of truth is not one.
- **Evals repo**: AC11.1's `CONTEXT.md` entry. `eval.yml` is a workflow in that file's one sense.
- SCAFFOLD here is the test tier (V28), never the specs scaffold. Bare `preflight` is a homonym: `ctx_inject`'s generic preflight, `_dead_preflight` and `_ownership_preflight` stay.

## Decisions

- These ADRs decide: 0071 (amended by 0163), 0104, 0118, 0119, 0122, 0123, 0138, 0140, 0142, 0143 (amended by 0166, 0170), 0146 (5), 0149, 0152 (2), 0158, 0160 (amended by 0164), 0162, 0163, 0164, 0166, 0167 (partly; the rest is rc-9's), 0170.
- One new ADR: 0176 (proposed), AC8.10. The operator accepts it in the release worktree, in the commit carrying the nine `### P-NN` hunks (`specs/ADRs/AGENTS.md` §3); `amends: 0167` is written then (0151 M2). 0143's repair and AC8.10's repairs take the 0138 lane.
- 0181 (proposed; operator 2026-10-03, "One ADR for rc-8's W8 law deletions (Recommended)") names every law line W8–W10 deletes or rewrites; every commit of this candidate deleting a law line cites it (0151 M3), T-050-183's cite 0177 and T-050-189's 0180. The operator accepts it before T-050-154's push.
- Operator, 2026-10-03, verbatim:
  - Train: "you will only create now the RC8 ... we will wait till we finish the RC8"; rc-9..rc-12 are §Carried.
  - Q1 "Keep in 0.5.0 as rc-11 (Recommended)". Q2 "Yes, into rc-8 (Recommended)".
  - Q3 "Register as bugs, fix in rc-8 W10 (Recommended)"; re-ruled for `init-announces-codex-trust`: "Not a bug: reject the entry (Recommended)".
  - Q4 "Derive it from `bugs.py fix` (Recommended)". Q5 "Reject; authority table goes to rc-12 notes (Recommended)". Q6 "rc-10 via dd-ask-me (Recommended)".
  - Amendment: "Amend AC8.9, delete them (Recommended)" (AC8.9's second deletion list); "Use the native tools (Recommended)" (AC8.10's P-07 and P-28).
  - Amendment (AskUserQuestion): "Add to rc-8 (Recommended)" (backlog `worktree-memory-states-plain-ledger-merge` joins the Origin, AC10.14); "Land eval.yml on main early (Recommended)" (AC11.5, AC11.6).
- Order (root map §1): AC8.9; the rest of W8; W9; W10, after AC9.3 and AC8.1's `Intent:` strip. Width: the PLAN's Parallel schedule (0149).
- W11 (amendment, operator 2026-10-03, AskUserQuestion, verbatim):
  - Fold (grill 170932Z): "fold into rc-8. make sure to define that it can surely be implemented in parallel ... because it's on other repo".
  - Q-W0: "Yes, only that slice (Recommended)". AC11.0 carries only "an associated repo's impl reads the main repo's Approved trio" of proposed 0174; the rest stays rc-11's.
  - 0179: "Accept as prepared (Recommended)".
- Accept points of 0176, 0177, 0179 and 0180: PLAN R7–R10. 0178 (`amends: 0122`) is accepted at closure, since it governs rc-12's promote.

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
- G6 At closure, findings and `active[]` are re-audited; rc-9 is defined from §Carried; one `dispositions` entry logs open before, resolved, open after. Closure never waits on a ruling: a task still pending on an operator accept at closure (T-050-183, T-050-187, T-050-188 on 0177's; T-050-189 on 0180's) leaves T-050-181's `blocked by:` once §Carried rc-9 records it.

## W8 — the test law and the library pipeline leave: acceptance

- AC8.9 (first) The CLI ships no library pipeline (FR `cli-ships-no-library-pipeline`; supersedes FR `preflight-ci-parity-derived`, F104):
  - Deleted: the `preflight` verb and its imports in `cli/commands/ci.py` (group help reworded); `features/ci_preflight/`; `CiPreflightScopeError`; `container.is_source_repo_root`; `subprocess_runner_for_ci`; `_ensure_ci_toolchain`. `workspace_guardrail._is_source_repo_root` stays (`public_assets` guards `public install`).
  - With them: `setup.cfg` `features.ci_preflight`, `docs/cli.md`, `docs/getting-started.md`, `tests/conftest.py:436`, `tests/contract/README.md`, `test_preflight_doctor_scope.py`, `test_cli_ci.py`'s preflight cases, and every other line the grep below names; the preflight lines of `dd-gitflow-default/SKILL.md`, `RC-FLOW.md`, and, beyond the grep, `dadaia-AGENTS.md:14`, `tests/AGENTS.md:39`, `setup.cfg:59`, `pyproject.toml:99`, `core/workspace_resolver.py:26`, `test_cli_help_quality.py`'s case.
  - `ci push-gate-check` and `ci install-hook` (the pre-push chokepoint) stay; their cases (`test_cli_ci.py:62`, `test_push_gate_check.py:86`) stay green, no new test.
  - `code` anchors resolve any tracked path, the symbol optional. The `cli` anchor kind, `REPO_TREE_ARTIFACTS` reaping (and its consumers `privacy_check._PUBLIC_ASSET_IGNORED_DIRS`, `REPO_TREE_EXCLUDED`), `venv_guard`'s tool names and `_memory_drift`'s extension list turn language-neutral or leave (as-is review; deletion preferred). `public/scaffold/backlog/AGENTS.md` §4.1's `code` and `cli` rows and "no Python sources" bullet are rewritten.
  - Also deleted, for G1 (no backlog or histo record binds `api`; ledger: `sa-subjects-resolve-is-circular`, `backlog-doctor-default-alias-map-unresolved-from-repo-subdir`, `backlog-subjects-readme-uses-unsupported-positional-resolve`, `backlog-subject-registry-lacks-top-level-doctor-cli-anchor`):
    - the `api` anchor kind and its alias map: `subject_registry.py:80-107,330-348`, `SubjectKind.API`, the `api` of the backlog schema enum and `_backlog_write._KINDS`, `STATES_CANON`'s `backlog_subject_aliases.txt`;
    - `doctor --alias-map` and `--source-root` with their threading (`cli/commands/doctor.py:104-105,278-287,320,335,356-357`, `build_context`, `build_registry`); `cli/_backlog_roots.py` leaves whole. `code` anchors come from the repo's tracked paths through the process adapter;
    - `backlog.py subjects` (`backlog.py:93-101` and its wiring; `_backlog_write`'s kind refusal stops naming it);
    - SPEC-DOC-005: `PLAN_MAX_LINES`, `features/specs/doctor_release.py:33,108-128`, `rules.py:69-74` (0143, 0152 (2)).
  - With them: `public/scaffold/backlog/AGENTS.md` §4.1's `api` row and `subjects` bullet, `dd-backlog-definition/SKILL.md:62`, `CONSUMER_VALIDATION_RECIPE.md:37`, the `--source-root .` of `.github/workflows/ci.yml:345` and `docs/getting-started.md:113`, `tests/contract/README.md:91`, and the cases the grep below names. `test_backlog_definition_backlog_script.py:493`'s `panel` refusal (B4) stays, gaining an `api` row. The memory pass rewrites `backlog-ledger.md:30,41` and `workspace-doctor.md:28-29,56`; `QUALITY.md:71` is AC8.10's.
  - `TOOL_CACHE_ENV` stays (0080), language-neutral; the no-cache-in-tree case `test_tool_caches_stay_in_the_tmp_zone.py` stays green and gains a `pytest` parametrize row, not a new test.
  - This repo's `AGENTS.md` gains a line installing the `dev` group into the workspace venv; its CI equivalent lives there and in `.github/`.
  - Command: `git grep -niE 'ci.?preflight|CiPreflight|_ensure_ci_toolchain|subprocess_runner_for_ci|[^_]is_source_repo_root|alias.?map|backlog_subject_aliases|SubjectKind\.API|kind=api|"code", "api"|py subjects|SCRIPT\} subjects|"subjects":|--source-root|source_root[:=]|"source_root"|SPEC-DOC-005|PLAN_MAX_LINES|check_plan_line_limit' -- . ':!specs' ':!CHANGELOG.md'` prints nothing; `.dadaia/.venv/bin/dadaia ci preflight`, `.dadaia/.venv/bin/dadaia doctor --source-root .` and `backlog.py subjects` exit 2.
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
  - Deleted as duplicates: `stewardship_mechanics` beyond AC8.10's checks (conftest); `repo_self_scan` (gitleaks, pre-push); `test_adr_canon`'s committed-ledger case (the CI doctor job). V28, V29, V31: AC8.1.
  - `source_repo_hygiene` splits (T-050-155 review F1; the CI repo-hygiene job checks only tracked projection files; the `gitignore-…-recurrence` chain, 10 bugs):
    - Visibility rows: moved to guard check `specs-canon-tracked` (T-050-161, `repo.py`), derived from the canon, never a hand-kept list (`additive-globs-hand-kept-beside-the-canon`):
      - Probes: one path per row of `canon.py`'s `CANON`, its `dest` or a sample its `pattern` matches, each judged by `git check-ignore --no-index` (plain `check-ignore` passes any tracked path).
      - Expected not ignored, except a row where rendering its `TEMPLATES` source through `workspace_layout.render_registry_tables` changes it: that row is expected ignored. Today that is `AGENTS.md` alone (`.gitignore:132`); whether it gets tracked is backlog `doctor-in-a-fresh-worktree-lacks-rendered-specs-law`'s.
      - The ignored half, kept from F-20: `releases/_archive/<v>/local-notes.md` and `releases/_archive/<v>/tmp/<f>` are ignored. `release.py ship` renames the live directory with its untracked files (`release.py:124`), and nothing refuses them.
      - Planted: a temp `.gitignore` hiding `specs/releases/**/TASKS.md`, and one re-including `_archive/**/local-notes.md`, each turn it red.
    - Hidden rows elsewhere (`local-notes.md`, `tmp/`): the canon scan's, `canon_violations` (`features/specs/canon.py:172`) at pre-push (`push_gate.py:216-232`) and doctor (`canon.py:194-206`).
    - Stale rows (`ACTIVE.md`, `GRILL.md`, `OQ-DECISIONS.md`, `ALPHA-*-QA.md`, `PRE-PR-REVIEW.md`, `reviews/`, `specs/_archive/releases/`, `backlog/candidates.md`): dropped; the canon refuses those paths.
  - Deleted: the mutation tooling (`tests/scripts/run_mutation_baseline.sh`, its wiring tests, `test_mutation_baseline_scope_stdlib_only.py`, `[tool.mutmut]`, the `mutation` group); the memory pass states mutation evidence is operator tooling.
  - Moved to guard checks, each red on a planted violation: V26 (`test_test_suite_ratchets.py`); V32, V33, V37–V40 (`test_slop_ratchets.py`; V32's twin in `test_import_linter_ignore_cap.py`); `suite_cannot_reach_a_real_workspace`, `suite_cannot_reach_the_instance`; `test_ci_workflow_hygiene.py`, `test_memory_canonical_shape.py`; `test_release_semver_canon`'s release-please cases and `test_version_lineage_consistency.py` (P-30's check); `test_adr_canon`'s superseded-successor case; AC8.6's check; `test_frozen_clock_aging_ratchet.py` and `test_harness_env_contract.py` (the suite is their subject; no principle names either; 0020 is repaired, AC8.10).
  - Not meta-tests (package subject): `test_core_file_io_purity` (package AST), `test_behavior_map` (shipped `behavior-map.json`), `test_public_source_hygiene` (shipped text, wheel), `test_console_scripts` (the shipped entry-point table), `test_release_semver_canon`'s id-grammar case; `test_law_states_what_the_code_does` is AC8.4's. `test_docs_derived_from_memory.py` stays until rc-12 (AC8.10).
  - The as-is review may add files, never remove one; no unique guard is lost; the parity check dies with preflight.
  - Command: `git ls-files tests | grep -E 'suite_cannot_reach|stewardship_mechanics|repo_self_scan|source_repo_hygiene|test_suite_ratchets|mutation_baseline|slop_ratchets|import_linter_ignore_cap|preflight|ci_workflow_hygiene|memory_canonical_shape|version_lineage|frozen_clock_aging|harness_env_contract'` prints nothing; the CI job's log names each moved guard.
  - At closure, `meta-tests-leave-pytest` stays active: `test_docs_derived_from_memory.py` is its one leftover (AC8.10), so its done-when is unmet.
- AC8.10 Every principle whose test leaves pytest keeps a check (0176):
  - QUALITY P-21 `tier-timeout`, P-22 `quarantine-needs-bug`, P-23 `private-import-ratchet`, P-28, P-33 `no-model-api-in-ci`; ARCHITECTURE P-07, P-10 `ignore-cap`, P-30 `release-workflow-canon`, P-32 `memory-canonical-shape`.
  - The seven named are guard checks with a planted violation. Each check is named by its `Measured by` in 0176's accept commit. That commit drops `RELEASE-TREE-MEMORY` (F128) and `-k model_api` (F131), and strikes P-30's archive clause, false under 0152 (1) (`release.py ship`).
  - P-07 and P-28 are measured by the tool itself:
    - P-07 by `lint-imports`: contract `features-no-cross-feature` lists `modules = dadaia_workspace.features.*`, which import-linter 2.13 expands (verified 2026-10-03: kept on the tree, broken by a planted sibling import). `setup.cfg:97-109`'s hand-kept list and `test_import_linter_ignore_cap.py:57` leave.
    - P-28 by pytest's `--strict-markers`, added to `pyproject.toml:153` `addopts` (absent today; the suite collects under it, and a planted unregistered mark fails collection). `_KNOWN_MARKERS` (`tests/conftest.py:234-238`) and `test_stewardship_mechanics.py:100` leave; P-28's statement drops `_KNOWN_MARKERS`.
  - Command: 0176's `measured_by` grep prints nothing; `git grep -nE '_KNOWN_MARKERS|modules_equals_disk|marker_set_is_pinned' -- . ':!specs' ':!CHANGELOG.md'` prints nothing; `lint-imports --config setup.cfg --no-cache` and `pytest --collect-only -q` exit 0.
  - P-29 stays outside 0176, its test file too: its record 0012 is rejected, publish-gate check #7 (rc-12) rules on it, and a `### P-NN` line never takes the 0138 lane.
  - Repaired in place (0138), each by a `chore(adrs): repair …` commit in the release worktree right after its moving task merges (`impl` cannot stage `decisions.jsonl`; a6bca8d52): 0016, 0017, 0020, 0021, 0023, 0025, 0049, 0052, 0070, 0071, 0078, 0080, 0088. 0080 keeps `test_workspace_layout_zones.py` (it asserts no `.cache` zone) and swaps `test_no_pollution.py` for AC8.9's no-cache case.
  - Truth corrections (0138), at or before the accept commit, after the removing task: `QUALITY.md:46` (`suite_files`, the xdist reason), `47, 51-53, 55, 59-60, 63-64, 69, 71`, `72` ("sits beside the ratchets"); `ARCHITECTURE.md:102, 110`, `134` (13 packages become 12), `139`; `ARCHITECTURE.md:130` ("seven" import-linter contracts; `setup.cfg` holds six) is already false.
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
- AC10.14 Law and memory state the plain ledger merge (FR `worktree-memory-states-plain-ledger-merge`; 0180):
  - Memory, the closure pass (0138 lane, no `### P-NN`), once the `0.5.0d-bug` union fix merges, whatever 0180's status: `worktrees.md:5,35,36` and `bug-ledger.md:32` drop the union merge, citing the fix commit. In the same pass, `worktrees.md:35` ("trio `Approved` on that branch") states AC11.0's main-repo read. `catalog.json` is regenerated by `memory.py catalog generate`.
  - Law, only after 0180's acceptance, cited in the commit (0151 M3): `public/data/worktrees-AGENTS.md:30` (step 7) states 0180's writer re-run, in an `impl` worktree, then `public stage`, `install`, `doctor`.
  - Check: `grep -rniw union specs/memory` states no union merge; `memory.py check` is clean; `public doctor` reports no drift.
  - At closure, the entry exits `delivered --release 0.5.0`; with 0180 still proposed, it stays active and rc-9 carries the law line alone.

## W11 — agent-behavior evals, a parallel lane in `dadaia-evals`: acceptance

- Origin: backlog `agent-behavior-evals` and the operator's fold (§Decisions). Detail lives in `.dadaia/handoff/dadaia-workspace/`: grills `2026-10-03T163043Z-main-thread-grill-evals-050` and `2026-10-03T170932Z-main-thread-grill-evals-format`, and draft `2026-10-03T173359Z-evals-enrichment-workflow-rc8-fr-draft` (finding 1).
- Parallel lane (0149):
  - AC11.2–AC11.6 write only in `repos/dadaia-evals`; no W8–W10 `W:` holds a path there. They run beside W8–W10, one `impl` worktree each, once AC11.0 merges.
  - AC11.0 and AC11.1 write here and queue like any task. AC11.0 shares `_worktree_new.py` and `test_worktree_new.py` with the open `0.5.0d-bug` worktree and T-050-164. AC11.1 shares the root map and `CONTEXT.md` with T-050-158, and `dd-gitflow-default/SKILL.md` with T-050-165.
- Order (root map §3, "no CI job calls a model API", binds until 0177 is accepted and AC11.1 merged): T-050-161 merges → the operator accepts 0177 → AC11.1 and AC11.5 merge, AC11.5 also onto `dadaia-evals` `main` → AC11.6. Before that, `dadaia-evals` holds no workflow that reads a model secret.
- G1 counts this repo only: AC11.0 (one function body and its case) and AC11.1's text. `dadaia-evals` lines are outside the readout; G4's "only job added" is this repo's CI.
- Operator prerequisites, the operator's GitHub acts on `dadaia-evals`:
  - an environment `evals` whose deployment-branch policy allows `main` only;
  - `claude setup-token`, stored as that environment's secret `CLAUDE_CODE_OAUTH_TOKEN`, never a repository secret;
  - extra usage off on the plan;
  - the `ci.yml` job required on `develop` and `main`.
  - Done: `main`, `develop` and `feature/0.5.0` on its origin (5c11f42).
- AC11.0 An associated repo's `impl` reads the main repo's Approved trio (0174's slice, Q-W0):
  - `_worktree_new.new(kind="impl")` reads the trio from the context's main repo, which is `repo` itself for a main repo. It goes through the `context list --json` read `flow_for` already makes: no second read, no branch on repo role.
  - Case, a parametrize row in the owner file `test_worktree_new.py`: an associated repo has `feature/<v>` and the main repo's trio is Approved. `worktree.py new <assoc> --kind impl` exits 0 and prints `[ok]` with `worktrees/<assoc>/<v><l>-impl`. With the main repo's PLAN Draft it exits 1, and its one fix line names `new <main> --kind release`.
- AC11.1 The model-API law is scoped by repo role (0177), shipped from `public/`:
  - The root map line (`public/data/AGENTS.md:43`) changes. No CI job of a context's repos calls a model API, except an evals repo's, and only in `workflow_dispatch` or `schedule` jobs (0177 (2)–(6)).
  - `dd-gitflow-default/SKILL.md` §3b and `CICD-AUTOMATION.md:17` state the same.
  - `CONTEXT.md` gains **Evals repo**: an associated repo whose one role is to measure agent behaviour against the distribution its context ships, and whose CI calls a model only under 0177. It sits beside **Scope** (`CONTEXT.md:102`, today the only entry naming associated repos).
  - The memory pass aligns `sdd-gate-v3`'s model-API line.
  - Check:
    - `grep -rl 'calls a model API' dadaia_workspace/public` and `grep -rl 'evals repo' dadaia_workspace/public` print the same three files.
    - `grep -r dadaia-evals dadaia_workspace/` prints nothing (0179).
    - The root map stays ≤ 8,293 B.
    - `public stage`, `install` and `doctor` are clean, and `no-model-api-in-ci` is green here.
- AC11.2 The `dadaia-evals` skeleton:
  - `AGENTS.md`: what lives here, how to run, `jobs/` never committed, no `push` or `pull_request` trigger calls a model.
  - `README.md`, and `.gitignore` (`jobs/`).
  - `tasks/t1-cold-onboarding/` and `tasks/t2-seeded-bug/`, each holding `instruction.md`, `task.toml`, `environment/Dockerfile`, `tests/test.sh` and `tests/test_grade.py`.
  - `scripts/compare.py`.
  - A Dockerfile holds the environment only (python, uv, git, Node, the Claude CLI pinned). The lib is its last layer, a wheel or a PyPI release (0179). No registry.
  - Check: each task's image builds with the 0.4.7 layer, and `git ls-files jobs` prints nothing.
- AC11.3 T1, cold onboarding:
  - `environment/` builds a `file://` bare repo with one commit, as `bare` does at `tests/e2e/test_onboarding_journey.py:136`.
  - `instruction.md` asks the agent to onboard it following only what `dadaia` prints.
  - `tests/test.sh` runs `uvx pytest tests/test_grade.py` and writes `/logs/verifier/reward.txt`.
  - It passes when `dadaia doctor --json` reports 0 errors, the context is ALIVE and specs are initialized.
  - Check: the unchanged grader passes on a hand-onboarded workspace of 0.4.7 and of the candidate, and fails on an empty one.
- AC11.4 T2, a seeded bug (Arm B):
  - `environment/` builds a small onboarded project with one planted contract break; the instruction gives the operator's confirmation.
  - It passes when:
    - a `BUGS.jsonl` record precedes the fix commit;
    - the RED test fails on the pre-fix sha and passes on the fix;
    - `git diff -U0 -- tests | grep '^-\s*assert'` prints nothing.
  - Check: as AC11.3's, on both versions, with one planted pass and one planted fail.
- AC11.5 The two workflows (0177, 0178), merged after 0177's acceptance and review to the `dadaia-evals` work branch, then through its PR edges to its `main` ahead of rc-12, since GitHub dispatches only a default-branch workflow. A PR edge carries every commit on its branch, so AC11.2–AC11.4 reach `main` too: "early" is before rc-12, not `eval.yml` alone (§Decisions).
  - `ci.yml` makes "CI green per PR edge" real: on `push` and `pull_request`, a GitHub-hosted runner, no secret, no environment. It runs the three checks below.
  - `eval.yml`:
    - Trigger: `workflow_dispatch` with the one input `lib_ref`; `permissions: contents: read`; a GitHub-hosted runner.
    - It stamps `release-please-config.json`'s `release-as` into `pyproject.toml`'s version line before `uv build`, and fails closed when `release-as` is missing.
    - harbor's `claude-code` agent runs three trials per task, at most two at once, on PyPI 0.4.7 and on the candidate wheel; pins and flags are the PLAN's; the model follows the economy template (0022).
    - Auth: the model job alone declares `environment: evals` and reads `CLAUDE_CODE_OAUTH_TOKEN` + `CLAUDE_FORCE_OAUTH=1` at job level.
    - `scripts/compare.py` blocks when a task passing ≥2/3 on 0.4.7 passes ≤1/3 on the candidate, or T1 is below 3/3 on the candidate. Anything else is readout.
    - A secret scan runs over `jobs/` and the summary before any upload or summary write, with the token's value among its patterns. It fails closed.
  - Check (0177's `measured_by`), run by `ci.yml` and by `eval.yml`'s first job, neither holding the secret:
    - The workflow check fails on a workflow that reads the secret or declares `evals`, if it has any of: a trigger other than `workflow_dispatch` or `schedule`, a non GitHub-hosted `runs-on`, the secret at workflow level, or an upload or summary write not preceded by the scan.
    - The scan exits non-zero on a fixture holding a planted token.
    - `compare.py` is red on a planted drop and on T1 at 2/3.
- AC11.6 The first run, as evidence:
  - One `eval.yml` run, `gh workflow run eval.yml -f lib_ref=<tip of feature/0.5.0>` on `dadaia-evals`, against 0.4.7, after AC11.1 merges and AC11.5 reaches `main` with the whole lane.
  - It confirms that the trial runs the candidate wheel: `dadaia capabilities --json` names the stamped version.
  - It confirms that two trials at once stay inside the plan's rate limit: no rate-limit error appears in `jobs/`.
  - A failing grader, unlike a failing agent, is fixed in the grader before closure.
  - Check: a `_RELEASE.json` log entry names the run URL, verdict, tokens and wall time.
- At closure, `agent-behavior-evals` exits `delivered --release 0.5.0`: that needs AC11.6 logged and 0177–0179 ruled (its done-when). The promote gate is rc-12's (§Carried).

## Replaces

- `ci preflight`, its scope error, runner and pytest bootstrap; the Python-only anchors, reaping list, tool names, extension list and `TOOL_CACHE_ENV` list (AC8.9).
- The `api` anchor kind and its alias map, `backlog.py subjects`, `doctor --alias-map` and `--source-root`, SPEC-DOC-005 (AC8.9).
- `dd-test-stewardship`, the tests-AGENTS template, the `Intent:` convention, V28, V29, V31; MEMORY-UPDATE's own canonical-memory rule.
- Duplicate meta-tests, the mutation tooling, meta-test pytest files; nine principles' pytest `Measured by` and P-30's archive clause (0176).
- The hand-kept `features-no-cross-feature` module list and `_KNOWN_MARKERS`, with their equality checks (0176).
- Prose, roster and count asserts; CONTEXT-MAP's `Measured` and skills `Budget` columns; 0143's symbol-list `measured_by`.
- Phase 5's "rewritten", Phase 6's "net ≤ 0"; required `evidence_seam`/`evidence_diff`, their verification, metric 2 over them, direction from `evidence_diff`; the `git log -S` recipe; an unreasoned `none`; the "reopen" wording; §3a row 4's resolve-only wording.
- Ad-hoc child envs, `COVERAGE_FILE` redirects; the cross-context walk; build-identity venv reuse; the bare `KeyError`; the no-block warning for an absent constitution; HOOKS-DRIFT-1's fixed "differs"; the reconcile scratch and unconditional hook rewrite; the deleted surface regex; the second `kind: memory` append.
- The map's unscoped "no CI job calls a model API", in the root map, SKILL.md §3b and `CICD-AUTOMATION.md` (0177); an `impl` worktree reading the trio from its own repo (AC11.0); memory's ledger union merge and step 7's bare conflict line (AC10.14).

## Risks

| Weakness | Mitigation |
|---|---|
| A deleted text assert was a real guard. | It maps to a behaviour assert or a reason in the commit body; the reviewer checks. |
| The `Intent:` strip (about 239 files) conflicts with `bug` worktrees. | W10 waits on it. |
| The root map passes its soft budget (8,293 of 8,192 B). | Basics rewrite existing bullets. |
| The deletion goal is missed. | Planned row by row; the closure logs it. |
| A grader keyed on one version fakes a drop. | AC11.3 and AC11.4 run each grader on both versions. |

## Carried — the 0.5.0 map (ADR 0140; one candidate at a time)

- rc-9: the tests tree mirrors the package, except `tests/contract/test_docs_derived_from_memory.py`, which P-29 names, until check #7 rules; the unit tier spawns no processes, carrying rc-7's slow-class G4 growth (operator 2026-10-02: "Same-runner-class rule; slow-class growth to rc-8 (Recommended)", tied to `unit-tier-without-processes`); the production-faithful hook harness (0163); `worktree-rows-injected-not-monkeypatched`; `windows-integration-coverage-gap`; `repo-ci-sast`. With rc-8, they complete 0167. If pending at rc-8's closure (G6): T-050-183, T-050-187, T-050-188 (0177's accept) and T-050-189 (0180's), with `agent-behavior-evals` or AC10.14's law line.
- rc-10: `public-law-language-neutral`; `dd-ask-me-owned-questioning-skill`, delivering 0165 and `dd-ai-eng-knowhow/AUTHORING.md:134` ("asks the whole frontier at once"), caught by 0165's repaired `measured_by`; `adr-born-at-release-with-options`; `adr-ledger-triage-process-rules`; `architecture-adr-section-generated`; F088, F089, F139–F148.
- rc-11: workspace replication (7 entries, ADRs 0171–0175, 0174 less AC11.0's slice); F084.
- rc-12, the promote: docs site F109, clone detection F110, launch prep F111; the residue (`spec-context-refusals-print-prose`, `privacy-baseline-one-parser`, `ledger-refusals-guess-specs-from-command-shape`, `ledger-reader-one-numbered-tolerant-iterator`, `doctor-in-a-fresh-worktree-lacks-rendered-specs-law`, F060); memory drift F123–F127; bug metrics F001, F004, F005, F009 (re-measured over AC9.3's links); the publish gate F067; `test_docs_derived_from_memory.py` leaves pytest after check #7 rules, `meta-tests-leave-pytest` exits delivered then; the audit checks never run, F137; the removal-authority notes (F069); PyJWT, closing at the ship; the evals gate at the promote (0178): the promote PR head is evaluated and its run logged on the work branch before the merge; at `approve`, `git diff --name-only <evaluated>..<tag>` lists only `CHANGELOG.md`, `.release-please-manifest.json` and `pyproject.toml` (its version line), else `eval.yml` runs on the tag sha first and only a non-blocking verdict approves. Open, the operator's before the promote (F4): ADR 0122's zero active backlog against the four post-0.5.0 evals follow-ups, `evals-release-gate-status`, `evals-harness-lanes-and-benchmark`, `evals-windows-smoke` and `devin-subagent-projection`.

## Open questions for the operator

- None for W8–W11: the 2026-10-03 grill frontiers are empty. F4 is rc-12's (§Carried). Operator acts: 0176, 0177, 0178, 0180 and 0181's acceptances (§Decisions); W11's GitHub prerequisites (the `evals` environment, its secret, the required `ci.yml` job).
