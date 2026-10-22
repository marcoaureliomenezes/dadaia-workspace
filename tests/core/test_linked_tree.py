"""A linked worktree's ``.git`` file anchors a protected glob only when git wrote it from a repo of
this workspace."""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.core import workspace_layout as wl
from tests.helpers.oslib import link, write_text


def linked_gitfile(root: Path, tree: Path) -> str:
    """The `.git` file git writes into the linked worktree *tree* of the workspace's repo `r`, and
    the back-pointer it keeps inside that repo's `.git`."""
    admin = root / "repos/r/.git/worktrees" / tree.name
    admin.mkdir(parents=True, exist_ok=True)
    write_text(admin / "gitdir", f"{(tree / '.git').as_posix()}\n")
    return f"gitdir: {admin.as_posix()}\n"


def test_a_git_file_anchors_a_root_only_when_its_gitdir_is_a_worktree_of_this_workspace(
    tmp_path: Path,
) -> None:
    """Under `worktrees/<r>/`, `.git` anchors the root of a tree git linked from `<root>/repos/<r>/`;
    a gitdir elsewhere, even named `worktrees/…`, a gitdir git never wrote (no back-pointer to this
    `.git`), or a symlinked `.git` anchors nothing and the glob
    fails closed at every depth."""
    rel = "worktrees/r/{}/src/secrets/k"
    names = ("real", "planted", "linked", "fabricated")
    real, planted, linked, fabricated = (tmp_path / "worktrees/r" / n for n in names)
    for tree in (real, planted, linked, fabricated):
        (tree / "src").mkdir(parents=True)
    write_text(real / ".git", linked_gitfile(tmp_path, real))
    write_text(planted / ".git", "gitdir: /elsewhere/worktrees/x\n")
    forged = (tmp_path / "repos/r/.git/worktrees/fabricated").as_posix()
    write_text(fabricated / ".git", f"gitdir: {forged}\n")
    write_text(tmp_path / "pointer", linked_gitfile(tmp_path, linked))
    link(str(tmp_path / "pointer"), linked / ".git", is_dir=False)

    def pg(name: str) -> str | None:
        return wl.protected_glob(tmp_path, rel.format(name), ("secrets",))

    assert pg("real") is None
    assert pg("planted") == "secrets"
    assert pg("linked") == "secrets"
    assert pg("fabricated") == "secrets"
