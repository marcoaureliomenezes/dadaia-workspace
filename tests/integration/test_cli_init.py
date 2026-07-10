"""dadaia init CLI — one fn: creates .dadaia+states, idempotent rerun, cwd default.

Merged per plan-integration.md (5 -> 1). Deleted the skip-message + assets-output
wording greps.
"""

from pathlib import Path

from typer.testing import CliRunner

from dadaia_workspace.cli.main import app

_runner = CliRunner()


def test_init_creates_states_idempotent_and_cwd_default(tmp_path: Path, monkeypatch) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    monkeypatch.chdir(ws)

    result = _runner.invoke(app, ["init", "--workspace", str(ws), "--skip-assets"])
    assert result.exit_code == 0, result.output
    assert (ws / ".dadaia").exists()
    assert (ws / ".dadaia" / "states" / "spec_contexts.json").exists()

    rerun = _runner.invoke(app, ["init", "--workspace", str(ws), "--skip-assets"])
    assert rerun.exit_code == 0, rerun.output

    # cwd-default case: a sibling (not nested) root so upward .dadaia resolution from
    # the first workspace never interferes.
    cwd_ws = tmp_path / "cwd-case"
    cwd_ws.mkdir()
    monkeypatch.chdir(cwd_ws)
    cwd_result = _runner.invoke(app, ["init", "--skip-assets"])
    assert cwd_result.exit_code == 0, cwd_result.output
    assert (cwd_ws / ".dadaia").exists()
