"""The one atomic writer of ``dd-bug-resolution/scripts/_atomic.py``.

* Public names: ``atomic_write(path, content, *, preserve_mode=False, newline="",
  ensure_parent=False)`` and ``SymlinkRefusedError`` (``OSError``; ``.path``). A symlink
  target is refused; the Windows ``PermissionError`` swap retries before it raises.
* Core re-exports ``atomic_write`` and ``SymlinkRefusedError`` from that one module object.
* ``SymlinkRefusedError`` has a single home, ``_atomic``; one ``except`` catches the raise
  from either import path.
"""

from __future__ import annotations

import os
import stat
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path
from types import ModuleType

import pytest

from dadaia_workspace.core.atomic_write import SymlinkRefusedError
from dadaia_workspace.core.atomic_write import atomic_write as shim_write
from dadaia_workspace.core.skill_owner import load_owner
from tests.helpers.oslib import (
    detect,
    is_link,
    make_readonly,
    read_text,
    run,
    write_text,
)
from tests.helpers.oslib import link as os_link

_ROOT = Path(__file__).resolve().parents[5]
_SKILLS = _ROOT / "dadaia_workspace" / "public" / "skills"
_BUGS = _SKILLS / "dd-bug-resolution" / "scripts" / "bugs.py"


@pytest.fixture
def atomic() -> ModuleType:
    return load_owner("dd-bug-resolution", "_atomic")


_Write = Callable[..., None]


def _moded(path: Path, text: str) -> int:
    """Write *text* to *path*, read-only off Windows (a read-only file there refuses the swap; elsewhere
    chmod holds for root too, and the mode then differs from a fresh sibling's in a non-exec bit
    under any umask); the mode."""
    write_text(path, text)
    if not detect().windows:
        make_readonly(path)
        sibling = path.with_name("fresh-" + path.name)
        write_text(sibling, text)
        assert (stat.S_IMODE(path.stat().st_mode) ^ stat.S_IMODE(sibling.stat().st_mode)) & ~0o111
        sibling.unlink()
    return stat.S_IMODE(path.stat().st_mode)


def _symlink(path: Path, target: Path) -> None:
    if not os_link(str(target), path, is_dir=False):
        pytest.skip("the host refuses symlinks")


_REAL = {"write_text": Path.write_text, "write_bytes": Path.write_bytes}


def _ledger_replace(path: Path, content: str | None, **_: object) -> None:
    load_owner("dd-bug-resolution", "_ledger").replace(path, content)


@pytest.fixture(params=["atomic", "shim"])
def full(request: pytest.FixtureRequest) -> _Write:
    if request.param == "shim":
        return shim_write
    return load_owner("dd-bug-resolution", "_atomic").atomic_write  # type: ignore[no-any-return]


@pytest.fixture(params=["atomic", "shim", "ledger"])
def write(request: pytest.FixtureRequest, full: _Write) -> _Write:
    return _ledger_replace if request.param == "ledger" else full


@pytest.mark.parametrize(
    ("content", "kwargs", "expected"),
    [
        ("hello\n", {}, b"hello\n"),
        ('{"name": "caf\u00e9"}', {}, '{"name": "caf\u00e9"}'.encode()),
        (b"\x00\x01hello\xff", {}, b"\x00\x01hello\xff"),
        ("hello\n", {"ensure_parent": True}, b"hello\n"),
        ("line\n", {"newline": None}, b"line" + os.linesep.encode()),
    ],
    ids=["lf", "utf8-no-bom", "binary", "ensure-parent", "newline-none"],
)
def test_write_round_trips_fresh_and_over_an_existing_target(
    full: _Write, tmp_path: Path, content: str | bytes, kwargs: dict[str, object], expected: bytes
) -> None:
    target = tmp_path / "nested" / "a.md" if "ensure_parent" in kwargs else tmp_path / "a.md"
    for _ in range(2):
        full(target, content, **kwargs)
        assert target.read_bytes() == expected


def test_preserve_mode_keeps_the_mode_and_only_the_ledger_door_makes_parents(
    full: _Write, tmp_path: Path
) -> None:
    _ledger_replace(tmp_path / "x" / "b.txt", "b\n")
    assert (tmp_path / "x" / "b.txt").read_bytes() == b"b\n"
    target = tmp_path / "a.md"
    mode = _moded(target, "orig\n")
    full(target, "new\n", preserve_mode=True)
    assert stat.S_IMODE(target.stat().st_mode) == mode
    with pytest.raises(OSError):
        full(tmp_path / "nowhere" / "a.md", "hello\n")
    assert not (tmp_path / "nowhere").exists()


def test_hardlink_target_is_rebound_not_written_through(write: _Write, tmp_path: Path) -> None:
    outside = tmp_path / "outside.md"
    write_text(outside, "original\n")
    target = tmp_path / "linked.md"
    os.link(outside, target)
    before = target.stat().st_ino
    write(target, "REBOUND\n")
    assert read_text(outside) == "original\n"
    assert target.stat().st_ino != before


