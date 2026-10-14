# Job 4 — Chokepoint: ref policy, `reference-transaction` hook, `dadaia worktree` runner (FR4)

**Status:** Draft

Wave 1, waits on —. Paths are repository-relative to `repos/dadaia-workspace/`. Design and evidence: PLAN §1 and the as-is review it points to.

- Built beside the old layout; the hook honours `DADAIA_WT=1` (Job 2) and a test sets the variable itself, so the job does not wait on Job 2. Design: ASIS §3 seams 1, 2, 10. The hook is shell + local git only (public law); it fails open when the runner is unresolvable (agent default, unruled: it fires on every ref update, so failing closed could brick `git commit`; the publication chokepoint stays pre-push).
- Verified on git 2.43.0 (ASIS H2): a branch deletion arrives as `0…0 0…0 refs/heads/wt/x` in `prepared`, so creation is `old == 0 && new != 0`. T5's RED pins `git branch -D wt/x` and `WT clean`.
- Audits (agent default, unruled — reason: `specs/audits/AGENTS.md` keeps the direct-write law): `ci ref-gate-check` lets an update through whose `old..new` touches only `specs/audits/**`, reusing the `audit` zone predicate of `core/invocation.scope`.
- `dadaia worktree <verb>` is a ≈ 22-line runner of the one implementation in `dd-gitflow-default/scripts/` (resolves the installed `worktree.py` like `ledger_scripts.resolve_script`; no cross-feature import). Net production lines: +57 python, +40 shell (reason in PLAN §6).

Tasks: 8 (4 jr, 4 sr, 0 pe). `who` names the dispatched role (`dd-release-definition` §5). Parallelism: Four chains start together: {T1→T2}, {T3→T4 after T2}, {T5→T6 after T4}, {T7→T8}. T1, T3, T5, T7 are the REDs.

| task | who | AC | `W:` | outcome |
|---|---|---|---|---|
| J4.T1 | sr | AC4.1 | `tests/features/chokepoints/test_branch_policy.py` | RED, literal shas: `check_ref_policy(lines, gitflow, origin)` refuses a work-role update to a sha ≠ origin's with one runnable `fix:`; passes the origin sha, creation, deletion, every non-work ref and an update touching only `specs/audits/**` |
| J4.T2 | jr | AC4.1 | `dadaia_workspace/features/chokepoints/branch_policy.py` | `check_ref_policy` (+14, one pure function over `Gitflow.role_of`); owner T1. After T1 |
| J4.T3 | sr | AC4.2 | `tests/cli/commands/test_ci__cli_ci.py` | RED: `ci ref-gate-check` reads `old new ref` lines on stdin, exits 1 with `[ref-gate] BLOCKED …` and one `fix:` line on a refusal, 0 otherwise; gitflow and work branch by `_gate_inputs` |
| J4.T4 | jr | AC4.2 | `dadaia_workspace/cli/commands/ci.py` | `ref-gate-check` (+18); owner T3. After T2, T3 |
| J4.T5 | sr | AC4.3, AC4.5, AC4.6, AC4.7 | `tests/public/scripts/test_reference_transaction.py`, `tests/features/spec_context/test_doctor__hooks_drift.py`, `tests/features/spec_context/test_service__hook_refresh.py` | RED on real git (tmp repo, stub `dadaia`): raw `worktree add -b wt/x` refused; marker passes; `commit` in a `wt/*` tree passes with no python call; `branch -D wt/x` passes (old=new=0); raw `merge --ff-only`/`reset --hard`/`commit` on the work branch refused; `pull --ff-only` and `branch -m` pass; unresolvable runner warns and exits 0; HOOKS-DRIFT-1 reports the second row absent and `install_git_hooks` writes it; every fix line it prints is runnable. Three more REDs, one each: AC4.5 a commit in an existing `wt/*` tree (update, old ≠ 0) passes; AC4.6 creating the tag `archive/wt/<name>` passes; AC4.7 creating a harness-native worktree branch (not `wt/*`, `worktrees-AGENTS.md:7`) passes |
| J4.T6 | jr | AC4.3 | `dadaia_workspace/public/scripts/reference-transaction.sh`, `dadaia_workspace/core/workspace_layout.py`, `dadaia_workspace/public/templates/shipped-hashes.json` | hook (≈ 40 shell lines), one `INSTALLED_GIT_HOOKS` row, one append-only hash entry; owner T5. After T4, T5 |
| J4.T7 | sr | AC4.4 | `tests/cli/commands/test_worktree.py` | RED (stub script): `dadaia worktree <verb> …` forwards argv, stdout and exit code to the installed `worktree.py`; `--help` lists the verbs; no installed script → refusal with `fix: <dadaia> public install` |
| J4.T8 | jr | AC4.4 | `dadaia_workspace/cli/commands/worktree.py`, `dadaia_workspace/cli/main.py` | runner (≈ +24 lines); owner T7. After T7 |
