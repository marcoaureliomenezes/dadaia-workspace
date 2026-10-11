"""J1.T3 (rc-14, ADR 0246, AC11.3): the one atomic writer of ``dd-bug-resolution/scripts/_atomic.py``.

Design seam for J1.T4 (this file is the contract; T4 makes it green):

* ``_atomic.py`` public names: ``atomic_write(path, content, *, preserve_mode=False,
  newline="", ensure_parent=False)`` and ``SymlinkRefusedError`` (``OSError``; ``.path``).
  It is the union of ``core/atomic_write.py`` (symlink refusal, uuid temp, ``preserve_mode``,
  ``ensure_parent``, unconditional temp cleanup) and ``_ledger.replace`` (the Windows
  ``PermissionError`` retry, 49 retries 0.01 s apart before the final raising swap).
* Core delegates through ``core.skill_owner.load_owner('dd-bug-resolution', '_atomic')``:
  ``core/atomic_write.py`` becomes a shim that re-exports ``atomic_write`` and
  ``SymlinkRefusedError`` from that one module object; ``_ledger.replace`` calls it too (T11).
* The exception class has a single home, ``_atomic.SymlinkRefusedError``; the core name is
  that same object, so one ``except`` catches the raise from either import path.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from types import ModuleType

import pytest

from dadaia_workspace.core.atomic_write import SymlinkRefusedError
from dadaia_workspace.core.skill_owner import load_owner

_ROOT = Path(__file__).resolve().parents[5]
_SKILLS = _ROOT / "dadaia_workspace" / "public" / "skills"
_BUGS = _SKILLS / "dd-bug-resolution" / "scripts" / "bugs.py"


@pytest.fixture
def atomic() -> ModuleType:
    return load_owner("dd-bug-resolution", "_atomic")


def _linked(tmp_path: Path) -> tuple[Path, Path]:
    target = tmp_path / "target.txt"
    target.write_text("keep\n", encoding="utf-8")
    link = tmp_path / "link.txt"
    link.symlink_to(target)
    return link, target


@pytest.mark.skipif(sys.platform == "win32", reason="symlink creation needs a privilege")
def test_symlinked_path_is_refused_and_untouched(atomic: ModuleType, tmp_path: Path) -> None:
    link, target = _linked(tmp_path)
    with pytest.raises(SymlinkRefusedError):
        atomic.atomic_write(link, "new\n")
    assert link.is_symlink() and link.resolve() == target
    assert target.read_text(encoding="utf-8") == "keep\n"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["link.txt", "target.txt"]


def test_one_exception_class_for_every_import_path(atomic: ModuleType) -> None:
    assert SymlinkRefusedError is atomic.SymlinkRefusedError
    ledger = load_owner("dd-bug-resolution", "_ledger")
    assert ledger.replace.__module__ == "_ledger"


@pytest.mark.skipif(sys.platform == "win32", reason="symlink creation needs a privilege")
def test_ledger_replace_raises_the_core_class(tmp_path: Path) -> None:
    link, target = _linked(tmp_path)
    with pytest.raises(SymlinkRefusedError):
        load_owner("dd-bug-resolution", "_ledger").replace(link, "new\n")
    assert target.read_text(encoding="utf-8") == "keep\n" and link.is_symlink()


@pytest.mark.skipif(sys.platform == "win32", reason="symlink creation needs a privilege")
def test_bugs_append_into_a_symlinked_ledger_exits_1_with_one_fix_line(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "cli").mkdir(parents=True)
    (repo / "cli" / "x.py").write_text("x = 1\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "add", "cli"], check=True)
    real = tmp_path / "real.jsonl"
    real.write_text("", encoding="utf-8")
    (repo / "specs" / "bugs").mkdir(parents=True)
    (repo / "specs" / "bugs" / "BUGS.jsonl").symlink_to(real)
    argv = ["append", "--specs", str(repo / "specs"), "--bug-id", "x", "--title", "t",
            "--severity", "LOW", "--surface", "cli", "--component", "c", "--context", "c",
            "--symptom", "s", "--repro", "r", "--expected", "e", "--correlates", "none"]  # fmt: skip
    done = subprocess.run(
        [sys.executable, "-B", str(_BUGS), *argv],
        capture_output=True,
        text=True,
        check=False,
        cwd=tmp_path,
    )
    assert done.returncode == 1, done.stdout + done.stderr
    assert "Error:" in done.stderr
    assert sum(line.lstrip().startswith("fix:") for line in done.stderr.splitlines()) == 1
    assert real.read_text(encoding="utf-8") == ""
    assert (repo / "specs" / "bugs" / "BUGS.jsonl").is_symlink()


def test_no_temp_sibling_survives_a_failed_swap(
    atomic: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dest = tmp_path / "a.txt"
    dest.write_text("old", encoding="utf-8")

    def boom(src: object, dst: object) -> None:
        raise OSError("injected")

    monkeypatch.setattr(os, "replace", boom)
    with pytest.raises(OSError, match="injected"):
        atomic.atomic_write(dest, "new")
    assert [p.name for p in tmp_path.iterdir()] == ["a.txt"]
    assert dest.read_text(encoding="utf-8") == "old"


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
    assert dest.read_text(encoding="utf-8") == "new\n"
    assert [p.name for p in tmp_path.iterdir()] == ["a.txt"]


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX modes")
def test_preserve_mode_and_ensure_parent(atomic: ModuleType, tmp_path: Path) -> None:
    dest = tmp_path / "a.txt"
    dest.write_text("old", encoding="utf-8")
    dest.chmod(0o640)
    atomic.atomic_write(dest, "new", preserve_mode=True)
    assert (dest.stat().st_mode & 0o777, dest.read_text(encoding="utf-8")) == (0o640, "new")
    deep = tmp_path / "x" / "y" / "b.txt"
    with pytest.raises(FileNotFoundError):
        atomic.atomic_write(deep, "b")
    atomic.atomic_write(deep, "b", ensure_parent=True)
    assert deep.read_text(encoding="utf-8") == "b"


def _child(code: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "PYTHONPATH": str(_ROOT), "PYTHONDONTWRITEBYTECODE": "1"}
    return subprocess.run(
        [sys.executable, "-B", "-c", code],
        capture_output=True,
        text=True,
        check=False,
        cwd=cwd,
        env=env,
    )


def test_a_planted_atomic_in_the_cwd_is_never_loaded(tmp_path: Path) -> None:
    """CWE-427: ``-c`` puts the cwd first on ``sys.path``; the loader still runs the packaged file."""
    (tmp_path / "_atomic.py").write_text("raise SystemExit('PLANTED')\n", encoding="utf-8")
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
    assert (tmp_path / "o.txt").read_text(encoding="utf-8") == "ok"
