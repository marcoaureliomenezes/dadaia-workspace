# Job 4 — four readers that answer a question from the wrong source (bug batch A)

**Status:** Draft

Wave 1, waits on —. Paths are repository-relative to `repos/dadaia-workspace/`; `P/` = `dadaia_workspace/`, `S/` = `dadaia_workspace/public/skills/`. Design and evidence: PLAN §1, §1.2. Each pair is a RED then a REBUILD of one unit; the four pairs share no path and may run in parallel. Every non-null `caused_by` below makes the fix a REBUILD (shape 3, `refactor(bugs): <id> — REBUILD <unit>: …`, the `caused_by:`/`evidence:`/`prior diffs read:`/`rebuild:` block in the body).

- **Closure outside git (T1, T2).** `_refuse_open_worktrees` (`S/dd-release-implementation/scripts/_release_phase.py:85-104`) reads git twice with different failure policies: `main_checkout` swallows the failure and returns `Path(".")` (`_git.py:233-239`), the `rev-parse --show-toplevel` on the next line raises. `own` derives from `specs.parent` (no git call); a specs tree that no git checkout holds is one refusal with one `fix:` line. Lineage: `caused_by=J4.T18`, confirm at Phase 0.
- **Planted `.git` file (T3, T4).** `is_worktree_gitfile` (`P/core/workspace_layout.py:277-285`) accepts any gitdir whose parent folder is named `worktrees`. A `.git` file anchors a root only when its gitdir lies under `<root>/repos/<slug>/.git/worktrees/`, this workspace's own repos. Lineage: `caused_by=protected-globs-miss-a-plain-tree-path`, confirm at Phase 0.
- **MEM-DRIFT-1 (T5, T6).** `_live_feature_package_names` (`P/features/specs/doctor_memory.py:72-74,282-288`) lists the INSTALLED library's packages. The list is the tree's own repo `dadaia_workspace/features/` (`specs.parent`); a repo without one has no list, so the rule returns no finding. Lineage: `caused_by=T-050-90`.
- **First-pass fix line (T7, T8).** `_first_pass_fix` (`P/features/workspace/onboarding.py:84-96`) prefixes `several.text` (up to three steps) to its own two: four to five steps against the root map §3 cap of three. With several work branches the line is `several.text` alone (it ends with the branch kept); doctor prints the next step on the rerun. The composition is deleted, nothing replaces it. Lineage: `caused_by=J1.T11`.
- **Lineage (main thread, in this job's `wt-main`).** Before each REBUILD task: `bugs.py update --set caused_by=<value> <id>`; after it merges: `resolve --caused-by <value>`.
- **Contract tests that stay green, unloosened:** `test__release_phase__fix_line.py`, the `protected-globs-miss-a-plain-tree-path` cases in `tests/core/test_workspace_layout*.py`, `tests/features/specs/test_doctor_memory.py`, `tests/features/workspace/test_onboarding*.py` (the steps property included).

**Gate law.** `verify:` is `python scripts/ci.py job`, no change. Definition of done: that run, `tests/public/skills/dd_release_implementation`, `tests/core`, `tests/features/specs`, `tests/features/workspace`, the own-diff self-check, the sweep greps.

**Sweep greps.** `git grep -n "rev-parse\", \"--show-toplevel" -- dadaia_workspace/public/skills/dd-release-implementation/scripts/_release_phase.py` prints nothing; `git grep -n "pkgutil" -- dadaia_workspace/features/specs/doctor_memory.py` prints nothing; `git grep -n 'then ", ' -- dadaia_workspace/features/workspace/onboarding.py` prints nothing.

Tasks: 8 (8 sr). Odd tasks are RED and precede their pair's even task.

| task | who | AC | `W:` | outcome |
|---|---|---|---|---|
| J4.T1 | sr | AC9.2 | `tests/public/skills/dd_release_implementation/scripts/test__release_phase__fix_line.py` | RED, integration. `release.py phase CLOSURE` on a specs tree inside a workspace but outside any git checkout exits 1 with one `[error]` line, one `fix:` line, no traceback (fails today: uncaught `GitError`) |
| J4.T2 | sr | AC9.2 | `dadaia_workspace/public/skills/dd-release-implementation/scripts/_release_phase.py` | REBUILD `_refuse_open_worktrees`: the first bullet; owner `test__release_phase__fix_line.py` |
| J4.T3 | sr | AC9.2 | `tests/core/test_workspace_layout__workspace_layout_zones.py` | RED, unit. Under `worktrees/<r>/…`, a `.git` file holding `gitdir: /elsewhere/worktrees/x` anchors no root (fails today); a real linked worktree's `.git` file, its gitdir under `<root>/repos/<r>/.git/worktrees/`, still anchors; a symlinked `.git` still does not |
| J4.T4 | sr | AC9.2 | `dadaia_workspace/core/workspace_layout.py` | REBUILD `is_worktree_gitfile`/`protected_glob`: the second bullet; owner `test_workspace_layout__workspace_layout_zones.py` |
| J4.T5 | sr | AC9.2 | `tests/features/specs/test_doctor_memory.py` | RED, unit. A specs tree whose repo holds `dadaia_workspace/features/` matching its map yields no MEM-DRIFT-1 finding; a tree whose repo holds no such folder yields none whatever the installed library lists (fails today: a false WARNING); a tree whose own folder disagrees with its map still yields one per name |
| J4.T6 | sr | AC9.2 | `dadaia_workspace/features/specs/doctor_memory.py` | REBUILD MEM-DRIFT-1's list: the third bullet; owner `test_doctor_memory.py` |
| J4.T7 | sr | AC9.2 | `tests/features/workspace/test_onboarding.py` | RED, unit. With several local work branches, the first-pass fix is exactly the `SeveralWorkBranches` text, at most three steps, naming no `worktree new` lane (fails today: five steps); with one work branch it is unchanged |
| J4.T8 | sr | AC9.2 | `dadaia_workspace/features/workspace/onboarding.py` | REBUILD `_first_pass_fix`: the fourth bullet; owner `test_onboarding.py`; net lines at most -4 |
