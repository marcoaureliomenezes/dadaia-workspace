# worktrees/AGENTS.md — Worktree Rules

Scope: this file governs only `worktrees/**`. It is the one home of the worktree rules;
a skill points here, never restates them.

- `WT` below is `python3 .agents/skills/dd-gitflow-default/scripts/worktree.py` — the one tool that opens, lists, merges and cleans a worktree.
- Shape: `worktrees/<repo>/<M.m.p><letter>-<kind>` on the local branch `wt/<same>`, cut from the repo's work branch; never pushed, never under `.dadaia/tmp` or a harness directory.
- A harness-native worktree (`.claude/worktrees/**`, a scratchpad) is not ours: never opened for SDD work, never merged by `WT`.

## 1. Kinds

- `impl` — one release task each: code, tests, and that task's `TASKS.md` marker only.
- `bug` — one fix: code, its regression test, the `BUGS.jsonl` lines.
- `backlog` — `specs/backlog/**` and `ADRs/decisions.jsonl`.
- `release` — a candidate's definition or amendment: `specs/releases/**`, `ADRs/decisions.jsonl`, `specs/memory/**`.
- The allowed set of each kind is `KINDS` in `worktree.py`; `WT merge` refuses a file outside it.
- Caps: `impl` 5 per repo and release, `release` 1 per repo and version; a cap refusal names the merge or clean that frees a slot.

## 2. The ritual — in this order, every time

1. The main thread opens: `WT new <repo> --kind <kind>` (an `impl` needs the Approved trio).
2. Work happens inside the worktree path only; `repos/<repo>` is never edited for the task.
3. Commit per the commit shapes of `dd-gitflow-default`; a dirty tree is refused at merge.
4. Run the kind's checks inside the worktree: the ledger script's `check`, and for `impl`/`bug` the tests.
5. `dd-code-reviewer` reviews `git diff <work branch>...HEAD`; the main thread writes its verdict as a handoff whose `scope` is `wt/<name>@<HEAD sha>`.
6. `WT merge <path>`: rebase onto the work branch, the allowed set, the APPROVED verdict for that exact sha, fast-forward, remove, `branch -d`. A rebase after review changes the sha: review again.
7. A conflict is resolved inside the worktree, never in `repos/<repo>`; `WT merge` re-runs cleanly after any stop.

- Never merge by hand, never `git worktree remove --force`, never `git branch -D` a `wt/` branch.
- An empty or merged worktree leaves by `WT clean <path>`; ignored files are kept (`--keep`) or dropped (`--drop`) by the operator's word.

## 3. Environment

- One venv: `.dadaia/.venv`. Inside a worktree, run tests as `.dadaia/.venv/bin/python -m pytest` from the worktree root; the repo's test conftest makes every child import the worktree's own code.
- A worktree never holds `.venv`, `.dadaia` or a tool cache; caches go where the harness env points.
- A subagent works only inside the worktree path it was given, bound to the context; only the main thread opens and merges.

## 4. Hygiene

- `WT list` and the doctor show every open worktree: kind, age, commits ahead, dirty or clean.
- Never close a candidate or `context dead` a context while one of its `wt/*` branches exists: merge or clean it first.
- Nothing lives under `worktrees/` but `<repo>/<name>` worktrees and this file.
