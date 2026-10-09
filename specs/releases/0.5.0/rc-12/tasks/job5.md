# Job 5 — REBUILD the production carry units (FR3)

**Status:** Approved

Six of FR3's twelve units live in production code. Each REBUILD keeps the unit's regression tests and the FR4 net green and unedited; it adds no branch, flag, special case or second path, and its net lines are ≤ 0 or its commit body says why (AC3.2). Commit shape 3 `refactor(bugs): <id> — REBUILD <unit>: …`.

- Unit assignment: `root-gate-blocks-editing-an-existing-entry` → J5.T1 (owner `tests/hooks/test_root_whitelist.py`); `job-merge-accepts-any-ci-run-url`, `job-merge-requires-a-remote-ci-run`, `merge-gate-accepts-verdict-written-by-the-merger` → J5.T2 (owner `tests/public/skills/dd_gitflow_default/scripts/test__worktree_end__verdict_binding.py`); `orphan-worktree-line-absent-from-the-bind-block-on-windows` → J5.T3 (owners `tests/hooks/test_ctx_inject.py`, `tests/infrastructure/test_ledger_scripts.py`); `shipped-law-hardcodes-the-posix-venv-path` → J5.T4 RED, J5.T5 implementation.
- `shipped-law-hardcodes-the-posix-venv-path` carries two fixes on one unit (`51df83007` renders the source CLI form at stage; `10ebbc4d8`, caused by it, adds the inverse `source_form` to every comparator). The REBUILD removes the two-way translation: one spelling of the workspace CLI, read the same way by stage, shipped history and TREE-5. This is the candidate's one public-law edit outside Job 1 and it lands only here, in J5.T5, after Job 1 (SPEC §5 Delivery constraints). Its design is decided by J5.T4's RED test inside the job (A7, ruled 2026-10-09); the `W:` below is the law-edit design's full set and shrinks by PLAN amendment if the design is code-only.
- J5.T2 owns `_worktree_end.py` after J1.T11's docstring edit (PLAN §Write ownership).

| task | AC | `W:` | outcome |
|---|---|---|---|
| J5.T1 | AC3.1, AC3.2 | `dadaia_workspace/hooks/root_whitelist.py` | source-only REBUILD of `_root_violation`; tests kept |
| J5.T2 | AC3.1, AC3.2 | `dadaia_workspace/public/skills/dd-gitflow-default/scripts/_worktree_end.py` | source-only REBUILD of `_check_approved` (three units); tests kept |
| J5.T3 | AC3.1, AC3.2 | `dadaia_workspace/hooks/ctx_inject.py`, `dadaia_workspace/infrastructure/ledger_scripts.py` | source-only REBUILD of `_worktrees`/`worktree_rows`; tests kept |
| J5.T4 | AC3.1 | `tests/core/test_workspace_layout.py`, `tests/core/test_template_history.py`, `specs/releases/0.5.0/rc-12/PLAN.md`, `specs/releases/0.5.0/rc-12/tasks/job5.md` | RED dispatch for the one-spelling CLI form under a win32 `PLATFORM` swap; post-review docstring correction records the forward-rendered historical-digest contract |
| J5.T5 | AC3.1, AC3.2 | `dadaia_workspace/core/workspace_layout.py`, `dadaia_workspace/core/template_history.py`, `dadaia_workspace/features/specs/doctor_structural.py`, `dadaia_workspace/infrastructure/runtime_transforms/codex_assets.py`, `dadaia_workspace/public/templates/shipped-hashes.json`, `specs/releases/0.5.0/rc-12/PLAN.md`, `specs/releases/0.5.0/rc-12/tasks/job5.md` | after J5.T4; source-only REBUILD deleting the two-way CLI translation; retain one POSIX source spelling and compare only its forward platform render; owner `tests/core/test_workspace_layout.py` |