def test_none_removes_a_file_and_leaves_a_missing_parent_missing(
    full: _Write, tmp_path: Path
) -> None:
    target = tmp_path / "state.json"
    target.write_bytes(b"previous")
    full(target, None)
    full(tmp_path / "missing" / "state.json", None)
    assert [p.name for p in tmp_path.iterdir()] == []


@pytest.mark.parametrize("content", ["new\n", None], ids=["text", "none"])
def test_a_junction_is_refused_and_untouched_through_every_door(
    write: _Write, tmp_path: Path, content: str | None, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "junction"
    write_text(target, "keep\n")
    monkeypatch.setattr(Path, "is_junction", lambda self: self == target)
    with pytest.raises(SymlinkRefusedError):
        write(target, content)
    assert read_text(target) == "keep\n"


@pytest.mark.parametrize("content", ["new\n", None], ids=["text", "none"])
def test_symlinked_path_is_refused_and_untouched_through_every_door(
    write: _Write, tmp_path: Path, content: str | None
) -> None:
    target = tmp_path / "target.txt"
    write_text(target, "keep\n")
    link = tmp_path / "link.txt"
    _symlink(link, target)
    with pytest.raises(SymlinkRefusedError):
        write(link, content)
    assert is_link(link) and read_text(target) == "keep\n"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["link.txt", "target.txt"]


@pytest.mark.parametrize("existing", [True, False], ids=["existing-target", "new-target"])
@pytest.mark.parametrize("failure_point", ["create_fails", "write_fails", "replace_fails"])
@pytest.mark.parametrize(
    ("content", "kwargs"),
    [("hello\n", {}), ("hello\n", {"newline": None, "preserve_mode": True}), (b"hello\n", {"preserve_mode": True})],
    ids=["text", "text-newline-none-mode", "binary-mode"],
)  # fmt: skip
def test_no_temp_sibling_survives_any_injected_failure(
    write: _Write, content: str | bytes, kwargs: dict[str, object], failure_point: str,
    existing: bool, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:  # fmt: skip
    if isinstance(content, bytes) and write is _ledger_replace:
        pytest.skip("the ledger door writes text only")
    target = tmp_path / "atom.md"
    if existing:
        write_text(target, "original\n")
    method = "write_bytes" if isinstance(content, bytes) else "write_text"

    def boom(self: Path, *args: object, **kw: object) -> None:
        if failure_point == "write_fails":  # bytes land on disk, then the write raises
            _REAL[method](self, *args, **kw)  # type: ignore[operator]
        raise OSError("injected failure")

    monkeypatch.setattr(*((os, "replace", boom) if failure_point == "replace_fails" else (Path, method, boom)))  # fmt: skip
    with pytest.raises(OSError, match="injected failure"):
        write(target, content, **kwargs)
    assert [p.name for p in tmp_path.iterdir()] == (["atom.md"] if existing else [])
    assert not existing or read_text(target) == "original\n"


def test_permission_error_retries_the_swap_on_a_fake_clock_through_every_door(
    write: _Write, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dest, real = tmp_path / "a.txt", os.replace
    naps: list[float] = []
    calls: list[int] = []

    def flaky(src: str, dst: str) -> None:
        calls.append(1)
        if len(calls) <= 2:
            raise PermissionError("held open")
        real(src, dst)

    monkeypatch.setattr(os, "replace", flaky)
    monkeypatch.setattr(time, "sleep", naps.append)
    write(dest, "new\n")
    assert (len(calls), naps) == (3, [0.01, 0.01])
    assert read_text(dest) == "new\n"
    assert [p.name for p in tmp_path.iterdir()] == ["a.txt"]


def test_one_exception_class_for_every_import_path(atomic: ModuleType) -> None:
    assert SymlinkRefusedError is atomic.SymlinkRefusedError
    ledger = load_owner("dd-bug-resolution", "_ledger")
    assert ledger.replace.__module__ == "_ledger"


def test_bugs_append_into_a_symlinked_ledger_exits_1_with_one_fix_line(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "cli").mkdir(parents=True)
    write_text(repo / "cli" / "x.py", "x = 1\n")
    run(["git", "init", "-q", str(repo)], check=True)
    run(["git", "-C", str(repo), "add", "cli"], check=True)
    real = tmp_path / "real.jsonl"
    write_text(real, "")
    (repo / "specs" / "bugs").mkdir(parents=True)
    _symlink(repo / "specs" / "bugs" / "BUGS.jsonl", real)
    argv = ["append", "--specs", str(repo / "specs"), "--bug-id", "x", "--title", "t",
            "--severity", "LOW", "--surface", "cli", "--component", "c", "--context", "c",
            "--symptom", "s", "--repro", "r", "--expected", "e", "--correlates", "none"]  # fmt: skip
    done = run([sys.executable, "-B", str(_BUGS), *argv], check=False, cwd=tmp_path)
    assert done.returncode == 1, done.stdout + done.stderr
    assert "[error]" in done.stderr
    assert sum(line.lstrip().startswith("fix:") for line in done.stderr.splitlines()) == 1
    assert read_text(real) == ""
    assert is_link(repo / "specs" / "bugs" / "BUGS.jsonl")


def _child(code: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    env = load_owner("dd-bug-resolution", "_git").scrubbed_env() | {"PYTHONPATH": str(_ROOT)}
    return run([sys.executable, "-B", "-c", code], check=False, cwd=cwd, env=env)


def test_a_planted_atomic_in_the_cwd_is_never_loaded(tmp_path: Path) -> None:
    """CWE-427: ``-c`` puts the cwd first on ``sys.path``; the loader still runs the packaged file."""
    write_text(tmp_path / "_atomic.py", "raise SystemExit('PLANTED')\n")
    done = _child(
        "from dadaia_workspace.core.skill_owner import load_owner as l;"
        "print(l('dd-bug-resolution', '_atomic').__file__)",
        tmp_path,
    )
    assert done.returncode == 0, done.stderr
    assert done.stdout.strip() == str(_SKILLS / "dd-bug-resolution" / "scripts" / "_atomic.py")


def test_a_call_through_load_owner_leaves_no_pycache(tmp_path: Path) -> None:
    """Only the bytecode THIS call writes counts: earlier runs may leave their own."""
    done = _child(
        "from pathlib import Path;"
        "from dadaia_workspace.core.skill_owner import load_owner as l;"
        f"pyc = lambda: set(Path({str(_SKILLS)!r}).rglob('*.pyc'));"
        "before = pyc();"
        "m = l('dd-bug-resolution', '_atomic');"
        f"m.atomic_write(Path({str(tmp_path / 'o.txt')!r}), 'ok');"
        "print(sorted(str(p) for p in pyc() - before))",
        tmp_path,
    )
    assert done.returncode == 0, done.stderr
    assert done.stdout.strip() == "[]"
    assert read_text(tmp_path / "o.txt") == "ok"


def _linked(tmp_path: Path) -> tuple[Path, Path]:
    target = tmp_path / "target.txt"
    write_text(target, "keep\n")
    link = tmp_path / "link.txt"
    _symlink(link, target)
    return link, target


def test_symlinked_path_is_refused_and_untouched(atomic: ModuleType, tmp_path: Path) -> None:
    link, target = _linked(tmp_path)
    with pytest.raises(SymlinkRefusedError):
        atomic.atomic_write(link, "new\n")
    assert is_link(link) and link.resolve() == target
    assert read_text(target) == "keep\n"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["link.txt", "target.txt"]


def test_ledger_replace_raises_the_core_class(tmp_path: Path) -> None:
    link, target = _linked(tmp_path)
    with pytest.raises(SymlinkRefusedError):
        load_owner("dd-bug-resolution", "_ledger").replace(link, "new\n")
    assert read_text(target) == "keep\n" and is_link(link)


def test_no_temp_sibling_survives_a_failed_swap(
    atomic: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dest = tmp_path / "a.txt"
    write_text(dest, "old")

    def boom(src: object, dst: object) -> None:
        raise OSError("injected")

    monkeypatch.setattr(os, "replace", boom)
    with pytest.raises(OSError, match="injected"):
        atomic.atomic_write(dest, "new")
    assert [p.name for p in tmp_path.iterdir()] == ["a.txt"]
    assert read_text(dest) == "old"


def test_permission_error_retries_the_swap_on_a_fake_clock(
    atomic: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dest, real, naps, calls = tmp_path / "a.txt", os.replace, [], []

    def flaky(src: object, dst: object) -> None:
        calls.append(1)
        if len(calls) <= 2:
            raise PermissionError("held open")
        real(src, dst)

    monkeypatch.setattr(os, "replace", flaky)
    monkeypatch.setattr(time, "sleep", naps.append)
    atomic.atomic_write(dest, "new\n")
    assert (len(calls), naps) == (3, [0.01, 0.01])
    assert read_text(dest) == "new\n"
    assert [p.name for p in tmp_path.iterdir()] == ["a.txt"]


def test_preserve_mode_and_ensure_parent(atomic: ModuleType, tmp_path: Path) -> None:
    dest = tmp_path / "a.txt"
    mode = _moded(dest, "old")
    atomic.atomic_write(dest, "new", preserve_mode=True)
    assert (stat.S_IMODE(dest.stat().st_mode), read_text(dest)) == (mode, "new")
    deep = tmp_path / "x" / "y" / "b.txt"
    with pytest.raises(FileNotFoundError):
        atomic.atomic_write(deep, "b")
    atomic.atomic_write(deep, "b", ensure_parent=True)
    assert read_text(deep) == "b"
