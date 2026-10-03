# SPEC — Release: 0.5.0, candidate 8 (W8: the test law and the library pipeline leave; W9: bug lineage derived; W10: the open bugs)

**Status:** Draft
**Release ID:** 0.5.0
**Owner:** dd-product-engineer
**Opened:** 2026-10-03
**Origin:** backlog:cli-ships-no-library-pipeline,lib-test-guidance-dehydrated,tests-agents-scaffold-without-placeholders,test-intent-docstring-backfill,meta-tests-leave-pytest,preflight-ci-parity-derived,delete-text-count-inventory-asserts,adr-0143-measured-by-checks-the-concept,skill-md-soft-hard-line-limit,memory-update-states-the-truth-correction-lane,bug-fix-adds-never-rewrites-asserts,bug-fix-commit-derived-by-grep,caused-by-proposed-by-blame,focused-review-on-caused-by,bug-terminal-transition-commit-shape,architecture-survey-flat-core-infrastructure,doctor-context-ignores-other-contexts,guidance-messages-name-the-right-target; bugs:test-suite-writes-outside-tmp,ci-preflight-writes-coverage-into-the-repo,hook-entrypoints-invisible-to-coverage,onboarding-next-step-names-another-context,init-on-a-copied-workspace-leaves-a-cli-bound-to-the-original,registry-row-missing-a-key-escapes-reg-schema,pre-push-warns-no-gitflow-block-for-an-absent-specs-tree,upgrade-leaves-reconcile-scratch-behind,bug-surface-schema-documents-the-deleted-regex,release-memory-appends-a-second-entry-on-rerun; findings:20260930-structural-convergence-F018,20260930-structural-convergence-F028,20260930-structural-convergence-F043,20260930-structural-convergence-F044,20260930-structural-convergence-F045,20260930-structural-convergence-F047,20260930-structural-convergence-F048,20260930-structural-convergence-F049,20260930-structural-convergence-F050,20260930-structural-convergence-F051,20260930-structural-convergence-F096,20260930-structural-convergence-F097,20260930-structural-convergence-F098,20260930-structural-convergence-F100,20260930-structural-convergence-F101,20260930-structural-convergence-F104,20260930-structural-convergence-F112,20260930-structural-convergence-F135,20260930-structural-convergence-F136

- Sources: grills of 2026-10-02 (rc-8, Q1–Q4) and 2026-10-03 (train, Q1–Q6); review B1–B11; PR #278 F1. Task ids start at T-050-153.
- Left out: `dependabot-pyjwt-open-on-main`, which closes at the ship (rc-12); `removals-shipped-without-recorded-authority`, rejected (Q5).

## Objective

- The library ships no pipeline of its own: `ci preflight` and the pytest bootstrap leave first (Q2).
- Test knowledge leaves the library (0166). Meta-tests leave pytest for one CI job, and tests assert behaviour (0163, 0167).
- Bug lineage is derived from git, and a bug fix adds a case (0163, 0164). SKILL.md gets one size law (0170).
- The ten open bugs are fixed, and production and tests both end smaller (§G1).

## Terms

- `CONTEXT.md` holds the terms. **W8**, **W9** and **W10** are this candidate; **DEL** and **FR** keep rc-5's meaning.
- **Meta-test**: a test whose subject is the suite or the repository (its files, CI or ledgers), not a package module.
- **Guard script**: a meta-test's unique check, moved into a script that the one CI job runs.
- **Owner file**: the one test file owning a module's behaviour; a RED enters it as a new case (0146 (5)).
- **Behaviour assert**: an assert on an exit code, an effect, or a stable id (a finding code, slug or flag). A sentence, a roster, or a count that has a source of truth is not one.
- SCAFFOLD here is the test tier (V28), never the specs scaffold.

## Bug history read (permanent architecture review)

