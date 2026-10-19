"""`export --hard` writes one tar.gz of the JSON, a commits-only bundle of each open lane and
`wt-rc` tree made at export time, and each pause bundle, every bundle object-scanned. Real git, a
bare origin, the real worktree scripts over a tmp workspace. Size: MEDIUM.
"""

from __future__ import annotations

import tarfile
from pathlib import Path

import pytest

from dadaia_workspace import container
from dadaia_workspace.core.exceptions import DadaiaError
from dadaia_workspace.core.models.spec_context import ContextState, SpecContextProject
from tests.fixtures.stores import context_store
from tests.helpers.oslib import write_text
from tests.helpers.privacy_fixtures import aws_key_shape
from tests.helpers.worktree_ws import (
    NEW_JOB,
    commit,
    fixes,
    git,
    make_workspace,
    open_tree,
    run,
)

RC, LANE, PAUSED, PUSHED = (
    "0.5.0/rc-1/wt-rc",
    "0.5.0/wt-backlog-x",
    "0.5.0/wt-backlog-y",
    "0.5.0/wt-backlog-z",
)
ARCHIVE = "workspace-export.tar.gz"


@pytest.fixture
def root(tmp_path: Path) -> Path:
    """A workspace whose context `c` owns repo `r`, with a bare `origin` holding the work branch."""
    (ws := tmp_path / "ws").mkdir()
    make_workspace(ws)
    write_text(ws / ".dadaia/states/spec_contexts.json", '{"contexts": []}')
    context_store(ws / ".dadaia/states").save(
        SpecContextProject("c", ContextState.ALIVE, "r", "", "2026-01-01T00:00:00+00:00")
    )
    repo = ws / "repos/r"
    git(repo, "checkout", "-q", "feature/0.5.0")
    git(tmp_path, "init", "-q", "--bare", str(tmp_path / "origin.git"))
    git(repo, "remote", "add", "origin", str(tmp_path / "origin.git"))
    git(repo, "push", "-q", "origin", "feature/0.5.0")
    return ws


def _export(root: Path) -> Path:
    return container.build_export_service(root).run(hard=True).path


def _members(archive: Path) -> list[str]:
    with tarfile.open(archive) as tar:
        assert all(m.isfile() for m in tar.getmembers())
        return sorted(tar.getnames())


def _refs(root: Path) -> str:
    return git(root / "repos/r", "for-each-ref")


def test_hard_export_carries_the_json_the_open_trees_and_the_pause_bundles(
    root: Path, tmp_path: Path
) -> None:
    repo = root / "repos/r"
    tips = {
        name: commit(open_tree(root, name), "specs/notes.md", f"{name}\n") for name in (RC, LANE)
    }
    commit(open_tree(root, NEW_JOB), "src/job.py")
    paused = commit(tree := open_tree(root, PAUSED), "specs/paused.md")
    assert run(root, "pause", str(tree)).returncode == 0
    pushed = open_tree(root, PUSHED)
    commit(pushed, "specs/pushed.md")
    git(pushed, "push", "-q", "origin", f"wt/{PUSHED}")
    registry = root / ".dadaia/states/spec_contexts.json"
    before, refs = registry.read_bytes(), _refs(root)

    archive = _export(root)

    assert archive == root / ".dadaia/dist" / ARCHIVE
    assert _members(archive) == [
        f"r/{RC}.bundle",
        f"r/{LANE}.bundle",
        f"r/{PAUSED}.bundle",
        "spec-contexts.json",
    ]
    with tarfile.open(archive) as tar:
        tar.extractall(tmp_path / "out", filter="data")
    for name, tip in {**tips, PAUSED: paused}.items():
        bundle = tmp_path / "out" / "r" / f"{name}.bundle"
        assert tip in git(repo, "bundle", "list-heads", str(bundle))
        git(repo, "bundle", "verify", str(bundle))
    assert [p.name for p in root.joinpath(".dadaia/dist").rglob("*.bundle")] == [
        f"{PAUSED.rsplit('/', 1)[-1]}.bundle"
    ]
    assert not tree.exists()
    assert (root / "worktrees/r" / LANE).is_dir() and (root / "worktrees/r" / RC).is_dir()
    assert registry.read_bytes() == before
    assert _refs(root) == refs


def test_a_dirty_open_tree_refuses_with_pauses_fix_and_stays(root: Path) -> None:
    commit(tree := open_tree(root, LANE), "specs/a.md")
    write_text(tree / "specs/a.md", "changed\n")
    (pause_fix,) = fixes(run(root, "pause", str(tree)))

    with pytest.raises(DadaiaError) as refused:
        _export(root)

    assert refused.value.fix == pause_fix.removeprefix("fix: ")
    assert (tree / "specs/a.md").read_text() == "changed\n"
    assert not (root / ".dadaia/dist" / ARCHIVE).exists()


@pytest.mark.parametrize("where", ["open", "paused"])
def test_a_secret_in_a_bundle_refuses_and_leaves_no_archive_and_no_ref(
    root: Path, where: str
) -> None:
    commit(tree := open_tree(root, LANE), "specs/notes.md", f"k={aws_key_shape()}\n")
    if where == "paused":
        assert run(root, "pause", str(tree)).returncode == 0
    refs = _refs(root)

    with pytest.raises(DadaiaError) as refused:
        _export(root)

    assert "specs/notes.md" in str(refused.value) and refused.value.fix
    assert aws_key_shape() not in str(refused.value)
    assert not (root / ".dadaia/dist" / ARCHIVE).exists()
    assert _refs(root) == refs
