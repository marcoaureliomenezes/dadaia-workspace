# Job 1 — the merge gate: `preflight` is `merge` minus the verdict, and the gate's fix line carries the tree (FR7, AC8.3)

**Status:** Draft

Wave 1, lifted from the SPEC's Wave 3 because every later review leans on `preflight` and it is the G7 lever (PLAN notes). One skill, one file pair: `_worktree_end.py` (`_kind_checks`, `merge`, `preflight`, the `_check_approved` refusal) and the `worktree.py` parser. Bug `preflight-skips-checks-merge-runs` (REBUILD of the composition; `_worktree_end.py` carries 25 ledger records) and the fix-line leg of `verdict-validation-stated-three-ways-without-the-reviewed-tree`. Prior diffs to read: `da9011517` (J17.T2, the first `preflight`), `fcbbe0850` (the sibling fix that cleared one of three statements).

- **Structural cause.** `_kind_checks` is the list "both verbs call" by convention only: `merge` runs `_kept` and the target-checkout test after the list, outside it. A third inline check in `merge` and a third copy in `preflight` is the layer; the REBUILD puts both inside the list.
- **Seams closed.**
  - `_kind_checks` takes `keep` and `drop` and ends every kind's list with `("ignored", …)` over `_kept(tree, "merge", keep, drop)` then `("target", …)` over the `branch --show-current` test of `into`, in the order `merge` ran them, so `merge`'s refusals do not move.
  - `merge` runs the list, then calls `_kept` once more for the paths to copy (one extra `git status`, accepted; a check cannot return a value).
  - `preflight` skips only the label `"verdict"`, takes `--keep` and `--drop` through the parser's existing `end_args`, and passes the verb word `merge` to `_kept`, so its fix line is the one `merge` prints.
  - `_check_approved` prints `reports validate <path> --reviewed-root <tree>` when an invalid file decided; the `--all` line (no verdict decides) is unchanged and its four asserts stay unedited.
- **Consumers (changed fix-line text).** `git grep -n 'reports.*validate' -- dadaia_workspace tests` lists the printer and the asserts at `test__worktree_end.py:202,295,368,402` and `test__worktree_end__verdict_binding.py:65`; only `:202` names the path form.
- Test-side first: T1, T2 (disjoint `W:`). Then T3.
- Commit bodies carry `git grep -n '_kept(' -- dadaia_workspace/public/skills/dd-gitflow-default` (call sites, the `def` line aside: 2 before, `merge` and `clean`; 3 after, the list too) and the Phase 0 block `caused_by: none`, `prior diffs read: da9011517, fcbbe0850`, `rebuild: _kind_checks, merge, preflight`.
- Pre-review checklist: one list decides what lands; no cross-component import; sweep line above; no platform fact; net lines about 0 to +6 (two list rows in, two inline blocks out, one flag pair).

Tasks: 3 (0 jr, 3 sr). `who` names the dispatched role (`dd-release-definition` §5).

| task | who | AC | `W:` | outcome |
|---|---|---|---|---|
| J1.T1 | sr | AC7.1 | `tests/public/skills/dd_gitflow_default/scripts/test__worktree_end__preflight.py` | RED, integration: per tree kind (task, job, plain, define, backlog, reconcile, hotfix), two trees get the same refusal from `preflight` and from `merge`: one holds an ignored file neither kept nor dropped, one has its target checkout off the target branch. The tree is approved first (`approve`) so `merge` reaches the later checks; the compared lines are the `[error]` line and the one `fix:` line. Owner this file; every existing case stays |
| J1.T2 | sr | AC8.3 | `tests/public/skills/dd_gitflow_default/scripts/test__worktree_end.py` | RED, integration: at `:202` the expected argv of a named invalid verdict gains `--reviewed-root <tree>`; the unnamed (`--all`) branch of the same assert is unchanged. A tightening of the one expected literal, no assert removed or loosened: the `test(J1.T2)` commit names the main-thread ruling of 2026-10-13 (root map §1) and the reviewer reverts the fix to confirm it goes red. Owner this file |
| J1.T3 | sr | AC7.1, AC7.2, AC8.3 | `dadaia_workspace/public/skills/dd-gitflow-default/scripts/_worktree_end.py`, `dadaia_workspace/public/skills/dd-gitflow-default/scripts/worktree.py` | REBUILD as the intro says: the two checks join `_kind_checks`; `merge` runs the list then lands; `preflight` skips only `"verdict"` and parses `--keep`/`--drop`; the invalid-verdict fix line carries the tree. Owners T1, T2. After T1, T2. Fix commit of `preflight-skips-checks-merge-runs` and of the gate-line leg of `verdict-validation-stated-three-ways-without-the-reviewed-tree` |
