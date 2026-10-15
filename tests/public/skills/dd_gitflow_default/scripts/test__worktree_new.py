"""`worktree.py new` opens one tree per job or task — each name shape;
an old-grammar name refused — and `list`; the
one venv. Size: MEDIUM (real git in a tmp workspace, never the live instance).
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from dadaia_workspace.core.cli_line import git_line, shell_line
from dadaia_workspace.core.skill_owner import load_owner
from tests.helpers.worktree_ws import JOB, TASK, approve, associate, commit, make_workspace, run_fix
from tests.helpers.worktree_ws import fixes as _fixes
from tests.helpers.worktree_ws import git as _git
from tests.helpers.worktree_ws import run as _run


@pytest.fixture
def definition_root(tmp_path: Path) -> Path:
    return make_workspace(tmp_path)


def _set_release(root: Path, phase: str, *, plan: str = "Approved") -> None:
    """Put the fake work branch in one coherent release phase."""
    repo = root / "repos/r"
    release = repo / "specs/releases/0.5.0"
    plan_md = release / "rc-1/PLAN.md"
    plan_md.write_text(plan_md.read_text().replace("**Status:** Approved", f"**Status:** {plan}"))
    state_path = release / "_RELEASE.json"
    state = json.loads(state_path.read_text())
    state["phase"] = phase
    state["defined"] = (
        {"sha": "def1234", "ts": "2026-10-09T10:00:00Z"} if phase != "DEFINITION" else None
    )
    state["implemented"] = (
        {"sha": "abc1234", "ts": "2026-10-09T11:00:00Z"} if phase == "CLOSURE" else None
    )
    state_path.write_text(json.dumps(state))
    _git(repo, "add", "specs/releases")
    _git(repo, "commit", "-qm", f"release {phase}")
    _git(repo, "branch", "-f", "feature/0.5.0", "HEAD")


@pytest.fixture
def root(definition_root: Path) -> Path:
    _set_release(definition_root, "IMPLEMENTATION")
    return definition_root


def test_a_release_job_needs_the_implementation_phase(definition_root: Path) -> None:
    """An Approved SPEC does not start implementation while PLAN is still Draft."""
    _set_release(definition_root, "DEFINITION", plan="Draft")
    repo = definition_root / "repos/r"

    refused = _run(definition_root, "new", "r", JOB)

    assert refused.returncode != 0
    assert _fixes(refused) == [f"fix: {_script()} new r 0.5.0-rc1/define"]
    assert not (definition_root / "worktrees/r" / JOB).exists()
    assert _git(repo, "branch", "--list", f"wt/{JOB}").strip() == ""


def test_reconcile_also_opens_in_closure(definition_root: Path) -> None:
    """Reconciliation spans the IMPLEMENTATION-to-CLOSURE boundary."""
    _set_release(definition_root, "CLOSURE")

    opened = _run(definition_root, "new", "r", "0.5.0-rc1/reconcile")

    assert (opened.returncode, opened.stdout) == (
        0,
        f"[ok] {definition_root / 'worktrees/r/0.5.0-rc1/reconcile'}\n",
    )


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


_NO_RELEASE = (("rm", "-rq", "specs/releases"), ("commit", "-qm", "no release"))
_RENAMED = (
    ("checkout", "-q", "feature/0.5.0"),
    ("commit", "-q", "--allow-empty", "-m", "window"),
    ("branch", "-m", "feature/0.5.0", "feature/0.6.0"),
)
_PROMOTED = (*_NO_RELEASE, ("branch", "-m", "feature/0.5.0", "feature/0.6.0"))


@pytest.mark.parametrize(
    "steps",
    [
        (),
        (*_NO_RELEASE, ("branch", "-D", "feature/0.5.0")),
        (*_RENAMED,),
        (("branch", "trunk"), ("checkout", "-q", "trunk"), *_PROMOTED),
        (("checkout", "-q", "--detach"), *_PROMOTED),
        (("branch", "dev"), ("checkout", "-q", "dev"), *_PROMOTED),
    ],
    ids=[
        "live-release",
        "no-release-no-work-branch",
        "window-commit-renamed",
        "trunk",
        "detached",
        "dev",
    ],
)
def test_a_plain_name_refuses_whatever_branch_the_repo_is_on(
    root: Path, steps: tuple[tuple[str, ...], ...]
) -> None:
    repo = root / "repos/r"
    for step in steps:
        _git(repo, *step)

    _assert_plain_refused(root, _run(root, "new", "r", "maintenance"))


@pytest.mark.parametrize(
    "steps",
    [
        (
            ("branch", "dev"),
            ("checkout", "-q", "dev"),
            ("update-ref", "refs/remotes/origin/feature/0.5.0", "main"),
            ("branch", "-D", "feature/0.5.0"),
        ),
        (
            *_NO_RELEASE,
            ("branch", "-D", "feature/0.5.0"),
            ("branch", "dev"),
            ("checkout", "-q", "--detach"),
        ),
    ],
    ids=["remote-only", "detached-no-work-branch"],
)
def test_a_plain_name_refuses_without_a_local_work_branch_with_the_list_fix(
    root: Path, steps: tuple[tuple[str, ...], ...]
) -> None:
    repo = root / "repos/r"
    for step in steps:
        _git(repo, *step)

    refused = _run(root, "new", "r", "maintenance")

    _assert_plain_refused(root, refused)
    run_fix(root, refused)
    _assert_plain_refused(root, _run(root, "new", "r", "maintenance"))


def _assert_plain_refused(root: Path, refused: subprocess.CompletedProcess[str]) -> None:
    """A one-segment name is no worktree name: refused with the `list` fix, nothing created, no base recorded."""
    repo = root / "repos/r"
    assert refused.returncode == 1
    assert "not a worktree name" in refused.stderr
    assert [f.removeprefix("fix: ") for f in _fixes(refused)] == [f"{_script()} list"]
    assert not (root / "worktrees/r").exists()
    assert _git(repo, "branch", "--list", "wt/maintenance").strip() == ""
    assert _git(repo, "config", "--get-regexp", r"dadaia-base").strip() == ""


def test_two_work_branches_still_refuse_a_plain_name_with_the_list_fix(root: Path) -> None:
    repo = root / "repos/r"
    _git(repo, "checkout", "-q", "feature/0.5.0")
    _git(repo, "commit", "-q", "--allow-empty", "-m", "lower work")
    _git(repo, "branch", "feature/0.6.0", "main")

    _assert_plain_refused(root, _run(root, "new", "r", "maintenance"))


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


def test_a_task_needs_its_job_branch_and_the_sixth_task_opens(root: Path) -> None:
    """A task is cut from its job branch; the number of open tasks is not capped."""
    orphan = _run(root, "new", "r", TASK)
    assert orphan.returncode == 1 and _fixes(orphan)[0].endswith(f"worktree.py new r {JOB}")
    assert _run(root, "new", "r", JOB).returncode == 0
    for task in range(1, 7):
        assert _run(root, "new", "r", f"{JOB}--J1.T{task}").returncode == 0
    assert _run(root, "new", "r", "0.5.0-rc1/j2").returncode == 0


def test_no_work_branch_refuses_with_a_fix_that_creates_it(root: Path) -> None:
    repo = root / "repos/r"
    _git(repo, "branch", "-D", "feature/0.5.0")
    result = _run(root, "new", "r", JOB)
    assert result.returncode == 1
    (fix,) = _fixes(result)
    assert (
        fix == f"fix: {git_line(repo, 'branch', 'feature/0.5.0', 'dev')}"
    )  # the live release's branch, cut from the flow's integration


def test_no_work_branch_with_several_live_releases_refuses_as_the_plain_base_does(
    root: Path,
) -> None:
    repo = root / "repos/r"
    _git(repo, "branch", "-D", "feature/0.5.0")
    (repo / "specs/releases/0.10.0").mkdir()
    (repo / "specs/releases/0.10.0/_RELEASE.json").write_text("{}")
    result = _run(root, "new", "r", JOB)
    assert result.returncode == 1
    (fix,) = _fixes(result)
    assert fix == (
        f"fix: Agent action: keep one of 0.10.0, 0.5.0 live under {repo / 'specs/releases'};"
        " ship or move out the others"
    )


@pytest.mark.parametrize(
    ("spec", "code", "out"),
    [("Approved", 0, "worktrees/a/0.5.0-rc1/j1"), ("Draft", 1, "")],
)
def test_an_associated_job_reads_the_main_repos_spec(
    root: Path, spec: str, code: int, out: str
) -> None:
    """`a` carries no specs; its job reads `r`'s release on `r`'s work branch."""
    associate(root, spec)
    if spec == "Draft":
        _set_release(root, "DEFINITION")
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
    """The shared venv's editable install points at repos/, yet a child
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
    """A block-list bug is fixed as its own job — `new <repo> hotfix/<bug-id>` cuts it
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
        "fix: Operator action: confirm bug a-block-bug so it is registered on feature/0.5.0 as open"
        " (dd-bug-registration), then open its hotfix job again"
    ]
    assert not (root / "worktrees/r/hotfix").exists()


@pytest.mark.parametrize("state", [None, "[]", "{not json"], ids=["missing", "array", "malformed"])
def test_an_unreadable_release_state_refuses_a_job_and_creates_nothing(
    root: Path, state: str | None
) -> None:
    """A missing, non-object or malformed `_RELEASE.json` on the work branch refuses
    job admission: `[error]`, one `fix:` line, no branch, no worktree."""
    repo = root / "repos/r"
    path = repo / "specs/releases/0.5.0/_RELEASE.json"
    if state is None:
        _git(repo, "rm", "-q", "specs/releases/0.5.0/_RELEASE.json")
    else:
        path.write_text(state)
        _git(repo, "add", "specs/releases")
    _git(repo, "commit", "-qm", "unreadable state")
    _git(repo, "branch", "-f", "feature/0.5.0", "HEAD")

    refused = _run(root, "new", "r", JOB)

    assert refused.returncode == 1
    assert any(
        line.startswith("[error]") for line in (refused.stdout + refused.stderr).splitlines()
    )
    assert len(_fixes(refused)) == 1
    assert _git(repo, "branch", "--list", f"wt/{JOB}").strip() == ""
    assert not (root / "worktrees/r" / JOB).exists()


@pytest.mark.parametrize(
    ("name", "word", "task"),
    [
        ("0.5.0-rc1/a-b", "a-b", None),
        ("0.5.0-rc1/a--J1.T1", "a", "J1.T1"),
        ("0.5.0-rc1/a--J1.S2.T3", "a", "J1.S2.T3"),
        ("0.5.0-rc1/a--b", "a", "b"),
        ("0.5.0-rc1/a--T-1-1", "a", "T-1-1"),
        ("0.5.0-rc1/1a", "1a", None),
        ("backlog/a-b", "a-b", None),
        ("backlog/1a", "1a", None),
        ("hotfix/a-b", "a-b", None),
        ("hotfix/1a", "1a", None),
        ("a-b", "a-b", None),
        ("1a", "1a", None),
        ("a--b", "a--b", None),
        ("backlog/a--b", "a--b", None),
    ],
)
def test_a_name_is_accepted_as_the_backlog_slug_and_the_task_id_grammar_say(
    name: str, word: str, task: str | None
) -> None:
    """The job, backlog, hotfix and plain words are the backlog `slug`; a task part is a
    release task id, so `--` only ever separates a job from `J<n>.T<k>`."""
    slug = load_owner("dd-bug-resolution", "_ledger").load_schema("backlog-v1")["$defs"]["slug"]
    task_id = load_owner("dd-bug-resolution", "_grammar").TASK_ID_RE
    accepted = bool(re.fullmatch(slug["pattern"], word)) and (
        task is None or bool(task_id.fullmatch(task))
    )
    names = load_owner("dd-gitflow-default", "_worktree_names")

    assert bool(names.NAME_RE.match(name)) is accepted
