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
- At most five task trees of one rc are open at once; a sixth `new` is refused.
- A task starts from its job branch. Other release trees start from the work branch. A plain tree starts from the live work branch when a release is live, otherwise from the currently checked-out branch.
- One path reader and one name grammar serve the gate, doctor, reaper and all worktree verbs. Plain branches are local-only; job and backlog branches are pushable.

## Two gates and one review

- A task merge requires a clean tree, ancestry and the current task commit shape. It refuses a non-`test(` implementation commit that touches a declared test glob or the built-in fallback test paths.
- RED tests and implementation therefore arrive through fresh, separate task dispatches. Task merge fast-forwards the job branch without a review or repository test command.
- A job or plain change requires one reviewer-authored `APPROVED` verdict whose sha or equivalent patch series and diff hash match the range.
- A job merge also requires no task tree open, refuses while git tracks any path under `tests/tmp/<job>/` (a hotfix tree: `tests/tmp/<bug-id>/`; only the index counts, never untracked or ignored files on disk) with an `Operator action:` to promote each scaffold test into its contract's home, and runs the recorded base's tracked `verify:` once as argv with the workspace venv first on `PATH`. A plain merge runs it when declared.
- The `verify:` line splits on whitespace alone: a quote groups a word and a backslash stays literal, so a Windows path reaches the command intact.
- `define` and backlog merges are specs-only, reviewed, and run the bugs, backlog and release checks rather than production tests.

## Lifecycle and cleanup

- `new`, `merge`, `preflight`, `clean`, `hash` and `list` are the complete public verbs. There is no stage verb or frozen-test anchor.
- `preflight <tree>` runs every check `merge` runs for that tree's kind except the verdict, prints `PREFLIGHT PASS|FAIL <tree> <sha>` and each refusal with its `fix:` line, and exits 1 on any failure; a review is dispatched only on a passing preflight ([[agent-orchestration]]).
- Merge fast-forwards the exact reviewed head, removes the worktree, deletes its local branch and removes a pushed upstream branch when applicable. It never rebases or force-deletes.
- `list --json` derives state from git: ready, open, empty, orphan, foreign or unregistered. A linked tree of a repo no context owns is `unregistered`, its one fix an operator act. No worktree state file exists.
- Release closure waits while a canonical worktree other than its own and the next candidate's `define` tree remains open; context death waits on every one. Tool environments and caches live at workspace level, never inside a worktree.
- Only the main thread opens and merges; leaf agents work only in the path they receive.

## Dependencies

[[sdd-gate-v3]], [[release-lifecycle]], [[bug-ledger]], [[workspace-doctor]], [[context-management]], [[agent-orchestration]].
