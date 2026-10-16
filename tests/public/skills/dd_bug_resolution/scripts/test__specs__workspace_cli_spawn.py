"""Every spawn of the workspace CLI from a skill script turns a CLI that exists but cannot run
into the one install fix, never a traceback. Size: SMALL."""

from __future__ import annotations

import io
import json
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

from dadaia_workspace.core.skill_owner import load_owner


def _bound_fix(ws: Path, _capsys: pytest.CaptureFixture[str], _mp: pytest.MonkeyPatch) -> str:
    return load_owner("dd-bug-resolution", "_specs")._bound_fix(ws / "repos/r", "rerun", None)[0]


def _worktree_cli(ws: Path, _capsys: pytest.CaptureFixture[str], _mp: pytest.MonkeyPatch) -> str:
    git = load_owner("dd-gitflow-default", "_worktree_git")
    with pytest.raises(git.Refusal) as refused:
        git.cli(ws, "context", "list", tree=ws / "repos/r")
    return str(refused.value.fix)


def _verdict(ws: Path, capsys: pytest.CaptureFixture[str], mp: pytest.MonkeyPatch) -> str:
    verdict = load_owner("dd-handoff-emitter", "verdict")
    real = subprocess.run
    bound = {"scope": "wt/x@1", "reviewed_sha": "1" * 40, "diff_sha256": "2" * 64, "root": str(ws)}

    def run(cmd: list[str], *a: object, **k: object) -> subprocess.CompletedProcess[str]:
        if str(cmd[1]).endswith("worktree.py"):
            return subprocess.CompletedProcess(cmd, 0, json.dumps(bound), "")
        return real(cmd, *a, **k)  # type: ignore[call-overload,no-any-return]

    mp.setattr(verdict.subprocess, "run", run)
    mp.setattr(sys, "stdin", io.StringIO("{}"))
    argv = [str(ws), "--sha", "1" * 40, "--context", "c", "--slug", "s", "--verdict", "APPROVED", "--reason", "r"]  # fmt: skip
    assert verdict.main(argv) == 1
    assert not list((ws / ".dadaia/handoff").glob("**/*.json"))
    return next(x[5:] for x in capsys.readouterr().err.splitlines() if x.startswith("fix: "))


@pytest.mark.skipif(sys.platform == "win32", reason="a non-executable file is a POSIX mode")
@pytest.mark.parametrize("caller", [_bound_fix, _worktree_cli, _verdict])
def test_a_workspace_cli_that_cannot_run_refuses_with_the_install_fix(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    caller: Callable[[Path, pytest.CaptureFixture[str], pytest.MonkeyPatch], str],
) -> None:
    (cli := tmp_path / ".dadaia/.venv/bin/dadaia").parent.mkdir(parents=True)
    cli.write_text("#!/bin/sh\n", "utf-8")
    cli.chmod(0o644)
    (tmp_path / ".dadaia/states").mkdir()
    (tmp_path / ".dadaia/states/spec_contexts.json").write_text("{}")
    (tmp_path / "repos/r").mkdir(parents=True)
    assert caller(tmp_path, capsys, monkeypatch) == f"uvx dadaia-workspace init {tmp_path}"
