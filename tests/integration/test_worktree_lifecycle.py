"""AC1.8 (T-050-96, T-050-108), AC12.7 (ADR 0185): `worktree.py merge` fast-forwards the
approved HEAD as it is, removes and `branch -d`s the worktree, re-runnable; every refusal (dirty,
outside the kind's allowed set, a moved work branch, no APPROVED verdict for HEAD, ignored files,
wrong branch, a stray blocking the fast-forward) carries one `fix:` that clears it; `clean`
removes only an empty `dadaia:` worktree.
Size: MEDIUM (real git, tmp workspace).
"""

from __future__ import annotations

import importlib.util
import json
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tests.fixtures.harness_env import base_env
from tests.helpers.release_state import write_release_phase
from tests.helpers.skill_scripts import stage_skill_scripts
from tests.helpers.worktree_ws import SCRIPT, approve, commit, fixes, git, make_workspace, run
from tests.helpers.worktree_ws import run_fix as _fix

pytestmark = pytest.mark.integration

TREE = "worktrees/r/0.5.0a-impl"


@pytest.fixture
def root(tmp_path: Path) -> Path:
    (tmp_path := tmp_path / "my ws").mkdir()  # every fix runs as printed: quoted
    make_workspace(tmp_path)
    git(tmp_path / "repos/r", "checkout", "-q", "feature/0.5.0")
    assert run(tmp_path, "new", "r", "--kind", "impl").returncode == 0
    return tmp_path


def _argv(result: subprocess.CompletedProcess[str]) -> list[str]:
    """The one fix line, split as the shell will: the expected argv is the oracle."""
    (fix,) = fixes(result)
    return shlex.split(fix.removeprefix("fix: "))


def test_merge_fast_forwards_removes_and_reruns(root: Path) -> None:
    repo, tree = root / "repos/r", root / TREE
    sha = commit(tree, "src/a.py")
    rejected = approve(
        root, sha, verdict="REJECTED", at="T09:00:00Z"
    )  # the newer APPROVED overrules
    (other := root / ".dadaia/handoff/z").mkdir()  # another context and a non-UTC name:
    rejected.rename(other / "a.handoff.json")  # produced_at orders, never the path
    approve(root, sha)
    result = run(root, "merge", TREE)
    assert result.returncode == 0, result.stderr
    assert git(repo, "rev-parse", "feature/0.5.0").strip() == sha  # HEAD as approved
    assert not tree.exists() and not git(repo, "branch", "--list", "wt/*").strip()
    assert run(root, "merge", TREE).returncode == 0  # a finished merge re-runs clean
    assert run(root, "new", "r", "--kind", "impl").returncode == 0
    shutil.rmtree(tree)  # the dadaia:-locked tree deleted by hand: an orphan, its exit clears it
    (row,) = json.loads(run(root, "list", "--json").stdout)
    assert (row["state"], row["path"]) == ("orphan", str(tree))
    assert run(root, *shlex.split(row["exit"])[2:]).returncode == 0
    assert json.loads(run(root, "list", "--json").stdout) == []
    git(repo, "worktree", "add", "-q", "-b", "wt/0.5.0a-impl", str(tree))
    commit(tree, "src/b.py")
    git(repo, "worktree", "remove", str(tree))  # interrupted: tree gone, its commit unmerged
    assert _argv(run(root, "merge", TREE)) == [
        *("git", "-C", str(repo), "worktree", "add", str(tree), "wt/0.5.0a-impl")
    ]
    assert git(repo, "branch", "--list", "wt/0.5.0a-impl").strip()  # never -D


