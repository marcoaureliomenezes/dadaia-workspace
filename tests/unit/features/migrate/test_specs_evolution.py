"""Unit tests for the specs-evolution migration framework (WS-SPECS-EVOLUTION).

Covers FR-S02 (version stamp), FR-S03 (registry), FR-S04 (backup-first), FR-S05
(upgrade orchestration). Determinism via injected ``clock``.

CRITICAL migration chain (data loss risk): idempotence on an already-migrated tree,
dry-run writing nothing, and backup-before-write ordering are each kept as named
tests — they are the irreplaceable data-loss detectors for this framework.
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


def test_registry_plan_and_latest_version() -> None:
    keys = [s.key for s in _registry.REGISTRY]
    assert "tree-v2" in keys
    first = _registry.REGISTRY[0]
    assert (first.from_version, first.to_version) == (0, 1)

    assert _registry.latest_version() == _version.CANONICAL_SPECS_VERSION
    assert _registry.plan(1, 1) == []
    assert [s.key for s in _registry.plan(0, 1)] == ["tree-v2"]

    with pytest.raises(ValueError, match="downgrade"):
        _registry.plan(1, 0)


def test_chain_idempotent_on_already_migrated_tree(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    (specs / "releases" / "legacy").mkdir(parents=True)  # already migrated
    # tree-v2 on a tree with nothing legacy to move is a safe no-op (no moves).
    results = _registry.run_chain(specs, 0, 1, dry_run=False)
    assert results[0][1].moved == []


# ───────────────────────────── backup (FR-S04) + doctor integration — 1 param ─


def test_backup_label_location_copy_and_doctor_visibility(tmp_path: Path) -> None:
    label = _backup.backup_label(0, 1, clock=_FIXED)
    assert label == "0→1-20260608T030808Z"

    specs = tmp_path / "specs"
    specs.mkdir()
    (specs / "constitution.md").write_text("# C\n", encoding="utf-8")
    assert _backup.backup_root(specs) == tmp_path / "specs_bkp"

    dest = _backup.backup_specs(specs, 0, 1, clock=_FIXED)
    assert dest.parent.name == "specs_bkp"
    assert (dest / "constitution.md").read_text(encoding="utf-8") == "# C\n"

    # Doctor: below-canonical tree warns; canonical-stamped tree is silent.
    from dadaia_workspace.features.specs import Severity, SpecsDoctor

    below = SpecsDoctor(specs).check()
    version_warns = [i for i in below if i.code == "SPECS-VERSION"]
    assert len(version_warns) == 1
    assert version_warns[0].severity == Severity.WARNING
    assert "dadaia specs upgrade" in version_warns[0].description

    canonical_specs = tmp_path / "specs_canonical"
    stamp = _version.CANONICAL_SPECS_VERSION
    _write_constitution(canonical_specs, f"---\nspecs_pattern_version: {stamp}\n---\n# C\n")
    canonical_issues = SpecsDoctor(canonical_specs).check()
    assert [i for i in canonical_issues if i.code == "SPECS-VERSION"] == []


# ───────────────────────────── upgrade (FR-S05) — CRITICAL, kept named ────────


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
    """The order contract: backup happens BEFORE the chain mutates the tree, the
    chain applies, and the tree is re-stamped to canonical only after both — and a
    second run against the now-canonical tree is idempotent (no second backup)."""
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

    # Second run: already at target → no-op, no second backup.
    second = _upgrade.upgrade(specs, clock=_FIXED)
    assert second.no_op is True
    assert second.backup_path is None

    # A tree already stamped canonical before any upgrade call is a no-op from the start.
    fresh_specs = tmp_path.parent / (tmp_path.name + "-fresh-canonical") / "specs"
    _write_constitution(
        fresh_specs, f"---\nspecs_pattern_version: {_version.CANONICAL_SPECS_VERSION}\n---\n# C\n"
    )
    fresh_result = _upgrade.upgrade(fresh_specs, clock=_FIXED)
    assert fresh_result.no_op is True
    assert fresh_result.backup_path is None
    assert not (fresh_specs.parent / "specs_bkp").exists()
