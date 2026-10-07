"""reaper-deletes-linked-git-worktrees: `sweep.remove`/`sweep.move`,
the one chokepoint of every reaper deletion and slop move, never touches a registered
linked worktree — an expired one under `.dadaia/tmp/` or one at an unlisted root entry.
AC1.10: the doctor lists the context's worktrees from git and touches none — a canonical one
with kind/age/ahead/state and, ready, its `worktree.py merge` fix; a foreign one (never a TTL
`expired` entry), an orphan `wt/*` and an unregistered `worktrees/` dir as findings.
Size: MEDIUM — git's own `.git`-file shape and `prunable` verdict are the contract.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import time
from pathlib import Path

import pytest

from dadaia_workspace.core.cli_line import shell_line
from dadaia_workspace.features.spec_context.doctor import DoctorService
from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient
from tests.fixtures.stores import context_store
from tests.helpers import worktree_ws

_TWO_DAYS_AGO = time.time() - 2 * 86_400

pytestmark = pytest.mark.slow(reason="real git init + worktree add subprocesses")


def _git(cwd: Path, *args: str) -> str:
    done = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True)
    return done.stdout


def _workspace_with_worktree(root: Path, worktree_rel: str) -> tuple[Path, Path]:
    for zone in ("tmp", "states", "sessions", "reaped"):
        (root / ".dadaia" / zone).mkdir(parents=True, exist_ok=True)
    (root / ".dadaia" / "states" / "spec_contexts.json").write_text(
        '{"contexts": [{"name": "lib", "repo_slug": "lib", "state": "alive"}]}', encoding="utf-8"
    )
    repo = root / "repos" / "lib"
    repo.mkdir(parents=True)
    _git(repo, "init", "-q", "-b", "main")
    (repo / "f.txt").write_text("f", encoding="utf-8")
    _git(repo, "add", "f.txt")
    _git(repo, "commit", "-q", "-m", "init")
    worktree = root / worktree_rel
    worktree.parent.mkdir(parents=True, exist_ok=True)
    _git(repo, "worktree", "add", "-q", "-b", "wt/a", str(worktree))
    (worktree / "uncommitted.txt").write_text("work in progress", encoding="utf-8")
    return repo, worktree


def _age_tree(top: Path) -> None:
    for dirpath, dirnames, filenames in os.walk(top, topdown=False):
        for name in [*filenames, *dirnames]:
            os.utime(Path(dirpath) / name, (_TWO_DAYS_AGO, _TWO_DAYS_AGO))
    os.utime(top, (_TWO_DAYS_AGO, _TWO_DAYS_AGO))


def _doctor(root: Path) -> DoctorService:
    return DoctorService(context_store(root / ".dadaia" / "states"), GitSubprocessClient(), root)


def _fix(root: Path) -> list[str]:
    return _doctor(root).fix()


@pytest.mark.parametrize(
    ("worktree_rel", "aged"),
    [(".dadaia/tmp/claude/20200101/wt-a", ".dadaia/tmp/claude"), ("scratch/wt-b", "")],
    ids=["ttl-reaper-expired-worktree", "slop-mover-unlisted-root-entry"],
)
def test_doctor_fix_never_reaps_or_moves_a_linked_worktree(
    tmp_path: Path, worktree_rel: str, aged: str
) -> None:
    repo, worktree = _workspace_with_worktree(tmp_path, worktree_rel)
    if aged:
        _age_tree(tmp_path / aged)

    _fix(tmp_path)

    assert (worktree / "uncommitted.txt").read_text(encoding="utf-8") == "work in progress"
    assert (worktree / ".git").is_file()
    assert "prunable" not in _git(repo, "worktree", "list", "--porcelain")


def test_doctor_lists_the_contexts_worktrees_from_git_and_touches_none(tmp_path: Path) -> None:
    (tmp_path := tmp_path / "my ws").mkdir()  # the fix quotes its spaced path
    root = worktree_ws.make_workspace(tmp_path)
    repo = root / "repos/r"
    worktree_ws.git(repo, "checkout", "-q", "feature/0.5.0")
    for job in ("j1", "j2"):
        assert worktree_ws.run(root, "new", "r", f"0.5.0-rc1/{job}").returncode == 0
    ready, empty = root / "worktrees/r/0.5.0-rc1/j1", root / "worktrees/r/0.5.0-rc1/j2"
    worktree_ws.commit(ready, "src/a.py")
    log = repo / ".git/logs/refs/heads/wt/0.5.0-rc1/j1"  # age is the branch's birth (ADR 0108)
    log.write_text(re.sub(r"> \d+ ", f"> {int(_TWO_DAYS_AGO)} ", log.read_text(), count=1))
    foreign = root / ".dadaia/tmp/claude/20200101/wt-a"
    # a canonical wt/ branch outside worktrees/r/ is still foreign — its merge would refuse
    worktree_ws.git(repo, "worktree", "add", "-q", "-b", "wt/0.5.0-rc1/j4", str(foreign))
    _age_tree(root / ".dadaia/tmp/claude")
    worktree_ws.git(repo, "branch", "wt/0.5.0-rc1/j3")
    (root / "worktrees/r/0.5.0-rc1/stray").mkdir()
    doctor = worktree_ws.registered_doctor(root)

    # a message is "<state> <path>  k=v…"
    found = {f.message.split(" ", 1)[1].split("  ")[0]: f for f in doctor.check_worktrees("c")}

    assert found[str(ready)].verdict == "warning"
    assert found[str(ready)].fix == shell_line(sys.executable, str(worktree_ws.SCRIPT), "merge", str(ready))
    assert found[str(empty)].message.startswith("empty") and found[str(empty)].fix == ""
    assert found[str(foreign)].message.startswith("foreign")  # the expired TTL entry surfaces here
    assert not [f for f in doctor.scan_ttl() if "20200101" in f.path]
    assert found[str(root / "worktrees/r/0.5.0-rc1/j3")].message.startswith("orphan")
    assert found[str(root / "worktrees/r/0.5.0-rc1/stray")].message.startswith("unregistered")
    (ready / "wip.txt").write_text("x")
    assert [f.fix for f in doctor.check_worktrees("c") if str(ready) in f.message] == [""]  # dirty
    doctor.fix()
    assert ready.is_dir() and empty.is_dir() and foreign.is_dir()
