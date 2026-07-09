"""v0.1.73 FR5 (bug ``specs-upgrade-backup-trips-preflight-dirty-gate``): the upgrade
backup must land OUTSIDE the repo worktree when a workspace root is resolvable — the
repair verb's byproduct must not re-trip the dirty-tree gate it repairs."""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.core import specs_backup


def _workspace_with_repo(tmp_path: Path) -> Path:
    ws = tmp_path / "ws"
    (ws / ".dadaia" / "states").mkdir(parents=True)
    (ws / ".dadaia" / "states" / "spec_contexts.json").write_text("{}", encoding="utf-8")
    specs = ws / "repos" / "consumer-repo" / "specs"
    specs.mkdir(parents=True)
    (specs / "constitution.md").write_text("# c\n", encoding="utf-8")
    return specs


def test_backup_lands_outside_repo_worktree_when_workspace_resolvable(tmp_path: Path) -> None:
    specs = _workspace_with_repo(tmp_path)
    ws = tmp_path / "ws"

    dest = specs_backup.backup_specs(specs, 1, 4)

    assert (ws / ".dadaia" / "tmp" / "specs-upgrade-backups" / "consumer-repo") in dest.parents
    # NOTHING lands inside the repo worktree.
    assert not (ws / "repos" / "consumer-repo" / "specs_bkp").exists()
    assert (dest / "constitution.md").is_file()


def test_backup_falls_back_to_sibling_without_workspace(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    specs.mkdir()
    (specs / "constitution.md").write_text("# c\n", encoding="utf-8")

    dest = specs_backup.backup_specs(specs, 1, 4)

    assert dest.parent == tmp_path / "specs_bkp"
    assert (dest / "constitution.md").is_file()
