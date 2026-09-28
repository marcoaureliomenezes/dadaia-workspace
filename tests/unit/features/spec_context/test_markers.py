"""``spec_context.markers`` — the ONE mtime-throttle-marker idiom (0.4.7 c5 T-047-41).

Intent: CONTRACT — sa-tool-caches-land-outside-the-cache-zone#B40-4: a marker sits at
.dadaia/tmp/hooks/<name> (ADR 0080), never flat at the tmp root.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.features.spec_context import markers

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("stamp", "age", "throttled"), [(True, 5, True), (True, 31, False), (False, 0, False)]
)
def test_a_marker_throttles_only_within_its_window(
    tmp_path: Path, stamp: bool, age: int, throttled: bool
) -> None:
    marker = tmp_path / ".dadaia" / "tmp" / "hooks" / "reconciler-last-sess1"
    if stamp:
        markers.stamp_throttle(tmp_path, "reconciler-last-sess1")
        assert marker.is_file() and not (tmp_path / ".dadaia" / "tmp" / marker.name).exists()
    now = marker.stat().st_mtime + age if stamp else 0.0
    assert (
        markers.throttled(tmp_path, "reconciler-last-sess1", window_seconds=30, now=now)
        is throttled
    )


def test_throttled_rejects_traversal_shaped_marker_name(tmp_path: Path) -> None:
    hostile = "../../../escape-probe"
    markers.stamp_throttle(tmp_path, hostile)
    assert not (tmp_path / "escape-probe").exists()
    assert markers.throttled(tmp_path, hostile, window_seconds=300, now=0.0) is False
