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


def _workspace(root: Path) -> Path:
    (root / ".dadaia" / "states").mkdir(parents=True)
    (root / ".dadaia" / "states" / "spec_contexts.json").write_text("{}", encoding="utf-8")
    return root


@pytest.mark.parametrize(
    "fenced",
    [
        pytest.param(False, id="S1-own-wins-over-cwd"),
        pytest.param(True, id="S11-fenced-own-falls-back-to-cwd"),
    ],
)
def test_the_cli_resolves_its_own_workspace_unless_fenced(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fenced: bool
) -> None:
    """sa-seven-workspace-root-rules#S1: the CLI's own workspace wins over the cwd;
    #S11: a fenced root is never the CLI's own workspace; an explicit start always walks."""
    own, other = _workspace(tmp_path / "a"), _workspace(tmp_path / "b")
    monkeypatch.setattr(sys, "prefix", str(own / ".dadaia" / ".venv"))
    if fenced:
        monkeypatch.setenv(FENCE_ENV, str(own))
    monkeypatch.chdir(other)
    assert resolve_workspace_root() == (other if fenced else own).resolve()
    assert resolve_workspace_root(other) == other.resolve()


def test_fix_bootstraps_when_the_cli_has_no_workspace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sys, "prefix", str(tmp_path / "venv"))
    monkeypatch.chdir(tmp_path)

    result = _runner.invoke(app, ["doctor"])

    fixes = [line for line in result.output.splitlines() if line.startswith("fix: ")]
    assert fixes == ["fix: uvx dadaia-workspace init <dir>"], result.output
