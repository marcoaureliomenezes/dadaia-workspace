# repos/dadaia-workspace — the library source tree

Hand-authored, repo-scoped. Not a projection: nothing here is regenerated.

- This repo is the **library** that scaffolds dadaia-workspace instances; the tree
  around it (`../../.dadaia/`, `../../.claude/`, root `AGENTS.md`) is the
  **instance**, projected from `dadaia_workspace/public/`.
- The always-on law is the workspace's root map, two levels up: read `../../AGENTS.md`.
- Change law or any AI-entity file at its source under `dadaia_workspace/public/`,
  then re-project from the workspace root with `.dadaia/.venv/bin/dadaia` (Windows
  `.dadaia/.venv/Scripts/dadaia.exe`): `public stage`, `public install`, `public doctor`.
- A library change is unfinished until the instance reflects it; never hand-edit a
  projected instance file to fake the result.
- Any failure of a workspace operation here is a product bug of this library:
  register it in `specs/bugs/`.

Gates, declared once and run by `worktree.py` as argv (never a shell) from the worktree root, the
workspace venv first on `PATH`:

verify: python scripts/ci.py job
verify-stage: python scripts/ci.py stage
verify-task: python scripts/ci.py task
tests: tests/**
tests-red: ^\s*@pytest\.mark\.xfail\(strict=True

- The RED marker's pytest form: one decorator line `@pytest.mark.xfail(strict=True, reason="...")`, its `reason` short enough to stay on one line after ruff format at 100 columns; never `marks=` inside `pytest.param`, never a module constant — a parametrized RED row becomes its own decorated function. `tests/fixtures/red_marker.py` makes every strict xfail expect `AssertionError`, so a RED test that errors cannot close its stage.
- The developer's pipeline — `.github/`, `scripts/ci.py`, `scripts/guards/`, `tests/`, Dependabot/SAST, mutation and test-audit — is private to this repository and never ships. What ships (`dadaia_workspace/public/**`, the projected law, the skill scripts) requires of a user's repo only its own `verify:`/`tests:` lines and local git: never a remote, CI, `gh`, a PR host or a language toolchain. `test_public_source_hygiene.py`'s `public-law-names-no-private-pipeline` row is the mechanical half.

- Versioning here: release-please owns the version, tag and CHANGELOG; the work branch
  is named for the live release (`_RELEASE.json`).
- Dev tools (pytest, ruff, mypy, lint-imports) come from the `dev` group, installed into
  the workspace venv from this repo's root: `VIRTUAL_ENV=../../.dadaia/.venv poetry install --no-root --with dev`.
