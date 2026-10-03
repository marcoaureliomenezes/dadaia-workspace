# SPEC — Release: 0.5.0, candidate 8 (W8: the test law leaves the library; W9: bug lineage derived; W10: the open bugs)

**Status:** Draft
**Release ID:** 0.5.0
**Owner:** dd-product-engineer
**Opened:** 2026-10-03
**Origin:** backlog:lib-test-guidance-dehydrated,tests-agents-scaffold-without-placeholders,test-intent-docstring-backfill,meta-tests-leave-pytest,preflight-ci-parity-derived,delete-text-count-inventory-asserts,adr-0143-measured-by-checks-the-concept,skill-md-soft-hard-line-limit,memory-update-states-the-truth-correction-lane,bug-fix-adds-never-rewrites-asserts,bug-fix-commit-derived-by-grep,caused-by-proposed-by-blame,focused-review-on-caused-by,bug-terminal-transition-commit-shape,architecture-survey-flat-core-infrastructure,doctor-context-ignores-other-contexts,guidance-messages-name-the-right-target; bugs:test-suite-writes-outside-tmp,ci-preflight-writes-coverage-into-the-repo,hook-entrypoints-invisible-to-coverage,onboarding-next-step-names-another-context,init-on-a-copied-workspace-leaves-a-cli-bound-to-the-original,registry-row-missing-a-key-escapes-reg-schema,pre-push-warns-no-gitflow-block-for-an-absent-specs-tree,upgrade-leaves-reconcile-scratch-behind,removals-shipped-without-recorded-authority,bug-surface-schema-documents-the-deleted-regex; findings:20260930-structural-convergence-F018,20260930-structural-convergence-F028,20260930-structural-convergence-F043,20260930-structural-convergence-F044,20260930-structural-convergence-F045,20260930-structural-convergence-F047,20260930-structural-convergence-F048,20260930-structural-convergence-F049,20260930-structural-convergence-F050,20260930-structural-convergence-F051,20260930-structural-convergence-F069,20260930-structural-convergence-F096,20260930-structural-convergence-F098,20260930-structural-convergence-F101,20260930-structural-convergence-F104,20260930-structural-convergence-F112,20260930-structural-convergence-F135,20260930-structural-convergence-F136

- Sources: the rc-8 grill (handoff `2026-10-02T204839Z-main-thread-grill-rc8-test-candidate`, Q1–Q4); rc-7's gate note (`_RELEASE.json` 2026-10-03T04:58:00Z); the 0170 rulings; PR #278 review F1. The old rc-8/rc-9 drafts are void (Q3). Task ids start at T-050-153.
- `dependabot-pyjwt-open-on-main` is left out: `develop` locks no `pyjwt` since de4e3179a, so the alerts close when the promote PR reaches `main`.

## Objective

- Test knowledge leaves the shipped library, and meta-tests leave pytest for one CI job (0163, 0166, 0167); tests assert behaviour, never a sentence or a hand-kept count (0167).
- Bug lineage is derived from git, and a bug fix adds a case, never rewrites an old assert (0163, 0164).
- SKILL.md gets one size law (0170); 0143's `measured_by` checks the concept.
- The ten open bugs are fixed in the window, one `bug` worktree at a time; production and tests end smaller (§G1).

## Terms

- `CONTEXT.md` holds the terms. **W8**, **W9** and **W10** are this candidate. **DEL** and **FR** keep rc-5's meaning.
- **Meta-test**: a test whose subject is the test suite or the repository (its files, its CI, its ledgers), not a module of the package.
- **Owner file**: the one test file that owns a module's behaviour; a RED enters it as a new case (0146 (5)).
- **Behaviour assert**: an assert on an exit code, an effect on disk or state, or a stable id (finding code, slug, flag). A sentence, a roster or a literal count with a source of truth is not one.
- **Readout**: a measured number logged, never asserted (0142, 0143).
- SCAFFOLD below always means the test tier (V28), never the specs scaffold.

## Bug history read (permanent architecture review)

