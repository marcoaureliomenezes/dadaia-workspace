# Job 9 — Activation: the hook becomes installable, the fix-line sweep covers the whole library (FR9)

**Status:** Draft

Wave 4, waits on Jobs 1–8. Paths are repository-relative to `repos/dadaia-workspace/`. Design and evidence: PLAN §1 and the as-is review it points to.

- **Why last.** The `reference-transaction` hook refuses creation of a `wt/*` ref outside `DADAIA_WT=1`. The installer is table-driven (`install_git_hooks`, `service.py:160-183`; `ci install-hook`, `context create`, `context alive`), so the `INSTALLED_GIT_HOOKS` row is the moment the hook becomes installable. Added in Job 3 it would let HOOKS-DRIFT-1 fence every repo against a hook the instance's WT cannot pass yet: a BLOCK whose fix is blocked, a Stall (review HIGH 5). After Jobs 1–8 the tool can pass the hook; the row lands here and nowhere earlier.
- **Installing is still the rollout's act.** This job adds the row and its hash entry; no repo gets the hook until `ci install-hook --force` runs after `public install` (PLAN §2 rollout).
- **Full fix-line sweep (AC9.2).** Jobs 4 and 5 sweep only their own `W:`. Here, with every code job merged, one test and two greps cover the library:
  - the test (T3) scans the string literals of `dadaia_workspace/**/*.py` that begin `fix:` or are passed to `fix_line`/`spell_fix` and finds none naming `worktree.py`;
  - `grep -rn 'worktree\.py' dadaia_workspace .github scripts` leaves only the resolve constants (`_worktree_names.SCRIPT`, `ledger_scripts.WORKTREE_SCRIPT`, `gate_policy._WORKTREE_SCRIPT`, `verdict.py:27`, `_release_phase.py:63-64`) and docstrings of the script's own verbs; the 6 `.md` hits are Job 6's and are zero by then;
  - a red sweep is a finding returned to the main thread (a PLAN amendment), never a write outside `W:`.
- Net production lines ≈ +1 (one row), tests ≈ +60.

Tasks: 3 (1 jr, 2 sr, 0 pe). `who` names the dispatched role (`dd-release-definition` §5). Parallelism: {T1→T2} and {T3} are independent and start together (disjoint `W:`).

| task | who | AC | `W:` | outcome |
|---|---|---|---|---|
| J9.T1 | sr | AC9.1 | `tests/features/spec_context/test_doctor__hooks_drift.py`, `tests/features/spec_context/test_service__hook_refresh.py` | RED: HOOKS-DRIFT-1 reports the `reference-transaction` row absent in a repo that lacks it, with a runnable `ci install-hook --force` fix; `install_git_hooks` writes it, marker-guarded and executable; the existing pre-push row cases keep their asserts |
| J9.T2 | jr | AC9.1 | `dadaia_workspace/core/workspace_layout.py`, `dadaia_workspace/public/templates/shipped-hashes.json` | one `INSTALLED_GIT_HOOKS` row (+1), one append-only hash entry; owner T1. After T1 |
| J9.T3 | sr | AC9.2 | `tests/core/test_cli_line__fix_line_contract.py` | RED-or-green sweep test per the intro: no `fix:`-prefixed or `fix_line`/`spell_fix` string literal in `dadaia_workspace/**/*.py` names `worktree.py`; the commit body lists the two greps with their hit counts |
