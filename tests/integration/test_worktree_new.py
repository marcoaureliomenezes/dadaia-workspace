"""Intent: CONTRACT — AC1.7 (T-050-95): `worktree.py new` and `list`; AC1.11 (T-050-101):
the one venv. Size: MEDIUM (real git in a tmp workspace, never the live instance).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from tests.helpers.worktree_ws import associate, make_workspace
from tests.helpers.worktree_ws import fixes as _fixes
from tests.helpers.worktree_ws import git as _git
from tests.helpers.worktree_ws import run as _run

pytestmark = pytest.mark.integration


@pytest.fixture
def root(tmp_path: Path) -> Path:
    return make_workspace(tmp_path)


def test_new_branches_and_locks(root: Path) -> None:
    repo = root / "repos/r"
    ahead = _git(repo, "commit-tree", "HEAD^{tree}", "-p", "HEAD", "-m", "ahead").strip()
    _git(repo, "branch", "-f", "feature/0.5.0", ahead)  # the start point is the work branch
    assert _run(root, "new", "r", "--kind", "impl").returncode == 0
    second = _run(root, "new", "r", "--kind", "backlog")
    assert second.returncode == 0, second.stderr
    assert (root / "worktrees/r/0.5.0a-impl").is_dir()
    assert (root / "worktrees/r/0.5.0b-backlog").is_dir()
    assert _git(repo, "rev-parse", "wt/0.5.0a-impl").strip() == ahead
    porcelain = _git(repo, "worktree", "list", "--porcelain").splitlines()
    assert [x for x in porcelain if x.startswith("locked")] == [
        "locked dadaia:impl:0.5.0a",
        "locked dadaia:backlog:0.5.0b",
    ]


def test_no_work_branch_refuses_with_a_fix_that_creates_it(root: Path) -> None:
    repo = root / "repos/r"
    _git(repo, "branch", "-D", "feature/0.5.0")
    result = _run(root, "new", "r", "--kind", "bug")
    assert result.returncode == 1
    (fix,) = _fixes(result)
    assert fix == f"fix: git -C {repo} branch feature/0.1.0 dev"  # the flow's integration


def test_impl_needs_an_approved_trio_in_the_live_candidate(root: Path) -> None:
    """ADR 0150 (3): the trio read is the highest `rc-<N>/` on the work branch."""
    repo = root / "repos/r"
    _git(repo, "checkout", "-q", "feature/0.5.0")
    (repo / "specs/releases/0.5.0/rc-10").mkdir()
    for doc in ("SPEC", "PLAN", "TASKS"):
        status = "Draft" if doc == "PLAN" else "Approved"
        (repo / f"specs/releases/0.5.0/rc-10/{doc}.md").write_text(f"**Status:** {status}\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "draft")
    _git(repo, "checkout", "-q", "main")
    result = _run(root, "new", "r", "--kind", "impl")
    assert result.returncode == 1 and len(_fixes(result)) == 1
    assert "PLAN" in result.stderr
    assert _run(root, "new", "r", "--kind", "bug").returncode == 0


@pytest.mark.parametrize(
    ("plan", "code", "out"),
    [("Approved", 0, "[ok] {root}/worktrees/a/0.5.0a-impl"), ("Draft", 1, "")],
)
def test_an_associated_impl_reads_the_main_repos_trio(
    root: Path, plan: str, code: int, out: str
) -> None:
    """AC11.0: `a` carries no specs; its `impl` is gated by `r`'s trio on `r`'s work branch."""
    associate(root, plan)
    result = _run(root, "new", "a", "--kind", "impl")
    assert (result.returncode, result.stdout.strip()) == (code, out.format(root=root))
    assert [f.split(" new ")[-1] for f in _fixes(result)] == (
        [] if code == 0 else ["r --kind release"]
    )


def test_caps_refuse_naming_an_existing_worktree(root: Path) -> None:
    for _ in range(5):
        assert _run(root, "new", "r", "--kind", "impl").returncode == 0
    sixth = _run(root, "new", "r", "--kind", "impl")
    assert sixth.returncode == 1  # a commit-less worktree's exit is clean (ADR 0128)
    assert _fixes(sixth)[0].endswith(f"worktree.py clean {root}/worktrees/r/0.5.0a-impl")
    tree = root / "worktrees/r/0.5.0a-impl"
    (tree / "x.py").write_text("")
    _git(tree, "add", "x.py")
    _git(tree, "commit", "-qm", "x")
    assert _fixes(_run(root, "new", "r", "--kind", "impl"))[0].endswith(f"merge {tree}")
    assert _run(root, "new", "r", "--kind", "release").returncode == 0
    second_release = _run(root, "new", "r", "--kind", "release")
    assert second_release.returncode == 1
    assert "0.5.0f-release" in _fixes(second_release)[0]


def test_letters_past_z_refuse_naming_a_worktree_exit(root: Path) -> None:
    repo, tree = root / "repos/r", root / "worktrees/r/0.5.0a-bug"
    assert _run(root, "new", "r", "--kind", "bug").returncode == 0
    (tree / "x.py").write_text("")
    _git(tree, "add", "x.py")
    _git(tree, "commit", "-qm", "x")
    for letter in "bcdefghijklmnopqrstuvwxyz":
        _git(repo, "branch", f"wt/0.5.0{letter}-bug", "feature/0.5.0")
    result = _run(root, "new", "r", "--kind", "bug")
    assert result.returncode == 1 and _fixes(result)[0].endswith(f"merge {tree}")


def test_symlinked_worktrees_component_refuses(
    root: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    (root / "worktrees").symlink_to(tmp_path_factory.mktemp("elsewhere"))
    result = _run(root, "new", "r", "--kind", "bug")
    assert result.returncode == 1 and len(_fixes(result)) == 1
    assert "symlink" in result.stderr


def test_list_reports_ours_with_ahead_and_dirty_and_a_native_one_as_foreign(root: Path) -> None:
    repo = root / "repos/r"
    assert _run(root, "new", "r", "--kind", "impl").returncode == 0
    _git(repo, "worktree", "add", "-q", str(root / "native"), "-b", "native")
    tree = root / "worktrees/r/0.5.0a-impl"
    (tree / "x.py").write_text("x = 1\n")
    _git(tree, "add", "x.py")
    _git(tree, "commit", "-qm", "x")
    (tree / "y.py").write_text("")
    result = _run(root, "list", "--json")
    assert result.returncode == 0, result.stderr
    by_state = {row["state"]: row for row in json.loads(result.stdout)}
    row = by_state["open"]  # dirty: never `ready`, no fix shown, its exit still the merge
    assert row["repo"] == "r" and row["kind"] == "impl" and row["id"] == "0.5.0a"
    assert row["ahead"] == 1 and row["dirty"] is True and row["age_hours"] >= 0
    assert row["fix"] == "" and row["exit"].endswith(f"merge {tree}")
    assert by_state["foreign"]["path"] == str(root / "native") and by_state["foreign"]["exit"] == ""
    assert not list((root / ".dadaia/states").glob("*worktree*"))


def test_the_one_venv_imports_the_checkout_it_runs_from() -> None:
    """AC1.11 (ADR 0113): the shared venv's editable install points at repos/, yet a child
    spawned from the suite's hermetic cwd imports THIS checkout (the conftest PYTHONPATH
    pin), and no checkout carries its own venv."""
    checkout = Path(__file__).resolve().parents[2]
    child = subprocess.run(
        [sys.executable, "-c", "import dadaia_workspace; print(dadaia_workspace.__file__)"],
        capture_output=True, text=True, check=True,
    )  # fmt: skip
    assert Path(child.stdout.strip()).resolve().is_relative_to(checkout)
    assert not (checkout / ".venv").exists()
