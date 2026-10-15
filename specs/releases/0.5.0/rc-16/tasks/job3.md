# Job 3 — Chokepoint: ref policy, `reference-transaction` hook script, `dadaia worktree` runner (FR3)

**Status:** Draft

Wave 1, waits on —. Paths are repository-relative to `repos/dadaia-workspace/`. Design and evidence: PLAN §1 and the as-is review it points to.

- Built beside the old layout; the hook honours `DADAIA_WT=1` (Job 2) and a test sets the variable itself, so the job does not wait on Job 2. Design: ASIS §3 seams 1, 2, 10. The hook is shell + local git only (public law); it fails open when the runner is unresolvable (agent default, unruled: it fires on every ref update, so failing closed could brick `git commit`; the publication chokepoint stays pre-push).
- **No install row here.** This job ships the hook script and the gate command; the hook-table row and its hash entry land in Job 9, after every code job. A hook installed before the instance's WT carries the marker is a Stall (review HIGH 5): the installer is table-driven, so without the row no repo gets the hook, whatever `ci install-hook`, `context create` or `context alive` run in between. The tests here copy the script into a tmp repo's `.git/hooks` by hand.
- Verified on git 2.43.0 (ASIS H2): a branch deletion arrives as `0…0 0…0 refs/heads/wt/x` in `prepared`, so creation is `old == 0 && new != 0`. T5's RED pins `git branch -D wt/x` and `WT clean`.
- Audits (agent default, unruled — reason: `specs/audits/AGENTS.md` keeps the direct-write law): `ci ref-gate-check` lets an update through whose `old..new` touches only `specs/audits/**`, reusing the `audit` zone predicate of `core/invocation.scope`.
- `dadaia worktree <verb>` is a ≈ 22-line runner of the one implementation in `dd-gitflow-default/scripts/` (resolves the installed `worktree.py` like `ledger_scripts.resolve_script`; no cross-feature import). Net production lines: +57 python, +40 shell (reason in PLAN §6).
- The three hook REDs (T5–T7) are real-git tests in three owner files, so they run in parallel; the shell script (T8) has all three as owners.

Tasks: 10 (4 jr, 6 sr, 0 pe). `who` names the dispatched role (`dd-release-definition` §5). Parallelism: Four chains start together: {T1→T2}, {T3→T4 after T2}, {T5,T6,T7→T8 after T4}, {T9→T10}. T1, T3, T5, T6, T7, T9 are the REDs.

| task | who | AC | `W:` | outcome |
|---|---|---|---|---|
| J3.T1 | sr | AC3.1 | `tests/features/chokepoints/test_branch_policy.py` | RED, literal shas: `check_ref_policy(lines, gitflow, origin)` refuses a work-role update to a sha ≠ origin's with one runnable `fix:`; passes the origin sha, creation, deletion, every non-work ref and an update touching only `specs/audits/**` |
| J3.T2 | jr | AC3.1 | `dadaia_workspace/features/chokepoints/branch_policy.py` | `check_ref_policy` (+14, one pure function over `Gitflow.role_of`); owner T1. After T1 |
| J3.T3 | sr | AC3.2 | `tests/cli/commands/test_ci__cli_ci.py` | RED: `ci ref-gate-check` reads `old new ref` lines on stdin, exits 1 with `[ref-gate] BLOCKED …` and one `fix:` line on a refusal, 0 otherwise; gitflow and work branch by `_gate_inputs` |
| J3.T4 | jr | AC3.2 | `dadaia_workspace/cli/commands/ci.py` | `ref-gate-check` (+18); owner T3. After T2, T3 |
| J3.T5 | sr | AC3.3 | `tests/public/scripts/test_reference_transaction.py` | RED on real git (tmp repo, the script copied into its hooks, stub `dadaia`), the creation side: raw `worktree add -b wt/x` refused with one runnable `fix:`; the same with `DADAIA_WT=1` passes; `commit` in a `wt/*` tree passes with no python call; `branch -D wt/x` and `WT clean` pass (old=new=0); an unresolvable runner warns and exits 0 |
| J3.T6 | sr | AC3.3 | `tests/public/scripts/test_reference_transaction__work_branch.py` | RED on real git, the work-branch side: raw `merge --ff-only`, `reset --hard` and `commit` on the work branch refused with one runnable `fix:`; `pull --ff-only` and `branch -m` pass. Parallel with T5, T7 (disjoint `W:`) |
| J3.T7 | sr | AC3.5, AC3.6, AC3.7 | `tests/public/scripts/test_reference_transaction__passes.py` | RED on real git, one per AC: a commit in an existing `wt/*` tree (an update, old ≠ 0) passes; creating the tag `archive/wt/<name>` passes; creating a harness-native worktree branch (not `wt/*`, `worktrees-AGENTS.md:7`) passes. Parallel with T5, T6 |
| J3.T8 | jr | AC3.3, AC3.5, AC3.6, AC3.7 | `dadaia_workspace/public/scripts/reference-transaction.sh` | the hook (≈ 40 shell lines), creation-only rule `old == 0 && new != 0`; owners T5, T6, T7. After T4, T5, T6, T7 |
| J3.T9 | sr | AC3.4 | `tests/cli/commands/test_worktree.py` | RED (stub script): `dadaia worktree <verb> …` forwards argv, stdout and exit code to the installed `worktree.py`; `--help` lists the verbs; no installed script → refusal with `fix: <dadaia> public install` |
| J3.T10 | jr | AC3.4 | `dadaia_workspace/cli/commands/worktree.py`, `dadaia_workspace/cli/main.py` | runner (≈ +24 lines); owner T9. After T9 |
