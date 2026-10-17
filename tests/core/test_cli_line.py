"""One CLI spelling; both platform forms are pinned."""

from __future__ import annotations

import ast
import re
from pathlib import Path, PurePosixPath, PureWindowsPath

import pytest

from dadaia_workspace.core import cli_line
from dadaia_workspace.core.platform import Capabilities, workspace_cli_path
from dadaia_workspace.core.skill_owner import load_owner
from tests.helpers import oslib
from tests.helpers.oslib import read_text, write_text


def test_posix_cli_path_and_fix_line(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("dadaia_workspace.core.platform.PLATFORM", Capabilities.detect("linux"))
    root = PurePosixPath("/ws/my ws")
    assert workspace_cli_path(root) == PurePosixPath("/ws/my ws/.dadaia/.venv/bin/dadaia")
    assert (
        cli_line.fix_line(root, "context", "bind", "a b")
        == "'/ws/my ws/.dadaia/.venv/bin/dadaia' context bind 'a b'"
    )


def test_windows_cli_path_and_fix_line(monkeypatch: pytest.MonkeyPatch) -> None:
    """Forward slashes; a part with a blank quoted whole, `-c` code one word; a head with a blank
    has no spelling that runs in cmd, PowerShell and Git Bash alike, so the line is an Agent action."""
    monkeypatch.setattr("dadaia_workspace.core.platform.PLATFORM", Capabilities.detect("win32"))
    root = PureWindowsPath(r"C:\ws\my ws")
    assert workspace_cli_path(root) == PureWindowsPath(
        r"C:\ws\my ws\.dadaia\.venv\Scripts\dadaia.exe"
    )
    assert cli_line.fix_line(PureWindowsPath(r"C:\ws"), "doctor", "--fix") == (
        "C:/ws/.dadaia/.venv/Scripts/dadaia.exe doctor --fix"
    )
    cli = r"C:\ws\my ws\.dadaia\.venv\Scripts\dadaia.exe"  # the Agent action shows the real value
    assert cli_line.fix_line(root, "doctor", "--fix") == (
        f"Agent action: run {cli} doctor --fix, quoting {cli} for your shell"
    )
    monkeypatch.setattr("sys.executable", r"C:\my ws\python.exe")
    assert cli_line.mkdir_line(PureWindowsPath(r"C:\my ws\tmp")) == (
        'Agent action: run C:\\my ws\\python.exe -c "import pathlib, sys; '
        'pathlib.Path(sys.argv[1]).mkdir(parents=True, exist_ok=True)" "C:/my ws/tmp", '
        "quoting C:\\my ws\\python.exe for your shell"
    )
    assert (
        cli_line.shell_line("git", "-C", r"C:\ws\repos\app", "status")
        == "git -C C:/ws/repos/app status"
    )


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


_SHELL = ["powershell", "-NoProfile", "-Command"] if oslib.detect().windows else ["sh", "-c"]


@pytest.mark.medium
def test_mkdir_line_runs_for_a_path_holding_a_quote_and_a_blank(tmp_path: Path) -> None:
    """The path is an argv word of the interpreter line, never text inside its code."""
    made = tmp_path / "it's here" / "deep"
    done = oslib.run([*_SHELL, cli_line.mkdir_line(made)])
    assert (done.returncode, made.is_dir()) == (0, True), done.stderr


@pytest.mark.medium
def test_materialize_line_runs_for_a_path_holding_a_quote_and_a_blank(tmp_path: Path) -> None:
    target = tmp_path / "it's a target.txt"
    write_text(target, "kept")
    link = tmp_path / "it's a link.txt"
    assert oslib.link(str(target), link, is_dir=False)
    done = oslib.run([*_SHELL, cli_line.materialize_line(link, target)])
    assert (done.returncode, oslib.is_link(link), read_text(link)) == (0, False, "kept"), (
        done.stderr
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
    write_text(tmp_path / ".dadaia" / "states" / "spec_contexts.json", "{}")
    assert cli_line.reinstall_fix(tmp_path / "specs") == cli_line.shell_line(
        "uvx", "dadaia-workspace", "init", str(tmp_path.resolve())
    )


def test_the_reinstall_fix_of_a_root_win32_cannot_spell_is_an_act(tmp_path: Path) -> None:
    root = tmp_path / "a$b"
    (root / ".dadaia" / "states").mkdir(parents=True)
    write_text(root / ".dadaia" / "states" / "spec_contexts.json", "{}")
    fix = load_owner("dd-bug-resolution", "_jsonl").reinstall_fix(
        root / "specs", oslib.detect("win32")
    )
    assert fix == (
        f"Agent action: run uvx dadaia-workspace init {root.resolve()}, "
        f"quoting {root.resolve()} for your shell"
    )


def test_no_string_outside_the_kernel_spells_a_fix_line_by_hand() -> None:
    package = Path(cli_line.__file__).resolve().parents[1]
    spelled = re.compile(r"(?<![\w-])fix:")
    hits: list[str] = []
    for path in package.rglob("*.py"):
        if path.name == "_refusal.py":  # the kernel
            continue
        tree = ast.parse(read_text(path))
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
