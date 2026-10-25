"""Every runnable line `worktree.py` prints is the kernel's `command`, and every line inside an
`Agent action:` sentence its `inline`: on a faked win32 host a path holding `%` has no safe
spelling, so each line becomes an Agent action naming the words instead of a hand-quoted guess.
Size: SMALL."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from dadaia_workspace.core.skill_owner import load_owner
from tests.helpers.oslib import command, detect, inline

_WIN = detect("win32")
_OWNER = "dd-gitflow-default"


@pytest.fixture
def win32(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", "win32")


def _mod(name: str) -> Any:
    return load_owner(_OWNER, name)


def test_a_row_names_its_exit_through_command_or_inline(win32: None, tmp_path: Path) -> None:
    git, bad = _mod("_worktree_git"), tmp_path / "a%b"
    ready = git._row(Path("r"), str(bad), "ready")
    assert ready["fix"] == command(*git.LAUNCH, "merge", str(bad), caps=_WIN)
    gone = git._row(Path("r"), str(bad), "orphan")
    assert gone["fix"] == command(*git.LAUNCH, "merge", str(bad), caps=_WIN)
    bad.mkdir()
    held = git._row(Path("r"), str(bad), "orphan")
    assert held["fix"] == (
        f"Agent action: stop what holds files open in {bad}, then move the folder {bad} out of the lane path (it may hold work), then run "
        f"`{inline(*git.LAUNCH, 'merge', str(bad), caps=_WIN)}`"
    )


def test_ignored_files_are_kept_by_a_command_line(
    win32: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    end, tree = _mod("_worktree_end"), tmp_path / "a%b"
    monkeypatch.setattr(end, "git", lambda *a, **k: "!! my%notes.scratch\0")
    with pytest.raises(end.Refusal) as refused:
        end._kept(tree, "merge", [], False)
    keep = inline(*end.LAUNCH, "merge", str(tree), "--keep", "my%notes.scratch", caps=_WIN)
    drop = inline(*end.LAUNCH, "merge", str(tree), "--drop", caps=_WIN)
    assert (
        refused.value.fix == f"Agent action: keep them with `{keep}` or discard them with `{drop}`"
    )


def test_a_red_gate_names_its_argv_through_inline(
    win32: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    end, tree = _mod("_worktree_end"), tmp_path / "worktrees" / "r" / "x"
    monkeypatch.setattr(end, "_declared_argv", lambda *a: ["python", "a%b.py"])
    monkeypatch.setattr(end, "workspace_of", lambda _tree: tmp_path)
    monkeypatch.setattr(
        end, "run", lambda *a, **k: SimpleNamespace(returncode=1, stdout="", stderr="")
    )
    with pytest.raises(end.Refusal) as refused:
        end._gate(tree, "work")
    assert refused.value.fix == (
        f"Agent action: make `{inline('python', 'a%b.py', caps=_WIN)}` exit 0 in {tree}"
        " and commit the fix in this worktree"
    )


def test_a_git_failure_reruns_through_inline(
    win32: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cli = _mod("worktree")
    monkeypatch.setattr(cli, "workspace_of", lambda *a: tmp_path)

    def failing(*a: object) -> str:
        raise cli.GitError(("merge",), "boom")

    monkeypatch.setattr(cli, "merge", failing)
    assert cli.main(["merge", "a%b"]) == 1
    rerun = inline(*cli.LAUNCH, "merge", str(Path("a%b").resolve()), caps=_WIN)
    assert (
        f"Agent action: clear what `git merge` reports above, then rerun {rerun}"
        in capsys.readouterr().err
    )
