"""`worktree.py new` opens each tree of the hierarchy on its parent's branch — each name shape;
an old-grammar or `reconcile` name refused — and `list`; the
one venv. Size: MEDIUM (real git in a tmp workspace, never the live instance).
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from dadaia_workspace.core.cli_line import git_line, shell_line
from dadaia_workspace.core.skill_owner import load_owner
from tests.helpers import worktree_ws
from tests.helpers.oslib import command, link, read_text, run, write_text
from tests.helpers.skill_scripts import stage_skill_scripts
from tests.helpers.worktree_ws import (
    NEW_JOB,
    NEW_TASK,
    approve,
    associate,
    commit,
    make_workspace,
    run_fix,
)
from tests.helpers.worktree_ws import fixes as _fixes
from tests.helpers.worktree_ws import git as _git
from tests.helpers.worktree_ws import run as _run

_platform = load_owner("dd-bug-resolution", "_platform")

RC = "0.5.0/rc-1/wt-rc"
LANE = "0.5.0/wt-backlog-an-idea"


def phase_fix(root: Path) -> str:
    """The one fix of a main tree refused for the rc's phase: it names the main repo's rc tree."""
    return (
        "fix: Agent action: reach phase IMPLEMENTATION in _RELEASE.json on wt/0.5.0/rc-1/wt-rc"
        f" at {root / 'worktrees/r' / RC} (release.py phase), then open its job again"
    )


@pytest.fixture
def definition_root(tmp_path: Path) -> Path:
    return make_workspace(tmp_path)


def _set_release(root: Path, phase: str, *, plan: str = "Approved") -> None:
    """Put the fake work branch in one coherent release phase."""
    repo = root / "repos/r"
    release = repo / "specs/releases/0.5.0"
    plan_md = release / "rc-1/PLAN.md"
    write_text(plan_md, read_text(plan_md).replace("**Status:** Approved", f"**Status:** {plan}"))
    state_path = release / "_RELEASE.json"
    state = json.loads(read_text(state_path))
    state["phase"] = phase
    state["defined"] = (
        {"sha": "def1234", "ts": "2026-10-09T10:00:00Z"} if phase != "DEFINITION" else None
    )
    state["implemented"] = (
        {"sha": "abc1234", "ts": "2026-10-09T11:00:00Z"} if phase == "CLOSURE" else None
    )
    if phase == "CLOSURE":  # closure's check wants its memory pass recorded
        state["log"] = [{"ts": "2026-10-09T12:00:00Z", "agent": "a", "kind": "memory", "text": "t"}]
    write_text(state_path, json.dumps(state))
    _git(repo, "add", "specs/releases")
    _git(repo, "commit", "-qm", f"release {phase}")
    _git(repo, "branch", "-f", "feature/0.5.0", "HEAD")


@pytest.fixture
def root(definition_root: Path) -> Path:
    _set_release(definition_root, "IMPLEMENTATION")
    return definition_root


def test_a_release_job_needs_the_implementation_phase(definition_root: Path) -> None:
    """An Approved SPEC does not start implementation while PLAN is still Draft; the rc's own tree opens."""
    _set_release(definition_root, "DEFINITION", plan="Draft")
    repo = definition_root / "repos/r"
    assert _run(definition_root, "new", "r", RC).returncode == 0

    refused = _run(definition_root, "new", "r", NEW_JOB)

    assert refused.returncode != 0
    assert _fixes(refused) == [phase_fix(definition_root)]
    assert not (definition_root / "worktrees/r" / NEW_JOB).exists()
    assert _git(repo, "branch", "--list", f"wt/{NEW_JOB}").strip() == ""


