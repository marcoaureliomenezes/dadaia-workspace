"""Named one-off migrations that ``install()`` still runs unconditionally.

K3 (v0.5.1): ``copy_tree``/``copy_file``/``write_generated`` (the pre-K3 file-copy
utilities this file used to pin) are retired — every projected file now flows through
the ``ProjectionRule``/``install_rules`` seam (``tests/unit/infrastructure/
test_projection.py`` covers its skip/overwrite/force contract). What remains here is
the one migration helper with no ``ProjectionRule`` equivalent: it deletes orphan
STATE, not a projected file.

Intent: CONTRACT — v0.5.0 F-09 (marker subsystem deletion cleanup).
"""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.infrastructure.install_helpers import remove_legacy_bind_epoch_state


def test_remove_legacy_bind_epoch_state_sweeps_orphan_markers(tmp_path: Path) -> None:
    """F-09 (v0.5.0 six-axis review): the marker subsystem is deleted, so leftover
    ``.dadaia/states/bind_epoch/`` markers are orphan state — the named migration
    sweeps the files and the dir, and is a no-op when the dir is absent."""
    ws = tmp_path / "ws"
    epoch = ws / ".dadaia" / "states" / "bind_epoch"
    epoch.mkdir(parents=True)
    (epoch / "demo").write_text("12345\n", encoding="utf-8")
    installed: list[str] = []
    remove_legacy_bind_epoch_state(ws, installed)
    assert not epoch.exists()
    assert any(line.startswith("[rm] ") and "bind_epoch" in line for line in installed)

    # Absent dir: silent no-op.
    installed2: list[str] = []
    remove_legacy_bind_epoch_state(ws, installed2)
    assert installed2 == []
