"""The guard matrix over the ONE traversal primitive (0.4.7 FR6a, T-047-19).

Intent: CONTRACT — 0.4.7 FR6 / T-047-19. Size: SMALL (unit).

Structural cause this suite pins: the five per-call-site guards in ``doctor.py``
(``_entries``, ``_mtime``, ``_remove``, ``_guarded``, ``_remove_dead_repo``) each
re-derived "may I touch this?" and disagreed — the bug family from
``doctor-ptr-gc-deletes-valid-lock-free-bind`` (direct deletion on a per-site rule)
through ``doctor-scan-raises-when-a-ttl-entry-vanishes-mid-walk`` and
``doctor-fix-aborts-whole-pass-on-first-undeletable-entry``. One guard, one home.
"""

from __future__ import annotations

import getpass
import os
import shutil
from collections.abc import Callable
from pathlib import Path

import pytest

from dadaia_workspace.features.spec_context import sweep


def _tree(root: Path, *, read_only: bool = False) -> Path:
    tree = root / "cache" / "mod"
    (tree / "pkg").mkdir(parents=True)
    (tree / "pkg" / "go.mod").write_text("module x\n")
    for path in (tree / "pkg" / "go.mod", tree / "pkg", tree) if read_only else ():
        path.chmod(0o555 if path.is_dir() else 0o444)
    return tree


def _file(path: Path, *, mode: int = 0o644) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("x")
    path.chmod(mode)
    return path


def _outside_link(tmp: Path) -> Path:
    """`ws/link` -> `outside/` holding `treasure.txt`; returns ws."""
    (tmp / "outside").mkdir()
    (tmp / "outside" / "treasure.txt").write_text("x")
    (tmp / "ws").mkdir()
    (tmp / "ws" / "link").symlink_to(tmp / "outside", target_is_directory=True)
    return tmp / "ws"


def _walk_symlinked(tmp: Path) -> Path:
    _outside_link(tmp)
    return tmp / "ws" / "link"


def _walk_plain(tmp: Path) -> Path:
    (tmp / "b").write_text("b")
    (tmp / "a").mkdir()
    return tmp


# fmt: off
@pytest.mark.parametrize(("setup", "names"), [
    pytest.param(_walk_plain, ["a", "b"], id="sorted-entries"),
    pytest.param(_walk_symlinked, [], id="never-follows-a-symlinked-root"),
    pytest.param(lambda tmp: tmp / "nope", [], id="missing-dir-is-empty"),
])
# fmt: on
def test_walk_lists_only_a_real_directorys_sorted_entries(tmp_path: Path, setup: Callable[[Path], Path], names: list[str]) -> None:
    """A symlinked root would yield entries whose parent is inside the workspace, so the destination would be reaped."""
    assert [p.name for p in sweep.walk(setup(tmp_path))] == names


def test_guarded_turns_an_oserror_into_exactly_one_skipped_action() -> None:
    def boom() -> str | None:
        raise OSError(13, "Permission denied")

    [action] = sweep.guarded("WS-tmp-slop", "tmp/x", boom)
    assert action.startswith("WS-tmp-slop: skipped 'tmp/x' (errno 13")
    assert sweep.guarded("CODE", "path", lambda: None) == []


_SKIP = "skipped '{rel}' (outside the workspace)"


