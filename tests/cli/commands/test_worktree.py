"""`dadaia worktree <verb> …`: a thin runner of the installed `worktree.py`.
Size: SMALL (in-process CliRunner, a stub script at the resolver's install location).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.core.cli_line import fix_line
from dadaia_workspace.infrastructure import ledger_scripts

_STUB = "import json, sys\nprint(json.dumps(sys.argv[1:]))\nsys.exit(3)\n"


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A workspace with no installed `worktree.py` and an empty packaged-skills fallback."""
    (tmp_path / "package").mkdir()
    monkeypatch.setattr(ledger_scripts, "_PACKAGE_SKILLS", tmp_path / "package")
    monkeypatch.setattr(ledger_scripts, "own_workspace_root", lambda: tmp_path)
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _install_stub(workspace: Path) -> None:
    scripts = workspace / ".agents" / "skills" / "dd-gitflow-default" / "scripts"
    scripts.mkdir(parents=True)
    (scripts / "worktree.py").write_text(_STUB, encoding="utf-8")


def test_argv_stdout_and_exit_code_are_forwarded(workspace: Path) -> None:
    _install_stub(workspace)
    result = CliRunner().invoke(app, ["worktree", "merge", "wt/x", "--sha", "abc"])
    assert json.loads(result.stdout) == ["merge", "wt/x", "--sha", "abc"]
    assert result.exit_code == 3


def test_help_lists_the_verbs(workspace: Path) -> None:
    result = CliRunner().invoke(
        app, ["worktree", "--help"], env={"COLUMNS": "400", "NO_COLOR": "1"}
    )
    assert result.exit_code == 0
    words = set(re.findall(r"\w+", result.output))
    assert {"new", "merge", "clean", "list", "preflight", "sync", "hash"} <= words


def test_no_installed_script_refuses_with_the_install_fix(workspace: Path) -> None:
    result = CliRunner().invoke(app, ["worktree", "list"])
    assert result.exit_code != 0
    assert f"fix: {fix_line(None, 'public', 'install')}" in result.output