def test_a_job_after_closure_is_refused_with_a_fix_that_can_work(definition_root: Path) -> None:
    """Phase never goes back: the one fix is not the `phase IMPLEMENTATION` step that refuses."""
    _set_release(definition_root, "CLOSURE")
    assert _run(definition_root, "new", "r", RC).returncode == 0

    refused = _run(definition_root, "new", "r", NEW_JOB)

    assert (refused.returncode, refused.stdout) == (1, "")
    assert [f.removeprefix("fix: ") for f in _fixes(refused)] == [
        f"{_script()} new r 0.5.0/rc-2/wt-rc"
    ]
    assert not (definition_root / "worktrees/r" / NEW_JOB).exists()
    rc_tree = definition_root / "worktrees/r" / RC
    run_fix(definition_root, refused)  # the printed act, run as printed, is not refused
    assert (definition_root / "worktrees/r/0.5.0/rc-2/wt-rc").is_dir()
    assert _git(rc_tree, "status", "--porcelain") == ""
    state = json.loads(read_text(rc_tree / "specs/releases/0.5.0/_RELEASE.json"))
    assert state["phase"] == "CLOSURE"


def test_a_main_tree_reads_the_phase_on_its_rcs_tree_not_the_work_branch(
    definition_root: Path,
) -> None:
    _set_release(definition_root, "DEFINITION", plan="Draft")
    assert _run(definition_root, "new", "r", RC).returncode == 0
    rc_tree = definition_root / "worktrees/r" / RC
    state = rc_tree / "specs/releases/0.5.0/_RELEASE.json"
    write_text(state, read_text(state).replace('"DEFINITION"', '"IMPLEMENTATION"'))
    _git(rc_tree, "commit", "-qam", "implementation")

    opened = _run(definition_root, "new", "r", NEW_JOB)

    assert (opened.returncode, opened.stdout) == (
        0,
        f"[ok] {definition_root / 'worktrees/r' / NEW_JOB}\n",
    )


def test_a_main_tree_refuses_a_release_state_that_breaks_the_schema_with_checks_finding(
    definition_root: Path,
) -> None:
    """The phase is IMPLEMENTATION, yet a log entry lacks `ts`: `release.py check` refuses the rc's tree."""
    _set_release(definition_root, "DEFINITION", plan="Draft")
    assert _run(definition_root, "new", "r", RC).returncode == 0
    rc_tree = definition_root / "worktrees/r" / RC
    state = rc_tree / "specs/releases/0.5.0/_RELEASE.json"
    doc = json.loads(read_text(state))
    doc.update(phase="IMPLEMENTATION", log=[{"agent": "a", "kind": "note", "text": "t"}])
    write_text(state, json.dumps(doc))
    _git(rc_tree, "commit", "-qam", "implementation")

    refused = _run(definition_root, "new", "r", NEW_JOB)

    assert (refused.returncode, refused.stdout) == (1, "")
    assert refused.stderr.splitlines() == [
        "[error] releases/0.5.0/_RELEASE.json:1 state.log[0] is missing required field 'ts'",
        f"fix: Agent action: {state} fails at the keys this finding names (specs/releases/AGENTS.md: "
        "release.py writes every _RELEASE.json field and ledger line) \u2014 revert the commit that "
        f"introduced it (`{_platform.git_inline(state.parent, 'log', '-p', '--', '_RELEASE.json')}` lists them), or delete the "
        "line if you wrote it and it is still uncommitted, then redo the change through `release.py`",
    ]
    assert not (definition_root / "worktrees/r" / NEW_JOB).exists()


def test_a_main_tree_needs_its_rcs_tree(root: Path) -> None:
    refused = _run(root, "new", "r", NEW_JOB)

    assert refused.returncode == 1
    assert [f.removeprefix("fix: ") for f in _fixes(refused)] == [f"{_script()} new r {RC}"]
    assert not (root / "worktrees/r").exists()


@pytest.mark.parametrize("name", ["0.5.0-rc1/reconcile", "0.5.0/rc-1/wt-reconcile"])
def test_a_reconcile_name_refuses_even_in_closure(definition_root: Path, name: str) -> None:
    """Reconciliation is the last commits of the rc's own tree: no tree of its own, in any phase."""
    _set_release(definition_root, "CLOSURE")

    refused = _run(definition_root, "new", "r", name)

    assert (refused.returncode, refused.stdout) == (1, "")
    assert not (definition_root / "worktrees/r").exists()


