# TASKS — 0.5.0 rc-11, Job 4 — structural derivation without hashes

**Status:** Draft

The following wrapper exists only so the pre-Job-1 checker can validate the definition. J1.T4 removes the heading and Contract line before this job opens; its task table is unchanged.

## Stage J4.S1 — compatibility wrapper

- Contract: J4.T1 is a RED-only dispatch; J4.T2 is a fresh implementation dispatch and touches no tests; structural registry/grant/source checks and public privacy remain green without content hashes.

| task | AC | `W:` | outcome |
|---|---|---|---|
| J4.T1 | AC7.1, AC8.3 | `tests/contract/test_docs_derived_from_memory.py`, `tests/infrastructure/test_entity_doctor.py`, `tests/infrastructure/test_entity_doctor__agentic_entities_derivation.py`, `tests/infrastructure/test_entity_doctor__entities_derivation_behavioral.py`, `tests/cli/test_help_digest.py`, `tests/public/skills/dd_gitflow_default/scripts/test__worktree_end.py` | deletion tests remove hash assertions while retaining registry, grants, ownership, source/projection and privacy behavior; memory checker absence is pinned |
| J4.T2 | AC7.1, AC8.3 | `dadaia_workspace/public/entities/behavior-map.json`, `dadaia_workspace/public/schemas/behavior-map-v1.schema.json`, `dadaia_workspace/infrastructure/entity_doctor.py`, `dadaia_workspace/infrastructure/ledger_scripts.py`, `dadaia_workspace/cli/help_digest.py`, `dadaia_workspace/public/skills/dd-release-implementation/MEMORY-UPDATE.md`, `README.md`, `llms.txt`, `docs/bug-ledger-lessons.md`, `docs/bug-loop.md`, `docs/cli.md`, `docs/concepts.md`, `docs/distribution.md`, `docs/getting-started.md`, `docs/index.md`, `docs/positioning.md`, `docs/quickstart.md` | delete `hash_tuple`, section markers and validators; preserve structural ownership; remove memory checker from doctor ledger scripts; product-memory edits remain reconciliation work |
