"""`dadaia worktree <verb> …`: a thin runner of the installed `worktree.py`.
Size: SMALL (in-process CliRunner, a stub script at the resolver's install location).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from typer.testing import CliRunner

import dadaia_workspace
from dadaia_workspace.cli.main import app
from dadaia_workspace.core.cli_line import fix_line
from dadaia_workspace.infrastructure import ledger_scripts
from tests.helpers.oslib import make_executable, run, write_text

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
    write_text(scripts / "worktree.py", _STUB)


@pytest.mark.medium
def test_argv_stdout_and_exit_code_are_forwarded(workspace: Path) -> None:
    _install_stub(workspace)
    result = CliRunner().invoke(app, ["worktree", "merge", "wt/x", "--sha", "abc"])
    assert json.loads(result.stdout) == ["merge", "wt/x", "--sha", "abc"]
    assert result.exit_code == 3


@pytest.mark.medium
def test_a_verb_help_flag_reaches_the_script(workspace: Path) -> None:
    _install_stub(workspace)
    result = CliRunner().invoke(app, ["worktree", "merge", "--help"])
    assert json.loads(result.stdout) == ["merge", "--help"]
    assert result.exit_code == 3


@pytest.mark.medium
@pytest.mark.parametrize("owned", [True, False], ids=["in-a-workspace", "outside-any-workspace"])
def test_help_lists_the_verbs(
    workspace: Path, monkeypatch: pytest.MonkeyPatch, owned: bool
) -> None:
    """The verbs come from the script's own help, forwarded: the packaged copy answers."""
    shipped = Path(dadaia_workspace.__file__).parent / "public" / "skills"
    monkeypatch.setattr(ledger_scripts, "_PACKAGE_SKILLS", shipped)
    if not owned:
        monkeypatch.setattr(ledger_scripts, "own_workspace_root", lambda: None)
    result = CliRunner().invoke(
        app, ["worktree", "--help"], env={"COLUMNS": "400", "NO_COLOR": "1"}
    )
    assert result.exit_code == 0
    words = set(re.findall(r"\w+", result.output))
    assert {"new", "merge", "clean", "list", "hash"} <= words


def test_no_installed_script_refuses_with_the_install_fix(workspace: Path) -> None:
    (workspace / ".dadaia" / "states").mkdir(parents=True)
    write_text(workspace / ".dadaia" / "states" / "spec_contexts.json", "{}")
    result = CliRunner().invoke(app, ["worktree", "list"])
    assert result.exit_code != 0
    assert f"fix: {fix_line(workspace.resolve(), 'public', 'install')}" in result.output


def test_outside_any_workspace_the_missing_script_names_the_init_act(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(ledger_scripts, "own_workspace_root", lambda: None)
    result = CliRunner().invoke(app, ["worktree", "list"])
    assert result.exit_code != 0
    assert (
        "fix: Agent action: run `uvx dadaia-workspace init` with the workspace's directory as its first argument"
        in result.output
    )


@pytest.mark.medium
def test_a_runner_that_lags_the_hook_still_creates_a_wt_branch(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The BLOCK's fix line is `worktree new`: the forwarder marks the run, whatever the projected runner does."""
    monkeypatch.delenv("DADAIA_WT", raising=False)
    repo = workspace / "repo"
    git = lambda *a: run(["git", "-C", str(repo), *a], check=True)  # noqa: E731
    repo.mkdir()
    git("init", "-q", "-b", "main")
    git(
        "-c",
        "user.email=a@b.invalid",
        "-c",
        "user.name=n",
        "commit",
        "-q",
        "--allow-empty",
        "-m",
        "i",
    )
    hook = repo / ".git" / "hooks" / "reference-transaction"
    hook.write_bytes(
        (
            Path(dadaia_workspace.__file__).parent
            / "public"
            / "scripts"
            / "reference-transaction.sh"
        ).read_bytes()
    )
    make_executable(hook)
    scripts = workspace / ".agents" / "skills" / "dd-gitflow-default" / "scripts"
    scripts.mkdir(parents=True)
    write_text(
        scripts / "worktree.py",
        f"import sys\nfrom subprocess import run\nsys.exit(run(['git', '-C', {str(repo)!r}, 'branch', 'wt/x']).returncode)\n",
    )
    result = CliRunner().invoke(app, ["worktree", "new", "repo", "x"])
    assert result.exit_code == 0
    assert "wt/x" in run(["git", "-C", str(repo), "branch"]).stdout
