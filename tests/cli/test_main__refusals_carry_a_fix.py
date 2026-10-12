"""`ci install-hook` on an off-repo directory prints `Error:` first and exactly one `fix:`
line, with no traceback. The case drives the console entry (`_safe_app`) on a temp dir."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from dadaia_workspace.cli import main

_ENV_VARS = ("DADAIA_SESSION_ID", "DADAIA_CONTEXT", "DADAIA_FENCED_ROOTS", "DADAIA_TRACEBACK")


def _run(argv: list[str]) -> int:
    sys.argv = ["dadaia", *argv]
    try:
        main._safe_app()
    except SystemExit as exc:
        return int(exc.code or 0)
    return 0


@pytest.fixture(autouse=True)
def _isolated(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr("dadaia_workspace.core.workspace_resolver.own_workspace_root", lambda: None)
    for var in _ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.chdir(tmp_path)


@pytest.mark.medium
def test_ci_install_hook_on_a_non_git_dir_is_one_refusal(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()
    capsys.readouterr()
    code = _run(["ci", "install-hook", "--repo", str(plain)])
    err = capsys.readouterr().err
    lines = err.splitlines()
    assert code == 1, err
    assert lines[0].startswith("Error:"), err
    assert "unexpected" not in err and "Traceback" not in err, err
    assert len([ln for ln in lines if ln.startswith("fix:")]) == 1, err
