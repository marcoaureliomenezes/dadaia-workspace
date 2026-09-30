"""Intent: CONTRACT — AC1.8 / ADRs 0106, 0124 (T-050-96): `worktree.py merge` refuses a file
outside its kind's allowed set, and the refusal's fix reverts it so the merge goes on.
Size: MEDIUM (real git, tmp workspace).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tests.helpers.worktree_ws import approve, commit, fixes, git, make_workspace, run

pytestmark = pytest.mark.integration


@pytest.mark.parametrize(
    ("kind", "inside", "outside"),
    [
        ("impl", "src/a.py", "specs/backlog/BACKLOG.json"),
        ("bug", "specs/bugs/BUGS.jsonl", "specs/releases/0.5.0/SPEC.md"),
        ("backlog", "specs/backlog/_archive/backlog_histo.jsonl", "src/a.py"),
        ("release", "specs/memory/ARCHITECTURE.md", "specs/constitution.md"),
    ],
)
def test_a_file_outside_the_kind_is_refused_and_its_fix_reverts_it(
    tmp_path: Path, kind: str, inside: str, outside: str
) -> None:
    root = make_workspace(tmp_path)
    base = git(root / "repos/r", "rev-parse", "feature/0.5.0").strip()
    git(root / "repos/r", "checkout", "-q", "feature/0.5.0")
    assert run(root, "new", "r", "--kind", kind).returncode == 0
    tree = root / f"worktrees/r/0.5.0a-{kind}"
    commit(tree, inside)
    commit(tree, outside)
    refused = run(root, "merge", str(tree))
    assert refused.returncode == 1 and outside in refused.stderr
    (fix,) = fixes(refused)
    env = {"HOME": str(root), "PATH": "/usr/bin:/bin", "GIT_CONFIG_NOSYSTEM": "1"}
    subprocess.run(fix.removeprefix("fix: "), shell=True, env=env, check=True)
    approve(root, git(tree, "rev-parse", "HEAD").strip())
    merged = run(root, "merge", str(tree))
    assert merged.returncode == 0, merged.stderr
    assert git(root / "repos/r", "diff", "--name-only", base, "feature/0.5.0").split() == [inside]
