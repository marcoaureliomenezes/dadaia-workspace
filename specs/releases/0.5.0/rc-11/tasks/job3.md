# TASKS — 0.5.0 rc-11, Job 3 — lean release state

**Status:** Draft

The following wrapper exists only so the pre-Job-1 checker can validate the definition. J1.T4 removes the heading and Contract line before this job opens; its task table is unchanged.

## Stage J3.S1 — compatibility wrapper

- Contract: J3.T1 is a RED-only dispatch; J3.T2 is a fresh implementation dispatch and touches no tests; historical releases remain readable and no new stage-shaped or legacy-log data is written.

| task | AC | `W:` | outcome |
|---|---|---|---|
| J3.T1 | AC3.2–AC3.5, AC4.2, AC4.3, AC5.1–AC5.4 | `tests/public/skills/dd_release_implementation/scripts/test__release_schema.py`, `tests/public/skills/dd_release_implementation/scripts/test_release.py`, `tests/public/skills/dd_release_implementation/scripts/test_release__release_script.py`, `tests/features/specs/test_doctor_release.py` | RED rows prove lean job documents and DAG overlap refusal, seven-section default, four new-log kinds, legacy reads, explicit open-bug authorization note and entry-only closure memory |
| J3.T2 | AC3.2–AC3.5, AC4.2, AC4.3, AC5.1–AC5.4 | `dadaia_workspace/public/skills/dd-release-implementation/scripts/release.py`, `dadaia_workspace/public/skills/dd-release-implementation/scripts/_release_check.py`, `dadaia_workspace/public/skills/dd-release-implementation/scripts/_release_tree.py`, `dadaia_workspace/public/skills/dd-release-implementation/scripts/_release_new.py`, `dadaia_workspace/public/skills/dd-release-implementation/scripts/_release_phase.py`, `dadaia_workspace/public/skills/dd-release-implementation/scripts/_release_store.py`, `dadaia_workspace/public/schemas/releases/release-state-v1.schema.json`, `dadaia_workspace/features/specs/doctor_release.py` | retain Job 1's schema parser as authority; remove stage/contracts/balance coupling; implement four log writers, historical reads, summary tracing, drift plus one memory entry and authorized per-id open-bug carry |
