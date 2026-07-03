"""Unit tests for the specs-evolution migration framework (WS-SPECS-EVOLUTION).

Covers FR-S02 (version stamp), FR-S03 (registry), FR-S04 (backup-first), FR-S05
(upgrade orchestration). Determinism via injected ``clock``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from dadaia_workspace.core import specs_backup as _backup
from dadaia_workspace.core import specs_version as _version
from dadaia_workspace.features.migrate import registry as _registry
from dadaia_workspace.features.migrate import upgrade as _upgrade

_FIXED = lambda: datetime(2026, 6, 8, 3, 8, 8, tzinfo=UTC)  # noqa: E731


# ───────────────────────────── version (FR-S02) ─────────────────────────────


def _write_constitution(specs_dir: Path, body: str) -> Path:
    specs_dir.mkdir(parents=True, exist_ok=True)
    path = specs_dir / "constitution.md"
    path.write_text(body, encoding="utf-8")
    return path


def test_absent_constitution_is_version_zero(tmp_path: Path) -> None:
    assert _version.read_pattern_version(tmp_path / "specs") == 0


def test_no_frontmatter_is_version_zero(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    _write_constitution(specs, "# Constitution\n\nbody\n")
    assert _version.read_pattern_version(specs) == 0


def test_read_stamped_version(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    _write_constitution(specs, "---\nspecs_pattern_version: 1\n---\n# Constitution\n")
    assert _version.read_pattern_version(specs) == 1


def test_write_version_creates_frontmatter(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    _write_constitution(specs, "# Constitution\n\nbody\n")
    _version.write_pattern_version(specs, 1)
    assert _version.read_pattern_version(specs) == 1
    # Original body preserved after the new frontmatter block.
    assert "# Constitution" in (specs / "constitution.md").read_text(encoding="utf-8")


def test_write_version_updates_existing_stamp(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    _write_constitution(specs, "---\nspecs_pattern_version: 0\nother: keep\n---\n# C\n")
    _version.write_pattern_version(specs, 1)
    text = (specs / "constitution.md").read_text(encoding="utf-8")
    assert _version.read_pattern_version(specs) == 1
    assert "other: keep" in text  # sibling frontmatter keys preserved


# ───────────────────────────── registry (FR-S03) ─────────────────────────────


def test_tree_v2_registered_as_first_step() -> None:
    keys = [s.key for s in _registry.REGISTRY]
    assert "tree-v2" in keys
    first = _registry.REGISTRY[0]
    assert (first.from_version, first.to_version) == (0, 1)


def test_latest_version_matches_canonical() -> None:
    assert _registry.latest_version() == _version.CANONICAL_SPECS_VERSION


def test_plan_empty_when_at_target() -> None:
    assert _registry.plan(1, 1) == []


def test_plan_walks_zero_to_one() -> None:
    steps = _registry.plan(0, 1)
    assert [s.key for s in steps] == ["tree-v2"]


def test_plan_rejects_downgrade() -> None:
    with pytest.raises(ValueError, match="downgrade"):
        _registry.plan(1, 0)


def test_chain_idempotent_on_already_migrated_tree(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    (specs / "releases" / "legacy").mkdir(parents=True)  # already migrated
    # tree-v2 on a tree with nothing legacy to move is a safe no-op (no moves).
    results = _registry.run_chain(specs, 0, 1, dry_run=False)
    assert results[0][1].moved == []


# ───────────────────────────── backup (FR-S04) ─────────────────────────────


def test_backup_label_format() -> None:
    label = _backup.backup_label(0, 1, clock=_FIXED)
    assert label == "0→1-20260608T030808Z"


def test_backup_copies_tree_into_specs_bkp(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    specs.mkdir()
    (specs / "constitution.md").write_text("# C\n", encoding="utf-8")
    dest = _backup.backup_specs(specs, 0, 1, clock=_FIXED)
    assert dest.parent.name == "specs_bkp"
    assert (dest / "constitution.md").read_text(encoding="utf-8") == "# C\n"


def test_backup_root_is_sibling_of_specs(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    assert _backup.backup_root(specs) == tmp_path / "specs_bkp"


# ───────────────────────────── upgrade (FR-S05) ─────────────────────────────


def test_upgrade_noop_when_already_canonical(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    _write_constitution(
        specs, f"---\nspecs_pattern_version: {_version.CANONICAL_SPECS_VERSION}\n---\n# C\n"
    )
    result = _upgrade.upgrade(specs, clock=_FIXED)
    assert result.no_op is True
    assert result.backup_path is None
    assert not (tmp_path / "specs_bkp").exists()


def test_upgrade_dry_run_writes_nothing(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    _write_constitution(specs, "# C\n")  # version 0
    (specs / "foundation").mkdir()
    (specs / "foundation" / "SPEC.md").write_text("x", encoding="utf-8")
    result = _upgrade.upgrade(specs, dry_run=True, clock=_FIXED)
    assert result.dry_run is True
    assert result.from_version == 0 and result.to_version == _version.CANONICAL_SPECS_VERSION
    assert not (tmp_path / "specs_bkp").exists()  # no backup written on dry-run
    assert _version.read_pattern_version(specs) == 0  # not re-stamped
    assert (specs / "foundation").exists()  # not migrated


def test_upgrade_backup_first_chain_restamp(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    _write_constitution(specs, "# Constitution\n")  # version 0
    (specs / "foundation").mkdir()
    (specs / "foundation" / "SPEC.md").write_text("found", encoding="utf-8")

    result = _upgrade.upgrade(specs, clock=_FIXED)

    assert result.no_op is False
    # 1. backup-first happened
    assert result.backup_path is not None and result.backup_path.exists()
    assert (result.backup_path / "foundation" / "SPEC.md").read_text(encoding="utf-8") == "found"
    # 2. chain applied (foundation moved to releases/legacy)
    assert (specs / "releases" / "legacy" / "foundation").exists()
    assert not (specs / "foundation").exists()
    # 3. re-stamped to canonical
    assert _version.read_pattern_version(specs) == _version.CANONICAL_SPECS_VERSION


def test_upgrade_is_idempotent(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    _write_constitution(specs, "# C\n")
    (specs / "foundation").mkdir()
    (specs / "foundation" / "SPEC.md").write_text("x", encoding="utf-8")
    _upgrade.upgrade(specs, clock=_FIXED)
    # Second run: already at target → no-op, no second backup.
    second = _upgrade.upgrade(specs, clock=_FIXED)
    assert second.no_op is True


# ─────────────────────── doctor integration (FR-S05/S06) ───────────────────────


def test_doctor_warns_on_below_version_tree(tmp_path: Path) -> None:
    from dadaia_workspace.features.specs import Severity, SpecsDoctor

    specs = tmp_path / "specs"
    _write_constitution(specs, "# Constitution\n")  # unstamped → version 0
    issues = SpecsDoctor(specs).check()
    version_warns = [i for i in issues if i.code == "SPECS-VERSION"]
    assert len(version_warns) == 1
    assert version_warns[0].severity == Severity.WARNING
    assert "dadaia specs upgrade" in version_warns[0].description


def test_doctor_silent_on_canonical_tree(tmp_path: Path) -> None:
    from dadaia_workspace.features.specs.doctor import SpecsDoctor

    specs = tmp_path / "specs"
    stamp = _version.CANONICAL_SPECS_VERSION
    _write_constitution(specs, f"---\nspecs_pattern_version: {stamp}\n---\n# C\n")
    issues = SpecsDoctor(specs).check()
    assert [i for i in issues if i.code == "SPECS-VERSION"] == []
