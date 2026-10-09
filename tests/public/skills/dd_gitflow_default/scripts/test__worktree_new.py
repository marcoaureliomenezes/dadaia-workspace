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

from dadaia_workspace.core.cli_line import git_line, shell_line
from tests.helpers.worktree_ws import JOB, TASK, approve, associate, commit, make_workspace
from tests.helpers.worktree_ws import fixes as _fixes
from tests.helpers.worktree_ws import git as _git
from tests.helpers.worktree_ws import run as _run


@pytest.fixture
def root(tmp_path: Path) -> Path:
    return make_workspace(tmp_path)


def test_new_makes_each_shape_on_its_branch_and_base(root: Path) -> None:
    repo = root / "repos/r"
    ahead = _git(repo, "commit-tree", "HEAD^{tree}", "-p", "HEAD", "-m", "ahead").strip()
    _git(repo, "branch", "-f", "feature/0.5.0", ahead)  # the start point is the work branch
    for name in (JOB, "0.5.0-rc1/define", "0.5.0-rc1/reconcile", "backlog/an-idea", TASK):
        result = _run(root, "new", "r", name)
        assert (result.returncode, result.stdout) == (0, f"[ok] {root / 'worktrees/r' / name}\n")
    assert _git(repo, "rev-parse", "wt/0.5.0-rc1/define").strip() == ahead
    porcelain = _git(repo, "worktree", "list", "--porcelain").splitlines()
    assert sorted(x for x in porcelain if x.startswith("locked")) == [
        "locked dadaia:0.5.0-rc1/define",
        "locked dadaia:0.5.0-rc1/j1",
        "locked dadaia:0.5.0-rc1/j1--J1.T1",
        "locked dadaia:0.5.0-rc1/reconcile",
        "locked dadaia:backlog/an-idea",
    ]


@pytest.mark.parametrize("live_release", [True, False], ids=["live-release", "no-release"])
def test_a_plain_worktree_uses_the_release_work_branch_or_checked_out_branch(
    root: Path, live_release: bool
) -> None:
    repo = root / "repos/r"
    if live_release:
        ahead = _git(repo, "commit-tree", "HEAD^{tree}", "-p", "HEAD", "-m", "work").strip()
        _git(repo, "branch", "-f", "feature/0.5.0", ahead)
        expected = ahead
    else:
        _git(repo, "rm", "-rq", "specs/releases")
        _git(repo, "commit", "-qm", "no release")
        expected = _git(repo, "rev-parse", "HEAD").strip()

    opened = _run(root, "new", "r", "maintenance")

    assert opened.returncode == 0, opened.stderr
    assert _git(repo, "rev-parse", "wt/maintenance").strip() == expected
    assert (root / "worktrees/r/maintenance").is_dir()


@pytest.mark.parametrize("name", ["0.5.0a-impl", "0.5.0b-release", "0.4.9-rc1/j1", "0.5.0-rc1/J1"])
def test_an_old_grammar_or_foreign_name_refuses(root: Path, name: str) -> None:
    result = _run(root, "new", "r", name)
    assert result.returncode == 1 and not (root / "worktrees/r").exists()
    assert [f.removeprefix("fix: ") for f in _fixes(result)] == [f"{_script()} list"]


def _script() -> str:
    """The script prefix of a fix line, as the product's `script()` prints it."""
    return shell_line(sys.executable, str(Path(__file__).resolve().parents[5] / "dadaia_workspace/public/skills"
               "/dd-gitflow-default/scripts/worktree.py"))  # fmt: skip


def _word(path: Path) -> str:
    """*path* as one word of a fix line, as `cli_line.shell_line` spells it."""
    return shell_line("x", str(path)).split(" ", 1)[1]


def test_a_task_needs_its_job_branch_and_a_sixth_task_refuses(root: Path) -> None:
    """AC1.3: a task is cut from its job branch; 5 task worktrees open per rc at most."""
    orphan = _run(root, "new", "r", TASK)
    assert orphan.returncode == 1 and _fixes(orphan)[0].endswith(f"worktree.py new r {JOB}")
    assert _run(root, "new", "r", JOB).returncode == 0
    for task in range(1, 6):
        assert _run(root, "new", "r", f"{JOB}--T-{task}").returncode == 0
    sixth = _run(root, "new", "r", f"{JOB}--T-6")
    assert sixth.returncode == 1  # a commit-less task's exit is clean
    assert _fixes(sixth)[0].endswith(
        f"worktree.py clean {_word(root / 'worktrees/r' / f'{JOB}--T-1')}"
    )
    assert _run(root, "new", "r", "0.5.0-rc1/j2").returncode == 0  # the cap counts tasks only


