"""The reference-transaction hook body: the creation refusal's fix line is the kernel's spelling
on every host, and an update the hook has no business with loads no kernel.

Owner: dd-sw-engineer-sr
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from dadaia_workspace.core.cli_line import reinstall_fix
from dadaia_workspace.core.platform import Capabilities
from dadaia_workspace.hooks import ref_transaction
from tests.fixtures.harness_env import suite_env
from tests.helpers import oslib
from tests.helpers.oslib import run, write_text

pytestmark = pytest.mark.medium

_ZERO, _SHA, _OTHER = "0" * 40, "a" * 40, "b" * 40
_CREATE = f"{_ZERO} {_SHA} refs/heads/wt/x\n".encode()
_UPDATE = f"{_SHA} {_OTHER} refs/heads/wt/x\n".encode()
_BLOCKED = "[ref-gate] BLOCKED refs/heads/wt/x: wt/ branches are created by the worktree runner"


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    run(["git", "init", "-q"], cwd=root, check=True)
    monkeypatch.chdir(root)
    return root


def _venv(tmp_path: Path, name: str, caps: oslib.Caps | None) -> Path:
    """A venv at *tmp_path*/*name*; with *caps*, its CLI file where that host keeps it."""
    venv = tmp_path / name
    venv.mkdir()
    if caps:
        cli = oslib.venv_tool(venv, "dadaia", caps)
        cli.parent.mkdir(parents=True)
        write_text(cli, "")
    return venv


@pytest.mark.parametrize("host", ["linux", "win32"])
@pytest.mark.parametrize("name", ["venv", "my venv"])
def test_the_creation_fix_is_the_kernels_command_on_every_host(
    host: str,
    name: str,
    repo: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    caps = oslib.detect(host)
    monkeypatch.setattr("dadaia_workspace.core.platform.PLATFORM", Capabilities.detect(host))
    venv = _venv(tmp_path, name, caps)
    monkeypatch.setattr(sys, "prefix", str(venv))
    assert ref_transaction.main(_CREATE) == 1
    cli = oslib.venv_tool(venv, "dadaia", caps)
    line = oslib.command(str(cli), "worktree", "new", "repo", "x", caps=caps)
    assert capsys.readouterr().err == f"{_BLOCKED}\nfix: {line}\n"


def test_without_a_cli_the_fix_is_the_reinstall(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    venv = _venv(tmp_path, "venv", None)
    monkeypatch.setattr(sys, "prefix", str(venv))
    assert ref_transaction.main(_CREATE) == 1
    assert capsys.readouterr().err == f"{_BLOCKED}\nfix: {reinstall_fix(venv)}\n"


def test_an_update_of_a_wt_branch_loads_no_kernel(tmp_path: Path) -> None:
    """The common firing, a commit in a wt tree, pays for the interpreter and nothing else."""
    code = (
        "import sys\n"
        "from dadaia_workspace.hooks import ref_transaction\n"
        f"assert ref_transaction.main({_UPDATE!r}) == 0\n"
        "assert 'dadaia_workspace.core.platform' not in sys.modules\n"
    )
    done = run([sys.executable, "-B", "-c", code], env=suite_env(os.environ, tmp_path), timeout=60)
    assert done.returncode == 0, done.stderr
