# Job 3 — the template selector (FR4)

**Status:** Draft

Wave 2, with Job 2. `public install --template <id>` is the only writer of `applied_template` and feeds the one whole install: no template-only re-projection, no flag on `reconcile`, no `upgrade` verb (replace-don't-layer; the `--only` flag was deleted by `671a7458e` for making a second plan). The template is validated before any write, so an unknown id leaves the overlay and the projections unchanged. All files here are new tests or production edits of units no other job in the wave writes.

- Order: T1–T3 (RED, disjoint, parallel) then T4, T5 and T6 (each needs its RED; disjoint).
- Commit bodies carry `git grep -n 'template' -- dadaia_workspace/cli/commands` hit lines for the sweep that no second selector path exists, and the diff stays at two options and one `save` call in production code.

Tasks: 6 (6 sr, 0 jr).

| task | who | AC | `W:` | outcome |
|---|---|---|---|---|
| J3.T1 | sr | AC4.1, AC4.2 | `tests/infrastructure/test_public_assets__template_selector.py` | RED, integration: `install(template="economy")` saves `applied_template` and projects the economy cells; an unknown id raises with the valid ids named and leaves overlay and projections unchanged; no `template` keeps the saved one. New file, owner `tests/infrastructure/test_public_assets__template_selector.py` |
| J3.T2 | sr | AC4.1, AC4.2 | `tests/cli/commands/test_public__template.py` | RED, integration: `dadaia public install --template economy` exits 0 and writes the overlay; `--template nope` exits non-zero naming the valid ids; no flag keeps the template; `--help` lists the ids. New file, owner `tests/cli/commands/test_public__template.py` |
| J3.T3 | sr | AC4.3 | `tests/cli/commands/test_init__template.py` | RED, integration: `init DIR --template economy` on a new workspace and on a re-run switches the saved template and re-projects; no flag keeps it; `reconcile` keeps the saved template. New file, owner `tests/cli/commands/test_init__template.py` |
| J3.T4 | sr | AC4.1, AC4.2 | `dadaia_workspace/infrastructure/public_assets.py`, `dadaia_workspace/features/public/service.py` | `install(..., template=None)`: validate with `template_by_id`, save through `JsonAgentModelPolicyStore.save` before `_load_agent_policy` in `_resolve_install_plan`; `PublicAssetService.install` forwards it. Owner T1. After T1 |
| J3.T5 | sr | AC4.1, AC4.2 | `dadaia_workspace/cli/commands/public.py` | one `--template` option on `public install`, valid ids from `TEMPLATES`, forwarded to the service. Owner T2. After T2 and T4 |
| J3.T6 | sr | AC4.3 | `dadaia_workspace/cli/commands/init.py`, `dadaia_workspace/features/workspace/service.py` | the same flag on `init`, forwarded by `WorkspaceService.init` to the same `install`; the re-init upgrade path is unchanged. Owner T3. After T3 and T4 |
