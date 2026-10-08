---
slug: worktrees
title: worktrees
tldr: Every agent change to a repo is made in a canonical worktree — a job, a task, define, reconcile or backlog — and lands by worktree.py merge after its gate.
summary: Canonical worktrees nested in a folder per candidate, worktrees/<repo>/<M.m.p>-rc<N>/{define,reconcile,<job>,<job>--<task-id>} plus worktrees/<repo>/backlog/<slug>, each on the wt/ branch of the same name; one name grammar and one path reader; worktree.py new, stage, merge, clean and list, stdlib and read from git alone; three gate levels, each judged by a line of the work branch's AGENTS.md — a task fast-forwards onto its job branch after the verify-task line, a stage closes on the verify-stage line, a job lands on the work branch with an APPROVED verdict carrying its CI run and the verify line run as argv — and the holds that keep closure and context dead waiting while one is open.
tags: [worktrees, gitflow, isolation, merge, review]
sources:
  - dadaia_workspace/public/skills/dd-gitflow-default/scripts/worktree.py
  - dadaia_workspace/public/skills/dd-gitflow-default/scripts/_worktree_*.py
  - dadaia_workspace/public/data/worktrees-AGENTS.md
---

## The tree

- A worktree is `worktrees/<repo>/<name>` on the branch `wt/<name>`; the names are `<M.m.p>-rc<N>/<job>` (one per job, `define` and `reconcile` among them), `<M.m.p>-rc<N>/<job>--<task-id>` (one per parallel task) `backlog/<slug>` and `hotfix/<bug-id>`; it never lives under `.dadaia/tmp` or a harness directory.
- `_worktree_names.py` holds the one grammar (`NAME_RE`) and the one path reader, `locate`, which turns a workspace-relative path under `repos/<r>/` or `worktrees/<r>/<a>/<b>/` into its repo, tree name and repo-relative tail; the gate's protected globs, the doctor, the reaper and every verb read a worktree path through it ([[sdd-gate-v3]]).
- A job tree and the `define`, `reconcile`, backlog and hotfix trees are cut from the repo's work branch; a hotfix tree needs no rc `SPEC.md`, only its bug `open` in the main repo's `specs/bugs/BUGS.jsonl` on the work branch (`_worktree_new`); a task tree is cut from its job branch and lands back on it.
- `repos/<repo>` receives agent work only as a merge from a worktree; `specs/audits/` is the one repo path written directly ([[sdd-gate-v3]]).
- One change — code, tests, specs, memory and derived docs — lands in one job; a job branch takes code only through task merges, its rc's `specs/` edits aside; a `define` or backlog tree lands `specs/` only.
- `worktrees/` is a root entry of the layout law; it holds only `<repo>/<name>` worktrees and its projected `AGENTS.md`, the one home of the worktree rules ([[public-asset-distribution]]); the doctor never moves anything under it ([[workspace-doctor]]).
- A worktree holds no `.venv`, `.dadaia` or tool cache: its gates run on the workspace venv, put first on `PATH`, and import the worktree's own package.
- `git stash` is never used in a worktree — every worktree of a repo shares one stash stack; work is set aside as a WIP commit.
- A harness-native worktree is not ours: never opened for SDD work, never merged.

## `worktree.py`

