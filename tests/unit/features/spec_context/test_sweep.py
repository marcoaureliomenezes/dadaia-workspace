"""The guard matrix over the ONE traversal primitive (0.4.7 FR6a, T-047-19).

Structural cause this suite pins: the five per-call-site guards in ``doctor.py``
(``_entries``, ``_mtime``, ``_remove``, ``_guarded``, ``_remove_dead_repo``) each
re-derived "may I touch this?" and disagreed — the bug family from
``doctor-ptr-gc-deletes-valid-lock-free-bind`` (direct deletion on a per-site rule)
through ``doctor-scan-raises-when-a-ttl-entry-vanishes-mid-walk`` and
``doctor-fix-aborts-whole-pass-on-first-undeletable-entry``. One guard, one home.
"""

from __future__ import annotations

import os
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
    expected = message and message.format(rel=rel)
    assert done == (sweep.Skipped(_SKIP.format(rel=rel)) if message == _SKIP else expected)
    assert bool(done) is (message not in (None, _SKIP))
    assert not target.is_symlink() and (target.exists() == (survivor == rel))
    assert survivor is None or (tmp_path / survivor).exists()


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
    assert done == (message if moved else sweep.Skipped(message)) and bool(done) is moved
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
    """bug doctor-ptr-gc-deletes-valid-lock-free-bind. Size: SMALL.

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


# ═════════════════════════════════════════════════════════════════════════════════
# rc-9 AC3.3: the delete act is judged by its outcome; a refusal is falsy (rows 6, 21, 22).
# ═════════════════════════════════════════════════════════════════════════════════


def _rmtree_leaving(error: OSError | None) -> Callable[..., None]:
    """``shutil.rmtree`` that deletes nothing: silent, as 3.14's swallowed retry (row 6), or
    reporting *error* to its ``onexc`` (row 22)."""

    def rmtree(path: str, *, onexc: Callable[..., object]) -> None:
        if error is not None:
            onexc(os.rmdir, path, error)

    return rmtree


# fmt: off
@pytest.mark.parametrize(("error", "line"), [
    pytest.param(None, "skipped 'tmp/x'", id="row6-silent-failure-judged-by-occupied"),
    pytest.param(OSError(39, "Directory not empty"), "skipped 'tmp/x' (errno 39: Directory not empty)", id="row22-no-operator-act-off-a-permission"),
])
# fmt: on
def test_a_surviving_target_is_refused_by_its_outcome(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, error: OSError | None, line: str
) -> None:
    target = _file(tmp_path / "tmp" / "x" / "f.txt").parent
    monkeypatch.setattr(sweep.shutil, "rmtree", _rmtree_leaving(error))

    done = sweep.remove(tmp_path, target, "tmp/x")

    assert done == sweep.Skipped(line) and not done
    assert target.is_dir()


def test_a_refusal_is_falsy_and_no_str(tmp_path: Path) -> None:
    """U2: no caller can read a refusal as an act — not by truth value, not as a ``str``."""
    workspace = _outside_link(tmp_path)

    done = sweep.remove(workspace, tmp_path / "outside" / "treasure.txt", "treasure")

    assert done == sweep.Skipped("skipped 'treasure' (outside the workspace)")
    assert not done and not isinstance(done, str)


def test_move_returns_its_failure_as_a_refusal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """U2 / row 27: a failed ``os.replace`` (not EXDEV) is the act's refusal, never raised."""
    source = _file(tmp_path / "slop.txt")
    monkeypatch.setattr(sweep.os, "replace", _not_the_owner)

    done = sweep.move(tmp_path, source, tmp_path / "reaped" / "slop.txt", "slop.txt")

    assert done == sweep.Skipped("skipped 'slop.txt' (errno 1: Operation not permitted)")
    assert source.read_text() == "x"


