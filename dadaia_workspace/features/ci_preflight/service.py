"""Preflight checks (one table, the CI-equivalent set) and an injectable runner."""

from __future__ import annotations

import os
import shutil
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

_ = shutil  # a test patches ``shutil.which`` to prove resolution never probes PATH

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
_PYTEST = ("-q", "-p", "no:cacheprovider", "-m", "not quarantine", "-n", "auto")
_COVERAGE = ("--cov=dadaia_workspace", "--cov-fail-under=80", "--cov-report=")

#: The check table, cheapest first (fail-fast): name, tool (``""``: none), arguments.
#: Caches follow the caller's env (ADR 0080); a gate never runs the quarantine lane.
_TABLE: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("ruff format --check", "ruff", ("format", "--check", *_RUFF_PATHS)),
    ("ruff check", "ruff", ("check", *_RUFF_PATHS)),
    ("mypy --strict", "mypy", ("--strict", *_MYPY_PATHS)),
    ("repo hygiene", "", ("bash", ".github/scripts/check_no_repo_local_claude.sh")),
    ("dadaia doctor", "dadaia", ("doctor", "--specs-dir", "specs", "--source-root", ".")),
    ("lint-imports", "lint-imports", ("--config", "setup.cfg", "--no-cache")),
    ("pytest", "pytest", (*_PYTEST, *_COVERAGE)),
)


def _is_executable_file(path: Path) -> bool:
    """A regular executable file — a same-named directory never resolves a tool."""
    try:
        return path.is_file() and os.access(path, os.X_OK)
    except OSError:
        return False


def _resolve_tool(
    name: str,
    *,
    python_executable: str | None = None,
    dadaia_bin: str | None = None,
    require: bool = False,
) -> tuple[str, ...]:
    """The argv prefix for tool *name*, never from the ambient PATH (bug B2): the sibling
    of the interpreter, else of ``DADAIA_BIN`` (neither ``resolve()``d: a venv python is a
    symlink out of the venv), else ``poetry run`` — or, *require*d, a runnable command
    that fails closed naming the tool and its poetry group (architect A10)."""
    py = python_executable if python_executable is not None else sys.executable
    bin_ptr = dadaia_bin if dadaia_bin is not None else os.environ.get("DADAIA_BIN")
    for anchor in (py, bin_ptr):
        if anchor and _is_executable_file(sibling := Path(os.path.abspath(anchor)).parent / name):
            return (str(sibling),)
    if not require:
        return ("poetry", "run", name)
    hint = f"{name} is not installed in the resolved environment. Install it with: poetry install --with dev"
    code = f"import sys; sys.stderr.write({hint!r} + chr(10)); raise SystemExit(1)"
    return (os.path.abspath(py), "-c", code)


def checks_for(
    quick: bool = False,
    *,
    python_executable: str | None = None,
    dadaia_bin: str | None = None,
) -> tuple[Check, ...]:
    """The ordered checks; ``quick`` drops the e2e suite. A missing ``lint-imports``
    fails closed instead of taking its arguments."""
    checks = []
    for name, tool, args in _TABLE:
        gated = tool == "lint-imports"
        prefix = (
            _resolve_tool(
                tool, python_executable=python_executable, dadaia_bin=dadaia_bin, require=gated
            )
            if tool
            else ()
        )
        if gated and len(prefix) > 1:
            args = ()  # the fail-closed command takes no arguments
        elif tool == "pytest" and quick:
            name, args = "pytest (no e2e)", (*args, "--ignore=tests/e2e")
        checks.append(Check(name, (*prefix, *args)))
    return tuple(checks)


def subprocess_runner(cwd: Path) -> Runner:
    """Run each check under ``cwd`` as CI does, in a bare checkout: every root above
    ``cwd`` is fenced, so no check resolves the workspace enclosing the checkout."""
    from dadaia_workspace.core.workspace_resolver import fenced_env
    from dadaia_workspace.infrastructure.subprocess_runner import subprocess_runner_for_ci

    return subprocess_runner_for_ci(cwd, fenced_env(cwd))


def run_preflight(
    checks: Sequence[Check],
    runner: Runner,
    fail_fast: bool = True,
) -> list[CheckResult]:
    """Run each check via ``runner``; ``fail_fast`` stops at the first failure."""
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