# fmt: off
@pytest.mark.parametrize(("setup", "rel", "message", "survivor"), [
    pytest.param(lambda t: (t, _file(t / "slop.txt")), "slop.txt", "deleted '{rel}'", None, id="file"),
    pytest.param(lambda t: (t, _tree(t)), "cache/mod", "deleted '{rel}'", None, id="tree"),
    pytest.param(lambda t: (t, _tree(t, read_only=True)), "cache/mod", "deleted '{rel}'", None, id="doctor-reaper-cannot-delete-read-only-trees"),
    pytest.param(lambda t: (t, _file(t / "go.sum", mode=0o444)), "go.sum", "deleted '{rel}'", None, id="read-only-file"),
    pytest.param(lambda t: (_outside_link(t), t / "ws" / "link"), "link", "deleted '{rel}'", "outside/treasure.txt", id="symlink-unlinked-destination-kept"),
    pytest.param(lambda t: ((t / "ws").mkdir() or t / "ws", _file(t / "elsewhere.txt")), "elsewhere.txt", _SKIP, "elsewhere.txt", id="outside-the-workspace-skipped"),
    pytest.param(lambda t: (t, t / "ghost"), "ghost", None, None, id="already-gone-reports-nothing"),
])
# fmt: on
def test_remove_deletes_a_read_only_tree(
    tmp_path: Path, setup: Callable[[Path], tuple[Path, Path]], rel: str, message: str | None, survivor: str | None
) -> None:
    """sa-reaper-destroys-its-own-hold-before-ttl#B3: the reaper owns what it reaps — a read-only tree or
    file (a Go module cache is dr-xr-xr-x all the way down; Windows refuses a read-only unlink) is made
    writable on the way down, then removed; a symlink goes, its destination never; outside is never touched."""
    workspace, target = setup(tmp_path)
    done = sweep.remove(workspace, target, rel)
    assert done == (message and message.format(rel=rel))
    assert isinstance(done, sweep.Skipped) is (message == _SKIP) and sweep.succeeded(done) is (message not in (None, _SKIP))
    assert not target.is_symlink() and (target.exists() == (survivor == rel))
    assert survivor is None or (tmp_path / survivor).exists()


@pytest.mark.skipif(os.name == "nt" or os.geteuid() == 0, reason="POSIX dir permissions; root bypasses them")
def test_an_expired_entry_another_account_holds_names_the_one_operator_act(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Intent: CONTRACT — doctor-tmp-expiry-foreign-owned-entry-never-clears: the TTL delete
    act that cannot lift a permission (chmod refused: not the owner) skips naming the owner
    and `Operator action: remove <the expired entry>`; once the operator removed it, the
    act has nothing left to report, so the finding clears."""
    entry = tmp_path / ".dadaia" / "tmp" / "a" / "20200101"
    (held := entry / "x" / "dist").mkdir(parents=True)
    (held / "f.whl").write_text("w", encoding="utf-8")
    held.chmod(0o555)
    monkeypatch.setattr(sweep.os, "chmod", _not_the_owner)

    done = sweep.remove(tmp_path, entry, "tmp/a/20200101")

    assert done == (
        "skipped 'tmp/a/20200101' (errno 13: Permission denied) — it holds an entry owned by "
        f"{getpass.getuser()}; Operator action: remove {tmp_path}/.dadaia/tmp/a/20200101"
    )
    assert isinstance(done, sweep.Skipped) and entry.exists()
    monkeypatch.undo()
    held.chmod(0o755)
    shutil.rmtree(entry)  # the operator's act
    assert sweep.remove(tmp_path, entry, "tmp/a/20200101") is None


def _not_the_owner(*_: object) -> None:
    raise PermissionError(1, "Operation not permitted")


def _exdev(a: object, b: object) -> None:
    raise OSError(18, "Invalid cross-device link")


# fmt: off
@pytest.mark.parametrize(("src", "dest", "message", "exdev"), [
    pytest.param("ws/repos/x/.pytest_cache/v", "ws/.dadaia/reaped/20260913/repos/x/.pytest_cache/v",
                 "moved 'rel' -> '.dadaia/reaped/20260913/repos/x/.pytest_cache/v'", False, id="B4-relocates-and-creates-parents"),
    pytest.param("ws/slop.txt", "ws/reaped/slop.txt", "moved 'rel' -> 'reaped/slop.txt'", True, id="B4-cross-device-copy-plus-remove-in-one-place"),
    pytest.param("elsewhere.txt", "ws/reaped/e", "skipped 'rel' (outside the workspace)", False, id="B8-source-outside-skipped"),
    pytest.param("ws/slop.txt", "escape.txt", "skipped 'rel' (outside the workspace)", False, id="B8-destination-outside-skipped"),
])
# fmt: on
def test_move_holds_the_content_inside_the_workspace_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, src: str, dest: str, message: str, exdev: bool
) -> None:
    """sa-reaper-destroys-its-own-hold-before-ttl#B4 (the moved content is held; EXDEV handled in ONE place,
    a failed move is never a partial delete) and #B8 (the mover never touches a path outside the workspace)."""
    workspace = (tmp_path / "ws")
    workspace.mkdir(exist_ok=True)
    source = _file(tmp_path / src)
    if exdev:
        monkeypatch.setattr(sweep.os, "replace", _exdev)
    done = sweep.move(workspace, source, tmp_path / dest, "rel")
    moved = message.startswith("moved")
    assert done == message and isinstance(done, sweep.Skipped) is (not moved) and sweep.succeeded(done) is moved
    assert (source.exists(), (tmp_path / dest).exists()) == (not moved, moved)
    assert not moved or (tmp_path / dest).read_text() == "x"


