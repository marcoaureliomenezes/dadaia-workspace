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

# The import-linter (``lint-imports``) config lives in setup.cfg. ``--no-cache`` keeps
# ``.import_linter_cache/`` out of the repo tree (repo-cleanliness law; see
# ``tests/contract/test_import_linter_cache_hygiene.py``). This mirrors the CI
# 'Lint (ruff)' job step ``lint-imports --config setup.cfg --no-cache``.
_LINT_IMPORTS_CONFIG: str = "setup.cfg"

# Actionable hints for REQUIRED tools that must FAIL CLOSED when absent (architect A10 /
# FR4). A missing required tool is a hard error naming the binary AND the poetry group
# that provides it — never a silent skip nor a cryptic ``poetry run`` command-not-found.
_REQUIRED_TOOL_HINT: dict[str, str] = {
    "lint-imports": (
        "lint-imports (import-linter) is not installed in the resolved environment. "
        "It enforces the import-boundary contracts (setup.cfg) in the CI 'Lint (ruff)' "
        "job and in `dadaia ci preflight`. Install it with: poetry install --with dev"
    ),
}


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


def _fail_closed_argv(python_executable: str, hint: str) -> tuple[str, ...]:
    """Build a self-contained argv that fails closed with an actionable message.

    A REQUIRED tool (``_resolve_tool(..., require=True)``) that is absent from every
    resolved tree must NOT degrade to a ``("poetry", "run", name)`` fallback — that
    emits a cryptic ``command not found`` and reads like an optional skip. Instead we
    return a runnable command (the resolved interpreter + ``-c``) that writes ``hint``
    to stderr and exits non-zero, so the preflight/CI check surfaces the missing binary
    and the poetry group that provides it. Architect A10 / FR4 fail-closed posture.
    """
    return (
        os.path.abspath(python_executable),
        "-c",
        f"import sys; sys.stderr.write({hint!r} + chr(10)); raise SystemExit(1)",
    )


def _resolve_tool(
    name: str,
    *,
    python_executable: str | None = None,
    dadaia_bin: str | None = None,
    require: bool = False,
) -> tuple[str, ...]:
    """Resolve the argv prefix that invokes tool ``name`` (bug B2 fix).

    Pinned resolution order — **no** ``shutil.which`` / ambient-PATH probing:

    1. **venv sibling of the interpreter** — ``Path(sys.executable).parent / name``.
       The runner that imports this module is the resolved venv's python, so its
       sibling tools are exactly the ones CI would use.
    2. **DADAIA_BIN-derived bin dir** — ``Path(DADAIA_BIN).parent / name``. The
       pre-push hook exports ``DADAIA_BIN`` pointing at the resolved ``dadaia``
       executable; its sibling tools share the same environment.
    3. **absent from both trees** — depends on ``require``:
       - ``require=False`` (default, ruff/mypy/pytest): **poetry fallback**
         ``("poetry", "run", name)``; the runner then fails closed at execution time
         (127 + "command not found") if poetry too is missing.
       - ``require=True`` (lint-imports / FR4): **fail closed** via
         :func:`_fail_closed_argv` — a hard, actionable error naming the missing
         binary and the poetry group (architect A10), never a silent skip.

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

    if require:
        hint = _REQUIRED_TOOL_HINT.get(
            name,
            f"{name} is not installed in the resolved environment. "
            "Install it with: poetry install --with dev",
        )
        return _fail_closed_argv(py, hint)

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


def _lint_imports_check(
    *,
    python_executable: str | None = None,
    dadaia_bin: str | None = None,
) -> Check:
    """Build the import-linter check enforcing the setup.cfg import-boundary contracts (FR4).

    Mirrors the CI 'Lint (ruff)' job step ``lint-imports --config setup.cfg --no-cache``:
    ``--config setup.cfg`` selects the contract set; ``--no-cache`` keeps
    ``.import_linter_cache/`` out of the repo tree (repo-cleanliness law;
    ``test_import_linter_cache_hygiene.py``). The executable is resolved via the shared
    ``_resolve_tool`` seam with ``require=True`` — a missing ``lint-imports`` binary FAILS
    CLOSED with an actionable message (architect A10), never a silent skip. When the tool
    is absent, ``_resolve_tool`` returns the self-contained fail-closed command (len > 1),
    so the contract flags are appended ONLY to a truly-resolved single-element prefix.
    """
    prefix = _resolve_tool(
        "lint-imports",
        python_executable=python_executable,
        dadaia_bin=dadaia_bin,
        require=True,
    )
    if len(prefix) == 1:
        return Check("lint-imports", (*prefix, "--config", _LINT_IMPORTS_CONFIG, "--no-cache"))
    # Fail-closed: ``prefix`` is already the actionable-error command (architect A10).
    return Check("lint-imports", prefix)


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

    v0.1.75 FR3 (speed wiring): ``-n auto`` runs the suite under ``pytest-xdist``,
    parallelizing across CPU cores. Randomization (``pytest-randomly``, always active)
    stays safe under xdist because each worker gets its own randomized order seeded
    from the same run seed — no test may depend on execution order or on running
    in-process with any other test (workspace isolation is enforced by ``conftest.py``
    fixtures, never shared global state).
    """
    pytest = _resolve_tool("pytest", python_executable=python_executable, dadaia_bin=dadaia_bin)
    # v0.7.0 FR5: the dead tests/performance ignore is retired (the directory no longer
    # exists) and every gating invocation excludes the quarantine lane — a quarantined
    # test runs only under an explicit `-m quarantine` diagnosis session, never in a gate.
    base = (*pytest, "-q", "-p", "no:cacheprovider", "-m", "not quarantine", "-n", "auto")
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
    lint_imports = _lint_imports_check(python_executable=python_executable, dadaia_bin=dadaia_bin)
    pytest_check = _pytest_check(quick, python_executable=python_executable, dadaia_bin=dadaia_bin)
    # Import-boundary contracts run with the other lint checks, before the slow pytest step.
    return (*lint, lint_imports, pytest_check)


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
