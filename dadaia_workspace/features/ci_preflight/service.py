"""Preflight check definitions and runner.

Pure orchestration: the check list lives here (single source of truth), and the
runner is injectable so tests can exercise pass/fail aggregation without spawning
real subprocesses.

The ``subprocess_runner`` factory — which contains the only subprocess call for
this feature — lives in ``dadaia_workspace.infrastructure.subprocess_runner`` and
is re-exported here for backwards compatibility.
"""

from __future__ import annotations

import tempfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

# A runner executes an argv and returns (exit_code, combined_output).
Runner = Callable[[Sequence[str]], "tuple[int, str]"]


@dataclass(frozen=True)
class Check:
    """One CI-equivalent check: a human name and the argv to run."""

    name: str
    argv: tuple[str, ...]


@dataclass(frozen=True)
class CheckResult:
    """Outcome of running a single check."""

    name: str
    passed: bool
    exit_code: int
    output: str


# Paths the lint/type checks target, matching .github/workflows/ci.yml.
_RUFF_PATHS: tuple[str, ...] = ("dadaia_workspace/", "tests/")
_MYPY_PATHS: tuple[str, ...] = ("dadaia_workspace/",)


def resolve_mypy_cache_dir(start: Path | None = None) -> Path:
    """Resolve a writable mypy cache dir OUTSIDE any repo working tree.

    Self-pollution fix (T-010-25 / bug ``ci-preflight-self-pollution-…``): mypy
    creates ``.mypy_cache/`` even with ``incremental = false``. Redirecting it
    away from the repo root stops the preflight gate from creating the pollution
    that its own final pytest check rejects.

    Resolution walks up from ``start`` (default: this module's location) looking
    for a workspace root — a directory containing a ``.dadaia/`` folder — and
    targets ``<ws>/.dadaia/tmp/ci-preflight/mypy-cache``. When no workspace is
    found (e.g. the package is installed standalone), it falls back to a path
    under the system temp dir, which is always outside any repo.
    """
    here = (start or Path(__file__)).resolve()
    for parent in (here, *here.parents):
        candidate = parent / ".dadaia"
        if candidate.is_dir():
            return candidate / "tmp" / "ci-preflight" / "mypy-cache"
    # No workspace above ``start`` — fall back to a stable system-tmp location.
    return Path(tempfile.gettempdir()) / "dadaia-ci-preflight" / "mypy-cache"


def _lint_type_checks() -> tuple[Check, ...]:
    """Build the lint/type checks with cache redirection baked into the argv.

    Ruff runs with ``--no-cache`` (no ``.ruff_cache/`` at root); mypy gets an
    explicit ``--cache-dir`` outside the repo (no ``.mypy_cache/`` at root).
    Ordered cheapest → most expensive so fail-fast surfaces quick problems first.
    """
    mypy_cache = resolve_mypy_cache_dir()
    return (
        Check(
            "ruff format --check",
            ("poetry", "run", "ruff", "format", "--check", "--no-cache", *_RUFF_PATHS),
        ),
        Check("ruff check", ("poetry", "run", "ruff", "check", "--no-cache", *_RUFF_PATHS)),
        Check(
            "mypy --strict",
            ("poetry", "run", "mypy", "--strict", "--cache-dir", str(mypy_cache), *_MYPY_PATHS),
        ),
    )


_PYTEST_FULL: Check = Check("pytest", ("poetry", "run", "pytest", "-q", "-p", "no:cacheprovider"))
_PYTEST_QUICK: Check = Check(
    "pytest (no e2e)",
    ("poetry", "run", "pytest", "-q", "-p", "no:cacheprovider", "--ignore=tests/e2e"),
)


def checks_for(quick: bool = False) -> tuple[Check, ...]:
    """Return the ordered check list. ``quick`` drops the slow e2e suite."""
    pytest_check = _PYTEST_QUICK if quick else _PYTEST_FULL
    return (*_lint_type_checks(), pytest_check)


def subprocess_runner(cwd: Path) -> Runner:
    """Build a runner that executes each check as a subprocess under ``cwd``.

    Delegates to ``dadaia_workspace.infrastructure.subprocess_runner.subprocess_runner_for_ci``
    so that this module never imports ``subprocess`` directly.
    """
    from dadaia_workspace.infrastructure.subprocess_runner import subprocess_runner_for_ci

    return subprocess_runner_for_ci(cwd)


def run_preflight(
    checks: Sequence[Check],
    runner: Runner,
    fail_fast: bool = True,
) -> list[CheckResult]:
    """Run each check via ``runner``.

    With ``fail_fast`` (default) the first failure stops the run — a pre-push
    gate only needs to know that *something* is broken, and stopping early keeps
    feedback fast. Set ``fail_fast=False`` to run every check and report all.
    """
    results: list[CheckResult] = []
    for check in checks:
        exit_code, output = runner(check.argv)
        passed = exit_code == 0
        results.append(
            CheckResult(name=check.name, passed=passed, exit_code=exit_code, output=output)
        )
        if not passed and fail_fast:
            break
    return results


def all_passed(results: Sequence[CheckResult]) -> bool:
    """True iff at least one check ran and none failed."""
    return len(results) > 0 and all(r.passed for r in results)


def failed_names(results: Sequence[CheckResult]) -> list[str]:
    """Names of checks that failed, in run order."""
    return [r.name for r in results if not r.passed]
