# SPEC — Release: 0.5.0

**Status:** Draft
**Release ID:** 0.5.0
**Owner:** dd-product-engineer
**Opened:** 2026-10-21
**Origin:** bugs:merge-accepts-a-verdict-written-by-the-merger,t3-grader-requires-an-active-backlog-entry,init-over-a-folder-with-a-venv-fix-line-names-another-folder,merge-of-a-gone-tree-with-its-parent-gone-prints-a-generic-fix-line,reconcile-rollback-advice-is-prose-not-a-fix-line,code-breaks-the-constitution-complexity-and-import-cycle-law,stats-counts-audit-commits-as-non-block-work-after-closure

---

## Bug window review

(Read the prior candidate's `## Bug window review`, then inspect each resolved record's
fix, found by its `fix(bugs)` or `refactor(bugs)` line, as `dd-bug-resolution/LINEAGE.md` defines.)

## 1. Problem

(Describe the problem this release solves.)

## 2. Measurable Goals

(List observable outcomes.)

## 3. Non-goals

(Explicitly list what this release does NOT cover.)

## 4. Requirements

### FR1 — worktree merge accepts a verdict written by the merger, and a caller-written produced_at outranks an earlier REJECTED

- Bug `merge-accepts-a-verdict-written-by-the-merger`.
- Repro: Reproduced at feature/0.5.0 114b632b3. Command 1: python -m pytest tests/public/skills/dd_gitflow_default/scripts/test__worktree_end__verdict_binding.py::test_a_bound_approval_of_head_lands -q -p no:cacheprovider (workspace venv, worktree root): exit 0, '1 passed' - approve() in tests/helpers/worktree_ws.py:218-230 writes the verdict by hand (a plain JSON file under .dadaia/handoff/c/) and worktree merge lands the tree: cases (a) and (b). Command 2: a scratch pytest (outside the repo, same helpers) that calls approve(verdict='REJECTED', at='T10:00:00Z') then approve(at='T11:00:00Z') for the same sha and runs worktree merge: exit 0, '1 passed', the merge lands: case (c). Ruled out: not an unmerged-worktree failure (the gate is merged code), not wrong usage (no flag is misused), not a missing feature (the fixed bug's contract already claimed the verdict binds the reviewer's evidence), not a designed validation with a runnable fix (the merge succeeds, nothing refuses).

### FR2 — T3 eval grader requires an active backlog entry while the law also admits an operator demand recorded in the SPEC Origin

