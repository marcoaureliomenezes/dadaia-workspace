"""Unit tests for `dadaia_workspace.features.migrate.tree_v2`.

Covers:
- AC-T1-4: idempotently moves foundation/ content to releases/legacy/foundation/
- AC-T6-4: moves root SPEC.md to releases/legacy/SPEC.md atomically
           (timestamp suffix when destination already exists — destructive-overwrite
           guard, kept as a named test)
- Idempotency across foundation/ SPEC.md/ and both together
- Dry-run: no filesystem changes, but planned moves are reported
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.features.migrate.tree_v2 import migrate_tree_v2


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


def test_timestamp_suffix_when_destination_exists(tmp_path: Path) -> None:
    """Destructive-overwrite guard: if releases/legacy/SPEC.md already exists, a
    timestamp-suffixed destination is used and the pre-existing file is preserved."""
    specs = tmp_path / "specs"
    specs.mkdir()
    _make_root_spec(specs, content="# Root SPEC v2\n")
    legacy = specs / "releases" / "legacy"
    legacy.mkdir(parents=True)
    (legacy / "SPEC.md").write_text("# Existing SPEC\n", encoding="utf-8")

    result = migrate_tree_v2(specs)

    assert not (specs / "SPEC.md").exists(), "root SPEC.md must be removed"
    assert len(result.moved) == 1
    _, dst = result.moved[0]
    assert dst != legacy / "SPEC.md"
    assert dst.stem.startswith("SPEC.")
    assert dst.suffix == ".md"
    assert dst.is_file()
    assert (legacy / "SPEC.md").read_text(encoding="utf-8") == "# Existing SPEC\n"


@pytest.mark.parametrize(
    "case",
    ["foundation-only", "root-spec-only", "both-together"],
)
def test_moves_and_idempotence_matrix(tmp_path: Path, case: str) -> None:
    specs = tmp_path / "specs"
    specs.mkdir()

    if case == "foundation-only":
        _make_foundation(specs)
        result = migrate_tree_v2(specs)
        legacy_foundation = specs / "releases" / "legacy" / "foundation"
        assert legacy_foundation.is_dir()
        assert (legacy_foundation / "SPEC.md").is_file()
        assert not (specs / "foundation").exists()
        assert len(result.moved) == 1
        src, dst = result.moved[0]
        assert src == specs / "foundation" and dst == legacy_foundation
        # Idempotent re-run: nothing left to move.
        second = migrate_tree_v2(specs)
        assert len(second.moved) == 0
        assert any("not found" in msg or "already" in msg for msg in second.skipped)

    elif case == "root-spec-only":
        _make_root_spec(specs)
        result = migrate_tree_v2(specs)
        legacy_spec = specs / "releases" / "legacy" / "SPEC.md"
        assert legacy_spec.is_file()
        assert legacy_spec.read_text(encoding="utf-8") == "# Root SPEC\n"
        assert not (specs / "SPEC.md").exists()
        assert len(result.moved) == 1
        src, dst = result.moved[0]
        assert src == specs / "SPEC.md" and dst == legacy_spec
        # Idempotent: absent root SPEC.md is silently skipped.
        second = migrate_tree_v2(specs)
        assert len(second.moved) == 0
        assert any(
            "SPEC.md not found" in msg or "nothing to migrate" in msg for msg in second.skipped
        )

    else:  # both-together
        _make_foundation(specs)
        _make_root_spec(specs)
        result = migrate_tree_v2(specs)
        assert len(result.moved) == 2
        legacy = specs / "releases" / "legacy"
        assert (legacy / "foundation").is_dir()
        assert (legacy / "SPEC.md").is_file()
        assert not (specs / "foundation").exists()
        assert not (specs / "SPEC.md").exists()
        # A pre-existing legacy/foundation/ from a partial prior migration is respected
        # (never clobbered) on a fresh source.
        specs2 = tmp_path / "specs2"
        specs2.mkdir()
        _make_foundation(specs2)
        legacy2 = specs2 / "releases" / "legacy" / "foundation"
        legacy2.mkdir(parents=True)
        result2 = migrate_tree_v2(specs2)
        assert len(result2.moved) == 0
        assert any("already exists" in msg for msg in result2.skipped)
        assert (specs2 / "foundation").is_dir()


def test_dry_run_reports_planned_moves_without_touching_filesystem(tmp_path: Path) -> None:
    # foundation only
    specs_f = tmp_path / "specs_f"
    specs_f.mkdir()
    _make_foundation(specs_f)
    result_f = migrate_tree_v2(specs_f, dry_run=True)
    assert result_f.dry_run is True
    assert len(result_f.moved) == 1
    assert (specs_f / "foundation").is_dir()
    assert not (specs_f / "releases" / "legacy" / "foundation").exists()

    # root SPEC.md only
    specs_s = tmp_path / "specs_s"
    specs_s.mkdir()
    _make_root_spec(specs_s)
    result_s = migrate_tree_v2(specs_s, dry_run=True)
    assert result_s.dry_run is True
    assert len(result_s.moved) == 1
    assert (specs_s / "SPEC.md").is_file()
    assert not (specs_s / "releases" / "legacy" / "SPEC.md").exists()

    # both together
    specs_b = tmp_path / "specs_b"
    specs_b.mkdir()
    _make_foundation(specs_b)
    _make_root_spec(specs_b)
    result_b = migrate_tree_v2(specs_b, dry_run=True)
    assert len(result_b.moved) == 2
    assert (specs_b / "foundation").is_dir()
    assert (specs_b / "SPEC.md").is_file()
