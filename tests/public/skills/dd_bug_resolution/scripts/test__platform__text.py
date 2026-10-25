"""The kernel's one text codec (`_platform`): UTF-8, LF by default, one decode error."""

from __future__ import annotations

import ast
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from dadaia_workspace.core.skill_owner import load_owner

K = load_owner("dd-bug-resolution", "_platform")
_KERNEL_DIR = Path(K.__file__).parent
_ENTRY_POINTS = sorted(_KERNEL_DIR.parents[1].glob("*/scripts/[!_]*.py"))


def test_read_text_retries_a_read_the_swap_holds_then_returns_the_text(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "a.md"
    path.write_text("ok\n", encoding="utf-8")
    calls: list[int] = []
    real = Path.read_text

    def held(self: Path, *args: object, **kwargs: object) -> str:
        calls.append(1)
        if len(calls) <= 3:
            raise PermissionError("held open")
        return real(self, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(time, "sleep", lambda _s: None)
    monkeypatch.setattr(Path, "read_text", held)
    assert (K.read_text(path), len(calls)) == ("ok\n", 4)


def test_read_text_raises_permissionerror_after_fifty_attempts_on_a_file_that_stays_held(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[int] = []

    def held(self: Path, *args: object, **kwargs: object) -> str:
        calls.append(1)
        raise PermissionError("denied")

    monkeypatch.setattr(time, "sleep", lambda _s: None)
    monkeypatch.setattr(Path, "read_text", held)
    with pytest.raises(PermissionError):
        K.read_text(tmp_path / "a.md")
    assert len(calls) == 50


def test_read_text_decodes_utf8_and_translates_crlf(tmp_path: Path) -> None:
    path = tmp_path / "a.md"
    path.write_bytes("café\r\nx\n".encode())
    assert K.read_text(path) == "café\nx\n"


def test_read_text_of_cp1252_bytes_raises_undecodable_naming_the_path_and_line(
    tmp_path: Path,
) -> None:
    path = tmp_path / "a.md"
    path.write_bytes(b"ok\ncaf\xe9\n")
    with pytest.raises(K.Undecodable) as bad:
        K.read_text(path)
    assert (bad.value.path, bad.value.line) == (path, 2)
    assert str(bad.value) == f"{path} is not valid UTF-8"
    assert bad.value.fix == (
        f"Agent action: re-encode line 2 of {path.resolve()} as UTF-8 in place; every other line stays"
    )


def test_read_text_fix_argument_replaces_the_default_fix(tmp_path: Path) -> None:
    path = tmp_path / "a.md"
    path.write_bytes(b"\xff")
    with pytest.raises(K.Undecodable) as bad:
        K.read_text(path, "Agent action: restore it")
    assert bad.value.fix == "Agent action: restore it"


def test_undecodable_is_the_kernels_refusal() -> None:
    refusal = load_owner("dd-bug-resolution", "_refusal").Refusal
    assert issubclass(K.Undecodable, refusal)


def test_write_text_writes_utf8_with_lf(tmp_path: Path) -> None:
    path = tmp_path / "a.md"
    K.write_text(path, "é\nx\n")
    assert path.read_bytes() == b"\xc3\xa9\nx\n"


def test_write_text_keeps_a_newline_the_caller_names(tmp_path: Path) -> None:
    path = tmp_path / "a.md"
    K.write_text(path, "a\nb", newline="\r\n")
    assert path.read_bytes() == b"a\r\nb"


def test_decode_drops_the_bom_and_crlf_and_replaces_bad_bytes() -> None:
    assert K.decode(b"\xef\xbb\xbfa\r\nb\xff") == "a\nb�"


def test_use_utf8_stdio_lets_a_cp1252_pipe_print_a_check_mark() -> None:
    code = (
        f"import sys; sys.path.insert(0, {str(_KERNEL_DIR)!r}); import _platform; "
        "_platform.use_utf8_stdio(); print('\\u2713')"
    )
    done = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        env={**os.environ, "PYTHONIOENCODING": "cp1252"},
    )
    assert (done.returncode, done.stdout.strip()) == (0, "✓".encode())


@pytest.mark.parametrize("entry", _ENTRY_POINTS, ids=lambda p: p.name)
def test_every_skill_entry_point_makes_its_stdio_utf8(entry: Path) -> None:
    main = next(
        n for n in ast.walk(ast.parse(K.read_text(entry))) if getattr(n, "name", "") == "main"
    )
    calls = {getattr(c.func, "id", "") for c in ast.walk(main) if isinstance(c, ast.Call)}
    assert "use_utf8_stdio" in calls
