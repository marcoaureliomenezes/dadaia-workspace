"""E2E: ci-preflight resolves and runs tool argv with poetry OFF the PATH.

Named regression for bug ``ci-preflight-checks-hardcode-poetry-run`` (T-011-06,
AC-W2-01). Before the fix every check argv was hardcoded to ``("poetry", "run",
...)`` so a push from a host without poetry on PATH died with
``command not found: poetry`` even though all tools existed in the resolved venv.

This exercises the REAL ``run_preflight`` + ``subprocess_runner`` against a FAKE
venv tree of stub executables, in a subprocess environment whose PATH is wiped of
poetry. There is no pytest-inside-pytest — the stub "pytest" is a trivial shell
script that exits 0. The real-tree run is final-gate item 7 (T-011-20).
"""

from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from dadaia_workspace.features.ci_preflight import (
    all_passed,
    checks_for,
    run_preflight,
    subprocess_runner,
)

pytestmark = pytest.mark.skipif(os.name != "posix", reason="stub executables use a POSIX shebang")


def _stub_exe(directory: Path, name: str, *, exit_code: int = 0) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    exe = directory / name
    exe.write_text(f"#!/bin/sh\nexit {exit_code}\n")
    exe.chmod(exe.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return exe


def _fake_venv(tmp_path: Path, exit_code: int = 0) -> Path:
    """Build a fake venv bin dir with python + ruff/mypy/pytest/lint-imports stubs."""
    venv_bin = tmp_path / "fakevenv" / "bin"
    _stub_exe(venv_bin, "python")
    # lint-imports (FR4) resolves through the same venv-sibling seam as the other tools.
    for tool in ("ruff", "mypy", "pytest", "lint-imports"):
        _stub_exe(venv_bin, tool, exit_code=exit_code)
    return venv_bin


@pytest.mark.parametrize("stub_exit_code", [0, 1], ids=["pass", "failure-report"])
def test_preflight_resolved_tool_pass_and_failure_report_with_poetry_off_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stub_exit_code: int
) -> None:
    """With poetry wiped off PATH: a passing stub venv resolves every tool to an
    ABSOLUTE fake-venv sibling path with zero poetry references and all checks pass;
    a failing stub venv reports the first resolved tool's non-zero exit as a failed
    check (fail-fast stops there) — no poetry fallback in either case."""
    venv_bin = _fake_venv(tmp_path, exit_code=stub_exit_code)
    monkeypatch.setenv("PATH", "")
    monkeypatch.delenv("DADAIA_BIN", raising=False)

    checks = checks_for(
        quick=True,
        python_executable=str(venv_bin / "python"),
        dadaia_bin=None,
    )

    if stub_exit_code == 0:
        # No argv references poetry — every tool resolved to the fake-venv sibling.
        for c in checks:
            assert "poetry" not in c.argv, f"{c.name}: {c.argv}"
            assert c.argv[0].startswith(str(venv_bin)), f"{c.name}: {c.argv}"

        results = run_preflight(checks, subprocess_runner(tmp_path), fail_fast=True)

        assert all_passed(results), [
            (r.name, r.exit_code, r.output) for r in results if not r.passed
        ]
        assert len(results) == len(checks)
    else:
        results = run_preflight(checks, subprocess_runner(tmp_path), fail_fast=True)

        assert not all_passed(results)
        # First check (ruff format --check) fails → fail-fast stops there.
        assert results[0].passed is False
        assert results[0].exit_code == 1


def test_missing_tool_everywhere_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Tool absent from venv AND DADAIA_BIN AND PATH → poetry fallback fails closed (127).

    Preserves the v0.1.10 fail-closed contract: no traceback, a clean
    'command not found' message, exit 127.
    """
    venv_bin = tmp_path / "barevenv" / "bin"
    _stub_exe(venv_bin, "python")  # python only; no ruff/mypy/pytest siblings
    monkeypatch.setenv("PATH", "")  # poetry not reachable either
    monkeypatch.delenv("DADAIA_BIN", raising=False)

    checks = checks_for(
        quick=True,
        python_executable=str(venv_bin / "python"),
        dadaia_bin=None,
    )
    # ruff/mypy/pytest fall back to ("poetry", "run", ...) since no sibling exists.
    # lint-imports (FR4) is a REQUIRED tool: instead of a poetry fallback it FAILS CLOSED
    # to an actionable command naming the missing binary + poetry group (architect A10).
    non_required = [c for c in checks if c.name != "lint-imports"]
    assert all(c.argv[0] == "poetry" for c in non_required), [c.argv for c in checks]
    lint_imports = next(c for c in checks if c.name == "lint-imports")
    assert lint_imports.argv[0] != "poetry", lint_imports.argv
    assert "poetry install --with dev" in " ".join(lint_imports.argv), lint_imports.argv

    results = run_preflight(checks, subprocess_runner(tmp_path), fail_fast=True)
    assert not all_passed(results)
    # fail-fast stops at the first check (ruff format --check → poetry fallback → 127).
    assert results[0].exit_code == 127
    assert "command not found" in results[0].output