@pytest.mark.skipif(os.name == "nt" or os.geteuid() == 0, reason="POSIX dir permissions; root bypasses them")
def test_a_permission_failure_names_the_recorded_entry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Row 21: the refusal names the entry the retry could not lift, recorded by this call."""
    entry = tmp_path / ".dadaia" / "tmp" / "a" / "20200101"
    (held := entry / "x" / "dist").mkdir(parents=True)
    (held / "f.whl").write_text("w", encoding="utf-8")
    held.chmod(0o555)
    monkeypatch.setattr(sweep.os, "chmod", _not_the_owner)
    try:
        done = sweep.remove(tmp_path, entry, "tmp/a/20200101")
    finally:
        monkeypatch.undo()
        held.chmod(0o755)

    assert str(done) == (
        f"skipped 'tmp/a/20200101' (errno 13: Permission denied) — {held}/f.whl sits in a "
        f"directory owned by {held.owner()}; Operator action: remove {entry}"
    )
    assert not done and (held / "f.whl").exists()


@pytest.mark.skipif(os.utime not in os.supports_follow_symlinks, reason="a link's own mtime is POSIX-only")
def test_a_root_level_held_symlink_keeps_its_hold_clock(tmp_path: Path) -> None:
    """Row 26 (ADR 0074): a root-level hold is its own clock, a symlink's included."""
    (tmp_path / "link").symlink_to(tmp_path / "nowhere")
    os.utime(tmp_path / "link", (0, 0), follow_symlinks=False)

    sweep.hold(tmp_path, tmp_path / "link", "link")

    [held] = (tmp_path / ".dadaia" / "reaped").glob("*/link")
    assert held.lstat().st_mtime > 1_000_000_000


# fmt: off
@pytest.mark.parametrize(("gitdir", "message"), [
    pytest.param("/repo/.git/worktrees/wt", "skipped 'tree' (holds a linked git worktree)", id="linked-worktree-skipped"),
    pytest.param("../.git/modules/sub", "deleted 'tree'", id="row24-submodule-is-no-worktree"),
])
# fmt: on
def test_only_a_gitdir_under_worktrees_marks_a_linked_worktree(tmp_path: Path, gitdir: str, message: str) -> None:
    """rc-9 AC3.6 row 24: a submodule's ``.git`` file names a relative gitdir that moves
    with its repo; only ``<common>/worktrees/<name>`` is a linked worktree."""
    tree = tmp_path / "tree"
    _file(tree / "sub" / ".git").write_text(f"gitdir: {gitdir}\n")

    done = sweep.remove(tmp_path, tree, "tree")

    assert str(done) == message


def test_n_moves_to_one_destination_make_n_holds(tmp_path: Path) -> None:
    """ADR 0074: an occupied destination yields the first free ``<name>-N`` beside it."""
    for _ in range(3):
        sweep.move(tmp_path, _file(tmp_path / "slop.txt"), tmp_path / "reaped" / "slop.txt", "slop")

    assert sorted(p.name for p in (tmp_path / "reaped").iterdir()) == ["slop.txt", "slop.txt-1", "slop.txt-2"]


@pytest.mark.skipif(os.name == "nt" or os.geteuid() == 0, reason="POSIX dir permissions; root bypasses them")
def test_an_unopenable_subdirectory_is_refused_never_raised(tmp_path: Path) -> None:
    """Rows 21/22: a 0o000 subdirectory fails ``os.open`` inside the walk; that failure is
    recorded and judged by the outcome, never re-called without its flags."""
    entry = tmp_path / "tmp" / "a" / "20200101"
    (locked := entry / "x").mkdir(parents=True)
    _file(locked / "f.txt")
    locked.chmod(0o000)

    done = sweep.remove(tmp_path, entry, "tmp/a/20200101")

    assert str(done) == (
        f"skipped 'tmp/a/20200101' (errno 13: Permission denied) — {locked} sits in a "
        f"directory owned by {entry.owner()}; Operator action: remove {entry}"
    )
    assert not done and (locked / "f.txt").exists()


def test_a_nested_hold_stamps_its_top_entry(tmp_path: Path) -> None:
    """ADR 0074: a hold of ``a/b/c`` restarts the clock of ``reaped/<day>/a``, not of ``a/b``."""
    _file(tmp_path / "a" / "b" / "c")
    sweep.hold(tmp_path, tmp_path / "a" / "b" / "c", "a/b/c")
    [top] = (tmp_path / ".dadaia" / "reaped").glob("*/a")
    _file(tmp_path / "a" / "b" / "c")
    os.utime(top, (0, 0))

    sweep.hold(tmp_path, tmp_path / "a" / "b" / "c", "a/b/c")

    assert top.stat().st_mtime > 1_000_000_000
