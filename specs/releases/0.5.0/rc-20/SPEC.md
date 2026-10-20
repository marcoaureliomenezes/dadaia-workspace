# SPEC — Release: 0.5.0

**Status:** Draft
**Release ID:** 0.5.0
**Owner:** dd-product-engineer
**Opened:** 2026-10-19
**Origin:** backlog:adoption-and-discoverability,eval-t3-discovery; bugs:bug-skill-registry-reader-crashes-on-a-bad-row,check-failure-fix-line-names-findings-that-do-not-exist,clean-of-an-unmerged-lane-offers-only-merge,cli-library-skill-omits-pause-as-a-dist-writer,closure-check-raises-a-traceback-outside-git,closure-refusal-fix-line-points-at-a-phase-that-cannot-go-back,consumer-recipe-expects-stamp-two,dist-obstruction-check-misses-a-dangling-link,first-pass-fix-line-chains-five-steps,fix-cite-retires-the-older-same-subject-fix,fold-subject-is-the-oldest-folded-subject,gone-tree-merge-judges-the-upstream-not-the-merge,kept-refusal-offers-keep-only,mcp-on-main-is-vulnerable-to-session-exhaustion,memory-drift-reads-the-installed-feature-list,merge-scan-copies-the-denylist-precedence,migrate-reports-a-stamp-three-registry-as-stamp-two,orphan-row-judges-merge-against-the-checked-out-head,planted-git-file-anchors-the-workspace-root,push-gate-rewrite-help-says-one-commit,reachability-probe-overrides-the-users-ssh-command,red-separation-act-names-an-implementation-commit,red-separation-splits-paths-on-blanks,restored-tree-comes-back-unlocked,subagent-bind-rebinds-the-parent-session-across-contexts,verdict-refusal-fix-cannot-clear-after-a-sync

---

## Bug window review

**Window:** the 12 records closed from rc-19's birth (2026-10-19T03:08:41Z) to rc-20's birth (2026-10-19T21:18:53Z), read in `BUGS.jsonl` and `_archive/bugs_histo.jsonl` at `740dc6927`; rc-19's review judged the 6 closed before it. `verdict.py stats 0.5.0-rc19` reads metric 9 at 18 rebuild-due: all 18 bugs rc-19's window closed sit on a path with 2 or more fix commits (`bugs.py stats`). Each fix is found by its id line (`git log -E --grep '^(fix|refactor)\(bugs\): .*<id>'`). Verdicts: 9 REBUILD in 4 units (R1-R4), 3 KEEP. A fifth REBUILD, R5, is a closure act and has no record.

