# SPEC — Release: 0.5.0

**Status:** Draft
**Release ID:** 0.5.0
**Owner:** dd-product-engineer
**Opened:** 2026-10-20
**Origin:** backlog:promote-gate-050,launch-operator-acts; bugs:mcp-on-main-is-vulnerable-to-session-exhaustion; findings:20260930-structural-convergence-F043,20260930-structural-convergence-F044,20260930-structural-convergence-F053,20260930-structural-convergence-F054,20260930-structural-convergence-F057,20260930-structural-convergence-F060,20260930-structural-convergence-F067,20260930-structural-convergence-F069,20260930-structural-convergence-F080,20260930-structural-convergence-F084,20260930-structural-convergence-F088,20260930-structural-convergence-F089,20260930-structural-convergence-F097,20260930-structural-convergence-F109,20260930-structural-convergence-F110,20260930-structural-convergence-F111,20260930-structural-convergence-F124,20260930-structural-convergence-F136,20260930-structural-convergence-F137,20260930-structural-convergence-F139,20260930-structural-convergence-F140,20260930-structural-convergence-F141,20260930-structural-convergence-F142,20260930-structural-convergence-F143,20260930-structural-convergence-F144,20260930-structural-convergence-F145,20260930-structural-convergence-F146,20260930-structural-convergence-F147,20260930-structural-convergence-F148

---

## Bug window review

**Window:** the 39 records closed between rc-20's birth (2026-10-19T21:18:53Z) and rc-21's birth (2026-10-20T15:14:19Z): 36 resolved and 3 superseded, read in `BUGS.jsonl` and `_archive/bugs_histo.jsonl` at `bb8eb0fbb`. `caused_by`: 18 name a bug, 17 a task, 4 `none`. Two children of an rc-20 fix fall inside the window: `rc-merge-reads-the-context-registry-twice` and `mem-drift-rebuild-silences-the-report-only-contract-case`. rc-20's readout puts metric 9 at 34 rebuild-due. Each fix is found by its id line and read with `git show --numstat`, tests and specs excluded; `fix_files` is write-once (U10), so unit counts are lower bounds.

