---
slug: worktrees
title: worktrees
tldr: Worktrees nest under worktrees/<repo>/<v>/ — wt-rc, wt-main, wt-task and the backlog and hotfix lanes — and each merges into its parent after its gate.
summary: The one path grammar and the base it derives, the per-kind gates (task separation, the reviewed job gate, the rc's ledger checks), sync, the level AGENTS.md files, merge cleanup, the rows list and closure holds.
tags: [worktrees, gitflow, isolation, merge, review]
sources:
  - dadaia_workspace/public/skills/dd-gitflow-default/scripts/worktree.py
  - dadaia_workspace/public/skills/dd-gitflow-default/scripts/_worktree_end.py
  - dadaia_workspace/public/skills/dd-gitflow-default/scripts/_worktree_git.py
  - dadaia_workspace/public/skills/dd-gitflow-default/scripts/_worktree_names.py
  - dadaia_workspace/public/skills/dd-gitflow-default/scripts/_worktree_new.py
  - dadaia_workspace/public/skills/dd-gitflow-default/scripts/_worktree_sync.py
  - dadaia_workspace/public/skills/dd-gitflow-default/scripts/levels/*.md
  - dadaia_workspace/public/data/worktrees-AGENTS.md
  - dadaia_workspace/cli/commands/worktree.py
---

## The hierarchy

- A tree is `worktrees/<repo>/<name>` on branch `wt/<name>`; its name is its path, and its leaf fixes its kind: `<v>/rc-<N>/wt-rc` (the rc's integration branch), `<v>/rc-<N>/job-<n>/wt-main` (a job), `<v>/rc-<N>/job-<n>/wt-task-<kkk>` (a task, three digits), and the lanes `<v>/wt-backlog-<slug>` and `<v>/wt-hotfix-<bug-id>`; a slug or bug id is the backlog slug grammar. Any other name is refused with `not a worktree name` and the `list` fix.
- One path reader serves the gate, the doctor, the reaper and every verb: the tree name runs to the first `wt-` segment under `worktrees/<repo>/`. The base derives from the name alone — a task's is its `wt-main`, a `wt-main`'s its `wt-rc`, a `wt-rc`'s and a lane's the work branch `<work><v>` — and no base is recorded anywhere else.
- `<v>` must be the version of the repo's one local work branch. One rule names it — `_worktree_git.work_versions` lists the local `<work><M.m.p>` branches and `work_version` picks the one — and `core.gitflow.work_branch` and the push gate read the same rule. Two local work branches refuse with one `Agent action:` that strands no commit and never deletes the checked-out branch: switch to the higher, kept branch first, then — when the higher does not contain the lower — merge the lower into it, then `git branch -d` the lower. With no work branch, the refusal's fix creates `<work><M.m.p>` (the live release's version, else the next patch after the highest tag) from its remote branch when one exists, else from the integration branch.
- `new` cuts a tree from its parent's branch and refuses while that branch is absent, its fix the `new` of the parent. A `wt-main` opens only while `_RELEASE.json` on its `wt-rc` reads `IMPLEMENTATION` (an unreadable state is one refusal carrying its repair); a hotfix lane only while the main repo's `BUGS.jsonl` on the work branch holds that bug open, refused otherwise with the `Operator action:` to confirm that bug, or for a bug the ledger already holds, the regression as a new bug; an existing branch is refused.
- `new` writes a short `AGENTS.md` once into each level folder it creates (`<v>/`, `rc-<N>/`, `job-<n>/`), never over an existing file; `list` reports no stray for a folder holding only it.
- `wt-rc`, `wt-main` and backlog branches are pushable; task and hotfix branches stay local.

## Merges and gates

- Every kind's checks start with a clean tree and end with the ignored-file check and the parent checkout being on the parent branch; `merge` fast-forwards the parent's checkout — the `wt-rc` tree for a `wt-main`, the `wt-main` tree for a task, the repo for a `wt-rc` or lane.
- A task lands on `wt-main` unreviewed, with ancestry and RED/implementation separation: a non-`test(` commit touching a declared test glob, or the built-in fallback test paths, is refused, so RED tests and implementation arrive through fresh, separate task dispatches. A parent tree removed by hand is refused with the `git worktree add` line that restores it.
- A `wt-main` lands on `wt-rc` and a hotfix lane on the work branch through the job gate: ancestry, one reviewer-authored `APPROVED` verdict whose sha or equivalent patch series and diff hash match the range, and the base's tracked `verify:` run once as argv with the workspace venv first on `PATH` and bytecode writing off (the kernel child env sets `PYTHONDONTWRITEBYTECODE`), so the gate leaves no `__pycache__` in the tree; the merge is the one run of `verify:`, no preflight runs before review, and a repo declaring no `verify:`, or one that is not a startable argv list, refuses with one act: land that `AGENTS.md` line through a `wt-backlog` lane, then `sync` the tree that owns the refused merge's base. A red `verify:` names where its fix lands by the judged tree's kind: a `wt-main` in a task of its job; a `wt-rc` in the `wt-rc` when a reconcile commit is at fault, else through a `wt-hotfix` lane when the work branch's `verify:` fails too, then its `sync`; any other tree in itself. Both refuse while git tracks any path under `tests/tmp/job-<n>/` (a hotfix: `tests/tmp/<bug-id>/`; only the index counts) with an `Agent action:` to promote each scaffold test into its contract's home (a delete needs the operator's order).
- A `wt-rc` lands on the work branch through the same job gate, then, in the main repo, `bugs.py`, `backlog.py` and `release.py` `check` and the workspace doctor on its `specs/`, a red one relaying its own first `fix:` line; an associated repo holds no `specs/`, so its merges run no ledger check. A backlog lane lands `specs/` and the repo's `AGENTS.md` only: reviewed, then those ledger checks, never a test or `verify:` run.
- A `wt-main` or `wt-rc` lands only with no tree below its folder open, the fix naming the open tree's `merge`.
- The `verify:` line splits on whitespace alone: a quote groups a word and a backslash stays literal, so a Windows path reaches the command intact.
- A base that moved past a tree is refused with that tree's `sync` through `dadaia worktree` as the fix.

## Verbs and lifecycle

- `new`, `merge`, `clean`, `sync`, `hash` and `list` are the complete verbs. `dadaia worktree <verb> …` runs the installed `worktree.py`, forwarding argv, output and exit code; with no installed script it refuses with `public install` as the fix. Every git child the verbs start carries `DADAIA_WT=1`, the sanctioned-run marker.
- `merge` lands the exact reviewed head, removes the worktree, deletes its local branch, removes a pushed upstream branch when applicable and drops each level folder left holding only its `AGENTS.md`. It never rebases or force-deletes, and re-runs cleanly after a stop or on a tree already removed. A git failure no check names ends as one refusal whose fix clears it and reruns the same call, never a traceback.
- `clean` drops one of our trees holding no commit ahead of its base; a tree with commits is refused with its `merge`.
- `sync <path>` rebases the tree and every open tree below it, parents first, each onto its base; a tree already holding its base is skipped, a dirty tree stops the run before any tree moves, and a conflict aborts that rebase and stops with one fix line; a re-run finishes. It never pushes.
- `list --json` derives state from git, one row per path: `ready`, `open`, `empty` (nothing ahead of its parent branch), `orphan` (a `wt/*` branch with no tree, whose surviving directory is named for removal before its merge), `foreign` or `unregistered` (a stray folder at any depth under `worktrees/<repo>/`, its removal the fix). A linked tree of a repo no context owns is `unregistered` with `registered: false`, its fix an `Agent action:` to land its work and remove it. No worktree state file exists.
- Release closure waits while any tree of the repo other than a `wt-rc` and the tree it runs from is open; context death waits on every one ([[release-lifecycle]], [[context-management]]). Tool environments and caches live at workspace level, never inside a worktree.
- Only the main thread opens and merges; leaf agents work only in the path they receive.

## Dependencies

[[sdd-gate-v3]], [[release-lifecycle]], [[bug-ledger]], [[workspace-doctor]], [[context-management]], [[agent-orchestration]].