def test_no_work_branch_refuses_with_a_fix_that_creates_it(root: Path) -> None:
    repo = root / "repos/r"
    _git(repo, "branch", "-D", "feature/0.5.0")
    result = _run(root, "new", "r", JOB)
    assert result.returncode == 1
    (fix,) = _fixes(result)
    assert (
        fix == f"fix: {git_line(repo, 'branch', 'feature/0.1.0', 'dev')}"
    )  # the flow's integration


@pytest.mark.parametrize(
    ("spec", "code", "out"),
    [("Approved", 0, "worktrees/a/0.5.0-rc1/j1"), ("Draft", 1, "")],
)
def test_an_associated_job_reads_the_main_repos_spec(
    root: Path, spec: str, code: int, out: str
) -> None:
    """AC11.0: `a` carries no specs; its job is gated by `r`'s SPEC on `r`'s work branch."""
    associate(root, spec)
    result = _run(root, "new", "a", JOB)
    assert (result.returncode, result.stdout.strip()) == (code, f"[ok] {root / out}" if out else "")
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
    assert row["fix"] == "" and row["exit"].endswith(f"merge {_word(tree)}")
    assert by_state["foreign"]["path"] == str(root / "native") and by_state["foreign"]["exit"] == ""
    assert by_state["unregistered"]["path"] == str(root / "worktrees/r/0.5.0-rc1/stray")
    assert not list((root / ".dadaia/states").glob("*worktree*"))


def test_the_one_venv_imports_the_checkout_it_runs_from() -> None:
    """AC1.11 (ADR 0113): the shared venv's editable install points at repos/, yet a child
    spawned from the suite's hermetic cwd imports THIS checkout (the conftest PYTHONPATH
    pin), and no checkout carries its own venv."""
    checkout = Path(__file__).resolve().parents[5]
    child = subprocess.run(
        [sys.executable, "-c", "import dadaia_workspace; print(dadaia_workspace.__file__)"],
        capture_output=True, text=True, check=True,
    )  # fmt: skip
    assert Path(child.stdout.strip()).resolve().is_relative_to(checkout)
    assert not (checkout / ".venv").exists()


def _bug_record(root: Path, status: str | None) -> None:
    """Work branch `feature/0.5.0` carries no rc and *status*'s one bug record (`None`: none)."""
    repo = root / "repos/r"
    _git(repo, "checkout", "-q", "feature/0.5.0")
    _git(repo, "rm", "-rq", "specs/releases")
    if status:
        commit(repo, "specs/bugs/BUGS.jsonl", f'{{"id": "a-block-bug", "status": "{status}"}}\n')
    _git(repo, "commit", "-qm", "no rc", "--allow-empty")


def test_a_hotfix_job_opens_with_no_rc_and_lands_on_the_work_branch(root: Path) -> None:
    """ADR 0206: a block-list bug is fixed as its own job — `new <repo> hotfix/<bug-id>` cuts it
    from the work branch with no rc SPEC, and its merge runs the same review and job gate."""
    _bug_record(root, "open")
    repo, name = root / "repos/r", "hotfix/a-block-bug"
    opened = _run(root, "new", "r", name)
    assert (opened.returncode, opened.stdout) == (0, f"[ok] {root / 'worktrees/r' / name}\n")
    assert _git(repo, "rev-parse", "wt/" + name) == _git(repo, "rev-parse", "feature/0.5.0")
    assert f"locked dadaia:{name}" in _git(repo, "worktree", "list", "--porcelain").splitlines()
    tree = root / "worktrees/r" / name
    approve(root, commit(tree, "src/fix.py"))
    landed = _run(root, "merge", str(tree))
    assert landed.returncode == 0, landed.stderr
    assert (repo / "src/fix.py").is_file() and not tree.exists()


@pytest.mark.parametrize("status", [None, "resolved"], ids=["no-record", "resolved"])
def test_a_hotfix_job_needs_its_open_bug_record_on_the_work_branch(
    root: Path, status: str | None
) -> None:
    _bug_record(root, status)
    refused = _run(root, "new", "r", "hotfix/a-block-bug")
    assert refused.returncode == 1 and "a-block-bug" in refused.stderr
    assert _fixes(refused) == [
        "fix: Operator action: register bug a-block-bug on feature/0.5.0 as open"
        " (dd-bug-registration), then open its hotfix job again"
    ]
    assert not (root / "worktrees/r/hotfix").exists()