- The preflight surface is a fix chain:
  - `ci-preflight-unusable-outside-the-source-repo` was resolved by a refusal, a symptom patch.
  - `preflight-doctor-judges-instance-state-ci-never-sees` followed, and `ci-preflight-writes-coverage-into-the-repo` is still open.
  - The structural cause is a library verb that serves only this repo, so AC8.9 deletes it.
- `surface: tests` holds 67 records, 34 with a `caused_by`. F018 finds 22% fix-induced, many born in meta-tests.
- 113 of 183 `fix(bugs):` commits removed asserts. The cause is the law (`dd-bug-resolution` Phases 5–6), so W9 deletes those clauses.
- 74% of resolves declare `caused_by: none` by judgement, and `bc135641c` repaired 6 links.
- Size ceilings outlived 0143 twice (a89a557ce; `skill_md_line_ceiling`), because its `measured_by` greps symbols.
- 7 resolved records on test-child env; `harness_env.py` is not yet the only builder (AC10.1).
- `session-start-bound-session-omits-onboarding-next-step` preceded `onboarding-next-step-names-another-context`. The as-is review checks whether it introduced the cross-context walk, and undoes it if so.
- rc-7 T-050-133 verifies `evidence_seam` and `evidence_diff`, 40% of them stale. 0164 (4) retires both fields.

## Decisions

- These ADRs decide: 0071 (as amended by 0163), 0104, 0118, 0119, 0122, 0123, 0138, 0140, 0142, 0143 (as amended by 0166 and 0170), 0146 (5), 0149, 0152 (2), 0158, 0160 (as amended by 0164), 0162, 0163, 0164, 0166, 0167 (partly: the rest goes to rc-9), 0170.
- Operator, 2026-10-03, quoted verbatim:
  - Train: "you will only create now the RC8 ... we will wait till we finish the RC8". rc-9..rc-12 are the map in §Carried.
  - Q1 "Keep in 0.5.0 as rc-11 (Recommended)".
  - Q2 "Yes, into rc-8 (Recommended)".
  - Q3 "Register as bugs, fix in rc-8 W10 (Recommended)".
  - Q4 "Derive it from `bugs.py fix` (Recommended)".
  - Q5 "Reject; authority table goes to rc-12 notes (Recommended)".
  - Q6 "rc-10 via dd-ask-me (Recommended)".
- Order (root map §1):
  1. AC8.9 (delete the pipeline).
  2. The rest of W8.
  3. W9.
  4. W10, which waits on AC9.3 and on AC8.1's `Intent:` strip. Its parallel width is the PLAN's Parallel schedule (0149).
- No new ADR. 0143's repair takes the 0138 lane.

## Gate — G1–G6, applied to W8–W10

