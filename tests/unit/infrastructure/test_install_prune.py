"""T-020-01: install-prune — _copy_tree removes orphan projections.

Regression for bug `install-does-not-prune-orphan-projections`: a projected file
whose source no longer exists in staging must be pruned on the next install, so the
instance stays drift-free without a manual sweep.
"""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager


def test_copy_tree_prunes_orphan(tmp_path: Path) -> None:
    mgr = FileSystemPublicAssetManager()
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    src.mkdir()
    (src / "keep.md").write_text("keep", encoding="utf-8")
    (src / "also-keep.md").write_text("also", encoding="utf-8")

    # First projection.
    installed: list[str] = []
    mgr._copy_tree(src, dst, force=True, installed=installed)
    assert (dst / "keep.md").exists()
    assert (dst / "also-keep.md").exists()

    # Source loses a file → next projection must prune the orphan from dst.
    (src / "also-keep.md").unlink()
    installed2: list[str] = []
    mgr._copy_tree(src, dst, force=True, installed=installed2)

    assert (dst / "keep.md").exists()
    assert not (dst / "also-keep.md").exists(), "orphan projection must be pruned"
    assert any(line.startswith("[prune]") and "also-keep.md" in line for line in installed2)


def test_copy_tree_prunes_orphan_in_nested_subdir(tmp_path: Path) -> None:
    mgr = FileSystemPublicAssetManager()
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    (src / "grp").mkdir(parents=True)
    (src / "grp" / "a.md").write_text("a", encoding="utf-8")
    mgr._copy_tree(src, dst, force=True, installed=[])
    assert (dst / "grp" / "a.md").exists()

    # Remove the whole source subdir → projection prunes the file and the empty dir.
    (src / "grp" / "a.md").unlink()
    (src / "grp").rmdir()
    mgr._copy_tree(src, dst, force=True, installed=[])
    assert not (dst / "grp" / "a.md").exists()
    assert not (dst / "grp").exists(), "empty pruned dir must be removed"


def test_copy_tree_no_prune_when_in_sync(tmp_path: Path) -> None:
    mgr = FileSystemPublicAssetManager()
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    src.mkdir()
    (src / "a.md").write_text("a", encoding="utf-8")
    mgr._copy_tree(src, dst, force=True, installed=[])
    installed: list[str] = []
    mgr._copy_tree(src, dst, force=True, installed=installed)
    assert not any(line.startswith("[prune]") for line in installed)
    assert (dst / "a.md").exists()
