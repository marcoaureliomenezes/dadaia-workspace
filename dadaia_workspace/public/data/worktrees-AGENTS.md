# worktrees/AGENTS.md — Worktree Rules

Scope: this file governs only `worktrees/**`. It is the one home of the worktree rules;
a skill points here, never restates them.

- `WT` below is `python3 .agents/skills/dd-gitflow-default/scripts/worktree.py` — the one tool that opens, lists, merges and cleans a worktree.
- Shape: `worktrees/<repo>/<M.m.p><letter>-<kind>` on the local branch `wt/<same>`, cut from the repo's work branch; never pushed, never under `.dadaia/tmp` or a harness directory.
- A harness-native worktree (`.claude/worktrees/**`, a scratchpad) is not ours: never opened for SDD work, never merged by `WT`.

## 1. Kinds

- `impl` — one release task, or the closure's derived-docs step (`MEMORY-UPDATE` step 7).
- `bug` — one fix.
- `backlog` — demand and decision records.
- `release` — one candidate, from definition to closure.
- The allowed set of each kind is `KINDS` in `_worktree_kinds.py`; `WT merge` refuses a file outside it.
- Caps: `impl` 5 per repo and release, `release` 1 per repo and version, ceilings only (what opens is §2 step 1); a cap refusal names a worktree to end.

## 2. The ritual

1. The main thread opens `WT new <repo> --kind <kind>` only as these allow (an `impl` needs the Approved trio):
   - `impl` and `bug` worktrees run in parallel only where the PLAN's Parallel schedule puts tasks in one step with disjoint `W:`; the bugs a release fixes are tasks of its PLAN.
   - An Arm B fix no PLAN names is the only open `bug` worktree, opened only when disjoint from the open tasks' `W:`; otherwise it waits.
   - Nothing else opens on the main thread's initiative, except the serial `release` worktree, the closure's derived-docs `impl` and the registration, backlog or resolve tail of one act.
2. Work happens inside the worktree path only; `repos/<repo>` is never edited for the task.
3. Commit per the commit shapes of `dd-gitflow-default`; a dirty tree is refused at merge.
4. Run the kind's checks inside the worktree: the ledger script's `check`, and for `impl`/`bug` the tests.
5. `dd-code-reviewer` reviews `git diff <work branch>...HEAD`; the main thread writes its verdict as a handoff with `agent` `dd-code-reviewer` and `scope` `wt/<name>@<HEAD sha>`.
6. `WT merge <path>` lands only a clean tree inside its allowed set, on top of the work branch (rebased only when behind), with a valid APPROVED verdict naming the rebased sha or a sha of its branch reflog with the same patch-id and message series (ADR 0168), by fast-forward; then removes the tree and `branch -d`s it.
7. A conflict is resolved inside the worktree, never in `repos/<repo>`; `WT merge` re-runs cleanly after any stop.
8. Inside a PLAN step, merges land in ready order; only a true `blocked by:` edge holds one back.

- A task widening its `W:` into an open sibling's `W:` stops; the main thread records the `blocked by:` edge in a `release` worktree and the widening task waits.
- A bug a task fixed is resolved in a `bug` worktree holding `specs/bugs/BUGS.jsonl` alone (`dd-gitflow-default` §3a).
- Candidate closure runs in its `release` worktree.

- Never `git stash` in a worktree: every worktree of a repo shares one stash stack; set work aside as a WIP commit, and read a baseline by `git archive <sha> | tar -x -C .dadaia/tmp/<agent>/<YYYYMMDD>/`.
- Never merge by hand, never `git worktree remove --force`, never `git branch -D` a `wt/` branch.
- An empty or merged worktree leaves by `WT clean <path>`; ignored files are kept (`--keep`) or dropped (`--drop`) by the operator's word.

## 3. Environment

- A worktree never holds its own `.venv`, `.dadaia` or tool cache; caches go where the harness env points.
- Tests run by the command the repo's `AGENTS.md` names for a worktree.
- A subagent works only inside the worktree path it was given, bound to the context; only the main thread opens (§2 step 1) and merges.

## 4. Hygiene

- `WT list` shows every open worktree: kind, age, commits ahead, dirty or clean.
- Never close a candidate or `context dead` a context while one of its `wt/*` branches exists, closure's own `release` worktree aside: merge or clean it first.
- Nothing lives under `worktrees/` but `<repo>/<name>` worktrees and this file.
