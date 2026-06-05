"""Preflight check definitions and runner.

Pure orchestration: the check list lives here (single source of truth), and the
runner is injectable so tests can exercise pass/fail aggregation without spawning
real subprocesses.
"""

from __future__ import annotations

import subprocess
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

# Ordered cheapest → most expensive so fail-fast surfaces quick problems first.
_LINT_TYPE_CHECKS: tuple[Check, ...] = (
    Check("ruff format --check", ("poetry", "run", "ruff", "format", "--check", *_RUFF_PATHS)),
    Check("ruff check", ("poetry", "run", "ruff", "check", *_RUFF_PATHS)),
    Check("mypy --strict", ("poetry", "run", "mypy", "--strict", *_MYPY_PATHS)),
)

_PYTEST_FULL: Check = Check("pytest", ("poetry", "run", "pytest", "-q", "-p", "no:cacheprovider"))
_PYTEST_QUICK: Check = Check(
    "pytest (no e2e)",
    ("poetry", "run", "pytest", "-q", "-p", "no:cacheprovider", "--ignore=tests/e2e"),
)


def checks_for(quick: bool = False) -> tuple[Check, ...]:
    """Return the ordered check list. ``quick`` drops the slow e2e suite."""
    pytest_check = _PYTEST_QUICK if quick else _PYTEST_FULL
    return (*_LINT_TYPE_CHECKS, pytest_check)


def subprocess_runner(cwd: Path) -> Runner:
    """Build a runner that executes each check as a subprocess under ``cwd``."""

    def _run(argv: Sequence[str]) -> tuple[int, str]:
        proc = subprocess.run(  # noqa: S603 — argv is a fixed, trusted check list
            list(argv),
            cwd=cwd,
            capture_output=True,
            text=True,
        )
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")

    return _run


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
