"""Unit tests for the specs stamp writer and ``upgrade`` orchestration (FR-S02, FR-S05)."""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.core import specs_version as _version
from dadaia_workspace.core.gitflow import merge_frontmatter
from dadaia_workspace.features.migrate import upgrade as _upgrade
from dadaia_workspace.features.spec_context import sweep


def _write_constitution(specs_dir: Path, body: str) -> Path:
    specs_dir.mkdir(parents=True, exist_ok=True)
    path = specs_dir / "constitution.md"
    path.write_text(body, encoding="utf-8")
    return path


def test_write_version_creates_and_updates_stamp(tmp_path: Path) -> None:
    # Creates frontmatter on a bare file, preserving the body.
    specs = tmp_path / "specs"
    _write_constitution(specs, "# Constitution\n\nbody\n")
    merge_frontmatter(specs, specs_pattern_version=1)
    assert "specs_pattern_version: 1\n" in (specs / "constitution.md").read_text(encoding="utf-8")
    assert "# Constitution" in (specs / "constitution.md").read_text(encoding="utf-8")

    # Updates an existing stamp, preserving sibling frontmatter keys.
    specs2 = tmp_path / "specs2"
    _write_constitution(specs2, "---\nspecs_pattern_version: 0\nother: keep\n---\n# C\n")
    merge_frontmatter(specs2, specs_pattern_version=1)
    text = (specs2 / "constitution.md").read_text(encoding="utf-8")
    assert "specs_pattern_version: 1\n" in text
    assert "other: keep" in text


# ───────────────────────────── upgrade (FR-S05) ────────────────────────────────


def test_upgrade_refuses_below_floor_without_any_write(tmp_path: Path) -> None:
    """A-10.1: refusing a below-floor tree never touches the filesystem — no
    backup, no re-stamp, no migrated content."""
    specs = tmp_path / "specs"
    _write_constitution(specs, "# C\n")  # version 0, below the canonical floor

    with pytest.raises(_upgrade.UpgradeRefused):
        _upgrade.upgrade(specs, remove=lambda p: sweep.remove(specs, p, p.name), dry_run=True)
    with pytest.raises(_upgrade.UpgradeRefused):
        _upgrade.upgrade(specs, remove=lambda p: sweep.remove(specs, p, p.name), dry_run=False)

    assert not (tmp_path / "specs_bkp").exists()
    assert _version.state(specs)[0] == "foreign"


def test_upgrade_at_or_above_floor_is_idempotent_and_repairs_placeholders(
    tmp_path: Path,
) -> None:
    """A tree already at (or past) the canonical version is a no-op; re-running is stable.
    (Fixed law sections are the doctor's repair, pinned in test_upgrade_fixed_sections.)"""
    specs = tmp_path / "specs"
    stamp = _version.CANONICAL_SPECS_VERSION
    _write_constitution(specs, f"---\nspecs_pattern_version: {stamp}\n---\n# C\n")

    result = _upgrade.upgrade(specs, remove=lambda p: sweep.remove(specs, p, p.name))
    assert result.from_version == stamp
    assert result.to_version == stamp
    assert result.ideas_removed == []

    # Dry-run at the floor plans nothing and writes nothing.
    dry = _upgrade.upgrade(specs, remove=lambda p: sweep.remove(specs, p, p.name), dry_run=True)
    assert dry.dry_run is True
    assert dry.no_op is True

    # Re-running is stable (idempotent).
    second = _upgrade.upgrade(specs, remove=lambda p: sweep.remove(specs, p, p.name))
    assert second.no_op is True
