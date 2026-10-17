"""`_worktree_new` names the missing parent's `new` through the kernel's `command`: on a faked
win32 host a repo name holding `%` has no safe spelling, so the line is an Agent action.
Size: SMALL."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

from dadaia_workspace.core.skill_owner import load_owner
from tests.helpers.oslib import command, detect


def test_a_missing_parent_branch_is_named_by_a_command_line(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    new: Any = load_owner("dd-gitflow-default", "_worktree_new")
    name = "0.5.0/rc-1/job-1/wt-main"
    monkeypatch.setattr(new, "_refuse_symlink", lambda *a: None)
    monkeypatch.setattr(new, "flow_for", lambda *a: {"work": "feature/", "main": "r"})
    monkeypatch.setattr(new, "work_version", lambda *a: "0.5.0")
    monkeypatch.setattr(new, "git", lambda *a, **k: "")
    with pytest.raises(new.Refusal) as refused:
        new.new(tmp_path, "a%b", name)
    start = new.base_of(name, "feature/")
    assert refused.value.fix == command(
        *new.LAUNCH, "new", "a%b", start.removeprefix("wt/"), caps=detect("win32")
    )