def test_new_makes_each_shape_on_its_branch_and_base(root: Path) -> None:
    repo = root / "repos/r"
    ahead = _git(repo, "commit-tree", "HEAD^{tree}", "-p", "HEAD", "-m", "ahead").strip()
    _git(repo, "branch", "-f", "feature/0.5.0", ahead)  # the start point is the work branch
    shas = {}
    for name in (RC, LANE, NEW_JOB, NEW_TASK):
        result = _run(root, "new", "r", name)
        assert (result.returncode, result.stdout) == (0, f"[ok] {root / 'worktrees/r' / name}\n")
        shas[name] = _git(repo, "rev-parse", f"wt/{name}").strip()
        commit(
            root / "worktrees/r" / name, "x.py", f"x = '{name}'\n"
        )  # the child must cut from this
    assert (shas[RC], shas[LANE]) == (ahead, ahead)
    assert shas[NEW_JOB] == _git(repo, "rev-parse", f"wt/{RC}").strip() != ahead
    assert shas[NEW_TASK] == _git(repo, "rev-parse", f"wt/{NEW_JOB}").strip() != shas[NEW_JOB]
    porcelain = _git(repo, "worktree", "list", "--porcelain").splitlines()
    assert sorted(x for x in porcelain if x.startswith(("locked", "branch"))) == sorted(
        [f"locked dadaia:{n}" for n in shas] + [f"branch refs/heads/wt/{n}" for n in shas]
        + ["branch refs/heads/main"]
    )  # fmt: skip


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
def test_a_plain_name_refuses_without_a_local_work_branch(
    root: Path, steps: tuple[tuple[str, ...], ...]
) -> None:
    repo = root / "repos/r"
    for step in steps:
        _git(repo, *step)

    _assert_plain_refused(root, _run(root, "new", "r", "maintenance"))


def _assert_plain_refused(root: Path, refused: subprocess.CompletedProcess[str]) -> None:
    """A one-segment name is no worktree name: refused, nothing created, no base recorded."""
    repo = root / "repos/r"
    assert refused.returncode == 1
    assert "not a worktree name" in refused.stderr
    assert not (root / "worktrees/r").exists()
    assert _git(repo, "branch", "--list", "wt/maintenance").strip() == ""
    assert "dadaia-base" not in _git(repo, "config", "--list")


def test_two_work_branches_still_refuse_a_plain_name(root: Path) -> None:
    repo = root / "repos/r"
    _git(repo, "checkout", "-q", "feature/0.5.0")
    _git(repo, "commit", "-q", "--allow-empty", "-m", "lower work")
    _git(repo, "branch", "feature/0.6.0", "main")

    _assert_plain_refused(root, _run(root, "new", "r", "maintenance"))


@pytest.mark.parametrize(
    "name",
    [
        "0.5.0a-impl",
        "0.5.0b-release",
        "0.4.9-rc1/j1",
        "0.5.0-rc1/J1",
        "0.5.0-rc1/j1",
        "0.5.0-rc1/j1--J1.T1",
        "0.5.0-rc1/define",
        "backlog/an-idea",
        "hotfix/a-block-bug",
        "0.5.0/rc-1/wt-define",
        "0.5.0/rc-1/job-1/wt-task-1",
        "0.4.9/rc-1/wt-rc",
        "0.4.9/wt-backlog-an-idea",
    ],
)
def test_an_old_grammar_or_foreign_name_refuses(root: Path, name: str) -> None:
    result = _run(root, "new", "r", name)
    assert result.returncode == 1 and not (root / "worktrees/r").exists()
    assert "0.5.0/rc-<N>/job-<n>/wt-main" in result.stderr  # the refusal teaches the hierarchy


def _script() -> str:
    """The script prefix of a fix line, as the product's `script()` prints it."""
    return shell_line(sys.executable, str(Path(__file__).resolve().parents[5] / "dadaia_workspace/public/skills"
               "/dd-gitflow-default/scripts/worktree.py"))  # fmt: skip


