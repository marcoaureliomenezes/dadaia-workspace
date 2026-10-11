# Job 9 — harness switching is cheap: the entity registry derives its per-harness implementations (FR5)

**Status:** Draft

Wave 2, after Job 6 (both edit `entity_doctor.py`). Operator ruling (2026-10-11): no harness is removed; the strategy is that switching harness changes little, so what the harness records already say is stated once. `entities/registry.json` lists, per behavior and rule, a prose string per harness that restates `core/harness_registry.py` (the directory and the hook format) and `hook_wrappers.py` (the lanes); 119 lines, seven `implementations` objects of six entries each.

- The registry keeps each entity's `id`, `mandate` and, for a behavior, its hook `modules`; it names only the exceptions, as `gaps: {harness: reason}` (for instance a harness whose hook format has no prompt-time lane, or no env block).
- The entity doctor derives "behavior X is implemented by harness H" as: H is a record of `HARNESS_RECORDS`, H is not in X's `gaps`, and the hook table of H carries the lane X needs. Adding a harness record needs no registry edit.
- Test-side first: T1; then T2; then T3.
- Net lines: the registry shrinks by about 55 lines; the doctor gains about 15; three tests port.

Tasks: 3 (1 jr, 2 sr). `who` names the dispatched role (SPEC FR5 of rc-13, `dd-release-definition` §5).

| task | who | AC | `W:` | outcome |
|---|---|---|---|---|
| J9.T1 | sr | AC5.1 | `tests/infrastructure/test_entity_doctor__entities_derivation_behavioral.py` | RED, unit: a registry with no `implementations` and a `gaps` map passes the entity doctor when every harness record is covered or gapped; a harness record added to a fake record table without any registry edit passes; a `gaps` key that names no harness record, and a hook module no behavior names, fail. Owner that file |
| J9.T2 | sr | AC5.1 | `dadaia_workspace/public/entities/registry.json`, `dadaia_workspace/infrastructure/entity_doctor.py` | REBUILD: replace each `implementations` object by `gaps` (and `modules` for behaviors); derive the coverage from the harness records and the hook table; delete the prose strings. Owner T1. Net lines ≤ 0 |
| J9.T3 | jr | AC5.1 | `tests/infrastructure/test_entity_doctor__agentic_entities_derivation.py`, `tests/infrastructure/test_projection_rules__hook_behaviour_coverage.py`, `tests/core/test_atomic_write__core_file_io_purity.py` | port the three readers of `implementations` (`:147-165`, `:153`, `:368`) to the derived coverage and `modules`; no assert of a surviving contract is rewritten. After T2 |