- G1 Principles, never a line-count limit (0142):
  - DELETE → REBUILD → UPDATE → KEEP → ADD; an ADD names what it could not delete. No question gets a second decider.
  - Readout at `<start>` and `<end>`:
    - production lines: `git ls-files -z 'dadaia_workspace/*.py' | xargs -0 cat | wc -l`;
    - test functions: `git grep -hE '^\s*(async\s+)?def test_' -- 'tests/*.py' | wc -l`;
    - test lines: `git ls-files -z 'tests/*.py' | xargs -0 cat | wc -l`;
    - guard-script lines and guard checks, by the glob the PLAN gives their home, copied here by amendment.
  - At birth (8f4ed785f): 25,307 / 1,233 / 45,464 / 0 / 0.
  - Deletion goal, a readout:
    - Production: rc-7 planned −160 and measured +342 (PR #278 F1), so rc-8 carries the 502-line miss and ends at or below 24,805, counting its own ADDs. The PLAN names the DELETE rows that carry it; AC8.9 is the largest.
    - Tests: at or below the c4 target, 1,167 functions and 43,232 lines, with guard scripts counted beside them, never hidden.
- G2 `bugs.py status` lists no open record whose `caused_by` names a W8–W10 record or commit.
- G3 Every still-open bug is re-run at `<end>`. One that no longer reproduces is resolved, citing the commit that removed its cause.
- G4 CI is green on the three OSes, and `.dadaia/.venv/bin/dadaia doctor --context dadaia-workspace` exits 0. Wall-clock is compared with rc-7's within one runner class, on the median. The guard-script job is the only job added.
- G5 A test that a DEL leaves dead leaves in the same commit. A new test follows the root-map test basics (AC8.1).
- G6 At closure, findings and `active[]` are re-audited, and rc-9 is defined from the §Carried line. One `dispositions` entry logs open before, resolved, and open after.

## W8 — the test law and the library pipeline leave: acceptance

- AC8.9 (lands first) The CLI ships no library pipeline (FR `cli-ships-no-library-pipeline`; supersedes FR `preflight-ci-parity-derived`, F104):
  - Deleted: `dadaia ci preflight` (`cli/commands/ci.py`, `features/ci_preflight/`) and its tests; `_ensure_ci_toolchain`'s pytest bootstrap; every law line naming `ci preflight`.
  - This repo's local CI equivalent lives in its own `AGENTS.md` and `.github/`, and its worktree test command still runs.
  - `code` anchors resolve any tracked file path, with the symbol optional. The `cli` anchor kind, `TOOL_CACHE_ENV`, `REPO_TREE_ARTIFACTS` reaping, `venv_guard`'s tool names and `_memory_drift`'s extension list each become language-neutral or are deleted; the as-is review picks, and deletion is preferred.
  - Commands:
    - `git grep -n 'ci_preflight\|_ensure_ci_toolchain' -- dadaia_workspace` prints nothing;
    - `grep -rn 'ci preflight' dadaia_workspace/public` prints nothing;
    - `.dadaia/.venv/bin/dadaia ci preflight` exits 2.
  - Case: a fresh `init` venv fails `import pytest`.
  - Case: a backlog `code` anchor to a `.go` file passes BL-SCHEMA.
  - At closure, `preflight-ci-parity-derived` exits `superseded --release 0.5.0`.
- AC8.1 Test knowledge leaves the library (FR `lib-test-guidance-dehydrated`; 0166; F112, F101):
  - Deleted: `public/skills/dd-test-stewardship/` and `public/templates/tests-AGENTS.md`, with their wiring: persona `skills:`, `behavior-map.json` rows, `workspace_layout.REPO_LAW`, `canon.py`, the onboarding list, `doctor_memory.py`, CONTEXT-MAP rows, and the tests that pin them.
  - The `Intent:` convention leaves: V28, V29, V31, and every test docstring's `Intent:` line.
  - The root map gains the test basics by rewriting existing bullets:
    - RED before the fix, at the lowest level;
    - behaviour, not text;
    - mock only at the boundary;
    - a literal expected value;
    - a fix commit never rewrites an old assert.
  - `slop-tests.md`, the QUALITY scaffold and the personas point at those basics.
  - Command 1 (0166's `measured_by`): `grep -rn 'dd-test-stewardship\|tests-AGENTS\|Intent:' dadaia_workspace/public` prints nothing, and `.dadaia/.venv/bin/dadaia public doctor` is clean.
  - Command 2: `git grep -n 'Intent:' -- tests` prints nothing.
  - At closure, `tests-agents-scaffold-without-placeholders` and `test-intent-docstring-backfill` exit `superseded --release 0.5.0`.
- AC8.2 One answer for canonical memory at closure (FR `memory-update-states-the-truth-correction-lane`; 0138):
  - Concept: one statement, one home. `MEMORY-UPDATE.md` states no rule of its own about canonical memory; it points at the memory law (a `### P-NN` principle changes only with its ADR, and any other section is corrected under 0138).
  - Its step 7 names no library-internal test.
  - Command: `grep -c 'QUALITY.md' dadaia_workspace/public/skills/dd-release-implementation/MEMORY-UPDATE.md` prints `1`, the pointer.
  - Command: `grep -rn 'never touched at closure' dadaia_workspace/public` prints nothing.
- AC8.3 Meta-tests leave pytest for one CI job (FR `meta-tests-leave-pytest`; 0163, 0166, 0167):
  - Duplicates are deleted:
    - `stewardship_mechanics`, covered by conftest;
    - `repo_self_scan`, covered by gitleaks and pre-push;
    - `source_repo_hygiene`, covered by the CI repo-hygiene job.
  - Deleted with their law: V28, V29 and V31, and the mutation tooling (`tests/scripts/run_mutation_baseline.sh`, its wiring tests, `test_mutation_baseline_scope_stdlib_only.py`, `[tool.mutmut]`, the `mutation` group). The memory pass states that mutation evidence is operator tooling.
  - Guards that move: V26 (`test_test_suite_ratchets.py`); V32, V33 and V37–V40 (`test_slop_ratchets.py`, and V32's twin in `test_import_linter_ignore_cap.py`); `suite_cannot_reach_a_real_workspace` and `suite_cannot_reach_the_instance`; and AC8.6's check. Each guard script carries a planted violation that turns it red, run in the CI job.
  - The parity check dies with preflight (AC8.9) and does not move.
  - A listed file that the as-is review proves unique moves its guard into a script; no guard is lost.
  - Command: `git ls-files tests | grep -E 'suite_cannot_reach|stewardship_mechanics|repo_self_scan|source_repo_hygiene|test_suite_ratchets|mutation_baseline|slop_ratchets|import_linter_ignore_cap|ci_preflight'` prints nothing, and the CI job's log names each moved guard.
- AC8.4 Tests assert behaviour (FR `delete-text-count-inventory-asserts`; 0167):
  - Concept: no test pins a value whose source of truth lives elsewhere: a sentence the law owns, or a roster or count that the code owns.
  - Prose asserts on a doc, law or skill are deleted.
  - A CLI assert checks exit code, effect and stable id; an exception assert checks type or attribute; a `fix:` line is executed. No new `--json` is added.
  - Count pins are deleted or derived from their source. CONTEXT-MAP's `Measured` column is deleted.
  - Command 1, the mechanical floor: `git grep -nE 'len\(.*\) *== *[0-9]{2,}' -- tests` prints nothing.
  - Command 2: CONTEXT-MAP has no `Measured` column.
  - Below that floor, the reviewer judges against the concept. The string-assert readout at `<start>`/`<end>` names each survivor's stable id.
- AC8.5 SKILL.md soft and hard limits (FR `skill-md-soft-hard-line-limit`; 0170):
  - `behavior-map.json` carries `skill_md_line_soft` 333 beside `skill_md_line_ceiling` 500, and the schema declares it.
  - `doctor` emits `SKILL-MD-LENGTH` as a WARNING over the soft limit, with one `Operator action:` fix line naming the real SKILL.md path and its split into `references/*.md` and/or `scripts/`.
  - CONTEXT-MAP §3 loses the skills `Budget` column.
  - Command: 0170's `measured_by`, verbatim.
- AC8.6 ADR 0143 measures the concept (FR `adr-0143-measured-by-checks-the-concept`; 0138 lane):
  - 0143's `measured_by` is repaired in place. It names a check that no test or script compares a file's line or byte count against a constant, except the two keys 0170 declares in `behavior-map.json`: `skill_md_line_soft` and `skill_md_line_ceiling`.
  - The check is an AC8.3 guard script, and a planted size row turns it red.
- AC8.7 `CONTEXT.md` gains **Meta-test**, **Guard script**, **Owner file** and **Behaviour assert**. The SCAFFOLD test tier leaves the Scaffold homonym entry.
- AC8.8 `dd-architecture-survey` runs read-only over `core/` and `infrastructure/` (FR `architecture-survey-flat-core-infrastructure`), with the ring rule unchanged. Its proposals reach intake before rc-9's PLAN.

## W9 — bug lineage derived: acceptance

- AC9.1 A bug fix adds a case (FR `bug-fix-adds-never-rewrites-asserts`; 0163, 0164 (4)):
  - Phase 5 loses "existing test rewritten", and Phase 6 loses "production AND tests net ≤ 0".
  - The RED is a parametrize row in the owner file, with a literal expected value and a behaviour name. Rewriting an old assert is its own commit, with a reason.
  - The review names `git diff -U0 -- tests | grep -E '^-\s*assert'`.
  - `REQUIRED_BY_VERB` drops `evidence_seam` and `evidence_diff`. They become optional in the schema, and their verification code leaves. `evidence_loop` stays.
  - `PILLAR-BUGS` row 44 loses its `evidence_seam` clause.
  - Command (0163's `measured_by`): `grep -rn 'net test lines\|<bug-id>#<id>\|mutmut' dadaia_workspace/public` prints nothing.
- AC9.2 The fix commit and its direction are derived: one decider (FR `bug-fix-commit-derived-by-grep`; 0164 (1); Q4):
  - `bugs.py fix <id>` prints the fix sha, test files and numstat, found through shape 3's `^fix\(bugs\): .*<id>` or shape 4's `(<sha>)`. No schema field is added.
  - `LINEAGE.md` uses it in place of `git log -S`.
  - `bugs.py stats`' `direction:` rows are computed from that numstat, never from `evidence_diff`.
  - In `PILLAR-BUGS`, row 27 (metric 3) and row 45 (net-positive) read the same numstat.
  - Command: for every record resolved since 2026-08-27, `bugs.py fix` prints a sha or lists the record as unlinked. Both counts are logged.
- AC9.3 `caused_by` is proposed by blame (FR `caused-by-proposed-by-blame`; 0164 (2), (3)):
  - `resolve` blames the lines that the staged diff removes and prints the candidates. It skips the regenerated files the projection declares, squash `(#n)` commits and `refactor(T-…)` commits.
  - It refuses a `--caused-by` outside the candidates, and `none` when candidates exist, unless `--lineage-reason` is given and stored.
  - One semantics in the schema, `LINEAGE.md` and the bugs law: "the fix of X wrote the lines this fix corrects".
  - Case: `none` with candidates exits non-zero; with `--lineage-reason` it passes.
- AC9.4 `caused_by` other than `none` makes the review read every line the prior fix wrote and state REBUILD or why not (FR `focused-review-on-caused-by`; 0164 (5)). It lives in `dd-code-review` and is measured by `PILLAR-BUGS`, never gated.
- AC9.5 `dd-gitflow-default` §3a row 4 widens to every terminal transition without code: `chore(bugs): <verb> <id> — <reason, or by <task-id> (<sha>)>`, one edit with AC9.1's (FR `bug-terminal-transition-commit-shape`).

## W10 — the open bugs, harm-ordered (Arm B)

W10 opens after AC9.3 and AC8.1's `Intent:` strip merge. Each RED is a behaviour assert in its owner file, and the MEDIUMs come first.

- AC10.1 One test child-env builder (DEL `test-suite-writes-outside-tmp`; F018, F049, F135, F136). Re-cut on top of AC8.9:
  - Every test child takes its env from `harness_env.py`: a tmp `HOME`, `PYTHONDONTWRITEBYTECODE=1` and `DADAIA_FENCED_ROOTS`.
  - Command 1: `git grep -nE 'os\.environ\.copy\(\)|dict\(os\.environ|\*\*os\.environ' -- tests` prints only the builder.
  - Command 2: after `env -u PYTHONDONTWRITEBYTECODE HOME=<tmp> python -m pytest -q -n 3 -p no:randomly`, `find dadaia_workspace tests -name __pycache__` prints nothing, and `<tmp>/.cache/pip` is absent.
  - F136 is scored from a CI E2E run.
- AC10.2 Coverage data lands outside the repo (DEL `ci-preflight-writes-coverage-into-the-repo`; F048). Re-cut on AC8.9:
  - On every documented path (CI, and the plain `pytest --cov` lines of `tests/README.md` and `tests/AGENTS.md`), no coverage file appears in the checkout.
  - One decider, whose location the as-is review picks.
  - Case: after each path, `git status --porcelain --ignored | grep -c coverage` prints `0`.
- AC10.3 Hooks are visible to coverage and bounded in cost (DEL `hook-entrypoints-invisible-to-coverage`; F051; 0118):
  - `hooks/ctx_inject.py` and `sdd_post_gate` are above 0 in CI's coverage JSON.
  - One case, parametrized over the hook lanes, counts operations at the boundary seam (the filesystem or subprocess fake), with no counter in production code. The count does not grow with workspace size.
- AC10.4 A run judges only its own context (DEL `onboarding-next-step-names-another-context`; FR `doctor-context-ignores-other-contexts`; FR `guidance-messages-name-the-right-target`, its SessionStart part; F028, F096, F098):
  - One decider: the bound context, or the one `--context` names. The cross-context walk is deleted.
  - Case: bound to X with two contexts, the next step's `step_id` and slug are X's.
  - Case: with slop only in another context's repo, `doctor --context X` exits 0.
- AC10.5 A copied workspace gets its own CLI (DEL `init-on-a-copied-workspace-leaves-a-cli-bound-to-the-original`; F045):
  - `init` reuses a venv only when its prefix and shebangs point at `DIR/.dadaia/.venv`.
  - Case: after `cp -a` and `init <copy>`, `head -1 <copy>/.dadaia/.venv/bin/dadaia` names `<copy>`, and the original is untouched.
- AC10.6 A registry row missing a key is unreadable (DEL `registry-row-missing-a-key-escapes-reg-schema`; 0162):
  - The one parse raises `SchemaVersionError`, and doctor reports `REG-SCHEMA` with an `Operator action:` line.
  - Case: a row without `created_at` exits 1 with `REG-SCHEMA`, and no `KeyError` is raised.
- AC10.7 An absent specs tree is reported as absent (DEL `pre-push-warns-no-gitflow-block-for-an-absent-specs-tree`; F043):
  - With no constitution, `core/gitflow.py` reports the absence with `fix: .dadaia/.venv/bin/dadaia specs init --context <ctx>`.
  - Case: the finding is asserted, and the fix line is executed.
- AC10.8 An upgrade leaves no scratch and no silent rewrite (DEL `upgrade-leaves-reconcile-scratch-behind`; F044; 0104):
  - `.dadaia/tmp/reconcile/` is absent after `init`.
  - `init` rewrites a project repo's `pre-push` only when it differs from the projected bytes, and that is preferred over a new print.
  - Case: a second `init` leaves the hook's bytes untouched, and a differing hook is refreshed.
- AC10.9 Withdrawn: the bug was rejected (Q5), and F069 moves to rc-12.
- AC10.10 `bug-record-v1.schema.json`'s `surface` description states the tracked-directory rule (DEL `bug-surface-schema-documents-the-deleted-regex`).
  - Command: `grep -c 'a-z0-9_-' dadaia_workspace/public/schemas/bugs/bug-record-v1.schema.json` prints `0`.
- AC10.11 Resolved at closure by citation: F050 by b5013bbfb; F047 by the commit `chore(bugs): reject removals-shipped-without-recorded-authority`; F100 by the commit exiting `init-announces-codex-trust` rejected (T-050-71 removed the trust INFO on purpose).
- AC10.12 HOOKS-DRIFT-1 reports an absent hook as absent (FR `guidance-messages-name-the-right-target`, its HOOKS-DRIFT-1 part; F098):
  - An absent hook gets its own finding code, distinct from a differing hook.
  - Case: delete a projected hook; doctor prints the absent-hook code, and its fix line restores the hook when executed.
  - The root-whitelist clause was delivered by T-050-146.
- AC10.13 A memory rerun appends nothing (DEL `release-memory-appends-a-second-entry-on-rerun`; F097):
  - A second `release.py memory` over an empty window is refused with a fix line, or exits 0 and leaves the log unchanged; the as-is review picks which.
  - Case: the log's `kind: memory` entries are unchanged after the rerun.

## Replaces

- `dadaia ci preflight`, the pytest bootstrap, and the Python-only anchors, cache env, reaping, tool names and extension list (AC8.9).
- `dd-test-stewardship`, the tests-AGENTS template, the `Intent:` convention, and V28, V29, V31.
- MEMORY-UPDATE's own canonical-memory rule.
- The duplicate meta-tests, the mutation tooling, and meta-test pytest files, whose guards move to scripts.
- Prose, roster and count asserts; CONTEXT-MAP's `Measured` column; and the skills `Budget` column.
- 0143's symbol-list `measured_by`.
- Phase 5's "rewritten" clause and Phase 6's "net ≤ 0"; the required `evidence_seam` and `evidence_diff` with their verification; direction read from `evidence_diff`; the `git log -S` recipe; an unreasoned `none`; and the "reopen" wording.
- §3a row 4's resolve-only wording.
- The ad-hoc test child envs and the `COVERAGE_FILE` redirects; the cross-context walk; build-identity venv reuse; the bare `KeyError`; the no-block warning for an absent constitution; HOOKS-DRIFT-1's "differs" for an absent hook; the reconcile scratch and the unconditional hook rewrite; the deleted surface regex; and the second `kind: memory` append.

## Risks

| Weakness | Mitigation |
|---|---|
| A deleted text assert was a real guard. | It maps to a behaviour assert or a reason in the commit body, and the reviewer checks. |
| Deleting the pytest bootstrap breaks this repo's worktree test command. | AC8.9's task updates the repo `AGENTS.md` command and proves it green. |
| The `Intent:` strip (about 239 files) conflicts with `bug` worktrees. | W10 waits on it (§Decisions). |
| The root map passes its soft budget (8,293 of 8,192 B). | Basics rewrite existing bullets. |
| The deletion goal is missed. | Planned row by row; the closure logs it. |

## Carried — the 0.5.0 map (ADR 0140; one candidate at a time)

- rc-9: the tests tree mirrors the package; the unit tier spawns no processes; `worktree-rows-injected-not-monkeypatched`; `windows-integration-coverage-gap`; `repo-ci-sast`. With this candidate, these complete 0167.
- rc-10: `public-law-language-neutral`; `dd-ask-me-owned-questioning-skill`, which delivers 0165; `adr-born-at-release-with-options`; `adr-ledger-triage-process-rules`; `architecture-adr-section-generated`; F088, F089 and F139–F148; dd-ask-me also covers `dd-ai-eng-knowhow/AUTHORING.md:134` ("asks the whole frontier at once"), which 0165's repaired `measured_by` catches.
- rc-11: workspace replication (7 entries, ADRs 0171–0175) and F084.
- rc-12, the promote:
  - docs site, clone detection and launch prep;
  - the residue: `spec-context-refusals-print-prose`, `privacy-baseline-one-parser`, `ledger-refusals-guess-specs-from-command-shape`, `ledger-reader-one-numbered-tolerant-iterator`, `doctor-in-a-fresh-worktree-lacks-rendered-specs-law`;
  - memory drift and metrics;
  - the removal-authority release notes (F069);
  - PyJWT, which closes at the ship.

## Open questions for the operator

- None: the 2026-10-03 grill frontier is empty.
