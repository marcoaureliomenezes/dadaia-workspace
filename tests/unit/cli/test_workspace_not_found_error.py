"""A verb run outside any workspace runs in the CLI's own workspace (review M1: fix lines
run from any cwd); with none, it names the searched directory and prints ONE runnable
``fix:`` line — the uvx bootstrap.

Intent: CONTRACT — bug workspace-not-found-error-is-false-and-fixless. Size: SMALL.

The CLI's own workspace is derived from ``sys.prefix`` (the venv lives at
``<root>/.dadaia/.venv``) — patched here as the interpreter boundary.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.core.workspace_resolver import FENCE_ENV, resolve_workspace_root

_runner = CliRunner()

_VERBS = [["doctor"], ["context", "list"], ["reports", "validate", "--all"]]


def _workspace(root: Path) -> Path:
    (root / ".dadaia" / "states").mkdir(parents=True)
    (root / ".dadaia" / "states" / "spec_contexts.json").write_text("{}", encoding="utf-8")
    return root


@pytest.mark.parametrize("verb", _VERBS, ids=" ".join)
def test_a_verb_outside_runs_in_the_cli_own_workspace(
    verb: list[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    own = _workspace(tmp_path / "ws")
    outside = tmp_path / "elsewhere"
    outside.mkdir()
    monkeypatch.setattr(sys, "prefix", str(own / ".dadaia" / ".venv"))
    monkeypatch.chdir(outside)

    result = _runner.invoke(app, verb)

    assert "No initialized workspace" not in result.output, result.output


def test_inside_another_workspace_the_cli_resolves_its_own(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    own, other = _workspace(tmp_path / "a"), _workspace(tmp_path / "b")
    monkeypatch.setattr(sys, "prefix", str(own / ".dadaia" / ".venv"))
    monkeypatch.chdir(other)
    assert resolve_workspace_root() == own.resolve()
    assert resolve_workspace_root(other) == other.resolve()  # an explicit start walks


def test_a_fenced_own_workspace_falls_back_to_the_cwd_walk(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    own, other = _workspace(tmp_path / "a"), _workspace(tmp_path / "b")
    monkeypatch.setattr(sys, "prefix", str(own / ".dadaia" / ".venv"))
    monkeypatch.setenv(FENCE_ENV, str(own))
    monkeypatch.chdir(other)
    assert resolve_workspace_root() == other.resolve()


def test_fix_bootstraps_when_the_cli_has_no_workspace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sys, "prefix", str(tmp_path / "venv"))
    monkeypatch.chdir(tmp_path)

    result = _runner.invoke(app, ["doctor"])

    fixes = [line for line in result.output.splitlines() if line.startswith("fix: ")]
    assert fixes == ["fix: uvx dadaia-workspace init <dir>"], result.output