| fix (ids) | commit(s) | unit | net src | verdict | reason |
|---|---|---|---|---|---|
| verdict-refusal-fix-cannot-clear-after-a-sync, gone-tree-merge-judges-the-upstream-not-the-merge, red-separation-splits-paths-on-blanks, red-separation-act-names-an-implementation-commit, kept-refusal-offers-keep-only, clean-of-an-unmerged-lane-offers-only-merge, orphan-row-judges-merge-against-the-checked-out-head, merge-scan-copies-the-denylist-precedence | `1ec2d8ef2`, `bc8ef6d08`, `e42f8c2b9` | `_worktree_end.py` merge-gate refusals | -4, -16, +7 | KEEP | One structural REBUILD, net negative, no child bug. |
| check-failure-fix-line-names-findings-that-do-not-exist, restored-tree-comes-back-unlocked, closure-refusal-fix-line-points-at-a-phase-that-cannot-go-back | `dca9cf8bc`, `68408987e`, `8e5358872` | `_refusal.py`, `_specs.py`, `_worktree_new.py`, `_worktree_git.py` | +7, +7, +4 | REBUILD (FR2) | Three bugs in four days on the check-relay and tree-open pair. The lock string is spelled in three places (`_worktree_git.py:37`, `_worktree_new.py:103`, `_worktree_pause.py:97`). A second parser of check's text remains (`_specs.py:87,94` `_VERDICT`). The rc number is parsed by hand (`_worktree_new.py:62`). |
| bug-skill-registry-reader-crashes-on-a-bad-row, fix-cite-retires-the-older-same-subject-fix, context-reader-reads-the-cwd-workspace-for-a-non-repo, rc-merge-reads-the-context-registry-twice | `4cca33968`, `bd8ec5ce2`, `902c574ed` | `_specs.py`, `_git.py`, `_bugs_check.py` | +3, +1, +2 | KEEP, noted | REBUILT in rc-20 FR3; all descend from ADR 0273's lookup. One more child in `_git.fix_commit` or `_specs.context_repos` makes the lookup the REBUILD target. |
| bugs-check-refuses-task-fixed-records | `f21c0e01e`, `c50735192`, `fa25106c7` | `_bugs_check._uncited` | 0 | KEEP | The check judges resolved records only, and its fix line is the archive act. ADR 0273's consequence text still names the old fix line, so ADR 0278 amends it (FR11). |
| push-gate-rewrite-help-says-one-commit, fold-subject-is-the-oldest-folded-subject | `e76d35cc5` | `chokepoints/fold.py` | +29 | KEEP | The fold now has one owner. The reviewer accepted the module boundary. |
| own-repo-name-is-refused-as-a-private-term (superseding privacy-scan-refuses-a-context-naming-itself) | `abe327033` | `privacy_check.py`, `container.py` | +9 | KEEP | The `own=True` flag argument (`container.py:72`) goes to 0.6.0 intake. |
| subagent-bind-rebinds-the-parent-session-across-contexts (superseding cross-context-agent-rebinds-the-whole-session), planted-git-file-anchors-the-workspace-root | `97aae3e1c`, `123e33b4c` | `gate_policy.py`, `workspace_layout.py` | +13, +21 | KEEP | ADR 0275. `123e33b4c` is a `ruff format` commit labelled `refactor(bugs):`, so under ADR 0273 (1) it becomes the cited fix. FR1 AC1.3 closes that gap. |
| memory-drift-reads-the-installed-feature-list, mem-drift-rebuild-silences-the-report-only-contract-case | `0c711b436`, `58383c322` | `doctor_memory.py` MEM-DRIFT-1 | -8, 0 | DELETE (FR3) | A second fix in four days on one rule. Its child came from a stale plant in a duplicated contract test. The rule reads the library's own `features/` folder, so it never fires in a user's repo. |
| first-pass-fix-line-chains-five-steps, closure-check-raises-a-traceback-outside-git, dist-obstruction-check-misses-a-dangling-link, reachability-probe-overrides-the-users-ssh-command, migrate-reports-a-stamp-three-registry-as-stamp-two, consumer-recipe-expects-stamp-two, cli-library-skill-omits-pause-as-a-dist-writer | `3551e1e0d`, `e6e18a924`, `7a58a0c03`, `eaf4ac497`, `d79ee4a67`, `45172a8d0` | one unit each | -1, +2, +1, +6, 0, 0 | KEEP | One fix per unit, no child. |
| pyproject-keeps-the-published-version-after-a-deploy, tests-and-evals-install-a-published-release | `cf063d8c8` | `eval.yml`, `release.yml`, `pyproject.toml`, `repo.py` | +13 | KEEP | An ADR-backed REBUILD (0274). |
| windows-contract-coverage-runs-at-its-timeout, export-hard-test-cannot-remove-read-only-git-objects-on-windows, damaged-pause-bundle-crashes-the-worker-on-windows, fix-line-tests-hand-spell-the-git-path-on-windows (superseding check-relay-fix-line-spells-the-path-two-ways-on-windows) | `b45a1d323`, `7b6585c31`, `4908ef2a5`, `e49537270` | `ci.yml`, test files | 0, 0, +8, 0 | KEEP | This was the third cap raise in 13 days. The structural question of the Windows leg's runtime goes to 0.6.0 intake, not to a fourth raise. |

**Overfitting check:** one fix changed a contract test (`58383c322`, the MEM-DRIFT-1 plant, under a main-thread ruling), and FR3 deletes that rule. No fix special-cases a test value; the positive nets are reviewer-accepted module boundaries.

## 1. Problem

The operator's words:

