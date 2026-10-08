# TASKS — 0.5.0 rc-11, Job 4 — structural derivation without hashes

**Status:** Approved

J1.T5 removes the pre-Job-1 compatibility heading and Contract label after J1.T2–J1.T4 merge and before this job opens; its task table is unchanged.

J4.T1 is a RED-only dispatch; J4.T2 is a fresh implementation dispatch and touches no tests; structural registry/grant/source checks and public privacy remain green without content hashes.

| task | AC | `W:` | outcome |
|---|---|---|---|
| J4.T1 | AC7.1, AC8.3 | `tests/infrastructure/test_entity_doctor.py`, `tests/infrastructure/test_entity_doctor__agentic_entities_derivation.py`, `tests/infrastructure/test_entity_doctor__entities_derivation_behavioral.py`, `tests/cli/test_help_digest.py`, `tests/public/skills/dd_gitflow_default/scripts/test__worktree_end.py` | deletion tests remove entity/hash assertions while retaining registry, grants, ownership, source/projection and privacy behavior; memory checker absence is pinned; doc-hash validator deletion is already owned by J1.T1 |
| J4.T2 | AC7.1, AC8.3 | `dadaia_workspace/public/entities/behavior-map.json`, `dadaia_workspace/public/schemas/behavior-map-v1.schema.json`, `dadaia_workspace/infrastructure/entity_doctor.py`, `dadaia_workspace/infrastructure/ledger_scripts.py`, `dadaia_workspace/cli/help_digest.py`, `dadaia_workspace/public/skills/dd-release-implementation/MEMORY-UPDATE.md`, `README.md`, `llms.txt`, `docs/cli.md`, `docs/distribution.md`, `docs/index.md`, `docs/positioning.md`, `docs/quickstart.md` | delete `hash_tuple` and the remaining hash-only section markers; preserve structural ownership; remove memory checker from doctor ledger scripts; worktree and bug semantic docs are co-located with Jobs 1 and 2, and product-memory edits remain reconciliation work |
