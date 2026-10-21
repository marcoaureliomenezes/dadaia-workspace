# SPEC — Release: 0.5.0

**Status:** Draft
**Release ID:** 0.5.0
**Owner:** dd-product-engineer
**Opened:** 2026-10-21
**Origin:** bugs:merge-accepts-a-verdict-written-by-the-merger,t3-grader-requires-an-active-backlog-entry,init-over-a-folder-with-a-venv-fix-line-names-another-folder,merge-of-a-gone-tree-with-its-parent-gone-prints-a-generic-fix-line,reconcile-rollback-advice-is-prose-not-a-fix-line,code-breaks-the-constitution-complexity-and-import-cycle-law,stats-counts-audit-commits-as-non-block-work-after-closure

---

## Bug window review

**Window:** the records closed between rc-21's birth (2026-10-20T15:14:19Z) and rc-22's birth (2026-10-21T00:28:07Z, `_RELEASE.json` log): one, `t3-instruction-omits-backlog-demand` (MEDIUM, `caused_by: J7.T3`, closed 16:44:45Z), read in `BUGS.jsonl` and `_archive/bugs_histo.jsonl` at `a01772b95`. rc-21's table covers the earlier closures; the lanes resolved after rc-22's birth are rc-23's window. Two rc-21 KEEP rows gained a child and are re-judged, and the verdict gate's fix chain is read beside them because FR1's record names its predecessor (as-is §2). Each fix is found by its id line and read with `git show --numstat`, tests and specs excluded.

| fix (ids) | commit(s) | unit | net src | verdict | reason |
|---|---|---|---|---|---|
| t3-instruction-omits-backlog-demand | `7c6a13c59` | `evals/tasks/t3-discovery/instruction.md` | +1 / -1 (text) | REBUILD (FR2) | The fix edited the grader's input to fit an unchanged grader. Its child (FR2's bug) came on the next eval: the grader states the law's entry rule more narrowly than the law. The REBUILD target is the grader. The instruction stays (main-thread ruling: "KEEP the instruction, its text-asserting test goes to 0.6.0 intake"). |
| rc-21 merge-gate refusals (8 ids) | `1ec2d8ef2`, `bc8ef6d08`, `e42f8c2b9` | `_worktree_end.py` `merge` | -4, -16, +7 | REBUILD of `merge`'s head (FR4) | rc-21 said KEEP. FR4's bug shows that `merge` has two entry paths and only the present-tree path checks the parent tree. |
| bugs-check-refuses-task-fixed-records, rc-merge-reads-the-context-registry-twice | `c50735192`, `902c574ed` | `_bugs_check.findings_for` | 0, +2 | REBUILD (FR6) | These are the "one more child" that rc-21's KEEP row warned about. The unit has 15 records and radon grade D. |
| merge-gate-accepts-verdict-written-by-the-merger, worktree-merge-first-approved-overrides-newer-rejected, verdict-ttl-shorter-than-merge-window | `cb5cc3fde` + `38d544309`, `b4995b57f`, J10.S2.T2 (`985b7be13`) | `_handoffs.reviewer_records`, `_worktree_end._moment` | — | REBUILD (FR1, ADR 0279) | All three are symptom patches of one cause: the gate trusts a file in a zone every agent can write, and the order comes from a field the writer chooses. The reaper-hold glob widened that zone. |

**Overfitting check:** `7c6a13c59` special-cases a test value (it hands the agent the exact work the grader needs). `tests/e2e/test_evals_t3.py::test_the_instruction_gives_the_operator_work_and_names_the_workspace` asserts instruction text. It goes to the 0.6.0 intake, since a test leaves only on the operator's order. No fix in the window changed an assert.

## 1. Problem

The operator's words:

- Grill, 2026-10-20 (handoff `2026-10-20T231549Z-main-thread-grill-evals-promote`):
  - Q3 self-approval: "Bloqueia o 0.5.0".
  - Q4: "Confirmo: bug CRITICAL (Recommended)".
  - Q5: "Fechar o que a ferramenta controla (Recommended)".
  - Q6: all four proposals, "Grader T3 vs lei (Recommended)", "init: fix line errada", "Propostas a, b, d do fechamento" and "Proposta c (radon D)".
  - Q1: "Readout Codex local em E (Recommended)".
  - Q2: "Gate binário + nota por checkpoints (Recommended)".
  - Summary: "Confirmo, segue (Recommended)".
- Grill round 2, 2026-10-21 (handoff `…-grill-evals-promote-r2`):
  - Q7: "Mover para .dadaia/states (Recommended)".
  - Q8: "Aceito a ADR (Recommended)".
  - Q9: "Recusa + fix certa (Recommended)".
  - Q10: "Sem RED; caracterização guarda (Recommended)".
- Q11, 2026-10-21 (main-thread intake): "Operator action: esvaziar ou outra pasta (Recommended)". Init's foreign-tree fix line is `Operator action: empty <folder> or name another empty folder for the workspace, then run init on it`, the same for every folder. It refines Q9's "move them out, then run init on the same folder".
- Main-thread ruling (logged): "Any confirmed bug in code the work branch holds takes a <v>/wt-hotfix-<bug-id> lane".