- `surface: tests` holds 67 records, 34 with a `caused_by`; F018: 22% fix-induced, many born in meta-tests.
- 113 of 183 `fix(bugs):` commits removed asserts. The cause is the law (`dd-bug-resolution` Phases 5–6), so W9 deletes those clauses instead of adding a rule beside them.
- 74% of resolves declare `caused_by: none` by judgement (`bc135641c` repaired 6 links); rc-7's G2 had the same blind spot.
- Size ceilings outlived 0143 twice (`size-ceiling-survives-adr-0143-in-core-file-io-purity`, a89a557ce; `skill_md_line_ceiling`) because its `measured_by` greps symbols; AC8.6 checks the concept.
- 7 resolved records answer "what env does a test child get?", and `harness_env.py` is still not the only builder; AC10.1 deletes the other paths, no eighth patch.
- `session-start-bound-session-omits-onboarding-next-step` (0.4.8) preceded `onboarding-next-step-names-another-context`; the as-is review checks whether it introduced the cross-context walk, and undoes it if so.
- rc-7 T-050-133 verifies `evidence_seam`/`evidence_diff`, 40% of them stale; 0164 (4) retires both, so that code is a §G1 deletion source.

## Decisions

- These ADRs decide: 0071 (as amended by 0163), 0119, 0122, 0123, 0138, 0140, 0142, 0143 (as amended by 0166 and 0170), 0146 (5), 0149, 0152 (2), 0158, 0160 (as amended by 0164), 0163, 0164, 0166, 0167, 0170. All are accepted.
- Grill: Q1 this is rc-8; Q2 0163–0167 accepted; Q3 old rc-8 residue → the promote candidate; Q4 the README byte budget is a readout, done there.
- Bugs are fixed on the spot (Arm B), one `bug` worktree at a time, scheduled by the PLAN (0149).
- Order (root map §1): W8's deletions → W9 → W10's fixes. AC9.2 and AC9.3 land before any W10 bug resolves, so all ten resolve under the 0164 contract (`bugs.py fix`, the blame proposal).
- No new ADR. The `measured_by` repair of 0143 takes the 0138 lane (`chore(adrs): repair …`).

## Gate — G1–G6, applied to W8–W10

