# worktrees/AGENTS.md — Worktree Rules

Scope: this file governs only `worktrees/**`.

- `WT` below is `python3 .agents/skills/dd-gitflow-default/scripts/worktree.py` — the one tool that opens, lists, merges and cleans a worktree.
- A subagent works only inside the worktree path it was given, bound to the context; only the main thread opens and merges.
- Only `WT`-opened trees under `worktrees/` carry SDD work; a harness-native worktree (`.claude/worktrees/**`, a scratchpad) stays outside `WT`.

## 1. The tree

- A plain change uses `worktrees/<repo>/<name>/` on `wt/<name>`, where `<name>` is one lowercase kebab segment outside the reserved release, `backlog` and `hotfix` namespaces. It records the live release's work branch as its base, or the currently checked-out branch when no release is live.
- One worktree per release job lives at `worktrees/<repo>/<M.m.p>-rc<N>/<job>/`, on `wt/<M.m.p>-rc<N>/<job>`, cut from the repo's work branch; its admission precondition is `specs/AGENTS.md` §3.
- Two more trees inside an rc folder: `define/` (the candidate's definition) and `reconcile/` (the Reconciliation job: memory, derived docs, `measured_by` repairs, the rc's measurement, closure).
- Outside an rc only `worktrees/<repo>/backlog/<slug>/`, on `wt/backlog/<slug>`, and `worktrees/<repo>/hotfix/<bug-id>/`, on `wt/hotfix/<bug-id>` (§3); a bug is a job.
- One worktree per task, `<M.m.p>-rc<N>/<job>--<task-id>/` on `wt/<M.m.p>-rc<N>/<job>--<task-id>`, cut from its job branch; at most 5 task worktrees are open per rc. One change — code, tests, specs, memory or derived docs — lands in one job.
- `WT new <repo> <name>` opens any tree named above and records the exact base its merge returns to.

## 2. Two gates, one review

1. Task: its commit takes shape 6 of `dd-gitflow-default` §3a; a RED-test subject starts `test(`. `WT merge <task path>` checks git hygiene and refuses an implementation dispatch that touches the repo's `tests:` globs (the built-in fallback when none is declared); it then fast-forwards the job branch. The RED-test dispatch and fresh implementation dispatch use separate task worktrees. A task behind its job branch rebases first and the gate reruns.
2. Job or plain change: `dd-code-reviewer` reviews `git diff <base>...HEAD` once and writes its own verdict with `verdict.py` (`dd-handoff-emitter`), its only write. A job branch may be pushed before review because push is not merge.
3. `WT merge <path>` lands HEAD as it is only when the tree is clean, HEAD contains its recorded base, no task worktree of the job is open, a valid APPROVED verdict names HEAD or the equivalent reviewed patch series, `diff_sha256` matches the range, and the recorded base's tracked `verify:` runs once and passes (a job refuses without one; a plain change may omit it). It returns to that base, fast-forwards it, removes the tree and deletes its branch.
4. A `define` or `backlog` tree lands `specs/` only: its merge needs one review plus `bugs.py check`, `backlog.py check`, `release.py check` and `.dadaia/.venv/bin/dadaia doctor --specs-dir <tree>/specs` on the tree, and runs no test.

- A moved work branch refuses with `fix: git -C <tree> rebase <work>`; the rebase runs inside the worktree. A ledger conflict is redone by the ledger's own writer on the rebased tree, never hand-merged. `WT merge` re-runs cleanly after any stop.

## 3. Hotfix and parallel work

- A hotfix (`specs/bugs/AGENTS.md` §2) is its own job, outside the rc's DAG: `WT new <repo> hotfix/<bug-id>` cuts it from the work branch with no rc `SPEC.md`, once the main repo's `specs/bugs/BUGS.jsonl` on the work branch holds that bug `open`; its gates, one review and merge are §2's.
- Jobs in one PLAN wave and tasks in one job run in parallel only with disjoint exact `W:` sets.

## 4. Environment and hygiene

- A worktree never holds its own `.venv`, `.dadaia` or tool cache; caches go where the harness env points; every tree uses `<root>/.dadaia/.venv`.
- Never `git stash` in a worktree: every worktree of a repo shares one stash stack; set work aside as a WIP commit.
- A tree leaves only by `WT merge` or `WT clean`, which keep unmerged work.
- An empty or merged worktree leaves by `WT clean <path>`; ignored files are kept (`--keep`) or dropped (`--drop`) by the operator's word.
- Merge or clean every `wt/*` branch of a context before closing its candidate or running `context dead`.
- `worktrees/` holds `<repo>/<name>` worktrees and this file.
