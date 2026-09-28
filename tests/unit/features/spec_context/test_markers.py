"""``spec_context.markers`` — the ONE mtime-throttle-marker idiom and its reaper
(0.4.7 c5 T-047-41: relocated out of ``presence`` so the reaper lane owns it)."""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.features.spec_context import markers

pytestmark = pytest.mark.unit


def test_stamp_then_throttled_within_window(tmp_path: Path) -> None:
    markers.stamp_throttle(tmp_path, "reconciler-last-sess1")
    now = (tmp_path / ".dadaia" / "tmp" / "hooks" / "reconciler-last-sess1").stat().st_mtime + 5
    assert markers.throttled(tmp_path, "reconciler-last-sess1", window_seconds=30, now=now)


def test_throttled_false_after_window_expires(tmp_path: Path) -> None:
    markers.stamp_throttle(tmp_path, "reconciler-last-sess1")
    now = (tmp_path / ".dadaia" / "tmp" / "hooks" / "reconciler-last-sess1").stat().st_mtime + 31
    assert not markers.throttled(tmp_path, "reconciler-last-sess1", window_seconds=30, now=now)


def test_throttled_false_when_marker_absent(tmp_path: Path) -> None:
    assert not markers.throttled(tmp_path, "reconciler-last-nobody", window_seconds=30, now=0.0)


def test_throttled_rejects_traversal_shaped_marker_name(tmp_path: Path) -> None:
    escape_probe = tmp_path / "escape-probe"
    hostile = f"../../../{escape_probe.name}"

    markers.stamp_throttle(tmp_path, hostile)

    assert not escape_probe.exists()
    assert markers.throttled(tmp_path, hostile, window_seconds=300, now=0.0) is False


def test_a_marker_lives_under_its_owner_dir_never_flat_in_tmp(tmp_path: Path) -> None:
    """sa-tool-caches-land-outside-the-cache-zone#B40-4: one placement rule — a throttle
    marker sits at .dadaia/tmp/hooks/<name> (ADR 0080), never flat at the tmp root."""
    markers.stamp_throttle(tmp_path, "reconciler-last-sess1")

    assert (tmp_path / ".dadaia" / "tmp" / "hooks" / "reconciler-last-sess1").is_file()
    assert not (tmp_path / ".dadaia" / "tmp" / "reconciler-last-sess1").exists()
