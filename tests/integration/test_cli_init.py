"""dadaia init CLI — one fn: creates .dadaia+states from the argv DIR, idempotent rerun.

Merged per plan-integration.md (5 -> 1). Deleted the skip-message + assets-output
wording greps.
"""

from pathlib import Path

from typer.testing import CliRunner

from dadaia_workspace.cli.main import app

_runner = CliRunner()


def test_init_creates_states_and_is_idempotent(tmp_path: Path, monkeypatch) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    monkeypatch.chdir(ws)

    result = _runner.invoke(app, ["init", str(ws), "--harness", "claude", "--skip-assets"])
    assert result.exit_code == 0, result.output
    assert (ws / ".dadaia").exists()
    assert (ws / ".dadaia" / "states" / "spec_contexts.json").exists()

    rerun = _runner.invoke(app, ["init", str(ws), "--harness", "claude", "--skip-assets"])
    assert rerun.exit_code == 0, rerun.output