- G1 Principles, never a line-count limit (ADR 0142):
  - Every unit walks DELETE → REBUILD → UPDATE → KEEP → ADD, and an ADD names what it could not delete or rebuild.
  - No question gets a second decider, and no rule contradicts another.
  - Readout at `<start>` and `<end>`, by rc-7's commands: production lines `git ls-files -z 'dadaia_workspace/*.py' | xargs -0 cat | wc -l`, test functions `git grep -hE '^\s*(async\s+)?def test_' -- 'tests/*.py' | wc -l`, test lines `git ls-files -z 'tests/*.py' | xargs -0 cat | wc -l`. At birth (8f4ed785f): 25,307 / 1,233 / 45,464.
  - Deletion goal, a readout and never a gate. Production: rc-7 planned −160 and measured +342 (PR #278 review F1), so rc-8 carries the 502-line miss and ends at or below 24,805 production lines. This candidate's own ADDs (AC8.5, AC9.2, AC9.3) count against that goal. The PLAN names the DELETE rows that carry it, and the closure logs planned against measured. Tests: at or below the c4 readout target, 1,167 functions and 43,232 lines.
- G2 `bugs.py status` lists no open record whose `caused_by` names a record or a commit of W8–W10. After AC9.3, a new record's `caused_by: none` carries its stored reason.
- G3 Every still-open bug is re-run at `<end>`. One that no longer reproduces is resolved, citing the commit that removed its cause, and the count is logged.
- G4 CI is green on the three OSes, and `.dadaia/.venv/bin/dadaia doctor --context dadaia-workspace` exits 0. Per-job wall-clock is compared with rc-7's closure only within one runner class, on the median (rc-7 ruling). The one meta-test job (AC8.3) is the only job added.
- G5 A test that a DEL leaves dead leaves in the same commit. A new test follows the root-map test basics (AC8.1), and a new test file enters only when no owner file owns the behaviour.
- G6 At closure, the open findings and `active[]` are re-audited against the merged waves, and the next candidate's SPEC is re-scoped before its PLAN. One `dispositions` entry logs open before, resolved with a commit, and open after.

## W8 — the test law leaves the library: acceptance

- AC8.1 Test knowledge leaves the library (FR `lib-test-guidance-dehydrated`; 0166; F112, F101):
  - `public/skills/dd-test-stewardship/` and `public/templates/tests-AGENTS.md` are deleted with their wiring: persona `skills:` lists, `behavior-map.json` rows, `workspace_layout.REPO_LAW`, `canon.py`, the onboarding list, `doctor_memory.py`, CONTEXT-MAP rows and the tests that pin them.
  - The `Intent:` convention leaves: V31, V28 and V29, and every test docstring's `Intent:` line.
  - The root map gains the test basics by rewriting existing bullets, never by adding a section: RED before the fix at the lowest level; behaviour, not text; mock only at the boundary; a literal expected value; a fix commit never rewrites an old assert. `slop-tests.md`, the QUALITY scaffold and the personas shrink to point at them.
  - Command 1 (0166's `measured_by`): `grep -rn 'dd-test-stewardship\|tests-AGENTS\|Intent:' dadaia_workspace/public` prints nothing, and `.dadaia/.venv/bin/dadaia public doctor` is clean.
  - Command 2: `git grep -n 'Intent:' -- tests` prints nothing.
  - On delivery, `tests-agents-scaffold-without-placeholders` and `test-intent-docstring-backfill` exit `superseded --release 0.5.0`.
- AC8.2 One answer for canonical memory at closure (FR `memory-update-states-the-truth-correction-lane`; 0138):
  - `public/skills/dd-release-implementation/MEMORY-UPDATE.md` stops restating the memory law and points at it: a `### P-NN` principle changes only with its accepted ADR, and any other section is corrected in the closure pass under 0138, naming its code evidence.
  - Its step 7 stops naming a library-internal test (`test_docs_derived_from_memory.py`).
  - Command: `grep -rn 'never touched at closure' dadaia_workspace/public` prints nothing.
- AC8.3 Meta-tests leave pytest for one CI job (FR `meta-tests-leave-pytest`, FR `preflight-ci-parity-derived`; 0163, 0166, 0167; F104):
  - These duplicates are deleted: both `suite_cannot_reach_*` (the conftest sessionfinish covers them), `stewardship_mechanics`, `repo_self_scan` (gitleaks and pre-push cover it), `source_repo_hygiene` (the CI repo-hygiene job covers it), and `test_test_suite_ratchets.py`.
  - The mutation tooling leaves: `tests/scripts/run_mutation_baseline.sh`, its wiring tests, `test_mutation_baseline_scope_stdlib_only.py`, `[tool.mutmut]` and the optional `mutation` group. The closure memory pass states that mutation evidence is operator tooling, kept outside the repo.
  - Each unique guard becomes a script that one CI job runs. Each script is proven by a planted violation that turns it red.
  - The CI/preflight parity script derives both sides, from `checks_for()` and from `ci.yml`. `_LOCAL_MARKERS` and `_CI_MARKERS` are deleted, and a check added to `ci.yml` alone fails the script.
  - Command: `git ls-files tests | grep -E 'suite_cannot_reach|stewardship_mechanics|repo_self_scan|source_repo_hygiene|test_suite_ratchets|mutation_baseline|slop_ratchets|ci_preflight_ci_gating_parity'` prints nothing, and the CI job's log names each moved guard. The as-is review may add further meta-test files to this list, but never remove one.
- AC8.4 Tests assert behaviour (FR `delete-text-count-inventory-asserts`; 0167):
  - Asserts on the prose of a doc, a law file or a skill are deleted. The pre-push denylist and the review grep keep covering leaks.
  - A CLI assert checks exit code, effect and stable id; an exception assert checks type or attribute; a `fix:` line is executed, never matched as text. No new `--json` is added.
  - Inventory and count pins are deleted, or derived from their source of truth. CONTEXT-MAP's `Measured` column is deleted, and size becomes a live readout.
  - Command 1: `git grep -nE 'len\(.*\) *== *[0-9]{2,}' -- tests` prints nothing.
  - Command 2: `dadaia_workspace/public/data/CONTEXT-MAP.md` has no `Measured` column.
  - Readout at `<start>` and `<end>`: the string-assert count, by the as-is review's one grep. The closure names each survivor as a stable id.
- AC8.5 SKILL.md soft and hard limits (FR `skill-md-soft-hard-line-limit`; 0170):
  - `behavior-map.json` carries `skill_md_line_soft` 333 beside `skill_md_line_ceiling` 500, and the behavior-map schema declares the new key.
  - `dadaia doctor` emits `SKILL-MD-LENGTH` (WARNING, never failing a gate) for each projected SKILL.md over the soft limit. Its one fix line is `Operator action:`, names the real SKILL.md path, and tells the agent to split that SKILL.md into its `references/*.md` and/or `scripts/`.
  - CONTEXT-MAP §3 loses the skills `Budget` column.
  - Command: 0170's `measured_by`, verbatim, including the test row `skill-md-over-the-soft-limit-warns`, which reads the value from the map.
- AC8.6 ADR 0143 measures the concept (FR `adr-0143-measured-by-checks-the-concept`; 0138 lane):
  - 0143's `measured_by` is repaired in place (`chore(adrs): repair …`). It names a check that no test or script compares a file's line or byte count against a constant, except the declared `skill_md_line_ceiling` (0170).
  - It runs as an AC8.3 script; a planted size row turns it red.
- AC8.7 `CONTEXT.md` gains **Meta-test**, **Owner file**, **Behaviour assert**; the SCAFFOLD test tier leaves its Scaffold homonym entry.

## W9 — bug lineage derived: acceptance

- AC9.1 A bug fix adds a case, never rewrites one (FR `bug-fix-adds-never-rewrites-asserts`; 0163, 0164 (4)):
  - `dd-bug-resolution` Phase 5 loses "existing test rewritten", and Phase 6 loses "production AND tests net ≤ 0".
  - The RED enters the owner file as a parametrize row with a literal expected value, named by behaviour and never by the bug slug. Rewriting a pre-existing assert is its own commit, with a reason.
  - The review step names `git diff -U0 -- tests | grep -E '^-\s*assert'`.
  - `REQUIRED_BY_VERB` no longer requires `evidence_seam` or `evidence_diff`. The schema keeps both fields optional, so history stays intact, and `evidence_loop` stays required. The code that verifies the two retired fields leaves with them.
  - Command (0163's `measured_by`): `grep -rn 'net test lines\|<bug-id>#<id>\|mutmut' dadaia_workspace/public` prints nothing.
- AC9.2 The fix commit is derived (FR `bug-fix-commit-derived-by-grep`; 0164 (1)):
  - `bugs.py fix <id>` prints the fix sha, its test files and the numstat. It finds the commit through shape 3's `^fix\(bugs\): .*<id>`, or through shape 4's `(<sha>)`. No schema field is added.
  - `LINEAGE.md` uses this verb in place of the `git log -S` recipe.
  - Command: over every record resolved since 2026-08-27, `bugs.py fix` prints a sha or lists the record as unlinked. The closure logs both counts.
- AC9.3 `caused_by` is proposed by blame (FR `caused-by-proposed-by-blame`; 0164 (2), (3)):
  - `resolve` blames the lines that the staged diff removes and prints the candidates. It skips regenerated files, using the skip set the projection declares it writes, and it skips squash `(#n)` and `refactor(T-…)` commits.
  - It refuses a `--caused-by` outside the candidates, and it refuses `none` when candidates exist, unless `--lineage-reason` is given. That reason is stored.
  - One sentence carries the semantics in the schema, in `LINEAGE.md` and in the bugs law: "the fix of X wrote the lines this fix corrects". The schema's "reopen" wording leaves.
  - Case: `none` with candidates exits non-zero; with `--lineage-reason` it passes.
- AC9.4 A declared cause focuses the review (FR `focused-review-on-caused-by`; 0164 (5)):
  - `dd-code-review` carries the step: when `caused_by` is not `none`, the review reads every line the prior fix wrote, and the verdict states REBUILD of the unit or why not.
  - `PILLAR-BUGS` measures those verdicts. This step is taught by the skill and never enforced by a gate.
- AC9.5 Terminal bug transitions have a commit shape (FR `bug-terminal-transition-commit-shape`):
  - `dd-gitflow-default` §3a row 4 widens to every terminal transition without code (resolve, reject, defer, supersede): `chore(bugs): <verb> <id> — <reason, or by <task-id> (<sha>)>`. No row is added.
  - AC9.1's §3a edit and this one land as one edit.

## W10 — the open bugs, harm-ordered (Arm B; one `bug` worktree each)

Every RED is a behaviour assert (AC8.4) entering its owner file. Each MEDIUM resolves before any LOW is opened.

- AC10.1 One test child-env builder (DEL `test-suite-writes-outside-tmp`; F018, F049, F135, F136):
  - Every process a test spawns takes its env from `tests/fixtures/harness_env.py`: a tmp `HOME`, `PYTHONDONTWRITEBYTECODE=1`, and `DADAIA_FENCED_ROOTS`. The parent's `COVERAGE_FILE` passes through unchanged.
  - Command 1: `git grep -nE 'os\.environ\.copy\(\)|dict\(os\.environ|\*\*os\.environ' -- tests` prints only the builder.
  - Command 2: run `env -u PYTHONDONTWRITEBYTECODE HOME=<tmp> python -m pytest -q -n 3 -p no:randomly`. After it, `find dadaia_workspace tests -name __pycache__` prints nothing, and `<tmp>/.cache/pip` does not exist.
  - F136: scored from a CI E2E run of `test_one_line_bootstrap.py`.
- AC10.2 One decider of the coverage data file (DEL `ci-preflight-writes-coverage-into-the-repo`; F048):
  - `dadaia ci preflight` is the only decider, and it sets `COVERAGE_FILE` outside the repo tree. `ci.yml`'s private redirects are deleted.
  - Command: `git grep -nE 'COVERAGE_FILE"?\]? *[:=]' -- . ':!dadaia_workspace/features/ci_preflight'` prints nothing. After a preflight run, `git status --porcelain --ignored | grep -c coverage` prints `0`.
- AC10.3 Hook entrypoints are visible to coverage, and their cost is bounded (DEL `hook-entrypoints-invisible-to-coverage`; F051; 0118):
  - In CI's coverage JSON, `hooks/ctx_inject.py` and `sdd_post_gate` are above 0.
  - One case, parametrized over the hook lanes, asserts that a hook's operation count does not grow with workspace size. It counts operations and never measures time.
- AC10.4 A run judges only its own context (DEL `onboarding-next-step-names-another-context`, FR `doctor-context-ignores-other-contexts`, and FR `guidance-messages-name-the-right-target`; F028, F096, F098):
  - One decider answers "which context does this run judge": the bound context, or the one `--context` names. The cross-context walk is deleted.
  - Case: with two contexts and the session bound to X, the next step's `step_id` and context slug are X's.
  - Case: with slop only in another context's repo, `doctor --context X` exits 0.
  - HOOKS-DRIFT-1 reports an absent hook under its own finding code, distinct from a differing hook. The entry's root-whitelist clause was already delivered by T-050-146.
- AC10.5 A copied workspace gets its own CLI (DEL `init-on-a-copied-workspace-leaves-a-cli-bound-to-the-original`; F045):
  - `init` reuses a venv only when its prefix and its entry-script shebangs point at `DIR/.dadaia/.venv`.
  - Case: after `cp -a <ws> <copy>` and `init <copy>`, `head -1 <copy>/.dadaia/.venv/bin/dadaia` names `<copy>`, and `<ws>` is untouched.
- AC10.6 A registry row missing a key is unreadable (DEL `registry-row-missing-a-key-escapes-reg-schema`):
  - The one registry parse (0162) raises `SchemaVersionError`, naming the row and the key, and the doctor reports `REG-SCHEMA` with one `Operator action:` fix line.
  - Case: a row without `created_at` gives exit 1 with `REG-SCHEMA`, and no `KeyError`.
- AC10.7 An absent specs tree is reported as absent (DEL `pre-push-warns-no-gitflow-block-for-an-absent-specs-tree`; F043):
  - With no `specs/constitution.md`, `core/gitflow.py` reports the absence with `fix: .dadaia/.venv/bin/dadaia specs init --context <ctx>`.
  - Case: assert the finding and execute the fix line. No message word is asserted.
- AC10.8 Upgrade leaves no scratch (DEL `upgrade-leaves-reconcile-scratch-behind`; F044; 0104):
  - `.dadaia/tmp/reconcile/` no longer exists after `init`.
  - `init` names each repo whose `pre-push` hook it refreshed. The case asserts the repo slug.
- AC10.9 Every 0.5.0 removal has a recorded authority (DEL `removals-shipped-without-recorded-authority`; F047, F069):
  - Each listed removal gets, in §Removal authority, its accepted ADR or the Replaces line that removed it, and a release-note line for the promote CHANGELOG; the as-is review fills it (SPEC amendment). No authority: a question to the operator.
- AC10.10 The bug schema states the one surface decider (DEL `bug-surface-schema-documents-the-deleted-regex`):
  - `bug-record-v1.schema.json`'s `surface` description says "a directory name tracked in the repo".
  - Command: `grep -c 'a-z0-9_-' dadaia_workspace/public/schemas/bugs/bug-record-v1.schema.json` prints `0`.
- AC10.11 `default-suite-calls-a-real-model-through-codex` was resolved by b5013bbfb. The closure resolves F050, citing that commit.

## Architecture survey (FR `architecture-survey-flat-core-infrastructure`)

- AC8.8 `dd-architecture-survey` runs read-only over the flat `core/` and `infrastructure/`, with the entry's concept map as input. The ring rule is unchanged.
- Its proposals reach the main thread's intake before the tree-mirror candidate's PLAN, so the mirror is laid out over the grouping the operator rules.

## Removal authority (AC10.9; filled by the as-is review)

| removal | commit | authority | release-note line |
|---|---|---|---|
| `jinja2` and the `[claude-sdk]` extra | de4e3179 | — | — |
| `certify-dadaia-workspace.sh`, `lint-memory-atoms.py`, `lint-dadaia-cli-reachability.py` | 56073ec4, d5f00170, 8353a7df | — | — |
| SPEC-DOC-028/037/007, `specs init --force` | f7cc8621 | — | — |

## Replaces

- `dd-test-stewardship`, `public/templates/tests-AGENTS.md`, the `Intent:` convention, and ratchets V28, V29 and V31 (0166).
- MEMORY-UPDATE's "never touched at closure" clause.
- The duplicate meta-tests, `test_test_suite_ratchets.py`, the mutation tooling, and the parity test's hand-kept marker dicts. Unique guards move into the CI job's scripts.
- Prose, roster and literal-count asserts, CONTEXT-MAP's `Measured` column, and the skills `Budget` column.
- 0143's symbol-list `measured_by`.
- Phase 5's "existing test rewritten" and Phase 6's "net ≤ 0", the required `evidence_seam`/`evidence_diff` and their verification, the `git log -S` lineage recipe, an unreasoned `caused_by: none`, and the schema's "reopen" wording.
- §3a row 4's resolve-only wording.
- The ad-hoc test child envs, `ci.yml`'s `COVERAGE_FILE` redirects, the repo-root `.coverage` default, and the test children that inherit the operator's `HOME`.
- The cross-context walk; build-identity venv reuse; `_from_dict`'s bare `KeyError`; the no-block warning for an absent constitution; HOOKS-DRIFT-1's "differs" for an absent hook; the reconcile scratch and the silent hook rewrite; the schema's deleted surface regex.

## Risks

| Weakness | Mitigation |
|---|---|
| Deleting text asserts loses a real guard. | Each maps to a behaviour assert in its owner file, or a reason in the commit body; the reviewer checks. |
| The `Intent:` strip touches about 239 test files and conflicts with a parallel `bug` worktree. | The PLAN runs the strip with no `bug` worktree open (0149). |
| Adding the test basics pushes the root map further past its soft budget (8,293 B against 8,192). | The basics rewrite existing bullets (AC8.1), and the closure logs the readout. |
| W10 bugs resolve before 0164's tooling, under the old contract. | AC9.2 and AC9.3 precede every W10 resolve (§Decisions). |
| The production deletion goal is not met. | The PLAN plans it row by row (§G1). The closure logs any miss, and the reviewer judges it. |

## Proposed split (operator rules before approval)

This candidate stays inside ADR 0152 (2) only if the tree mirror and the unit tier wait. Proposed: **rc-9** takes `tests-tree-mirrors-the-package`, `unit-tier-without-processes`, `worktree-rows-injected-not-monkeypatched`, `windows-integration-coverage-gap`, the production-faithful hook harness (c4 AC9.5 residue, which must precede the mirror), and rc-7's slow-class G4 growth. These complete 0167's `measured_by`.

- **rc-10** is the promote candidate: the old rc-9, reworked, plus the old rc-8 residue (Q3).
- Why: the mirror's `git mv` touches most test files and conflicts with every parallel `bug` worktree; after W8–W10 it moves REDs already in final shape, over the survey's grouping (AC8.8). "No split": they join this Origin as W11.

## Open questions for the operator

- OQ1 The split above. Recommended: yes.
- OQ2 0165's delivery: `grill-one-question-with-options` was rejected as absorbed by `dd-ask-me-owned-questioning-skill`. That entry amends 0165 and 0146, and it belongs to the ask-me/ADR family (`adr-born-at-release-with-options`). Recommended: deliver it with that family, not here.
- OQ3 `removals-shipped-without-recorded-authority`: F047 proposes rejecting it as not a broken tool contract. Recommended: keep it here (AC10.9), because the authority table costs one SPEC amendment.