def test_dirty_and_outside_set_each_refuse_with_one_fix(root: Path) -> None:
    tree = root / TREE
    (tree / "wip").mkdir()  # an untracked directory, and a tracked edit staged:
    (tree / "wip/x.py").write_text("")
    (tree / "specs/releases/0.5.0/rc-1/SPEC.md").write_text("dirty")
    git(tree, "add", "specs/releases/0.5.0/rc-1/SPEC.md")
    dirty = run(root, "merge", TREE)
    assert "uncommitted" in dirty.stderr
    add, then, *remove = fixes(dirty)[0].split("`")[1::2]  # Operator action: commit or remove
    assert [shlex.split(add), shlex.split(then)] == [  # the commit takes the kind's own message
        ["git", "-C", str(tree), "add", "-A"],
        ["git", "-C", str(tree), "commit"],
    ]
    for step in remove:
        subprocess.run(step, shell=True, check=True, capture_output=True)  # noqa: S602
    assert git(tree, "status", "--porcelain") == ""  # removed, clean,
    assert not (tree / "wip").exists()
    assert git(tree, "stash", "list") == ""  # never in the stack every worktree shares
    commit(tree, "specs/backlog/BACKLOG copy.json", "{}")  # new: the undo removes it
    commit(tree, "specs/releases/0.5.0/rc-1/SPEC.md", "edited")  # on the work branch: restored
    for rel, owner in (("specs/backlog/BACKLOG copy.json", "backlog"), ("SPEC.md", "release")):
        outside = run(root, "merge", TREE)
        assert rel in outside.stderr and f"{owner} worktree" in outside.stderr
        restore, then = fixes(outside)[0].split("`")[1::2]  # Operator action: restore, commit
        subprocess.run(restore, shell=True, check=True)  # noqa: S602 — runs as printed
        assert shlex.split(then) == ["git", "-C", str(tree), "commit"]
        git(tree, "commit", "-qm", f"revert: {rel}")


def test_work_branch_refusals_fix_runs_verbatim(tmp_path: Path) -> None:
    (ws := tmp_path / "my ws").mkdir()
    make_workspace(ws)
    repo = ws / "repos/r"
    git(repo, "branch", "feature/0.4.9", "feature/0.5.0")  # two work branches: the older goes
    _fix(ws, two := run(ws, "new", "r", "--kind", "impl"))
    assert "2 work branches" in two.stderr
    assert not git(repo, "branch", "--list", "feature/0.4.9").strip()
    git(repo, "branch", "-m", "feature/0.5.0", "dev")  # none: the fix cuts one from dev
    _fix(ws, none := run(ws, "new", "r", "--kind", "impl"))
    assert "no work branch" in none.stderr
    assert git(repo, "branch", "--list", "feature/*").strip()


