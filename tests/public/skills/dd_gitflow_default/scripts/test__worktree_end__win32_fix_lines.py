"""`_worktree_end` names the open child and the unmerged tree through the kernel's `command`: on a
faked win32 host a path holding `%` has no safe spelling, so each line is an Agent action.
Size: SMALL."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

from dadaia_workspace.core.skill_owner import load_owner
from tests.helpers.oslib import command, detect, inline

_WIN = detect("win32")


@pytest.fixture
def end(monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.setattr(sys, "platform", "win32")
    return load_owner("dd-gitflow-default", "_worktree_end")


def test_an_open_child_is_named_by_a_command_line(
    end: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    child = {"name": "0.5.0/rc-1/job-1/wt-main", "path": "/w/a%b"}
    monkeypatch.setattr(end, "ours", lambda repo: [child])
    with pytest.raises(end.Refusal) as refused:
        end._open_children(Path("r"), "0.5.0/rc-1/wt-rc")
    assert refused.value.fix == command(*end.LAUNCH, "merge", "/w/a%b", caps=_WIN)


def test_an_unmerged_tree_is_named_by_a_command_line(
    end: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    tree = tmp_path.resolve() / "a%b"
    name = "0.5.0/rc-1/wt-rc"
    monkeypatch.setattr(end, "_target", lambda root, path: (tmp_path, tree, name, "feature/0.5.0"))
    monkeypatch.setattr(end, "ours", lambda repo: [{"path": str(tree), "name": name}])
    monkeypatch.setattr(end, "git", lambda *a, **k: "2")
    with pytest.raises(end.Refusal) as refused:
        end.clean(tmp_path, "p", [], False)
    assert refused.value.fix == (
        f"Agent action: dispatch dd-code-reviewer on {tree} at its HEAD, then run "
        f"`{inline(*end.LAUNCH, 'merge', str(tree), caps=_WIN)}`"
    )