| bug id | fix commits | unit | verdict | reason (evidence) |
|---|---|---|---|---|
| `stats-crashes-on-a-release-state-that-breaks-its-schema` | `3148f9b08`, `d12be0bf3`, `38ed65b80` | the check relay: `_stats.table`, `_worktree_new._refuse_unready`, `_specs.check_release`, `_refusal.py` | REBUILD R1 | `caused_by: stats-crashes-on-an-unreadable-release-state`. The relay took three REBUILD commits in one rc, and it caused the next two rows. |
| `check-relay-reads-a-pass-from-text-not-exit-status` | `a26b1d3b9` (group) | same | REBUILD R1 | `caused_by` the row above. `_refusal.py` gained a parser (`38ed65b80`, +7) that the next fix deleted (−7). `check_release` still regex-parses check's text (`_specs.py:66`), beside the one parser `_refusal.fix_of`. `_stats.py` carries 8 bugs. |
| `rc-tree-absent-fix-line-does-not-clear-its-refusal` | `a26b1d3b9` (group) | `_worktree_new._refuse_unready` | REBUILD R1 | `caused_by` the first row. Same group fix. `_worktree_new.py` carries 7 bugs. |
| `denylist-scan-runs-only-at-pre-push` | `b6f91fdc7`, `0192947e6`, `305b84a09`, `5261998e0` | the push-gate fold and content path: `cli/commands/ci.py` `_fold`, `_rewrite_unpublished`, `_content_decision`; `push_gate.py`; the merge-scan call in `_worktree_end.py` | REBUILD R2 | Four fix commits on one unit, +152 net. The fold was reshaped three times in review: atomicity came after a reset, as a third shape. `ci.py` carries 21 bugs and `_worktree_end.py` 29. |
| `push-gate-rewrite-orphans-shas-cited-in-the-range` | `a6d9d383b`, `e3dd793af` (both reverted at HEAD), `bfcbc6c18` | `ci.py` `_rewrite_unpublished` | REBUILD R2 | `caused_by: J9.T6`. The record was reopened by revert, and it caused the next row. |
| `rewrite-remedy-fix-line-bypasses-the-one-renderer` | `8510beb8f` | same | REBUILD R2 | `caused_by` the row above. A fix line bypassed the one renderer. |
| `worktree-sync-orphans-the-fix-sha-a-lanes-resolve-cites` | `bfcbc6c18`, `09bc7b352` | the fix-cite rule: `_git.fix_commit`, `_git.context_repos` | REBUILD R3 | `caused_by: resolve-records-a-fix-sha-a-later-rebase-unreaches`. The lookup was rebuilt twice (`09bc7b352`, "REBUILD of the lookup after review"). Two units decide which context owns a repo: `context_repos` reads `.dadaia/states/spec_contexts.json` raw (`_git.py:74-84`), and `_stats._context` asks `context list --json` (`_stats.py:58-69`). |
| `export-scratch-dir-failure-prints-no-fix-line` | `60ac71469` (group) | `container.py` `scan_bundle`; the scratch refusal in `export/service.py` | REBUILD R4 | `caused_by: J5.T6`. Scan logic lives in the composition root (`container.py:1`, "builds services"; `scan_bundle` at `:145`), and `container.py` carries 10 bugs. |
| `scan-refusal-hides-gits-reason` | `60ac71469`, `ace3ef2c2`, `68c3cf330` | `scan_bundle` | REBUILD R4 | `caused_by: J5.T7`. Three fix commits, and the unbundle-failure routing was re-ruled twice (grill: J5 r3 and the bugs review). |
| `import-turns-a-null-repo-url-into-none` | `f7cf18c76` | `ExportService.read` | KEEP, noted | `caused_by: none`. One REBUILD commit put the `export-v1` schema in place of the hand validator, and no bug followed it. Noted: `export/service.py` has 3 bugs, and its scratch half is R4's. |
| `release-check-crashes-on-a-non-object-log-entry` | `d39613438`, `27ac0d38a` | `_release_store` loader | KEEP, noted | `caused_by: J1.T23`. The second commit deletes the five per-reader dict checks the loader makes dead (net 0), a deletion-shaped fix. |
| `removal-test-hand-spells-a-posix-path-suffix` | `7b4a39e0d`, `a2a685360` | one test file | KEEP | Test only. The second commit is `ruff format`. |

**R5, closure act:** `623e50af5` repaired ADR 0270's `measured_by` to accept the docstring at `features/spec_context/service.py:468` instead of rewording that docstring, as rc-19 AC4.5 required. That loosens a check: it is the "an assert the fix changed" pattern.

**REBUILD work list** (bugs law §2; Job 1 executes the verdicts; each keeps the contract tests its fixes hardened): R1 is FR1, R2 is FR2, R3 is FR3, R4 is FR4, R5 is FR5.

## 1. Problem

The operator's words (Origin):

- Q1: "to ship the 0.5.0 the minimal gates are the work and backlog related with documentation and how to maximaze ou discoverability and of course adoption. we had been clean about it. for humans and agents. of course, auso the evals, the onboarding."
- Q3: "Gate: page live first (Recommended)".
- Q4: "entrypoints and proof. ... the agent alone is capable of discovering, get how to install, how to do the full onboarding and continue to using."
- Q6: "T1+T2 Claude, + discovery T3 (Recommended)", where `eval.yml` lands on main.
- Q7: "4 rcs: 18-21 (Recommended)", with rc-20 as "adoption, with the portfolio page in parallel".
- The rc-18 grill, Q2 on ADR 0178: "Amend: record-only delta + T3 gates (Recommended)", which became ADR 0269.
- The rc-20 grill, early: "Claude Code gates, Hermes readout (Recommended)".
- Dependabot #21: "Register, resolve at promote (Recommended)".

