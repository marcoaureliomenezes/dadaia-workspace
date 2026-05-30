"""Unit tests for `dadaia_workspace.features.migrate.tree_v2`.

Covers:
- AC-T1-4: idempotently moves foundation/ content to releases/legacy/foundation/
- AC-T6-4: moves root SPEC.md to releases/legacy/SPEC.md atomically
           (timestamp suffix when destination already exists)
- Idempotency: running migrate twice is safe
- Dry-run: no filesystem changes, but planned moves are reported
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.features.migrate.tree_v2 import MigrateResult, migrate_tree_v2


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _make_foundation(specs_dir: Path) -> Path:
    """Create a legacy specs/foundation/ with a SPEC.md file."""
    foundation = specs_dir / "foundation"
    foundation.mkdir(parents=True, exist_ok=True)
    (foundation / "SPEC.md").write_text("# Foundation SPEC\n", encoding="utf-8")
    return foundation


def _make_root_spec(specs_dir: Path, content: str = "# Root SPEC\n") -> Path:
    """Create a legacy specs/SPEC.md file."""
    root_spec = specs_dir / "SPEC.md"
    root_spec.write_text(content, encoding="utf-8")
    return root_spec


# ---------------------------------------------------------------------------
# T-1 — foundation/ migration (AC-T1-4)
# ---------------------------------------------------------------------------


class TestMigrateFoundation:
    def test_moves_foundation_to_legacy(self, tmp_path: Path) -> None:
        """foundation/ content is moved to releases/legacy/foundation/."""
        specs = tmp_path / "specs"
        specs.mkdir()
        _make_foundation(specs)

        result = migrate_tree_v2(specs)

        legacy_foundation = specs / "releases" / "legacy" / "foundation"
        assert legacy_foundation.is_dir(), "legacy/foundation/ must exist after migration"
        assert (legacy_foundation / "SPEC.md").is_file(), "SPEC.md must be inside legacy/foundation/"
        assert not (specs / "foundation").exists(), "original foundation/ must be removed"
        assert len(result.moved) == 1
        src, dst = result.moved[0]
        assert src == specs / "foundation"
        assert dst == legacy_foundation

    def test_idempotent_when_legacy_foundation_already_exists(self, tmp_path: Path) -> None:
        """Running migrate twice does not fail or clobber existing legacy/foundation/."""
        specs = tmp_path / "specs"
        specs.mkdir()
        _make_foundation(specs)

        # First run
        migrate_tree_v2(specs)

        # Second run: foundation/ is gone, nothing to do
        result = migrate_tree_v2(specs)

        assert len(result.moved) == 0
        assert any("not found" in msg or "already" in msg for msg in result.skipped)

    def test_idempotent_when_legacy_foundation_pre_exists(self, tmp_path: Path) -> None:
        """If releases/legacy/foundation/ already exists, the move is skipped."""
        specs = tmp_path / "specs"
        specs.mkdir()
        _make_foundation(specs)
        # Pre-create legacy/foundation/ (simulates a prior partial migration)
        legacy = specs / "releases" / "legacy" / "foundation"
        legacy.mkdir(parents=True)

        result = migrate_tree_v2(specs)

        assert len(result.moved) == 0
        assert any("already exists" in msg for msg in result.skipped)
        # original foundation/ must NOT have been moved
        assert (specs / "foundation").is_dir()

    def test_no_foundation_skips_step_1(self, tmp_path: Path) -> None:
        """When foundation/ is absent, step 1 is silently skipped."""
        specs = tmp_path / "specs"
        specs.mkdir()

        result = migrate_tree_v2(specs)

        assert len(result.moved) == 0
        assert any("foundation" in msg for msg in result.skipped)

    def test_dry_run_does_not_move_foundation(self, tmp_path: Path) -> None:
        """dry_run=True reports the planned move without writing anything."""
        specs = tmp_path / "specs"
        specs.mkdir()
        _make_foundation(specs)

        result = migrate_tree_v2(specs, dry_run=True)

        assert result.dry_run is True
        assert len(result.moved) == 1
        # filesystem must be untouched
        assert (specs / "foundation").is_dir(), "dry-run must not delete foundation/"
        assert not (specs / "releases" / "legacy" / "foundation").exists()


# ---------------------------------------------------------------------------
# T-6 — root SPEC.md migration (AC-T6-4)
# ---------------------------------------------------------------------------


class TestMigrateRootSpec:
    def test_moves_root_spec_to_legacy(self, tmp_path: Path) -> None:
        """specs/SPEC.md is moved to specs/releases/legacy/SPEC.md."""
        specs = tmp_path / "specs"
        specs.mkdir()
        _make_root_spec(specs)

        result = migrate_tree_v2(specs)

        legacy_spec = specs / "releases" / "legacy" / "SPEC.md"
        assert legacy_spec.is_file(), "SPEC.md must exist at releases/legacy/SPEC.md"
        assert legacy_spec.read_text(encoding="utf-8") == "# Root SPEC\n"
        assert not (specs / "SPEC.md").exists(), "root SPEC.md must be removed"
        assert len(result.moved) == 1
        src, dst = result.moved[0]
        assert src == specs / "SPEC.md"
        assert dst == legacy_spec

    def test_timestamp_suffix_when_destination_exists(self, tmp_path: Path) -> None:
        """If releases/legacy/SPEC.md already exists, a timestamp suffix is added."""
        specs = tmp_path / "specs"
        specs.mkdir()
        _make_root_spec(specs, content="# Root SPEC v2\n")
        # Pre-create the destination
        legacy = specs / "releases" / "legacy"
        legacy.mkdir(parents=True)
        (legacy / "SPEC.md").write_text("# Existing SPEC\n", encoding="utf-8")

        result = migrate_tree_v2(specs)

        # Original file must be moved (with a timestamp suffix)
        assert not (specs / "SPEC.md").exists(), "root SPEC.md must be removed"
        assert len(result.moved) == 1
        _, dst = result.moved[0]
        # Destination should NOT overwrite the existing SPEC.md
        assert dst != legacy / "SPEC.md"
        assert dst.stem.startswith("SPEC.")
        assert dst.suffix == ".md"
        assert dst.is_file()
        # Pre-existing file must be preserved
        assert (legacy / "SPEC.md").read_text(encoding="utf-8") == "# Existing SPEC\n"

    def test_idempotent_when_root_spec_absent(self, tmp_path: Path) -> None:
        """When specs/SPEC.md is absent, step 2 is silently skipped."""
        specs = tmp_path / "specs"
        specs.mkdir()

        result = migrate_tree_v2(specs)

        assert len(result.moved) == 0
        assert any("SPEC.md not found" in msg or "nothing to migrate" in msg for msg in result.skipped)

    def test_dry_run_does_not_move_root_spec(self, tmp_path: Path) -> None:
        """dry_run=True reports the planned move without writing anything."""
        specs = tmp_path / "specs"
        specs.mkdir()
        _make_root_spec(specs)

        result = migrate_tree_v2(specs, dry_run=True)

        assert result.dry_run is True
        assert len(result.moved) == 1
        # filesystem must be untouched
        assert (specs / "SPEC.md").is_file(), "dry-run must not remove SPEC.md"
        assert not (specs / "releases" / "legacy" / "SPEC.md").exists()


# ---------------------------------------------------------------------------
# Combined: both foundation/ and SPEC.md present
# ---------------------------------------------------------------------------


class TestMigrateBothPresent:
    def test_moves_both_in_single_run(self, tmp_path: Path) -> None:
        """When both legacy artifacts exist, both are migrated in one call."""
        specs = tmp_path / "specs"
        specs.mkdir()
        _make_foundation(specs)
        _make_root_spec(specs)

        result = migrate_tree_v2(specs)

        assert len(result.moved) == 2
        legacy = specs / "releases" / "legacy"
        assert (legacy / "foundation").is_dir()
        assert (legacy / "SPEC.md").is_file()
        assert not (specs / "foundation").exists()
        assert not (specs / "SPEC.md").exists()

    def test_dry_run_shows_both_moves(self, tmp_path: Path) -> None:
        """dry_run reports both planned moves without touching the filesystem."""
        specs = tmp_path / "specs"
        specs.mkdir()
        _make_foundation(specs)
        _make_root_spec(specs)

        result = migrate_tree_v2(specs, dry_run=True)

        assert len(result.moved) == 2
        assert (specs / "foundation").is_dir()
        assert (specs / "SPEC.md").is_file()


# ---------------------------------------------------------------------------
# scaffold integrity: verify public/scaffold has no foundation/ or SPEC.md
# ---------------------------------------------------------------------------


class TestScaffoldIntegrity:
    """AC-T1-1 and AC-T6-1: the shipped scaffold must not contain legacy files."""

    def test_scaffold_has_no_foundation_directory(self) -> None:
        """AC-T1-1: scaffold/foundation/ must not exist."""
        scaffold_dir = (
            Path(__file__).parent.parent.parent.parent.parent
            / "dadaia_workspace"
            / "public"
            / "scaffold"
        )
        assert not (scaffold_dir / "foundation").exists(), (
            "scaffold/foundation/ must be deleted (AC-T1-1)"
        )

    def test_scaffold_has_no_root_spec_md(self) -> None:
        """AC-T6-1: scaffold/SPEC.md must not exist."""
        scaffold_dir = (
            Path(__file__).parent.parent.parent.parent.parent
            / "dadaia_workspace"
            / "public"
            / "scaffold"
        )
        assert not (scaffold_dir / "SPEC.md").exists(), (
            "scaffold/SPEC.md must be deleted (AC-T6-1)"
        )


# ---------------------------------------------------------------------------
# service.py fallback list (AC-T1-2)
# ---------------------------------------------------------------------------


class TestServiceFallback:
    """AC-T1-2: service.py fallback must not contain 'foundation'."""

    def test_service_fallback_excludes_foundation(self) -> None:
        """The fallback subdir list in service.py must not include 'foundation'."""
        service_path = (
            Path(__file__).parent.parent.parent.parent.parent
            / "dadaia_workspace"
            / "features"
            / "spec_context"
            / "service.py"
        )
        source = service_path.read_text(encoding="utf-8")
        # Check that 'foundation' does NOT appear in the fallback tuple
        # We look for the specific tuple pattern and ensure 'foundation' is absent.
        # The fallback list is in the form: ("", "memory", "features")
        import ast
        import re

        # Find the loop that iterates over the fallback subdirectories
        match = re.search(
            r'for subdir in \(([^)]+)\)',
            source,
        )
        assert match is not None, "Could not find fallback subdir tuple in service.py"
        tuple_source = "(" + match.group(1) + ")"
        subdirs = ast.literal_eval(tuple_source)
        assert "foundation" not in subdirs, (
            f"'foundation' must not be in the fallback subdir list (AC-T1-2). Found: {subdirs}"
        )
