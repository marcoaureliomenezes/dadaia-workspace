---
slug: ci-preflight
title: ci-preflight
tldr: "dadaia ci preflight runs the library's CI checks locally — ruff format, ruff check, mypy --strict, lint-imports, pytest — and refuses outside the source repo."
summary: "The local CI-equivalent run a contributor makes before every push of the dadaia-workspace source repo: five ordered checks resolved from the running venv, fail-fast by default, exit 1 with each failing check's output tail; any other repo is refused with a message pointing at its own CI."
tags: [ci, preflight, lint, typecheck, tests]
sources:
  - dadaia_workspace/features/ci_preflight/**
  - dadaia_workspace/cli/commands/ci.py
  - dadaia_workspace/infrastructure/subprocess_runner.py
---

## Behavior

- `dadaia ci preflight [--quick] [--fail-fast/--no-fail-fast]` runs, in order: `ruff format --check`, `ruff check` (over `dadaia_workspace/` and `tests/`), `mypy --strict` (over `dadaia_workspace/`), `lint-imports --config setup.cfg --no-cache` (the import-boundary contracts), then `pytest -q -p no:cacheprovider -m "not quarantine" -n auto`.
- `--quick` skips `tests/e2e`; fail-fast (the default) stops at the first failing check, `--no-fail-fast` runs all.
- Each check prints `[PASS]` or `[FAIL]`; a failed run exits 1, naming the failed checks and printing the last lines of each failing check's output.
- Tools resolve beside the running interpreter, then beside `DADAIA_BIN`, never from the ambient `PATH`; an absent `ruff`, `mypy` or `pytest` falls back to `poetry run`, and an absent `lint-imports` fails closed with the install command.
- Cache redirection is the repo's own configuration, so preflight runs exactly what a contributor types by hand.

## Boundaries

- It runs only at the dadaia-workspace source repo root; anywhere else it exits with a scope error telling the operator to run that repo's own CI.
- The pre-push hook does not run it: the push boundary is branch name plus denylist scan ([[sdd-gate-v3]]); preflight is the discipline before every push, and CI runs the same checks on every push.

## Dependencies

[[sdd-gate-v3]], [[pypi-distribution]], [[QUALITY]].