Gaps, verified at `740dc6927` against the researcher's facts from `2059b779e`:

- The repo has `llms.txt` and no `llms-full.txt` (`git ls-files`).
- The PyPI `Homepage` (`pyproject.toml:37`) and the GitHub homepage (`gh repo view`, `homepageUrl`) both point at the PyPI project page.
- The keywords (`pyproject.toml:14-18`) and the GitHub topics lack `cursor`, `devin`, `github-copilot` and `agent-skills`, yet `docs/index.md:62` names Cursor, Devin and GitHub Copilot as entry harnesses.
- `docs/index.md` defects:
  - `:7` promises "from `pip install`", but the quickstart's path is `uvx`.
  - `:50-54` spells `context bind`, `context baseline` and `context create` bare, without the venv path the rest of the page uses.
  - The page never names `init --from` (replicate a workspace, shipped in rc-19).
- `docs/quickstart.md` defects:
  - `:28` hard-codes `0.1.0`, but a tagged repo's work branch is the next patch (`_worktree_git.py:109`).
  - `:37` uses `$R`, which the page never sets, and no line creates the `rc-1/wt-rc` tree that `release.py new` writes in. So §1's second half cannot run as printed.
  - `:117` names `tasks/<job>.md`, but the law names `tasks/job<n>.md`.
  - The page never names `init --from`.
- README: the human section opens with a command block (`README.md:46-51`), but the agent section (`:97`) has no command-level fast path.
- Evals:
  - `evals/tasks/` holds T1 and T2 only.
  - `evals/scripts/compare.py:16` `FLOOR` already expects `t3-discovery: 2`, and `:36-39` iterates over `FLOOR`. So every run today BLOCKs "below floor" on T3.
  - `main` carries the `eval.yml` skeleton of `7af463ec0`, which calls no model.
- Bug window: 9 of the 12 fixes rc-19 closed are REBUILD-due, and R5 loosened an ADR check.

## 2. Measurable goals

| # | goal | target | source |
|---|---|---|---|
| 1 | Origin bugs | every one resolved and archived, except `mcp-on-main-is-vulnerable-to-session-exhaustion`, which resolves at the 0.5.0 promote | `bugs.py status` |
| 2 | REBUILDs R1-R4 | each lands as a `refactor(bugs):` REBUILD; net lines <= 0 per unit, tests excluded | `git diff --numstat` per REBUILD commit |
| 3 | ADR 0270's grep, as accepted | it prints only `service.py`'s `RepoLiveStatus(... current_branch=branch)` line | the grep in 0270's restored `measured_by` |
| 4 | T3 | the image builds on the baseline and on the candidate; the grader passes a hand-done workspace and fails an empty one | `tests/e2e/test_evals_t3.py` |
| 5 | discoverability | `llms-full.txt` committed and fresh; the keywords hold the four names; the GitHub topics equal the keywords | the contract test; `gh repo view --json repositoryTopics` |
| 6 | docs | none of §1's index, quickstart and README defects remain; the quickstart's §1 runs as printed, both blocks | `tests/e2e/test_onboarding_journey.py` |
| 7 | readout metrics 1, 2, 4, 6, 7, 9 | each read beside rc-19's (15/18 (83%), 2/15 (13%), n/a, 0, 0, 18) and its target (<= 20%, >= 70%, <= 4 h, 0, 0, 0) | `verdict.py stats 0.5.0-rc20`; baseline: rc-19's closure summary in `_RELEASE.json` |

## 3. Non-goals

- The portfolio page is out of scope here. It is the portfolio site 0.1.0 rc-1, a parallel job, and its prod deploy lands in rc-21.
- rc-20 changes no URL. The `Homepage` and GitHub homepage repoint is an rc-21 launch act (backlog `launch-operator-acts`), done after prod is live.
- rc-20 does not run T1, T2 or T3 for the record, and does not run the scorecard. Those runs and the launch acts belong to rc-21 (Q7).
- No Hermes leg enters `eval.yml`. Hermes runs T3 once, as a readout that does not gate, and only if the operator sets an `ANTHROPIC_API_KEY` and a search key in the `evals` environment.
- No Codex, Copilot or Devin eval lane, and no `evals/gate` commit status (ADR 0269(c)); all wait for 0.6.0.
- No Zensical and no GitHub Pages site.
- `rc18-review-loose-ends` stays 0.6.0. Its items that re-verified as live bugs enter only as registered bugs.
- A bug that is not yet registered is not a requirement here. The bug law governs it (FR9).

