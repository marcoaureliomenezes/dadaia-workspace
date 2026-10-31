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
from tests.helpers.oslib import (
    PERMISSIONS_ENFORCED,
    command,
    make_executable,
    make_readonly,
    make_writable,
    read_text,
    stub_cli,
    write_text,
)
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

RC, BACKLOG, HOTFIX = "0.5.0/rc-1/wt-rc", "0.5.0/wt-backlog-x", "0.5.0/wt-hotfix-a-bug"


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


@pytest.mark.parametrize("name", [BACKLOG, RC, HOTFIX])
def test_pause_then_resume_restores_the_branch_tip_and_tree(root: Path, name: str) -> None:
    repo = root / "repos/r"
    if name == HOTFIX:  # a hotfix lane is the fix of one open bug on the work branch, never pushed
        commit(repo, "specs/bugs/BUGS.jsonl", '{"id": "a-bug", "status": "open"}\n')
        git(repo, "push", "-q", "origin", "feature/0.5.0")
    tree = open_tree(root, name)
    tip = commit(tree, "specs/notes.md", "kept\n")
    snapshot = git(tree, "rev-parse", "HEAD^{tree}")

    paused = run(root, "pause", str(tree))

    assert paused.returncode == 0, paused.stderr
    assert _bundle(root, name).is_file()
    assert not tree.exists()
    assert not (root / "worktrees/r/0.5.0").exists()
    assert git(repo, "branch", "--list", _branch(name)) == ""
    resumed = run(root, "resume", str(tree))
    assert resumed.returncode == 0, resumed.stderr
    assert git(tree, "rev-parse", "HEAD").strip() == tip
    assert git(repo, "rev-parse", _branch(name)).strip() == tip
    assert git(tree, "rev-parse", "HEAD^{tree}") == snapshot
    assert read_text(tree / "specs/notes.md") == "kept\n"
    assert git(tree, "status", "--porcelain") == ""
    assert (root / "worktrees/r/0.5.0/AGENTS.md").is_file()
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
    assert [p for p in (root / ".dadaia").rglob("tmp*")] == []
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


def test_a_resumed_tree_is_locked_as_new_locks_it(root: Path) -> None:
    repo, tree = root / "repos/r", _lane(root)
    assert run(root, "pause", str(tree)).returncode == 0

    assert run(root, "resume", str(tree)).returncode == 0

    assert f"locked dadaia:{BACKLOG}" in git(repo, "worktree", "list", "--porcelain").splitlines()


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


def test_resume_onto_an_occupied_tree_path_refuses_and_leaves_no_branch(root: Path) -> None:
    repo, tree = root / "repos/r", _lane(root)
    assert run(root, "pause", str(tree)).returncode == 0
    tree.mkdir(parents=True, exist_ok=True)
    write_text(tree / "stray.txt", "x")

    refused = run(root, "resume", str(tree))

    assert refused.returncode == 1, refused.stderr
    assert len(fixes(refused)) == 1, refused.stderr
    assert git(repo, "branch", "--list", _branch(BACKLOG)) == ""
    assert _bundle(root, BACKLOG).is_file()


def test_a_refused_pause_for_ignored_files_names_them_and_a_cache_is_not_one(root: Path) -> None:
    tree = _ignored(root)
    (tree / "__pycache__").mkdir()
    write_text(tree / "__pycache__/m.pyc", "x")

    refused = run(root, "pause", str(tree))

    assert refused.returncode == 1, refused.stderr
    assert "notes.scratch" in refused.stderr
    assert "__pycache__" not in refused.stderr


def test_resume_refuses_with_no_bundle(root: Path) -> None:
    refused = run(root, "resume", str(root / "worktrees/r" / BACKLOG))

    assert refused.returncode == 1, refused.stderr
    assert len(fixes(refused)) == 1, refused.stderr


@pytest.mark.parametrize("name", [BACKLOG, RC])
def test_list_shows_a_paused_tree_whose_exit_is_the_resume_line(root: Path, name: str) -> None:
    commit(tree := open_tree(root, name), "specs/a.md")
    assert run(root, "pause", str(tree)).returncode == 0

    rows = json.loads(run(root, "list", "--json").stdout)

    (row,) = rows  # no stray level folder beside the paused row
    assert row["state"] == "paused"
    assert row["kind"] == "paused" and row["repo"] == "r" and row["warn"] is False
    assert Path(row["path"]) == tree
    assert row["exit"] == command(sys.executable, str(SCRIPT), "resume", str(tree))
    assert row["fix"] == ""


_SKILL = (
    Path(__file__).resolve().parents[5] / "dadaia_workspace/public/skills/dd-cli-library/SKILL.md"
)


def test_the_dist_writer_sentence_names_worktree_pause_and_resume() -> None:
    """The skill's sentence listing what writes `.dadaia/dist/` names every verb that does."""
    (sentence,) = [ln for ln in read_text(_SKILL).splitlines() if ".dadaia/dist/" in ln]

    assert "`worktree pause`" in sentence
    assert "`worktree resume`" in sentence


@pytest.mark.skipif(not PERMISSIONS_ENFORCED, reason="needs a folder this process cannot empty")
def test_a_folder_git_cannot_delete_is_named_and_the_rerun_ends_the_pause(root: Path) -> None:
    make_readonly((tree := _lane(root)) / "specs")
    aside = root.parent / "aside"
    # the bundle is written, git forgot the tree, the folder stays
    for _ in range(2):
        refused = run(root, "pause", str(tree))
        assert refused.returncode == 1
        (fix,) = fixes(refused)
        assert fix == f"fix: Agent action: stop what holds files open in {tree}, then move the folder {tree} out of the lane path (it may hold work)"  # fmt: skip
    tree.rename(aside)
    make_writable(aside / "specs")
    done = run(root, "pause", str(tree))
    assert done.returncode == 0, done.stderr
    assert _bundle(root, BACKLOG).is_file()
    assert git(root / "repos/r", "branch", "--list", _branch(BACKLOG)) == ""
