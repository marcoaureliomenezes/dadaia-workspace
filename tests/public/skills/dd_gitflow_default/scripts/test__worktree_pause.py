"""`worktree.py pause` bundles one clean lane or `wt-rc` tree (the commits origin lacks) at
`.dadaia/dist/<repo>/<name>.bundle`, removes the tree and its branch; `resume` recreates both from
the bundle and deletes it. Real git, a bare origin, a tmp workspace.
Size: MEDIUM.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

import dadaia_workspace
from tests.fixtures.stores import fake_venv
from tests.helpers.oslib import command, make_executable, read_text, stub_cli, write_text
from tests.helpers.oslib import run as os_run
from tests.helpers.worktree_ws import (
    NEW_JOB,
    NEW_TASK,
    SCRIPT,
    commit,
    fixes,
    git,
    make_workspace,
    open_tree,
    run,
)

RC, BACKLOG = "0.5.0/rc-1/wt-rc", "0.5.0/wt-backlog-x"


@pytest.fixture
def root(tmp_path: Path) -> Path:
    """A workspace whose repo `r` has a bare `origin` holding the work branch."""
    (ws := tmp_path / "ws").mkdir()
    make_workspace(ws)
    repo = ws / "repos/r"
    git(repo, "checkout", "-q", "feature/0.5.0")
    remote = tmp_path / "origin.git"
    git(tmp_path, "init", "-q", "--bare", str(remote))
    git(repo, "remote", "add", "origin", str(remote))
    git(repo, "push", "-q", "origin", "feature/0.5.0")
    return ws


def _bundle(root: Path, name: str) -> Path:
    """Where the bundle of tree *name* sits: `.dadaia/dist/<repo>/<name>.bundle`."""
    *folders, leaf = name.split("/")
    return root.joinpath(".dadaia", "dist", "r", *folders, f"{leaf}.bundle")


def _branch(name: str) -> str:
    return f"wt/{name}"


def _requires(repo: Path, bundle: Path) -> str:
    """What `git bundle verify` says the bundle needs from *repo*."""
    done = os_run(["git", "bundle", "verify", str(bundle)], cwd=repo)
    return done.stdout + done.stderr


@pytest.mark.parametrize("name", [BACKLOG, RC])
def test_pause_then_resume_restores_the_branch_tip_and_tree(root: Path, name: str) -> None:
    repo, tree = root / "repos/r", open_tree(root, name)
    tip = commit(tree, "specs/notes.md", "kept\n")
    snapshot = git(tree, "rev-parse", "HEAD^{tree}")

    paused = run(root, "pause", str(tree))

    assert paused.returncode == 0, paused.stderr
    assert _bundle(root, name).is_file()
    assert not tree.exists()
    assert git(repo, "branch", "--list", _branch(name)) == ""
    resumed = run(root, "resume", str(tree))
    assert resumed.returncode == 0, resumed.stderr
    assert git(tree, "rev-parse", "HEAD").strip() == tip
    assert git(repo, "rev-parse", _branch(name)).strip() == tip
    assert git(tree, "rev-parse", "HEAD^{tree}") == snapshot
    assert read_text(tree / "specs/notes.md") == "kept\n"
    assert git(tree, "status", "--porcelain") == ""
    assert not _bundle(root, name).exists()
    assert not (root / ".dadaia/dist/r").exists()


def test_the_bundle_holds_only_the_commits_origin_lacks(root: Path, tmp_path: Path) -> None:
    tree = open_tree(root, BACKLOG)
    pushed = commit(tree, "specs/a.md")
    git(tree, "push", "-q", "origin", _branch(BACKLOG))
    local = commit(tree, "specs/b.md")

    paused = run(root, "pause", str(tree))

    assert paused.returncode == 0, paused.stderr
    bundle = _bundle(root, BACKLOG)
    assert pushed in _requires(root / "repos/r", bundle)
    fresh = tmp_path / "fresh"
    git(tmp_path, "clone", "-q", str(tmp_path / "origin.git"), str(fresh))
    git(fresh, "fetch", "-q", str(bundle), f"{_branch(BACKLOG)}:{_branch(BACKLOG)}")
    assert git(fresh, "rev-parse", _branch(BACKLOG)).strip() == local
    assert git(fresh, "rev-list", "--count", f"{pushed}..{local}").strip() == "1"


def _lane(root: Path) -> Path:
    tree = open_tree(root, BACKLOG)
    commit(tree, "specs/a.md")
    return tree


def _dirty(root: Path) -> Path:
    write_text((tree := _lane(root)) / "specs/a.md", "changed\n")
    return tree


def _ignored(root: Path) -> Path:
    write_text((tree := _lane(root)) / "notes.scratch", "x")
    return tree


def _job(root: Path) -> Path:
    open_tree(root, RC)
    commit(tree := open_tree(root, NEW_JOB), "src/a.py")
    return tree


def _task(root: Path) -> Path:
    _job(root)
    commit(tree := open_tree(root, NEW_TASK), "src/b.py")
    return tree


def _rc_with_an_open_job(root: Path) -> Path:
    commit(rc := open_tree(root, RC), "specs/a.md")
    open_tree(root, NEW_JOB)
    return rc


def _fully_pushed(root: Path) -> Path:
    git(tree := _lane(root), "push", "-q", "origin", _branch(BACKLOG))
    return tree


def _failing_bundle_verify(root: Path) -> Path:
    """`git bundle verify` fails: a `git` first on PATH that refuses that one subcommand."""
    real = shutil.which("git")
    source = f"""#!python