## 4. Requirements

Wave ranking, by the pick:

1. Law, skills and dev loop: FR1, FR2 and FR3. Job 1 executes the verdicts.
2. Shared foundation: FR4 and FR5.
3. Features and bugs: FR6 (T3), plus the registered bug batch (FR9), each bug in the job the PLAN assigns it.
4. Promote-facing: FR7 (adoption).

### FR1 — one relay of `release.py check` (R1)

- AC1.1 Every skill script that runs `release.py check` reaches it through one unit, and that unit spawns check once per call. Check's exit status alone decides pass or refuse. The refusal's message and fix line are the ones check printed, read by `_refusal`'s one parser, with no second regex over check's text (today `_specs.py:66`). Test: unit.
- AC1.2 The contract tests of `stats-crashes-on-a-release-state-that-breaks-its-schema`, `check-relay-reads-a-pass-from-text-not-exit-status` and `rc-tree-absent-fix-line-does-not-clear-its-refusal`, and those of the three rc-19-window stats bugs, stay green and unloosened. Test: unit (existing).
- AC1.3 Net lines <= 0 over every file the REBUILD touches, new ones included: `_stats.py`, `_worktree_new.py`, `_specs.py`, `_refusal.py` and the fifth relay, `_worktree_end._refuse_red`; tests excluded. Test: none; `git diff --numstat` is the evidence.

### FR2 — the push-gate fold and content path have one owner (R2)

- AC2.1 The fold (`_fold`, `_rewrite_unpublished`) and the content decision (`_content_decision`) leave `cli/commands/ci.py`, which keeps argument parsing and printing only. Their one owner is the feature that owns the push gate, and the PLAN names it from the as-is review. Every fix line still goes through the one renderer. Test: unit.
- AC2.2 The contract tests of `denylist-scan-runs-only-at-pre-push`, `push-gate-rewrite-orphans-shas-cited-in-the-range`, `rewrite-remedy-fix-line-bypasses-the-one-renderer` and `worktree-sync-orphans-the-fix-sha-a-lanes-resolve-cites` stay green and unloosened. They cover these partitions: the fold either finishes or changes nothing; every folded message is kept; test separation survives the split; and main and rc merges are not scanned. Test: integration (existing).
- AC2.3 Net lines <= 0 over every file the REBUILD touches, new ones included: `ci.py`, `push_gate.py`, the new `features/chokepoints/fold.py` and the merge-scan call in `_worktree_end.py`; tests excluded. Test: none; `git diff --numstat`.

### FR3 — one decider of a repo's context, under the fix-cite rule (R3)

- AC3.1 Among skill scripts, one unit answers "which context owns this repo, and which repos it holds". `_git.context_repos` stops reading `.dadaia/states/spec_contexts.json` raw, and `_stats._context` stops deciding the same question apart from it. Test: unit.
- AC3.2 `fix_commit`'s contract tests stay green and unloosened: a `Reapply "S"` read as a revert of a revert, a group line, a commit HEAD reverts that is skipped, and an associated repo read. Test: unit (existing).
- AC3.3 Net lines <= 0 over `_git.py` and `_stats.py`, tests excluded. Test: none; `git diff --numstat`.

### FR4 — `scan_bundle` leaves the composition root (R4)

- AC4.1 `scan_bundle` and its refusals move out of `container.py` into the feature that writes and reads bundles. `container.py` only wires it. Test: unit.
- AC4.2 Every scan refusal keeps the fix line that the J5 r3 and J5-bugs rulings fix (cases (a) to (e), plus the scratch act). The contract tests of `export-scratch-dir-failure-prints-no-fix-line` and `scan-refusal-hides-gits-reason` stay green and unloosened, and each follows its printed fix. Test: integration (existing).
- AC4.3 Net lines <= 0 over `container.py`, `export/service.py` and the owner the bundle code moves to, counting the moved lines on both sides, tests excluded. Test: none; `git diff --numstat`.

