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
from tests.helpers.oslib import cli_path, command, stub_cli, write_text


def _bound_fix(ws: Path, _capsys: pytest.CaptureFixture[str], _mp: pytest.MonkeyPatch) -> str:
    return load_owner("dd-bug-resolution", "_specs")._bound_fix(ws / "repos/r", "rerun", None)[0]


def _worktree_cli(ws: Path, _capsys: pytest.CaptureFixture[str], _mp: pytest.MonkeyPatch) -> str:
    git = load_owner("dd-gitflow-default", "_worktree_git")
    with pytest.raises(git.Refusal) as refused:
        git.cli(ws, "context", "list", tree=ws / "repos/r")
    return str(refused.value.fix)


def _verdict(ws: Path, capsys: pytest.CaptureFixture[str], mp: pytest.MonkeyPatch) -> str:
    verdict = load_owner("dd-handoff-emitter", "verdict")
    real = verdict.run
    bound = {"scope": "wt/x@1", "reviewed_sha": "1" * 40, "diff_sha256": "2" * 64, "root": str(ws)}

    def run(cmd: list[str], *a: object, **k: object) -> subprocess.CompletedProcess[str]:
        if str(cmd[1]).endswith("worktree.py"):
            return subprocess.CompletedProcess(cmd, 0, json.dumps(bound), "")
        return real(cmd, *a, **k)  # type: ignore[call-overload,no-any-return]

    mp.setattr(verdict, "run", run)
    mp.setattr(sys, "stdin", io.StringIO("{}"))
    argv = [str(ws), "--sha", "1" * 40, "--context", "c", "--slug", "s", "--verdict", "APPROVED", "--reason", "r"]  # fmt: skip
    assert verdict.main(argv) == 1
    assert not list((ws / ".dadaia/handoff").glob("**/*.json"))
    return next(x[5:] for x in capsys.readouterr().err.splitlines() if x.startswith("fix: "))


@pytest.mark.parametrize("caller", [_bound_fix, _worktree_cli, _verdict])
def test_a_workspace_cli_that_cannot_run_refuses_with_the_install_fix(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    caller: Callable[[Path, pytest.CaptureFixture[str], pytest.MonkeyPatch], str],
) -> None:
    (cli := cli_path(tmp_path)).parent.mkdir(parents=True)
    write_text(cli, "#!/bin/sh\n")
    (tmp_path / ".dadaia/states").mkdir()
    write_text(tmp_path / ".dadaia/states/spec_contexts.json", "{}")
    (tmp_path / "repos/r").mkdir(parents=True)
    assert caller(tmp_path, capsys, monkeypatch) == command(
        "uvx", "dadaia-workspace", "init", str(tmp_path)
    )


def test_run_cli_with_the_root_found_and_the_cli_missing_refuses_with_the_install_fix(
    tmp_path: Path,
) -> None:
    (tmp_path / ".dadaia/states").mkdir(parents=True)
    write_text(tmp_path / ".dadaia/states/spec_contexts.json", "{}")
    specs = load_owner("dd-bug-resolution", "_specs")
    with pytest.raises(specs.Refusal) as refused:
        specs.run_cli(tmp_path, "context", "list")
    assert refused.value.fix == command("uvx", "dadaia-workspace", "init", str(tmp_path))


_ROWS = [
    {"name": "c", "main_repo": "r", "associated_repos": [{"slug": "a"}, {"slug": "gone"}]},
    {"name": "d", "main_repo": "z", "associated_repos": [{"slug": "y"}]},
]


def _workspace(root: Path, cli: str) -> Path:
    """A workspace whose CLI runs *cli*, holding checkouts r, a (of context c), q (of none) and y (of d)."""
    (cli_dir := cli_path(root).parent).mkdir(parents=True)
    stub_cli(cli_dir, "dadaia", cli)
    (root / ".dadaia/states").mkdir(parents=True)
    write_text(root / ".dadaia/states/spec_contexts.json", "{}")
    for slug in ("r", "a", "q", "y"):
        (root / "repos" / slug / ".git").mkdir(parents=True)
    return root


def _answering(root: Path) -> Path:
    return _workspace(root, f"#!python\nimport json\nprint(json.dumps({_ROWS!r}))\n")


def test_context_row_answers_the_context_that_owns_a_main_or_associated_repo(
    tmp_path: Path,
) -> None:
    specs = load_owner("dd-bug-resolution", "_specs")
    root = _answering(tmp_path)
    assert [(specs.context_row(root, root / "repos" / s) or {}).get("name") for s in ("r", "a", "q", "y")] == ["c", "c", None, "d"]  # fmt: skip


def test_context_repos_is_the_repo_and_the_existing_checkouts_its_context_associates(
    tmp_path: Path,
) -> None:
    specs = load_owner("dd-bug-resolution", "_specs")
    root = _answering(tmp_path)
    assert specs.context_repos(root / "repos/r") == [root / "repos/r", root / "repos/a"]
    assert specs.context_repos(root / "repos/q") == [root / "repos/q"]


def test_context_repos_of_a_repo_with_no_workspace_or_no_cli_is_the_repo_alone(
    tmp_path: Path,
) -> None:
    specs = load_owner("dd-bug-resolution", "_specs")
    (repo := tmp_path / "bare/repos/r").mkdir(parents=True)
    assert specs.context_repos(repo) == [repo]
    (root := tmp_path / "ws").mkdir()
    (root / ".dadaia/states").mkdir(parents=True)
    write_text(root / ".dadaia/states/spec_contexts.json", "{}")
    (repo := root / "repos/r").mkdir(parents=True)
    assert specs.context_repos(repo) == [repo]


def test_a_cli_that_runs_and_fails_refuses_with_its_own_fix_line(tmp_path: Path) -> None:
    specs = load_owner("dd-bug-resolution", "_specs")
    root = _workspace(
        tmp_path,
        "#!python\nimport sys\nprint('[error] bad row', file=sys.stderr)\n"
        "print('fix: Agent action: repair the registry row', file=sys.stderr)\nsys.exit(1)\n",
    )
    for ask in (lambda: specs.context_row(root, root / "repos/r"), lambda: specs.context_repos(root / "repos/r")):  # fmt: skip
        with pytest.raises(specs.Refusal) as refused:
            ask()
        assert refused.value.fix == "Agent action: repair the registry row"
