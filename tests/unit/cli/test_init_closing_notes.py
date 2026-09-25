"""``dadaia init`` closes with the root-launch law exactly once and prints no harness
settings advice.

Intent: CONTRACT — 0.4.7 FR3c (T-047-57) + bug init-claude-note-cites-a-wrong-settings-key.
Size: SMALL.

Claude Code reads the root ``AGENTS.md`` natively, so init has no settings key to
recommend; the note it once printed named a key that does not exist.

QA-atom law (v0.1.57): ``CliRunner`` is built with NO ``mix_stderr`` kwarg.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app

_runner = CliRunner()

_LAW = "Sessions launch at the workspace root."


@pytest.mark.parametrize("harness", ["claude", "codex"])
def test_init_prints_the_law_once_and_no_settings_advice(tmp_path: Path, harness: str) -> None:
    result = _runner.invoke(app, ["init", str(tmp_path / "ws"), "--harness", harness])

    assert result.exit_code == 0, result.stdout
    assert result.stdout.count(_LAW) == 1
    assert "settings" not in result.stdout
    assert "instructionFiles" not in result.stdout
