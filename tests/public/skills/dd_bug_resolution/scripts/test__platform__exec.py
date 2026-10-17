"""The kernel's exec-bit, filesystem-swap and link rules."""

from __future__ import annotations

import os
import stat
import time
from pathlib import Path

import pytest

from dadaia_workspace.core.skill_owner import load_owner
from tests.helpers.oslib import read_text, write_text

K = load_owner("dd-bug-resolution", "_platform")
POSIX, WIN = K.detect("linux"), K.detect("win32")


def _chmods(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, int]]:
    seen: list[tuple[str, int]] = []
    monkeypatch.setattr(os, "chmod", lambda p, m, **_: seen.append((str(p), m)))
    return seen


def test_make_executable_adds_the_exec_bits_on_posix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    script = tmp_path / "run.sh"
    write_text(script, "x")
    script.chmod(0o644)
    mode = stat.S_IMODE(script.stat().st_mode)
    seen = _chmods(monkeypatch)
    K.make_executable(script, POSIX)
    assert seen == [(str(script), mode | 0o111)]


def test_make_executable_is_a_no_op_on_windows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    script = tmp_path / "run.sh"
    write_text(script, "x")
    seen = _chmods(monkeypatch)
    K.make_executable(script, WIN)
    assert seen == []


def test_is_executable_is_existence_on_windows(tmp_path: Path) -> None:
    script = tmp_path / "run.sh"
    write_text(script, "x")
    assert K.is_executable(script, WIN) is True
    assert K.is_executable(tmp_path / "absent", WIN) is False


def test_a_file_made_executable_on_this_host_is_executable_and_an_absent_one_is_not(
    tmp_path: Path,
) -> None:
    script = tmp_path / "run.sh"
    write_text(script, "x")
    K.make_executable(script)
    assert K.is_executable(script) is True
    assert K.is_executable(tmp_path / "absent") is False


def test_replace_swaps_a_file_onto_an_existing_one_and_a_directory_onto_a_free_name(
    tmp_path: Path,
) -> None:
    write_text(tmp_path / "a", "new")
    write_text(tmp_path / "b", "old")
    K.replace(tmp_path / "a", tmp_path / "b")
    assert [p.name for p in sorted(tmp_path.iterdir())] == ["b"]
    assert read_text(tmp_path / "b") == "new"
    (tmp_path / "d").mkdir()
    K.replace(tmp_path / "d", tmp_path / "e")
    assert [p.name for p in sorted(tmp_path.iterdir())] == ["b", "e"]


def test_replace_retries_a_held_open_destination_then_succeeds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[int] = []
    real = os.replace

    def held(src: object, dst: object) -> None:
        calls.append(1)
        if len(calls) <= 3:
            raise PermissionError("held open")
        real(src, dst)  # type: ignore[arg-type]

    monkeypatch.setattr(time, "sleep", lambda _s: None)
    monkeypatch.setattr(os, "replace", held)
    write_text(tmp_path / "a", "x")
    K.replace(tmp_path / "a", tmp_path / "b")
    assert (len(calls), read_text(tmp_path / "b")) == (4, "x")


def test_replace_raises_after_fifty_attempts_on_a_destination_that_stays_held(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[int] = []

    def held(src: object, dst: object) -> None:
        calls.append(1)
        raise PermissionError("held open")

    monkeypatch.setattr(time, "sleep", lambda _s: None)
    monkeypatch.setattr(os, "replace", held)
    with pytest.raises(PermissionError):
        K.replace(tmp_path / "a", tmp_path / "b")
    assert len(calls) == 50


def test_link_either_makes_a_link_is_link_sees_or_reports_false(tmp_path: Path) -> None:
    target = tmp_path / "t"
    write_text(target, "x")
    made = K.link("t", tmp_path / "l", is_dir=False)
    assert K.is_link(tmp_path / "l") is made
    assert K.is_link(target) is False
    assert K.is_link(tmp_path / "absent") is False


def test_is_link_sees_a_dangling_link(tmp_path: Path) -> None:
    made = K.link("nowhere", tmp_path / "l", is_dir=False)
    assert K.is_link(tmp_path / "l") is made


def test_make_writable_gives_the_owner_write_on_a_file_and_a_directory(tmp_path: Path) -> None:
    folder = tmp_path / "d"
    folder.mkdir()
    file = folder / "f"
    write_text(file, "x")
    file.chmod(0o444)
    K.make_writable(file)
    K.make_writable(folder)
    assert stat.S_IMODE(file.stat().st_mode) & 0o200 == 0o200
    assert stat.S_IMODE(folder.stat().st_mode) & 0o200 == 0o200
