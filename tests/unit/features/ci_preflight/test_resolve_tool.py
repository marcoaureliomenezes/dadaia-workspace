"""Unit tests for runner-derived tool argv resolution (T-011-06, bug B2).

`_resolve_tool` must build each check's tool prefix from the *resolved runner
environment* — never from the ambient PATH (no ``shutil.which``):

    1. venv sibling of ``sys.executable``  (``Path(sys.executable).parent / name``)
    2. ``DADAIA_BIN``-derived bin dir       (``Path(DADAIA_BIN).parent / name``)
    3. ``("poetry", "run", name)`` fallback ONLY when no sibling exists anywhere.

The pinned order and the fail-soft poetry fallback are the bug fix: on a host
where poetry is absent from PATH the venv sibling resolves first, so the gate no
longer dies with ``command not found: poetry``.
"""

from __future__ import annotations

import stat
from pathlib import Path

from dadaia_workspace.features.ci_preflight.service import (
    _resolve_tool,
    checks_for,
)


def _make_exe(directory: Path, name: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    exe = directory / name
    exe.write_text("#!/bin/sh\n")
    exe.chmod(exe.stat().st_mode | stat.S_IXUSR)
    return exe


def test_resolve_tool_prefers_venv_sibling_of_python(tmp_path: Path) -> None:
    """A tool that sits beside the interpreter wins over every other source."""
    venv_bin = tmp_path / "venv" / "bin"
    python = _make_exe(venv_bin, "python")
    ruff = _make_exe(venv_bin, "ruff")

    # DADAIA_BIN also has a ruff, but the venv sibling must win.
    dadaia_bin = tmp_path / "dadaia" / "bin"
    _make_exe(dadaia_bin, "ruff")
    _make_exe(dadaia_bin, "dadaia")

    argv = _resolve_tool(
        "ruff",
        python_executable=str(python),
        dadaia_bin=str(dadaia_bin / "dadaia"),
    )
    assert argv == (str(ruff),)


def test_resolve_tool_sibling_of_python_symlink_not_its_target(tmp_path: Path) -> None:
    """Venv-symlink regression (live-gate defect): ``bin/python`` is a symlink to
    the base interpreter; resolution must look for siblings next to the SYMLINK,
    never next to its target (which would escape the venv into the system bin)."""
    base_bin = tmp_path / "usr" / "bin"
    base_python = _make_exe(base_bin, "python3.12")  # no ruff here

    venv_bin = tmp_path / "venv" / "bin"
    venv_bin.mkdir(parents=True)
    python_link = venv_bin / "python"
    python_link.symlink_to(base_python)
    ruff = _make_exe(venv_bin, "ruff")

    argv = _resolve_tool("ruff", python_executable=str(python_link), dadaia_bin=None)
    assert argv == (str(ruff),)


def test_resolve_tool_falls_back_to_dadaia_bin_when_no_venv_sibling(tmp_path: Path) -> None:
    """No sibling beside python → resolve from the DADAIA_BIN-derived bin dir."""
    venv_bin = tmp_path / "venv" / "bin"
    python = _make_exe(venv_bin, "python")  # python only; no mypy beside it

    dadaia_bin_dir = tmp_path / "dadaia" / "bin"
    _make_exe(dadaia_bin_dir, "dadaia")
    mypy = _make_exe(dadaia_bin_dir, "mypy")

    argv = _resolve_tool(
        "mypy",
        python_executable=str(python),
        dadaia_bin=str(dadaia_bin_dir / "dadaia"),
    )
    assert argv == (str(mypy),)


def test_resolve_tool_poetry_fallback_when_missing_everywhere(tmp_path: Path) -> None:
    """Tool absent from venv AND DADAIA_BIN → poetry-run fallback (fail-closed at run time)."""
    venv_bin = tmp_path / "venv" / "bin"
    python = _make_exe(venv_bin, "python")
    dadaia_bin_dir = tmp_path / "dadaia" / "bin"
    _make_exe(dadaia_bin_dir, "dadaia")

    argv = _resolve_tool(
        "pytest",
        python_executable=str(python),
        dadaia_bin=str(dadaia_bin_dir / "dadaia"),
    )
    assert argv == ("poetry", "run", "pytest")


def test_resolve_tool_poetry_fallback_when_dadaia_bin_unset(tmp_path: Path) -> None:
    """DADAIA_BIN unset and no venv sibling → poetry fallback (no PATH probing)."""
    venv_bin = tmp_path / "venv" / "bin"
    python = _make_exe(venv_bin, "python")

    argv = _resolve_tool("ruff", python_executable=str(python), dadaia_bin=None)
    assert argv == ("poetry", "run", "ruff")


def test_resolve_tool_never_calls_shutil_which(monkeypatch, tmp_path: Path) -> None:
    """Hard guard: resolution must not consult the ambient PATH via shutil.which."""
    import dadaia_workspace.features.ci_preflight.service as svc

    sentinel_called = False

    def _boom(*_a: object, **_k: object) -> str | None:
        nonlocal sentinel_called
        sentinel_called = True
        return "/usr/bin/ruff"

    monkeypatch.setattr(svc.shutil, "which", _boom, raising=True)

    venv_bin = tmp_path / "venv" / "bin"
    python = _make_exe(venv_bin, "python")
    _resolve_tool("ruff", python_executable=str(python), dadaia_bin=None)

    assert sentinel_called is False


def test_resolve_tool_dir_named_like_tool_is_not_treated_as_executable(tmp_path: Path) -> None:
    """A directory matching the tool name must not satisfy resolution — fall through."""
    venv_bin = tmp_path / "venv" / "bin"
    python = _make_exe(venv_bin, "python")
    (venv_bin / "ruff").mkdir()  # a *directory* named ruff, not an executable file

    argv = _resolve_tool("ruff", python_executable=str(python), dadaia_bin=None)
    assert argv == ("poetry", "run", "ruff")


def test_all_five_checks_built_through_resolve_tool(tmp_path: Path) -> None:
    """Every check argv must start with the resolved-venv prefix, never bare ('poetry').

    With a fully populated venv the five tool prefixes resolve to the sibling
    executables; the bug B2 condition (every argv hardcoded to 'poetry') is gone.
    """
    venv_bin = tmp_path / "venv" / "bin"
    _make_exe(venv_bin, "python")
    ruff = _make_exe(venv_bin, "ruff")
    mypy = _make_exe(venv_bin, "mypy")
    pytest_exe = _make_exe(venv_bin, "pytest")
    python = venv_bin / "python"

    full = checks_for(
        quick=False,
        python_executable=str(python),
        dadaia_bin=None,
    )
    quick = checks_for(
        quick=True,
        python_executable=str(python),
        dadaia_bin=None,
    )

    by_name = {c.name: c.argv for c in full}
    assert by_name["ruff format --check"][0] == str(ruff)
    assert by_name["ruff check"][0] == str(ruff)
    assert by_name["mypy --strict"][0] == str(mypy)
    assert by_name["pytest"][0] == str(pytest_exe)

    quick_by_name = {c.name: c.argv for c in quick}
    assert quick_by_name["pytest (no e2e)"][0] == str(pytest_exe)

    # No check argv begins with the bare 'poetry' literal when tools resolve.
    for c in (*full, *quick):
        assert c.argv[0] != "poetry", c.name


def test_preflight_works_with_poetry_off_path(tmp_path: Path) -> None:
    """Named regression for bug ci-preflight-checks-hardcode-poetry-run.

    The whole point of the bug: with poetry absent, a fully populated venv must
    still yield runnable argv. We build the checks against a fake venv tree (no
    poetry anywhere) and assert NONE of the resolved argv reference poetry.
    """
    venv_bin = tmp_path / "venv" / "bin"
    _make_exe(venv_bin, "python")
    for tool in ("ruff", "mypy", "pytest"):
        _make_exe(venv_bin, tool)
    python = venv_bin / "python"

    checks = checks_for(quick=False, python_executable=str(python), dadaia_bin=None)
    for c in checks:
        assert "poetry" not in c.argv, f"{c.name} still references poetry: {c.argv}"
