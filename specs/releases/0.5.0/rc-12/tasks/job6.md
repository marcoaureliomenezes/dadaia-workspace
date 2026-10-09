# Job 6 — CP4: `spec_contexts.json` has one writer (FR5)

**Status:** Approved

Pure refactor: exit codes, fix lines, ledgers, files and JSON output are unchanged, and the Job 3 net stays green and unedited (AC4.3).

- Design: `migrate/state_v2.py` and `reconcile/service.py` receive the store and write through `infrastructure/json_context_store.py`; `reconcile.service` stops importing `capabilities` and `migrate.state_v2` directly (composed by the container), so both `setup.cfg` `ignore_imports` edges are deleted and the ignore cap in `scripts/guards/slop.py` drops by 2 (AC5.2).
- Test actions (net lines ≤ 0, tests included): narrow `test_state_v2.py` and `test_service.py` to the store seam (J6.T1, RED for AC5.1 because today neither module accepts the store); delete the assertions there that re-pin the registry file format the store's own tests (`tests/infrastructure/test_json_context_store*.py`) already pin; lint: the edge count stays pinned by the existing ignore-cap check, no new test.
- Metric (before → after), from the workspace root: `python3 .dadaia/reports/dadaia-workspace/futures-audit/coupling/analyze.py repos/dadaia-workspace <out>` → `ignored_imports` 2 → 0; `git grep -nE "spec_contexts\.json" -- dadaia_workspace` filtered to `write_bytes|write_text|atomic_write|unlink` write sites, counted per module, 3 → 1.

| task | AC | `W:` | outcome |
|---|---|---|---|
| J6.T1 | AC5.1 | `tests/features/migrate/test_state_v2.py`, `tests/features/reconcile/test_service.py` | RED dispatch and test actions: both writers driven through an injected store |
| J6.T2 | AC5.1, AC5.2 | `dadaia_workspace/infrastructure/json_context_store.py`, `dadaia_workspace/features/migrate/state_v2.py`, `dadaia_workspace/features/reconcile/service.py`, `dadaia_workspace/container.py`, `dadaia_workspace/cli/commands/reconcile.py`, `dadaia_workspace/cli/commands/init.py`, `dadaia_workspace/cli/commands/migrate.py`, `setup.cfg` | after J6.T1; source-only: one writer, both `ignore_imports` edges deleted; the container composes the injected dependencies and the three production callers supply them |
| J6.T3 | AC5.2 | `scripts/guards/slop.py` | after J6.T2; the ignore cap in the ignore-cap check drops by 2, the only edit |
