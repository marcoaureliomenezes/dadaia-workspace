"""A backlog-lane merge runs the workspace
doctor on its own `specs/` — the check the work branch's CI runs — fenced to the tree, so a tree
the doctor refuses never lands. Size: MEDIUM (real git, tmp workspace, a stub CLI).
"""

from __future__ import annotations

import os
from pathlib import Path

from tests.helpers.oslib import cli_argv, inline, venv_dir
from tests.helpers.worktree_ws import approve, commit, fixes, git, make_workspace, patch_cli, run

LANE, RC = "0.5.0/wt-backlog-d", "0.5.0/rc-1/wt-rc"


def test_a_backlog_merge_runs_the_doctor_fenced_to_its_tree(tmp_path: Path) -> None:
    (root := tmp_path / "ws").mkdir()
    make_workspace(root)
    git(root / "repos/r", "checkout", "-q", "feature/0.5.0")
    assert run(root, "new", "r", LANE).returncode == 0
    tree = root / "worktrees/r" / LANE
    approve(root, commit(tree, "specs/RED-doctor", ""))
    refused = run(root, "merge", str(tree))
    assert refused.returncode == 1 and "dadaia doctor check failed" in refused.stderr
    out = refused.stdout.splitlines()
    assert out[0] == f"doctor --specs-dir {tree / 'specs'}" and out[2] == f"cwd {tree}"
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
    red = f'print("[error] SPEC-DOC-004 bad Status", "{DOCTOR_FIX}", sep="\\n"); sys.exit(1)'
    patch_cli(root, RED_DOCTOR, red)
    git(root / "repos/r", "checkout", "-q", "feature/0.5.0")
    assert run(root, "new", "r", LANE).returncode == 0
    tree = root / "worktrees/r" / LANE
    approve(root, commit(tree, "specs/notes", ""))
    refused = run(root, "merge", str(tree))
    assert refused.returncode == 1
    assert fixes(refused) == [DOCTOR_FIX]
    assert refused.stderr.count("[error]") == 1


def test_a_backlog_merge_lands_specs_only(tmp_path: Path) -> None:
    (root := tmp_path / "ws").mkdir()
    make_workspace(root)
    git(root / "repos/r", "checkout", "-q", "feature/0.5.0")
    assert run(root, "new", "r", LANE).returncode == 0
    tree = root / "worktrees/r" / LANE
    approve(root, commit(tree, "src/a.py"))
    refused = run(root, "merge", str(tree))
    assert refused.returncode == 1 and "src/a.py is code" in refused.stderr


def test_an_rc_merge_runs_the_job_gate(tmp_path: Path) -> None:
    (root := tmp_path / "ws").mkdir()
    make_workspace(root)
    git(root / "repos/r", "checkout", "-q", "feature/0.5.0")
    assert run(root, "new", "r", RC).returncode == 0
    tree = root / "worktrees/r" / RC
    approve(root, commit(tree, "RED-job", ""), name=RC)
    refused = run(root, "merge", str(tree))
    sync = inline(*cli_argv(venv_dir(root)), "worktree", "sync", str(tree))
    assert refused.returncode == 1 and "verify: exited 1" in refused.stderr
    assert fixes(refused) == [
        f"fix: Agent action: make `python scripts/ci.py job` exit 0 in {tree} and commit the fix"
        " in this worktree when a reconcile commit is at fault, or through a wt-hotfix lane when"
        f" the work branch's verify: fails too, then `{sync}`"
    ]


def test_an_rc_gate_red_from_the_work_branch_clears_through_a_hotfix_then_the_printed_sync(
    tmp_path: Path,
) -> None:
    (root := tmp_path / "ws").mkdir()
    make_workspace(root)
    repo = root / "repos/r"
    git(repo, "checkout", "-q", "feature/0.5.0")
    commit(repo, "RED-job", "")
    commit(repo, "specs/bugs/BUGS.jsonl", '{"id": "some-bug", "status": "open"}\n')
    assert run(root, "new", "r", RC).returncode == 0
    tree = root / "worktrees/r" / RC
    approve(root, commit(tree, "src/z.py"), name=RC)
    refused = run(root, "merge", str(tree))
    sync = inline(*cli_argv(venv_dir(root)), "worktree", "sync", str(tree))
    assert refused.returncode == 1 and fixes(refused)[0].endswith(f"then `{sync}`")
    hotfix = root / "worktrees/r/0.5.0/wt-hotfix-some-bug"
    assert run(root, "new", "r", "0.5.0/wt-hotfix-some-bug").returncode == 0
    git(hotfix, "rm", "-q", "RED-job")
    git(hotfix, "commit", "-qm", "fix code")
    approve(root, git(hotfix, "rev-parse", "HEAD").strip(), name="0.5.0/wt-hotfix-some-bug")
    assert run(root, "merge", str(hotfix)).returncode == 0
    assert run(root, "sync", str(tree)).returncode == 0
    approve(root, git(tree, "rev-parse", "HEAD").strip(), name=RC, at="T11:00:00Z")
    landed = run(root, "merge", str(tree))
    assert landed.returncode == 0, landed.stderr
