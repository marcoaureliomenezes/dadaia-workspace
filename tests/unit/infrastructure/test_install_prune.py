"""T-020-01: install-prune — _copy_tree removes orphan projections.

Regression for bug `install-does-not-prune-orphan-projections`: a projected file
whose source no longer exists in staging must be pruned on the next install, so the
instance stays drift-free without a manual sweep.
"""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager


def test_copy_tree_prunes_orphans_and_stays_silent_when_in_sync(tmp_path: Path) -> None:
    mgr = FileSystemPublicAssetManager()
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    (src / "grp").mkdir(parents=True)
    (src / "keep.md").write_text("keep", encoding="utf-8")
    (src / "also-keep.md").write_text("also", encoding="utf-8")
    (src / "grp" / "a.md").write_text("a", encoding="utf-8")

    # First projection. It returns what it owns — the caller records that as the ledger
    # entry, and pruning on later runs is scoped to it (bug
    # claude-install-prunes-operator-authored-files).
    installed: list[str] = []
    owned = mgr._copy_tree(src, dst, force=True, installed=installed)
    assert owned == {"keep.md", "also-keep.md", "grp/a.md"}
    assert (dst / "keep.md").exists()
    assert (dst / "also-keep.md").exists()
    assert (dst / "grp" / "a.md").exists()

    # In sync: a second projection with no source changes prunes nothing.
    installed_sync: list[str] = []
    owned = mgr._copy_tree(src, dst, force=True, installed=installed_sync, owned=owned)
    assert not any(line.startswith("[prune]") for line in installed_sync)

    # Source loses a file → next projection must prune the orphan from dst.
    (src / "also-keep.md").unlink()
    installed2: list[str] = []
    owned = mgr._copy_tree(src, dst, force=True, installed=installed2, owned=owned)
    assert (dst / "keep.md").exists()
    assert not (dst / "also-keep.md").exists(), "orphan projection must be pruned"
    assert any(line.startswith("[prune]") and "also-keep.md" in line for line in installed2)

    # Source loses a whole subdir → projection prunes the file and the empty dir.
    (src / "grp" / "a.md").unlink()
    (src / "grp").rmdir()
    mgr._copy_tree(src, dst, force=True, installed=[], owned=owned)
    assert not (dst / "grp" / "a.md").exists()
    assert not (dst / "grp").exists(), "empty pruned dir must be removed"


def test_a_file_dadaia_never_projected_is_never_pruned(tmp_path: Path) -> None:
    """The ownership boundary itself: no ledger entry ⇒ no delete.

    This is the half that was missing. The test above only ever asked "is an orphan
    removed?", which a prune-everything implementation answers correctly — so it
    certified the data-loss bug as working.
    """
    mgr = FileSystemPublicAssetManager()
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    src.mkdir()
    (src / "lib.md").write_text("lib", encoding="utf-8")
    dst.mkdir()
    (dst / "operator.md").write_text("mine", encoding="utf-8")

    installed: list[str] = []
    owned = mgr._copy_tree(src, dst, force=True, installed=installed, owned=None)

    assert (dst / "operator.md").read_text(encoding="utf-8") == "mine"
    assert not any("[prune]" in line for line in installed)
    assert owned == {"lib.md"}, "the ledger records only what dadaia wrote"
