# TASKS — 0.5.0 rc-11, Job 3 — lean release state

**Status:** Approved

J1.T5 removes the pre-Job-1 compatibility heading and Contract label after J1.T2–J1.T4 merge and before this job opens; its task table is unchanged.

J3.T1 and J3.T2 remain the original RED/source pair; J3.T2 is already task-merged. Fresh source-only J3.T3 uses the unchanged Job 2 summary-Origin JSON RED as its acceptance input and touches no test. Job 3 must merge before J2.T2 completes; historical releases remain readable and no new stage-shaped or legacy-log data is written.

| task | AC | `W:` | outcome |
|---|---|---|---|
| J3.T1 | AC3.2–AC3.5, AC4.2, AC5.1–AC5.4 | `tests/public/skills/dd_release_implementation/scripts/test_release__lean_state.py`, `tests/features/specs/test_doctor_release.py` | dedicated owner `test_release__lean_state.py`; RED proves lean job documents and DAG overlap refusal, seven-section default, four new-log kinds, legacy reads, explicit open-bug authorization note and entry-only closure memory without sharing Job 2's consumer tests |
| J3.T2 | AC3.2–AC3.5, AC4.2, AC5.1–AC5.4 | `dadaia_workspace/public/skills/dd-release-implementation/scripts/release.py`, `dadaia_workspace/public/skills/dd-release-implementation/scripts/_release_check.py`, `dadaia_workspace/public/skills/dd-release-implementation/scripts/_release_new.py`, `dadaia_workspace/public/skills/dd-release-implementation/scripts/_release_store.py`, `dadaia_workspace/public/skills/dd-release-implementation/RELEASE-EVENTS.md`, `dadaia_workspace/public/schemas/releases/release-state-v1.schema.json`, `dadaia_workspace/features/specs/doctor_release.py` | owner `tests/public/skills/dd_release_implementation/scripts/test_release__lean_state.py`; consume Job 1's schema/phase authority without writing it; emit the shared summary shape that Job 2 tests with a direct fixture, so neither job needs the other's merge; implement four log writers, historical reads, drift plus one memory entry and authorized per-id open-bug carry; supporting release-state prose changes here |
| J3.T3 | AC5.1 | `dadaia_workspace/public/skills/dd-release-implementation/scripts/release.py` | fresh source-only caller correction: `release.py check --json` must serialize the informational Origin trace rows produced from the closure summary while its exit status continues to derive only from error rows; reuse the existing check result and add no second Origin parser, output path or Job 2 source edit |
