"""Preflight check definitions and runner.

Pure orchestration: the check list lives here (single source of truth), and the
runner is injectable so tests can exercise pass/fail aggregation without spawning
real subprocesses.

The ``subprocess_runner`` factory — which contains the only subprocess call for
this feature — lives in ``dadaia_workspace.infrastructure.subprocess_runner`` and
is re-exported here for backwards compatibility.
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

# ``shutil`` is imported so the no-PATH-probing contract is testable (a test
# monkeypatches ``shutil.which`` and asserts it is never called). Resolution
# itself MUST NOT consult the ambient PATH — see ``_resolve_tool``.
_ = shutil

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


def _is_executable_file(path: Path) -> bool:
    """True iff ``path`` is an existing regular file with the executable bit.

    A directory whose name matches a tool (e.g. a ``ruff/`` package dir) must
    never satisfy resolution — only a real executable file does.
    """
    try:
        return path.is_file() and os.access(path, os.X_OK)
    except OSError:
        return False


def _resolve_tool(
    name: str,
    *,
    python_executable: str | None = None,
    dadaia_bin: str | None = None,
) -> tuple[str, ...]:
    """Resolve the argv prefix that invokes tool ``name`` (bug B2 fix).

    Pinned resolution order — **no** ``shutil.which`` / ambient-PATH probing:

    1. **venv sibling of the interpreter** — ``Path(sys.executable).parent / name``.
       The runner that imports this module is the resolved venv's python, so its
       sibling tools are exactly the ones CI would use.
    2. **DADAIA_BIN-derived bin dir** — ``Path(DADAIA_BIN).parent / name``. The
       pre-push hook exports ``DADAIA_BIN`` pointing at the resolved ``dadaia``
       executable; its sibling tools share the same environment.
    3. **poetry fallback** — ``("poetry", "run", name)``. Used only when the tool
       is absent from both trees; the runner then fails closed at execution time
       (127 + "command not found") if poetry too is missing.

    ``python_executable`` / ``dadaia_bin`` are injectable for testing; in
    production they default to ``sys.executable`` and ``os.environ["DADAIA_BIN"]``.
    """
    # NOTE: the interpreter/dadaia paths must NOT be ``resolve()``d before taking
    # ``parent`` — a venv's ``bin/python`` is a symlink to the base interpreter
    # (e.g. ``/usr/bin/python3.12``), and following it would escape the venv and
    # look for siblings in the system bin dir. Tool siblings live next to the
    # symlink itself.
    py = python_executable if python_executable is not None else sys.executable
    venv_sibling = Path(os.path.abspath(py)).parent / name
    if _is_executable_file(venv_sibling):
        return (str(venv_sibling),)

    bin_ptr = dadaia_bin if dadaia_bin is not None else os.environ.get("DADAIA_BIN")
    if bin_ptr:
        dadaia_sibling = Path(os.path.abspath(bin_ptr)).parent / name
        if _is_executable_file(dadaia_sibling):
            return (str(dadaia_sibling),)

    return ("poetry", "run", name)


def _lint_type_checks(
    *,
    python_executable: str | None = None,
    dadaia_bin: str | None = None,
) -> tuple[Check, ...]:
    """Build the lint/type checks with cache redirection baked into the argv.

    Ruff runs with ``--no-cache`` (no ``.ruff_cache/`` at root); mypy gets an
    explicit ``--cache-dir`` outside the repo (no ``.mypy_cache/`` at root).
    Ordered cheapest → most expensive so fail-fast surfaces quick problems first.
    Each tool prefix is resolved via ``_resolve_tool`` (runner-derived, not
    ``poetry``-hardcoded — bug B2).
    """
    mypy_cache = resolve_mypy_cache_dir()
    ruff = _resolve_tool("ruff", python_executable=python_executable, dadaia_bin=dadaia_bin)
    mypy = _resolve_tool("mypy", python_executable=python_executable, dadaia_bin=dadaia_bin)
    return (
        Check(
            "ruff format --check",
            (*ruff, "format", "--check", "--no-cache", *_RUFF_PATHS),
        ),
        Check("ruff check", (*ruff, "check", "--no-cache", *_RUFF_PATHS)),
        Check(
            "mypy --strict",
            (*mypy, "--strict", "--cache-dir", str(mypy_cache), *_MYPY_PATHS),
        ),
    )


def _pytest_check(
    quick: bool,
    *,
    python_executable: str | None = None,
    dadaia_bin: str | None = None,
) -> Check:
    """Build the pytest check, resolving the pytest executable via ``_resolve_tool``.

    W1-5 de-flake: ``tests/performance`` is excluded from BOTH quick and full preflight runs.
    Those tests assert on wall-clock budgets (e.g. a 90s ceiling) and fail under machine load,
    turning the pre-push gate into a load-dependent flake
    (bug ``prepush-gate-blocked-by-loadsensitive-perf-test-wallclock-bound``). Performance
    tests remain runnable directly and in any perf-specific CI selection.
    """
    pytest = _resolve_tool("pytest", python_executable=python_executable, dadaia_bin=dadaia_bin)
    base = (*pytest, "-q", "-p", "no:cacheprovider", "--ignore=tests/performance")
    if quick:
        return Check("pytest (no e2e)", (*base, "--ignore=tests/e2e"))
    return Check("pytest", base)


def checks_for(
    quick: bool = False,
    *,
    python_executable: str | None = None,
    dadaia_bin: str | None = None,
) -> tuple[Check, ...]:
    """Return the ordered check list. ``quick`` drops the slow e2e suite.

    ``python_executable`` / ``dadaia_bin`` are injectable for testing; in
    production they default to ``sys.executable`` / ``DADAIA_BIN`` via
    ``_resolve_tool``.
    """
    lint = _lint_type_checks(python_executable=python_executable, dadaia_bin=dadaia_bin)
    pytest_check = _pytest_check(quick, python_executable=python_executable, dadaia_bin=dadaia_bin)
    return (*lint, pytest_check)


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
