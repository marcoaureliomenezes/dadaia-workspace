"""A verb run outside any workspace names the searched directory and prints ONE
runnable ``fix:`` line — ``cd`` to the running CLI's own workspace when it has one,
else the uvx bootstrap.

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

_runner = CliRunner()

_VERBS = [["doctor"], ["context", "list"], ["reports", "validate", "--all"]]


def _workspace(root: Path) -> Path:
    (root / ".dadaia" / "states").mkdir(parents=True)
    (root / ".dadaia" / "states" / "spec_contexts.json").write_text("{}", encoding="utf-8")
    return root


@pytest.mark.parametrize("verb", _VERBS, ids=" ".join)
def test_fix_cds_into_the_cli_own_workspace(
    verb: list[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    own = _workspace(tmp_path / "ws")
    outside = tmp_path / "elsewhere"
    outside.mkdir()
    monkeypatch.setattr(sys, "prefix", str(own / ".dadaia" / ".venv"))
    monkeypatch.chdir(outside)

    result = _runner.invoke(app, verb)

    assert result.exit_code != 0
    assert str(outside) in result.output
    assert "Run 'dadaia init'" not in result.output
    fixes = [line for line in result.output.splitlines() if line.startswith("fix: ")]
    assert fixes == [f"fix: cd {own}"], result.output


def test_fix_bootstraps_when_the_cli_has_no_workspace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sys, "prefix", str(tmp_path / "venv"))
    monkeypatch.chdir(tmp_path)

    result = _runner.invoke(app, ["doctor"])

    fixes = [line for line in result.output.splitlines() if line.startswith("fix: ")]
    assert fixes == ["fix: uvx dadaia-workspace init <dir>"], result.output
