"""v0.1.73 FR5 (bug ``specs-upgrade-backup-trips-preflight-dirty-gate``): the upgrade
backup must land OUTSIDE the repo worktree when a workspace root is resolvable — the
repair verb's byproduct must not re-trip the dirty-tree gate it repairs."""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.core import specs_backup


def _workspace_with_repo(tmp_path: Path) -> Path:
    ws = tmp_path / "ws"
    (ws / ".dadaia" / "states").mkdir(parents=True)
    (ws / ".dadaia" / "states" / "spec_contexts.json").write_text("{}", encoding="utf-8")
    specs = ws / "repos" / "consumer-repo" / "specs"
    specs.mkdir(parents=True)
    (specs / "constitution.md").write_text("# c\n", encoding="utf-8")
    return specs


@pytest.mark.parametrize(
    ("name", "resolvable_workspace"),
    [("workspace_resolvable", True), ("no_workspace", False)],
)
def test_backup_location(tmp_path: Path, name: str, resolvable_workspace: bool) -> None:
    if resolvable_workspace:
        specs = _workspace_with_repo(tmp_path)
        ws = tmp_path / "ws"
        dest = specs_backup.backup_specs(specs, 1, 4)
        assert (ws / ".dadaia" / "tmp" / "specs-upgrade-backups" / "consumer-repo") in dest.parents
        # NOTHING lands inside the repo worktree (the v0.1.73 bug pin: the backup must
        # not re-trip the dirty gate it repairs).
        assert not (ws / "repos" / "consumer-repo" / "specs_bkp").exists()
        assert (dest / "constitution.md").is_file()
    else:
        specs = tmp_path / "specs"
        specs.mkdir()
        (specs / "constitution.md").write_text("# c\n", encoding="utf-8")
        dest = specs_backup.backup_specs(specs, 1, 4)
        assert dest.parent == tmp_path / "specs_bkp"
        assert (dest / "constitution.md").is_file()
