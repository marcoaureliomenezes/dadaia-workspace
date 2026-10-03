"""Unit tests for runner-derived tool argv resolution (T-011-06, bug B2).

`_resolve_tool` must build each check's tool prefix from the *resolved runner
environment* — never from the ambient PATH (no ``shutil.which``):

    1. venv sibling of ``sys.executable``  (``Path(sys.executable).parent / name``)
    2. ``("poetry", "run", name)`` fallback ONLY when no sibling exists anywhere.

The pinned order and the fail-soft poetry fallback are the bug fix: on a host
where poetry is absent from PATH the venv sibling resolves first, so the gate no
longer dies with ``command not found: poetry``.
"""

from __future__ import annotations

import stat
from pathlib import Path

import pytest

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


# fmt: off
@pytest.mark.parametrize(("venv", "expected"), [
    pytest.param(["ruff"], "venv/bin/ruff", id="venv-sibling-wins"),
    pytest.param([], None, id="poetry-fallback-when-missing"),
    pytest.param(["ruff/"], None, id="dir-named-like-tool-not-executable"),
    pytest.param(["ruff", "python->base"], "venv/bin/ruff", id="sibling-of-a-python-symlink-never-its-target"),
])
# fmt: on
def test_resolve_tool_precedence(tmp_path: Path, venv: list[str], expected: str | None) -> None:
    """Bug B2: venv sibling of sys.executable (next to the SYMLINK, never its target) > poetry."""
    venv_bin = tmp_path / "venv" / "bin"
    if "python->base" in venv:
        venv_bin.mkdir(parents=True)
        (venv_bin / "python").symlink_to(_make_exe(tmp_path / "usr" / "bin", "python3.12"))
    else:
        _make_exe(venv_bin, "python")
    for name in venv:
        if name.endswith("/"):
            (venv_bin / name[:-1]).mkdir()
        elif "->" not in name:
            _make_exe(venv_bin, name)
    argv = _resolve_tool("ruff", python_executable=str(venv_bin / "python"))
    assert argv == ((str(tmp_path / expected),) if expected else ("poetry", "run", "ruff"))


def test_resolve_tool_never_calls_shutil_which_and_wires_all_checks(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Hard guard: resolution must not consult the ambient PATH via shutil.which, AND
    every one of the five checks resolves through it (never hardcoded 'poetry')."""
    import dadaia_workspace.features.ci_preflight.service as svc

    sentinel_called = False

    def _boom(*_a: object, **_k: object) -> str | None:
        nonlocal sentinel_called
        sentinel_called = True
        return "/usr/bin/ruff"

    monkeypatch.setattr(svc.shutil, "which", _boom, raising=True)  # type: ignore[attr-defined]

    venv_bin = tmp_path / "venv" / "bin"
    _make_exe(venv_bin, "python")
    _resolve_tool("ruff", python_executable=str(venv_bin / "python"))
    assert sentinel_called is False

    ruff = _make_exe(venv_bin, "ruff")
    mypy = _make_exe(venv_bin, "mypy")
    pytest_exe = _make_exe(venv_bin, "pytest")
    _make_exe(venv_bin, "dadaia")
    python = venv_bin / "python"

    full = checks_for(quick=False, python_executable=str(python))
    quick = checks_for(quick=True, python_executable=str(python))

    by_name = {c.name: c.argv for c in full}
    assert by_name["ruff format --check"][0] == str(ruff)
    assert by_name["ruff check"][0] == str(ruff)
    assert by_name["mypy --strict"][0] == str(mypy)
    assert by_name["pytest"][0] == str(pytest_exe)

    quick_by_name = {c.name: c.argv for c in quick}
    assert quick_by_name["pytest (no e2e)"][0] == str(pytest_exe)

    for c in (*full, *quick):
        assert c.argv[0] != "poetry", c.name
