"""Every skill script that looks for the workspace above its cwd or itself skips a root
`DADAIA_FENCED_ROOTS` fences — the worktree script's root, the dev-server registry, the release
closure's worktree wait, and the fix line a missing specs tree prints. Size: MEDIUM (real git and
scripts in a tmp workspace)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from dadaia_workspace.infrastructure.ledger_scripts import load_owner
from tests.fixtures.harness_env import suite_env
from tests.helpers.oslib import replace, write_text
from tests.helpers.oslib import run as os_run
from tests.helpers.skill_scripts import stage_skill_scripts
from tests.helpers.worktree_ws import NEW_JOB, NEW_TASK, commit, git, make_workspace, run


@pytest.fixture
def ws(tmp_path: Path) -> Path:
    """A workspace whose own skill scripts are staged inside it, and a folder in it with no repo."""
    (root := tmp_path / "ws").mkdir()
    make_workspace(root)
    skills = (
        "dd-gitflow-default",
        "dd-bug-resolution",
        "dd-cli-library",
        "dd-release-implementation",
    )
    for skill in skills:
        stage_skill_scripts(skill, root / ".agents/skills" / skill / "scripts")
    (root / "folder").mkdir()
    return root


def _fenced(ws: Path, script: str, *argv: str) -> subprocess.CompletedProcess[str]:
    """*script* of the staged skills, run from `ws/folder` with the workspace fenced."""
    path = next((ws / ".agents/skills").glob(f"*/scripts/{script}"))
    env = suite_env(os.environ, Path.home(), overrides={"DADAIA_FENCED_ROOTS": str(ws)})
    return os_run([sys.executable, str(path), *argv], cwd=ws / "folder", env=env)  # fmt: skip


def test_the_worktree_script_finds_no_root_in_a_fenced_workspace(ws: Path) -> None:
    refused = _fenced(ws, "worktree.py", "list")
    assert refused.returncode == 1
    assert "no workspace root above the cwd or this script" in refused.stderr


def test_the_dev_server_registry_finds_no_sentinel_in_a_fenced_workspace(ws: Path) -> None:
    refused = _fenced(ws, "registry.py", "list")
    assert refused.returncode == 1
    assert "no workspace sentinel above the cwd" in refused.stderr


def test_a_missing_specs_tree_names_no_fenced_workspace_cli(ws: Path) -> None:
    refused = _fenced(ws, "bugs.py", "status")
    assert refused.returncode == 1
    assert [x for x in refused.stderr.splitlines() if x.startswith("fix: ")] == [
        "fix: Agent action: re-run inside a repo that holds its specs/ tree"
    ]


def test_the_closure_waits_for_no_worktree_of_a_fenced_workspace(
    ws: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    git(ws / "repos/r", "checkout", "-q", "feature/0.5.0")
    assert run(ws, "new", "r", "0.5.0/rc-1/wt-rc").returncode == 0
    assert run(ws, "new", "r", NEW_JOB).returncode == 0  # an open tree: unfenced, closure waits
    wait = load_owner("dd-release-implementation", "_release_phase")._refuse_open_worktrees
    monkeypatch.setenv("DADAIA_FENCED_ROOTS", str(ws))
    assert wait(ws / "repos/r/specs") is None


LANE = "0.5.0/wt-backlog-x"


def _open_drafted(ws: Path, *names: str) -> None:
    """Each of *names* opened as a tree of repo `r` carrying one commit, so it holds an exit."""
    git(ws / "repos/r", "checkout", "-q", "feature/0.5.0")
    for name in names:
        assert run(ws, "new", "r", name).returncode == 0
        tree = ws / "worktrees/r" / name
        write_text(tree / "draft.scratch.md", f"{name}\n")
        git(tree, "add", "-f", "draft.scratch.md")
        git(tree, "commit", "-qm", "draft")


@pytest.mark.parametrize(
    ("others", "held", "legacy"),
    [
        (("0.5.0/rc-2/wt-rc",), 0, False),
        (("0.5.0/rc-2/wt-rc", "0.5.0/rc-3/wt-rc"), 0, False),
        (("0.5.0/rc-2/wt-rc",), 0, True),
        ((NEW_JOB,), 1, False),
        ((NEW_JOB, NEW_TASK), 2, False),
        ((LANE,), 1, False),
    ],
)
def test_the_closure_waits_for_a_job_task_or_lane_tree_and_spares_every_wt_rc_tree(
    ws: Path, others: tuple[str, ...], held: int, legacy: bool
) -> None:
    """The closure of the live candidate waits for every open job, task or lane tree of the
    repo and spares the `wt-rc` trees of any candidate. A legacy release folder with no
    `rc-<N>/` counts as the first candidate."""
    _open_drafted(ws, "0.5.0/rc-1/wt-rc", *others)
    wait = load_owner("dd-release-implementation", "_release_phase")._refuse_open_worktrees
    reconcile_specs = ws / "worktrees/r/0.5.0/rc-1/wt-rc/specs"
    if legacy:
        release = reconcile_specs / "releases/0.5.0"
        for entry in (release / "rc-1").iterdir():
            replace(entry, release / entry.name)
        (release / "rc-1").rmdir()
    if not held:
        assert wait(reconcile_specs) is None
    else:
        with pytest.raises(
            load_owner("dd-release-implementation", "_release_phase").Refusal,
            match=rf"repos/r still holds {held} open wt/\* worktree\(s\)",
        ):
            wait(reconcile_specs)


@pytest.mark.parametrize(("own", "before"), [(NEW_JOB, ("0.5.0/rc-1/wt-rc",)), (LANE, ())])
def test_the_closure_spares_the_tree_it_runs_from_whatever_its_kind(
    ws: Path, own: str, before: tuple[str, ...]
) -> None:
    """A job tree needs its candidate's `wt-rc` open first, and that one is spared too."""
    _open_drafted(ws, *before, own)
    wait = load_owner("dd-release-implementation", "_release_phase")._refuse_open_worktrees
    assert wait(ws / "worktrees/r" / own / "specs") is None