def _word(path: Path) -> str:
    """*path* as one word of a fix line, as `cli_line.shell_line` spells it."""
    return shell_line("x", str(path)).split(" ", 1)[1]


def test_a_task_needs_its_job_branch_and_the_sixth_task_opens(root: Path) -> None:
    """A task is cut from its main tree; the number of open tasks is not capped."""
    orphan = _run(root, "new", "r", NEW_TASK)
    [orphan_fix] = _fixes(orphan)
    assert orphan.returncode == 1 and orphan_fix.endswith(f"worktree.py new r {NEW_JOB}")
    assert _run(root, "new", "r", RC).returncode == 0
    assert _run(root, "new", "r", NEW_JOB).returncode == 0
    for task in range(1, 7):
        assert _run(root, "new", "r", f"0.5.0/rc-1/job-1/wt-task-{task:03d}").returncode == 0
    assert _run(root, "new", "r", "0.5.0/rc-1/job-2/wt-main").returncode == 0


def test_no_work_branch_refuses_with_a_fix_that_creates_it(root: Path) -> None:
    repo = root / "repos/r"
    _git(repo, "branch", "-D", "feature/0.5.0")
    result = _run(root, "new", "r", NEW_JOB)
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
    write_text(repo / "specs/releases/0.10.0/_RELEASE.json", "{}")
    result = _run(root, "new", "r", NEW_JOB)
    assert result.returncode == 1
    (fix,) = _fixes(result)
    assert fix == (
        f"fix: Agent action: keep one of 0.10.0, 0.5.0 live under {repo / 'specs/releases'};"
        " ship or move out the others"
    )


@pytest.mark.parametrize(
    ("spec", "code", "out"),
    [("Approved", 0, "worktrees/a/0.5.0/rc-1/job-1/wt-main"), ("Draft", 1, "")],
)
def test_an_associated_job_reads_the_main_repos_spec(
    root: Path, spec: str, code: int, out: str
) -> None:
    """`a` carries no specs; its main tree reads `r`'s release on `r`'s rc tree."""
    associate(root, spec)
    if spec == "Draft":
        _set_release(root, "DEFINITION")
    for repo in ("r", "a"):
        assert (
            _run(root, "new", repo, RC).returncode == 0
        )  # the rc's own tree needs no release phase
    result = _run(root, "new", "a", NEW_JOB)
    assert (result.returncode, result.stdout.strip()) == (code, f"[ok] {root / out}" if out else "")
    assert _fixes(result) == ([] if code == 0 else [phase_fix(root)])


def test_an_associated_jobs_phase_refusal_names_the_main_repos_rc_tree(root: Path) -> None:
    associate(root, "Draft")
    _set_release(root, "DEFINITION")
    for repo in ("r", "a"):
        assert _run(root, "new", repo, RC).returncode == 0

    refused = _run(root, "new", "a", NEW_JOB)

    assert refused.returncode == 1
    [fix] = _fixes(refused)
    assert str(root / "worktrees/r" / RC) in fix
    assert str(root / "worktrees/a") not in fix


