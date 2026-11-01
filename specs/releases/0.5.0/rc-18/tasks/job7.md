# Job 7 — ref gate pins, test quality and the hook's common-dir contract (FR10, FR8, FR9.2, FR3 hook)

**Status:** Draft

Wave 2, waits on Job 5, Job 6. Paths are repository-relative to `repos/dadaia-workspace/`. Design and evidence: PLAN §1 and §1.1.

- **Waits.** Job 5 owns `test__worktree_end__verdict_binding.py`, `test__worktree_end__define_gate.py` and `test__worktree_end.py`; Job 6 owns `tests/cli/commands/test_ci.py` and `tests/features/workspace/test_onboarding.py` and the `ci.py` help this job's fold reads.
- **Test-only rule.** Tasks T3 to T6 touch tests and nothing else; they change no behaviour. Asserts are removed only where AC8.1 names them ("inert" cases removed or made live, vacuous asserts made to assert); the commit names the SPEC order ("Approve (Recommended)") and each removed case. Every other assert stays or is tightened.
- **Hook (T1, T2).** `hooks/ref_transaction.py` cannot import a public skill file; its common-dir read takes the helper's contract (`--path-format=absolute`, the parent of the common dir) and a test pins that the hook and `_git.main_checkout` answer alike for a worktree and its main checkout.
- **AC10.3.** The stale reading at `test_branch_policy.py:253` follows rc-17 AC14.7 (recreating the work branch at another sha is refused). rc-16's SPEC is closed history and is not edited.
- **AC8.1 scope.** The as-is review located the inert verdict-binding cases, the inert `declared_verify` and `test_entity_doctor.py:487-493`; the 13 stale docstrings and the for/if loop are listed by the task's first grep. A file the grep finds outside this job's `W:` is reported to the main thread as a `W:` amendment, never edited.
- **AC8.4.** The conftest-size test writes under `tmp_path`; the merge-time `tests/tmp` residue is reproduced (a merge's `verify:` on a tree, then `git status`) and reported as a `bug-proposal:` finding, or shown gone with the command and its output.

**Gate law (rc-18).** The job's `verify:` is `python scripts/ci.py job` (median 1m52, measured in rc-17; no `verify:` change). An implementer's definition of done is that run, plus the touched test directories (`tests/hooks`, `tests/public/scripts`, `tests/features`, `tests/fixtures`, `tests/scripts`, `tests/infrastructure`, `tests/public/skills/dd_gitflow_default`), plus the own-diff self-check over `git diff <base>...HEAD`: no removed `assert` line and no newly skipped test unless this file names the order, and the sweep greps. No preflight, no full CI line; CI on push is the net. A RED task fails only on its new RED tests and says which. Every task reads `.dadaia/tmp/main-thread/20261018/rc18-common.md`.

**Sweep greps.** `git grep -n '_fix_command' -- tests` prints only the folded home; `git grep -n 'tests/tmp' -- tests/fixtures/test_conftest_size.py` prints nothing; `git diff <base>...HEAD -- tests | grep -E '^-\s*assert'` prints only lines the commit bodies name.

Tasks: 6 (3 jr, 3 sr, 0 pe). `who` names the dispatched role (`dd-release-definition` §5). Parallelism: T1 then T2; T3, T4, T5, T6 have disjoint `W:` and start with T1.

| task | who | AC | `W:` | outcome |
|---|---|---|---|---|
| J7.T1 | sr | AC3.1, AC10.2 | `tests/hooks/test_ref_transaction.py` | RED, integration: a forced, unmarked move of an existing `wt/*` branch passes the hook with no gate added; the hook and `main_checkout` answer alike for a worktree and its main checkout |
| J7.T2 | jr | AC3.1 | `dadaia_workspace/hooks/ref_transaction.py` | closed with no change by ruling (see the closure record). Planned: the hook's common-dir read takes the helper's contract; net lines at most 0 |
| J7.T3 | sr | AC10.3, AC8.5 | `tests/features/chokepoints/test_branch_policy.py`, `tests/public/scripts/test_reference_transaction__work_branch.py`, `tests/public/scripts/test_reference_transaction.py`, `tests/fixtures/fix_world.py` | test-only: the `:253` reading reconciled; "a refusal's fix line runs" has one home in the `fix_world` census and `_fix_command` and its copies (`work_branch.py:470-520`, `test_reference_transaction.py:208`, `test_branch_policy.py:277`) fold into it |
| J7.T4 | sr | AC8.1 | `tests/public/skills/dd_gitflow_default/scripts/test__worktree_end__verdict_binding.py`, `tests/public/skills/dd_gitflow_default/scripts/test__worktree_end__define_gate.py`, `tests/infrastructure/test_entity_doctor.py`, `tests/public/skills/dd_gitflow_default/scripts/test__worktree_end.py` (main-thread `W:` amendment: `test__worktree_end.py`) | test-only: inert verdict-binding cases and the inert `declared_verify` made live or removed, the for/if setup loop flattened, the lost dirty-tree case restored, the stale docstrings corrected, the vacuous asserts at `:487-493` made to assert |
| J7.T5 | jr | AC8.2, AC8.3, AC8.4 | `tests/scripts/test_ci.py`, `tests/features/workspace/test_onboarding.py`, `tests/fixtures/test_conftest_size.py` | test-only: the `verify:` pin has one home (`test_ci.py:151` goes); `test_onboarding.py:153-162` takes opaque strings; the size test writes under `tmp_path` |
| J7.T6 | jr | AC9.2 | `tests/features/specs/test_canon__scaffold_placeholder_repair.py` | docstring only: the overreach and the false "the upgrade dry run reports it" go |
| J7.T7 | sr | AC8.1, AC8.5, AC10.2 | `tests/hooks/test_ref_transaction.py`, `tests/fixtures/fix_world.py`, `tests/public/skills/dd_gitflow_default/scripts/test__worktree_end.py`, `tests/core/test_cli_line__refusal_fix_lines_clear_their_refusal.py` | job-7 review: the forced `wt/*` move runs through git with the hook installed, to a commit off the old tip; the census runs the printed fix (runner and slug parsed from it); the job-merge verdict test named for what it asserts |
| J7.T8 | jr | AC8.5 | `tests/fixtures/fix_world.py`, `tests/core/test_cli_line__fix_line_contract.py`, `tests/core/test_cli_line__refusal_fix_lines_clear_their_refusal.py` | `60e9741ea`: `Case.play` is the one place that plays a case's act with the printed fix, for both census drivers |

**Closure record (main thread, 2026-10-18).** 2 tasks landed beyond the PLAN, the rows after the planned ones, read from `git log wt/0.5.0/rc-18/wt-rc`.

- Ruled, the "Hook" bullet above: the helper contract is `rev-parse --git-common-dir`, resolved, its parent, not `--path-format=absolute`; J7.T2 closed with no change.
- Ruled, AC8.2: `tests/scripts/test_ci.py:151` stays; it pins `ci.py`'s step plan, and the `verify:` line's one home is `test__worktree_end.py`. J7.T5 left `test_ci.py` unchanged.
- Ruled, AC8.4 narrowed: conftest classification stays keyed to the checkout, so `test_conftest_size.py` keeps its `tests/tmp/` module; `test_suite_session_env.py` places its module in the checkout, since its subject is the checkout tripwire. The merge-time residue is the main thread's reproduction at the job-7 merge; its result was not given to the closure pass. The job-7 review and re-review each read `git status --short --ignored` after `ci.py job`: only `__pycache__`, no `tests/tmp`.
- Ruled, AC8.1: "13 stale docstrings" has no recorded source list (source list not recorded); it is bounded to the four touched files, 3 corrected.
- Ruled, AC8.5: one census row, for the work-branch force refusal; the creation and recreate refusals stay outside the census and go to the backlog (`rc18-review-loose-ends`).
- Ruled, J7.T7/T8: the census runs the printed fix; `Case.play` is the one place that plays a case's act, for both census drivers.
- `W:` amendment (main thread): J7.T4 writes `test__worktree_end.py`.
