"""`export --hard` writes one tar.gz of the JSON, a commits-only bundle of each open lane and
`wt-rc` tree made at export time, and each pause bundle, every bundle object-scanned. Real git, a
bare origin, the real worktree scripts over a tmp workspace. Size: MEDIUM.
"""

from __future__ import annotations

import os
import shutil
import tarfile
from pathlib import Path

import pytest

from dadaia_workspace import container
from dadaia_workspace.core.cli_line import fix_line, git_line
from dadaia_workspace.core.exceptions import DadaiaError, GitSyncError
from dadaia_workspace.core.models.git_scan import GitObjectReadError
from dadaia_workspace.core.models.spec_context import ContextState, SpecContextProject
from dadaia_workspace.core.platform import act
from dadaia_workspace.infrastructure.git_objects import GitSubprocessObjectReader
from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient
from tests.fixtures.harness_env import run_bash, suite_env
from tests.fixtures.stores import context_store
from tests.helpers.oslib import PERMISSIONS_ENFORCED, make_readonly, make_writable, write_text
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


def test_a_worktree_outside_worktrees_is_not_carried_and_does_not_crash(root: Path) -> None:
    commit(open_tree(root, LANE), "specs/notes.md")
    foreign = root / "repos/r/.claude/worktrees/agent-1"
    git(root / "repos/r", "worktree", "add", "-q", str(foreign), "-b", "agent-1")

    assert _members(_export(root)) == [f"r/{LANE}.bundle", "spec-contexts.json"]


def test_a_dirty_tree_with_no_commit_ahead_refuses_with_pauses_fix(root: Path) -> None:
    write_text((tree := open_tree(root, LANE)) / "scripts/ci.py", "changed\n")
    (pause_fix,) = fixes(run(root, "pause", str(tree)))

    with pytest.raises(DadaiaError) as refused:
        _export(root)

    assert refused.value.fix == pause_fix.removeprefix("fix: ")
    assert not (root / ".dadaia/dist" / ARCHIVE).exists()


def test_a_pause_bundle_is_never_dropped_when_its_repo_is_off_disk(
    root: Path, tmp_path: Path
) -> None:
    commit(tree := open_tree(root, PAUSED), "specs/paused.md")
    assert run(root, "pause", str(tree)).returncode == 0
    shutil.move(root / "repos/r", tmp_path / "away")

    with pytest.raises(DadaiaError) as refused:
        _export(root)

    assert PAUSED in str(refused.value)
    assert refused.value.fix == fix_line(root, "context", "alive", "c")
    assert not (root / ".dadaia/dist" / ARCHIVE).exists()


def _refused_scan(root: Path) -> DadaiaError:
    """The refusal of an export whose scan failed: no archive, no scratch path named."""
    with pytest.raises(DadaiaError) as refused:
        _export(root)
    assert not (root / ".dadaia/dist" / ARCHIVE).exists()
    assert ".dadaia/tmp" not in f"{refused.value}\n{refused.value.fix}"
    return refused.value


def _follow(root: Path, fix: str) -> None:
    """Run the refusal's one `fix:` line as an agent would, from the workspace root."""
    env = suite_env(
        os.environ, Path.home(), overrides={"HOME": str(root), "GIT_CONFIG_NOSYSTEM": "1"}
    )
    run_bash(fix, cwd=root, env=env, check=True)


def _paused(root: Path) -> Path:
    commit(tree := open_tree(root, PAUSED), "specs/paused.md")
    assert run(root, "pause", str(tree)).returncode == 0
    return root / ".dadaia/dist/r" / f"{PAUSED}.bundle"


@pytest.mark.timeout(15)
@pytest.mark.parametrize(
    "header",
    [b"# v2 git bundle\n", b"# v2 git bundle\n-\n\n", b"# v2 git bundle\n-\xff\xfe x\n\n"],
    ids=["truncated", "bare-prerequisite", "non-utf8-prerequisite"],
)
def test_a_damaged_pause_bundle_is_the_operators_ruling_and_is_kept(
    root: Path, header: bytes
) -> None:
    (bundle := _paused(root)).write_bytes(header)

    refused = _refused_scan(root)

    assert refused.fix == act(
        "operator", f"rule whether {bundle} is restored from a copy or discarded"
    )
    assert bundle.read_bytes() == header


