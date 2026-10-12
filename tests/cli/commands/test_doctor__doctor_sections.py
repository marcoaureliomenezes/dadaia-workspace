"""`specs doctor` and `backlog doctor` no longer exist: `dadaia doctor` is the one command."""

from __future__ import annotations

from typer.testing import CliRunner

from dadaia_workspace.cli.help_digest import command_paths
from dadaia_workspace.cli.main import app

_runner = CliRunner()


def test_specs_doctor_and_backlog_doctor_commands_are_gone() -> None:
    """(c) the two replaced commands are DELETED, not aliased — no hidden survivor in
    the Typer tree, and therefore none in the backlog subject registry's CLI anchors."""
    anchors = {" ".join(p) for p in command_paths()}
    assert "specs doctor" not in anchors
    assert "backlog doctor" not in anchors
    assert "doctor" in anchors
    for group, verb in (("specs", "doctor"), ("backlog", "doctor")):
        result = _runner.invoke(app, [group, verb, "--help"])
        assert result.exit_code != 0, f"`dadaia {group} {verb}` still resolves"
