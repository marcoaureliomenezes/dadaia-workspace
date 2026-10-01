"""dadaia init CLI — one fn: creates .dadaia+states and the level-1 root files from the argv
DIR; the rerun overwrites no operator file."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.core.workspace_layout import occupied

_runner = CliRunner()


@pytest.mark.parametrize(
    "links",
    [(), ("prompt.md", ".dadaia/states/server_registry.json")],
    ids=["fresh", "dangling-links-never-written-through"],
)
def test_init_creates_states_and_the_three_root_files_and_is_idempotent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, links: tuple[str, ...]
) -> None:
    """Intent: CONTRACT — AC2.2 (ADR 0095): init and its re-run create `prompt.md`,
    `AGENTS.md` and `.dadaiaignore` when absent and never overwrite the operator's; a dangling
    link (CWE-59) is present, never written through."""
    ws, outside = tmp_path / "ws", tmp_path / "outside"
    outside.mkdir()
    for rel in links:
        (ws / rel).parent.mkdir(parents=True, exist_ok=True)
        (ws / rel).symlink_to(outside / Path(rel).name)
    ws.mkdir(exist_ok=True)
    monkeypatch.chdir(ws)

    result = _runner.invoke(app, ["init", str(ws), "--harness", "claude"])
    assert result.exit_code == 0, result.output
    assert occupied(ws / ".dadaia" / "states" / "spec_contexts.json")
    assert all(occupied(ws / name) for name in ("prompt.md", "AGENTS.md", ".dadaiaignore"))
    assert list(outside.iterdir()) == []
    (ws / ".dadaiaignore").write_text("# mine\n", encoding="utf-8")

    rerun = _runner.invoke(app, ["init", str(ws), "--harness", "claude"])
    assert rerun.exit_code == 0, rerun.output
    assert (ws / ".dadaiaignore").read_text(encoding="utf-8") == "# mine\n"
    assert list(outside.iterdir()) == []
