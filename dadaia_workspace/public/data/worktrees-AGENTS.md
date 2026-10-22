# worktrees/AGENTS.md — Worktree Rules

Scope: this file governs only `worktrees/**`.

- `WT` below is `.dadaia/.venv/bin/dadaia worktree` — the one interface that opens, lists, merges, cleans and syncs a worktree (its verbs: `WT --help`); only the main thread opens and merges. A subagent works only inside the path it was given.
- The reference-transaction ref gate refuses creating a `wt/*` branch and moving a work branch by a raw commit, `merge --ff-only`, `reset --hard` or `update-ref`; it passes a move or a creation only when the local `refs/remotes/origin/<work>` is absent, holds the new sha, or the old sha is an ancestor of the new one and every path changed between them (renames off) is under `specs/audits/**`; `branch -m/-M/-C` onto a work branch (git writes it outside a reference transaction) and a local rewrite or deletion of that tracking ref (no network read) are out of scope; a failed ancestry or diff read refuses, and the hook lets any creation or move through when no runner is found or the runner faults. Every dadaia CLI and skill-script git call carries the marker that passes it (set by `_git.py`/`git_subprocess`).
- A forced move of a `wt/*` branch passes the ref gate by design: `WT merge` is the chokepoint, not the hook.
- `DADAIA_WT=1` reaches every `scrubbed_env` child, so a raw git call inside `verify:` passes the ref gate by design.
- Only `WT`-opened trees carry SDD work; a harness-native worktree (`.claude/worktrees/**`, a scratchpad) stays outside.

## 1. The tree

- A tree's name is its path under `worktrees/<repo>/`, its branch `wt/` plus that name; `<v>` is the version of an existing local work branch `<work><v>`.
- Leaves: the rc, job, task and lane shapes of `dd-gitflow-default` (The branch contract), where `kkk` is the `T<k>` of `J<n>.T<k>` in 3 digits (the rc's `wt-rc` is its integration branch: its define is the first commits, its reconcile the last). Any other name is refused; there is no free-named tree.
- Cut points: `dd-gitflow-default` (The branch contract). A `wt-main` opens only while `_RELEASE.json` on its `wt-rc` reads `IMPLEMENTATION`; a `wt-hotfix` only while the main repo's `specs/bugs/BUGS.jsonl` on the work branch holds that bug `open`; it needs no rc `SPEC.md`.
- `WT new` writes a short `AGENTS.md` into each `<v>/`, `rc-<N>/` and `job-<n>/` folder it creates; the last merge or clean removes a folder holding only it.
- One change lands in one job; a bug lands as `specs/bugs/AGENTS.md` (Resolution) says, a promote is its PR plus `release.py ship`.

## 2. Merges, gates, review

1. Task into `wt-main`: shape 6 (a bug fix: shape 3) of `dd-gitflow-default` (Commit shapes), a RED-test subject starts `test(`; `WT merge <task path>` refuses an implementation commit that touches the repo's `tests:` globs (built-in fallback when none) or a dirty `wt-main`, then fast-forwards. A RED-test and its implementation use separate task trees.
2. `wt-main` into `wt-rc`, and `wt-rc` and a `wt-hotfix` into `<work><v>`: `dd-code-reviewer` reviews `git diff <base>...HEAD` once; only the dispatched `dd-code-reviewer` writes a verdict, with `verdict.py` (`dd-handoff-emitter`), into `.dadaia/states/verdicts/<context>/`. `WT merge` lands HEAD as it is only when the tree is clean, HEAD contains its base, no tree below it is open, no path is tracked under `tests/tmp/<job>/`, a valid APPROVED verdict names HEAD or the equivalent reviewed patch series with a matching `diff_sha256`, and the base's tracked `verify:` passes (a repo without one refuses). A `wt-rc` of the main repo adds `bugs.py check`, `backlog.py check`, `release.py check` and `.dadaia/.venv/bin/dadaia doctor --specs-dir <tree>/specs`.
3. `wt-backlog-*` into `<work><v>`: `specs/` and any edit to the repo's `AGENTS.md` (how a missing `verify:` line lands), one review plus those same checks, no test and no `verify:` run.
4. Each merge fast-forwards its base, removes the tree and deletes its branch; the work branch receives only closed rcs and lanes, audits aside. Release closure refuses while `WT list` shows any row of the repo (a paused, foreign or stray one included) but a `wt-rc` and the tree it runs from.

- A task, `wt-hotfix` or `wt-backlog` merge also refuses a tree whose `<base>..HEAD` carries a denylisted term (`.dadaia/.venv/bin/dadaia ci push-gate-check --onto <base>`, the pre-push content matcher); its fix is an Agent action naming the listed paths: remove the term from them in the unpublished commits, reworded or split by hand, so a verdict on the old HEAD no longer binds.
- A lane that lands during an open rc moves `<work><v>`: `WT sync <wt-rc path>` rebases `wt-rc`, each `wt-main` and each task, parents first, never pushing; it stops at the first conflict with one fix line and a re-run finishes. A ledger conflict is redone by the ledger's own writer, never hand-merged. `WT merge` re-runs cleanly after any stop.
- Jobs of one PLAN wave and tasks of one job run in parallel only with disjoint exact `W:` sets.

## 3. Environment and hygiene

- A worktree never holds its own `.venv`, `.dadaia` or tool cache; caches go where the harness env points; every tree uses `<root>/.dadaia/.venv`.
- Never `git stash` in a worktree: every worktree of a repo shares one stash stack; set work aside as a WIP commit.
- A tree leaves only by `WT merge`, `WT clean` or `WT pause`, which keep unmerged work. `WT merge` and `WT clean` keep (`--keep`) or drop (`--drop`) ignored files by the operator's word; `WT pause` takes a lane or `wt-rc` tree only, refuses one holding ignored files, and `WT resume` restores it.
- Before `context dead`, merge, clean or pause every `wt/*` tree of the context (a job or task tree is never paused); dead refuses an open one.