import subprocess, sys
args = sys.argv[1:]
if ("bundle", "verify") in zip(args, args[1:]):
    sys.exit("error: the bundle is corrupt")
sys.exit(subprocess.call([{real!r}, *args]))
"""
    stub_cli(shim := root.parent / "shim", "git", source)
    os.environ["PATH"] = os.pathsep.join([str(shim), os.environ["PATH"]])
    return _lane(root)


@pytest.mark.parametrize(
    "setup",
    [_dirty, _ignored, _job, _task, _rc_with_an_open_job, _fully_pushed, _failing_bundle_verify],
)
def test_a_refused_pause_prints_one_fix_and_touches_nothing(
    root: Path, monkeypatch: pytest.MonkeyPatch, setup: Callable[[Path], Path]
) -> None:
    monkeypatch.setenv("PATH", os.environ["PATH"])  # restores PATH when a setup shims it
    repo, tree = root / "repos/r", setup(root)
    refs = git(repo, "for-each-ref", "--format=%(refname) %(objectname)")
    state = git(tree, "status", "--porcelain", "--ignored")

    refused = run(root, "pause", str(tree))

    assert refused.returncode == 1, refused.stderr
    assert len(fixes(refused)) == 1, refused.stderr
    assert list((root / ".dadaia").rglob("*.bundle")) == []
    assert git(repo, "for-each-ref", "--format=%(refname) %(objectname)") == refs
    assert git(tree, "status", "--porcelain", "--ignored") == state


_HOOK = Path(dadaia_workspace.__file__).parent / "public/scripts/reference-transaction.sh"


def _install_ref_gate(root: Path) -> None:
    """The `reference-transaction` shim in repo `r`, over a venv that can import the package."""
    fake_venv(root, pth=True)
    shutil.copy(_HOOK, hook := root / "repos/r/.git/hooks/reference-transaction")
    make_executable(hook)


def test_resume_creates_the_branch_through_the_cli_marker(root: Path) -> None:
    repo, tree = root / "repos/r", _lane(root)
    tip = git(tree, "rev-parse", "HEAD").strip()
    _install_ref_gate(root)
    assert run(root, "pause", str(tree)).returncode == 0

    raw = os_run(["git", "-C", str(repo), "branch", _branch(BACKLOG), tip])

    assert raw.returncode != 0
    assert "[ref-gate] BLOCKED" in raw.stderr
    resumed = run(root, "resume", str(tree))
    assert resumed.returncode == 0, resumed.stderr
    assert git(repo, "rev-parse", _branch(BACKLOG)).strip() == tip


def test_a_lane_whose_branch_was_pushed_resumes(root: Path) -> None:
    tree = open_tree(root, BACKLOG)
    commit(tree, "specs/a.md")
    git(tree, "push", "-q", "origin", _branch(BACKLOG))
    tip = commit(tree, "specs/b.md")
    assert run(root, "pause", str(tree)).returncode == 0

    resumed = run(root, "resume", str(tree))

    assert resumed.returncode == 0, resumed.stderr
    assert git(tree, "rev-parse", "HEAD").strip() == tip
    assert git(root / "repos/r", "ls-remote", "--heads", "origin", _branch(BACKLOG)) != ""


def test_resume_refuses_while_the_local_branch_exists(root: Path) -> None:
    repo, tree = root / "repos/r", _lane(root)
    tip = git(tree, "rev-parse", "HEAD").strip()
    assert run(root, "pause", str(tree)).returncode == 0
    git(repo, "branch", _branch(BACKLOG), tip)

    refused = run(root, "resume", str(tree))

    assert refused.returncode == 1, refused.stderr
    assert len(fixes(refused)) == 1, refused.stderr
    assert _bundle(root, BACKLOG).is_file()
    assert not tree.exists()


def test_resume_refuses_with_no_bundle(root: Path) -> None:
    refused = run(root, "resume", str(root / "worktrees/r" / BACKLOG))

    assert refused.returncode == 1, refused.stderr
    assert len(fixes(refused)) == 1, refused.stderr


def test_list_shows_a_paused_tree_whose_exit_is_the_resume_line(root: Path) -> None:
    tree = _lane(root)
    assert run(root, "pause", str(tree)).returncode == 0

    rows = json.loads(run(root, "list", "--json").stdout)

    (row,) = [r for r in rows if r["state"] == "paused"]
    assert row["kind"] == "paused" and row["repo"] == "r" and row["warn"] is False
    assert Path(row["path"]) == tree
    assert row["exit"] == command(sys.executable, str(SCRIPT), "resume", str(tree))
    assert row["fix"] == ""
