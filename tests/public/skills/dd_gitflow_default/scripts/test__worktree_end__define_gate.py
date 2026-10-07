"""trio-status-canon-judged-outside-the-define-merge-gate: a `define` merge runs the workspace
doctor on its own `specs/` — the check the work branch's CI runs — fenced to the tree, so a tree
the doctor refuses never lands. Size: MEDIUM (real git, tmp workspace, a stub CLI).
"""

from __future__ import annotations

import os
from pathlib import Path

from tests.helpers.worktree_ws import approve, commit, fixes, git, make_workspace, patch_cli, run


def test_a_define_merge_runs_the_doctor_fenced_to_its_tree(tmp_path: Path) -> None:
    (root := tmp_path / "ws").mkdir()
    make_workspace(root)
    git(root / "repos/r", "checkout", "-q", "feature/0.5.0")
    assert run(root, "new", "r", "0.5.0-rc1/define").returncode == 0
    tree = root / "worktrees/r/0.5.0-rc1/define"
    approve(root, commit(tree, "specs/RED-doctor", ""))
    refused = run(root, "merge", str(tree))
    assert refused.returncode == 1 and "dadaia doctor check failed" in refused.stderr
    out = refused.stdout.splitlines()
    assert out[0] == f"doctor --specs-dir {tree}/specs" and out[2] == f"cwd {tree}"
    assert str(root) in out[1].removeprefix("fenced ").split(os.pathsep)  # no workspace acted on
    git(tree, "rm", "-q", "specs/RED-doctor")
    git(tree, "commit", "-qm", "doctor-clean")
    approve(root, git(tree, "rev-parse", "HEAD").strip(), at="T11:00:00Z")
    landed = run(root, "merge", str(tree))
    assert landed.returncode == 0, landed.stderr


DOCTOR_FIX = "fix: dadaia doctor --fix --specs-dir specs"
RED_DOCTOR = 'sys.exit(os.path.exists(os.path.join(specs, "RED-doctor")))'


def test_a_red_doctor_refuses_once_with_its_own_fix_line(tmp_path: Path) -> None:
    (root := tmp_path / "ws").mkdir()
    make_workspace(root)
    cli = root / ".dadaia/.venv/bin/dadaia"
    red = f'print("[error] SPEC-DOC-004 bad Status", "{DOCTOR_FIX}", sep="\\n"); sys.exit(1)'
    assert RED_DOCTOR in cli.read_text()
    patch_cli(root, RED_DOCTOR, red)
    git(root / "repos/r", "checkout", "-q", "feature/0.5.0")
    assert run(root, "new", "r", "0.5.0-rc1/define").returncode == 0
    tree = root / "worktrees/r/0.5.0-rc1/define"
    approve(root, commit(tree, "specs/notes", ""))
    refused = run(root, "merge", str(tree))
    assert refused.returncode == 1
    assert fixes(refused) == [DOCTOR_FIX]
    assert refused.stderr.count("[error]") == 1
