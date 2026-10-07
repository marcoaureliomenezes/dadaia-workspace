"""AC12.4 (venv-guard-misses-prefixed-and-absolute-dadaia): the venv guard judges every command
of a Bash line, so no prefix, env assignment or foreign path carries a bare `dadaia` past it."""

from __future__ import annotations

import pytest

from dadaia_workspace.core.platform import PLATFORM, Capabilities
from dadaia_workspace.hooks import venv_guard

_CLI = f".dadaia/.venv/{PLATFORM.venv_scripts_dir}/dadaia{PLATFORM.venv_exe_suffix}"
_PY = f".dadaia/.venv/{PLATFORM.venv_scripts_dir}/python3{PLATFORM.venv_exe_suffix}"


def _bash(command: str) -> dict[str, object]:
    return {"tool_name": "Bash", "tool_input": {"command": command}}


def _assert_blocked(command: str) -> None:
    reason = venv_guard.evaluate_payload(_bash(command))
    assert reason is not None, f"expected block for {command!r}"
    assert sum(line.startswith("fix: ") for line in reason.splitlines()) == 1


def _win32(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("dadaia_workspace.core.platform.PLATFORM", Capabilities.detect("win32"))


@pytest.mark.xfail(strict=True, reason="venv-guard-misses-prefixed-and-absolute-dadaia")
def test_blocks_cd_and() -> None:
    _assert_blocked("cd x && dadaia doctor")


@pytest.mark.xfail(strict=True, reason="venv-guard-misses-prefixed-and-absolute-dadaia")
def test_blocks_semicolon() -> None:
    _assert_blocked("true; dadaia doctor")


@pytest.mark.xfail(strict=True, reason="venv-guard-misses-prefixed-and-absolute-dadaia")
def test_blocks_semicolon_subshell() -> None:
    _assert_blocked("true;(dadaia doctor)")


@pytest.mark.xfail(strict=True, reason="venv-guard-misses-prefixed-and-absolute-dadaia")
def test_blocks_subshell_semicolon() -> None:
    _assert_blocked("(true);dadaia doctor")


@pytest.mark.xfail(strict=True, reason="venv-guard-misses-prefixed-and-absolute-dadaia")
def test_blocks_pipe() -> None:
    _assert_blocked("echo y | dadaia doctor")


@pytest.mark.xfail(strict=True, reason="venv-guard-misses-prefixed-and-absolute-dadaia")
def test_blocks_if_then() -> None:
    _assert_blocked("if true; then dadaia doctor; fi")


@pytest.mark.xfail(strict=True, reason="venv-guard-misses-prefixed-and-absolute-dadaia")
def test_blocks_brace_group() -> None:
    _assert_blocked("{ dadaia doctor; }")


@pytest.mark.xfail(strict=True, reason="venv-guard-misses-prefixed-and-absolute-dadaia")
def test_blocks_negation() -> None:
    _assert_blocked("! dadaia doctor")


@pytest.mark.xfail(strict=True, reason="venv-guard-misses-prefixed-and-absolute-dadaia")
def test_blocks_time() -> None:
    _assert_blocked("time dadaia doctor")


@pytest.mark.xfail(strict=True, reason="venv-guard-misses-prefixed-and-absolute-dadaia")
def test_blocks_or() -> None:
    _assert_blocked("false || dadaia doctor")


@pytest.mark.xfail(strict=True, reason="venv-guard-misses-prefixed-and-absolute-dadaia")
def test_blocks_background() -> None:
    _assert_blocked("sleep 1 & dadaia doctor")


@pytest.mark.xfail(strict=True, reason="venv-guard-misses-prefixed-and-absolute-dadaia")
def test_blocks_subshell() -> None:
    _assert_blocked("(dadaia doctor)")


@pytest.mark.xfail(strict=True, reason="venv-guard-misses-prefixed-and-absolute-dadaia")
def test_blocks_newline() -> None:
    _assert_blocked("true\ndadaia doctor")


@pytest.mark.xfail(strict=True, reason="venv-guard-misses-prefixed-and-absolute-dadaia")
def test_blocks_env_assignment() -> None:
    _assert_blocked("DADAIA_CONTEXT=x dadaia doctor")


@pytest.mark.xfail(strict=True, reason="venv-guard-misses-prefixed-and-absolute-dadaia")
def test_blocks_absolute_path() -> None:
    _assert_blocked("/usr/local/bin/dadaia doctor")


@pytest.mark.xfail(strict=True, reason="venv-guard-misses-prefixed-and-absolute-dadaia")
def test_blocks_dot_slash() -> None:
    _assert_blocked("./dadaia doctor")


@pytest.mark.xfail(strict=True, reason="venv-guard-misses-prefixed-and-absolute-dadaia")
def test_blocks_foreign_venv() -> None:
    _assert_blocked("repos/other/.venv/bin/dadaia doctor")


@pytest.mark.xfail(strict=True, reason="venv-guard-misses-prefixed-and-absolute-dadaia")
def test_blocks_cd_and_python() -> None:
    _assert_blocked("cd x && python3 -m dadaia_workspace doctor")


@pytest.mark.xfail(strict=True, reason="venv-guard-misses-prefixed-and-absolute-dadaia")
def test_blocks_system_python() -> None:
    _assert_blocked("/usr/bin/python3 -m dadaia_workspace doctor")


@pytest.mark.xfail(strict=True, reason="venv-guard-misses-prefixed-and-absolute-dadaia")
def test_blocks_win32_exe(monkeypatch: pytest.MonkeyPatch) -> None:
    _win32(monkeypatch)
    _assert_blocked("dadaia.exe doctor")


@pytest.mark.xfail(strict=True, reason="venv-guard-misses-prefixed-and-absolute-dadaia")
def test_blocks_win32_absolute_exe(monkeypatch: pytest.MonkeyPatch) -> None:
    _win32(monkeypatch)
    _assert_blocked("C:/tools/dadaia.exe doctor")


@pytest.mark.parametrize(
    "command",
    [
        f"{_CLI} doctor",
        f"cd x && {_CLI} doctor",
        f"true; {_CLI} doctor",
        f"echo y | {_CLI} doctor",
        f"(true);{_CLI} doctor",
        f"if true; then {_CLI} doctor; fi",
        f"{{ {_CLI} doctor; }}",
        f"! {_CLI} doctor",
        f"true\n{_CLI} doctor",
        f"DADAIA_CONTEXT=x {_CLI} doctor",
        f"/home/user/ws/{_CLI} doctor",
        f"{_PY} -m dadaia_workspace doctor",
        f"cd x && {_PY} -m dadaia_workspace doctor",
        'echo "a; dadaia doctor"',
        "x 2>&1 | cat",
        'echo "dadaia doctor',
    ],
)
def test_born_green_allows_the_venv_path_in_every_position(command: str) -> None:
    assert venv_guard.evaluate_payload(_bash(command)) is None


def test_born_green_allows_the_win32_venv_cli_in_every_position(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _win32(monkeypatch)
    for command in (
        ".dadaia/.venv/Scripts/dadaia.exe doctor",
        "cd x && .dadaia/.venv/Scripts/dadaia.exe doctor",
        "/c/ws/.dadaia/.venv/Scripts/dadaia.exe doctor",
    ):
        assert venv_guard.evaluate_payload(_bash(command)) is None, command


def test_blocks_win32_bare_dadaia(monkeypatch: pytest.MonkeyPatch) -> None:
    """Born green: today's first-token rule already blocks it; it stays blocked."""
    _win32(monkeypatch)
    _assert_blocked("dadaia doctor")
