# TASKS — 0.5.0 rc-11, Job 3 — lean release state

**Status:** Draft

The following wrapper exists only so the pre-Job-1 checker can validate the definition. J1.T5 removes the heading and Contract line after J1.T2–J1.T4 merge and before this job opens; its task table is unchanged.

## Stage J3.S1 — compatibility wrapper

- Contract: J3.T1 is a RED-only dispatch; J3.T2 is a fresh implementation dispatch and touches no tests; historical releases remain readable and no new stage-shaped or legacy-log data is written.

| task | AC | `W:` | outcome |
|---|---|---|---|
| J3.T1 | AC3.2–AC3.5, AC4.2, AC5.1–AC5.4 | `tests/public/skills/dd_release_implementation/scripts/test_release__lean_state.py`, `tests/features/specs/test_doctor_release.py` | dedicated owner `test_release__lean_state.py`; RED proves lean job documents and DAG overlap refusal, seven-section default, four new-log kinds, legacy reads, explicit open-bug authorization note and entry-only closure memory without sharing Job 2's consumer tests |
| J3.T2 | AC3.2–AC3.5, AC4.2, AC5.1–AC5.4 | `dadaia_workspace/public/skills/dd-release-implementation/scripts/release.py`, `dadaia_workspace/public/skills/dd-release-implementation/scripts/_release_check.py`, `dadaia_workspace/public/skills/dd-release-implementation/scripts/_release_new.py`, `dadaia_workspace/public/skills/dd-release-implementation/scripts/_release_store.py`, `dadaia_workspace/public/skills/dd-release-implementation/RELEASE-EVENTS.md`, `dadaia_workspace/public/schemas/releases/release-state-v1.schema.json`, `dadaia_workspace/features/specs/doctor_release.py` | owner `tests/public/skills/dd_release_implementation/scripts/test_release__lean_state.py`; consume Job 1's schema/phase authority without writing it; emit the shared summary shape that Job 2 tests with a direct fixture, so neither job needs the other's merge; implement four log writers, historical reads, drift plus one memory entry and authorized per-id open-bug carry; supporting release-state prose changes here |
