"""A bound APPROVED older than the handoff
zone's TTL is held by the real expiry lane, and the merge of its sha still lands.
Size: MEDIUM (real git, tmp workspace, a stub CLI, the real doctor).
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from dadaia_workspace.core.workspace_layout import DADAIA_ZONES
from tests.helpers.worktree_ws import (
    NEW_JOB,
    NEW_TASK,
    approve,
    commit,
    git,
    make_workspace,
    registered_doctor,
    run,
)

RC = "0.5.0/rc-1/wt-rc"


@pytest.fixture
def root(tmp_path: Path) -> Path:
    (tmp_path := tmp_path / "my ws").mkdir()
    make_workspace(tmp_path)
    git(tmp_path / "repos/r", "checkout", "-q", "feature/0.5.0")
    for name in (RC, NEW_JOB, NEW_TASK):
        assert run(tmp_path, "new", "r", name).returncode == 0
    return tmp_path


def test_a_verdict_reaped_past_the_handoff_ttl_still_lands_its_merge(root: Path) -> None:
    commit(root / "worktrees/r" / NEW_TASK, "src/a.py")
    assert run(root, "merge", f"worktrees/r/{NEW_TASK}").returncode == 0
    head = git(root / "worktrees/r" / NEW_JOB, "rev-parse", "HEAD").strip()
    handoff = approve(root, head)
    ttl = next(z.ttl_seconds for z in DADAIA_ZONES if z.name == "handoff")
    assert ttl is not None
    aged = time.time() - ttl - 60
    os.utime(handoff, (aged, aged))
    registered_doctor(root).expire()
    assert not handoff.exists()  # the real lane moved it out of the zone
    landed = run(root, "merge", f"worktrees/r/{NEW_JOB}")
    assert landed.returncode == 0, landed.stderr
    assert git(root / "repos/r", "rev-parse", f"wt/{RC}").strip() == head