### FR5 — ADR 0270's check, as accepted (R5)

- AC5.1 The `repo_live_status` docstring (`features/spec_context/service.py:468`) no longer spells `current_branch=`, and states the same contract. Test: none; 0270's grep is the evidence.
- AC5.2 After AC5.1 merges, a shape-2 `chore(adrs): repair` on the `wt-rc` restores 0270's `measured_by` to its text before `623e50af5`: "prints only the RepoLiveStatus live read in features/spec_context/service.py, the repo_live_status docstring reworded so it no longer matches". The grep then prints one line. Test: none; the grep.
- Note, from the PR #298 review: the docstring at `service.py:468` is accurate. It describes the live `RepoLiveStatus` value, not the deleted stored field, so the gap is text only: the docstring's spelling matches the grep. FR5 changes no behaviour.

### FR6 — eval T3 discovery (backlog `eval-t3-discovery`; ADR 0269(b))

- AC6.1 `evals/tasks/t3-discovery/` takes T1's shape (`task.toml`, `instruction.md`, `environment/Dockerfile`, `tests/test.sh`, `tests/test_grade.py`), and `eval.yml` runs it unchanged through `harbor run -p evals/tasks -a claude-code`. It needs no new secret. Test: E2E.
- AC6.2 The instruction is a vague goal. It names `dadaia-workspace` and a `file://` project, and asks the agent to try the tool on that project and keep using it. It names no command, install path or doc URL. The image does not pre-install dadaia: no `dadaia` is on `PATH`. An install of `dadaia-workspace` inside the image resolves to that run's `environment/lib/` build, the candidate wheel or the pinned baseline, and never to whatever PyPI serves at run time. The PLAN names the mechanism. Test: E2E (the image build).
- AC6.3 The grader is code-only, in T1's style. It passes when `/workspace` holds one ALIVE context on the project's URL, with its specs initialized, `doctor` reporting no error for it, and at least one entry in its backlog (the "keep using" proof). Otherwise it fails. Test: E2E (`tests/e2e/test_evals_t3.py`: the image builds on each version; the grader passes a hand-done workspace and fails an empty one).
- AC6.4 `compare.py`'s `FLOOR` stays as it is (`t3-discovery: 2`). The bar is T1 3/3, T2 >= 2/3 and T3 >= 2/3, and it is run in rc-21. Test: none in rc-20; the rc-21 run is the E2E.

### FR7 — adoption and discoverability (backlog `adoption-and-discoverability`)

- AC7.1 `llms-full.txt` sits at the repo root. It holds the full text of every page `llms.txt` links in the repo, in `llms.txt`'s order, and one generator writes it. A contract test beside `test_the_cli_reference_is_the_committed_output_of_the_generator` fails when the file is stale, and `llms.txt` links it. The test excludes `CHANGELOG.md`, and the closure memory commit regenerates `llms-full.txt`. Test: unit (contract).
- AC7.2 The keywords gain `cursor`, `devin`, `github-copilot` and `agent-skills`, and each one names something the README says (`pyproject.toml:11-13`). At closure, the main thread sets the GitHub topics to the keyword set. Test: none for the topics (`gh repo view` is the evidence); the README claim is doc text.
- AC7.3 `Homepage` stays as it is. rc-20's closure summary names the rc-21 repoint: `pyproject.toml:37` and its comment at `:34-35`, plus `gh repo edit --homepage`, as one `launch-operator-acts` act. Test: none.
- AC7.4 `docs/index.md` and `docs/quickstart.md` lose every defect §1 lists, and both name `init --from`. The quickstart's §1 runs as printed: both blocks, the rc tree and the version read from the repo. The test that already pins it, `test_the_quickstart_block_runs_as_printed`, is hardened in its home to cover the second block. These docs derive from memory. Their atoms move in the PE's closure memory pass, as in rc-19, because `release.py check` refuses `specs/memory` in a task's `W:`. Test: E2E (the hardened journey).
- AC7.5 README's agent section opens with a fast path of at most five lines: the install line, the `AGENTS.md` map, `doctor`, and `llms.txt` / `llms-full.txt`. Test: none, doc text; T3 is its proof.