- Roadmap Q7: "4 rcs: 18-21 (Recommended)", with rc-21 as "prove and ship: scorecard >= 9, T1+T2+T3 run and recorded, launch acts, promote".
- Roadmap Q1: "all of it must be handle seriously before we deliver the version 0.5.0". Q2 adds "0 known defects".
- Roadmap Q3: "Gate: page live first (Recommended)".
- rc-21 grill, 2026-10-20: Q1 "Keep: resolve at promote, carried"; Q2 "Close both in 0277 (Recommended)"; Q3 "Yes, all four (Recommended)"; Q4 "/projetos/dadaia-workspace + amend 0273 (Recommended)"; summary "Confirmed, go (Recommended)".

Gaps, verified at `bb8eb0fbb`:

- The scorecard last passed at `f5263f80f`; 108 commits since changed `dadaia_workspace/public` (67 files, +1327/-570), unjudged.
- T3 has never run against a model. ADR 0269 says "T3 must be stable (k=3) before rc-21".
- ADR 0242 publishes only with zero open findings, yet `20260930-structural-convergence` holds 29 `open` findings (9 HIGH). `promote-gate-050` and `launch-operator-acts` are still `active`.
- ADR 0178 (5) allows only the release-please files between E and the tag, but ADR 0269 (a) puts `_RELEASE.json` there: the approve step would fall into a second eval run. ADR 0242's D1-D10 readout has no measure.
- `pyproject.toml:37` and the GitHub homepage both point at PyPI. The GitHub topics lack `cursor`, `devin`, `github-copilot` and `agent-skills`.
- `dd-gitflow-default` §3a has five gaps (L1-L5, FR1).
- ADR 0273's consequence still names the old fix line of `_uncited` (`_bugs_check.py:207`).
- `CHANGELOG.md:357` and `:389` list D1 and the skills repo as pending.

## 2. Measurable goals

| # | goal | target | source |
|---|---|---|---|
| 1 | agentic scorecard | every cell >= 9 from both judges at the frozen tip | `.dadaia/reports/dadaia-workspace/agentic-scorecard/<UTC>/` |
| 2 | evals on E | T1 3/3, T2 >= 2/3, T3 >= 2/3, verdict `non-blocking` | the `eval.yml` job summary; `evals/scripts/compare.py` |
| 3 | ADR 0242 | 0 open findings; no Origin slug in `active[]`; only the carried mcp bug open | `audit.py check`, `BACKLOG.json`, `bugs.py status` |
| 4 | E is the evaluated tree | `git diff --name-only E..<promote PR head>` lists only `specs/releases/0.5.0/_RELEASE.json` | git |
| 5 | REBUILD pack and deletions | net source lines <= 0 per FR2 and < 0 per FR3, tests excluded | `git diff --numstat` |
| 6 | launch | homepage and topics as FR7 states, set after the page is live | `gh repo view --json homepageUrl,repositoryTopics` |
| 7 | readout metrics 1, 2, 4, 6, 7, 9 | each read beside rc-20's (34/38 (89%), 7/22 (32%), n/a, 0, 0, 34) and its target (<= 20%, >= 70%, <= 4 h, 0, 0, 0) | `verdict.py stats 0.5.0-rc21`; rc-20's summary |

## 3. Non-goals (0.6.0)

- The roadmap's Q2 OUT list stays out: worktree-layout-per-context, context-show-derives-worktrees, multi-platform-by-construction-migration, bug-stats-hotspots-and-age, audit-project-scorecard-cycle, repo-ci-sast-gates, eval-codex-lane-in-library-ci, evals-benchmark-lanes, release-approve-requires-evals-gate, windows-smoke-t1-at-release.
- No Codex, Copilot or Devin eval lane. No `evals/gate` commit status (ADR 0269 (c)). ADR 0225 stays `proposed`.
- The Hermes T3 spike runs only if the operator sets its keys, and as readout only.
- Out, to the main thread's intake as one 0.6.0 proposal: the T3 grader LOWs (unregistered rows, `PIP_NO_INDEX`), the rc-20 review loose ends, `own=True`, the Windows leg runtime, the `gate_policy`/`_anchors` LOWs.
- Unregistered bug proposals are not requirements; the bug law governs them.
- No `release.yml` change. The approve step stays the operator's manual read.
- No hand-written `[0.5.0]` CHANGELOG section (FR10).

