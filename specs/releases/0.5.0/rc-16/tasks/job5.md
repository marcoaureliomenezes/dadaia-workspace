# Job 5 — Consumers: closure rule, verdict, fix lines, `--specs-dir` lane (FR5; bug-window R3; `new-reconcile-opens-while-a-job-is-open`)

**Status:** Draft

Wave 3, waits on Job 4. Paths are repository-relative to `repos/dadaia-workspace/`. Design and evidence: PLAN §1 and the as-is review it points to.

- **Bug `new-reconcile-opens-while-a-job-is-open`.** Closure refuses any open job, task or lane tree of the repo and passes when only rcs' `wt-rc` trees are open (`_refuse_open_worktrees`, `_release_phase.py:62-95`; the `f"{nxt}/define"` exception added by a fix is deleted). Reconcile is the last commits of `wt-rc`: `phase CLOSURE` first. T1's RED names the bug. Prior diffs: `d68a7c42f`.
- **Closure exempts the tree it runs from (AC5.5).** Today the clause `Path(r['path']) != top[0]` (`_release_phase.py:89-90`) exempts it; the new rule keeps it, for the old `reconcile` tree and a future `wt-rc` alike. Without it `phase CLOSURE` run from rc-16's own old-layout reconcile tree refuses itself (review MEDIUM). T1 pins it: a CLOSURE run from an open tree of any kind passes when no other tree is open.
- `verdict.py stats <M.m.p>-rc<N>` counts trees under `wt/<M.m.p>/rc-<N>/`. Its internal calls stay on the sibling script (`verdict.py:27`: the `hash` call and `_release_phase._worktree_rows` run the skill's own entry point, the law's shape; no skill-to-CLI hop). Only PRINTED fix lines say `dadaia worktree …`.
- Every fix line printed by this job's own files names `dadaia worktree …` (`_specs.py:54`, `gate_policy.py:53`, `ledger_scripts.py:213`); the sweep here covers only this job's `W:`. The full-library sweep is Job 9. `ci.yml:4-5` comment updated; `wt/**` trigger stays.
- **R3 (AC5.4).** An explicit `--specs-dir` holding no tree reports one finding carrying `state()`'s fix from the specs-section builder; `_absent_tree` (`cli/commands/doctor.py:196`) and the `target = None` reassignment (`:303-304`) are gone; net ≤ 0. Kept tests: those of `doctor-ledger-lane-absent-specs-dir-fix-never-clears` and its two predecessors, asserts unchanged. T8 edits `ledger_scripts.py` after T6.

Tasks: 8 (4 jr, 4 sr, 0 pe). `who` names the dispatched role (`dd-release-definition` §5). Parallelism: T1, T3, T5, T7 (REDs) start together; T2, T4, T6 follow their REDs; T8 after T6.

| task | who | AC | `W:` | outcome |
|---|---|---|---|---|
| J5.T1 | sr | AC5.1, AC5.5 | `tests/public/skills/dd_bug_resolution/scripts/test__specs__workspace_root.py` | RED (rows are stubs), named for `new-reconcile-opens-while-a-job-is-open`: `phase CLOSURE` refuses while a job, task or lane tree is open and passes when only rcs' `wt-rc` trees are open; it passes when the only open tree is the one it runs from (AC5.5); the stacked `release.py new` flow is unchanged |
| J5.T2 | jr | AC5.1, AC5.5 | `dadaia_workspace/public/skills/dd-release-implementation/scripts/_release_phase.py` | `_refuse_open_worktrees` over the new rule, keeping the own-tree clause (≈ −8); owner T1. After T1 |
| J5.T3 | sr | AC5.2 | `tests/public/skills/dd_handoff_emitter/scripts/test_verdict.py`, `tests/public/skills/dd_handoff_emitter/scripts/test_verdict__characterization.py` | RED: `stats` counts verdicts of trees under `wt/<M.m.p>/rc-<N>/`; the writer's `hash` binding still runs the sibling script |
| J5.T4 | jr | AC5.2 | `dadaia_workspace/public/skills/dd-handoff-emitter/scripts/verdict.py` | the `stats` prefix only (±1); owner T3. After T3 |
| J5.T5 | sr | AC5.3 | `tests/core/test_cli_line__fix_line_contract.py`, `tests/core/test_cli_line__refusal_fix_lines_clear_their_refusal.py`, `tests/features/spec_context/test_gate_policy.py`, `tests/infrastructure/test_ledger_scripts.py` | RED first as `test(J5.T5)`: every fix line printed by the gate, the rows reader and the kernel names `dadaia worktree …` and is a runnable command |
| J5.T6 | jr | AC5.3 | `dadaia_workspace/public/skills/dd-bug-resolution/scripts/_specs.py`, `dadaia_workspace/features/spec_context/gate_policy.py`, `dadaia_workspace/infrastructure/ledger_scripts.py`, `.github/workflows/ci.yml` | fix-line strings, the `_specs.py:23` docstring and the `ci.yml` comment; owner T5. After T5; sweep `grep -n 'worktree\.py'` over these four files leaves only the resolve constants |
| J5.T7 | sr | AC5.4 | `tests/cli/commands/test_doctor__doctor_without_an_instance.py`, `tests/cli/commands/test_doctor__doctor_sections.py` | RED = the three predecessor bugs' cases with unchanged asserts, plus one finding for an absent explicit tree |
| J5.T8 | jr | AC5.4 | `dadaia_workspace/cli/commands/doctor.py`, `dadaia_workspace/infrastructure/ledger_scripts.py` | delete `_absent_tree` and the reassignment; the ledger lane keeps its one guard (net ≤ 0); owner T7. After T6 (same file `ledger_scripts.py`) and T7 |
