"""AC1.3 (rc-9, ADR 0191): `worktree.py new` opens one tree per job or task — each name shape;
an old-grammar name refused — and `list`; AC1.11 (T-050-101): the
one venv. Size: MEDIUM (real git in a tmp workspace, never the live instance).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from tests.helpers.worktree_ws import JOB, TASK, associate, make_workspace
from tests.helpers.worktree_ws import fixes as _fixes
from tests.helpers.worktree_ws import git as _git
from tests.helpers.worktree_ws import run as _run

pytestmark = pytest.mark.integration


@pytest.fixture
def root(tmp_path: Path) -> Path:
    return make_workspace(tmp_path)


def test_new_makes_each_shape_on_its_branch_and_base(root: Path) -> None:
    repo = root / "repos/r"
    ahead = _git(repo, "commit-tree", "HEAD^{tree}", "-p", "HEAD", "-m", "ahead").strip()
    _git(repo, "branch", "-f", "feature/0.5.0", ahead)  # the start point is the work branch
    for name in (JOB, "0.5.0-rc1/define", "0.5.0-rc1/reconcile", "backlog/an-idea", TASK):
        result = _run(root, "new", "r", name)
        assert (result.returncode, result.stdout) == (0, f"[ok] {root}/worktrees/r/{name}\n")
    assert _git(repo, "rev-parse", "wt/0.5.0-rc1/define").strip() == ahead
    porcelain = _git(repo, "worktree", "list", "--porcelain").splitlines()
    assert sorted(x for x in porcelain if x.startswith("locked")) == [
        "locked dadaia:0.5.0-rc1/define",
        "locked dadaia:0.5.0-rc1/j1",
        "locked dadaia:0.5.0-rc1/j1--J1.S1.T1",
        "locked dadaia:0.5.0-rc1/reconcile",
        "locked dadaia:backlog/an-idea",
    ]


@pytest.mark.parametrize("name", ["0.5.0a-impl", "0.5.0b-release", "0.4.9-rc1/j1", "0.5.0-rc1/J1"])
def test_an_old_grammar_or_foreign_name_refuses(root: Path, name: str) -> None:
    result = _run(root, "new", "r", name)
    assert result.returncode == 1 and not (root / "worktrees/r").exists()
    assert [f.split(" ", 2)[2] for f in _fixes(result)] == [f"{_script()} list"]


def _script() -> str:
    return str(Path(__file__).resolve().parents[2] / "dadaia_workspace/public/skills"
               "/dd-gitflow-default/scripts/worktree.py")  # fmt: skip


def test_a_task_needs_its_job_branch_and_a_sixth_task_refuses(root: Path) -> None:
    """AC1.3: a task is cut from its job branch; 5 task worktrees open per rc at most."""
    orphan = _run(root, "new", "r", TASK)
    assert orphan.returncode == 1 and _fixes(orphan)[0].endswith(f"worktree.py new r {JOB}")
    assert _run(root, "new", "r", JOB).returncode == 0
    for task in range(1, 6):
        assert _run(root, "new", "r", f"{JOB}--T-{task}").returncode == 0
    sixth = _run(root, "new", "r", f"{JOB}--T-6")
    assert sixth.returncode == 1  # a commit-less task's exit is clean
    assert _fixes(sixth)[0].endswith(f"worktree.py clean {root}/worktrees/r/{JOB}--T-1")
    assert _run(root, "new", "r", "0.5.0-rc1/j2").returncode == 0  # the cap counts tasks only


def test_no_work_branch_refuses_with_a_fix_that_creates_it(root: Path) -> None:
    repo = root / "repos/r"
    _git(repo, "branch", "-D", "feature/0.5.0")
    result = _run(root, "new", "r", JOB)
    assert result.returncode == 1
    (fix,) = _fixes(result)
    assert fix == f"fix: git -C {repo} branch feature/0.1.0 dev"  # the flow's integration


@pytest.mark.parametrize(
    ("spec", "code", "out"),
    [("Approved", 0, "[ok] {root}/worktrees/a/0.5.0-rc1/j1"), ("Draft", 1, "")],
)
def test_an_associated_job_reads_the_main_repos_spec(
    root: Path, spec: str, code: int, out: str
) -> None:
    """AC11.0: `a` carries no specs; its job is gated by `r`'s SPEC on `r`'s work branch."""
    associate(root, spec)
    result = _run(root, "new", "a", JOB)
    assert (result.returncode, result.stdout.strip()) == (code, out.format(root=root))
    assert [f.split(" new ")[-1] for f in _fixes(result)] == (
        [] if code == 0 else ["r 0.5.0-rc1/define"]
    )
    assert _run(root, "new", "a", "0.5.0-rc1/define").returncode == 0  # definition needs none


def test_symlinked_worktrees_component_refuses(
    root: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    (root / "worktrees").symlink_to(tmp_path_factory.mktemp("elsewhere"))
    result = _run(root, "new", "r", JOB)
    assert result.returncode == 1 and len(_fixes(result)) == 1
    assert "symlink" in result.stderr


def test_list_reports_ours_with_ahead_and_dirty_and_a_native_one_as_foreign(root: Path) -> None:
    repo = root / "repos/r"
    assert _run(root, "new", "r", JOB).returncode == 0
    _git(repo, "worktree", "add", "-q", str(root / "native"), "-b", "native")
    (root / "worktrees/r/0.5.0-rc1/stray").mkdir()
    tree = root / "worktrees/r" / JOB
    (tree / "x.py").write_text("x = 1\n")
    _git(tree, "add", "x.py")
    _git(tree, "commit", "-qm", "x")
    (tree / "y.py").write_text("")
    result = _run(root, "list", "--json")
    assert result.returncode == 0, result.stderr
    by_state = {row["state"]: row for row in json.loads(result.stdout)}
    row = by_state["open"]  # dirty: never `ready`, no fix shown, its exit still the merge
    assert row["repo"] == "r" and row["name"] == JOB
    assert row["ahead"] == 1 and row["dirty"] is True and row["age_hours"] >= 0
    assert row["fix"] == "" and row["exit"].endswith(f"merge {tree}")
    assert by_state["foreign"]["path"] == str(root / "native") and by_state["foreign"]["exit"] == ""
    assert by_state["unregistered"]["path"] == str(root / "worktrees/r/0.5.0-rc1/stray")
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