### FR9 — the bug window

- AC9.1 The operator confirmed 25 bugs on 2026-10-19: the 22 re-verified ones ("Register all 22, fix in rc-20 (Recommended)"), the Dependabot bug `mcp-on-main-is-vulnerable-to-session-exhaustion` ("Register, resolve at promote (Recommended)"), `windows-contract-coverage-runs-at-its-timeout` ("Register, raise cap in rc-20 (Recommended)") and `merge-scan-copies-the-denylist-precedence` ("Register, fix in rc-20 (Recommended)"). They were registered through the backlog lane `0.5.0/wt-backlog-rc20-bug-batch` before the PLAN. The Origin `bugs:` lists every bug open on this tree: these 25 minus the Windows timeout, plus the two found during definition, `subagent-bind-rebinds-the-parent-session-across-contexts` and `closure-refusal-fix-line-points-at-a-phase-that-cannot-go-back`, for 26. The bugs resolved in hotfix lanes on the work branch are not in the Origin: the Windows timeout, the three Windows test bugs and the own-name CRITICAL. They are not listed here as requirements; the PLAN assigns each one to a job. Test: none; `bugs.py status` is the evidence.
- AC9.2 Each of them is fixed in rc-20 under `specs/bugs/AGENTS.md` §2, RED test first, because no rc closes with an open bug. The one exception is the Dependabot bug, which stays open in rc-20 and resolves at the 0.5.0 promote (`feature/0.5.0` already holds no `mcp`). Test: per bug, its RED.

### Replaces

- R1: `_specs.check_release` regex-parsing check's text beside `_refusal`'s parser, and each caller's own relay of check.
- R2: the fold and the content decision living in `cli/commands/ci.py`.
- R3: `_git.context_repos` reading the registry file raw, beside `_stats._context`'s second answer to the same question.
- R4: `scan_bundle` and its refusals living in the composition root `container.py`.
- R5: ADR 0270's `measured_by` accepting the docstring it was written to exclude (`623e50af5`).

### Closure

- Backlog exits, `delivered` `--release 0.5.0`: `adoption-and-discoverability` and `eval-t3-discovery`. Every Origin bug is resolved and archived, except the Dependabot bug (AC9.2). The closure memory commit regenerates `llms-full.txt` (AC7.1).
- The memory pass covers the atoms that cite the moved units (`sdd/bug-ledger.md` for R3, `platform/context-portability.md` for R4, `agent-evals.md` for T3, and the atoms behind `docs/index.md` and `docs/quickstart.md` for AC7.4), and `catalog.json`.

## 5. Constraints and risks

- Order: Job 1 (FR1-FR3) runs first. FR4 and FR5 come before FR6, and FR7 comes last. The registered bugs go where the PLAN puts them.
- Net lines <= 0 for FR1-FR5. FR6 and FR7 are net additions, new capability that no unit carries.
- Public boundary: T3, `llms-full.txt` and every doc require of a user no remote, CI, vendor CLI or toolchain. `eval.yml` is this repo's developer CI, not a user requirement.
- T3 depends on the image resolving the candidate without pre-installing it (AC6.2). If Harbor's build cannot do that, the PLAN returns the question to the main thread before Job 6 starts.
- Consumers of each moved name (R2-R4) are found by the as-is review and the `dd-researcher` pre-mortem. The PLAN answers each.

## 6. Open questions

none.

- FR8 (`eval.yml` to `main` through the Operational-Change Lane) is dropped by main-thread ruling, logged as "FR8 dropped" in the grill report. `main` already carries the `eval.yml` registration skeleton (`7af463ec0`), and `gh workflow run eval.yml --ref feature/0.5.0` ran green on 2026-10-07. So rc-21 dispatches the candidate with `--ref feature/0.5.0`, and the 0.5.0 promote carries `eval.yml` to `main`, as Q6 rules. A lane now would only add a weekly cron that tests 0.4.7 and blocks on T3's floor. The number FR8 is not reused.
