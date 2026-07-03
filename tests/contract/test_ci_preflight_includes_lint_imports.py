"""Preflight-wiring contract: `dadaia ci preflight` enforces the import-linter contracts (FR4).

The pre-push hook runs `dadaia ci preflight`, so adding the import-linter contracts to
`checks_for()` makes every push enforce the setup.cfg import boundaries alongside
ruff/mypy/pytest. This contract pins two invariants:

  (a) `checks_for()` contains a `lint-imports` check whose argv is EXACTLY the CI
      'Lint (ruff)' job invocation — `lint-imports --config setup.cfg --no-cache` —
      placed with the other lint checks, immediately before the slow pytest step.
  (b) FAIL-CLOSED (architect A10): when `lint-imports` cannot be resolved from the
      runner-derived tree, the check is NOT silently skipped — it surfaces an actionable
      error naming the missing binary AND the poetry group that provides it.

Both are asserted at unit level by DI-faking tool resolution (`python_executable` /
`dadaia_bin`), the established ci_preflight fake pattern — no subprocess is spawned.

AC-7(d) mutation-sanity: deleting the `lint-imports` Check from `checks_for()` makes the
(a) assertion below FAIL (the check disappears from the returned tuple).
"""

from __future__ import annotations

import stat
from pathlib import Path

import pytest

from dadaia_workspace.features.ci_preflight import checks_for

pytestmark = pytest.mark.contract


def _make_exe(directory: Path, name: str) -> Path:
    """Create a stub executable file (the established ci_preflight fake pattern)."""
    directory.mkdir(parents=True, exist_ok=True)
    exe = directory / name
    exe.write_text("#!/bin/sh\n")
    exe.chmod(exe.stat().st_mode | stat.S_IXUSR)
    return exe


def test_checks_for_includes_lint_imports_with_exact_ci_argv(tmp_path: Path) -> None:
    """(a) The preflight tuple carries a `lint-imports` check equal to the CI job argv."""
    venv_bin = tmp_path / "venv" / "bin"
    python = _make_exe(venv_bin, "python")
    lint_imports = _make_exe(venv_bin, "lint-imports")

    for quick in (False, True):
        checks = checks_for(quick=quick, python_executable=str(python), dadaia_bin=None)
        names = [c.name for c in checks]

        # Present — never a silent skip.
        assert "lint-imports" in names, names

        # Exact CI invocation: `lint-imports --config setup.cfg --no-cache`.
        by_name = {c.name: c.argv for c in checks}
        assert by_name["lint-imports"] == (
            str(lint_imports),
            "--config",
            "setup.cfg",
            "--no-cache",
        ), by_name["lint-imports"]

        # Placement: with the other lint checks, immediately before the slow pytest step.
        assert names[-2] == "lint-imports", names
        assert names[-1].startswith("pytest"), names


def test_lint_imports_check_fails_closed_when_binary_absent(tmp_path: Path) -> None:
    """(b) Absent `lint-imports` → an actionable fail-closed check, not a silent skip."""
    # Fake venv with python but NO lint-imports sibling; DADAIA_BIN-derived tree unset.
    venv_bin = tmp_path / "venv" / "bin"
    python = _make_exe(venv_bin, "python")

    checks = checks_for(python_executable=str(python), dadaia_bin=None)
    by_name = {c.name: c.argv for c in checks}

    # The check still exists — absence of the binary is NOT a silent skip.
    assert "lint-imports" in by_name, [c.name for c in checks]
    argv = by_name["lint-imports"]

    # Fail-closed: it resolves to a runnable error command (the interpreter), never to the
    # absent lint-imports binary and never to a bare `poetry run` fallback.
    assert argv[0] != "poetry", argv
    assert not argv[0].endswith("lint-imports"), argv
    assert Path(argv[0]).name.startswith("python"), argv

    # The command surfaces an actionable error naming the binary AND the poetry group,
    # and it is a hard non-zero failure (never a no-op).
    joined = " ".join(argv)
    assert "lint-imports" in joined, joined
    assert "poetry install --with dev" in joined, joined
    assert "SystemExit(1)" in joined, joined