## 4. Requirements

Wave ranking, by the pick:

1. Law, skills and dev loop: FR1 (law) and FR11 (ADRs, in the define).
2. Shared foundation: FR2 (REBUILD pack) and FR3 (deletions).
3. Features and bugs: FR4 (ADR 0242 dispositions, specs only) and FR10 (CHANGELOG text).
4. Promote-facing, in this order: FR7 AC7.1 (the repo edit), FR5 (scorecard, the last job that changes text), then closure and E, FR6, FR8, FR7 AC7.2, FR9.

### FR1 — `dd-gitflow-default` §3a law gaps L1-L5 (main-thread ruling: "One law job for dd-gitflow-default §3a gaps L1-L5 — reason: lying/missing law text is decided in scope")

- AC1.1 (L1) Shape 3 has a row for a fix that is itself a test change: a `test(<id>):` commit whose body carries the `fix(bugs): <id> — …` line, as `58383c322` does. Test: none, law text; the scorecard and the review judge it.
- AC1.2 (L2) The define rows name the `pyproject.toml` version line and its commit, `chore(release): rc-<N> is labelled <release>rc<N>`. Test: none, law text; `scripts/guards/repo.py` version-label already pins the value.
- AC1.3 (L3) There is a shape for a code revert (git's own `Revert "<subject>"`). A format-only commit carries no `fix(bugs)` or `refactor(bugs)` line, because ADR 0273 (1) would make it the record's cited fix. Test: none, law text.
- AC1.4 (L4) The archive row of shape 4 lists `wt-main` job trees beside lanes and the `wt-rc`. Test: none, law text.
- AC1.5 (L5) Item 1 of the block list in `specs/bugs/AGENTS.md` §2 (the scaffold's) states which red counts, so that a red run of the work branch's checks, like the CI integration run that triggered rc-20's hotfix, reads one way. The line requires no remote or CI of a user's repo (public boundary). The exact words are the main thread's ruling in the job file. Test: none, law text.
- AC1.6 The scaffold edit re-pins its canon digests (`public/templates/shipped-hashes.json`), and the repo's own copy stays byte-identical. Every skill that cites a changed row is swept. Test: unit (the existing digest and copy pins).

### FR2 — the REBUILD pack (bug window; main-thread ruling: "Bug-window REBUILD pack, net ≤ 0 — reason: lighter option, three units")

- AC2.1 One helper in `_worktree_git.py` re-adds a tree locked. `_worktree_new.py` and `_worktree_pause.py` call it. Afterwards `git grep -n -- '--lock' dadaia_workspace/public/skills/dd-gitflow-default/scripts` prints one line. Test: unit (the `restored-tree-comes-back-unlocked` contract tests stay green and unloosened).
- AC2.2 The drop of a merged branch has one source that returns argv. Both the printed act (`drop_steps`) and the executed path (`_worktree_end._remove`) come from it. Test: unit.
- AC2.3 `_specs.py`'s `_VERDICT` regex goes. A check refusal's message is read only by `_refusal`'s one parser. Check's exit status alone still decides. Test: unit (the check-relay contract tests stay green and unloosened).
- AC2.4 `_worktree_new.py` reads the rc number through `_grammar.candidate_number`, and the hand parse at `:62` goes. Test: unit (the CLOSURE-act test, unchanged).
- AC2.5 Net source lines <= 0 over every file the pack touches, tests excluded. Test: none; `git diff --numstat`.

### FR3 — the four operator-ordered deletions (operator, Q3: "Yes, all four (Recommended)")

- AC3.1 One copy of the judgment-only doctor contract test is deleted: `tests/cli/commands/test_doctor.py:452` or `tests/core/test_cli_line__fix_line_contract.py:1013`. The PLAN names which. The other stays as the contract's one home. Test: unit (the kept copy).
- AC3.2 `tests/features/export/test_scan.py:116-123` is deleted. Its AST grep duplicates the import-linter contract `features-no-cross-feature` (`setup.cfg:93`), which stays the one check. Test: the lint contract.
- AC3.3 Dead state is deleted with the asserts that pin it: `Decision.message_listed` (`branch_policy.py:39`, `test_ci.py:326`), `SeveralWorkBranches.text` (`core/gitflow.py:105`, `test_gitflow.py:227`), and `schema_version_before` on the already-current migrate path (`state_v2.py`, `test_state_v2.py:91`). Test: unit (the surviving asserts).
- AC3.4 MEM-DRIFT-1 leaves the shipped doctor (`features/specs/doctor_memory.py`, `rules.py:83` and their tests) and becomes a repo guard under `scripts/guards/`. The guard checks the library's own `features/` map against `specs/memory/ARCHITECTURE.md` and is planted red once. The closure memory pass moves `ARCHITECTURE.md:52`, `QUALITY.md:54` and the `workspace-doctor` atom. Test: unit (the guard's plant).
- AC3.5 Each removed or moved assert lands in a `test(...)` commit that names the operator's ruling "Yes, all four (Recommended)" (root map §1). Test: none.
- AC3.6 Net source lines < 0 over FR3, tests excluded. Test: none; `git diff --numstat`.

### FR4 — ADR 0242: findings, backlog, publish-gate checks (main-thread ruling: "ADR 0242 compliance in scope — reason: accepted law")

- AC4.1 Each of the 29 Origin findings gets a terminal disposition through `audit.py disposition`. Its one-line reason cites evidence from a read-only `dd-researcher` re-verification. Then `audit.py close --sha <sha>` runs. A disposition adds no gate and no hand-written CHANGELOG section (FR10). Afterwards `audit.py check --specs specs` exits 0 and no finding of any audit reads `open`. Test: none; `audit.py check`.
- AC4.2 Before E, the main thread triages the rc-13 residuals (summary at 2026-10-11T01:06:40Z) into bug proposals or discards (`promote-gate-050` (5)). Test: none.
- AC4.3 At closure, `promote-gate-050` and `launch-operator-acts` exit `delivered --release 0.5.0`. Every slug that a 0.5.0 Origin names is then absent from `active[]`. Test: unit (existing, `test_delivered_outside_the_release_origin_is_refused`).
- AC4.4 Before the promote PR merges, each kept publish-gate check of `promote-gate-050` (1) is a `note` in `_RELEASE.json` naming sha E. The kept checks are 1, 2, 3, 4+19, 5+6, 7, 8, 9 reduced, 12 reduced, and 17+18. Check 2 reads as ADR 0242 words it. Check 5 reads as FR10. Check 9 is ADR 0274 (3)'s two-label journey. The D1-D10 line reads as ADR 0277. Test: none; `release.py check` and the log.

### FR5 — the agentic scorecard >= 9 (roadmap Q7: "scorecard >= 9"; constitution §5)

- AC5.1 Round 1 runs at the define tip. Two independent `dd-code-reviewer` judges score every cell (R1-R8, P1-P3, S1-S12, C1-C6) against `.dadaia/reports/dadaia-workspace/agentic-scorecard/20261017T0519Z/rubric.md`. Each cell below 9 carries `path:line` and becomes a PLAN task (main-thread ruling: "Scorecard round 1 at the define tip"). Test: none; the record.
- AC5.2 A fix deletes or corrects text before it adds any. No fix adds a mechanism. Test: none; the review.
- AC5.3 The final round runs at the frozen tip, after every job that writes `dadaia_workspace/public/**`. Both judges put every cell at >= 9, and the record lives under `.dadaia/reports/dadaia-workspace/agentic-scorecard/<UTC>/`. Test: none; the record is the evidence.

### FR6 — evals T1, T2, T3 (ADR 0269, as amended by 0274 (5) and 0277)

- AC6.1 Once `gh` works and the work branch is pushed, the main thread dispatches `gh workflow run eval.yml --ref feature/0.5.0` as an early T3 readout ("T3 readout eval once gh works — reason: ADR 0269 'T3 stable at k=3 before rc-21'"). Its run URL and per-task passes are logged as a `note`. It gates nothing, and a T3 below 2/3 returns to the main thread before E. Test: E2E (the run).
- AC6.2 The gating run is on sha E. It shows T1 3/3, T2 >= 2/3 and T3 >= 2/3 on the candidate, and `compare.py` prints `non-blocking`. The operator reads the verdict (ADR 0178 (4)). Test: E2E (the run).
- AC6.3 A `chore(release):` commit, before the promote PR merges, puts a `note` in `_RELEASE.json` naming the run URL, the verdict and E. Afterwards `git diff --name-only E..<promote PR head>` lists only `specs/releases/0.5.0/_RELEASE.json`. Test: none; git.

### FR7 — launch acts (backlog `launch-operator-acts` D5; operator, Q4: "/projetos/dadaia-workspace + amend 0273 (Recommended)")

- AC7.1 Before E, `pyproject.toml:37` reads `Homepage = "https://marco-menezes.com/projetos/dadaia-workspace"`, and the comment at `:34-35` says the homepage is that page. Nothing else in the file changes. Test: none, metadata; the line is the evidence.
- AC7.2 After FR8's page is live: `gh repo edit --homepage https://marco-menezes.com/projetos/dadaia-workspace --add-topic cursor --add-topic devin --add-topic github-copilot --add-topic agent-skills`. `gh repo view --json homepageUrl,repositoryTopics` shows the URL and the four names, and a `note` records it (ADR 0242: "D5 is performed at the promote and recorded"). Test: none; the `gh` read.

### FR8 — the portfolio prod deploy before the promote (roadmap Q3: "Gate: page live first (Recommended)")

- AC8.1 After E, the portfolio's claim table, which pins `2059b779e`, is re-checked against E in the portfolio site's own lane. A mismatch is corrected there (main-thread ruling: "Portfolio claim table re-checked against E; prod deploy right before the promote"). Test: none in this repo.
- AC8.2 The operator approves the portfolio site's develop → main deploy. Before the dadaia-workspace promote PR merges, `https://marco-menezes.com/projetos/dadaia-workspace` serves the dadaia-workspace page. Test: none; an HTTP read is the evidence.

### FR9 — the promote sequence (`dd-gitflow-default` §2 steps 8-11; ADRs 0178, 0242, 0269, 0277)

- AC9.1 The order is fixed:
  1. The rc-21 closure reconcile runs: backlog exits, bug archive, memory pass, and the `llms-full.txt` regeneration. E is the last commit that is not `_RELEASE.json`.
  2. The push follows, and every CI job goes green.
  3. FR6 runs on E, and its record lands.
  4. On the operator's explicit order, the PR feature/0.5.0 → develop opens. It needs the reviewer's APPROVED, security lens included, quoted in the PR, and green CI.
  5. FR8, then FR7 AC7.2.
  6. The promote PR develop → main opens, with APPROVED on the integration tip, and merges.
  7. The release-please PR follows. Its approve step applies ADR 0178 (5) as ADR 0277 amends it. Publication happens only on the operator's manual approval.
  8. The `archive/` tag is set, the work branch is renamed, and `release.py ship` runs on the next work branch.

  Test: none; the PRs and the log.
- AC9.2 The mcp record is carried (operator, Q1: "Keep: resolve at promote, carried"). `release.py ship` runs with `--allow-open mcp-on-main-is-vulnerable-to-session-exhaustion`. The log holds a `note` that starts `Operator authorization verbatim:`, quotes those words and names that id, and the closure summary's `carried` field names the id. The record resolves after the promote merge closes the alert on main. Test: none; `ship` refuses without all three.

### FR10 — CHANGELOG pending lines (main-thread ruling: "CHANGELOG historic headings untouched — reason: the file's preamble")

- AC10.1 `CHANGELOG.md:357` no longer lists D1 (`CLAUDE_API_KEY`, removed by ADR 0025) as pending, and `:389` no longer lists the skills repo as pending. Every historic heading stays as written. release-please writes the one new `[0.5.0]` section. Test: none, doc text.

### FR11 — the define's law records (operator, Q2: "Close both in 0277 (Recommended)"; Q4: "… + amend 0273 (Recommended)")

- AC11.1 ADR 0277 is proposed in this define and accepted by the main thread with the operator's words. It amends 0269 (no 0.4.7 pairing, per 0274 (5)) and 0178 (5) (the tag-diff set gains `specs/releases/0.5.0/_RELEASE.json`), and it states T3 as the 0.5.0 adoption readout in place of ADR 0242's D1-D10. Test: none; `doctor` `LEDGER-ADR-SCHEMA` and its `measured_by`.
- AC11.2 ADR 0278 is proposed and accepted the same way. It amends 0273's stale consequence: `_uncited`'s fix line is the one archive act naming every missed id. Test: unit (its `measured_by`, the existing archive-act tests).

### Replaces

- FR2: three spellings of the locked re-add; the text-vs-argv pair for the merged-branch drop; `_specs._VERDICT`; the hand parse of the rc number.
- FR3: one copy of the judgment-only doctor test; the AST grep in `test_scan.py`; `Decision.message_listed`, `SeveralWorkBranches.text`, and `schema_version_before` on the current path; doctor rule MEM-DRIFT-1, which becomes a repo guard.
- FR11: ADR 0178 (5)'s tag-diff set without `_RELEASE.json`; ADR 0242's D1-D10 readout; ADR 0273's old fix-line consequence.

### Closure

- Backlog exits, `delivered --release 0.5.0`: `promote-gate-050` and `launch-operator-acts`. The bug archive takes `mem-drift-rebuild-silences-the-report-only-contract-case` and every record resolved in rc-21. The mcp record stays open and carried (AC9.2).
- The memory pass covers the atoms behind MEM-DRIFT-1 (`ARCHITECTURE.md`, `QUALITY.md`, `workspace-doctor`), the agent-evals atom (the recorded run), the PyPI-distribution atom (Homepage), the ADR index and `catalog.json`, and it regenerates `llms-full.txt`. All of it lands before E (ADR 0269 (a)).

## 5. Constraints and risks

- Preconditions: the operator runs `gh auth login`. rc-20 (183 commits) is pushed and CI is green before any rc-21 job merges ("Push rc-20 and clear CI before rc-21 jobs land"). A red goes to the red-CI loop.
- ADR 0269 (a): after E, no file changes except `_RELEASE.json`, so every repo edit (AC7.1, FR10, the memory pass) lands before E.
- Constitution §5: the scorecard is the last implementation job of the final rc, after every text-changing job, before the gating eval and before the closure summary. The AC6.1 readout gates nothing.
- Net lines: FR2 <= 0 and FR3 < 0. FR1 and FR5 delete or correct text before adding any.
- Public boundary: no AC requires a remote, CI, `gh` or a toolchain of a user's repo. `gh`, `eval.yml` and the portfolio are this repo's developer acts.
- Risk: a T3 below floor at the readout, or a red gating run, costs a re-cut E. Its cause enters by Arm B.
- Risk: FR1 and FR3 change public text; a read-only `dd-researcher` pre-mortem names the consumers before approval, and the PLAN answers each.

## 6. Open questions

none. The PLAN closes the seams that remain open: which doctor test copy stays (AC3.1), the helper names (FR2), and the guard's home (AC3.4).