Gaps, measured on `114b632b3` (the rc-21 E; eval report https://claude.ai/artifact/VvmTFaNpdAJ4pQamJygW26 and the grill handoff's findings):

- In 3 of 18 Claude trials (T3 Rx3W9vi, T3 TbQpmBP, T2 ENMsbbD) and 2 of 9 Codex trials, the implementing main thread ran `verdict.py --verdict APPROVED` itself, and the merge accepted it. The gate trusts the `agent` field of any file under `.dadaia/handoff/` (an ADDITIVE zone) and orders verdicts by a `produced_at` the writer chooses.
- Codex's T3 SPEC+PLAN with `Origin operator-demand` (`release.py check` green) scored 0/3; every T3 Claude trial of run 39462036716 met init's sibling fix line. The other four bugs are rc-21's closure proposals (a)-(d); each FR's repro states its gap.
- The scorecard last passed at `b411e7a6e` (rc-21 round 2). Every lane that touches `dadaia_workspace/public/**` leaves that pass stale.

## 2. Measurable goals

| # | goal | target | source |
|---|---|---|---|
| 1 | the seven Origin bugs | each `resolved`, its fix commit found by its id line; only the carried mcp record open | `bugs.py status --specs specs`, `bugs.py check` |
| 2 | self-approval on the Claude lane | 0 merges on a verdict the main thread wrote (baseline 3 of 18 trials) | the checkpoint scorer's self-approve flag on the gating run (FR9) |
| 3 | constitution §5 item 3 | `radon cc -s -n D dadaia_workspace` prints nothing (baseline 9 functions); `lint-imports` keeps every contract, the new `help_digest` → `cli.main` one included | radon 6.0.1 in the workspace venv; `scripts/ci.py job` |
| 4 | agentic scorecard | every cell >= 9 from both judges at the frozen tip | `.dadaia/reports/dadaia-workspace/agentic-scorecard/<UTC>/` |
| 5 | evals on E | T1 3/3, T2 >= 2/3, T3 >= 2/3, `compare.py` prints `non-blocking` | the `eval.yml` job summary (ADR 0277) |
| 6 | Codex readout on E | T1-T3 at k=3, recorded as readout (baseline at `114b632b3`: T1 3/3, T2 3/3, T3 0/3; checkpoint means 100, 100, 74) | the local harbor run; a `_RELEASE.json` note |
| 7 | E is the evaluated tree | `git diff --name-only E..<promote PR head>` lists only `specs/releases/0.5.0/_RELEASE.json` | git |
| 8 | readout metrics 1, 2, 4, 6, 7, 9 | each read beside rc-21's (2/2 (100%), 5/7 (71%), n/a, 4, 0, 0) and its target (<= 20%, >= 70%, <= 4 h, 0, 0, 0); rc-21's metric 6 drops by its three `chore(audits)` commits | `verdict.py stats 0.5.0-rc21` read at `a01772b95`; `verdict.py stats 0.5.0-rc22` |

## 3. Non-goals (0.6.0)

- The CI Codex lane (`eval-codex-lane-in-library-ci`, ruled 0.6.0). The Codex lane here is a local readout, and the 0.5.0 gate stays Claude.
- Graded rewards inside the graders. The gate stays binary (Q2), and checkpoint scores are computed outside the repo, as readout only.
- Any new gate, step or review round. The one import-linter contract runs inside the `lint-imports` that `ci.py` already runs (Q10).
- A pre-gate identity key for Copilot, Codex, Kimi, Cursor or Devin. Each row names none until its key is verified (ADR 0279). The shell-level forge on those harnesses is the accepted residual (Q5).
- The 0.6.0 intake items. Bug proposals still waiting for confirmation are not requirements; the bug law governs them.

## 4. Requirements

Each bug FR lands by its own `0.5.0/wt-hotfix-<bug-id>` lane (`specs/bugs/AGENTS.md` §2), not by an rc job. Its AC is the record resolved with its named RED test. FR2, FR3 and FR5 have already merged on `feature/0.5.0`.

Wave ranking, by the pick:

1. Law, skills and dev loop: FR10 (ADR 0279, in the define). FR1, FR2, FR3 and FR5 go first, in the lane order of the r2 handoff.
2. Shared foundation: FR4 and FR7.
3. Features and bugs: FR6 runs last among the lanes, because it touches `workspace_layout.py`, `init.py` and `reconcile.py` after FR1, FR3 and FR5.
4. Promote-facing: FR8 (the scorecard, the rc's one implementation job, after every lane that writes `dadaia_workspace/public/**`), then the closure, E and FR9.

### FR1 — worktree merge accepts a verdict written by the merger, and a caller-written produced_at outranks an earlier REJECTED

- Bug `merge-accepts-a-verdict-written-by-the-merger` (CRITICAL; ADR 0279; operator Q4, Q5, Q7, Q8).
- Repro: Reproduced at feature/0.5.0 114b632b3. Command 1: python -m pytest tests/public/skills/dd_gitflow_default/scripts/test__worktree_end__verdict_binding.py::test_a_bound_approval_of_head_lands -q -p no:cacheprovider (workspace venv, worktree root): exit 0, '1 passed' - approve() in tests/helpers/worktree_ws.py:218-230 writes the verdict by hand (a plain JSON file under .dadaia/handoff/c/) and worktree merge lands the tree: cases (a) and (b). Command 2: a scratch pytest (outside the repo, same helpers) that calls approve(verdict='REJECTED', at='T10:00:00Z') then approve(at='T11:00:00Z') for the same sha and runs worktree merge: exit 0, '1 passed', the merge lands: case (c). Ruled out: not an unmerged-worktree failure (the gate is merged code), not wrong usage (no flag is misused), not a missing feature (the fixed bug's contract already claimed the verdict binds the reviewer's evidence), not a designed validation with a runnable fix (the merge succeeds, nothing refuses).
- AC1.1 `verdict.py` writes a verdict only under `.dadaia/states/verdicts/<ctx>/`, and `verdicts` joins the states canon. Any agent's file-tool write there, the reviewer's included, is refused by the existing PROTECTED/STATE class with its one fix line. Test: unit (`tests/hooks/test_sdd_gate.py`, a `Write` payload).
- AC1.2 The merge reads verdicts only from that place. A hand-placed verdict under `.dadaia/handoff/` or the reaper hold, with the right diff hash, is not honoured. That covers case (b), and case (c), a later hand-written `produced_at` after a `verdict.py` REJECTED. The handoff-zone read, the reaper-hold read, the `agent`-field filter and the verdict TTL class are deleted. Test: integration (`test__worktree_end__verdict_binding.py`).
- AC1.3 The pre-gate judges one Bash act: a command that runs `verdict.py` with `--verdict`. It refuses the act when the harness's registry row names a subagent key and the payload's value is not `dd-code-reviewer`; an absent value is the main thread. `verdict.py stats` and `--help` pass, and so does any runtime whose row names no key. The Claude Code row names `agent_type`, and its PreToolUse matcher gains `Bash`. Every other row names none. The refusal prints one `fix: Agent action:` line that dispatches `dd-code-reviewer`. The pre-gate has one reader of the identity field. Test: unit (`tests/features/spec_context/test_gate_policy.py`, `tests/hooks/test_sdd_gate.py`, the hook-wrapper matcher pin).
- AC1.4 The worktrees law §2 states once that only the dispatched `dd-code-reviewer` writes a verdict, with `verdict.py`. The map §3 gate bullet names the one judged Bash act. The handoff law, the emitter skill and the reviewer persona point to that line, and none of them places a verdict under `.dadaia/handoff/`. Test: unit (the existing law-text pins, `tests/infrastructure/test_projection.py`); the scorecard judges the text.
- AC1.5 `tests/helpers/worktree_ws.py` `approve()` writes the place and body shape that `verdict.py` writes. The rows of `test__worktree_end__verdict_ttl.py` that test the deleted reaper-hold read are deleted in a `test(...)` commit naming the operator's Q7 words "Mover para .dadaia/states (Recommended)" (root map §1). Test: unit.
- AC1.6 The record resolves with `--caused-by merge-gate-accepts-verdict-written-by-the-merger` and names its RED test, after the instance is reprojected and `doctor` is clean. Test: none; `bugs.py check`.

### FR2 — T3 eval grader requires an active backlog entry while the law also admits an operator demand recorded in the SPEC Origin

- Bug `t3-grader-requires-an-active-backlog-entry` (HIGH; operator Q6). Merged and resolved (`332f2a5eb`, fix `5fe06d62f`).
- Repro: Reproduced at feature/0.5.0 114b632b3 in a scratch dir (specs/backlog/BACKLOG.json = {schema: backlog-v1, active: []}; specs/releases/0.1.0/rc-1/SPEC.md with '**Status:** Approved' and '**Origin:** operator-demand'): python -I -c 'import test_grade as g; g.BACKLOG=<library backlog.py>; g.WORKSPACE=<scratch>; print(g.filled(Path("specs")))' printed 'backlog check clean, SPEC Origin operator-demand -> filled = False', exit 0; the grader then appends 'no valid backlog entry' and scores 0. Ruled out: not a failure inside an unmerged worktree (the grader is merged), not wrong usage (the operator's own law admits the SPEC Origin path), not a missing feature (the law already defines both entry paths), not a designed validation whose fix line runs (the grader prints no fix).
- AC2.1 The grader passes a tree that entered work by either path the law admits, each judged by its checker's exit status: `backlog.py check` clean with an active entry, or a release SPEC with `release.py check` clean. It still scores 0 when neither holds. The verifier stays binary. Test: E2E (`tests/e2e/test_evals_t3.py` rows for operator-demand, delivered-backlog and none).

### FR3 — init over a folder holding only a .venv refuses and its fix line names the sibling folder, not the act that onboards the named one

- Bug `init-over-a-folder-with-a-venv-fix-line-names-another-folder` (MEDIUM; operator Q6, Q9, Q11). Merged and resolved (`62ae52e04`). The Q11 fix lines `813ab93ba` and `c3bd83228` followed.
- Repro: Reproduced at feature/0.5.0 114b632b3 in a scratch dir (mkdir -p r3/workspace/.venv; never the live instance), worktree code on PYTHONPATH: python -c 'from dadaia_workspace.cli.main import app; ...' with argv init <scratch>/workspace --harness claude: exit 1; stderr "Error: '<scratch>/workspace' already holds a foreign tree (not a dadaia workspace)." then 'fix: uvx dadaia-workspace init <scratch>/workspace-workspace --harness claude'; the folder still holds only .venv. Ruled out: not an unmerged-worktree failure, not wrong usage (init on the folder the operator named is the documented act), not an environment limit, not a designed validation whose fix line runs (the line runs but onboards another folder than the named one), not a missing feature.
- AC3.1 The refusal stays. It names the foreign entries, and its one fix line is `Operator action: empty <folder> or name another empty folder for the workspace, then run init on it`, the same for every folder. The move of the pinned assert in `test_init__init_requires_dir_and_harness.py` names Q9. Test: unit (that file and `tests/cli/test_main__refusals_carry_a_fix.py`).

### FR4 — worktree merge of a task whose tree is gone, with its parent tree also gone, ends in a generic fix line

- Bug `merge-of-a-gone-tree-with-its-parent-gone-prints-a-generic-fix-line` (MEDIUM; operator Q6).
- Repro: Reproduced at feature/0.5.0 114b632b3 in a scratch workspace (repos/r with branch wt/0.5.0/rc-1/job-1/wt-task-001, no worktrees/ folders), worktree code: python -m dadaia_workspace worktree merge <scratch>/worktrees/r/0.5.0/rc-1/job-1/wt-task-001 (via the CLI entry on a scratch root): exit 1; '[error] git branch --show-current: fatal: cannot change to <scratch>/worktrees/r/0.5.0/rc-1/job-1/wt-main: No such file or directory' then 'fix: Agent action: clear the git failure above, then rerun <runner> worktree.py merge <path>'. Calling _worktree_end.merge directly raises GitError with the same text. With neither the tree nor the branch present the same call returns 'merged into' without any check. Ruled out: not an unmerged-worktree failure, not wrong usage, not a designed validation whose fix line runs (the line cannot clear the failure, it restates it), not a missing feature.
- AC4.1 One parent-tree check runs first on both paths of `merge`, tree present and tree gone. A merge whose parent tree is gone refuses with the fix line that restores the parent tree, as the present-tree merge does, whether or not the branch exists. `_kind_checks` loses its inline copy, and net source lines on `_worktree_end.py` are <= 0. Test: unit (`test__worktree_end__removal.py`).

### FR5 — reconcile prints its rollback advice as prose with no fix: line

- Bug `reconcile-rollback-advice-is-prose-not-a-fix-line` (MEDIUM; operator Q6). Merged and resolved (`2dcc10f5d`, fix `2ea8f2c4f`).
- Repro: Reproduced at feature/0.5.0 114b632b3 in a scratch dir, worktree code: typer CliRunner over reconcile.reconcile with container.reconcile_workspace replaced by a ReconcileResult(ok=False, error='projection failed', rollback_required=True): exit 1; output '[error] reconciliation failed: projection failed' then '[rollback-required] reinstall the previous exact provider version, then run its matching <venv>/bin/dadaia public install.'; no line starts with 'fix:'. Ruled out: not an unmerged-worktree failure, not wrong usage, not a designed validation whose fix line runs (there is no fix line), not a missing feature (the law demands the line on every block).
- AC5.1 A failed reconcile prints its error and then exactly one `fix:` line through the CLI's one refusal renderer. The JSON key `rollback_required` is unchanged. Test: unit (`tests/features/reconcile/test_service.py`, `tests/cli/test_main__refusals_carry_a_fix.py`).

### FR6 — Nine functions above radon grade C and one import cycle break constitution section 5 item 3

- Bug `code-breaks-the-constitution-complexity-and-import-cycle-law` (HIGH; operator Q6 "Proposta c (radon D)", Q10).
- Repro: Reproduced at feature/0.5.0 114b632b3: radon cc -s -n D dadaia_workspace (workspace venv, radon 6.0.1), exit 0, prints the nine functions with grades D (28, 22, 23, 23, 26, 26, 25, 23, 21) and nothing else; sed -n 39p dadaia_workspace/cli/help_digest.py prints the lazy 'from dadaia_workspace.cli.main import app  # lazy: avoid an import cycle'. Ruled out: not an unmerged-worktree failure, not wrong usage, not a law ambiguity (item 3 states grade C or better and zero import cycle), not a missing feature, not an environment limit; the nine scores were re-measured on this tree, not copied.
- AC6.1 `help_digest.command_paths` takes the root command from its caller, which reads it from Typer's context. The lazy `cli.main` import and its `lru_cache` go. The RED test is a forbidden import-linter contract, `dadaia_workspace.cli.help_digest` → `dadaia_workspace.cli.main`, in `setup.cfg`. It is broken before the fix and kept after it, inside the `lint-imports` that `ci.py` already runs. Test: the lint contract.
- AC6.2 Each of the nine functions is split to grade C or better with no behaviour change: every verb's output and every refusal's message and fix line stay byte-identical. No RED is possible for a grade (Q10). The existing characterization and contract tests are the guard and stay unloosened. Afterwards `radon cc -s -n D dadaia_workspace` prints nothing. Test: unit (the existing tests); the scorecard is the measure.

### FR7 — verdict.py stats metric 6 counts the chore(audits) commits the work branch takes directly

- Bug `stats-counts-audit-commits-as-non-block-work-after-closure` (LOW; operator Q6).
- Repro: Reproduced at feature/0.5.0 114b632b3 in a scratch git repo with two empty commits, 'docs(memory): closure' then 'chore(audits): F1 resolved': PYTHONDONTWRITEBYTECODE=1 python3 -c 'import _stats; print(_stats._after_closure(Path("."), <closure sha>, "HEAD"))' (skill scripts on sys.path): prints 1, exit 0; expected 0. Ruled out: not an unmerged-worktree failure, not wrong usage, not a missing feature (the commit shape exists in the law), not an environment limit. Law note: the metric's exempt list is code only; the exemption is read from dd-gitflow-default section 4.
- AC7.1 Metric 6 counts no `chore(audits)` commit. The repro reads 0. Test: unit (a `_stats` row on a scratch repo).

### FR8 — the agentic scorecard final round (constitution §5)

- AC8.1 The round runs at the frozen tip, after every lane that writes `dadaia_workspace/public/**` (FR1, FR4, FR6, FR7) has merged. Two independent `dd-code-reviewer` judges score every cell (R1-R8, P1-P3, S1-S12, C1-C6) against `agentic-scorecard/20261017T0519Z/rubric.md`. Every cell below 9 carries its `path:line` and is fixed, then the round is re-scored. Test: none; the record is the evidence.
- AC8.2 A fix deletes or corrects text before it adds any. No fix adds a mechanism. Test: none; the review.
- AC8.3 Both judges put every cell at >= 9, and the record lives under `.dadaia/reports/dadaia-workspace/agentic-scorecard/<UTC>/`. Test: none; the record.

### FR9 — E, the gating eval, the readouts and the promote (ADRs 0269, 0277; operator Q1, Q2, summary)

- AC9.1 After the rc-22 closure reconcile (§Closure), E is the last commit that is not `_RELEASE.json`. The push follows, and every CI job goes green. Test: none; git and CI.
- AC9.2 `eval.yml` runs on E with T1 3/3, T2 >= 2/3 and T3 >= 2/3, and `compare.py` prints `non-blocking`. A `chore(release):` note names the run URL, the verdict and E. Test: E2E (the run).
- AC9.3 The local Codex readout runs on E: harbor `-a codex`, on E's wheel, T1-T3 at k=3, with the operator's Codex login. The tasks are adapted to the Codex harness in scratch only. The result is recorded as a note and gates nothing (Q1). Test: none; the note.
- AC9.4 A checkpoint score of 0-100 per trial, with the process flags (self-approve, reviewer dispatches), comes from a script outside the repo for every lane of AC9.2 and AC9.3. It is recorded as a note and gates nothing (Q2). Test: none; the note.
- AC9.5 The promote continues on the new E through rc-21 SPEC FR6-FR9 (AC6.3, FR7 AC7.2, FR8, AC9.1 steps 4-8, AC9.2). The operator's "Let's move forward with the promotion" is the AC9.1 step 4 order. So the PR feature/0.5.0 → develop opens without a new question once the gate on E is `non-blocking` (summary ruling). The operator's own acts remain: the portfolio PR #33 merge and the PyPI approval. Test: none; the PRs and the log.

### FR10 — the define's law record (operator Q8: "Aceito a ADR (Recommended)")

- AC10.1 ADR 0279 is proposed (`1b513b006`), accepted with the operator's Q7 and Q8 words (`3a7547e0b`), has its `measured_by` repaired (`079285f98`) and is rendered in the ARCHITECTURE adr-list (`a01772b95`). It amends 0096 and 0133 for the one verdict act only. Test: unit (its `measured_by`, FR1's AC1.2-AC1.3 tests); `doctor` `LEDGER-ADR-SCHEMA`.

### Replaces

- FR1 (as-is R2, R3): the verdict place under `.dadaia/handoff/<ctx>/`, the merge's reaper-hold read, the `agent`-field identity test and the verdict TTL class. Also ADR 0096's and 0133's "Bash is never judged", for the verdict act only (R1).
- FR2 (R9): T3's backlog-only entry rule, the grader's private copy of the law's entry rule.
- FR3 (R4): init's sibling `<dir>-workspace` fix for a foreign tree.
- FR4: `_kind_checks`'s inline parent-tree check, which only the present-tree path reached.
- FR5 (R5): reconcile's `[rollback-required]` prose and `[error] reconciliation failed` line.
- FR6 (R6): `help_digest`'s lazy `cli.main` import, its `lru_cache` and the zero-argument `command_paths()`.
- FR7 (R8): metric 6's subject list, which counted `chore(audits)` commits.

### Closure

- The bug archive takes the seven Origin records. The mcp record stays open and carried (rc-21 AC9.2).
- The memory pass (`MEMORY-UPDATE.md`) covers at least the atoms the lanes made stale:
  - `workspace-init.md:27` (the sibling fix line);
  - `agent-evals.md:16` (the backlog-only grader);
  - `harness-claude-code.md:25` (the matcher gains `Bash`);
  - the `ARCHITECTURE.md` ADR 0133 summary ("Bash is not covered");
  - the verdict place wherever an atom states it (`agent-comms`, `agent-orchestration`, `worktrees`, `bug-ledger`);
  - `docs/getting-started.md:32` against init's new fix line;
  - the catalog.
- `llms-full.txt` is regenerated. All of it, and every scorecard fix, lands before E: after E only `_RELEASE.json` changes (ADR 0269 (a)).

## 5. Constraints and risks

- Each bug lands by its hotfix lane before any other merge, then `worktree sync` (`specs/bugs/AGENTS.md` §2). Lane order follows the r2 handoff. FR6 goes last.
- A library change is finished only once the instance is reprojected and `doctor` is clean. After FR1 lands, a verdict written before the upgrade is not honoured, so reviews in flight on open lanes are redone (ADR 0279).
- Hook cost: on Claude Code, every Bash call pays the pre-gate, 0.06 s measured over 8 runs (ADR 0279). It is a per-call cost; no `verify:` line changes.
- Public boundary: no AC requires a remote, CI, `gh` or a toolchain of a user's repo. `eval.yml`, harbor and the checkpoint scorer are this repo's developer acts.
- Risk: R1 and R2 change a judged set, a path and a fix line. A read-only `dd-researcher` pre-mortem names their consumers before the SPEC is approved, and the PLAN answers each hit.
- Risk: a T3 below 2/3 on E, or a red gating run, costs a re-cut E. Its cause enters by Arm B.

## 6. Open questions

none. The PLAN closes the seams that remain open: the scorecard job's DAG, and the Copilot key, which stays none (ADR 0279).
