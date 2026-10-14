---
slug: worktrees
title: worktrees
tldr: Repository changes are isolated in canonical plain, release, task, backlog or hotfix worktrees and land by worktree.py merge after the gate for that tree shape.
summary: The worktree grammar, recorded bases, RED/implementation separation, one reviewed job or plain-change gate, the preflight that runs that gate without the verdict, merge cleanup and closure holds.
tags: [worktrees, gitflow, isolation, merge, review]
sources:
  - dadaia_workspace/public/skills/dd-gitflow-default/scripts/worktree.py
  - dadaia_workspace/public/skills/dd-gitflow-default/scripts/_worktree_end.py
  - dadaia_workspace/public/skills/dd-gitflow-default/scripts/_worktree_git.py
  - dadaia_workspace/public/skills/dd-gitflow-default/scripts/_worktree_names.py
  - dadaia_workspace/public/skills/dd-gitflow-default/scripts/_worktree_new.py
  - dadaia_workspace/public/data/worktrees-AGENTS.md
---

## Shapes and bases

- A plain change is `worktrees/<repo>/<name>` on `wt/<name>`; its base is recorded in repository-local git config and is the branch its merge returns to.
- Release jobs, `define` and `reconcile` use `<M.m.p>-rc<N>/<job>`; tasks add `--<task-id>`; backlog and hotfix trees use their named namespaces. A job, backlog, hotfix or plain name is the backlog slug grammar (single hyphens, since `--` separates a job from its task) and a task id is the release task-id grammar.
- No cap bounds the open task trees of an rc; the approved PLAN's schedule governs parallelism.
- A task starts from its job branch, and `new` refuses a task whose job branch does not exist. Other release trees start from the work branch. One rule names the work branch — `_worktree_git.work_versions` lists the repo's local `<work><M.m.p>` branches and `work_version` picks the one — and every tree, a plain tree's recorded base (a recorded `<work><M.m.p>` resolves to the work branch as the rule finds it at read time, so a tree opened before a promote rename still merges), `core.gitflow.work_branch` and the push gate read it. A plain tree starts from the repo's work branch, and from the checked-out branch only when the repo has no work branch and no release is live; several live releases are refused by the one live-release decider. Two local work branches refuse, with a fix that strands no commit: `git branch -d` of the lower one when the higher contains it, else an `Agent action:` to merge the lower into the higher first. With no work branch, the refusal's fix creates `<work><M.m.p>` (the live release's version, else the next patch after the highest tag) from its remote branch when one exists, else from the integration branch.
- One path reader and one name grammar serve the gate, doctor, reaper and all worktree verbs. Plain branches are local-only; job and backlog branches are pushable.

## Two gates and one review

- A task merge requires a clean tree, ancestry and the current task commit shape; a task whose job tree was removed by hand is refused with the `git worktree add` line that restores it. It refuses a non-`test(` implementation commit that touches a declared test glob or the built-in fallback test paths.
- RED tests and implementation therefore arrive through fresh, separate task dispatches. Task merge fast-forwards the job branch without a review or repository test command.
- A job or plain change requires one reviewer-authored `APPROVED` verdict whose sha or equivalent patch series and diff hash match the range.
- A job merge also requires no task tree open, refuses while git tracks any path under `tests/tmp/<job>/` (a hotfix tree: `tests/tmp/<bug-id>/`; only the index counts, never untracked or ignored files on disk) with an `Agent action:` to promote each scaffold test into its contract's home (a delete needs the operator's order), and runs the base's tracked `verify:` once as argv with the workspace venv first on `PATH` and bytecode writing off (the kernel child env sets `PYTHONDONTWRITEBYTECODE`), so the gate leaves no `__pycache__` in the tree. A plain merge runs it when declared.
- The `verify:` line splits on whitespace alone: a quote groups a word and a backslash stays literal, so a Windows path reaches the command intact.
- `define` and backlog merges are specs-only, reviewed, and run the bugs, backlog and release checks rather than production tests.

## Lifecycle and cleanup

- `new`, `merge`, `preflight`, `clean`, `hash` and `list` are the complete public verbs. There is no stage verb or frozen-test anchor.
- `preflight <tree> [--keep …] [--drop]` runs every check `merge` runs for that tree's kind except the verdict, the ignored-file and target-checkout checks included, prints `PREFLIGHT PASS|FAIL <tree> <sha>` and each refusal with its `fix:` line, and exits 1 on any failure; a review is dispatched only on a passing preflight ([[agent-orchestration]]).
- Merge fast-forwards the exact reviewed head, removes the worktree, deletes its local branch and removes a pushed upstream branch when applicable. It never rebases or force-deletes. A git failure no check names ends as one refusal whose fix clears it and reruns the same call, never a traceback.
- `list --json` derives state from git, one row per path: ready, open, empty, orphan, foreign or unregistered. An orphan whose directory survives names removing that directory before its merge; a directory two levels under `worktrees/<repo>/`, or an unlisted one level under it, is `unregistered`. A linked tree of a repo no context owns is `unregistered`, its one fix an operator act. No worktree state file exists.
- Release closure waits while a canonical worktree other than its own and the next candidate's `define` tree remains open; context death waits on every one. Tool environments and caches live at workspace level, never inside a worktree.
- Only the main thread opens and merges; leaf agents work only in the path they receive.

## Dependencies

[[sdd-gate-v3]], [[release-lifecycle]], [[bug-ledger]], [[workspace-doctor]], [[context-management]], [[agent-orchestration]].
