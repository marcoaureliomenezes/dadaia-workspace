"""Unit tests for the specs-evolution framework (WS-SPECS-EVOLUTION; simplified
v0.5.1 T-051-16, K10).

Covers FR-S02 (version stamp), the registry's surviving "stamp v6 or refuse" rule
(FR-S03, replacing the retired versioned migration chain — see
``features/migrate/registry.py``'s docstring), and FR-S05 (upgrade
orchestration).

The versioned-chain tests this file used to carry (``test_registry_plan_...``,
``test_upgrade_dry_run_writes_nothing``, ``test_upgrade_backup_first_chain_restamp``)
are DELETED with their subject (the six migration modules + ``MigrationStep``/
``plan``/``run_chain``) — replaced below by ``test_check_upgradable_refuses_below_
floor_and_is_silent_at_or_above_it`` and
``test_upgrade_refuses_below_floor_without_any_write`` /
``test_upgrade_at_or_above_floor_is_idempotent_and_repairs_placeholders``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.core import specs_version as _version
from dadaia_workspace.features.migrate import registry as _registry
from dadaia_workspace.features.migrate import upgrade as _upgrade


def _write_constitution(specs_dir: Path, body: str) -> Path:
    specs_dir.mkdir(parents=True, exist_ok=True)
    path = specs_dir / "constitution.md"
    path.write_text(body, encoding="utf-8")
    return path


# ───────────────────────────── version (FR-S02) — 1 param ─────────────────────


@pytest.mark.parametrize(
    ("body", "expected_version", "assert_extra"),
    [
        pytest.param(None, 0, None, id="absent-constitution-is-version-zero"),
        pytest.param("# Constitution\n\nbody\n", 0, None, id="no-frontmatter-is-version-zero"),
        pytest.param(
            "---\nspecs_pattern_version: 1\n---\n# Constitution\n",
            1,
            None,
            id="read-stamped-version",
        ),
    ],
)
def test_version_read_matrix(
    tmp_path: Path, body: str | None, expected_version: int, assert_extra: object
) -> None:
    specs = tmp_path / "specs"
    if body is not None:
        _write_constitution(specs, body)
    assert _version.read_pattern_version(specs) == expected_version


def test_write_version_creates_and_updates_stamp(tmp_path: Path) -> None:
    # Creates frontmatter on a bare file, preserving the body.
    specs = tmp_path / "specs"
    _write_constitution(specs, "# Constitution\n\nbody\n")
    _version.write_pattern_version(specs, 1)
    assert _version.read_pattern_version(specs) == 1
    assert "# Constitution" in (specs / "constitution.md").read_text(encoding="utf-8")

    # Updates an existing stamp, preserving sibling frontmatter keys.
    specs2 = tmp_path / "specs2"
    _write_constitution(specs2, "---\nspecs_pattern_version: 0\nother: keep\n---\n# C\n")
    _version.write_pattern_version(specs2, 1)
    text = (specs2 / "constitution.md").read_text(encoding="utf-8")
    assert _version.read_pattern_version(specs2) == 1
    assert "other: keep" in text


# ───────────────────────────── registry (FR-S03) — 1 param ────────────────────


def test_check_upgradable_refuses_below_floor_and_is_silent_at_or_above_it() -> None:
    """A-10.1: "the registry refuses <6 with the upgrade instruction"."""
    with pytest.raises(_registry.UpgradeRefused, match="0.4.x"):
        _registry.check_upgradable(current=0, goal=6)
    with pytest.raises(_registry.UpgradeRefused, match="0.4.x"):
        _registry.check_upgradable(current=5, goal=6)

    # At, or past, the floor: no exception (the caller treats it as "nothing to do").
    _registry.check_upgradable(current=6, goal=6)
    _registry.check_upgradable(current=7, goal=6)


# ───────────────────────────── upgrade (FR-S05) ────────────────────────────────


def test_upgrade_refuses_below_floor_without_any_write(tmp_path: Path) -> None:
    """A-10.1: refusing a below-floor tree never touches the filesystem — no
    backup, no re-stamp, no migrated content."""
    specs = tmp_path / "specs"
    _write_constitution(specs, "# C\n")  # version 0, below the canonical floor

    with pytest.raises(_registry.UpgradeRefused):
        _upgrade.upgrade(specs, dry_run=True)
    with pytest.raises(_registry.UpgradeRefused):
        _upgrade.upgrade(specs, dry_run=False)

    assert not (tmp_path / "specs_bkp").exists()
    assert _version.read_pattern_version(specs) == 0


def test_upgrade_at_or_above_floor_is_idempotent_and_repairs_placeholders(
    tmp_path: Path,
) -> None:
    """A tree already at (or past) the canonical version is a no-op besides the
    unconditional placeholder-atom repair; re-running is stable."""
    specs = tmp_path / "specs"
    stamp = _version.CANONICAL_SPECS_VERSION
    _write_constitution(specs, f"---\nspecs_pattern_version: {stamp}\n---\n# C\n")

    result = _upgrade.upgrade(specs)
    assert result.from_version == stamp
    assert result.to_version == stamp
    assert result.no_op is True
    assert result.placeholder_removed == []

    # Dry-run at the floor plans nothing and writes nothing.
    dry = _upgrade.upgrade(specs, dry_run=True)
    assert dry.dry_run is True
    assert dry.no_op is True

    # Re-running is stable (idempotent).
    second = _upgrade.upgrade(specs)
    assert second.no_op is True