def test_a_pause_bundle_missing_its_prerequisites_refuses_with_fetch_and_then_exports(
    root: Path, tmp_path: Path
) -> None:
    bundle = _paused(root)
    shutil.rmtree(root / "repos/r")
    git(root / "repos", "init", "-q", "r")
    git(repo := root / "repos/r", "remote", "add", "origin", str(tmp_path / "origin.git"))

    refused = _refused_scan(root)

    assert refused.fix == git_line(repo, "fetch", "origin")
    assert bundle.is_file()
    _follow(root, refused.fix)
    assert f"r/{PAUSED}.bundle" in _members(_export(root))


@pytest.mark.skipif(not PERMISSIONS_ENFORCED, reason="permissions do not bind this process")
def test_an_unreadable_pause_bundle_names_the_file_and_exports_once_readable(root: Path) -> None:
    bundle = _paused(root)
    make_readonly(bundle, locked=True)
    try:
        refused = _refused_scan(root)
    finally:
        make_writable(bundle)

    assert refused.fix == act("agent", f"make {bundle} readable, then run the export again")
    assert f"r/{PAUSED}.bundle" in _members(_export(root))


def test_a_git_object_read_failure_refuses_with_fsck_and_then_exports(
    root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    commit(open_tree(root, LANE), "specs/notes.md")

    def broken(*_args: object, **_kwargs: object) -> object:
        raise GitObjectReadError("listing the range failed")

    monkeypatch.setattr(GitSubprocessObjectReader, "new_objects", broken)
    refused = _refused_scan(root)

    assert refused.fix == git_line(root / "repos/r", "fsck")
    monkeypatch.undo()
    _follow(root, refused.fix)
    assert f"r/{LANE}.bundle" in _members(_export(root))


def test_git_that_cannot_run_refuses_with_the_push_gates_fix(
    root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    commit(open_tree(root, LANE), "specs/notes.md")

    def missing(*_args: object, **_kwargs: object) -> str:
        raise FileNotFoundError("git")

    monkeypatch.setattr(GitSubprocessClient, "git", missing)

    assert _refused_scan(root).fix == act("operator", "make git runnable here")


def test_a_dirty_job_tree_is_not_carried_and_does_not_refuse(root: Path) -> None:
    open_tree(root, RC)
    commit(job := open_tree(root, NEW_JOB), "src/job.py")
    write_text(job / "src/job.py", "changed\n")
    commit(open_tree(root, LANE), "specs/notes.md")

    assert _members(_export(root)) == [f"r/{LANE}.bundle", "spec-contexts.json"]


def test_a_symlinked_pause_bundle_refuses_and_is_never_archived(root: Path, tmp_path: Path) -> None:
    commit(tree := open_tree(root, PAUSED), "specs/paused.md")
    assert run(root, "pause", str(tree)).returncode == 0
    bundle = root / ".dadaia/dist/r" / f"{PAUSED}.bundle"
    elsewhere = tmp_path / "elsewhere.bundle"
    bundle.replace(elsewhere)
    bundle.symlink_to(elsewhere)

    with pytest.raises(DadaiaError) as refused:
        _export(root)

    assert PAUSED in str(refused.value) and refused.value.fix
    assert not (root / ".dadaia/dist" / ARCHIVE).exists()


@pytest.mark.skipif(not PERMISSIONS_ENFORCED, reason="permissions do not bind this process")
def test_a_scratch_dir_that_cannot_be_created_refuses_with_the_space_act_and_then_exports(
    root: Path,
) -> None:
    commit(open_tree(root, LANE), "specs/notes.md")
    (tmp := root / ".dadaia/tmp").mkdir(parents=True, exist_ok=True)
    make_readonly(tmp)
    try:
        with pytest.raises(DadaiaError) as refused:
            _export(root)
    finally:
        make_writable(tmp)

    assert refused.value.fix == act(
        "agent", f"free space and write permission under {tmp}, then rerun the export"
    )
    assert not (root / ".dadaia/dist" / ARCHIVE).exists()
    assert f"r/{LANE}.bundle" in _members(_export(root))
