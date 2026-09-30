"""Intent: CONTRACT — AC1.7 (T-050-95): `worktree.py new` and `list`. Size: MEDIUM (real
git in a tmp workspace, never the live instance).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

_SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "dadaia_workspace/public/skills/dd-gitflow-default/scripts/worktree.py"
)
_TRIO = ("SPEC", "PLAN", "TASKS")


def _git(repo: Path, *args: str) -> str:
    env = {"HOME": str(repo), "PATH": os.environ["PATH"], "GIT_CONFIG_NOSYSTEM": "1"}
    ident = ["-c", "user.name=t", "-c", "user.email=t@t", "-c", "init.defaultBranch=main"]
    out = subprocess.run(
        ["git", *ident, "-C", str(repo), *args], env=env, check=True, capture_output=True, text=True
    )
    return out.stdout


@pytest.fixture
def root(tmp_path: Path) -> Path:
    (tmp_path / ".dadaia/states").mkdir(parents=True)
    (tmp_path / ".dadaia/states/spec_contexts.json").write_text("{}")
    repo = tmp_path / "repos/r"
    repo.mkdir(parents=True)
    _git(repo, "init", "-q")
    rel = repo / "specs/releases/0.5.0"
    rel.mkdir(parents=True)
    for doc in _TRIO:
        (rel / f"{doc}.md").write_text(f"# {doc}\n\n**Status:** Approved\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "init")
    _git(repo, "branch", "feature/0.5.0")
    return tmp_path


def _run(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {
        "HOME": str(root),
        "PATH": os.environ["PATH"],
        "GIT_DIR": "/nonexistent",
        "GIT_CONFIG_NOSYSTEM": "1",
    }
    return subprocess.run(
        [sys.executable, str(_SCRIPT), *args], cwd=root, env=env, capture_output=True, text=True
    )


def _fixes(result: subprocess.CompletedProcess[str]) -> list[str]:
    return [line for line in result.stderr.splitlines() if line.startswith("fix: ")]


def test_new_branches_locks_and_marks_union_idempotently(root: Path) -> None:
    repo = root / "repos/r"
    assert _run(root, "new", "r", "--kind", "impl").returncode == 0
    second = _run(root, "new", "r", "--kind", "backlog")
    assert second.returncode == 0, second.stderr
    assert (root / "worktrees/r/0.5.0a-impl").is_dir()
    assert (root / "worktrees/r/0.5.0b-backlog").is_dir()
    assert _git(repo, "rev-parse", "wt/0.5.0a-impl") == _git(repo, "rev-parse", "feature/0.5.0")
    porcelain = _git(repo, "worktree", "list", "--porcelain")
    assert "locked dadaia:impl:0.5.0a" in porcelain
    assert "locked dadaia:backlog:0.5.0b" in porcelain
    attributes = (repo / ".git/info/attributes").read_text().splitlines()
    assert attributes.count("*.jsonl merge=union") == 1


def test_no_work_branch_refuses_with_a_fix_that_creates_it(root: Path) -> None:
    repo = root / "repos/r"
    _git(repo, "branch", "-D", "feature/0.5.0")
    result = _run(root, "new", "r", "--kind", "bug")
    assert result.returncode == 1
    (fix,) = _fixes(result)
    assert fix == f"fix: git -C {repo} branch feature/0.1.0 main"


def test_impl_needs_an_approved_trio_on_the_work_branch(root: Path) -> None:
    repo = root / "repos/r"
    _git(repo, "checkout", "-q", "feature/0.5.0")
    (repo / "specs/releases/0.5.0/PLAN.md").write_text("**Status:** Draft\n")
    _git(repo, "commit", "-qam", "draft")
    _git(repo, "checkout", "-q", "main")
    result = _run(root, "new", "r", "--kind", "impl")
    assert result.returncode == 1 and len(_fixes(result)) == 1
    assert "PLAN" in result.stderr
    assert _run(root, "new", "r", "--kind", "bug").returncode == 0


def test_caps_refuse_naming_an_existing_worktree(root: Path) -> None:
    for _ in range(5):
        assert _run(root, "new", "r", "--kind", "impl").returncode == 0
    sixth = _run(root, "new", "r", "--kind", "impl")
    assert sixth.returncode == 1
    (fix,) = _fixes(sixth)
    assert "worktree.py merge" in fix and "0.5.0a-impl" in fix
    assert _run(root, "new", "r", "--kind", "release").returncode == 0
    second_release = _run(root, "new", "r", "--kind", "release")
    assert second_release.returncode == 1
    assert "0.5.0f-release" in _fixes(second_release)[0]


def test_letters_past_z_refuse(root: Path) -> None:
    repo = root / "repos/r"
    for letter in "abcdefghijklmnopqrstuvwxyz":
        _git(repo, "branch", f"wt/0.5.0{letter}-bug", "feature/0.5.0")
    result = _run(root, "new", "r", "--kind", "bug")
    assert result.returncode == 1 and len(_fixes(result)) == 1


def test_symlinked_worktrees_component_refuses(
    root: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    (root / "worktrees").symlink_to(tmp_path_factory.mktemp("elsewhere"))
    result = _run(root, "new", "r", "--kind", "bug")
    assert result.returncode == 1 and len(_fixes(result)) == 1
    assert "symlink" in result.stderr


def test_failure_after_add_rolls_back(root: Path) -> None:
    repo = root / "repos/r"
    (repo / ".git/info/attributes").mkdir(parents=True)
    result = _run(root, "new", "r", "--kind", "bug")
    assert result.returncode == 1 and len(_fixes(result)) == 1
    assert not (root / "worktrees/r/0.5.0a-bug").exists()
    assert "wt/" not in _git(repo, "branch", "--list", "wt/*")
    assert "0.5.0a-bug" not in _git(repo, "worktree", "list")


def test_list_reports_only_ours_with_ahead_and_dirty(root: Path) -> None:
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
    (row,) = json.loads(result.stdout)
    assert row["repo"] == "r" and row["kind"] == "impl" and row["id"] == "0.5.0a"
    assert row["ahead"] == 1 and row["dirty"] is True and row["age_hours"] >= 0
    assert not list((root / ".dadaia/states").glob("*worktree*"))