def test_move_resets_the_ttl_clock_and_never_follows_a_symlinked_source(tmp_path: Path) -> None:
    """sa-reaper-destroys-its-own-hold-before-ttl#B3: the reaped clock starts at the move, never at the
    origin's mtime (FR6b); #B4: a symlink is moved, its destination never."""
    workspace = _outside_link(tmp_path)
    old = _file(workspace / "old")
    os.utime(old, (0, 0))
    sweep.move(workspace, old, workspace / "reaped" / "old", "old")
    sweep.move(workspace, workspace / "link", workspace / "reaped" / "link", "link")
    assert (workspace / "reaped" / "old").lstat().st_mtime > 1_000_000_000
    assert (workspace / "reaped" / "link").is_symlink()
    assert (tmp_path / "outside" / "treasure.txt").exists()


# ═════════════════════════════════════════════════════════════════════════════════
# The CRITICAL bug's repro, over the primitive (doctor-ptr-gc-deletes-valid-lock-free-bind).
# ═════════════════════════════════════════════════════════════════════════════════


def test_a_live_bind_record_survives_a_full_doctor_fix_pass(tmp_path: Path) -> None:
    """Intent: CONTRACT — bug doctor-ptr-gc-deletes-valid-lock-free-bind. Size: SMALL.

    Bind, run ``fix()``, resolve the session again: the bind is intact. The original
    CRITICAL deleted live bind state because a per-call-site rule inferred deadness from
    the absence of a lock. There is no per-site deletion left: ``sessions/`` carries no
    TTL, so no verdict ever names it, and every filesystem act goes through one guard.
    """
    from datetime import UTC, datetime

    from dadaia_workspace.core import session_store, workspace_layout
    from dadaia_workspace.core.workspace_layout import provisioned_zones
    from dadaia_workspace.features.spec_context.doctor import DoctorService

    dadaia = tmp_path / ".dadaia"
    for zone in provisioned_zones():
        (dadaia / zone.name).mkdir(parents=True, exist_ok=True)
    (tmp_path / workspace_layout.DADAIAIGNORE).write_text("", encoding="utf-8")

    now = datetime.now(tz=UTC).isoformat().replace("+00:00", "Z")
    record = session_store.new_binding_record(
        session_id="sess-1", context="ctx-a", runtime="claude-code", pid=os.getpid(), now=now
    )
    session_store.write_session(tmp_path, "sess-1", record)

    class _Store:
        def list_all(self) -> list[object]:
            return []

        def get(self, name: str) -> None:
            return None

    DoctorService(_Store(), None, tmp_path).fix()  # type: ignore[arg-type]

    assert session_store.live_session(tmp_path, "sess-1") is not None
    assert session_store.read_session(tmp_path, "sess-1") == record
