"""Characterization of ``dadaia init`` at the public CLI."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app


@pytest.mark.medium
@pytest.mark.slow(reason="runs the public workspace bootstrap")
def test_init_creates_the_literal_level_one_state(tmp_path: Path) -> None:
    ws = tmp_path / "ws"

    result = CliRunner().invoke(app, ["init", str(ws), "--harness", "claude"])

    assert result.exit_code == 0
    cli = ws / ".dadaia" / ".venv" / "bin" / "dadaia"
    assert result.output == (
        f"✓ Workspace {ws} (claude)\n"
        "✓ 164 asset(s) installed\n"
        f"CLI: {cli}\n"
        "Sessions launch at the workspace root.\n"
        "Next (command step context): no ALIVE Spec Context — create one\n"
        f"fix: Operator action: run {cli} context create with a context name and --main-repo "
        "set to the main repo's clone URL\n"
    )
    assert (ws / ".dadaia/states/spec_contexts.json").read_bytes() == (
        b'{\n  "schema_version": "2",\n  "contexts": []\n}'
    )
    assert (ws / ".dadaia/states/harness_profile.json").read_bytes() == (
        b'{\n  "schema_version": "1",\n  "harnesses": [\n    "claude"\n  ]\n}'
    )
