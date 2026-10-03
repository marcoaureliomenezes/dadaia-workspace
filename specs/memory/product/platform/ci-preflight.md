---
slug: ci-preflight
title: ci-preflight
tldr: "dadaia ci preflight runs the library's seven CI checks locally, fenced like a bare checkout, and refuses outside the source repo."
summary: "The local CI-equivalent run a contributor makes before every push of the dadaia-workspace source repo: seven ordered checks resolved from the running venv, run in a fenced bare checkout as CI runs them, fail-fast by default, exit 1 with each failing check's output tail; any other repo is refused with a message pointing at its own CI."
tags: [ci, preflight, lint, typecheck, tests]
sources:
  - dadaia_workspace/features/ci_preflight/**
  - dadaia_workspace/cli/commands/ci.py
  - dadaia_workspace/infrastructure/subprocess_runner.py
---

## Behavior

- `dadaia ci preflight [--quick] [--fail-fast/--no-fail-fast]` runs the library's locally runnable `ci.yml` checks, cheapest first: `ruff format --check`, `ruff check` (over `dadaia_workspace/` and `tests/`), `mypy --strict` (over `dadaia_workspace/`), repo hygiene (`.github/scripts/check_no_repo_local_claude.sh`), `dadaia doctor --specs-dir specs --source-root .`, `lint-imports --config setup.cfg --no-cache` (the import-boundary contracts), then `pytest -q -p no:cacheprovider -m "not quarantine" -n auto` with the 80% coverage floor.
- `--quick` skips `tests/e2e`; fail-fast (the default) stops at the first failing check, `--no-fail-fast` runs all.
- Each check prints `[PASS]` or `[FAIL]`; a failed run exits 1, naming the failed checks and printing the last lines of each failing check's output.
- Tools resolve beside the running interpreter, never from the ambient `PATH`; an absent `ruff`, `mypy` or `pytest` falls back to `poetry run`, and an absent `lint-imports` fails closed with the install command.
- Cache redirection is the repo's own configuration, so preflight runs exactly what a contributor types by hand.
- Every check runs as CI does, in a bare checkout: each root above the checkout is fenced (`DADAIA_FENCED_ROOTS`), so the doctor judges only the repo's `specs` and ledgers, never the enclosing workspace.

## Boundaries

- It runs only at the dadaia-workspace source repo root; anywhere else it exits with a scope error telling the operator to run that repo's own CI.
- The pre-push hook neither runs nor names it: the push boundary is branch policy, the specs canon, law-line deletions and the denylist scan ([[sdd-gate-v3]]); preflight is this repo's discipline before every push, and CI runs the same checks on every push.

## Dependencies

[[sdd-gate-v3]], [[pypi-distribution]], [[QUALITY]].
