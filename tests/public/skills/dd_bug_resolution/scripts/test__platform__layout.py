"""The kernel's venv layout, foreign-path and home rules, over both host capabilities."""

from __future__ import annotations

from pathlib import Path, PurePosixPath

import pytest

from dadaia_workspace.core.skill_owner import load_owner

K = load_owner("dd-bug-resolution", "_platform")
POSIX, WIN = K.detect("linux"), K.detect("win32")


@pytest.mark.parametrize(
    ("caps", "python", "cli"),
    [
        (POSIX, "/w/.dadaia/.venv/bin/python", "/w/.dadaia/.venv/bin/dadaia"),
        (WIN, "/w/.dadaia/.venv/Scripts/python.exe", "/w/.dadaia/.venv/Scripts/dadaia.exe"),
    ],
)
def test_venv_tools_live_where_the_host_puts_them(caps: object, python: str, cli: str) -> None:
    root = PurePosixPath("/w")
    venv = K.venv_dir(root)
    assert str(K.python_in(venv, caps)) == python
    assert str(K.cli_path(root, caps)) == cli
    assert str(K.venv_tool(venv, "dadaia", caps)) == cli


@pytest.mark.parametrize(
    ("candidate", "windows", "posix"),
    [
        ("C:\\tools\\python.exe", True, False),
        ("C:/tools/python.exe", True, False),
        ("\\tools\\python.exe", False, False),
        ("\\\\host\\share\\python.exe", True, False),
        ("/usr/bin/python", False, True),
        ("python", False, False),
    ],
)
def test_a_path_is_fully_qualified_by_the_host_rule(
    candidate: str, windows: bool, posix: bool
) -> None:
    assert K.is_fully_qualified(candidate, WIN) is windows
    assert K.is_fully_qualified(candidate, POSIX) is posix


def test_norm_sep_spells_a_foreign_path_with_forward_slashes() -> None:
    assert K.norm_sep("a\\b/c\\") == "a/b/c/"


def test_cli_argv_is_the_console_script_on_every_host() -> None:
    venv = PurePosixPath("/ws/.dadaia/.venv")
    assert K.cli_argv(venv, WIN) == ["/ws/.dadaia/.venv/Scripts/dadaia.exe"]
    assert K.cli_argv(venv, POSIX) == ["/ws/.dadaia/.venv/bin/dadaia"]


def test_canonical_cli_maps_the_windows_spelling_to_the_source_form() -> None:
    win = "run .venv/Scripts/dadaia.exe doctor"
    assert K.canonical_cli(win, WIN) == "run .venv/bin/dadaia doctor"
    assert K.canonical_cli("run .venv/bin/dadaia doctor", POSIX) == "run .venv/bin/dadaia doctor"


def test_cli_words_are_the_console_script_of_the_root_venv_then_the_argv() -> None:
    root = PurePosixPath("/ws")
    assert K.cli_words(root, "context", "bind", caps=WIN) == (
        "/ws/.dadaia/.venv/Scripts/dadaia.exe", "context", "bind",
    )  # fmt: skip
    assert K.cli_words(root, caps=POSIX) == ("/ws/.dadaia/.venv/bin/dadaia",)


def test_cli_words_of_no_root_name_the_venv_running_now(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.prefix", "/cache/venvs/proj")
    assert K.cli_words(None, "doctor", caps=POSIX) == ("/cache/venvs/proj/bin/dadaia", "doctor")


def test_home_env_sets_the_variable_the_host_reads(tmp_path: Path) -> None:
    assert K.home_env(tmp_path, POSIX) == {"HOME": str(tmp_path)}
    assert K.home_env(tmp_path, WIN) == {"HOME": str(tmp_path), "USERPROFILE": str(tmp_path)}
