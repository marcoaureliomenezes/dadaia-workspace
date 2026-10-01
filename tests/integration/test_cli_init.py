"""dadaia init CLI — one fn: creates .dadaia+states and the level-1 root files from the argv
DIR; the rerun overwrites no operator file."""

from pathlib import Path

from typer.testing import CliRunner

from dadaia_workspace.cli.main import app

_runner = CliRunner()


def test_init_creates_states_and_the_three_root_files_and_is_idempotent(
    tmp_path: Path, monkeypatch
) -> None:
    """Intent: CONTRACT — AC2.2 (ADR 0095): init and its re-run create `prompt.md`,
    `AGENTS.md` and `.dadaiaignore` when absent and never overwrite the operator's."""
    ws = tmp_path / "ws"
    ws.mkdir()
    monkeypatch.chdir(ws)

    result = _runner.invoke(app, ["init", str(ws), "--harness", "claude"])
    assert result.exit_code == 0, result.output
    assert (ws / ".dadaia" / "states" / "spec_contexts.json").exists()
    assert all((ws / name).is_file() for name in ("prompt.md", "AGENTS.md", ".dadaiaignore"))
    for name in ("prompt.md", ".dadaiaignore"):
        (ws / name).write_text("# mine\n", encoding="utf-8")

    rerun = _runner.invoke(app, ["init", str(ws), "--harness", "claude"])
    assert rerun.exit_code == 0, rerun.output
    for name in ("prompt.md", ".dadaiaignore"):
        assert (ws / name).read_text(encoding="utf-8") == "# mine\n", name
