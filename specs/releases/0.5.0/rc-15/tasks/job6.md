# Job 6 — the closure worklist decider lives in the kernel; the job gate runs `doctor` (FR5)

**Status:** Draft

Wave 2, after Job 3 (both edit `scripts/ci.py`). The release skill's only non-kernel skill import is the navigator's `_memory_drift` (`report`, `render`, `git`; `Refusal` is already the kernel class). The module moves to the kernel with its decisions unchanged (Q3 option B, agent default); `CATALOG` moves to `_specs.py`. 5 ledger bugs sit on `_memory_drift.py`: its tests and decisions stay, only its placement changes. `memory.py` keeps working because the navigator's entry bootstrap already names the kernel folder.

- **Seams closed.**
  - The module keeps its name, `git mv` into `dd-bug-resolution/scripts/`; the navigator's copy is removed in the same task.
  - `CATALOG` is imported from `_specs` by `_memory_check.py`, `_memory_catalog.py`, `memory.py` and `_memory_drift.py`; `_memory_schema.py` stops defining it and does not re-export it.
  - `release.py` is unchanged: it reaches `drift` through `_release_tree`'s `__all__`.
  - The thin-wrapper test's body becomes one helper that returns a script's foreign imports; the contract test and a planted-import test both call it. The plants: a release script importing `_memory_catalog` (a sibling of another skill) and a module with a `sys.path` line naming another skill.
  - AC5.3 re-measure: `python -m dadaia_workspace doctor --specs-dir specs` wall time against one `python scripts/ci.py job` run, both in the commit body (0.91 s measured in the as-is review; the gate-cost line holds while it stays below one gate run).
  - **Main-thread ruling (2026-10-13) named in `test(J6.T3)`:** `test_job_verify_is_the_fast_check` gains `"doctor: doctor"` at the end of its expected list; nothing is removed or loosened.
- Test-side first: T1, T2, T3 (disjoint `W:`). Then T4, T5.
- Commit bodies carry `git grep -nE '_CROSS_SKILL_EDGES|_EDGE_PATH_LINES|_memory_drift' -- dadaia_workspace scripts tests` and `git grep -n 'sys.path.insert' -- dadaia_workspace/public/skills/dd-release-implementation`.
- Pre-review checklist: one decider for the worklist; the only skill-to-skill edge is the kernel; sweep lines; no platform fact; net lines about 0 (121 move; six allowlist lines and the insert leave).

Tasks: 5 (1 jr, 4 sr). `who` names the dispatched role (`dd-release-definition` §5).

| task | who | AC | `W:` | outcome |
|---|---|---|---|---|
| J6.T1 | sr | AC5.2 | `tests/infrastructure/test_public_assets__public_scripts_thin_wrapper.py` | RED, unit: the two allowlists and their uses leave; any import outside the stdlib, the skill folder and the kernel fails; the planted cross-skill import and `sys.path` line turn it red. The suite is red on `_release_tree.py` until T4. A tightening: the reviewer reverts T4 to confirm. Owner this file |
| J6.T2 | sr | AC5.1 | `tests/public/skills/dd_spec_navigator/scripts/test__memory_drift.py` | the `sys.path` setup at `:196,236` names the kernel only (support code in a `test(J6.T2)` commit; no assert edited). Red until T4 |
| J6.T3 | sr | AC5.3 | `tests/scripts/test_ci.py` | the expected plan gains `doctor: doctor`, with the ruling named. Red until T5 |
| J6.T4 | sr | AC5.1, AC5.2 | `dadaia_workspace/public/skills/dd-bug-resolution/scripts/_memory_drift.py`, `dadaia_workspace/public/skills/dd-spec-navigator/scripts/_memory_drift.py`, `dadaia_workspace/public/skills/dd-bug-resolution/scripts/_specs.py`, `dadaia_workspace/public/skills/dd-spec-navigator/scripts/_memory_schema.py`, `dadaia_workspace/public/skills/dd-spec-navigator/scripts/_memory_check.py`, `dadaia_workspace/public/skills/dd-spec-navigator/scripts/_memory_catalog.py`, `dadaia_workspace/public/skills/dd-spec-navigator/scripts/memory.py`, `dadaia_workspace/public/skills/dd-release-implementation/scripts/_release_tree.py` | the move as the intro says, and the `sys.path.insert` at `_release_tree.py:19` leaves. Owners T1, T2 and the existing `test__memory_drift*.py`, `test_memory*.py`, `test_release*.py` unedited. After T1, T2 |
| J6.T5 | jr | AC5.3 | `scripts/ci.py` | `STAGE` gains `doctor` (the existing job); no new check. Owner T3. After T3, T4 |