def _legacy(ws: Path, name: str, *, tree: bool = True) -> Path:
    """The old-grammar branch `wt/<name>` with one unmerged commit, on a tree at `worktrees/r/<name>`
    (`tree=False`: the tree removed, the branch left an orphan)."""
    repo, path = ws / "repos/r", ws / "worktrees/r" / name
    git(repo, "worktree", "add", "-q", "-b", f"wt/{name}", str(path), "feature/0.5.0")
    commit(path, "legacy.txt")
    if not tree:
        git(repo, "worktree", "remove", str(path))
    return path


@pytest.mark.parametrize("tree", [True, False], ids=["open-tree", "orphan-branch"])
def test_the_closure_waits_for_an_old_layout_job_tree_or_orphan_branch(
    ws: Path, tree: bool
) -> None:
    """A tree or branch of the old grammar is still work: the closure of the new layout holds it."""
    _open_drafted(ws, "0.5.0/rc-1/wt-rc")
    _legacy(ws, "0.5.0-rc1/j1", tree=tree)
    mod = load_owner("dd-release-implementation", "_release_phase")
    with pytest.raises(mod.Refusal, match=r"repos/r still holds 1 open wt/\* worktree\(s\)"):
        mod._refuse_open_worktrees(ws / "worktrees/r/0.5.0/rc-1/wt-rc/specs")


@pytest.mark.parametrize(("others", "held"), [((), 0), (("0.5.0-rc1/j1",), 1)])
def test_the_closure_run_from_an_old_layout_tree_spares_it_and_waits_for_the_others(
    ws: Path, others: tuple[str, ...], held: int
) -> None:
    """From an old-layout `reconcile` tree the closure spares its own tree; another open
    old-layout tree still holds it."""
    git(ws / "repos/r", "checkout", "-q", "feature/0.5.0")
    own = _legacy(ws, "0.5.0-rc1/reconcile")
    for name in others:
        _legacy(ws, name)
    mod = load_owner("dd-release-implementation", "_release_phase")
    if not held:
        assert mod._refuse_open_worktrees(own / "specs") is None
    else:
        with pytest.raises(mod.Refusal, match=rf"repos/r still holds {held} open wt/\* worktree"):
            mod._refuse_open_worktrees(own / "specs")
