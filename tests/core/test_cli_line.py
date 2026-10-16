"""One CLI spelling; both platform forms are pinned."""

from __future__ import annotations

import ast
import re
from pathlib import Path, PurePosixPath, PureWindowsPath

import pytest

from dadaia_workspace.core import cli_line
from dadaia_workspace.core.platform import Capabilities, workspace_cli_path
from dadaia_workspace.core.skill_owner import load_owner


def test_posix_cli_path_and_fix_line(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("dadaia_workspace.core.platform.PLATFORM", Capabilities.detect("linux"))
    root = PurePosixPath("/ws/my ws")
    assert workspace_cli_path(root) == PurePosixPath("/ws/my ws/.dadaia/.venv/bin/dadaia")
    assert (
        cli_line.fix_line(root, "context", "bind", "a b")
        == "'/ws/my ws/.dadaia/.venv/bin/dadaia' context bind 'a b'"
    )


def test_windows_cli_path_and_fix_line(monkeypatch: pytest.MonkeyPatch) -> None:
    """Forward slashes; a part with a blank quoted whole, `-c` code one word; the CLI heads a
    Windows line as the venv's python.exe running the module, never the pip launcher, and a
    root with a blank spells that head `C":..."`."""
    monkeypatch.setattr("dadaia_workspace.core.platform.PLATFORM", Capabilities.detect("win32"))
    root = PureWindowsPath(r"C:\ws\my ws")
    assert workspace_cli_path(root) == PureWindowsPath(
        r"C:\ws\my ws\.dadaia\.venv\Scripts\dadaia.exe"
    )
    assert cli_line.fix_line(PureWindowsPath(r"C:\ws"), "doctor", "--fix") == (
        "C:/ws/.dadaia/.venv/Scripts/python.exe -m dadaia_workspace doctor --fix"
    )
    assert cli_line.fix_line(root, "doctor", "--fix") == (
        'C":/ws/my ws/.dadaia/.venv/Scripts/python.exe" -m dadaia_workspace doctor --fix'
    )
    monkeypatch.setattr("sys.executable", r"C:\my ws\python.exe")
    assert cli_line.mkdir_line(PureWindowsPath(r"C:\my ws\tmp")) == (
        'C":/my ws/python.exe" -c "import pathlib; '
        "pathlib.Path(r'C:/my ws/tmp').mkdir(parents=True, exist_ok=True)\""
    )
    assert (
        cli_line.shell_line("git", "-C", r"C:\ws\repos\app", "status")
        == "git -C C:/ws/repos/app status"
    )


@pytest.mark.parametrize("root", [r"C:\ws", r"C:\ws\my ws"])
def test_no_windows_fix_line_names_the_pip_launcher(
    root: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The launcher garbles a quoted path in cmd: the venv's python.exe heads the line instead."""
    monkeypatch.setattr("dadaia_workspace.core.platform.PLATFORM", Capabilities.detect("win32"))
    line = cli_line.fix_line(PureWindowsPath(root), "doctor")
    assert "dadaia.exe" not in line
    assert "python.exe" in line


@pytest.mark.parametrize("platform", ["linux", "win32"])
def test_cli_line_renders_every_argv_as_the_kernel_does(
    platform: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One producer: the package's renderers are the kernel's `command`, an unspellable word's
    Agent action included, so no argv is spelled two ways."""
    caps = Capabilities.detect(platform)
    monkeypatch.setattr("dadaia_workspace.core.platform.PLATFORM", caps)
    owner = load_owner("dd-bug-resolution", "_platform")
    kernel = owner.detect(platform)
    for argv in (
        ("git", "commit", "-m", "it's $HOME"),
        ("uvx", "dadaia-workspace", "init", "C:/Users/Shared/Jo$x/my ws"),
        ("C:/Program Files/x.exe", "a b"),
    ):
        assert cli_line.shell_line(*argv) == owner.command(*argv, caps=kernel)
    assert cli_line.git_line(
        "C:/Users/Shared/my ws", "commit", "-m", "it's $HOME"
    ) == owner.command(
        "git", "-C", "C:/Users/Shared/my ws", "commit", "-m", "it's $HOME", caps=kernel
    )


def test_no_workspace_names_the_cli_of_the_running_venv(monkeypatch: pytest.MonkeyPatch) -> None:
    """CI over a bare checkout runs the CLI from a venv outside any workspace: the fix
    line names THAT executable, never a workspace-relative path that does not exist."""
    monkeypatch.setattr("dadaia_workspace.core.platform.PLATFORM", Capabilities.detect("linux"))
    monkeypatch.setattr("sys.prefix", "/cache/venvs/proj")
    cli = str(Path("/cache/venvs/proj", "bin", "dadaia"))
    assert cli_line.fix_line(None, "doctor", "--fix") == cli_line.shell_line(cli, "doctor", "--fix")


def test_the_kernel_spells_the_fix_line_and_the_reinstall_act(tmp_path: Path) -> None:
    assert cli_line.spell_fix("do it") == "fix: do it"
    assert (
        cli_line.reinstall_fix(tmp_path)
        == "Agent action: run `uvx dadaia-workspace init` with the workspace's directory as its first argument"
    )
    (tmp_path / ".dadaia" / "states").mkdir(parents=True)
    (tmp_path / ".dadaia" / "states" / "spec_contexts.json").write_text("{}", encoding="utf-8")
    assert cli_line.reinstall_fix(tmp_path / "specs") == cli_line.shell_line(
        "uvx", "dadaia-workspace", "init", str(tmp_path.resolve())
    )


def test_no_string_outside_the_kernel_spells_a_fix_line_by_hand() -> None:
    package = Path(cli_line.__file__).resolve().parents[1]
    spelled = re.compile(r"(?<![\w-])fix:")
    hits: list[str] = []
    for path in package.rglob("*.py"):
        if path.name == "_refusal.py":  # the kernel
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        docs = {id(n.body[0].value) for n in ast.walk(tree)
                if isinstance(n, ast.Module | ast.FunctionDef | ast.ClassDef) and n.body
                and isinstance(n.body[0], ast.Expr)}  # fmt: skip
        hits += [
            f"{path.relative_to(package)}:{n.lineno}"
            for n in ast.walk(tree)
            if isinstance(n, ast.Constant)
            and isinstance(n.value, str)
            and id(n) not in docs
            and spelled.search(n.value)
        ]
    assert hits == []