@pytest.mark.parametrize(
    ("named", "verdict", "valid", "older", "at"),
    [
        (False, "APPROVED", True, None, "T10:00:00Z"),
        (True, "REJECTED", True, None, "T10:00:00Z"),
        (True, "APPROVED", False, "APPROVED", "T10:00:00Z"),
        (True, "REJECTED", True, "APPROVED", "T10:00:00Z"),
        (True, "APPROVED", True, "APPROVED", "Tx"),
        (True, "REJECTED", True, "APPROVED", "T11:00:00"),  # 02:00Z if read in Asia/Tokyo
        (True, "REJECTED", True, "APPROVED", "T09:00:00Z"),  # tied with the older APPROVED
    ],
    ids=[
        *("outside-reflog", "rejected", "invalid", "rejected-after-approved"),
        *("no-produced-at", "naive-produced-at", "tied-produced-at"),
    ],
)
def test_merge_needs_a_valid_approval_of_the_exact_head(
    root: Path, named: bool, verdict: str, valid: bool, older: str | None, at: str
) -> None:
    commit(root / TREE, "src/a.py")
    head = commit(root / TREE, "src/b.py")
    copy = subprocess.run(  # head's tree, parent and message, outside wt/<name>'s reflog
        ["git", "-C", str(root / TREE), "commit-tree", f"{head}^{{tree}}", "-p", f"{head}~"],
        input="src/b.py\n",
        env=base_env() | {"GIT_COMMITTER_DATE": "2001-01-01T00:00:00"},
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    if older:  # the newest produced_at decides (ADR 0110), never a name sorting last
        approve(root, head, verdict=older, at="T09:00:00Z").rename(
            root / ".dadaia/handoff/c/v.handoff.json"
        )
    target = (
        approve(root, head, verdict=verdict, valid=valid, at=at)
        if named
        else (approve(root, copy), "--all")[1]
    )
    commit(root / "repos/r", "src/z.py")  # moved: only an identical series in the reflog counts
    git(root / TREE, "rebase", "-q", "feature/0.5.0")
    result = run(root, "merge", TREE)
    head = git(root / TREE, "rev-parse", "HEAD").strip()
    assert result.returncode == 1 and head in result.stderr
    cli = str(root / ".dadaia/.venv/bin/dadaia")
    assert _argv(result) == [cli, "reports", "validate", str(target)]
    assert git(root / "repos/r", "rev-parse", "feature/0.5.0").strip() != head


def test_failed_fast_forward_tells_a_stray_from_a_moved_work_branch(root: Path) -> None:
    repo, tree = root / "repos/r", root / TREE
    sha = commit(tree, "src/a.py")
    approve(root, sha)
    (repo / "src").mkdir()
    (repo / "src/a.py").write_text(
        "stray"
    )  # untracked in repos/r: the fast-forward would clobber it
    stray = run(root, "merge", TREE)
    assert "src/a.py" in stray.stderr and fixes(stray) == [
        f"fix: Operator action: commit or remove the paths above in {repo}"
    ]
    (repo / "src/a.py").unlink()
    cli = root / ".dadaia/.venv/bin/dadaia"  # a sibling lands while the verdict is read
    move = f"subprocess.run(['git', '-C', {str(repo)!r}, 'commit', '-qm', 'm', '--allow-empty'])"
    verdict = 'elif args[:2] == ["reports", "validate"]:\n'
    cli.write_text(cli.read_text().replace(verdict, f"{verdict}    import subprocess; {move}\n"))
    moved = run(root, "merge", TREE)
    assert _argv(moved) == ["git", "-C", str(tree), "rebase", "feature/0.5.0"] and tree.exists()


def test_merge_lists_ignored_files_and_keeps_them_by_its_fix(root: Path) -> None:
    repo, tree = root / "repos/r", root / TREE
    approve(root, commit(tree, "src/a.py"))
    (tree / "my notes.scratch").write_text("keep me")
    (tree / "__pycache__").mkdir()
    (tree / "__pycache__/a.pyc").write_bytes(b"")
    git(repo, "checkout", "-q", "main")
    refused = run(root, "merge", TREE)
    assert "my notes.scratch" in refused.stderr and "__pycache__" not in refused.stderr
    wrong_branch = run(root, "merge", TREE, "--keep", "my notes.scratch")
    assert _argv(wrong_branch) == ["git", "-C", str(repo), "switch", "feature/0.5.0"]
    _fix(root, wrong_branch)
    _fix(root, refused)
    assert (repo / "my notes.scratch").read_text() == "keep me" and not tree.exists()


def test_clean_removes_only_an_empty_worktree_of_ours(root: Path) -> None:
    repo, tree = root / "repos/r", root / TREE
    commit(tree, "src/a.py")
    assert _argv(run(root, "clean", TREE)) == [sys.executable, str(SCRIPT), "merge", str(tree)]
    git(tree, "reset", "-q", "--hard", "feature/0.5.0")
    assert run(root, "clean", TREE).returncode == 0 and not tree.exists()
    # ours is the canonical wt/ branch, locked or not (T-050-99 N2); a tree on another is not
    git(repo, "worktree", "add", "-q", "-b", "side", str(root / "worktrees/r/0.5.0b-bug"))
    foreign = run(root, "clean", "worktrees/r/0.5.0b-bug")
    assert foreign.returncode == 1 and (root / "worktrees/r/0.5.0b-bug").exists()


def test_each_kind_allows_its_own_set_only() -> None:
    """ADRs 0106, 0124, 0148 (7), 0153: the allowed sets `merge` enforces, one row per kind boundary."""
    spec = importlib.util.spec_from_file_location("kinds", SCRIPT.parent / "_worktree_kinds.py")
    assert spec and spec.loader
    kinds = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(kinds)
    rows = {
        ("impl", "src/a.py"): True,
        ("impl", "specs/releases/0.5.0/rc-5/TASKS.md"): True,
        ("impl", "specs/releases/0.5.0/TASKS.md"): False,
        ("impl", "specs/backlog/BACKLOG.json"): False,
        ("bug", "specs/bugs/BUGS.jsonl"): True,
        ("bug", "specs/bugs/_archive/bugs_histo.jsonl"): True,
        ("bug", "specs/releases/0.5.0/rc-5/SPEC.md"): False,
        ("backlog", "specs/backlog/_archive/backlog_histo.jsonl"): True,
        ("backlog", "src/a.py"): False,
        ("release", "specs/memory/ARCHITECTURE.md"): True,
        ("release", "specs/constitution.md"): True,
        ("release", "specs/bugs/AGENTS.md"): True,
        ("release", "specs/audits/x/FINDINGS.jsonl"): False,
    }
    assert {row: kinds.allows(*row) for row in rows} == rows


def test_release_closure_waits_for_every_other_wt(tmp_path: Path) -> None:
    """AC1.10 (F4): closure runs in its release worktree, whose own wt/* is spared; any
    other wt/* refuses it, naming repos/<r> and the owner's exit — `clean` for an empty
    tree (N1), which clears it."""
    (root := tmp_path / "ws").mkdir()
    make_workspace(root)
    git(root / "repos/r", "checkout", "-q", "feature/0.5.0")
    assert run(root, "new", "r", "--kind", "release").returncode == 0
    specs = root / "worktrees/r/0.5.0a-release/specs"
    write_release_phase(specs, "0.5.0", "IMPLEMENTATION")
    (specs / "releases/_archive").mkdir()
    (specs / "releases/_archive/releases_histo.jsonl").write_text("")
    assert run(root, "new", "r", "--kind", "impl").returncode == 0  # empty
    for skill in (
        "dd-spec-navigator",
        "dd-gitflow-default",
        "dd-release-implementation",
        "dd-bug-resolution",
    ):
        stage_skill_scripts(skill, tmp_path / "skills" / skill / "scripts")
    script = tmp_path / "skills/dd-release-implementation/scripts/release.py"
    closure = [sys.executable, str(script), "phase", "CLOSURE", "--sha", "beef123"]
    closure += ["--specs", str(specs)]

    refused = subprocess.run(closure, cwd=root, capture_output=True, text=True)
    fix = refused.stderr.rsplit("fix: ", 1)[1].strip()
    assert "repos/r " in refused.stderr and fix.endswith(f"clean {root}/worktrees/r/0.5.0b-impl")
    subprocess.run(fix, shell=True, cwd=root, check=True)  # noqa: S602
    assert subprocess.run(closure, cwd=root, capture_output=True).returncode == 0


def test_a_verdict_carries_over_only_an_identical_patch_and_message_series(root: Path) -> None:
    """AC3.19 (ADR 0168): once the work branch moved, a reword, a dropped or added empty
    commit, a reorder, code amended under the same message (a colored config included), a gitlink
    amended under the same message (diff.ignoreSubmodules=all), or a hand-resolved conflict each change the approved series and refuse for review."""
    repo, tree = root / "repos/r", root / TREE
    commit(tree, "src/a.py")
    git(tree, "commit", "-q", "--allow-empty", "-m", "empty")
    approve(root, approved := git(tree, "rev-parse", "HEAD").strip())
    commit(repo, "src/z.py")
    git(repo, "config", "color.ui", "always")
    refusal = [str(root / ".dadaia/.venv/bin/dadaia"), "reports", "validate", "--all"]
    work = git(repo, "rev-parse", "feature/0.5.0")
    for change in (
        [("rm", "-q", "src/a.py"), ("commit", "-q", "--amend", "-C", "HEAD")],  # same message
        [("commit", "-q", "--amend", "--allow-empty", "-m", "reworded")],  # same patch-ids
        [("reset", "-q", "--hard", "HEAD~")],  # the empty commit dropped
        [("commit", "-q", "--allow-empty", "-m", "empty 2")],  # one more empty commit
        [  # the same two commits, reordered
            ("reset", "-q", "--hard", "HEAD~2"),
            ("cherry-pick", "--allow-empty", approved, f"{approved}~"),
        ],
    ):
        git(tree, "reset", "-q", "--hard", approved)
        for step in change:
            git(tree, *step)
        git(tree, "rebase", "-q", "feature/0.5.0")
        assert _argv(run(root, "merge", TREE)) == refusal, change
        assert git(repo, "rev-parse", "feature/0.5.0") == work
    git(repo, "config", "diff.ignoreSubmodules", "all")  # a gitlink change shows no diff
    git(tree, "reset", "-q", "--hard", approved)
    for sha in (approved, f"{approved}~"):  # the same message, another gitlink: fail closed
        git(
            tree,
            "update-index",
            "--add",
            "--cacheinfo",
            f"160000,{git(tree, 'rev-parse', sha).strip()},sub",
        )
        git(
            tree, "commit", "-q", *(("--amend", "-C", "HEAD") if sha != approved else ("-m", "sub"))
        )
        if sha == approved:
            approve(root, git(tree, "rev-parse", "HEAD").strip())
    git(tree, "rebase", "-q", "feature/0.5.0")
    assert _argv(run(root, "merge", TREE)) == refusal
    assert git(repo, "rev-parse", "feature/0.5.0") == work
    git(tree, "reset", "-q", "--hard", approved)
    work = commit(repo, "src/a.py", "theirs\n") + "\n"
    assert run(root, "merge", TREE).returncode == 1  # moved; the agent's rebase conflicts
    subprocess.run(["git", "-C", str(tree), "rebase", "feature/0.5.0"], capture_output=True)
    (tree / "src/a.py").write_text("resolved\n")
    git(tree, "add", "src/a.py")
    git(tree, "-c", "core.editor=true", "rebase", "--continue")
    assert _argv(run(root, "merge", TREE)) == refusal
    assert git(repo, "rev-parse", "feature/0.5.0") == work


@pytest.mark.parametrize("change", ["same-patch", "new-patch"])
def test_a_moved_work_branch_refuses_and_its_fix_rebase_keeps_only_an_identical_patch(
    root: Path, change: str
) -> None:
    """AC12.7 (ADR 0185): a moved work branch refuses with the rebase fix line, both branches
    unchanged; after it, a patch-identical rebase lands under the old verdict (ADR 0168),
    a changed patch refuses for review."""
    repo, tree = root / "repos/r", root / TREE
    approve(root, mine := commit(tree, "src/a.py"))
    work = commit(repo, "src/z.py")
    moved = run(root, "merge", TREE)
    assert _argv(moved) == ["git", "-C", str(tree), "rebase", "feature/0.5.0"]
    assert [
        git(repo, "rev-parse", "feature/0.5.0").strip(),
        git(tree, "rev-parse", "HEAD").strip(),
    ] == [work, mine]
    _fix(root, moved)
    if change == "new-patch":
        (tree / "src/a.py").write_text("x = 2\n")
        git(tree, "commit", "-q", "--amend", "-C", "HEAD", "-a")
    result = run(root, "merge", TREE)
    landed = git(repo, "rev-parse", "feature/0.5.0").strip()
    if change == "same-patch":
        assert result.returncode == 0, result.stderr
        assert git(repo, "rev-parse", "feature/0.5.0~").strip() == work != landed
    else:
        assert _argv(result)[1:] == ["reports", "validate", "--all"] and landed == work


@pytest.mark.parametrize(
    ("base", "mine", "lands"),
    [
        (None, "verify: echo 'fix: mine' >&2; false\n", False),
        (None, "verify: cat\n", True),
        (None, "verify: git rev-parse HEAD\n", True),
        (None, "verify: git -C ../../../repos/r switch -q main\n", False),  # checked after it
        ("# a prose verify: mention declares nothing\n", None, False),
        ("", None, False),
        ("# a prose verify: mention declares nothing\n", "verify: true\n", True),
    ],
    ids=[
        *("exits-1", "exits-0-stdin-closed", "prints-head", "switches-the-repo", "undeclared"),
        *("no-agents-md", "declared-by-the-worktree"),
    ],
)
def test_merge_lands_only_what_the_declared_verify_command_passes(
    root: Path, base: str | None, mine: str | None, lands: bool
) -> None:
    """AC12.5 (ADR 0185): `merge` runs HEAD's `AGENTS.md` `verify:` line in the tree before
    the fast-forward; a failure or no declaration lands nothing."""
    repo, tree = root / "repos/r", root / TREE
    if base is not None:  # the work branch declares nothing, or has no AGENTS.md
        if base:
            commit(repo, "AGENTS.md", base)
        else:
            git(repo, "rm", "-q", "AGENTS.md")
            git(repo, "commit", "-qm", "no AGENTS.md")
        git(tree, "reset", "-q", "--hard", "feature/0.5.0")
    head = commit(tree, "AGENTS.md", mine) if mine else commit(tree, "src/a.py")
    approve(root, head)
    work = git(repo, "rev-parse", "feature/0.5.0").strip()
    result = run(root, "merge", TREE, input="stdin leak\n")  # a closed stdin: `cat` reads none
    assert "stdin leak" not in result.stdout
    assert git(repo, "rev-parse", "feature/0.5.0").strip() == (head if lands else work)
    if not lands:
        assert git(tree, "rev-parse", "HEAD").strip() == head
    assert (result.returncode, tree.exists()) == ((0, False) if lands else (1, True))
    if mine == "verify: git rev-parse HEAD\n":
        assert head in result.stdout.splitlines()
    if mine and "false" in mine:  # the verify's own `fix:` line never reaches stderr
        assert fixes(result) == [
            f"fix: Operator action: make `echo 'fix: mine' >&2; false` exit 0 in {tree}"
            " and commit the fix in this worktree"
        ]
    if base is not None and not mine:
        assert fixes(result) == [
            "fix: Operator action: declare this repo's check command as a verify: line in"
            f" {tree}/AGENTS.md and commit it in this worktree"
        ]