- `python3 .agents/skills/dd-gitflow-default/scripts/worktree.py <verb>` is stdlib only; every refusal prints one `fix:` line, it runs no other script's verb and imports only owner parsers.
- `new <repo> <name>` derives the version from the repo's work branch and refuses a name outside the grammar or for another version; a job needs its rc's `SPEC.md` `Approved` on the work branch of the context's main repo — a job in an associated repo reads its main repo's — judged by `release.py`'s own status parser, the refusal naming the rc's `define` tree; a task needs its job branch and refuses a sixth open task tree in the rc, naming an open one's exit; it creates the tree already locked `dadaia:<name>` in one `git worktree add --lock` and refuses a symlinked `worktrees/` component.
- Each gate level — task, stage and job — runs a line the work branch's tracked root `AGENTS.md` declares — `verify-task:`, `verify-stage:`, `verify:` (job) — split by `shlex` and run in the tree as one argv list, never through a shell, stdin closed, the workspace venv first on `PATH`; no worktree changes the command that judges it, so a job cannot weaken its own gate. A missing or unstartable line refuses with an `Operator action:` to commit it on the work branch; a non-zero exit refuses naming the command to make pass in the worktree.
- `merge <task path>` lands a task on its job branch with no verdict: it refuses a dirty tree and a job branch that is no ancestor of HEAD (`fix: git -C <tree> rebase <job branch>`); then it runs the work branch's `verify-task:` line on the touched files (deleted paths dropped), and fast-forwards.
- `stage <job path>` closes a stage: refused while a task tree of the job is open, then the work branch's `verify-stage:` line green.
- `merge <job path>` lands a job on the work branch, in order: no task tree of the job open; the work branch an ancestor of HEAD; the newest `dd-code-reviewer` handoffs, by `produced_at`, naming in their `scope` HEAD or a sha of the branch's reflog whose (`git patch-id --stable`, full message) series over the work branch equals HEAD's, in order, valid `APPROVED`, each naming that sha as `reviewed_sha` and carrying a `diff_sha256` equal to the hash of the diff the merge lands (`worktree.py hash`), read from the handoff zone and from the reaper's hold of it — a newer verdict overrules an older one, and a missing or unparseable `produced_at` ranks newest and refuses ([[agent-comms]]); no commit made on the job branch directly that touches code, read from its reflog; then the work branch's `verify:` line, run on HEAD.
- `merge <define or backlog path>` needs every changed path under `specs/`, the work branch an ancestor of HEAD, a valid `APPROVED` verdict and the `bugs.py`, `backlog.py` and `release.py` `check`s green on the tree; it runs no test.
- Every merge lands HEAD as it is: ignored files are kept or dropped (tool caches and `*.pyc` are disposable), the target branch must be checked out where it lands, and only a fast-forward follows; a failed fast-forward names its fix by ancestry — a moved base refuses with the rebase, otherwise a stray change in the checkout is an `Operator action:`. It never rebases or rewrites; a ledger conflict after a rebase is redone by the ledger's own writer, never hand-merged.
- After the fast-forward it removes the tree, `branch -d`s it (never `--force` or `-D`), deletes the branch on the remote that is its upstream when it was pushed, and removes the rc folder the tree leaves empty; a re-run after any stop finishes the job.
- `clean <path>` removes only a `dadaia:`-locked, clean worktree with no commit ahead of the branch it was cut from.
- `list [--json]` reads every worktree fact from git alone, writing nothing under `.dadaia/states/`: ours `ready` (ahead, clean), `open` (ahead, dirty) or `empty`; an `orphan` `wt/*` branch with no tree; a `foreign` tree git registers; an `unregistered` directory two levels under `worktrees/<repo>/` — each with age, commits ahead, dirty, a warning past a day or off-canon, and its one exit, `clean` when empty, else `merge`.
- A `wt/` branch is pushable when it is a job's or a backlog tree's — never a task's or `define`'s; `_worktree_names.pushable` is the answer the pre-push gate reads ([[sdd-gate-v3]]).

## Holds

- The doctor's `WORKTREE` lines and the session-start injection render these rows ([[workspace-doctor]], [[context-management]]).
- `release.py phase CLOSURE` refuses while the repo holds an open `wt/*` other than the worktree it runs in, and `context dead` refuses while any is open, each naming the row's exit ([[release-lifecycle]], [[context-management]]).

## The work

- Only the main thread opens and merges worktrees; a sub-agent works only inside the path it was given, one per task tree, the tasks of one stage in parallel with disjoint `W:` sets ([[release-lifecycle]], [[agent-orchestration]]).
- The reviewer reviews a job's `git diff <work branch>...HEAD` once, plus once per stage past 400 added lines, never a task; a patch-identical rebase keeps the verdict, while a changed patch, a reworded message, or an added or dropped commit needs a new review ([[agent-orchestration]]).
- A hotfix is its own job, outside the candidate's DAG ([[bug-ledger]]).

## Runtime state

`worktrees/<repo>/<name>/`, `wt/*` branches and `dadaia:` locks in the repo's git, `.git/info/attributes`.

## Dependencies

[[sdd-gate-v3]], [[release-lifecycle]], [[bug-ledger]], [[backlog-ledger]], [[workspace-doctor]], [[context-management]], [[agent-orchestration]], [[agent-comms]], [[public-asset-distribution]].
