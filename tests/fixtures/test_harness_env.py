"""rc-9 AC3.1: the suite's whole env is one pure function — the operator's session out, the
temp home and the suite keys in (bugs outside-tmp-home-pin-coupled-to-session-hooks,
operator-env-scrub-row-leaves-stale-pinned-home)."""

from __future__ import annotations

import sys
from pathlib import Path, PurePosixPath

import pytest

_HOME = "/tmp/h"


# fmt: off
@pytest.mark.parametrize(("parent", "expected"), [
    pytest.param(
        {"PATH": "/bin", "HOME": "/op", "XDG_CACHE_HOME": "/op/.cache",
         "DADAIA_CONTEXT": "ghost", "DADAIA_SESSION_ID": "s", "DADAIA_PERSONA": "p",
         "CLAUDE_CODE_SESSION_ID": "c", "CODEX_SESSION_ID": "x", "CODEX_THREAD_ID": "t",
         "CLAUDE_AGENT_PERSONA": "a", "CODEX_AGENT_PERSONA": "b",
         "DADAIA_FENCED_ROOTS": "/fence", "DADAIA_REQUIRE_UVX": "1"},
        {"PATH": "/bin", "HOME": _HOME, "USERPROFILE": _HOME, "XDG_CACHE_HOME": f"{_HOME}/.cache",
         "LOCALAPPDATA": f"{_HOME}/AppData/Local", "KIMI_CODE_HOME": f"{_HOME}/.kimi-code",
         "PYTHONDONTWRITEBYTECODE": "1", "DADAIA_FENCED_ROOTS": "/fence", "DADAIA_REQUIRE_UVX": "1"},
        id="operator-out-temp-home-in",
    ),
])
# fmt: on
def test_suite_env(parent: dict[str, str], expected: dict[str, str]) -> None:
    from tests.fixtures.harness_env import suite_env

    assert suite_env(parent, PurePosixPath(_HOME)) == expected


@pytest.mark.medium
def test_run_python_runs_this_interpreter() -> None:
    from tests.fixtures.harness_env import run_python

    done = run_python("-c", "import sys; print(sys.executable)")
    assert done.stdout.strip() == sys.executable


def test_git_bash_off_windows_is_bash(monkeypatch: pytest.MonkeyPatch) -> None:
    from dadaia_workspace.core.platform import Capabilities
    from tests.fixtures.harness_env import git_bash

    monkeypatch.setattr("dadaia_workspace.core.platform.PLATFORM", Capabilities.detect("linux"))
    assert git_bash() == "bash"


def test_git_bash_on_windows_is_the_one_beside_git(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from dadaia_workspace.core.platform import Capabilities
    from tests.fixtures.harness_env import git_bash

    (tmp_path / "Git" / "cmd").mkdir(parents=True)
    (tmp_path / "Git" / "bin").mkdir()
    (tmp_path / "Git" / "cmd" / "git.exe").write_text("", "utf-8")
    (tmp_path / "Git" / "bin" / "bash.exe").write_text("", "utf-8")
    monkeypatch.setattr("dadaia_workspace.core.platform.PLATFORM", Capabilities.detect("win32"))
    monkeypatch.setattr("shutil.which", lambda _name: str(tmp_path / "Git" / "cmd" / "git.exe"))
    assert git_bash() == str(tmp_path / "Git" / "bin" / "bash.exe")


def test_git_bash_on_windows_without_git_refuses(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from dadaia_workspace.core.platform import Capabilities
    from tests.fixtures.harness_env import git_bash

    monkeypatch.setattr("dadaia_workspace.core.platform.PLATFORM", Capabilities.detect("win32"))
    monkeypatch.setattr("shutil.which", lambda _name: None)
    monkeypatch.setenv("PROGRAMFILES", str(tmp_path))
    with pytest.raises(FileNotFoundError, match="Git Bash"):
        git_bash()


@pytest.mark.medium
def test_run_bash_runs_the_command(monkeypatch: pytest.MonkeyPatch) -> None:
    from dadaia_workspace.core.platform import Capabilities
    from tests.fixtures.harness_env import run_bash

    monkeypatch.setattr("dadaia_workspace.core.platform.PLATFORM", Capabilities.detect("linux"))
    assert run_bash("echo hi").stdout.strip() == "hi"


def test_retire_tree_moves_a_tree_holding_a_readonly_git(tmp_path: Path) -> None:
    from tests.fixtures.harness_env import retire_tree

    repo = tmp_path / "repos" / "alpha"
    (repo / ".git").mkdir(parents=True)
    obj = repo / ".git" / "obj"
    obj.write_text("x", "utf-8")
    obj.chmod(0o444)
    elsewhere = tmp_path / "gone"
    elsewhere.mkdir()
    moved = retire_tree(repo, elsewhere)
    assert (moved, repo.exists(), (moved / ".git" / "obj").read_text("utf-8")) == (
        elsewhere / "alpha",
        False,
        "x",
    )
