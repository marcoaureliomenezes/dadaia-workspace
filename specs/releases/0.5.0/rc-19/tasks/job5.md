# Job 5 — dadaia export: read-only, soft and hard (FR5, ADRs 0175 + 0272)

**Status:** Draft

Wave 3, waits on Job 3 (`write_bundle`) and Job 4 (`export/service.py`, the model). Paths are repository-relative to `repos/dadaia-workspace/`. Design and evidence: PLAN §1, §1.1, §2 (seams R3, R5).

- **Owner (T5, T6).** `ExportService` writes the artifacts and is the reader's owner (the read half lands in Job 6 with its consumer). The registry stays byte-identical. A repo with no remote is recorded with url `null`, main or associated alike. `state` is the registry's lowercase value. `schema_version` is `export-v1` (`EXPORT_SCHEMA_VERSION`). `export --help` stops naming `import`.
- **Hard (T6).** One `workspace-export.tar.gz` (names: PLAN §2) built with `tarfile`, members named by `as_posix()`: `spec-contexts.json` and `<repo>/<name>.bundle`. The bundles of open lanes and `wt-rc` trees come from `write_bundle` through `load_owner("dd-gitflow-default", "_worktree_pause")` (the `core/gitflow.py` precedent), made into a scratch dir under `.dadaia/tmp/` at export time and not left in `dist`; pause bundles are copied. A dirty open tree refuses with pause's commit-first fix line and the tree stays; job and task trees are not carried.
- **Scan (T7).** The container supplies `scan_bundle(bundle, repo)` as a callable, like `SecretScan`: a scratch bare repo under `.dadaia/tmp/` with `objects/info/alternates` to the repo's object store, one `refs/remotes/origin/p<i>` per prerequisite sha of the bundle header, `git bundle unbundle`, then `new_objects(scratch, head, "")` through the pre-push matcher with its denylist and baseline. No ref or object is written into `repos/<slug>`; no archive is left when a scan hits.
- **Schema (T5).** `dadaia_workspace/public/schemas/export-v1.schema.json` is shipped, found by `_ledger.load_schema`'s `rglob`; the JSON is validated by `_ledger.validate` reached as `load_owner` does for other skills.

**Gate law.** `verify:` `python scripts/ci.py job`, no change. Definition of done: that run, `tests/features/export`, `tests/cli`, `tests/test_container.py`, the own-diff self-check; T8 also runs `test_public__characterization.py` and `test_init__characterization.py` by name.

**Sweep greps.** `git grep -nE "_refresh_branches|spec-contexts-export-v1" -- dadaia_workspace/ tests` prints nothing; `git grep -n "git bundle create" -- dadaia_workspace/` still prints only `_worktree_pause.py`.

Tasks: 8 (7 sr, 1 jr). T1 to T4 REDs (serial where they share a file); T5 after T1 and T2; T6 after T3 and T5; T7 after T4 and T6; T8 after T7.

| task | who | AC | `W:` | outcome |
|---|---|---|---|---|
| J5.T1 | sr | AC5.1, AC5.2 | `tests/features/export/test_service.py`, `tests/cli/commands/test_export.py` | RED, integration: the soft artifact holds `export-v1`, contexts (slug, name, lowercase state, url, associated), `dadaia_version`, the harnesses of the profile; the registry is byte-identical after `export`; a repo with no remote is `null`; `export --help` does not name `import`; the old-format rows are replaced in this `test(...)` commit naming ADR 0272's acceptance |
| J5.T2 | sr | AC5.5 | `tests/features/export/test_export_schema.py` | RED, unit, new file: the shipped schema validates both artifacts' JSON and refuses a wrong `state` casing and a missing `schema_version` |
| J5.T3 | sr | AC5.3 | `tests/features/export/test_export_hard.py` | RED, integration, new file: `export --hard` writes one `.tar.gz` of the JSON and `<repo>/<name>.bundle` members only (POSIX names); a bundle of each open lane and `wt-rc`, each pause bundle; a dirty open tree refuses with pause's fix line and stays; a job tree is not carried |
| J5.T4 | sr | AC5.4 | `tests/features/export/test_export_hard.py` | RED, integration: a secret planted in a lane's unpushed commit makes `export --hard` refuse and leave no archive; no ref appears in `repos/<slug>` |
| J5.T5 | sr | AC5.1, AC5.2, AC5.5 | `dadaia_workspace/public/schemas/export-v1.schema.json`, `dadaia_workspace/features/export/service.py`, `dadaia_workspace/core/models/spec_context.py`, `dadaia_workspace/cli/commands/export.py` | REBUILD of `ExportService.run` as the soft writer, `--hard` option declared, schema shipped; owner T1 and T2 tests; net lines at most +60 |
| J5.T6 | sr | AC5.3, AC5.5 | `dadaia_workspace/features/export/service.py`, `dadaia_workspace/container.py` | hard export: members, bundles through `write_bundle`, pause bundles; owner the T3 tests |
| J5.T7 | sr | AC5.4 | `dadaia_workspace/features/export/service.py`, `dadaia_workspace/container.py` | the scan callable and the container's `scan_bundle`; owner the T4 tests |
| J5.T8 | jr | AC5.1, AC5.3 | `docs/cli.md`, `tests/cli/commands/test_public__characterization.py`, `tests/cli/commands/test_init__characterization.py` | regenerate `docs/cli.md` from the tree (`python -c` calling `render_digest()` and writing the file; never by hand); `test(...)`: install-count literals +1 asset (the schema), both platforms, recounted |