def test_symlinked_worktrees_component_refuses(
    root: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    assert link(str(tmp_path_factory.mktemp("elsewhere")), root / "worktrees", is_dir=True)
    result = _run(root, "new", "r", NEW_JOB)
    assert result.returncode == 1 and len(_fixes(result)) == 1
    assert "symlink" in result.stderr


def test_list_reports_ours_with_ahead_and_dirty_and_a_native_one_as_foreign(root: Path) -> None:
    repo = root / "repos/r"
    assert _run(root, "new", "r", LANE).returncode == 0
    _git(repo, "worktree", "add", "-q", str(root / "native"), "-b", "native")
    (root / "worktrees/r/0.5.0/stray").mkdir()
    tree = root / "worktrees/r" / LANE
    write_text(tree / "x.py", "x = 1\n")
    _git(tree, "add", "x.py")
    _git(tree, "commit", "-qm", "x")
    write_text(tree / "y.py", "")
    result = _run(root, "list", "--json")
    assert result.returncode == 0, result.stderr
    by_state = {row["state"]: row for row in json.loads(result.stdout)}
    row = by_state["open"]  # dirty: never `ready`, no fix shown, its exit still the merge
    assert row["repo"] == "r" and row["name"] == LANE
    assert row["ahead"] == 1 and row["dirty"] is True and row["age_hours"] >= 0
    assert row["fix"] == "" and row["exit"].endswith(f"merge {_word(tree)}")
    assert by_state["foreign"]["path"] == str(root / "native") and by_state["foreign"]["exit"] == ""
    assert by_state["unregistered"]["path"] == str(root / "worktrees/r/0.5.0/stray")
    assert not list((root / ".dadaia/states").glob("*worktree*"))


def test_the_one_venv_imports_the_checkout_it_runs_from() -> None:
    """The shared venv's editable install points at repos/, yet a child
    spawned from the suite's hermetic cwd imports THIS checkout (the conftest PYTHONPATH
    pin), and no checkout carries its own venv."""
    checkout = Path(__file__).resolve().parents[5]
    child = run([sys.executable, "-c", "import dadaia_workspace; print(dadaia_workspace.__file__)"], check=True)  # fmt: skip
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
    """A block-list bug is fixed as its own job — `new <repo> <v>/wt-hotfix-<bug-id>` cuts it
    from the work branch with no rc SPEC, and its merge runs the same review and job gate."""
    _bug_record(root, "open")
    repo, name = root / "repos/r", "0.5.0/wt-hotfix-a-block-bug"
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
    refused = _run(root, "new", "r", "0.5.0/wt-hotfix-a-block-bug")
    assert refused.returncode == 1 and "a-block-bug" in refused.stderr
    act = "confirm bug a-block-bug" if status is None else "confirm the regression as a new bug"
    assert _fixes(refused) == [f"fix: Operator action: {act} (dd-bug-registration §2)"]
    assert not (root / "worktrees/r/0.5.0").exists()


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
        write_text(path, state)
        _git(repo, "add", "specs/releases")
    _git(repo, "commit", "-qm", "unreadable state")
    _git(repo, "branch", "-f", "feature/0.5.0", "HEAD")
    assert _run(root, "new", "r", RC).returncode == 0  # the rc's own tree reads no state

    refused = _run(root, "new", "r", NEW_JOB)

    assert refused.returncode == 1
    assert any(
        line.startswith("[error]") for line in (refused.stdout + refused.stderr).splitlines()
    )
    assert len(_fixes(refused)) == 1
    assert _git(repo, "branch", "--list", f"wt/{NEW_JOB}").strip() == ""
    assert not (root / "worktrees/r" / NEW_JOB).exists()


def test_a_main_tree_reads_an_rc_without_a_release_state_as_not_implementation(
    root: Path,
) -> None:
    """A new version's wt-rc exists before `release.py new`: it holds no state, so the job is
    refused for its phase and nothing is created."""
    assert _run(root, "new", "r", RC).returncode == 0
    shutil.rmtree(root / "worktrees/r" / RC / "specs/releases/0.5.0")

    refused = _run(root, "new", "r", NEW_JOB)

    assert (refused.returncode, refused.stdout) == (1, "")
    assert refused.stderr == (
        "[error] a job needs release 0.5.0 in phase IMPLEMENTATION on wt/0.5.0/rc-1/wt-rc\n"
        f"{phase_fix(root)}\n"
    )
    assert not (root / "worktrees/r" / NEW_JOB).exists()


def test_a_main_tree_whose_rc_tree_was_removed_by_hand_is_refused_with_a_fix_that_restores_it(
    root: Path,
) -> None:
    assert _run(root, "new", "r", RC).returncode == 0
    rc_tree = root / "worktrees/r" / RC
    shutil.rmtree(rc_tree)

    refused = _run(root, "new", "r", NEW_JOB)

    fix = git_line(root / "repos/r", "worktree", "add", "-f", "-f", "--lock", "--reason",
                   f"dadaia:{RC}", str(rc_tree), f"wt/{RC}")  # fmt: skip
    assert (refused.returncode, refused.stdout) == (1, "")
    assert refused.stderr == f"[error] {rc_tree} does not exist\nfix: {fix}\n"
    assert not (root / "worktrees/r" / NEW_JOB).exists()
    run_fix(root, refused)
    assert f"locked dadaia:{RC}" in _git(root / "repos/r", "worktree", "list", "--porcelain").splitlines()  # fmt: skip
    assert _run(root, "new", "r", NEW_JOB).returncode == 0


def test_a_main_tree_is_refused_when_release_check_exits_non_zero_with_no_finding(
    root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The exit status decides: a `release.py check` that crashes is a refusal, never a pass."""
    assert _run(root, "new", "r", RC).returncode == 0
    staged = stage_skill_scripts("dd-gitflow-default", tmp_path / "skills/dd-gitflow-default/scripts")  # fmt: skip
    write_text(
        tmp_path / "skills/dd-release-implementation/scripts/release.py",
        "import sys\nprint('Traceback (most recent call last):', file=sys.stderr)\nsys.exit(1)\n",
    )
    monkeypatch.setattr(worktree_ws, "SCRIPT", staged / "worktree.py")

    refused = _run(root, "new", "r", NEW_JOB)

    specs = root / "worktrees/r" / RC / "specs"
    assert (refused.returncode, refused.stdout) == (1, "")
    lines = refused.stderr.splitlines()
    assert lines[0] == "[error] release.py check exited 1", refused.stderr
    release = (tmp_path / "skills/dd-release-implementation/scripts/release.py").resolve()
    check = command(sys.executable, str(release), "check", "--specs", str(specs))
    assert lines[1:] == [f"fix: {check}"], refused.stderr
    assert not (root / "worktrees/r" / NEW_JOB).exists()


@pytest.mark.parametrize(
    ("name", "word", "task"),
    [
        ("0.5.0/wt-backlog-a-b", "a-b", None),
        ("0.5.0/rc-1/job-1/wt-task-001", None, "001"),
        ("0.5.0/rc-1/job-1/wt-task-1", None, "1"),
        ("0.5.0/rc-1/job-1/wt-task-b", None, "b"),
        ("0.5.0/rc-1/job-1/wt-task-0001", None, "0001"),
        ("0.5.0/rc-1/job-1/wt-main", None, None),
        ("0.5.0/wt-backlog-a--b", "a--b", None),
        ("0.5.0/wt-backlog-1a", "1a", None),
        ("0.5.0/wt-hotfix-a-b", "a-b", None),
        ("0.5.0/wt-hotfix-1a", "1a", None),
        ("a-b", "a-b", None),
        ("0.5.0/rc-1/wt-rc", None, None),
        ("a--b", "a--b", None),
        ("0.5.0/wt-hotfix-a--b", "a--b", None),
    ],
)
def test_a_name_is_accepted_as_the_backlog_slug_and_the_task_id_grammar_say(
    name: str, word: str | None, task: str | None
) -> None:
    """The backlog and hotfix words are the backlog `slug`; a task part is three digits; a name
    with no `wt-` leaf is no tree."""
    slug = load_owner("dd-bug-resolution", "_ledger").load_schema("backlog-v1")["$defs"]["slug"]
    accepted = (
        "/wt-" in name
        and (word is None or bool(re.fullmatch(slug["pattern"], word)))
        and (task is None or bool(re.fullmatch(r"\d{3}", task)))
    )
    names = load_owner("dd-gitflow-default", "_worktree_names")

    assert bool(names.NAME_RE.match(name)) is accepted


def test_new_writes_one_level_file_into_each_folder_it_creates(root: Path) -> None:
    for name in (RC, NEW_JOB):
        assert _run(root, "new", "r", name).returncode == 0
    base = root / "worktrees/r"
    levels = [base / "0.5.0", base / "0.5.0/rc-1", base / "0.5.0/rc-1/job-1"]
    assert [(p / "AGENTS.md").is_file() for p in levels] == [True, True, True]
    tree_file = read_text(base / NEW_JOB / "AGENTS.md")
    assert tree_file == "verify: python scripts/ci.py job\n" != read_text(levels[2] / "AGENTS.md")


def test_new_never_writes_over_an_existing_level_file_nor_rewrites_one(root: Path) -> None:
    version = root / "worktrees/r/0.5.0"
    version.mkdir(parents=True)
    write_text(version / "AGENTS.md", "mine\n")
    assert _run(root, "new", "r", RC).returncode == 0
    assert read_text(version / "AGENTS.md") == "mine\n"
    rc_file = version / "rc-1/AGENTS.md"
    assert rc_file.is_file()
    write_text(rc_file, "edited\n")
    assert _run(root, "new", "r", NEW_JOB).returncode == 0
    assert _run(root, "new", "r", "0.5.0/rc-1/job-2/wt-main").returncode == 0
    assert read_text(rc_file) == "edited\n"
    assert read_text(version / "AGENTS.md") == "mine\n"


def test_list_shows_no_stray_for_a_level_folder_holding_only_its_file(root: Path) -> None:
    repo = root / "repos/r"
    assert _run(root, "new", "r", RC).returncode == 0
    tree = root / "worktrees/r" / NEW_JOB
    assert _run(root, "new", "r", NEW_JOB).returncode == 0
    _git(repo, "worktree", "remove", "-f", "-f", str(tree))
    _git(repo, "branch", "-D", f"wt/{NEW_JOB}")
    assert (tree.parent / "AGENTS.md").is_file() and not tree.exists()
    rows = json.loads(_run(root, "list", "--json").stdout)
    assert [r["path"] for r in rows if r["state"] == "unregistered"] == []


def _leftover(root: Path) -> Path:
    """A non-empty folder at the rc's tree path that git does not list."""
    folder = root / "worktrees/r" / RC
    folder.mkdir(parents=True)
    write_text(folder / "stray.txt", "x\n")
    return folder


def test_new_onto_an_unlisted_folder_makes_no_branch_and_names_its_move(root: Path) -> None:
    folder = _leftover(root)

    refused = _run(root, "new", "r", RC)

    assert (refused.returncode, refused.stdout) == (1, "")
    assert _git(root / "repos/r", "branch", "--list", f"wt/{RC}").strip() == ""
    assert _fixes(refused) == [
        f"fix: Agent action: stop what holds files open in {folder}, then move the folder {folder} out of the lane path (it may hold work), then rerun `{_script()} new r {RC}`"
    ]
    folder.rename(root / "aside")
    assert _run(root, "new", "r", RC).returncode == 0
    assert (folder / "specs").is_dir()


@pytest.mark.parametrize("leftover", [False, True])
def test_a_branch_left_without_its_tree_is_cleared_by_the_printed_acts(
    root: Path, leftover: bool
) -> None:
    folder = root / "worktrees/r" / RC
    _git(root / "repos/r", "branch", f"wt/{RC}", "feature/0.5.0")
    _git(root / "repos/r", "checkout", "-q", "feature/0.5.0")
    refused = _run(root, "new", "r", RC)
    assert refused.returncode == 1 and "exists" in refused.stderr
    if leftover:
        _leftover(root)
        assert "move the folder" in _fixes(_run(root, "clean", str(folder)))[0]
        folder.rename(root / "aside")
    run_fix(root, refused)

    assert _run(root, "new", "r", RC).returncode == 0
    assert (folder / "specs").is_dir()


def test_merge_onto_a_leftover_folder_without_a_branch_ends_through_new(root: Path) -> None:
    folder = _leftover(root)

    merged = _run(root, "merge", str(folder))
    assert (merged.returncode, _fixes(merged)) == (1, [f"fix: {_script()} new r {RC}"])
    new_fix = _run(root, "new", "r", RC)  # the line merge prints, run as printed
    assert _fixes(new_fix) == [
        f"fix: Agent action: stop what holds files open in {folder}, then move the folder {folder} out of the lane path (it may hold work), then rerun `{_script()} new r {RC}`"
    ]
    folder.rename(root / "aside")

    assert _run(root, "new", "r", RC).returncode == 0
