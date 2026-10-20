# Job 2 — one decider names a tree's ledger scripts (FR2, R2)

**Status:** Draft

Wave 1, waits on —. Paths are repository-relative to `repos/dadaia-workspace/`. Design and evidence: PLAN §1, §1.1.

- **Shape.** One function answers "which scripts judge this tree's `specs/`": on a `wt-rc` the copies the tree tracks (`git ls-files` of the three ledger scripts' relative paths, each resolved in the tree), else the instance's; a backlog lane always the instance's; an associated repo none (`_ledgers` already returns before any script runs). The `own: bool` parameter, the `if h and own` comprehension filter (`_worktree_end.py:311`), the `len(held) == 1` rule (`:312`) and the caller's `kind_of(name) == "rc"` (`:420`) go: the kind table in `_kind_checks` binds the decider once per kind (a `partial` of the rc row, another of the backlog row). `_worktree_end.py` must not grow (33 bugs).
- **Contract tests that stay green, unloosened (AC2.2):** those of `trio-status-canon-judged-outside-the-define-merge-gate`, `wt-rc-merge-runs-ledger-checks-on-an-associated-repo-tree`, `merge-checks-a-tree-ledger-with-the-instance-schema`, `merge-runs-a-tree-carried-ledger-script-without-verify`, all in `test__worktree_end__tree_ledgers.py` and `test__worktree_end__define_gate.py`.

**Gate law.** `verify:` `python scripts/ci.py job`, no change. Definition of done: that run, `tests/public/skills/dd_gitflow_default`, the own-diff self-check (no removed assert, no new skip).

**Sweep greps.** `git grep -nE "\bown\b" -- dadaia_workspace/public/skills/dd-gitflow-default/scripts/_worktree_end.py` prints nothing; `git grep -n "len(held)" -- dadaia_workspace/public/skills/dd-gitflow-default/scripts/` prints nothing.

Tasks: 2 (2 sr). T2 after T1.

| task | who | AC | `W:` | outcome |
|---|---|---|---|---|
| J2.T1 | sr | AC2.1 | `tests/public/skills/dd_gitflow_default/scripts/test__worktree_end__tree_ledgers.py` | RED, integration: a `wt-rc` tracking two copies of one ledger script runs the tree's copy (fails today: the single-match rule falls back to the instance's); a backlog lane whose tree tracks a copy runs the instance's; an associated repo runs none; literal script paths asserted |
| J2.T2 | sr | AC2.1, AC2.2 | `dadaia_workspace/public/skills/dd-gitflow-default/scripts/_worktree_end.py` | REBUILD (R2): the decider above, the flag, the filter and the single-match rule deleted; owner `test__worktree_end__tree_ledgers.py`; net lines at most -4 |
