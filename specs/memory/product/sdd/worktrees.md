---
slug: worktrees
title: worktrees
tldr: Every agent change to a repo is made in a canonical worktree of one of four kinds and lands by worktree.py merge — reviewed, verified, fast-forwarded.
summary: Canonical worktrees worktrees/<repo>/<M.m.p><letter>-<kind> on wt/ branches cut from the work branch; four kinds, each an allowed set; worktree.py new, merge, clean and list, stdlib and read from git alone; the merge ritual — allowed set, HEAD containing the work branch, an APPROVED verdict on HEAD or a patch-identical sha of its reflog, the repo's verify command green, fast-forward only, never a rebase — and the holds that keep closure and context dead waiting while one is open.
tags: [worktrees, gitflow, isolation, merge, review]
sources:
  - dadaia_workspace/public/skills/dd-gitflow-default/scripts/worktree.py
  - dadaia_workspace/public/skills/dd-gitflow-default/scripts/_worktree_*.py
  - dadaia_workspace/public/data/worktrees-AGENTS.md
---

## The worktree

- A worktree is `worktrees/<repo>/<M.m.p><letter>-<kind>` on the local branch `wt/<same>`, cut from the HEAD of the repo's work branch; it is never pushed and never lives under `.dadaia/tmp` or a harness directory.
- `repos/<repo>` receives agent work only as a merge from a worktree; `specs/audits/` is the one repo path written directly ([[sdd-gate-v3]]).
- `worktrees/` is a root entry of the layout law; it holds only `<repo>/<name>` worktrees and its projected `AGENTS.md`, the one home of the worktree rules ([[public-asset-distribution]]); the doctor never moves anything under it ([[workspace-doctor]]).
- A worktree holds no `.venv`, `.dadaia` or tool cache: its tests run on the workspace venv and import the worktree's own package; the repo's root `AGENTS.md` declares one `verify: <command>` line, the check `merge` runs.
- `git stash` is never used in a worktree — every worktree of a repo shares one stash stack; work is set aside as a WIP commit.
- A harness-native worktree is not ours: never opened for SDD work, never merged.

## Kinds

| Kind | Allowed set (repo-relative, `fnmatch`) | Cap |
|---|---|---|
| `impl` | any path outside `specs/`, plus `specs/releases/*/rc-*/TASKS.md` | 5 per repo and release |
| `bug` | any path outside `specs/`, `specs/bugs/BUGS.jsonl`, `specs/bugs/_archive/*` | — |
| `backlog` | `specs/backlog/*`, `specs/ADRs/decisions.jsonl`, `specs/bugs/BUGS.jsonl` | — |
| `release` | `specs/releases/*`, `specs/ADRs/decisions.jsonl`, `specs/memory/*`, `specs/*/AGENTS.md`, `specs/constitution.md` | 1 per repo and version |

- `KINDS` in `_worktree_kinds.py` is the one table, and a commit stages only paths its kind's allowed set holds (`dd-gitflow-default` §3a); the gate loads its `kind_holding` to name the kind a refused repo write belongs in, and a path no kind holds gets an `Operator action:` fix.

## `worktree.py`

- `python3 .agents/skills/dd-gitflow-default/scripts/worktree.py <verb>` is stdlib only; every refusal prints one `fix:` line, it runs no other script's verb and imports only owner parsers.
- `new <repo> --kind <kind>` derives the version from the repo's work branch; `impl` needs the live candidate's trio `Approved` on that branch of the context's main repo — an associated repo reads its main repo's trio, and the refusal names `new <main> --kind release` — judged by `release.py`'s own status parser; a cap refusal, and letters past `z`, name an existing worktree's `merge` or `clean`; it creates the tree already locked `dadaia:<kind>:<id>` in one `git worktree add --lock` and refuses a symlinked `worktrees/` component.
- `merge <path> [--keep <files>… | --drop]` lands HEAD as it is, in order: refuse a dirty tree, its fix an `Operator action:` to commit the changes in the kind's shape or remove them, never a stash; refuse a file outside the kind's allowed set, naming the kind that holds it, the fix an `Operator action:` to revert that file to the work branch in one commit; refuse when the work branch is no ancestor of HEAD, `fix: git -C <tree> rebase <work>` (the rebase runs inside the worktree; a ledger conflict is redone by the ledger's own writer, never hand-merged); require the newest `dd-code-reviewer` handoffs, by `produced_at`, naming in their `scope` HEAD or a sha of the branch's reflog whose (`git patch-id --stable`, full message) series over the work branch equals HEAD's, in order, to be valid `APPROVED` — a newer verdict overrules an older one, and a missing or unparseable `produced_at` ranks newest and refuses ([[agent-comms]]); run the `verify:` line of HEAD's `AGENTS.md` in the tree, stdin closed, a non-zero exit or no `verify:` line refusing with an `Operator action:`; keep or drop ignored files (tool caches and `*.pyc` are disposable); fast-forward only. It never rebases or rewrites.
- A failed fast-forward names its fix by ancestry: the work branch moved while `merge` ran refuses with the rebase; otherwise a stray change in the checkout, an `Operator action:`.
- After the fast-forward it removes the tree and `branch -d`s it, never `--force` or `-D`; a re-run after any stop finishes the job.
- `clean <path>` removes only a `dadaia:`-locked, clean worktree with no commit ahead.
- `list [--json]` reads every worktree fact from git alone, writing nothing under `.dadaia/states/`: ours `ready` (ahead, clean), `open` (ahead, dirty) or `empty`; an `orphan` `wt/*` branch with no tree; a `foreign` tree git registers; an `unregistered` directory under `worktrees/<repo>/` — each with kind, age, commits ahead, dirty, a warning past a day or off-canon, and its one exit, `clean` when empty, else `merge`.

## Holds

- The doctor's `WORKTREE` lines and the session-start injection render these rows ([[workspace-doctor]], [[context-management]]).
- `release.py phase CLOSURE` refuses while the repo holds an open `wt/*` other than the worktree it runs in, and `context dead` refuses while any is open, each naming the row's exit ([[release-lifecycle]], [[context-management]]).

## The ritual

- Only the main thread opens and merges worktrees; `impl` and `bug` worktrees run side by side only where the PLAN's Parallel schedule puts their tasks in one step with disjoint `W:`, and an Arm B fix no PLAN names is the only open `bug` worktree ([[release-lifecycle]], [[bug-ledger]]).
- The reviewer reviews `git diff <work branch>...HEAD`; a patch-identical rebase keeps the verdict, while a changed patch, a reworded message, or an added or dropped commit needs a new review ([[agent-orchestration]]).

## Runtime state

`worktrees/<repo>/<name>/`, `wt/*` branches and `dadaia:` locks in the repo's git, `.git/info/attributes`.

## Dependencies

[[sdd-gate-v3]], [[release-lifecycle]], [[bug-ledger]], [[backlog-ledger]], [[workspace-doctor]], [[context-management]], [[agent-orchestration]], [[public-asset-distribution]].
