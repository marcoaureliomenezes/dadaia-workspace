"""copy_tree is copy-and-record ONLY — pruning belongs to the install ledger.

The per-dir orphan prune this file used to pin was retired deliberately (bug
retired-lib-asset-leaves-orphan-projection): it derived the desired state from the
CURRENT source, so a fully retired family never pruned (the src-exists guard returned
first) while operator files dropped into managed dirs were deleted without record.
Ledger-driven reconciliation (``_reconcile_install_ledger``, covered by
``tests/integration/test_install_ledger_reconciliation.py``) owns removal now.
"""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.infrastructure.public_assets import (
    FileSystemPublicAssetManager,
    OverwritePolicy,
)


def test_copy_tree_copies_and_never_prunes(tmp_path: Path) -> None:
    mgr = FileSystemPublicAssetManager()
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    (src / "grp").mkdir(parents=True)
    (src / "keep.md").write_text("keep", encoding="utf-8")
    (src / "grp" / "a.md").write_text("a", encoding="utf-8")

    installed: list[str] = []
    mgr._copy_tree(src, dst, overwrite=OverwritePolicy.FORCE, installed=installed)
    assert (dst / "keep.md").exists()
    assert (dst / "grp" / "a.md").exists()

    # A file the source no longer carries is NOT this function's problem — the
    # ledger reconciler removes it (with the sha safety check) at install() end.
    (src / "keep.md").unlink()
    installed2: list[str] = []
    mgr._copy_tree(src, dst, overwrite=OverwritePolicy.FORCE, installed=installed2)
    assert (dst / "keep.md").exists(), "copy_tree must never delete"
    assert not any(line.startswith("[prune]") for line in installed2)


def test_copy_tree_missing_source_is_a_noop(tmp_path: Path) -> None:
    mgr = FileSystemPublicAssetManager()
    installed: list[str] = []
    mgr._copy_tree(
        tmp_path / "absent", tmp_path / "dst", overwrite=OverwritePolicy.FORCE, installed=installed
    )
    assert installed == []
