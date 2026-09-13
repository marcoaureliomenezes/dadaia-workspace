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

import os
from pathlib import Path

import pytest

from dadaia_workspace.features.spec_context import sweep


def test_walk_returns_the_sorted_entries_of_a_directory(tmp_path: Path) -> None:
    (tmp_path / "b").write_text("b")
    (tmp_path / "a").mkdir()
    assert [p.name for p in sweep.walk(tmp_path)] == ["a", "b"]


def test_walk_never_follows_a_symlinked_directory(tmp_path: Path) -> None:
    """A symlinked root would otherwise yield entries whose parent is inside the
    workspace, so every per-entry guard would pass and the destination be reaped."""
    real = tmp_path / "real"
    real.mkdir()
    (real / "treasure.txt").write_text("x")
    link = tmp_path / "link"
    link.symlink_to(real, target_is_directory=True)
    assert sweep.walk(link) == []


def test_walk_of_a_missing_or_unreadable_directory_is_empty(tmp_path: Path) -> None:
    assert sweep.walk(tmp_path / "nope") == []


def test_mtime_of_an_entry_that_vanished_is_absent_not_an_error(tmp_path: Path) -> None:
    assert sweep.mtime(tmp_path / "gone") is None
    present = tmp_path / "here"
    present.write_text("x")
    assert sweep.mtime(present) is not None


def test_mtime_reads_the_link_itself_never_its_destination(tmp_path: Path) -> None:
    link = tmp_path / "dangling"
    link.symlink_to(tmp_path / "absent")
    assert sweep.mtime(link) is not None


def test_guarded_turns_an_oserror_into_exactly_one_skipped_action() -> None:
    def boom() -> str | None:
        raise OSError(13, "Permission denied")

    actions = sweep.guarded("WS-tmp-slop", "tmp/x", boom)
    assert len(actions) == 1
    assert actions[0].startswith("WS-tmp-slop: skipped 'tmp/x' (errno 13")


def test_guarded_reports_nothing_when_the_step_has_nothing_to_report() -> None:
    assert sweep.guarded("CODE", "path", lambda: None) == []


def test_remove_deletes_a_file_inside_the_workspace(tmp_path: Path) -> None:
    victim = tmp_path / "slop.txt"
    victim.write_text("x")
    assert sweep.remove(tmp_path, victim, "slop.txt") == "deleted 'slop.txt'"
    assert not victim.exists()


def test_remove_deletes_a_directory_tree_inside_the_workspace(tmp_path: Path) -> None:
    victim = tmp_path / "slopdir"
    (victim / "deep").mkdir(parents=True)
    (victim / "deep" / "f").write_text("x")
    assert sweep.remove(tmp_path, victim, "slopdir") == "deleted 'slopdir'"
    assert not victim.exists()


def test_remove_unlinks_a_symlink_and_never_its_destination(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "treasure.txt").write_text("x")
    workspace = tmp_path / "ws"
    workspace.mkdir()
    link = workspace / "link"
    link.symlink_to(outside, target_is_directory=True)
    assert sweep.remove(workspace, link, "link") == "deleted 'link'"
    assert not link.is_symlink()
    assert (outside / "treasure.txt").exists()


def test_remove_skips_an_entry_whose_own_location_is_outside_the_workspace(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "ws"
    (workspace / "repos").mkdir(parents=True)
    stranger = tmp_path / "elsewhere.txt"
    stranger.write_text("x")
    assert sweep.remove(workspace, stranger, "elsewhere.txt") == (
        "skipped 'elsewhere.txt' (outside the workspace)"
    )
    assert stranger.exists()


def test_remove_of_an_entry_already_gone_reports_nothing(tmp_path: Path) -> None:
    assert sweep.remove(tmp_path, tmp_path / "ghost", "ghost") is None


def test_move_relocates_an_entry_and_creates_the_destination_parents(tmp_path: Path) -> None:
    src = tmp_path / "repos" / "x" / ".pytest_cache"
    src.mkdir(parents=True)
    (src / "v").write_text("x")
    dest = tmp_path / ".dadaia" / "reaped" / "20260913" / "repos" / "x" / ".pytest_cache"
    message = sweep.move(tmp_path, src, dest, "repos/x/.pytest_cache")
    assert message is not None
    assert "repos/x/.pytest_cache" in message
    assert not src.exists()
    assert (dest / "v").read_text() == "x"


def test_move_resets_the_ttl_clock_at_the_move(tmp_path: Path) -> None:
    """The reaped clock starts at the move, never at the origin's own mtime (FR6b)."""
    src = tmp_path / "old"
    src.write_text("x")
    os.utime(src, (0, 0))
    dest = tmp_path / ".dadaia" / "reaped" / "20260913" / "old"
    sweep.move(tmp_path, src, dest, "old")
    moved = sweep.mtime(dest)
    assert moved is not None
    assert moved > 1_000_000_000


def test_move_skips_a_source_outside_the_workspace(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    workspace.mkdir()
    stranger = tmp_path / "elsewhere.txt"
    stranger.write_text("x")
    assert sweep.move(workspace, stranger, workspace / "reaped" / "e", "elsewhere.txt") == (
        "skipped 'elsewhere.txt' (outside the workspace)"
    )
    assert stranger.exists()


def test_move_skips_a_destination_outside_the_workspace(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    workspace.mkdir()
    src = workspace / "slop.txt"
    src.write_text("x")
    assert sweep.move(workspace, src, tmp_path / "escape.txt", "slop.txt") == (
        "skipped 'slop.txt' (outside the workspace)"
    )
    assert src.exists()


def test_move_never_follows_a_symlinked_source(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "treasure.txt").write_text("x")
    workspace = tmp_path / "ws"
    workspace.mkdir()
    link = workspace / "link"
    link.symlink_to(outside, target_is_directory=True)
    sweep.move(workspace, link, workspace / "reaped" / "link", "link")
    assert (outside / "treasure.txt").exists()
    assert (workspace / "reaped" / "link").is_symlink()


def test_move_of_an_entry_already_gone_reports_nothing(tmp_path: Path) -> None:
    assert sweep.move(tmp_path, tmp_path / "ghost", tmp_path / "r" / "ghost", "ghost") is None


def test_a_cross_device_move_falls_back_to_copy_plus_remove_inside_the_primitive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """EXDEV is handled in ONE place; a failed move is never a partial delete."""
    src = tmp_path / "slop.txt"
    src.write_text("payload")

    def exdev(a: object, b: object) -> None:
        raise OSError(18, "Invalid cross-device link")

    monkeypatch.setattr(sweep.os, "replace", exdev)
    dest = tmp_path / "reaped" / "slop.txt"
    assert sweep.move(tmp_path, src, dest, "slop.txt") is not None
    assert dest.read_text() == "payload"
    assert not src.exists()


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
    from dadaia_workspace.core.workspace_layout import Creator, zones_created_by
    from dadaia_workspace.features.spec_context.doctor import DoctorService

    dadaia = tmp_path / ".dadaia"
    for zone in (*zones_created_by(Creator.INIT), *zones_created_by(Creator.INSTALL)):
        (dadaia / zone.name).mkdir(parents=True, exist_ok=True)
    (tmp_path / workspace_layout.INSTANCE_EXCEPTIONS).parent.mkdir(parents=True, exist_ok=True)

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
