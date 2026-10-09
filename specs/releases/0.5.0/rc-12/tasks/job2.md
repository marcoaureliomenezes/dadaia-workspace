# Job 2 — a release job opens only in IMPLEMENTATION (FR2, Arm B)

**Status:** Draft

The candidate's one intended behaviour change, in its own job. Bug `worktree-new-opens-a-job-outside-implementation` (MEDIUM). Two dispatches: J2.T1 commits the failing tests, a fresh J2.T2 implements without touching a test path.

- J2.T2 replaces the SPEC-status check at `_worktree_new.py:87-95` with one phase check read through the existing `_release_schema` import; both checks are never kept; net lines ≤ 0 (AC2.3). It turns `worktrees-AGENTS.md:12` into a pointer to `specs/AGENTS.md` §3 (AC2.4), commits the fix with shape 3 (`fix(bugs): worktree-new-opens-a-job-outside-implementation — …`), then resolves the record with shape 4; the resolve names the gate at `_worktree_new.py:87-95` (the record's repro cites 85-93, which is wrong).
- AC2.2 is behaviour-preserving for every tree but job and task trees: a `reconcile` tree opens in IMPLEMENTATION and in CLOSURE, as today; `define` and hotfix trees are unaffected (A9, ruled 2026-10-09).

| task | AC | `W:` | outcome |
|---|---|---|---|
| J2.T1 | AC2.1, AC2.2 | `tests/public/skills/dd_gitflow_default/scripts/test__worktree_new.py` | RED dispatch: real-git cases — SPEC Approved, PLAN Draft, phase DEFINITION refuses a job with one `fix:` line and no tree or branch; IMPLEMENTATION opens job and task trees; a `reconcile` tree opens in IMPLEMENTATION and CLOSURE; `define` and hotfix unaffected |
| J2.T2 | AC2.1–AC2.4 | `dadaia_workspace/public/skills/dd-gitflow-default/scripts/_worktree_new.py`, `dadaia_workspace/public/data/worktrees-AGENTS.md`, `specs/bugs/BUGS.jsonl` | after J2.T1; source-only fix (shape 3) and resolve (shape 4); owner `tests/public/skills/dd_gitflow_default/scripts/test__worktree_new.py` |
