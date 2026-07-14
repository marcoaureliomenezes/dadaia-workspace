# Closure: Release - v0.2.4

> **Status:** Aprovado
> **Release ID:** v0.2.4
> **Owner:** product-engineer
> **Closed:** 2026-07-14

## Summary

v0.2.4 prevents every projected Python hook runtime from writing import bytecode into a
managed repository. Claude command generation, Codex executable wrappers, the workspace
ctx-inject registration, and PI's direct subprocess now invoke Python with `-B`.

The hotfix also replaces an already-registered bytecode-writing ctx-inject command during
workspace reinitialization and adds an executed regression that runs the generated Codex
wrapper from a source-shaped repository with `PYTHONDONTWRITEBYTECODE` absent.

## Tasks completed

| Task ID | Description | Final commit |
|---|---|---|
| T1 | Suppress hook-runtime bytecode across Claude, Codex, and PI | `73b18b88ab6c7c368c89ee90595f825fd148e356` |
| T2 | Verify, disposition, and close the hotfix | `73b18b88ab6c7c368c89ee90595f825fd148e356` |

## Validations

| Description | Command | Evidence |
|---|---|---|
| Executed installed Codex wrapper | remove bytecode, then `printf '{}' \| .dadaia/hooks/codex-pre-gate` from the source repo | zero `__pycache__` directories and zero `.pyc` files after execution |
| Focused cross-harness projection tests | `.dadaia/.venv/bin/python -m pytest -p no:cacheprovider -q tests/unit/infrastructure/test_public_assets_hooks.py tests/unit/features/workspace/test_service_harness_profile.py tests/integration/test_public_assets.py` | `13 passed in 4.02s` |
| Full Python suite | `PYTHONDONTWRITEBYTECODE=1 .dadaia/.venv/bin/python -m pytest -p no:cacheprovider -q` | `2648 passed, 9 skipped in 175.01s` |
| Public projection | `.dadaia/.venv/bin/dadaia public stage && ... public install --target all && ... public doctor` | Claude settings, all four Codex wrappers, PI extension, privacy, model resolution, AI surface, and workflow policy all `[ok]` |
| Specs and bugs | `.dadaia/.venv/bin/dadaia specs doctor && .dadaia/.venv/bin/dadaia bugs status` | `0 error(s)` and `0 open bug(s)`; four unrelated legacy warnings remain |
| Repository hygiene | forbidden cache/state scan plus `git diff --check` | no repository bytecode/cache/state artifact; diff clean |

Ruff and mypy were not run because the workspace virtual environment does not contain
those executables and Poetry is not installed.

## Drifts

### Second Claude command builder

**Description:** The initial root-cause pass found the public runtime-config builder, but
the focused integration test exposed a second ctx-inject command builder in
`WorkspaceService` that could append a non-`-B` registration.

**Resolution:** The second builder now emits `-B`, and reinitialization recognizes and
replaces prior Python ctx-inject commands that omit it. The temp-workspace integration
fixture now provisions an executable test interpreter before absolute commands render.

**Memory updates:** none. Existing memory already requires repository-clean projected
hooks; this hotfix brings implementation back into compliance.

## Memory updates

- `specs/memory/product/distribution/public-asset-distribution.md`: no change; already
  declares repository-clean projections.
- `specs/memory/product/harness/harness-claude-code.md`: no change; launch detail remains
  an implementation concern under the existing clean-runtime contract.
- `specs/memory/product/harness/harness-codex.md`: no change for the same reason.
- `specs/memory/product/harness/harness-pi.md`: no change for the same reason.

## Dispositions

| File | Kind | Terminal status | Evidence |
|---|---|---|---|
| `specs/bugs/bugs.jsonl#hook-runtimes-create-repo-bytecode` | bug | `resolved` | v0.2.4 resolved event and validations above |

## Backlog returns

None.

## Archive decision

**MOVE** - move the release directory to `specs/_archive/releases/v0.2.4/` and reset
`specs/releases/ACTIVE.md` to `release: none` / `phase: none`.