- Bug `t3-grader-requires-an-active-backlog-entry`.
- Repro: Reproduced at feature/0.5.0 114b632b3 in a scratch dir (specs/backlog/BACKLOG.json = {schema: backlog-v1, active: []}; specs/releases/0.1.0/rc-1/SPEC.md with '**Status:** Approved' and '**Origin:** operator-demand'): python -I -c 'import test_grade as g; g.BACKLOG=<library backlog.py>; g.WORKSPACE=<scratch>; print(g.filled(Path("specs")))' printed 'backlog check clean, SPEC Origin operator-demand -> filled = False', exit 0; the grader then appends 'no valid backlog entry' and scores 0. Ruled out: not a failure inside an unmerged worktree (the grader is merged), not wrong usage (the operator's own law admits the SPEC Origin path), not a missing feature (the law already defines both entry paths), not a designed validation whose fix line runs (the grader prints no fix).

### FR3 — init over a folder holding only a .venv refuses and its fix line names the sibling folder, not the act that onboards the named one

- Bug `init-over-a-folder-with-a-venv-fix-line-names-another-folder`.
- Repro: Reproduced at feature/0.5.0 114b632b3 in a scratch dir (mkdir -p r3/workspace/.venv; never the live instance), worktree code on PYTHONPATH: python -c 'from dadaia_workspace.cli.main import app; ...' with argv init <scratch>/workspace --harness claude: exit 1; stderr "Error: '<scratch>/workspace' already holds a foreign tree (not a dadaia workspace)." then 'fix: uvx dadaia-workspace init <scratch>/workspace-workspace --harness claude'; the folder still holds only .venv. Ruled out: not an unmerged-worktree failure, not wrong usage (init on the folder the operator named is the documented act), not an environment limit, not a designed validation whose fix line runs (the line runs but onboards another folder than the named one), not a missing feature.

### FR4 — worktree merge of a task whose tree is gone, with its parent tree also gone, ends in a generic fix line

- Bug `merge-of-a-gone-tree-with-its-parent-gone-prints-a-generic-fix-line`.
- Repro: Reproduced at feature/0.5.0 114b632b3 in a scratch workspace (repos/r with branch wt/0.5.0/rc-1/job-1/wt-task-001, no worktrees/ folders), worktree code: python -m dadaia_workspace worktree merge <scratch>/worktrees/r/0.5.0/rc-1/job-1/wt-task-001 (via the CLI entry on a scratch root): exit 1; '[error] git branch --show-current: fatal: cannot change to <scratch>/worktrees/r/0.5.0/rc-1/job-1/wt-main: No such file or directory' then 'fix: Agent action: clear the git failure above, then rerun <runner> worktree.py merge <path>'. Calling _worktree_end.merge directly raises GitError with the same text. With neither the tree nor the branch present the same call returns 'merged into' without any check. Ruled out: not an unmerged-worktree failure, not wrong usage, not a designed validation whose fix line runs (the line cannot clear the failure, it restates it), not a missing feature.

### FR5 — reconcile prints its rollback advice as prose with no fix: line

- Bug `reconcile-rollback-advice-is-prose-not-a-fix-line`.
- Repro: Reproduced at feature/0.5.0 114b632b3 in a scratch dir, worktree code: typer CliRunner over reconcile.reconcile with container.reconcile_workspace replaced by a ReconcileResult(ok=False, error='projection failed', rollback_required=True): exit 1; output '[error] reconciliation failed: projection failed' then '[rollback-required] reinstall the previous exact provider version, then run its matching <venv>/bin/dadaia public install.'; no line starts with 'fix:'. Ruled out: not an unmerged-worktree failure, not wrong usage, not a designed validation whose fix line runs (there is no fix line), not a missing feature (the law demands the line on every block).

### FR6 — Nine functions above radon grade C and one import cycle break constitution section 5 item 3

- Bug `code-breaks-the-constitution-complexity-and-import-cycle-law`.
- Repro: Reproduced at feature/0.5.0 114b632b3: radon cc -s -n D dadaia_workspace (workspace venv, radon 6.0.1), exit 0, prints the nine functions with grades D (28, 22, 23, 23, 26, 26, 25, 23, 21) and nothing else; sed -n 39p dadaia_workspace/cli/help_digest.py prints the lazy 'from dadaia_workspace.cli.main import app  # lazy: avoid an import cycle'. Ruled out: not an unmerged-worktree failure, not wrong usage, not a law ambiguity (item 3 states grade C or better and zero import cycle), not a missing feature, not an environment limit; the nine scores were re-measured on this tree, not copied.

### FR7 — verdict.py stats metric 6 counts the chore(audits) commits the work branch takes directly

- Bug `stats-counts-audit-commits-as-non-block-work-after-closure`.
- Repro: Reproduced at feature/0.5.0 114b632b3 in a scratch git repo with two empty commits, 'docs(memory): closure' then 'chore(audits): F1 resolved': PYTHONDONTWRITEBYTECODE=1 python3 -c 'import _stats; print(_stats._after_closure(Path("."), <closure sha>, "HEAD"))' (skill scripts on sys.path): prints 1, exit 0; expected 0. Ruled out: not an unmerged-worktree failure, not wrong usage, not a missing feature (the commit shape exists in the law), not an environment limit. Law note: the metric's exempt list is code only; the exemption is read from dd-gitflow-default section 4.


## 5. Constraints and risks

(Upstream blockers, sequencing constraints, risk table.)

## 6. Open questions

(Questions the operator must decide before approval, or `none`.)
