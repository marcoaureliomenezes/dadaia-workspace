# Job 9 — Onboarding: `specs init` cuts the local work branch, the first pass runs in a `wt-backlog-first-pass` lane (FR9)

**Status:** Draft

Wave 3, waits on Job 5. Paths are repository-relative to `repos/dadaia-workspace/`. Design and evidence: PLAN §1 and the as-is review it points to.

- Operator ruling 'specs init corta o branch': `dadaia specs init` also cuts the local work branch `feature/<v>` (the name `core.gitflow.work_branch` computes, the one rule); onboarding 3b runs in a `wt-backlog-first-pass` lane cut from it; 3c `context baseline` publishes as today. Without it, deleting `plain` strands 3b: memory is written before `baseline` cuts any branch (ASIS H3).
- Units (PLAN §1): `cli/commands/specs.py` `init` (contract: scaffold, never commit; tests `test_specs.py`), `features/workspace/onboarding.py` `STEPS` row `first-pass` (the one derivation `doctor`, `init`, `context create` and SessionStart print) and `features/spec_context/service.py` `baseline` (anchor-first publish; it already merges an existing local `<work>`, `:606-612`).
- **Open seam, escalate before coding (T1).** A lane cut from `feature/<v>` sees only committed files, but `specs init` commits nothing and `test_absent_specs_scaffolds_lists_paths_and_commits_nothing` pins that. Agent default, unruled — reason: the lane cannot merge back over untracked scaffold files, so `init` must commit the scaffold on the branch it cuts (`commit_paths` of baseline's `_ONBOARDING` paths, with the marker the git client already carries) and leave the repo checked out on it; the commits-nothing assert stays green where no cut happens (an existing work branch). If T1's author finds that assert cannot stay unchanged, the task stops and returns the seam to the main thread: a changed product contract needs the operator.
- Docs follow in the Reconciliation (Job 10): `docs/quickstart.md`, `docs/getting-started.md` and the byte-equal `tests/fixtures/quickstart.md` are derived documents and change only in the memory pass. Job 7 owns map §7 3b (`data/AGENTS.md`) and shape 9 (`dd-gitflow-default/SKILL.md`).
- The `first-pass` fix line stays one `fix:` of the `Agent action:` form naming `dadaia worktree new <repo> <v>/wt-backlog-first-pass` through `fix_line`/`spell_fix`; its step id, kind and `STEP_IDS` order are unchanged.

Tasks: 6 (1 jr, 5 sr, 0 pe). `who` names the dispatched role (`dd-release-definition` §5). Parallelism: T1, T3, T5 (REDs) start together; T2, T4, T6 follow their own RED.

| task | who | AC | `W:` | outcome |
|---|---|---|---|---|
| J9.T1 | sr | AC9.1 | `tests/cli/commands/test_specs.py` | RED: `specs init` on a repo with no work branch cuts the local `feature/0.1.0`, commits the scaffold on it and leaves it checked out (on an unborn repo the root commit lands on it, as `baseline` does); a rerun with the branch present cuts nothing; the existing commits-nothing assert is untouched. Escalates the open seam if it cannot be |
| J9.T2 | sr | AC9.1 | `dadaia_workspace/cli/commands/specs.py` | cut and commit through the git client and `work_branch` (≈ +10); owner T1. After T1 |
| J9.T3 | sr | AC9.2 | `tests/features/spec_context/test_service__context_baseline.py` | RED: `baseline` on a repo whose local `feature/<v>` already holds the scaffold commit pushes it, anchor-first, and returns the work branch; nothing to commit is not an error |
| J9.T4 | sr | AC9.2 | `dadaia_workspace/features/spec_context/service.py` | `baseline` accepts the existing work branch (≈ ±8); owner T3. After T3; independent of T1/T2 |
| J9.T5 | sr | AC9.3 | `tests/features/workspace/test_onboarding__onboarding_steps.py`, `tests/features/workspace/test_onboarding.py` | RED (`test_onboarding.py:84-92` pins the 3b fix words and moves with it): the `first-pass` step's literal fix line is `Agent action: open the lane … worktree new <repo> <v>/wt-backlog-first-pass, then run the dd-audit-project first pass in it — <pending files>`; step order and kinds unchanged |
| J9.T6 | jr | AC9.3 | `dadaia_workspace/features/workspace/onboarding.py` | the `first-pass` fix lambda (≈ +3); owner T5. After T5 |
